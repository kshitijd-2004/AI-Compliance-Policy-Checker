from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict
from pinecone import Pinecone
from openai import OpenAI

from app import models

class VectorSettings(BaseSettings):
    OPENAI_API_KEY: str
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str

    model_config = SettingsConfigDict(
        extra='ignore', 
        env_file=".env",
        )

settings = VectorSettings()

pc = Pinecone(api_key=settings.PINECONE_API_KEY)
index = pc.Index(settings.PINECONE_INDEX_NAME)

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Call OpenAI embeddings on a batch of texts."""
    resp = client.embeddings.create(
        input=texts,
        model="text-embedding-3-small",
    )
    return [d.embedding for d in resp.data]


def index_policy_chunks(chunks: List[models.PolicyChunk]) -> None:
    """Upsert a batch of PolicyChunk rows into Pinecone."""
    if not chunks:
        return

    texts = [c.text for c in chunks]
    embeddings = embed_texts(texts)

    vectors = []
    for chunk, emb in zip(chunks, embeddings):
        vectors.append(
            {
                "id": f"chunk-{chunk.id}",
                "values": emb,
                "metadata": {
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.id,
                },
            }
        )

    # upsert to Pinecone
    index.upsert(vectors=vectors)
