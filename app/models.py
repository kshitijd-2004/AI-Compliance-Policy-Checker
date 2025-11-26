from datetime import datetime
from typing import List, Optional

from sqlalchemy import ForeignKey, String, Text, DateTime, func, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum


# -----------------------------
# Declarative Base
# -----------------------------
class Base(DeclarativeBase):
    pass


# -----------------------------
# Policy Type Enum
# -----------------------------
class PolicyType(str, enum.Enum):
    confidentiality = "confidentiality"
    external_communication = "external_communication"
    data_privacy = "data_privacy"
    security = "security"
    hr = "hr"


# -----------------------------
# Policy Document Model
# -----------------------------
class PolicyDocument(Base):
    __tablename__ = "policy_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    policy_type: Mapped[PolicyType] = mapped_column(SAEnum(PolicyType))
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    chunks: Mapped[List["PolicyChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan"
    )


# -----------------------------
# Policy Chunk Model
# -----------------------------
class PolicyChunk(Base):
    __tablename__ = "policy_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("policy_documents.id"))
    section_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    document: Mapped["PolicyDocument"] = relationship(back_populates="chunks")


# -----------------------------
# Compliance Check Model
# -----------------------------
class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    policy_type: Mapped["PolicyType | None"] = mapped_column(
        SAEnum(PolicyType),
        nullable=True,
    )

    # model’s judgement
    overall_risk: Mapped[str] = mapped_column(String(20), nullable=False)

    # store issues as JSON blob
    issues: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # suggested rewrite
    suggested_text: Mapped[str | None] = mapped_column(Text, nullable=True)