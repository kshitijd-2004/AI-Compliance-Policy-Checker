from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app import models, schemas

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
@router.post("/upload", response_model=schemas.PolicyDocumentRead)
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

    return doc


@router.get("/", response_model=list[schemas.PolicyDocumentRead])
def list_policies(db: Session = Depends(get_db)):
    docs = (
        db.query(models.PolicyDocument)
        .order_by(models.PolicyDocument.created_at.desc())
        .all()
    )
    return docs
