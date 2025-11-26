from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from openai import OpenAI

from app.database import SessionLocal
from app import schemas
from app.vectorstore import query_policy_chunks
from pydantic_settings import BaseSettings, SettingsConfigDict
from app import models

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


@router.post("/check", response_model=schemas.ComplianceCheckResponse)
async def check_compliance(
    body: schemas.ComplianceCheckRequest,
    db: Session = Depends(get_db),
):
    # Build Pinecone filters if department / policy_type are provided
    filters = {}
    if body.department:
        filters["department"] = body.department
    if body.policy_type:
        filters["policy_type"] = body.policy_type.value


    matches = query_policy_chunks(
        query=body.text,
        top_k=body.top_k,
        filters=filters,
    )

    if not matches:
        # No relevant chunks found; return "NONE" risk with empty issues
        return schemas.ComplianceCheckResponse(
            overall_risk="NONE",
            issues=[],
            suggested_text=None,
        )

        # log no matches case too
        db_obj = models.ComplianceCheck(
            text=body.text,
            department=body.department,
            policy_type=body.policy_type,
            overall_risk=resp.overall_risk,
            issues=[],
            suggested_text=None,
        )
        db.add(db_obj)
        db.commit()
        return resp

    # Build a context string from retrieved chunks
    context_snippets = []
    for m in matches:
        meta = m.metadata or {}
        snippet = f"[doc_id={meta.get('document_id')}, chunk_id={meta.get('chunk_id')}] {meta.get('text', '')}"
        context_snippets.append(snippet)

    context_text = "\n\n".join(context_snippets)

    # Call LLM to do compliance analysis
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

    completion = llm_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a strict compliance reviewer."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    raw_json = completion.choices[0].message.content

    # Let Pydantic validate/parse it into our schema
    try:
        # mypy-unsafe but fine here: parse_raw is on BaseModel
        resp = schemas.ComplianceCheckResponse.model_validate_json(raw_json)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Model returned invalid JSON for compliance result",
        )
    
    # Log the compliance check in the database
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
def list_compliance_logs(db: Session = Depends(get_db)):
    logs = (
        db.query(models.ComplianceCheck)
        .order_by(models.ComplianceCheck.created_at.desc())
        .limit(100)
        .all()
    )
    return logs


