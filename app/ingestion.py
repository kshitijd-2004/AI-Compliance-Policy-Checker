from typing import List
from app import models
import fitz
from sqlalchemy.orm import Session
from app.vectorstore import index_policy_chunks


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file using PyMuPDF (fitz)"""
    doc = fitz.open(file_path)
    texts: List[str] = []
    for page in doc:
        texts.append(page.get_text())
    return "\n".join(texts)

def split_text_into_chunks(text: str, chunk_size: int = 2000, overlap: int = 200) -> list[str]:
    """Split text into chunks of a specified size"""
    text = text.strip()
    if not text:
            return []

    n = len(text)

    # If text is shorter than one chunk, just return it as a single chunk
    if n <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < n:
        end = min(n, start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end == n:
            # we've reached the end, stop
            break

        next_start = end - overlap
        # safety: ensure progress
        if next_start <= start:
            next_start = end  # no overlap if it would go backwards / stay same

        start = next_start

    return chunks
def ingest_policy_document(db: Session, document_id: int) -> None:
    """Extract text from a PDF, split into chunks, and save to the database"""
    doc = db.get(models.PolicyDocument, document_id)

    if not doc:
        return
    
    text = extract_text_from_pdf(doc.file_path)
    chunks = split_text_into_chunks(text)
    
    for chunk in chunks:
        policy_chunk = models.PolicyChunk(
            document_id=document_id,
            text=chunk
        )
        db.add(policy_chunk)

    db.commit()

    # store doc chunks in Pinecone
    db.refresh(doc)
    doc_chunks = (
        db.query(models.PolicyChunk)
        .filter(models.PolicyChunk.document_id == document_id)
        .all()
    )
    index_policy_chunks(doc_chunks)


