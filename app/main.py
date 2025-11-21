from fastapi import FastAPI

from .models import Base
from .database import engine
from app.routers_policies import router as policies_router
from app.routers_compliance import router as compliance_router


Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Compliance Policy Checker", description="A tool to check AI models for compliance with various policies.")

app.include_router(policies_router)
app.include_router(compliance_router)


@app.get("/health")
def get_health():
    return {"status": "AI Compliance Policy Checker is running."}
