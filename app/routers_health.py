from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database import SessionLocal
from app.vectorstore import index

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
def health_check() -> dict[str, object]:
    db_ok = False
    pinecone_ok = False

    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            db_ok = True
        finally:
            db.close()
    except Exception:
        db_ok = False

    try:
        index.describe_index_stats()
        pinecone_ok = True
    except Exception:
        pinecone_ok = False

    status = "ok" if db_ok and pinecone_ok else "degraded"

    if not db_ok or not pinecone_ok:
        raise HTTPException(
            status_code=503,
            detail={
                "status": status,
                "db_ok": db_ok,
                "pinecone_ok": pinecone_ok,
            },
        )

    return {
        "status": status,
        "db_ok": db_ok,
        "pinecone_ok": pinecone_ok,
    }
