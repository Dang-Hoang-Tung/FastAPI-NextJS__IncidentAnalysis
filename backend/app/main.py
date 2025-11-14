from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

import logging
import traceback
from datetime import datetime

# ------------------------------------------------------
# Logging
# ------------------------------------------------------

logger = logging.getLogger("incident_api")
logger.setLevel(logging.INFO)

# Console handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
)
ch.setFormatter(formatter)
logger.addHandler(ch)



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
# RAG: Build FAISS Vectorstore
# ------------------------------------------------------

splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=200)
policy_chunks = splitter.split_text(POLICIES_TEXT)

embedding = OpenAIEmbeddings()
policy_db = FAISS.from_texts(policy_chunks, embedding=embedding)


def get_relevant_policies(query: str, k: int = 4) -> str:
    """Retrieve top-k most relevant policy sections."""
    docs = policy_db.similarity_search(query, k=k)
    return "\n\n".join(doc.page_content for doc in docs)



# ------------------------------------------------------
# LLM Setup with fallback models
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

llm = primary_llm.with_fallbacks([fallback_llm])

policy_llm = llm.with_structured_output(PolicyAnalysis)
incident_llm = llm.with_structured_output(IncidentForm)

email_parser = StrOutputParser()



# ------------------------------------------------------
# Policy analysis chain
# ------------------------------------------------------

policy_prompt = PromptTemplate(
    template="""
You are an expert in social care.

RELEVANT POLICY CONTEXT (retrieved via RAG):
{policy_context}

FULL POLICIES AND PROCEDURES (may be long):
{policies_text}

CONVERSATION TRANSCRIPT:
{transcript}

Identify potential policy issues.
""",
    input_variables=["policies_text", "transcript", "policy_context"],
)

policy_chain = policy_prompt | policy_llm



# ------------------------------------------------------
# Incident form chain
# ------------------------------------------------------

incident_prompt = PromptTemplate(
    template="""
You are completing a structured incident form.

FORM DEFINITION:
{incident_form_template}

RELEVANT POLICY CONTEXT (retrieved via RAG):
{policy_context}

POLICY ISSUES (JSON):
{issues_json}

TRANSCRIPT:
{transcript}

Fill in the incident form accurately and comprehensively.
""",
    input_variables=["incident_form_template", "issues_json", "transcript", "policy_context"],
)

incident_chain = incident_prompt | incident_llm



# ------------------------------------------------------
# Email generation chain
# ------------------------------------------------------

email_prompt = PromptTemplate(
    template="""
You are generating an escalation email.

EMAIL TEMPLATE:
{email_template}

RELEVANT POLICY CONTEXT (retrieved via RAG):
{policy_context}

INCIDENT FORM (JSON):
{incident_form_json}

POLICY ISSUES IDENTIFIED (JSON):
{issues_json}

Write a clear, professional email summarizing:
- What happened
- Which policies may be involved
- Why these issues matter
- Any needed follow-up actions
""",
    input_variables=[
        "email_template",
        "incident_form_json",
        "issues_json",
        "policy_context",
    ],
)

email_chain = email_prompt | llm | email_parser



# ------------------------------------------------------
# API Endpoint
# ------------------------------------------------------
def log_exception(error: Exception, context: str = ""):
    logger.error(f"Error during {context}: {error}")
    logger.error(traceback.format_exc())


@app.post("/api/analyze", response_model=IncidentResponse)
async def analyze_transcript(body: TranscriptRequest):
    transcript = body.transcript

    logger.info("Received transcript for analysis.")
    start_time = datetime.now()

    # ---- Step 0: RAG retrieval ----
    try:
        policy_context = get_relevant_policies(transcript)
        logger.info("Retrieved RAG policy context.")
    except Exception as e:
        log_exception(e, "RAG retrieval")
        raise HTTPException(status_code=500, detail="Failed to retrieve policy context.")

    # ---- Step 1: Policy analysis ----
    try:
        policy_result: PolicyAnalysis = await policy_chain.ainvoke(
            {
                "policies_text": POLICIES_TEXT,
                "transcript": transcript,
                "policy_context": policy_context,
            }
        )
        issues_json = [i.model_dump() for i in policy_result.issues]
        logger.info(f"Policy analysis complete. Found {len(issues_json)} issues.")
    except Exception as e:
        log_exception(e, "policy analysis")
        raise HTTPException(status_code=500, detail="LLM failed during policy analysis.")

    # ---- Step 2: Incident form generation ----
    try:
        incident_form: IncidentForm = await incident_chain.ainvoke(
            {
                "incident_form_template": INCIDENT_FORM_TEMPLATE,
                "issues_json": issues_json,
                "transcript": transcript,
                "policy_context": policy_context,
            }
        )
        logger.info("Incident form generation completed.")
    except Exception as e:
        log_exception(e, "incident form generation")
        raise HTTPException(status_code=500, detail="LLM failed during incident form generation.")

    # ---- Step 3: Email generation ----
    try:
        email_text = await email_chain.ainvoke(
            {
                "email_template": EMAIL_TEMPLATE,
                "incident_form_json": incident_form.model_dump(),
                "issues_json": issues_json,
                "policy_context": policy_context,
            }
        )
        logger.info("Email draft generation completed.")
    except Exception as e:
        log_exception(e, "email generation")
        raise HTTPException(status_code=500, detail="LLM failed during email generation.")

    # ---- Success logging ----
    duration = (datetime.now() - start_time).total_seconds()
    logger.info(f"Request completed successfully in {duration:.2f}s")

    return IncidentResponse(
        incident_form=incident_form,
        email_draft=email_text,
    )
