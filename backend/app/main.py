from pathlib import Path
from typing import Optional, List, Annotated

from fastapi import FastAPI
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser


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
    """Single potential policy issue found in the transcript."""
    policy_id: Optional[str] = Field(
        default=None,
        description="Most relevant policy section name or heading, or null if unclear."
    )
    description: str = Field(
        description="Concise description of the concern / incident aspect."
    )
    severity: str = Field(
        description='Overall severity, one of ["Low", "Medium", "High", "Critical"].'
    )
    evidence: str = Field(
        description="Short quotes or clear references from the transcript."
    )


class PolicyAnalysis(BaseModel):
    """Structured output for the policy analysis step."""
    issues: List[PolicyIssue] = Field(
        default_factory=list,
        description="List of policy issues identified in the transcript."
    )


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


class IncidentFormLLM(IncidentForm):
    """What the LLM returns when generating the incident form."""
    policies_breached: List[str] = Field(
        default_factory=list,
        description="List of relevant policy section names or IDs."
    )
    risk_level: str = Field(
        description='Overall risk level, one of ["Low", "Medium", "High", "Critical"].'
    )


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

In addition, derive:
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
# LangChain setup
# ------------------------------------------------------

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
)

# Structured LLMs
policy_llm = llm.with_structured_output(PolicyAnalysis)
incident_llm = llm.with_structured_output(IncidentFormLLM)

# We still only need a string parser for the email
email_parser = StrOutputParser()


# ---------- Policy analysis chain (structured) ----------

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

Identify potential policy issues or concerns.

For each issue, you must populate:
- policy_id: the most relevant section name or heading from the policy document
             (e.g. "Section 3: Mobility & Moving", "Section 5: Mental Health and Emotional Well-being"),
             or null if not clear.
- description: a concise description of the concern.
- severity: one of ["Low", "Medium", "High", "Critical"] based on risk and recurrence.
- evidence: short quotes or clear references from the transcript.

Return data that fits the `PolicyAnalysis` schema (a list of `PolicyIssue` items).
""",
    input_variables=["policies_text", "transcript"],
)

policy_chain = policy_prompt | policy_llm


# ---------- Incident form chain (structured) ----------

incident_prompt = PromptTemplate(
    template="""
You are completing an incident report form for a social care provider.

Here is the organisation's incident form definition:
{incident_template_text}

You are also given:
- A list of policy issues in JSON (already analysed).
- The original transcript.

POLICY ISSUES (JSON):
{issues_json}

TRANSCRIPT:
{transcript}

Using all the above, fill out the incident report and derive risk information.
You MUST return data that fits the `IncidentFormLLM` schema, which includes:

- All form fields (date_time_of_incident, service_user_name, etc.)
- policies_breached: list of policy_id strings or section names.
- risk_level: one of ["Low", "Medium", "High", "Critical"].
""",
    input_variables=["incident_template_text", "issues_json", "transcript"],
)

incident_chain = incident_prompt | incident_llm


# ---------- Email drafting chain (string output) ----------

email_prompt = PromptTemplate(
    template="""
You are drafting a professional escalation email based on an incident form
and an email template.

EMAIL TEMPLATE:
{email_template}

INCIDENT FORM (JSON-like data):
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

    # 1) Policy analysis -> PolicyAnalysis (structured)
    policy_result: PolicyAnalysis = await policy_chain.ainvoke(
        {"policies_text": POLICIES_TEXT, "transcript": transcript}
    )
    issues: List[PolicyIssue] = policy_result.issues or []

    # For the incident chain, pass plain JSON-ish data, not Pydantic objects
    issues_json = [issue.model_dump() for issue in issues]

    # 2) Incident form generation -> IncidentFormLLM (structured)
    incident_result: IncidentFormLLM = await incident_chain.ainvoke(
        {
            "incident_template_text": INCIDENT_TEMPLATE_TEXT,
            "issues_json": issues_json,
            "transcript": transcript,
        }
    )

    # Split the structured result into:
    # - form fields
    # - policies_breached + risk_level
    incident_form = IncidentForm(
        date_time_of_incident=incident_result.date_time_of_incident,
        service_user_name=incident_result.service_user_name,
        location_of_incident=incident_result.location_of_incident,
        type_of_incident=incident_result.type_of_incident,
        description_of_incident=incident_result.description_of_incident,
        immediate_actions_taken=incident_result.immediate_actions_taken,
        was_first_aid_administered=incident_result.was_first_aid_administered,
        were_emergency_services_contacted=incident_result.were_emergency_services_contacted,
        who_was_notified=incident_result.who_was_notified,
        witnesses=incident_result.witnesses,
        agreed_next_steps=incident_result.agreed_next_steps,
        risk_assessment_needed=incident_result.risk_assessment_needed,
        risk_assessment_details=incident_result.risk_assessment_details,
    )

    policies_breached = incident_result.policies_breached or []
    risk_level = incident_result.risk_level or "Low"

    # 3) Email draft -> string
    email_text = await email_chain.ainvoke(
        {
            "email_template": EMAIL_TEMPLATE,
            "incident_form_json": incident_result.model_dump(),
        }
    )

    return IncidentResponse(
        incident_form=incident_form,
        email_draft=email_text,
        issues=issues,
        policies_breached=policies_breached,
        risk_level=risk_level,
    )
