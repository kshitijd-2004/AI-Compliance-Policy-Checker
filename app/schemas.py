from datetime import datetime
from typing import Optional, List, Any

from pydantic import BaseModel, ConfigDict, field_validator
from app.models import PolicyType


class PolicyDocumentBase(BaseModel):
    title: str
    policy_type: PolicyType
    department: Optional[str] = None
    version: Optional[str] = None


class PolicyDocumentCreate(PolicyDocumentBase):
    pass


class PolicyDocumentRead(PolicyDocumentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplianceIssue(BaseModel):
    type: str
    policy_reference: Optional[str] = None
    excerpt: Optional[str] = None
    explanation: str


class ComplianceCheckRequest(BaseModel):
    text: str
    department: Optional[str] = None
    policy_type: Optional[PolicyType] = None
    top_k: int = 5  # how many chunks to retrieve

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Text must not be empty")
        if len(v) > 8000:
            raise ValueError("Text must not exceed 8000 characters")
        return v


class ComplianceCheckResponse(BaseModel):
    overall_risk: str  # e.g. "LOW" | "MEDIUM" | "HIGH" | "NONE"
    issues: List[ComplianceIssue]
    suggested_text: Optional[str] = None

class ComplianceCheckLog(BaseModel):
    id: int
    created_at: datetime
    text: str
    department: Optional[str] = None
    policy_type: Optional[PolicyType] = None
    overall_risk: str
    issues: Optional[List[ComplianceIssue]] = None
    suggested_text: Optional[str] = None

    model_config = ConfigDict( 
        from_attributes = True   # so we can return ORM model instances
    )
           
