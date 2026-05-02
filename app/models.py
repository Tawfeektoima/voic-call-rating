"""
SQLAlchemy ORM models for the Call Rating Platform.

Tables
------
- Employee   : agents whose calls are being evaluated
- Campaign   : evaluation campaigns with specific scoring prompts
- Call       : individual call records linking an employee, campaign, audio, and results
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime,
    ForeignKey, Enum as SAEnum, JSON,
)
from sqlalchemy.orm import relationship

from app.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CallStatus(str, enum.Enum):
    """Lifecycle status of a call record."""
    PENDING      = "pending"
    PROCESSING   = "processing"
    TRANSCRIBED  = "transcribed"
    EVALUATED    = "evaluated"
    FAILED       = "failed"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Employee(Base):
    __tablename__ = "employees"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(255), nullable=False)
    department = Column(String(255), nullable=True)
    employee_code = Column(String(50), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    calls = relationship("Call", back_populates="employee", lazy="dynamic")

    def __repr__(self):
        return f"<Employee id={self.id} name={self.name!r}>"


class Campaign(Base):
    __tablename__ = "campaigns"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(255), nullable=False, unique=True)
    description      = Column(Text, nullable=True)
    evaluation_prompt = Column(Text, nullable=False)
    created_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    calls = relationship("Call", back_populates="campaign", lazy="dynamic")

    def __repr__(self):
        return f"<Campaign id={self.id} name={self.name!r}>"


class Call(Base):
    __tablename__ = "calls"

    id               = Column(Integer, primary_key=True, index=True)
    employee_id      = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    campaign_id      = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    audio_file_path  = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=True)
    audio_duration   = Column(Float, nullable=True) # in seconds

    # Processing state
    status           = Column(SAEnum(CallStatus), default=CallStatus.PENDING, nullable=False, index=True)
    error_message    = Column(Text, nullable=True)

    # Results
    transcript       = Column(Text, nullable=True)
    reasoning        = Column(Text, nullable=True)
    evaluation_score = Column(Float, nullable=True)
    strengths        = Column(JSON, nullable=True)          # list of strength strings
    weaknesses       = Column(JSON, nullable=True)          # list of weakness JSON objects

    # Supervisor Review
    overridden_score = Column(Float, nullable=True)
    reviewer_notes   = Column(Text, nullable=True)
    reviewed_at      = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processed_at     = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    employee = relationship("Employee", back_populates="calls")
    campaign = relationship("Campaign", back_populates="calls")

    def __repr__(self):
        return f"<Call id={self.id} status={self.status.value}>"


class SystemLog(Base):
    """Dedicated table for logging system-level errors like CUDA OOM."""
    __tablename__ = "system_logs"

    id            = Column(Integer, primary_key=True, index=True)
    call_id       = Column(Integer, nullable=True)
    error_type    = Column(String(50), nullable=False)
    error_message = Column(Text, nullable=False)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<SystemLog id={self.id} type={self.error_type}>"
