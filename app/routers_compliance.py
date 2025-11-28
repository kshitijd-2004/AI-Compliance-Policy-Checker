import json

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import OpenAI

from app.database import SessionLocal
from app import schemas, models
from app.agent_graph import compliance_app 
from app.vectorstore import query_policy_chunks


router = APIRouter(prefix="/compliance", tags=["compliance"])


# --- settings for OpenAI (LLM for analysis) ---
class LLMSettings(BaseSettings):
    OPENAI_API_KEY: str

    model_config = SettingsConfigDict(
        extra='ignore', 
        env_file=".env",
        )


llm_settings = LLMSettings()
llm_client = OpenAI(api_key=llm_settings.OPENAI_API_KEY)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def classify_context_with_llm(text: str) -> tuple[str | None, models.PolicyType | None]:
    """
    Use the LLM to infer department and policy_type from the user's text.
    Returns (department, policy_type_enum_or_None).
    """
    prompt = f"""
You are a classifier for an AI compliance system.

Given a piece of text, infer:
- which department it most likely belongs to (e.g. "Sales", "Support", "HR", "Legal", "Marketing")
- which policy_type applies, from this fixed list:
  ["confidentiality", "external_communication", "data_privacy", "security", "hr"]

If you are unsure about a field, set it to null.

Return ONLY a JSON object with this exact shape:

{{
  "department": "Sales" | "Support" | "HR" | "Legal" | "Marketing" | null,
  "policy_type": "confidentiality" | "external_communication" | "data_privacy" | "security" | "hr" | null
}}

Text:
\"\"\"{text}\"\"\"    
"""

    completion = llm_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You classify text into department and policy_type for compliance checks."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    content = completion.choices[0].message.content
    data = json.loads(content) if hasattr(schemas, "json") else __import__("json").loads(content)

    department = data.get("department")
    policy_type_str = data.get("policy_type")

    policy_type_enum: models.PolicyType | None = None
    if policy_type_str:
        try:
            policy_type_enum = models.PolicyType(policy_type_str)
        except ValueError:
            policy_type_enum = None

    return department, policy_type_enum


@router.post("/check", response_model=schemas.ComplianceCheckResponse)
async def check_compliance(
    body: schemas.ComplianceCheckRequest,
    db: Session = Depends(get_db),
):
    # Build initial graph state
    initial_state = {
        "text": body.text,
        "department": body.department,
        "policy_type": body.policy_type,
        "top_k": body.top_k,
    }

    try:
        # Run synchronous graph
        final_state = compliance_app.invoke(initial_state)
    except Exception as e:
        # If Pinecone/LLM explodes, catch here
        raise HTTPException(
            status_code=500,
            detail=f"Compliance graph failed: {str(e)}",
        )

    if "response" not in final_state:
        raise HTTPException(
            status_code=500,
            detail="Compliance graph returned no response",
        )

    # Turn dict back into response model
    resp = schemas.ComplianceCheckResponse.model_validate(final_state["response"])

    # ---- Log to DB ----
    db_obj = models.ComplianceCheck(
        text=body.text,
        department=body.department,
        policy_type=body.policy_type,
        overall_risk=resp.overall_risk,
        issues=[i.model_dump() for i in resp.issues] if resp.issues else [],
        suggested_text=resp.suggested_text,
    )
    db.add(db_obj)
    db.commit()

    return resp


@router.get("/logs", response_model=list[schemas.ComplianceCheckLog])
def list_compliance_logs(
    department: Optional[str] = Query(default=None),
    risk: Optional[str] = Query(default=None, alias="overall_risk"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    ):

    q = db.query(models.ComplianceCheck)

    if department: # filter bt department
        q = q.filter(models.ComplianceCheck.department == department)

    if risk: # filter by overall_risk
        q = q.filter(models.ComplianceCheck.overall_risk == risk.upper())


    logs = (
        q.order_by(models.ComplianceCheck.created_at.desc())
        .limit(limit)
        .all()
    )
    return logs

@router.get("/logs/{log_id}", response_model=schemas.ComplianceCheckLog)
def get_compliance_log(
    log_id: int,
    db: Session = Depends(get_db),
):
    """
    Fetch a single compliance check log by ID.
    """
    log = db.query(models.ComplianceCheck).get(log_id)
    if not log:
        raise HTTPException(
            status_code=404,
            detail=f"Compliance check with id={log_id} not found.",
        )
    return log



