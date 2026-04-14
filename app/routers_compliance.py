from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import schemas, models
from app.agent_graph import compliance_app
from app.get_db import get_db


router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.post("/check", response_model=schemas.ComplianceCheckResponse)
async def check_compliance(
    body: schemas.ComplianceCheckRequest,
    db: Session = Depends(get_db),
) -> schemas.ComplianceCheckResponse:
    initial_state = {
        "text": body.text,
        "department": body.department,
        "policy_type": body.policy_type,
        "top_k": body.top_k,
    }

    try:
        final_state = compliance_app.invoke(initial_state)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Compliance graph failed: {e}",
        )

    if "response" not in final_state:
        raise HTTPException(
            status_code=500,
            detail="Compliance graph returned no response",
        )

    resp = schemas.ComplianceCheckResponse.model_validate(final_state["response"])

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
    department: str | None = Query(default=None),
    risk: str | None = Query(default=None, alias="overall_risk"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[schemas.ComplianceCheckLog]:
    q = db.query(models.ComplianceCheck)

    if department:
        q = q.filter(models.ComplianceCheck.department == department)

    if risk:
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
) -> schemas.ComplianceCheckLog:
    log = db.get(models.ComplianceCheck, log_id)
    if not log:
        raise HTTPException(
            status_code=404,
            detail=f"Compliance check with id={log_id} not found.",
        )
    return log
