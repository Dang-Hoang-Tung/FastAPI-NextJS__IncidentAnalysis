import csv
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI
from pydantic import BaseModel

# LangChain (new layout)
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser


# ------------------------------------------------------
# FastAPI App
# ------------------------------------------------------

app = FastAPI(
    title="Incident Response API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


# ------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------

class TranscriptRequest(BaseModel):
    transcript: str


class PolicyIssue(BaseModel):
    policy_id: Optional[str] = None   # e.g. "Section 3: Mobility & Moving"
    description: str                  # what the issue is
    severity: str                     # Low / Medium / High / Critical
    evidence: str                     # quotes / details from transcript


class IncidentForm(BaseModel):
    title: str
    incident_summary: str
    policies_breached: List[str]
    risk_level: str
    recommended_actions: List[str]


class IncidentResponse(BaseModel):
    incident_form: IncidentForm
    email_draft: str
    issues: List[PolicyIssue]


# ------------------------------------------------------
# Data loading (policies + templates)
# ------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def safe_read_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8")


# 1) Policies & procedures (full document)
POLICIES_TEXT = safe_read_text(DATA_DIR / "Policies and Procedures Document.txt")

# 2) Incident report form “template” – derive from CSV headers
def load_incident_form_fields(path: Path) -> List[str]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            headers = []
    # strip whitespace
    return [h.strip() for h in headers if h and h.strip()]

INCIDENT_FIELDS = load_incident_form_fields(DATA_DIR / "Incident Report Form.csv")

INCIDENT_TEMPLATE_TEXT = (
    "Incident Report Form fields:\n"
    + "\n".join(f"- {field}" for field in INCIDENT_FIELDS)
    if INCIDENT_FIELDS
    else "Incident Report Form with standard fields such as date, time, location, "
         "individual involved, description of incident, actions taken, and follow-up."
)

# 3) Email template (you can create / change this file)
EMAIL_TEMPLATE = safe_read_text(
    DATA_DIR / "email_template.txt",
    default=(
        "Subject: Incident Report - {service_user_name}\n\n"
        "Dear {recipient_name},\n\n"
        "I am writing to report an incident involving {service_user_name} that "
        "occurred on {incident_date}. Please find the details below:\n\n"
        "{incident_summary}\n\n"
        "Policies breached / key concerns:\n{policies_breached}\n\n"
        "Recommended actions:\n{recommended_actions}\n\n"
        "Kind regards,\n\n{sender_name}\n"
    ),
)


# ------------------------------------------------------
# LangChain setup (new style)
# ------------------------------------------------------

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
)

policy_parser = JsonOutputParser()
incident_parser = JsonOutputParser()
email_parser = StrOutputParser()


# ---------- Policy analysis chain ----------

policy_prompt = PromptTemplate(
    template="""
You are an expert in safeguarding and incident reporting in social care.

You are given:
- A telephone / meeting transcript.
- The organisation's Policies and Procedures document.

POLICIES AND PROCEDURES:
{policies_text}

TRANSCRIPT:
{transcript}

Identify potential policy issues or concerns. For each issue, provide:
- policy_id: the most relevant section name or heading from the policy document
             (e.g. "Section 3: Mobility & Moving", "Section 5: Mental Health and Emotional Well-being"),
             or null if not clear.
- description: a concise description of the concern.
- severity: one of ["Low", "Medium", "High", "Critical"] based on risk and recurrence.
- evidence: short quotes or clear references from the transcript.

Return a JSON array in the following format:

{format_instructions}
""",
    input_variables=["policies_text", "transcript"],
    partial_variables={
        "format_instructions": policy_parser.get_format_instructions()
    },
)

policy_chain = policy_prompt | llm | policy_parser


# ---------- Incident form chain ----------

incident_prompt = PromptTemplate(
    template="""
You are completing an incident report form for a social care provider.

Here are the organisation's incident form fields:
{incident_template_text}

You are also given:
- A list of policy issues in JSON.
- The original transcript.

POLICY ISSUES (JSON):
{issues_json}

TRANSCRIPT:
{transcript}

Using all the above, generate a single JSON object for the incident form with
the following structure:

{format_instructions}

Guidance:
- "title": a short, clear title for the incident (e.g. "Repeated falls at home").
- "incident_summary": clear narrative of what happened, drawing on transcript.
- "policies_breached": list of policy section names or IDs that are relevant.
- "risk_level": overall risk level, one of ["Low", "Medium", "High", "Critical"].
- "recommended_actions": list of concrete next steps (e.g. arrange risk assessment,
  inform family, review care plan, contact GP, etc.).
""",
    input_variables=["incident_template_text", "issues_json", "transcript"],
    partial_variables={
        "format_instructions": incident_parser.get_format_instructions()
    },
)

incident_chain = incident_prompt | llm | incident_parser


# ---------- Email drafting chain ----------

email_prompt = PromptTemplate(
    template="""
You are drafting a professional escalation email based on an incident form
and an email template.

EMAIL TEMPLATE:
{email_template}

INCIDENT FORM (JSON):
{incident_form_json}

Write a clear, concise, and professional email to the appropriate recipient(s):
- Summarise the incident.
- Mention key policy sections breached and the overall risk level.
- Include recommended actions where relevant.
- Maintain a supportive, non-blaming tone.
- Assume UK social care practice and terminology.

Return ONLY the email body as plain text (no JSON, no markdown).
""",
    input_variables=["email_template", "incident_form_json"],
)

email_chain = email_prompt | llm | email_parser


# ------------------------------------------------------
# AI Endpoint
# ------------------------------------------------------

@app.post("/api/analyze", response_model=IncidentResponse)
async def analyze_transcript(body: TranscriptRequest):
    transcript = body.transcript

    # print(transcript)
    # return transcript[:20]

    # 1) Policy analysis
    policy_issues_data = await policy_chain.ainvoke(
        {"policies_text": POLICIES_TEXT, "transcript": transcript}
    )

    if not isinstance(policy_issues_data, list):
        policy_issues_data = []

    issues: List[PolicyIssue] = []
    for raw in policy_issues_data:
        try:
            issues.append(
                PolicyIssue(
                    policy_id=raw.get("policy_id"),
                    description=raw.get("description", ""),
                    severity=raw.get("severity", "Low"),
                    evidence=raw.get("evidence", ""),
                )
            )
        except Exception:
            # Skip malformed entries rather than breaking the whole request
            continue

    # 2) Incident form generation
    incident_data = await incident_chain.ainvoke(
        {
            "incident_template_text": INCIDENT_TEMPLATE_TEXT,
            "issues_json": policy_issues_data,
            "transcript": transcript,
        }
    )

    if not isinstance(incident_data, dict):
        incident_data = {}

    incident_form = IncidentForm(
        title=incident_data.get("title", "Incident Report"),
        incident_summary=incident_data.get("incident_summary", ""),
        policies_breached=incident_data.get("policies_breached", []),
        risk_level=incident_data.get("risk_level", "Low"),
        recommended_actions=incident_data.get("recommended_actions", []),
    )

    # 3) Email draft
    email_text = await email_chain.ainvoke(
        {
            "email_template": EMAIL_TEMPLATE,
            "incident_form_json": incident_data,
        }
    )

    return IncidentResponse(
        incident_form=incident_form,
        email_draft=email_text,
        issues=issues,
    )


# # ------------------------------------------------------
# # Existing example endpoints (unchanged)
# # ------------------------------------------------------

# @app.get("/api")
# def root():
#     return {"message": "API is running"}


# @app.get("/api/items/{item_id}")
# def read_item(item_id: int, q: Optional[str] = None):
#     return {"item_id": item_id, "q": q}


# class Item(BaseModel):
#     name: str
#     description: Optional[str] = None
#     price: float
#     tax: Optional[float] = None


# @app.post("/api/items")
# def create_item(item: Item):
#     return item


# ENGINEER_ROLES = [
#     {"title": "Frontend Developer", "mainskill": "React"},
#     {"title": "Backend Developer", "mainskill": "Node.js"},
#     {"title": "Fullstack Developer", "mainskill": "Next.js"},
#     {"title": "Machine Learning Engineer", "mainskill": "Tensorflow"},
#     {"title": "Data Scientist", "mainskill": "Apache Spark"},
#     {"title": "Software Architect", "mainskill": "System Analysis"},
# ]


# @app.get("/api/engineer-roles")
# async def read_role(title: str):
#     for role in ENGINEER_ROLES:
#         if role["title"].casefold() == title.casefold():
#             return role
#     return None
