from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .models import Base
from .database import engine
from app.routers_policies import router as policies_router
from app.routers_compliance import router as compliance_router
from app.routers_health import router as health_router


Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Compliance Policy Checker", description="A tool to check AI models for compliance with various policies.")

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


@app.get("/health")
def get_health():
    return {"status": "AI Compliance Policy Checker is running."}
