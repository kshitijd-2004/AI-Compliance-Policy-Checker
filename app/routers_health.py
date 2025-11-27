from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.vectorstore import index

router = APIRouter(prefix="/health", tags=["health"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def health_check():
    db_ok = False
    pinecone_ok = False

    # Check DB
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    # Check Pinecone
    try:
        # cheap-ish call to verify connectivity
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
