from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app import models, schemas
from app.ingestion import ingest_policy_document
from app.vectorstore import delete_policy_vectors


router = APIRouter(prefix="/policies", tags=["policies"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- Storage dir ----------
BASE_DIR = Path(__file__).resolve().parent.parent
POLICY_STORAGE_DIR = BASE_DIR / "storage" / "policies"
POLICY_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


# ---------- Endpoints ----------
@router.post("/", response_model=schemas.PolicyDocumentRead)
async def upload_policy(
    title: str = Form(...),
    policy_type: schemas.PolicyType = Form(...),
    department: str | None = Form(None),
    version: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a name")

    # build deterministic filename
    ext = Path(file.filename).suffix
    safe_name = title.replace(" ", "_").lower()
    dest_filename = f"{safe_name}_{policy_type.value}{ext}"
    dest_path = POLICY_STORAGE_DIR / dest_filename

    # save file to disk
    content = await file.read()
    dest_path.write_bytes(content)

    # create DB row
    doc = models.PolicyDocument(
        title=title,
        file_path=str(dest_path),
        policy_type=policy_type,  # enum
        department=department,
        version=version,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    ingest_policy_document(db, doc.id)
    
    return doc


@router.get("/", response_model=list[schemas.PolicyDocumentRead])
def list_policies(db: Session = Depends(get_db)):
    docs = (
        db.query(models.PolicyDocument)
        .order_by(models.PolicyDocument.created_at.desc())
        .all()
    )
    return docs


@router.delete("/{policy_id}", status_code=204)
def delete_policy(policy_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.PolicyDocument).filter(models.PolicyDocument.id == policy_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Policy not found")

    chunk_ids = [c.id for c in doc.chunks]
    delete_policy_vectors(chunk_ids)

    # Cascade deletes PolicyChunk rows via relationship config
    db.delete(doc)
    db.commit()

    # Remove file from disk
    file_path = Path(doc.file_path)
    if not file_path.exists():
        file_path = POLICY_STORAGE_DIR / file_path.name
    if file_path.exists():
        file_path.unlink()


@router.get("/{policy_id}/download")
def download_policy(policy_id: int, inline: bool = False, db: Session = Depends(get_db)):
    doc = db.query(models.PolicyDocument).filter(models.PolicyDocument.id == policy_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Policy not found")

    file_path = Path(doc.file_path)
    if not file_path.exists():
        # DB may store a stale absolute path (e.g. project was moved);
        # fall back to looking up the filename in the current storage dir.
        file_path = POLICY_STORAGE_DIR / file_path.name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Policy file not found on disk")

    disposition = "inline" if inline else "attachment"
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/pdf",
        content_disposition_type=disposition,
    )

