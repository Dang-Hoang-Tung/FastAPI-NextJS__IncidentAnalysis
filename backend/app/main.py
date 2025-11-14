from pathlib import Path
from typing import Optional, List

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
    """Used internally for the LLM to detect concerns."""
    policy_id: Optional[str] = None
    description: str
    severity: str
    evidence: str


class PolicyAnalysis(BaseModel):
    issues: List[PolicyIssue] = Field(default_factory=list)


class IncidentForm(BaseModel):
    """The only schema the LLM outputs AND the API returns."""
    date_time_of_incident: str
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
    risk_assessment_details: Optional[str] = None


class IncidentResponse(BaseModel):
    incident_form: IncidentForm
    email_draft: str


# ------------------------------------------------------
# Data loading
# ------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def safe_read_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8")


POLICIES_TEXT = safe_read_text(DATA_DIR / "Policies and Procedures Document.txt")

INCIDENT_FORM_TEMPLATE = """
- date_time_of_incident (string)
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
"""

EMAIL_TEMPLATE = safe_read_text(
    DATA_DIR / "email_template.txt",
    default=(
        "Subject: Incident Report - {service_user_name}\n\n"
        "Dear {recipient_name},\n\n"
        "Please find the incident summary below:\n\n"
        "{incident_summary}\n\n"
        "Kind regards,\n{sender_name}\n"
    ),
)


# ------------------------------------------------------
# LLM Setup
# ------------------------------------------------------

primary_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    timeout=20,
)

fallback_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    timeout=40,
)

# Automatically retry with fallback if:
#  - primary times out
#  - primary returns invalid JSON
#  - primary returns malformed output
llm = primary_llm.with_fallbacks([fallback_llm])


# Structured output LLMs
policy_llm = llm.with_structured_output(PolicyAnalysis)
incident_llm = llm.with_structured_output(IncidentForm)

# Email uses plain string output
email_parser = StrOutputParser()


# ---------- Policy analysis prompt ----------

policy_prompt = PromptTemplate(
    template="""
You are an expert in social care.

POLICIES AND PROCEDURES:
{policies_text}

CONVERSATION TRANSCRIPT:
{transcript}

Identify potential policy issues.
""",
    input_variables=["policies_text", "transcript"],
)

policy_chain = policy_prompt | policy_llm


# ---------- Incident form prompt ----------

incident_prompt = PromptTemplate(
    template="""
You are completing a structured incident form.

FORM DEFINITION:
{incident_form_template}

POLICY ISSUES (JSON):
{issues_json}

TRANSCRIPT:
{transcript}

Fill in the full incident form comprehensively.
""",
    input_variables=["incident_form_template", "issues_json", "transcript"],
)

incident_chain = incident_prompt | incident_llm


# ---------- Email generation ----------

email_prompt = PromptTemplate(
    template="""
You are generating an escalation email.

EMAIL TEMPLATE:
{email_template}

INCIDENT FORM (JSON):
{incident_form_json}

POLICY ISSUES IDENTIFIED (JSON):
{issues_json}

Write a professional email draft summarizing the incident, including:
- what happened (based on the incident form)
- which policies or procedure sections may be relevant (based on the issues)
- why these are concerns (briefly)
- what actions or follow-up may be needed
""",
    input_variables=["email_template", "incident_form_json", "issues_json"],
)

email_chain = email_prompt | llm | email_parser


# ------------------------------------------------------
# API Endpoint
# ------------------------------------------------------

@app.post("/api/analyze", response_model=IncidentResponse)
async def analyze_transcript(body: TranscriptRequest):
    transcript = body.transcript

    # Step 1: Internal policy analysis (not returned to frontend)
    policy_result: PolicyAnalysis = await policy_chain.ainvoke(
        {"policies_text": POLICIES_TEXT, "transcript": transcript}
    )
    issues_json = [i.model_dump() for i in policy_result.issues]

    # Step 2: Generate structured IncidentForm
    incident_form: IncidentForm = await incident_chain.ainvoke(
        {
            "incident_form_template": INCIDENT_FORM_TEMPLATE,
            "issues_json": issues_json,
            "transcript": transcript,
        }
    )

    # Step 3: Generate email
    email_text = await email_chain.ainvoke(
        {
            "email_template": EMAIL_TEMPLATE,
            "incident_form_json": incident_form.model_dump(),
            "issues_json": issues_json,
        }
    )


    return IncidentResponse(
        incident_form=incident_form,
        email_draft=email_text,
    )
