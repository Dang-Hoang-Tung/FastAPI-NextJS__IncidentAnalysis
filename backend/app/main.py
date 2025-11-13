from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI
from pydantic import BaseModel

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
    # Matches the Incident Report Form table
    date_time_of_incident: str               # ISO datetime string or human-readable
    service_user_name: str
    location_of_incident: str
    type_of_incident: str
    description_of_incident: str
    immediate_actions_taken: str
    was_first_aid_administered: bool
    were_emergency_services_contacted: bool
    who_was_notified: str
    witnesses: str
    agreed_next_steps: str
    risk_assessment_needed: bool
    risk_assessment_details: Optional[str] = None  # "If Yes, Which Risk Assessment"


class IncidentResponse(BaseModel):
    incident_form: IncidentForm
    email_draft: str
    issues: List[PolicyIssue]
    # derived, not on the physical form but useful for UI/email
    policies_breached: List[str]
    risk_level: str


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

# 2) Incident report form “template” – now fixed to match your table
INCIDENT_TEMPLATE_TEXT = """
Incident Report Form - Fields and Types:

- date_time_of_incident (DateTime): Date and time of the incident.
- service_user_name (Text): Name of the service user.
- location_of_incident (Text): Where the incident took place.
- type_of_incident (Text): Brief label/category for the incident.
- description_of_incident (Text): Full description of what happened.
- immediate_actions_taken (Text): Actions taken immediately after the incident.
- was_first_aid_administered (Boolean): true/false.
- were_emergency_services_contacted (Boolean): true/false.
- who_was_notified (Text): People/services who were informed.
- witnesses (Text): Names/roles of any witnesses.
- agreed_next_steps (Text): Agreed follow-up actions.
- risk_assessment_needed (Boolean): true/false.
- risk_assessment_details (Text): If yes, which risk assessment / details.

In addition, include:
- policies_breached: list of relevant policy section names or IDs.
- risk_level: overall risk ["Low", "Medium", "High", "Critical"].
"""

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

Here is the organisation's incident form definition:
{incident_template_text}

You are also given:
- A list of policy issues in JSON.
- The original transcript.

POLICY ISSUES (JSON):
{issues_json}

TRANSCRIPT:
{transcript}

Using all the above, generate a single JSON object with the following keys:

{format_instructions}

The JSON object MUST contain at least:
- date_time_of_incident (string, use ISO 8601 if possible, otherwise a clear human-readable datetime).
- service_user_name (string)
- location_of_incident (string)
- type_of_incident (string)
- description_of_incident (string)
- immediate_actions_taken (string)
- was_first_aid_administered (boolean)
- were_emergency_services_contacted (boolean)
- who_was_notified (string)
- witnesses (string)
- agreed_next_steps (string)
- risk_assessment_needed (boolean)
- risk_assessment_details (string or null)

And also:
- policies_breached (list of policy_id strings or section names).
- risk_level (one of ["Low", "Medium", "High", "Critical"]).
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
            continue  # skip malformed entries

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
        date_time_of_incident=incident_data.get("date_time_of_incident", ""),
        service_user_name=incident_data.get("service_user_name", ""),
        location_of_incident=incident_data.get("location_of_incident", ""),
        type_of_incident=incident_data.get("type_of_incident", ""),
        description_of_incident=incident_data.get("description_of_incident", ""),
        immediate_actions_taken=incident_data.get("immediate_actions_taken", ""),
        was_first_aid_administered=incident_data.get(
            "was_first_aid_administered", False
        ),
        were_emergency_services_contacted=incident_data.get(
            "were_emergency_services_contacted", False
        ),
        who_was_notified=incident_data.get("who_was_notified", ""),
        witnesses=incident_data.get("witnesses", ""),
        agreed_next_steps=incident_data.get("agreed_next_steps", ""),
        risk_assessment_needed=incident_data.get("risk_assessment_needed", False),
        risk_assessment_details=incident_data.get("risk_assessment_details"),
    )

    policies_breached = incident_data.get("policies_breached", []) or []
    risk_level = incident_data.get("risk_level", "Low")

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
        policies_breached=policies_breached,
        risk_level=risk_level,
    )
