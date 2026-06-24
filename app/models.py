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
    Column, Integer, String, Float, Text, DateTime, Date, Time,
    ForeignKey, Enum as SAEnum, JSON, Boolean, Index, UniqueConstraint, text,
)
from sqlalchemy.orm import relationship

from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)


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
    OPS_MANAGER = "OPS_MANAGER"
    TEAM_MANAGER = "TEAM_MANAGER"
    TEAM_LEADER = "TEAM_LEADER"


class RoleNoteVisibility(str, enum.Enum):
    INTERNAL = "INTERNAL"
    RECIPIENT_VISIBLE = "RECIPIENT_VISIBLE"
    AGENT_VISIBLE = "AGENT_VISIBLE"


class RoleNoteStatus(str, enum.Enum):
    OPEN = "OPEN"
    READ = "READ"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_REPLY = "WAITING_REPLY"
    RESOLVED = "RESOLVED"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class EmployeeStatus(str, enum.Enum):
    """Account states for the platform."""
    ACTIVE    = "active"
    DISABLED  = "disabled"
    SUSPENDED = "suspended"


def _recording_ingestion_enum(enum_cls: type[enum.Enum], *, name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
    )


class RecordingIngestionRunTrigger(str, enum.Enum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    RETRY = "retry"
    RECONCILIATION = "reconciliation"


class RecordingIngestionRunStatus(str, enum.Enum):
    REQUESTED = "requested"
    READING_SOURCE = "reading_source"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class RecordingIngestionRecordStatus(str, enum.Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    QUARANTINED = "quarantined"
    INSPECTING = "inspecting"
    ACCEPTED = "accepted"
    HANDOFF_PENDING = "handoff_pending"
    SUBMITTED = "submitted"
    DUPLICATE = "duplicate"
    FAILED = "failed"
    RETRY_SCHEDULED = "retry_scheduled"
    REQUIRES_REVIEW = "requires_review"
    REJECTED = "rejected"


class RecordingIngestionInspectionStatus(str, enum.Enum):
    PENDING = "pending"
    PASSED = "passed"
    REJECTED = "rejected"
    UNAVAILABLE = "unavailable"


class RecordingIngestionAttemptPhase(str, enum.Enum):
    VALIDATION = "validation"
    DOWNLOAD = "download"
    SIGNATURE_CHECK = "signature_check"
    MALWARE_SCAN = "malware_scan"
    MEDIA_VERIFICATION = "media_verification"
    STORAGE = "storage"
    HANDOFF = "handoff"


class RecordingIngestionAttemptStatus(str, enum.Enum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    RETRY_SCHEDULED = "retry_scheduled"


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
    __table_args__ = (
        Index("ix_employees_role_status", "role", "status"),
    )

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(255), nullable=False)
    email      = Column(String(255), unique=True, index=True, nullable=False)
    otp_email  = Column(String(255), nullable=True, index=True)
    department = Column(String(255), nullable=True)
    employee_code = Column(String(50), unique=True, nullable=False, index=True)
    national_id_hash = Column(String(128), nullable=True, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role       = Column(SAEnum(UserRole), default=UserRole.AGENT, nullable=False, index=True)
    qa_scope_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    qa_scope_campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True, index=True)
    avatar     = Column(String(255), nullable=True) # URL or initials
    tier       = Column(SAEnum(EmployeeTier), default=EmployeeTier.BRONZE, nullable=False)
    status     = Column(String(50), default="active", nullable=False, index=True)
    skills     = Column(JSON, nullable=True) # e.g. {"empathy": 80, "resolution": 75}
    phone_number = Column(String(50), nullable=True)
    emotion_history = Column(JSON, nullable=True) # e.g. [65, 70, 72, 68]
    agent_tenure_days = Column(Integer, nullable=True) # (Task 65)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    calls = relationship("Call", back_populates="employee", lazy="dynamic")
    mastery_stats = relationship("AgentMasteryStats", back_populates="employee", uselist=False, cascade="all, delete-orphan")
    coaching_sessions = relationship("CoachingSession", back_populates="employee", cascade="all, delete-orphan")
    violations = relationship(
        "AgentViolation",
        back_populates="employee",
        cascade="all, delete-orphan",
        foreign_keys="AgentViolation.employee_id",
    )
    attendance_records = relationship("AttendanceRecord", back_populates="employee", cascade="all, delete-orphan")
    login_otp_challenges = relationship("LoginOtpChallenge", back_populates="employee", cascade="all, delete-orphan")
    qa_scope_team = relationship("Team", foreign_keys=[qa_scope_team_id])
    qa_scope_campaign = relationship("Campaign", foreign_keys=[qa_scope_campaign_id])

    def __repr__(self):
        return f"<Employee id={self.id} name={self.name!r}>"

    @property
    def qa_scope_team_name(self) -> str | None:
        return self.qa_scope_team.name if self.qa_scope_team else None

    @property
    def qa_scope_campaign_name(self) -> str | None:
        return self.qa_scope_campaign.name if self.qa_scope_campaign else None


class LoginOtpChallenge(Base):
    __tablename__ = "login_otp_challenges"
    __table_args__ = (
        Index("ix_login_otp_employee_active", "employee_id", "used_at", "expires_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    otp_hash = Column(String(128), nullable=False)
    purpose = Column(String(50), default="LOGIN", nullable=False, index=True)
    destination_email = Column(String(255), nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=5, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    ip_address = Column(String(64), nullable=True)
    device_id_hash = Column(String(128), nullable=True, index=True)

    employee = relationship("Employee", back_populates="login_otp_challenges")


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
    created_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    calls = relationship("Call", back_populates="campaign", lazy="dynamic")
    violations = relationship("AgentViolation", back_populates="campaign", cascade="all, delete-orphan")
    operational_targets = relationship("OperationalTarget", back_populates="campaign", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Campaign id={self.id} name={self.name!r}>"


class Call(Base):
    __tablename__ = "calls"
    __table_args__ = (
        Index("ix_calls_employee_created_at", "employee_id", "created_at"),
        Index("ix_calls_campaign_created_at", "campaign_id", "created_at"),
        Index("ix_calls_status_created_at", "status", "created_at"),
        Index("ix_calls_lead_status_created_at", "lead_status", "created_at"),
    )

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
    needs_review        = Column(Boolean, default=False)
    qa_alarm            = Column(Boolean, default=False, nullable=False)
    qa_alarm_reason     = Column(Text, nullable=True)
    qa_alarm_evidence   = Column(Text, nullable=True)

    # Timestamps
    created_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    processed_at     = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    employee = relationship("Employee", back_populates="calls")
    campaign = relationship("Campaign", back_populates="calls")
    outcome  = relationship("CallOutcome", back_populates="call", uselist=False, cascade="all, delete-orphan")
    qa_pairs = relationship("CallQAPair", back_populates="call", cascade="all, delete-orphan")
    annotations = relationship("CallAnnotation", back_populates="call", cascade="all, delete-orphan")
    violations = relationship("AgentViolation", back_populates="call", cascade="all, delete-orphan")
    ingestion_record = relationship("RecordingIngestionRecord", back_populates="call", uselist=False)

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


class RecordingIngestionRun(Base):
    __tablename__ = "recording_ingestion_runs"
    __table_args__ = (
        Index("ix_recording_ingestion_runs_source_status", "source_name", "status"),
        Index("ix_recording_ingestion_runs_source_started_at", "source_name", "started_at"),
        Index(
            "uq_recording_ingestion_runs_active_source",
            "source_name",
            unique=True,
            postgresql_where=text("status IN ('requested', 'reading_source', 'processing')"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(100), nullable=False, default="vicdi_tests", index=True)
    trigger = Column(
        _recording_ingestion_enum(RecordingIngestionRunTrigger, name="recordingingestionruntrigger"),
        nullable=False,
        index=True,
    )
    status = Column(
        _recording_ingestion_enum(RecordingIngestionRunStatus, name="recordingingestionrunstatus"),
        nullable=False,
        default=RecordingIngestionRunStatus.REQUESTED,
        index=True,
    )
    requested_by_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    rows_seen = Column(Integer, nullable=False, default=0)
    new_count = Column(Integer, nullable=False, default=0)
    duplicate_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    retryable_count = Column(Integer, nullable=False, default=0)
    failure_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    requested_by = relationship("Employee", foreign_keys=[requested_by_employee_id])
    attempts = relationship("RecordingIngestionAttempt", back_populates="ingestion_run", cascade="all, delete-orphan")
    records = relationship("RecordingIngestionRecord", back_populates="ingestion_run")


class RecordingIngestionRecord(Base):
    __tablename__ = "recording_ingestion_records"
    __table_args__ = (
        UniqueConstraint("source_name", "source_key", name="uq_recording_ingestion_records_source_key"),
        Index("ix_recording_ingestion_records_source_status_retry", "source_name", "status", "next_retry_at"),
        Index("ix_recording_ingestion_records_employee_id", "employee_id"),
        Index("ix_recording_ingestion_records_call_id", "call_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ingestion_run_id = Column(Integer, ForeignKey("recording_ingestion_runs.id"), nullable=False, index=True)
    source_name = Column(String(100), nullable=False, default="vicdi_tests", index=True)
    source_key = Column(String(255), nullable=False, index=True)
    source_row_number = Column(Integer, nullable=False, index=True)
    source_payload = Column(JSON, nullable=False)
    recording_url = Column(Text, nullable=False)
    recording_url_fingerprint = Column(String(128), nullable=False, index=True)
    source_call_date = Column(Date, nullable=True, index=True)
    source_score = Column(Float, nullable=True)
    source_quality_notes = Column(Text, nullable=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    status = Column(
        _recording_ingestion_enum(RecordingIngestionRecordStatus, name="recordingingestionrecordstatus"),
        nullable=False,
        default=RecordingIngestionRecordStatus.PENDING,
        index=True,
    )
    attempt_count = Column(Integer, nullable=False, default=0)
    next_retry_at = Column(DateTime(timezone=True), nullable=True, index=True)
    quarantine_file_path = Column(String(500), nullable=True)
    stored_file_path = Column(String(500), nullable=True)
    content_type = Column(String(100), nullable=True)
    byte_size = Column(Integer, nullable=True)
    file_sha256 = Column(String(128), nullable=True, index=True)
    signature_status = Column(
        _recording_ingestion_enum(RecordingIngestionInspectionStatus, name="recordingingestioninspectionstatus"),
        nullable=False,
        default=RecordingIngestionInspectionStatus.PENDING,
        index=True,
    )
    malware_scan_status = Column(
        _recording_ingestion_enum(RecordingIngestionInspectionStatus, name="recordingingestioninspectionstatus"),
        nullable=False,
        default=RecordingIngestionInspectionStatus.PENDING,
        index=True,
    )
    media_verification_status = Column(
        _recording_ingestion_enum(RecordingIngestionInspectionStatus, name="recordingingestioninspectionstatus"),
        nullable=False,
        default=RecordingIngestionInspectionStatus.PENDING,
        index=True,
    )
    scanner_name = Column(String(100), nullable=True)
    scanner_version = Column(String(100), nullable=True)
    inspection_completed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id"), nullable=True, unique=True)
    pipeline_queued_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_error_category = Column(String(100), nullable=True)
    last_error_detail = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True, index=True)

    ingestion_run = relationship("RecordingIngestionRun", back_populates="records")
    employee = relationship("Employee", foreign_keys=[employee_id])
    campaign = relationship("Campaign", foreign_keys=[campaign_id])
    call = relationship("Call", back_populates="ingestion_record")
    attempts = relationship("RecordingIngestionAttempt", back_populates="ingestion_record", cascade="all, delete-orphan")

    @property
    def source_reference(self) -> str | None:
        payload = self.source_payload or {}
        crdts = payload.get("CRDTS")
        if isinstance(crdts, str) and crdts.strip():
            return crdts.strip()
        return self.source_key

    @property
    def agent_code(self) -> str | None:
        payload = self.source_payload or {}
        source_code = payload.get("CODE")
        if isinstance(source_code, str) and source_code.strip():
            return source_code.strip()
        if self.employee is not None and getattr(self.employee, "employee_code", None):
            return str(self.employee.employee_code).strip() or None
        return None

    @property
    def agent_name(self) -> str | None:
        payload = self.source_payload or {}
        source_name = payload.get("NAME")
        if isinstance(source_name, str) and source_name.strip():
            return source_name.strip()
        if self.employee is not None and getattr(self.employee, "name", None):
            return str(self.employee.name).strip() or None
        return None


class RecordingIngestionAttempt(Base):
    __tablename__ = "recording_ingestion_attempts"
    __table_args__ = (
        UniqueConstraint(
            "ingestion_record_id",
            "attempt_number",
            "phase",
            name="uq_recording_ingestion_attempts_record_attempt_phase",
        ),
        Index("ix_recording_ingestion_attempts_run_id", "ingestion_run_id"),
        Index("ix_recording_ingestion_attempts_record_id", "ingestion_record_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ingestion_record_id = Column(Integer, ForeignKey("recording_ingestion_records.id"), nullable=False)
    ingestion_run_id = Column(Integer, ForeignKey("recording_ingestion_runs.id"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    phase = Column(
        _recording_ingestion_enum(RecordingIngestionAttemptPhase, name="recordingingestionattemptphase"),
        nullable=False,
        index=True,
    )
    status = Column(
        _recording_ingestion_enum(RecordingIngestionAttemptStatus, name="recordingingestionattemptstatus"),
        nullable=False,
        default=RecordingIngestionAttemptStatus.STARTED,
        index=True,
    )
    error_category = Column(String(100), nullable=True)
    error_detail = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    http_status = Column(Integer, nullable=True)
    bytes_downloaded = Column(Integer, nullable=True)

    ingestion_record = relationship("RecordingIngestionRecord", back_populates="attempts")
    ingestion_run = relationship("RecordingIngestionRun", back_populates="attempts")


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
    supervisor_id         = Column(Integer, ForeignKey("employees.id"), nullable=False)
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


class InterviewJobStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAUSED = "paused"
    CLOSED = "closed"


class InterviewCandidateStatus(str, enum.Enum):
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEWING = "interviewing"
    EVALUATED = "evaluated"
    SHORTLISTED = "shortlisted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class InterviewSessionStatus(str, enum.Enum):
    INVITED = "invited"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class InterviewQuestionSource(str, enum.Enum):
    BASE = "base"
    CV_AI = "cv_ai"
    HR_MANUAL = "hr_manual"


class InterviewAnswerStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    EVALUATED = "evaluated"
    FAILED = "failed"

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


class AgentViolation(Base):
    __tablename__ = "agent_violations"
    __table_args__ = (
        Index("ix_agent_violations_employee_created_at", "employee_id", "created_at"),
        Index("ix_agent_violations_violation_created_at", "violation_id", "created_at"),
        Index("ix_agent_violations_severity_created_at", "severity", "created_at"),
        Index("ix_agent_violations_hr_flagged_created_at", "hr_flagged", "created_at"),
    )

    id                = Column(Integer, primary_key=True, index=True)
    employee_id       = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    call_id           = Column(Integer, ForeignKey("calls.id"), nullable=False, index=True)
    campaign_id       = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    violation_id      = Column(String(50), nullable=False, index=True)
    # e.g. "abusive_language", "dead_air", "skipped_offer"
    severity          = Column(String(10), nullable=False, index=True)
    # "high" | "medium" | "low"
    occurrence        = Column(Integer, nullable=False)
    # 1 = first time, 2 = second, 3 = third+
    penalty_tier      = Column(String(20), nullable=False)
    # "Warning" | "1 HR" | "2 HR" | "3 HR" | "Half Day" | "Full Day" | "Termination"
    score_deduction   = Column(Float, default=0.0, nullable=False)
    hr_flagged        = Column(Boolean, default=False, nullable=False, index=True)
    qa_approved       = Column(Boolean, default=False, nullable=False, index=True)
    qa_approved_by_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    qa_approved_at    = Column(DateTime(timezone=True), nullable=True)
    qa_approval_note  = Column(Text, nullable=True)
    hr_approved       = Column(Boolean, default=False, nullable=False, index=True)
    hr_approved_by_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    hr_approved_at    = Column(DateTime(timezone=True), nullable=True)
    hr_approval_note  = Column(Text, nullable=True)
    auto_fail         = Column(Boolean, default=False, nullable=False)
    evidence          = Column(Text, nullable=True)
    timestamp_in_call = Column(String(10), nullable=True)
    # "MM:SS" format, e.g. "03:45"
    created_at        = Column(DateTime(timezone=True),
                               default=lambda: datetime.now(timezone.utc),
                               index=True)

    # Relationships
    employee  = relationship("Employee", back_populates="violations", foreign_keys=[employee_id])
    call      = relationship("Call", back_populates="violations")
    campaign  = relationship("Campaign", back_populates="violations")
    qa_approver = relationship("Employee", foreign_keys=[qa_approved_by_id])
    hr_approver = relationship("Employee", foreign_keys=[hr_approved_by_id])


class ScoreOverrideAudit(Base):
    __tablename__ = "score_override_audits"

    id            = Column(Integer, primary_key=True, index=True)
    call_id       = Column(Integer, ForeignKey("calls.id"), nullable=False, index=True)
    reviewer_id   = Column(Integer, ForeignKey("employees.id"), nullable=False)
    reviewer_name = Column(String(255), nullable=False)
    old_score     = Column(Float, nullable=True)
    new_score     = Column(Float, nullable=False)
    reason        = Column(Text, nullable=True)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    call          = relationship("Call", backref="override_audits")
    reviewer      = relationship("Employee")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id            = Column(Integer, primary_key=True, index=True)
    actor_id      = Column(Integer, ForeignKey("employees.id"), nullable=True)
    actor_email   = Column(String(255), nullable=True)
    action        = Column(String(100), nullable=False)
    target        = Column(String(255), nullable=True)
    before_state  = Column(Text, nullable=True)
    after_state   = Column(Text, nullable=True)
    reason        = Column(Text, nullable=True)
    success       = Column(Boolean, nullable=False, default=True)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    actor         = relationship("Employee", foreign_keys=[actor_id])


class AppPermission(Base):
    __tablename__ = "app_permissions"

    id          = Column(Integer, primary_key=True, index=True)
    key         = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active   = Column(Boolean, default=True, nullable=False, index=True)
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role", "permission_id", name="uq_role_permission"),
        Index("ix_role_permissions_role", "role"),
    )

    id            = Column(Integer, primary_key=True, index=True)
    role          = Column(SAEnum(UserRole), nullable=False)
    permission_id = Column(Integer, ForeignKey("app_permissions.id"), nullable=False, index=True)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    permission = relationship("AppPermission")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        Index("ix_attendance_records_employee_date", "employee_id", "attendance_date"),
    )

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    attendance_date = Column(Date, nullable=False, index=True)
    status = Column(String(50), nullable=False)
    scheduled_minutes = Column(Integer, nullable=True)
    worked_minutes = Column(Integer, nullable=True)
    late_minutes = Column(Integer, nullable=True)
    absence_reason = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    employee = relationship("Employee", back_populates="attendance_records")

    def __repr__(self):
        return f"<AttendanceRecord id={self.id} employee_id={self.employee_id} date={self.attendance_date}>"


class OperationalTarget(Base):
    __tablename__ = "operational_targets"
    __table_args__ = (
        Index("ix_operational_targets_camp_metric_seg", "campaign_id", "metric_name", "segment"),
        Index("ix_operational_targets_effective_dates", "effective_from", "effective_to"),
    )

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True, index=True) # Nullable for company-wide scope
    metric_name = Column(String(255), nullable=False, index=True)
    segment = Column(String(100), nullable=True)
    target_value = Column(Float, nullable=False)
    warning_threshold = Column(Float, nullable=True)
    critical_threshold = Column(Float, nullable=True)
    effective_from = Column(DateTime(timezone=True), nullable=False)
    effective_to = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    campaign = relationship("Campaign", back_populates="operational_targets")

    def __repr__(self):
        return f"<OperationalTarget id={self.id} campaign_id={self.campaign_id} metric={self.metric_name!r}>"


class Team(Base):
    __tablename__ = "teams"

    id          = Column(Integer, primary_key=True)
    name        = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True, index=True)
    manager_id  = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    leader_id   = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    is_active   = Column(Boolean, nullable=False, default=True, index=True)
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    campaign = relationship("Campaign", foreign_keys=[campaign_id])
    manager  = relationship("Employee", foreign_keys=[manager_id])
    leader   = relationship("Employee", foreign_keys=[leader_id])
    assignments = relationship("EmployeeTeamAssignment", back_populates="team", cascade="all, delete-orphan")


class EmployeeTeamAssignment(Base):
    __tablename__ = "employee_team_assignments"

    id            = Column(Integer, primary_key=True)
    employee_id   = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    team_id       = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    assigned_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    ended_at      = Column(DateTime(timezone=True), nullable=True)
    is_active     = Column(Boolean, nullable=False, default=True)
    created_by_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    __table_args__ = (
        Index("ix_employee_team_assignments_employee_active", "employee_id", "is_active"),
        Index("ix_employee_team_assignments_team_active", "team_id", "is_active"),
    )

    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id])
    team     = relationship("Team", back_populates="assignments", foreign_keys=[team_id])
    created_by = relationship("Employee", foreign_keys=[created_by_id])


class AgentTransferRequest(Base):
    __tablename__ = "agent_transfer_requests"

    id              = Column(Integer, primary_key=True)
    agent_id        = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    from_team_id    = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    to_team_id      = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    requested_by_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    reviewed_by_id  = Column(Integer, ForeignKey("employees.id"), nullable=True)
    status          = Column(String(50), nullable=False, default="PENDING", index=True)
    reason          = Column(Text, nullable=False)
    review_note     = Column(Text, nullable=True)
    created_at      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    reviewed_at     = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    agent        = relationship("Employee", foreign_keys=[agent_id])
    from_team    = relationship("Team", foreign_keys=[from_team_id])
    to_team      = relationship("Team", foreign_keys=[to_team_id])
    requested_by = relationship("Employee", foreign_keys=[requested_by_id])
    reviewed_by  = relationship("Employee", foreign_keys=[reviewed_by_id])


class RoleNote(Base):
    __tablename__ = "role_notes"

    id                    = Column(Integer, primary_key=True)
    sender_id             = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    recipient_id          = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    recipient_role        = Column(String(50), nullable=True, index=True)
    visibility            = Column(SAEnum(RoleNoteVisibility), nullable=False, default=RoleNoteVisibility.INTERNAL, index=True)
    team_id               = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    campaign_id           = Column(Integer, ForeignKey("campaigns.id"), nullable=True, index=True)
    employee_id           = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    call_id               = Column(Integer, ForeignKey("calls.id"), nullable=True, index=True)
    parent_note_id        = Column(Integer, ForeignKey("role_notes.id"), nullable=True, index=True)
    title                 = Column(String(255), nullable=False)
    body                  = Column(Text, nullable=False)
    note_type             = Column(String(50), nullable=False, default="GENERAL", index=True)
    priority              = Column(String(50), nullable=False, default="NORMAL", index=True)
    status                = Column(String(50), nullable=False, default="OPEN", index=True)
    kpi_key               = Column(String(100), nullable=True)
    kpi_label             = Column(String(255), nullable=True)
    current_value         = Column(Float, nullable=True)
    target_value          = Column(Float, nullable=True)
    period_start          = Column(DateTime(timezone=True), nullable=True)
    period_end            = Column(DateTime(timezone=True), nullable=True)
    agent_name_snapshot   = Column(String(255), nullable=True)
    team_name_snapshot    = Column(String(255), nullable=True)
    campaign_name_snapshot = Column(String(255), nullable=True)
    created_at            = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at            = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    read_at               = Column(DateTime(timezone=True), nullable=True)
    resolved_at           = Column(DateTime(timezone=True), nullable=True)
    resolved_by_id        = Column(Integer, ForeignKey("employees.id"), nullable=True)
    deleted_at            = Column(DateTime(timezone=True), nullable=True, index=True)
    deleted_by_id         = Column(Integer, ForeignKey("employees.id"), nullable=True)
    delete_reason         = Column(Text, nullable=True)

    # Relationships
    sender      = relationship("Employee", foreign_keys=[sender_id])
    recipient   = relationship("Employee", foreign_keys=[recipient_id])
    team        = relationship("Team", foreign_keys=[team_id])
    campaign    = relationship("Campaign", foreign_keys=[campaign_id])
    employee    = relationship("Employee", foreign_keys=[employee_id])
    call        = relationship("Call", foreign_keys=[call_id])
    parent      = relationship("RoleNote", remote_side=[id], foreign_keys=[parent_note_id])
    resolved_by = relationship("Employee", foreign_keys=[resolved_by_id])
    deleted_by  = relationship("Employee", foreign_keys=[deleted_by_id])


class KpiThresholdConfig(Base):
    __tablename__ = "kpi_threshold_configs"

    id             = Column(Integer, primary_key=True, index=True)
    team_id        = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    campaign_id    = Column(Integer, ForeignKey("campaigns.id"), nullable=True, index=True)
    kpi_key        = Column(String(100), nullable=False, index=True)
    kpi_label      = Column(String(255), nullable=False)
    threshold_type = Column(String(50), nullable=False)
    target_value   = Column(Float, nullable=False)
    is_active      = Column(Boolean, nullable=False, default=True, index=True)
    created_by_id  = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    created_at     = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at     = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    team       = relationship("Team", foreign_keys=[team_id])
    campaign   = relationship("Campaign", foreign_keys=[campaign_id])
    created_by = relationship("Employee", foreign_keys=[created_by_id])


class InterviewJob(Base):
    __tablename__ = "interview_jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    department = Column(String(255), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True, index=True)
    status = Column(SAEnum(InterviewJobStatus), default=InterviewJobStatus.DRAFT, nullable=False, index=True)
    base_questions = Column(JSON, nullable=True)
    scoring_weights = Column(JSON, nullable=True)
    mcq_enabled = Column(Boolean, nullable=False, default=False)
    mcq_questions = Column(JSON, nullable=True)
    created_by_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    updated_by_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    team = relationship("Team", foreign_keys=[team_id])
    campaign = relationship("Campaign", foreign_keys=[campaign_id])
    created_by = relationship("Employee", foreign_keys=[created_by_id])
    updated_by = relationship("Employee", foreign_keys=[updated_by_id])
    candidates = relationship("InterviewCandidate", back_populates="job", cascade="all, delete-orphan")
    sessions = relationship("InterviewSession", back_populates="job", cascade="all, delete-orphan")
    questions = relationship("InterviewQuestion", back_populates="job", cascade="all, delete-orphan")
    mcq_submissions = relationship("InterviewMcqSubmission", back_populates="job", cascade="all, delete-orphan")


class InterviewCandidate(Base):
    __tablename__ = "interview_candidates"
    __table_args__ = (
        UniqueConstraint("job_id", "contact_email_normalized", name="uq_interview_candidates_job_email_normalized"),
        Index("ix_interview_candidates_job_status", "job_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("interview_jobs.id"), nullable=False, index=True)
    full_name = Column(String(255), nullable=False, index=True)
    contact_email = Column(String(255), nullable=False)
    contact_email_normalized = Column(String(255), nullable=False, index=True)
    phone_number = Column(String(50), nullable=True)
    phone_normalized = Column(String(50), nullable=True, index=True)
    national_id_hash = Column(String(128), nullable=True, index=True)
    national_id_last4 = Column(String(4), nullable=True)
    date_of_birth_encrypted = Column(Text, nullable=True)
    address_encrypted = Column(Text, nullable=True)
    registration_source = Column(String(50), nullable=False, default="hr", index=True)
    status = Column(SAEnum(InterviewCandidateStatus), default=InterviewCandidateStatus.APPLIED, nullable=False, index=True)
    final_score = Column(Float, nullable=True)
    global_percentile = Column(Float, nullable=True)
    applied_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    converted_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, unique=True)
    created_by_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    job = relationship("InterviewJob", back_populates="candidates")
    converted_employee = relationship("Employee", foreign_keys=[converted_employee_id])
    created_by = relationship("Employee", foreign_keys=[created_by_id])
    documents = relationship("InterviewCandidateDocument", back_populates="candidate", cascade="all, delete-orphan")
    sessions = relationship("InterviewSession", back_populates="candidate", cascade="all, delete-orphan")
    questions = relationship("InterviewQuestion", back_populates="candidate", cascade="all, delete-orphan")
    answers = relationship("InterviewAnswer", back_populates="candidate", cascade="all, delete-orphan")
    workflow_events = relationship("InterviewWorkflowEvent", back_populates="candidate", cascade="all, delete-orphan")
    mcq_submissions = relationship("InterviewMcqSubmission", back_populates="candidate", cascade="all, delete-orphan")


class InterviewCandidateDocument(Base):
    __tablename__ = "interview_candidate_documents"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("interview_candidates.id"), nullable=False, index=True)
    document_type = Column(String(50), nullable=False, default="cv")
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    content_type = Column(String(100), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    is_encrypted = Column(Boolean, nullable=False, default=False, index=True)
    extracted_text = Column(Text, nullable=True)
    extraction_status = Column(String(50), nullable=False, default="pending", index=True)
    extraction_error = Column(Text, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    candidate = relationship("InterviewCandidate", back_populates="documents")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("interview_candidates.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("interview_jobs.id"), nullable=False, index=True)
    session_token_hash = Column(String(128), nullable=False, unique=True, index=True)
    status = Column(SAEnum(InterviewSessionStatus), default=InterviewSessionStatus.INVITED, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    question_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    candidate = relationship("InterviewCandidate", back_populates="sessions")
    job = relationship("InterviewJob", back_populates="sessions")
    questions = relationship("InterviewQuestion", back_populates="session", cascade="all, delete-orphan")
    answers = relationship("InterviewAnswer", back_populates="session", cascade="all, delete-orphan")
    mcq_submission = relationship("InterviewMcqSubmission", back_populates="session", uselist=False, cascade="all, delete-orphan")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("interview_jobs.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=True, index=True)
    candidate_id = Column(Integer, ForeignKey("interview_candidates.id"), nullable=True, index=True)
    question_text = Column(Text, nullable=False)
    expected_skills_tags = Column(JSON, nullable=True)
    source = Column(SAEnum(InterviewQuestionSource), nullable=False, default=InterviewQuestionSource.BASE)
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    job = relationship("InterviewJob", back_populates="questions")
    session = relationship("InterviewSession", back_populates="questions")
    candidate = relationship("InterviewCandidate", back_populates="questions")
    answers = relationship("InterviewAnswer", back_populates="question", cascade="all, delete-orphan")


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"
    __table_args__ = (
        UniqueConstraint("session_id", "question_id", name="uq_interview_answers_session_question"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("interview_candidates.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("interview_questions.id"), nullable=False, index=True)
    audio_file_path = Column(String(500), nullable=True)
    transcribed_text = Column(Text, nullable=True)
    relevance_score = Column(Float, nullable=True)
    fluency_score = Column(Float, nullable=True)
    grammar_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)
    ai_summary = Column(Text, nullable=True)
    status = Column(SAEnum(InterviewAnswerStatus), nullable=False, default=InterviewAnswerStatus.PENDING, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    evaluated_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    session = relationship("InterviewSession", back_populates="answers")
    candidate = relationship("InterviewCandidate", back_populates="answers")
    question = relationship("InterviewQuestion", back_populates="answers")


class InterviewMcqSubmission(Base):
    __tablename__ = "interview_mcq_submissions"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_interview_mcq_submissions_session"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("interview_candidates.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("interview_jobs.id"), nullable=False, index=True)
    answers = Column(JSON, nullable=False)
    question_bank_snapshot = Column(JSON, nullable=False)
    breakdown = Column(JSON, nullable=True)
    score = Column(Float, nullable=False, default=0.0)
    total_questions = Column(Integer, nullable=False, default=0)
    percentage = Column(Float, nullable=False, default=0.0)
    completed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    session = relationship("InterviewSession", back_populates="mcq_submission")
    candidate = relationship("InterviewCandidate", back_populates="mcq_submissions")
    job = relationship("InterviewJob", back_populates="mcq_submissions")


class InterviewWorkflowEvent(Base):
    __tablename__ = "interview_workflow_events"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("interview_candidates.id"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    event_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    candidate = relationship("InterviewCandidate", back_populates="workflow_events")
    actor = relationship("Employee", foreign_keys=[actor_id])


class EmployeeShift(Base):
    __tablename__ = "employee_shifts"
    __table_args__ = (
        UniqueConstraint("employee_id", "work_date", name="uq_employee_shift_date"),
        Index("ix_employee_shifts_employee_id_work_date", "employee_id", "work_date"),
        Index("ix_employee_shifts_status_work_date", "status", "work_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    work_date = Column(Date, nullable=False, index=True)
    shift_start = Column(Time, nullable=True)
    shift_end = Column(Time, nullable=True)
    grace_before_minutes = Column(Integer, nullable=False, default=10)
    grace_after_minutes = Column(Integer, nullable=False, default=10)
    status = Column(String(50), nullable=False, default="scheduled", index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    employee = relationship("Employee", foreign_keys=[employee_id])


class TrustedDevice(Base):
    __tablename__ = "trusted_devices"
    __table_args__ = (
        UniqueConstraint("employee_id", "device_id_hash", name="uq_trusted_device_employee_device"),
        Index("ix_trusted_devices_employee_id_is_trusted", "employee_id", "is_trusted"),
    )

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    device_id_hash = Column(String(128), nullable=False, index=True)
    device_fingerprint_hash = Column(String(128), nullable=True)
    user_agent_hash = Column(String(128), nullable=True)
    device_label = Column(String(255), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoke_reason = Column(Text, nullable=True)
    is_trusted = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    employee = relationship("Employee", foreign_keys=[employee_id])
    approved_by = relationship("Employee", foreign_keys=[approved_by_id])


class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_employee_id_is_active", "employee_id", "is_active"),
        Index("ix_user_sessions_employee_device_active", "employee_id", "device_id_hash", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    trusted_device_id = Column(Integer, ForeignKey("trusted_devices.id"), nullable=True, index=True)
    sid = Column(String(64), nullable=False, unique=True, index=True)
    jti = Column(String(64), nullable=False, unique=True, index=True)
    device_id_hash = Column(String(128), nullable=False, index=True)
    device_fingerprint_hash = Column(String(128), nullable=True)
    user_agent_hash = Column(String(128), nullable=True)
    ip_address = Column(String(64), nullable=True)
    issued_at = Column(DateTime(timezone=True), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True, index=True)
    revoke_reason = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    employee = relationship("Employee", foreign_keys=[employee_id])
    trusted_device = relationship("TrustedDevice", foreign_keys=[trusted_device_id])


