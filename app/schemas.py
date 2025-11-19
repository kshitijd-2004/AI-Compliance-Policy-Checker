from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict
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
