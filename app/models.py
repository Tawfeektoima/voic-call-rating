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
    ForeignKey, Enum as SAEnum, JSON, Boolean, Index,
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
    agent_tenure_days = Column(Integer, nullable=True) # (Task 65)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    calls = relationship("Call", back_populates="employee", lazy="dynamic")
    mastery_stats = relationship("AgentMasteryStats", back_populates="employee", uselist=False, cascade="all, delete-orphan")
    coaching_sessions = relationship("CoachingSession", back_populates="employee", cascade="all, delete-orphan")

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
    audio_file_path  = Column(String(500), nullable=True) # Nullable for live sessions
    original_filename = Column(String(255), nullable=True)
    audio_duration   = Column(Float, nullable=True) # in seconds
    source           = Column(String(50), default="uploaded", nullable=False) # Improved (I-03)

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

    # Intelligence Hub Additions (Task 65)
    call_datetime       = Column(DateTime(timezone=True), nullable=True)
    call_hour           = Column(Integer, nullable=True)
    call_day_of_week    = Column(String(20), nullable=True)
    calls_before_this   = Column(Integer, nullable=True)
    filler_words_count  = Column(Integer, default=0)
    interruptions_count = Column(Integer, default=0)
    avg_response_time_sec = Column(Float, nullable=True)

    # Compliance Flags (Task 66)
    opening_ok          = Column(Boolean, default=False)
    closing_ok          = Column(Boolean, default=False)
    dob_verified        = Column(Boolean, default=False)
    de_escalation_success = Column(Boolean, default=False)
    sales_eval_data     = Column(JSON, nullable=True)

    # Timestamps
    created_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processed_at     = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    employee = relationship("Employee", back_populates="calls")
    campaign = relationship("Campaign", back_populates="calls")
    outcome  = relationship("CallOutcome", back_populates="call", uselist=False, cascade="all, delete-orphan")
    qa_pairs = relationship("CallQAPair", back_populates="call", cascade="all, delete-orphan")
    annotations = relationship("CallAnnotation", back_populates="call", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Call id={self.id} status={self.status.value}>"


class CallOutcome(Base):
    """Business intelligence outcomes extracted from a call evaluation."""
    __tablename__ = "call_outcomes"

    id                    = Column(Integer, primary_key=True, index=True)
    call_id               = Column(Integer, ForeignKey("calls.id"), unique=True, nullable=False, index=True)

    # Common Outcome Fields
    campaign_type         = Column(String(50), nullable=False)
    primary_outcome       = Column(String(255), nullable=True)
    outcome_value         = Column(Float, nullable=True)
    follow_up_required    = Column(Boolean, default=False, nullable=False)
    follow_up_date        = Column(DateTime(timezone=True), nullable=True)

    # Programmatic Talk-Time KPIs
    agent_talk_time       = Column(Float, nullable=True)
    customer_talk_time    = Column(Float, nullable=True)
    talk_ratio            = Column(Float, nullable=True)

    # Flexible Campaign-Specific Data (JSON blob)
    campaign_specific_data = Column(JSON, nullable=True)

    created_at            = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    call = relationship("Call", back_populates="outcome")

    def __repr__(self):
        return f"<CallOutcome id={self.id} call_id={self.call_id} type={self.campaign_type}>"


class CallQAPair(Base):
    """Objection/Response pairs for RAG and training (Task 65)."""
    __tablename__ = "call_qa_pairs"

    id                    = Column(Integer, primary_key=True, index=True)
    call_id               = Column(Integer, ForeignKey("calls.id"), nullable=False, index=True)
    objection             = Column(Text, nullable=False)
    response              = Column(Text, nullable=False)
    customer_emotion_at   = Column(String(50), nullable=True)
    customer_emotion_after = Column(String(50), nullable=True)
    is_golden_response    = Column(Boolean, default=False)
    created_at            = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    call = relationship("Call", back_populates="qa_pairs")


class CallAnnotation(Base):
    """Timestamped supervisor notes and tags (Task 65)."""
    __tablename__ = "call_annotations"

    id                    = Column(Integer, primary_key=True, index=True)
    call_id               = Column(Integer, ForeignKey("calls.id"), nullable=False, index=True)
    timestamp             = Column(Float, nullable=False) # seconds into call
    note                  = Column(Text, nullable=False)
    tag                   = Column(String(50), nullable=True) # best_practice, mistake, etc.
    created_at            = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    call = relationship("Call", back_populates="annotations")


class CoachingSession(Base):
    """Training sessions for agents and their impact (Task 65)."""
    __tablename__ = "coaching_sessions"

    id                    = Column(Integer, primary_key=True, index=True)
    employee_id           = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    date                  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    topic                 = Column(String(255), nullable=False)
    score_before          = Column(Float, nullable=True) # Avg score before session
    score_after           = Column(Float, nullable=True)  # Avg score after session
    notes                 = Column(Text, nullable=True)
    created_at            = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    employee = relationship("Employee", back_populates="coaching_sessions")


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


# ---------------------------------------------------------------------------
# Live Pipeline Models (Phase 1)
# ---------------------------------------------------------------------------

class LiveSessionStatus(str, enum.Enum):
    ACTIVE   = "active"
    FLUSHING = "flushing"
    COMPLETE = "complete"


class LiveSession(Base):
    __tablename__ = "live_sessions"

    id              = Column(String(36), primary_key=True) # UUID
    agent_id        = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    campaign_id     = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    call_id         = Column(Integer, ForeignKey("calls.id"), nullable=True, index=True)
    gpu_id          = Column(Integer, default=0, nullable=False) # Dynamic routing target (C-5)
    status          = Column(SAEnum(LiveSessionStatus), default=LiveSessionStatus.ACTIVE, nullable=False)
    reconnect_token = Column(String(64), nullable=False)
    agent_audio_path = Column(String(500), nullable=True) # Stores uploaded microphone file
    created_at      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<LiveSession id={self.id} status={self.status.value}>"


class LiveTranscriptSegment(Base):
    __tablename__ = "live_transcript_segments"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("live_sessions.id"), nullable=False)
    timestamp  = Column(Float, nullable=False)
    speaker    = Column(String(50), nullable=False)
    text       = Column(Text, nullable=False)

    __table_args__ = (
        Index("idx_session_timestamp", "session_id", "timestamp"),
        Index("idx_session_id", "session_id"),
    )

    def __repr__(self):
        return f"<LiveTranscriptSegment(id={self.id}, session_id='{self.session_id}', text='{self.text[:20]}...')>"


# ---------------------------------------------------------------------------
# Self-Improvement Loop Models (Phase 7)
# ---------------------------------------------------------------------------

class CandidateStatus(str, enum.Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class GoldenPairCandidate(Base):
    """
    Human-in-the-Loop Review Queue for high-quality Q&A pairs.
    Nominated by AI when evaluation score >= 85 and response is substantial.
    """
    __tablename__ = "golden_pair_candidates"

    id          = Column(Integer, primary_key=True, index=True)
    call_id     = Column(Integer, ForeignKey("calls.id"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    question    = Column(Text, nullable=False) # The customer's objection
    answer      = Column(Text, nullable=False) # The agent's response
    score       = Column(Float, nullable=False) # The evaluation score of the call
    status      = Column(SAEnum(CandidateStatus), default=CandidateStatus.PENDING, nullable=False, index=True)
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
