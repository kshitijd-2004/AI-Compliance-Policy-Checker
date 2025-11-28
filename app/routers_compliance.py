import json

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import OpenAI

from app.database import SessionLocal
from app import schemas, models
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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



@router.post("/check", response_model=schemas.ComplianceCheckResponse)
async def check_compliance(
    body: schemas.ComplianceCheckRequest,
    db: Session = Depends(get_db),
):
    # 0) Check if there's at least one policy document in the DB
    policy_count = db.scalar(select(func.count(models.PolicyDocument.id)))
    if not policy_count:
        raise HTTPException(
            status_code=400,
            detail="No policy documents found. Please upload at least one policy before running compliance checks.",
        )
    
    # 1) Decide effective department / policy_type (user override > model)
    inferred_department = None
    inferred_policy_type: models.PolicyType | None = None

    if not body.department or not body.policy_type:
        inferred_department, inferred_policy_type = classify_context_with_llm(body.text)

    effective_department = body.department or inferred_department
    effective_policy_type = body.policy_type or inferred_policy_type

    # 2) Build Pinecone filters from effective values
    filters: dict[str, str] = {}
    if effective_department:
        filters["department"] = effective_department
    if effective_policy_type:
        filters["policy_type"] = effective_policy_type.value

    # 3) Query Pinecone
    try:
        matches = query_policy_chunks(
            query=body.text,
            top_k=body.top_k,
            filters=filters if filters else None,
        )

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail="Vector retrieval service (Pinecone) is unavailable or failed.",
        )


    # 4) If no matches, still log a "NONE" risk check
    if not matches:
        resp = schemas.ComplianceCheckResponse(
            overall_risk="NONE",
            issues=[],
            suggested_text=None,
        )

        db_obj = models.ComplianceCheck(
            text=body.text,
            department=effective_department,
            policy_type=effective_policy_type,
            overall_risk=resp.overall_risk,
            issues=[],
            suggested_text=None,
        )
        db.add(db_obj)
        db.commit()

        return resp

    # 5) Build context from matches
    context_snippets = []
    for m in matches:
        meta = m.metadata or {}
        snippet = f"[doc_id={meta.get('document_id')}, chunk_id={meta.get('chunk_id')}] {meta.get('text', '')}"
        context_snippets.append(snippet)

    context_text = "\n\n".join(context_snippets)

    # 6) Ask LLM to analyze compliance
    prompt = f"""
You are a compliance assistant. Given:

1) The user's text (draft message)
2) Relevant policy excerpts

Decide:
- Overall risk: one of ["NONE", "LOW", "MEDIUM", "HIGH"]
- List of issues (if any) with:
  - type (e.g. "Confidentiality", "External Communication", "Data Privacy")
  - policy_reference (if you can infer it from the excerpt, otherwise null)
  - excerpt (the risky part of the user text)
  - explanation (why it is a problem)

Then propose a fully rewritten version of the text that is compliant.

Return ONLY a JSON object with this structure:

{{
  "overall_risk": "LOW",
  "issues": [
    {{
      "type": "Confidentiality",
      "policy_reference": "Security Policy §3.2",
      "excerpt": "some text from the user message",
      "explanation": "short explanation"
    }}
  ],
  "suggested_text": "rewritten compliant text"
}}

User text:
\"\"\"{body.text}\"\"\"


Policy context:
\"\"\"{context_text}\"\"\"    
"""
    try:
        completion = llm_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a strict compliance reviewer."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="LLM service (OpenAI) failed while performing compliance analysis.",
        )

    raw_json = completion.choices[0].message.content

    try:
        resp = schemas.ComplianceCheckResponse.model_validate_json(raw_json)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Model returned invalid JSON for compliance result",
        )

    # 7) Log the compliance check with effective filters
    db_obj = models.ComplianceCheck(
        text=body.text,
        department=effective_department,
        policy_type=effective_policy_type,
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



