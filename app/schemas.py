from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models import PolicyType


class PolicyDocumentBase(BaseModel):
    title: str
    policy_type: PolicyType
    department: str | None = None
    version: str | None = None


class PolicyDocumentCreate(PolicyDocumentBase):
    pass


class PolicyDocumentRead(PolicyDocumentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplianceIssue(BaseModel):
    type: str
    policy_reference: str | None = None
    excerpt: str | None = None
    explanation: str


class ComplianceCheckRequest(BaseModel):
    text: str
    department: str | None = None
    policy_type: PolicyType | None = None
    top_k: int = 5

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Text must not be empty")
        if len(v) > 8000:
            raise ValueError("Text must not exceed 8000 characters")
        return v


class ComplianceCheckResponse(BaseModel):
    overall_risk: str
    issues: list[ComplianceIssue]
    suggested_text: str | None = None


class ComplianceCheckLog(BaseModel):
    id: int
    created_at: datetime
    text: str
    department: str | None = None
    policy_type: PolicyType | None = None
    overall_risk: str
    issues: list[ComplianceIssue] | None = None
    suggested_text: str | None = None

    model_config = ConfigDict(from_attributes=True)
