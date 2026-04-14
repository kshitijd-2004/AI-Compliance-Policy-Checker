from __future__ import annotations

from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict
from pinecone import Pinecone
from openai import OpenAI

from app import models


class VectorSettings(BaseSettings):
    OPENAI_API_KEY: str
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str

    model_config = SettingsConfigDict(extra="ignore", env_file=".env")


settings = VectorSettings()

pc = Pinecone(api_key=settings.PINECONE_API_KEY)
index = pc.Index(settings.PINECONE_INDEX_NAME)

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Call OpenAI embeddings on a batch of texts."""
    resp = client.embeddings.create(
        input=texts,
        model="text-embedding-3-small",
    )
    return [d.embedding for d in resp.data]


def index_policy_chunks(chunks: list[models.PolicyChunk]) -> None:
    """Upsert a batch of PolicyChunk rows into Pinecone."""
    if not chunks:
        return

    documents_by_id: dict[int, models.PolicyDocument] = {}
    for chunk in chunks:
        if chunk.document_id not in documents_by_id:
            documents_by_id[chunk.document_id] = chunk.document

    texts = [c.text for c in chunks]
    embeddings = embed_texts(texts)

    vectors: list[dict[str, Any]] = []
    for chunk, emb in zip(chunks, embeddings):
        doc = documents_by_id.get(chunk.document_id)
        vectors.append(
            {
                "id": f"chunk-{chunk.id}",
                "values": emb,
                "metadata": {
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.id,
                    "policy_type": doc.policy_type.value if doc and doc.policy_type else None,
                    "department": doc.department if doc else None,
                    "text": chunk.text,
                },
            }
        )

    index.upsert(vectors=vectors)


def delete_policy_vectors(chunk_ids: list[int]) -> None:
    """Delete vectors from Pinecone for the given PolicyChunk row IDs."""
    if not chunk_ids:
        return
    vector_ids = [f"chunk-{cid}" for cid in chunk_ids]
    index.delete(ids=vector_ids)


def query_policy_chunks(
    query: str,
    top_k: int = 8,
    filters: dict[str, Any] | None = None,
) -> list[Any]:
    """Query Pinecone for relevant policy chunks given a query string."""
    query_emb = embed_texts([query])[0]

    resp = index.query(
        vector=query_emb,
        top_k=top_k,
        include_metadata=True,
        filter=filters or {},
    )

    return resp.matches
