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
    ForeignKey, Enum as SAEnum, JSON, Boolean,
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


class CampaignType(str, enum.Enum):
    """Business category of the campaign."""
    SALES            = "sales"
    CUSTOMER_SERVICE = "customer_service"
    TECHNICAL       = "technical"
    COLLECTIONS      = "collections"


class CampaignStatus(str, enum.Enum):
    """Operational status of the campaign."""
    ACTIVE    = "active"
    PAUSED    = "paused"
    COMPLETED = "completed"


class LeadStatus(str, enum.Enum):
    """Lead quality status from call analysis."""
    HOT  = "hot"
    WARM = "warm"
    COLD = "cold"


class UserRole(str, enum.Enum):
    """Access levels for the platform."""
    AGENT   = "AGENT"
    QA      = "QA"
    ADMIN   = "ADMIN"
    HR_MANAGER = "HR_MANAGER"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class EmployeeTier(str, enum.Enum):
    """Performance tier of the employee."""
    BRONZE   = "bronze"
    SILVER   = "silver"
    GOLD     = "gold"
    PLATINUM = "platinum"


class Employee(Base):
    __tablename__ = "employees"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(255), nullable=False)
    email      = Column(String(255), unique=True, index=True, nullable=False)
    department = Column(String(255), nullable=True)
    employee_code = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role       = Column(SAEnum(UserRole), default=UserRole.AGENT, nullable=False)
    avatar     = Column(String(255), nullable=True) # URL or initials
    tier       = Column(SAEnum(EmployeeTier), default=EmployeeTier.BRONZE, nullable=False)
    skills     = Column(JSON, nullable=True) # e.g. {"empathy": 80, "resolution": 75}
    phone_number = Column(String(50), nullable=True)
    emotion_history = Column(JSON, nullable=True) # e.g. [65, 70, 72, 68]
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    calls = relationship("Call", back_populates="employee", lazy="dynamic")
    mastery_stats = relationship("AgentMasteryStats", back_populates="employee", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Employee id={self.id} name={self.name!r}>"


class Campaign(Base):
    __tablename__ = "campaigns"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(255), nullable=False, unique=True)
    description      = Column(Text, nullable=True)
    type             = Column(SAEnum(CampaignType), default=CampaignType.CUSTOMER_SERVICE, nullable=False)
    status           = Column(SAEnum(CampaignStatus), default=CampaignStatus.ACTIVE, nullable=False)
    kpis             = Column(JSON, nullable=True)  # List of strings or key-value pairs
    color            = Column(String(7), default="#6366f1", nullable=False) # Default indigo
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
    transcript       = Column(JSON, nullable=True)
    reasoning        = Column(Text, nullable=True)
    evaluation_score = Column(Float, nullable=True)
    strengths        = Column(JSON, nullable=True)          # list of strength strings
    weaknesses       = Column(JSON, nullable=True)          # list of weakness JSON objects

    # Supervisor Review
    overridden_score = Column(Float, nullable=True)
    reviewer_notes   = Column(Text, nullable=True)
    reviewed_at      = Column(DateTime(timezone=True), nullable=True)

    # Deep Analysis Results
    agent_talk_time     = Column(Float, nullable=True)
    customer_talk_time  = Column(Float, nullable=True)
    tags                = Column(JSON, nullable=True)     # e.g. ["Objection Handled", "Positive Close"]
    lead_status         = Column(SAEnum(LeadStatus), nullable=True)
    is_golden_moment    = Column(Boolean, default=False, nullable=False)
    call_summary        = Column(Text, nullable=True)
    emotion_timeline    = Column(JSON, nullable=True)     # e.g. [{"time": 5, "emotion": "positive"}]
    speaker_map         = Column(JSON, nullable=True)     # e.g. {"SPEAKER_00": "Agent", "SPEAKER_01": "Customer"}

    # Timestamps
    created_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processed_at     = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    employee = relationship("Employee", back_populates="calls")
    campaign = relationship("Campaign", back_populates="calls")

    def __repr__(self):
        return f"<Call id={self.id} status={self.status.value}>"


class AgentMasteryStats(Base):
    """Aggregated performance metrics for an agent across all calls."""
    __tablename__ = "agent_mastery_stats"

    id               = Column(Integer, primary_key=True, index=True)
    employee_id      = Column(Integer, ForeignKey("employees.id"), unique=True, nullable=False, index=True)
    
    rapport_building = Column(Float, default=100.0)
    emotional_sync   = Column(Float, default=100.0)
    ownership_trust  = Column(Float, default=100.0)
    process_clarity  = Column(Float, default=100.0)
    
    updated_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    employee = relationship("Employee", back_populates="mastery_stats")

    def __repr__(self):
        return f"<AgentMasteryStats employee_id={self.employee_id}>"


class SystemLog(Base):
    """Dedicated table for logging system-level errors like CUDA OOM."""
    __tablename__ = "system_logs"

    id            = Column(Integer, primary_key=True, index=True)
    call_id       = Column(Integer, nullable=True)
    error_type    = Column(String(50), nullable=False)
    error_message = Column(Text, nullable=False)
    severity      = Column(String(20), default="warning") # critical, warning, info
    resolved      = Column(Boolean, default=False)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<SystemLog id={self.id} type={self.error_type}>"
