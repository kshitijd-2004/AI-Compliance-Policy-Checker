from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import Base
from app.database import engine
from app.routers_policies import router as policies_router
from app.routers_compliance import router as compliance_router
from app.routers_health import router as health_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Compliance Policy Checker",
    description="LLM-powered compliance evaluation using RAG and structured AI outputs.",
)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(policies_router)
app.include_router(compliance_router)
app.include_router(health_router)
