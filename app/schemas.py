"""
Pydantic schemas for request/response validation and the Groq structured output.
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
import json
from app.security import validate_password_strength


# ===========================
#  Employee Schemas
# ===========================

class EmployeeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    otp_email: Optional[str] = Field(None, max_length=255)
    national_id: Optional[str] = Field(None, max_length=32)
    password: Optional[str] = Field(None, min_length=6)
    role: str = "AGENT"
    department: Optional[str] = None
    employee_code: str = Field(..., min_length=1, max_length=50)
    avatar: Optional[str] = None
    tier: str = "bronze"
    skills: Optional[dict] = None
    emotion_history: Optional[List[float]] = None
    phone_number: Optional[str] = None
    status: str = "active"

    @field_validator("password")
    @classmethod
    def validate_employee_password(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            validate_password_strength(value)
        return value


class EmployeeUpdate(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None


class EmployeeStatusUpdate(BaseModel):
    status: str


class TeamLeaderAssignmentUpdate(BaseModel):
    leader_id: Optional[int] = None


class QaScopeAssignmentUpdate(BaseModel):
    team_id: Optional[int] = None
    campaign_id: Optional[int] = None


class TeamDirectoryOut(BaseModel):
    id: int
    name: str
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
    manager_id: Optional[int] = None
    manager_name: Optional[str] = None
    leader_id: Optional[int] = None
    leader_name: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: Optional[int] = None
    actor_email: Optional[str] = None
    action: str
    target: Optional[str] = None
    before_state: Optional[str] = None
    after_state: Optional[str] = None
    reason: Optional[str] = None
    success: bool = True
    created_at: datetime


class RoleDefinitionOut(BaseModel):
    role: str
    label: str
    description: str
    permissions: List[str] = Field(default_factory=list)
    assignable_by_hr: bool = False


class RolePermissionUpdate(BaseModel):
    permissions: List[str] = Field(default_factory=list)
    reason: Optional[str] = None


class RolePermissionCatalogOut(BaseModel):
    roles: List[RoleDefinitionOut]
    available_permissions: List[str]








class AgentMasteryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    rapport_building: float
    emotional_sync: float
    ownership_trust: float
    process_clarity: float
    updated_at: datetime

class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    otp_email: Optional[str] = None
    role: str
    department: Optional[str]
    employee_code: str
    avatar: Optional[str]
    tier: str
    skills: Optional[dict]
    emotion_history: Optional[List[float]]
    phone_number: Optional[str] = None
    qa_scope_team_id: Optional[int] = None
    qa_scope_team_name: Optional[str] = None
    qa_scope_campaign_id: Optional[int] = None
    qa_scope_campaign_name: Optional[str] = None
    agent_tenure_days: Optional[int] = 0
    mastery_stats: Optional[AgentMasteryOut] = None
    created_at: datetime
    status: str = "active"


class BulkEmployeeFailure(BaseModel):
    index: int
    employee_code: Optional[str] = None
    error: str


class BulkEmployeeResult(BaseModel):
    success: List[EmployeeOut]
    failed: List[BulkEmployeeFailure]
    message: str
    success_count: int
    failed_count: int


# ===========================
#  Auth Schemas
# ===========================

class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    role: str = "AGENT"

    @field_validator("password")
    @classmethod
    def validate_register_password(cls, value: str) -> str:
        validate_password_strength(value)
        return value

class UserLogin(BaseModel):
    employee_code: Optional[str] = None
    email: Optional[str] = None
    password: str

    @model_validator(mode="after")
    def identifier_required(self):
        if not (self.employee_code or self.email):
            raise ValueError("Employee code is required.")
        return self


class UserOtpVerify(BaseModel):
    challenge_id: int
    otp_code: str = Field(..., min_length=4, max_length=10)


class PasswordResetRequest(BaseModel):
    email: str
    national_id: str = Field(..., min_length=4, max_length=32)


class PasswordResetConfirm(BaseModel):
    challenge_id: int
    otp_code: str = Field(..., min_length=4, max_length=10)
    new_password: str = Field(..., min_length=6)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        validate_password_strength(value)
        return value

class MeResponse(BaseModel):
    id: int
    name: str
    campaign_id: Optional[int] = None
    role: str
    permissions: List[str] = Field(default_factory=list)
    email: Optional[str] = None
    avatar: Optional[str] = None
    qa_scope_team_id: Optional[int] = None
    qa_scope_team_name: Optional[str] = None
    qa_scope_campaign_id: Optional[int] = None
    qa_scope_campaign_name: Optional[str] = None
    account_status: str = "active"
    status: str = "active"


class InterviewJobCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    department: Optional[str] = Field(None, max_length=255)
    team_id: Optional[int] = Field(None, ge=1)
    campaign_id: Optional[int] = Field(None, ge=1)
    status: str = "draft"
    base_questions: List[str] = Field(default_factory=list)
    scoring_weights: Optional[dict] = None
    mcq_enabled: bool = False
    mcq_questions: List[dict] = Field(default_factory=list)


class InterviewJobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    department: Optional[str] = Field(None, max_length=255)
    team_id: Optional[int] = Field(None, ge=1)
    campaign_id: Optional[int] = Field(None, ge=1)
    status: Optional[str] = None
    base_questions: Optional[List[str]] = None
    scoring_weights: Optional[dict] = None
    mcq_enabled: Optional[bool] = None
    mcq_questions: Optional[List[dict]] = None


class InterviewJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    department: Optional[str] = None
    team_id: Optional[int] = None
    campaign_id: Optional[int] = None
    status: str
    base_questions: Optional[list] = None
    scoring_weights: Optional[dict] = None
    mcq_enabled: bool
    mcq_questions: Optional[list] = None
    created_by_id: int
    updated_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class InterviewCandidateCreate(BaseModel):
    job_id: int = Field(..., ge=1)
    full_name: str = Field(..., min_length=1, max_length=255)
    contact_email: str = Field(..., min_length=3, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=50)
    national_id: Optional[str] = Field(None, min_length=4, max_length=32)


class InterviewCandidateUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    contact_email: Optional[str] = Field(None, min_length=3, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = None
    national_id: Optional[str] = Field(None, min_length=4, max_length=32)
    final_score: Optional[float] = None
    global_percentile: Optional[float] = None


class InterviewCandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    full_name: str
    contact_email: str
    contact_email_normalized: str
    phone_number: Optional[str] = None
    phone_normalized: Optional[str] = None
    national_id_last4: Optional[str] = None
    status: str
    final_score: Optional[float] = None
    global_percentile: Optional[float] = None
    applied_at: datetime
    completed_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    converted_employee_id: Optional[int] = None
    created_by_id: Optional[int] = None
    mcq_score: Optional[float] = None
    mcq_total_questions: Optional[int] = None
    mcq_percentage: Optional[float] = None
    mcq_completed_at: Optional[datetime] = None


class InterviewCandidateDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    document_type: str
    original_filename: str
    content_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    extraction_status: str
    extraction_error: Optional[str] = None
    uploaded_at: datetime


class InterviewSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    job_id: int
    status: str
    expires_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    question_count: int
    created_at: datetime


class InterviewPortalJobOut(BaseModel):
    id: int
    title: str
    description: str
    department: Optional[str] = None
    mcq_enabled: bool


class InterviewPortalRegistrationOut(BaseModel):
    status: str = "success"
    candidate_id: int
    candidate_name: str
    job_id: int
    job_title: str
    session_id: int
    session_token: str
    invite_url: Optional[str] = None
    expires_at: datetime
    question_count: int
    duplicate_recent: bool = False
    document_id: Optional[int] = None
    document_extraction_status: Optional[str] = None


class InterviewMcqQuestionOut(BaseModel):
    id: int
    category: str
    question: str
    options: List[str]
    type: str
    correct: Optional[int] = None
    trait_tags: List[str] = Field(default_factory=list)


class InterviewMcqPortalOut(BaseModel):
    mcq_enabled: bool
    mcq_completed: bool
    question_count: int = 0
    questions: List[InterviewMcqQuestionOut] = Field(default_factory=list)


class InterviewMcqSubmitRequest(BaseModel):
    answers: dict[str, int] = Field(default_factory=dict)


class InterviewMcqSubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    candidate_id: int
    job_id: int
    answers: dict
    question_bank_snapshot: list
    breakdown: Optional[dict] = None
    score: float
    total_questions: int
    percentage: float
    completed_at: datetime
    created_at: datetime


class InterviewMcqReviewQuestionOut(BaseModel):
    question_id: int
    question_text: str
    options: List[str]
    user_answer: Optional[int] = None
    correct_answer: Optional[int] = None
    type: Optional[str] = None
    is_correct: Optional[bool] = None
    trait_tags: List[str] = Field(default_factory=list)
    chosen_trait: Optional[str] = None


class InterviewMcqReviewOut(BaseModel):
    status: str = "success"
    candidate_id: int
    candidate_name: str
    score: float
    total_questions: int
    percentage: float
    completed_at: Optional[datetime] = None
    iq: List[InterviewMcqReviewQuestionOut] = Field(default_factory=list)
    computer: List[InterviewMcqReviewQuestionOut] = Field(default_factory=list)
    personality: List[InterviewMcqReviewQuestionOut] = Field(default_factory=list)
    personality_breakdown: dict[str, int] = Field(default_factory=dict)


class InterviewCandidateReviewAnswerOut(BaseModel):
    answer_id: int
    question_id: int
    question_text: str
    overall_score: Optional[float] = None
    status: str
    ai_summary: Optional[str] = None
    transcribed_text: Optional[str] = None
    submitted_at: Optional[datetime] = None
    evaluated_at: Optional[datetime] = None
    error_message: Optional[str] = None


class InterviewCandidateReviewMetricsOut(BaseModel):
    evaluation_state: str
    submitted_answers: int
    evaluated_answers: int
    average_answer_score: Optional[float] = None
    strongest_answer_score: Optional[float] = None
    weakest_answer_score: Optional[float] = None


class InterviewCandidateReviewMcqSummaryOut(BaseModel):
    completed: bool = False
    score: Optional[float] = None
    total_questions: Optional[int] = None
    percentage: Optional[float] = None
    completed_at: Optional[datetime] = None
    objective_breakdown: dict[str, float] = Field(default_factory=dict)
    personality_breakdown: dict[str, int] = Field(default_factory=dict)


class InterviewCandidateRecommendationOut(BaseModel):
    label: str
    score: Optional[float] = None
    rationale: str
    strengths: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)


class InterviewCandidateReviewOut(BaseModel):
    status: str = "success"
    candidate: InterviewCandidateOut
    interview_metrics: InterviewCandidateReviewMetricsOut
    mcq_summary: InterviewCandidateReviewMcqSummaryOut
    recommendation: InterviewCandidateRecommendationOut
    answers: List[InterviewCandidateReviewAnswerOut] = Field(default_factory=list)


class InterviewQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    session_id: Optional[int] = None
    candidate_id: Optional[int] = None
    question_text: str
    expected_skills_tags: Optional[dict | list] = None
    source: str
    display_order: int
    created_at: datetime


class InterviewAnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    candidate_id: int
    question_id: int
    transcribed_text: Optional[str] = None
    relevance_score: Optional[float] = None
    fluency_score: Optional[float] = None
    grammar_score: Optional[float] = None
    overall_score: Optional[float] = None
    ai_summary: Optional[str] = None
    status: str
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    evaluated_at: Optional[datetime] = None
    error_message: Optional[str] = None


class InterviewWorkflowEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    actor_id: Optional[int] = None
    event_type: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    note: Optional[str] = None
    event_payload: Optional[dict] = None
    created_at: datetime


class CandidateTimelineEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    event_type: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    note: Optional[str] = None
    event_payload: Optional[dict] = None
    created_at: datetime


class InterviewCandidateInviteRequest(BaseModel):
    expires_in_hours: int = Field(default=24, ge=1, le=168)
    questions: Optional[List[str]] = None


class InterviewCandidateInviteOut(BaseModel):
    candidate_id: int
    session_id: int
    session_token: str
    invite_url: Optional[str] = None
    expires_at: datetime
    question_count: int


class InterviewCandidateDecisionUpdate(BaseModel):
    note: Optional[str] = None
    send_email: Optional[bool] = False


class InterviewCandidateIdentitySummaryOut(BaseModel):
    candidate_id: int
    full_name: str
    job_id: int
    job_title: Optional[str] = None
    department: Optional[str] = None
    status: str
    phone_last4: Optional[str] = None
    national_id_last4: Optional[str] = None
    contact_email_masked: Optional[str] = None
    converted_employee_id: Optional[int] = None


class InterviewEmployeeMatchOut(BaseModel):
    employee_id: int
    employee_code: str
    employee_email: str
    role: str
    status: str


class InterviewCandidateOnboardingReadinessOut(BaseModel):
    candidate_id: int
    status: str
    is_ready: bool
    blocking_reasons: List[str] = Field(default_factory=list)
    blocking_categories: List[str] = Field(default_factory=list)
    suggested_employee_code: Optional[str] = None
    suggested_company_email: Optional[str] = None
    candidate_identity_summary: InterviewCandidateIdentitySummaryOut
    existing_employee_match: Optional[InterviewEmployeeMatchOut] = None


class InterviewCandidateBulkActionRequest(BaseModel):
    candidate_ids: List[int] = Field(..., min_length=1, max_length=200)
    note: Optional[str] = None


class InterviewCandidateBulkActionOut(BaseModel):
    requested: int
    updated: int
    skipped: int
    candidate_ids: List[int] = Field(default_factory=list)


class InterviewCandidateConvertRequest(BaseModel):
    employee_code: str = Field(..., min_length=1, max_length=50)
    role: str = "AGENT"
    department: Optional[str] = Field(None, max_length=255)
    otp_email: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = Field(None, min_length=6)
    phone_number: Optional[str] = Field(None, max_length=50)


class InterviewPortalSessionOut(BaseModel):
    candidate_id: int
    candidate_name: str
    job_id: int
    job_title: str
    session_id: int
    status: str
    expires_at: datetime
    question_count: int
    mcq_enabled: bool = False
    mcq_completed: bool = False
    mcq_question_count: int = 0
    question_time_limit_seconds: int = 180


class InterviewAnswerSubmitOut(BaseModel):
    answer_id: int
    session_id: int
    question_id: int
    status: str
    transcribed_text: Optional[str] = None


class InterviewQuestionStartOut(BaseModel):
    answer_id: int
    session_id: int
    question_id: int
    status: str
    started_at: datetime
    time_limit_seconds: int


class InterviewPortalAnswerHistoryOut(BaseModel):
    answer_id: int
    question_id: int
    question_text: str
    status: str
    overall_score: Optional[float] = None
    ai_summary: Optional[str] = None
    submitted_at: Optional[datetime] = None
    evaluated_at: Optional[datetime] = None


class InterviewPortalMcqResultOut(BaseModel):
    completed: bool = False
    score: Optional[float] = None
    total_questions: Optional[int] = None
    percentage: Optional[float] = None
    completed_at: Optional[datetime] = None
    objective_breakdown: dict[str, float] = Field(default_factory=dict)
    personality_breakdown: dict[str, int] = Field(default_factory=dict)


class InterviewPortalDashboardOut(BaseModel):
    candidate_id: int
    candidate_name: str
    job_id: int
    job_title: str
    session_id: int
    session_status: str
    completed_at: Optional[datetime] = None
    question_count: int
    submitted_answers: int
    evaluated_answers: int
    average_score: Optional[float] = None
    answers: List[InterviewPortalAnswerHistoryOut] = Field(default_factory=list)
    mcq_result: InterviewPortalMcqResultOut


class InterviewCandidateConversionOut(BaseModel):
    candidate_id: int
    employee_id: int
    employee_code: str
    employee_email: str
    role: str


class InterviewRetentionPurgeRequest(BaseModel):
    older_than_days: int = Field(default=90, ge=1, le=3650)
    dry_run: bool = True


class InterviewRetentionPurgeOut(BaseModel):
    archived_candidates_matched: int
    candidates_deleted: int
    document_rows_deleted: int
    answer_audio_files_deleted: int
    document_files_deleted: int
    dry_run: bool

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    type: str = "customer_service"
    status: str = "active"
    kpis: Optional[List[str]] = None
    color: str = "#6366f1"
    evaluation_prompt: str = Field(..., min_length=10)


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    type: str
    status: str
    kpis: Optional[List[str]] = None
    color: str
    evaluation_prompt: str
    created_at: datetime

    # Computed stats
    total_calls: int = 0
    agent_count: int = 0
    avg_score: float = 0.0


# ===========================
#  Groq Evaluation Schemas
# ===========================

class QAPairItem(BaseModel):
    """Objection/Response pair for RAG (Task 65)."""
    objection: str = Field(..., description="The customer objection or critical question")
    response: str = Field(..., description="The agent's response to the objection")
    customer_emotion_at: str = Field(default="neutral", description="Customer emotion during the objection")
    customer_emotion_after: str = Field(default="neutral", description="Customer emotion after the agent's response")
    is_golden: bool = Field(default=False, description="Whether this response is considered an ideal 'Golden' response")


class StrengthItem(BaseModel):
    """Schema for individual identified strengths in a call."""
    issue: str = Field(..., description="Short category label for the strength")
    detail: str = Field(default="", description="Explanation of the positive behavior")


class WeaknessItem(BaseModel):
    """Schema for individual identified weaknesses in a call."""
    issue: str = Field(..., description="Short category label for the weakness")
    detail: str = Field(..., description="Explanation of what was wrong")
    deduction: float = Field(..., description="Points deducted for this weakness")
    score: Optional[float] = Field(default=None, description="Points earned in this category")
    max: Optional[int] = Field(default=None, description="Maximum possible points for this category")


class EvaluationResult(BaseModel):
    """
    Strict schema that Groq must return.
    This is used both as the prompt instruction AND as the validation model.
    """
    reasoning: str = Field(..., description="Detailed step-by-step reasoning for the evaluation and scoring")
    score: float = Field(..., ge=0, le=100, description="Overall call score from 0 to 100")
    strengths: List[StrengthItem] = Field(default_factory=list, description="List of positive behaviors found in the call")
    weaknesses: List[WeaknessItem] = Field(
        default_factory=list,
        description="List of identified weaknesses with issues and deductions",
    )
    summary: str = Field(default="", description="One-paragraph overall assessment of the call")

    # --- RAG Core (Task 65) ---
    qa_pairs: List[QAPairItem] = Field(
        default_factory=list, 
        description="Extract all objection/response pairs found in the call"
    )

    # --- Compliance Flags (Task 66) ---
    opening_ok: bool = Field(default=False, description="Whether the agent used the correct opening")
    closing_ok: bool = Field(default=False, description="Whether the agent used the correct closing")
    dob_verified: bool = Field(default=False, description="Whether Date of Birth was verified (if applicable)")

    # --- Business Intelligence Outcome Fields ---
    primary_outcome: Optional[str] = Field(default=None, description="Primary business outcome of the call")
    outcome_value: Optional[float] = Field(default=None, description="Monetary or numeric value of the outcome")
    follow_up_required: bool = Field(default=False, description="Whether a follow-up action is required")
    follow_up_date: Optional[str] = Field(default=None, description="Suggested follow-up date if applicable (ISO format)")
    campaign_specific_data: Optional[dict] = Field(default=None, description="Campaign-type-specific extracted fields")
    
    # --- Sales Support (Task 4) ---
    raw_sales_data: Optional[dict] = Field(default=None, description="Full raw data from sales evaluations")

    # --- Violations (Task V03) ---
    raw_violations: list = Field(default_factory=list, description="List of violation dicts from LLM, to be processed by apply_violations()")


    @field_validator("strengths", mode="before")
    @classmethod
    def validate_strengths(cls, v):
        if isinstance(v, list):
            new_v = []
            for item in v:
                if isinstance(item, str):
                    new_v.append({"issue": item, "detail": ""})
                else:
                    new_v.append(item)
            return new_v
        return v


EvaluationResult.model_rebuild()


# ===========================
#  Call Schemas
# ===========================

class TranscriptSegmentSchema(BaseModel):
    id: str
    start: float
    end: float
    speaker: str
    text: str
    emotion: Optional[str] = "calm"
    needs_review: bool = False

class CallOutcomeOut(BaseModel):
    """Serialization schema for CallOutcome records."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    call_id: int
    campaign_type: str
    primary_outcome: Optional[str] = None
    outcome_value: Optional[float] = None
    follow_up_required: bool = False
    follow_up_date: Optional[datetime] = None
    agent_talk_time: Optional[float] = None
    customer_talk_time: Optional[float] = None
    talk_ratio: Optional[float] = None
    campaign_specific_data: Optional[dict] = None
    created_at: datetime


class CallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    campaign_id: int
    original_filename: Optional[str] = None
    status: str
    transcript: Optional[List[TranscriptSegmentSchema]] = None
    reasoning: Optional[str] = None
    evaluation_score: Optional[float] = None
    audio_duration: Optional[float] = None
    strengths: Optional[List[StrengthItem]] = None
    weaknesses: Optional[List[WeaknessItem]] = None
    error_message: Optional[str] = None
    
    # Review fields
    overridden_score: Optional[float] = None
    reviewer_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    qa_alarm: bool = False
    qa_alarm_reason: Optional[str] = None
    qa_alarm_evidence: Optional[str] = None

    @field_validator("transcript", "strengths", "weaknesses", mode="before")
    @classmethod
    def validate_json_fields(cls, v):
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                v = []
        
        if isinstance(v, list):
            new_v = []
            for item in v:
                if isinstance(item, str):
                    # Convert legacy string to structured object
                    new_v.append({"issue": item, "detail": ""})
                else:
                    new_v.append(item)
            return new_v
        return v

    created_at: datetime
    processed_at: Optional[datetime] = None

    # Deep Analysis Results
    agent_talk_time: Optional[float] = None
    customer_talk_time: Optional[float] = None
    tags: Optional[List[str]] = None
    lead_status: Optional[str] = None
    is_golden_moment: bool = False
    needs_review: bool = False
    call_summary: Optional[str] = None
    emotion_timeline: Optional[List[dict]] = None

    # Business Intelligence Outcome (One-to-One)
    outcome: Optional[CallOutcomeOut] = None


class CallReviewUpdate(BaseModel):
    overridden_score: Optional[float] = None
    reviewer_notes: Optional[str] = None
    reason: Optional[str] = None


class CallUploadResponse(BaseModel):
    """Returned immediately after a successful upload."""
    call_id: int
    status: str = "pending"
    message: str = "Audio uploaded successfully. Processing has started in the background."


class ScoreOverview(BaseModel):
    average_score: float
    total_calls: int
    pass_rate: float


# ===========================
#  Analytics / Ranking
# ===========================

class EmployeeRanking(BaseModel):
    employee_id: int
    employee_name: str
    employee_code: str
    department: Optional[str]
    avg_score: float
    total_calls: int


class CommonError(BaseModel):
    """A frequently occurring weakness across employees."""
    category: str
    occurrence_count: int
    affected_employees: int
    avg_deduction: float
    example_details: List[str] = Field(default_factory=list)


class EmployeePerformance(BaseModel):
    avg_score: float
    total_calls: int
    rank: str
    skills_matrix: Optional[dict] = None
    cumulative_stats: Optional[AgentMasteryOut] = None
    recent_evaluations: List[CallOut]


class DashboardKPIs(BaseModel):
    total_calls_today: int
    total_calls: int
    avg_qa_score: float
    queue_depth: int
    pass_rate: float
    weekly_trend: List[dict]
    campaign_performance: List[dict]


class SystemMetricPoint(BaseModel):
    time: str
    value: float


class ServiceStatus(BaseModel):
    name: str
    status: str
    latency: str


class SystemMetrics(BaseModel):
    gpu_load: float
    cpu_load: float
    inference_time: int
    calls_processing: int
    queue_depth: int
    uptime: float
    disk_usage: float
    gpu_history: List[SystemMetricPoint]
    inference_history: List[SystemMetricPoint]
    pipeline_latency: float
    services: List[ServiceStatus]


class SystemLogOut(BaseModel):
    id: int
    call_id: Optional[int] = None
    error_type: str
    error_message: str
    severity: Optional[str] = "info"
    resolved: Optional[bool] = False
    created_at: datetime

    class Config:
        from_attributes = True

class Alert(SystemLogOut):
    pass

class AlertCreate(BaseModel):
    call_id: Optional[int] = None
    error_type: str
    error_message: str
    severity: Optional[str] = "info"
    resolved: Optional[bool] = False


# ===========================
#  Sales Evaluation Schemas
# ===========================

class OfferDetail(BaseModel):
    offer_name: str
    presented: bool
    qualifying_questions_asked: bool = False
    branch_followed_correctly: bool = True
    walked_through_enrollment: bool = False
    skip_reason: str = ""


class ViolationDetail(BaseModel):
    flagged: bool
    evidence: str = ""


class SalesViolations(BaseModel):
    policy_misrepresentation: ViolationDetail
    abusive_language: ViolationDetail
    forced_sale: ViolationDetail
    talking_to_another_person: ViolationDetail
    arabic_language: ViolationDetail
    eating_drinking: ViolationDetail
    background_noise: ViolationDetail
    dead_air: ViolationDetail
    hung_up_no_reason: ViolationDetail
    no_callback_after_drop: ViolationDetail
    hold_no_permission: ViolationDetail
    hold_too_long: ViolationDetail
    no_mute_cough: ViolationDetail
    transferred_dead_air: ViolationDetail


class SalesPenalty(BaseModel):
    violation: str
    occurrence: int
    penalty: str


class SalesScoreBreakdown(BaseModel):
    opening: float = 0.0
    script_compliance: float = 0.0
    customer_handling: float = 0.0
    conduct: float = 0.0
    closing: float = 0.0


class SalesEvaluationResult(BaseModel):
    score: float
    summary: str
    reasoning: str = ""
    strengths: List[StrengthItem] = []
    areas_for_improvement: List[str] = []
    opening: dict = {}
    qualifying_questions: dict = {}
    offers_presented: List[str] = []
    offers_skipped_incorrectly: List[str] = []
    offer_details: List[OfferDetail] = []
    closing: dict = {}
    violations: list = []
    penalties: List[SalesPenalty] = []
    score_breakdown: Optional[SalesScoreBreakdown] = None


# ===========================
#  Live Pipeline Schemas
# ===========================

class SessionStartRequest(BaseModel):
    campaign_id: int

class SessionStartResponse(BaseModel):
    session_id: str
    wss_url: str
    reconnect_token: str

# ===========================
#  HR Violations Schemas
# ===========================

class AgentViolationOut(BaseModel):
    id: int
    call_id: int
    violation_id: str
    severity: str
    occurrence: int
    penalty_tier: str
    score_deduction: float
    hr_flagged: bool
    qa_approved: bool
    qa_approved_by_id: Optional[int]
    qa_approved_at: Optional[datetime]
    qa_approval_note: Optional[str]
    hr_approved: bool
    hr_approved_by_id: Optional[int]
    hr_approved_at: Optional[datetime]
    hr_approval_note: Optional[str]
    auto_fail: bool
    evidence: Optional[str]
    timestamp_in_call: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class AgentViolationHistory(BaseModel):
    employee_id: int
    employee_name: str
    total_violations: int
    total_deductions: float
    violations: List[AgentViolationOut]

class ViolationSummaryRow(BaseModel):
    employee_id: int
    employee_name: str
    total_violations: int
    high_count: int
    medium_count: int
    low_count: int
    hr_flagged_count: int
    total_deductions: float
    last_violation_at: Optional[datetime]

class PendingViolationOut(BaseModel):
    violation_id: int
    employee_id: int
    employee_name: str
    team_id: Optional[int]
    team_name: Optional[str]
    call_id: int
    violation_type: str
    severity: str
    occurrence: int
    penalty_tier: str
    evidence: Optional[str]
    created_at: datetime

class ViolationApprovalUpdate(BaseModel):
    note: Optional[str] = None

class ViolationStats(BaseModel):
    total_violations_today: int
    total_violations_this_week: int
    most_common_violation: Optional[str]
    most_common_violation_count: int
    agents_with_hr_flags: int
    auto_fails_today: int


# --- Call Detail UI Support (Task-UI04) ---

class DeductionItem(BaseModel):
    category: str
    deduction: float
    score: float
    max: float

class ViolationItemOut(BaseModel):
    violation_id: str
    severity: str
    timestamp: Optional[str] = None
    evidence: Optional[str] = None

class ScoreOverrideAuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    call_id: int
    reviewer_id: int
    reviewer_name: str
    old_score: Optional[float] = None
    new_score: float
    reason: Optional[str] = None
    created_at: datetime

class CallDetailResponse(CallOut):
    model_config = ConfigDict(from_attributes=True)
    
    ai_summary: Optional[str] = None
    strengths: List[StrengthItem] = []
    deductions: List[DeductionItem] = []
    violations: List[ViolationItemOut] = []
    override_audits: List[ScoreOverrideAuditOut] = []


class BulkCallItemResult(BaseModel):
    filename: str
    success: bool
    call_id: Optional[int] = None
    error: Optional[str] = None


class BulkCallUploadResponse(BaseModel):
    results: List[BulkCallItemResult]
    success_count: int
    failed_count: int
    message: str


# ===========================
#  Team Manager Reporting Schemas
# ===========================

class TeamManagerAlertOut(BaseModel):
    type: str
    message: str
    severity: str
    team_id: Optional[int] = None
    agent_id: Optional[int] = None

class TeamManagerTeamRowOut(BaseModel):
    team_id: int
    team_name: str
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
    leader_id: Optional[int] = None
    leader_name: Optional[str] = None
    agent_count: int
    sales: int
    revenue: float
    conversion_rate: float
    average_qa_score: float
    attendance_rate: float

class TeamManagerDashboardOut(BaseModel):
    total_teams: int
    total_agents: int
    total_sales: int
    total_revenue: float
    average_conversion_rate: float
    average_qa_score: float
    attendance_rate: float
    teams: List[TeamManagerTeamRowOut]
    alerts: List[TeamManagerAlertOut]

class TeamManagerAgentRowOut(BaseModel):
    agent_id: int
    agent_name: str
    email: str
    team_id: int
    team_name: str
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
    sales: int
    revenue: float
    conversion_rate: float
    qa_score: Optional[float] = None
    attendance_rate: Optional[float] = None
    status: str

class TeamManagerAgentDetailOut(BaseModel):
    agent_id: int
    agent_name: str
    email: str
    employee_code: str
    team_id: int
    team_name: str
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
    sales: int
    revenue: float
    conversion_rate: float
    qa_score: Optional[float] = None
    attendance_rate: Optional[float] = None
    status: str
    created_at: datetime

class TeamManagerSalesRow(BaseModel):
    team_id: int
    team_name: str
    sales: int
    total_calls: int

class TeamManagerSalesReportOut(BaseModel):
    teams: List[TeamManagerSalesRow]
    total_sales: int

class TeamManagerRevenueRow(BaseModel):
    team_id: int
    team_name: str
    revenue: float

class TeamManagerRevenueReportOut(BaseModel):
    teams: List[TeamManagerRevenueRow]
    total_revenue: float

class TeamManagerConversionRow(BaseModel):
    team_id: int
    team_name: str
    sales: int
    total_calls: int
    conversion_rate: float

class TeamManagerConversionReportOut(BaseModel):
    teams: List[TeamManagerConversionRow]
    average_conversion_rate: float

class TeamManagerAttendanceRow(BaseModel):
    agent_id: int
    agent_name: str
    attendance_date: str
    status: str
    scheduled_minutes: Optional[int] = None
    worked_minutes: Optional[int] = None
    late_minutes: Optional[int] = None

class TeamManagerAttendanceReportOut(BaseModel):
    records: List[TeamManagerAttendanceRow]
    attendance_rate: float

class TeamManagerKpisOut(BaseModel):
    month: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    period_label: Optional[str] = None
    total_sales: int
    total_revenue: float
    average_qa_score: float
    average_conversion_rate: float
    attendance_rate: float


# ===========================
#  Team Leader Schemas
# ===========================

class TeamLeaderDashboardOut(BaseModel):
    team_count: int
    agent_count: int
    average_qa_score: float
    attendance_rate: float
    sales: int
    revenue: float
    conversion_rate: float
    pending_notes_count: int
    pending_transfer_requests_count: int

class TeamLeaderTeamRowOut(BaseModel):
    team_id: int
    team_name: str
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
    leader_id: Optional[int] = None
    leader_name: Optional[str] = None
    agent_count: int
    sales: int
    revenue: float
    conversion_rate: float
    average_qa_score: float
    attendance_rate: float

class TeamLeaderAgentRowOut(BaseModel):
    agent_id: int
    agent_name: str
    email: str
    team_id: int
    team_name: str
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
    sales: int
    revenue: float
    conversion_rate: float
    qa_score: Optional[float] = None
    attendance_rate: Optional[float] = None
    status: str

class TeamLeaderCallRowOut(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    campaign_id: int
    campaign_name: Optional[str] = None
    status: str
    evaluation_score: Optional[float] = None
    overridden_score: Optional[float] = None
    audio_duration: Optional[float] = None
    created_at: datetime

class TeamLeaderKpisOut(BaseModel):
    month: str
    total_sales: int
    total_revenue: float
    average_qa_score: float
    average_conversion_rate: float
    attendance_rate: float


# ===========================
#  KPI Threshold Config Schemas
# ===========================

class KpiThresholdCreate(BaseModel):
    team_id: Optional[int] = None
    campaign_id: Optional[int] = None
    kpi_key: str
    kpi_label: Optional[str] = None
    threshold_type: str  # MINIMUM, MAXIMUM
    target_value: float
    is_active: bool = True

class KpiThresholdUpdate(BaseModel):
    kpi_label: Optional[str] = None
    threshold_type: Optional[str] = None
    target_value: Optional[float] = None
    is_active: Optional[bool] = None

class KpiThresholdOut(BaseModel):
    id: int
    team_id: Optional[int] = None
    campaign_id: Optional[int] = None
    kpi_key: str
    kpi_label: str
    threshold_type: str
    target_value: float
    is_active: bool
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===========================
#  Agent Transfer Requests Schemas
# ===========================

class AgentTransferRequestCreate(BaseModel):
    agent_id: int
    from_team_id: int
    to_team_id: Optional[int] = None
    reason: str

class AgentTransferRequestOut(BaseModel):
    id: int
    agent_id: int
    agent_name: Optional[str] = None
    from_team_id: int
    from_team_name: Optional[str] = None
    to_team_id: Optional[int] = None
    to_team_name: Optional[str] = None
    requested_by_id: int
    requested_by_name: Optional[str] = None
    reviewed_by_id: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    status: str
    reason: str
    review_note: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ===========================
#  Role Notes Schemas
# ===========================

class RoleNoteCreate(BaseModel):
    recipient_id: Optional[int] = None
    recipient_role: Optional[str] = None
    visibility: str = "INTERNAL"
    team_id: Optional[int] = None
    campaign_id: Optional[int] = None
    employee_id: Optional[int] = None
    call_id: Optional[int] = None
    parent_note_id: Optional[int] = None
    title: str
    body: str
    note_type: str = "GENERAL"
    priority: str = "NORMAL"
    kpi_key: Optional[str] = None
    kpi_label: Optional[str] = None
    current_value: Optional[float] = None
    target_value: Optional[float] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_role_note(self):
        if not self.title or not self.title.strip():
            raise ValueError("title is required")
        if not self.body or not self.body.strip():
            raise ValueError("body is required")
        if self.recipient_id is not None and self.recipient_role is not None:
            raise ValueError("provide recipient_id or recipient_role, not both")
        if self.note_type in {"KPI_ALERT", "KPI_FOLLOW_UP"}:
            if self.team_id is None:
                raise ValueError("team_id is required for KPI notes")
            required = [self.kpi_key, self.kpi_label, self.current_value, self.target_value]
            if any(value is None for value in required):
                raise ValueError("KPI fields are required for KPI notes")
        return self

class RoleNoteUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    priority: Optional[str] = None

class RoleNoteStatusUpdate(BaseModel):
    status: str

class RoleNoteRecipientOut(BaseModel):
    id: int
    name: str
    role: str
    reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class RoleNoteOut(BaseModel):
    id: int
    sender_id: int
    sender_name: Optional[str] = None
    recipient_id: Optional[int] = None
    recipient_name: Optional[str] = None
    recipient_role: Optional[str] = None
    visibility: Optional[str] = None
    team_id: Optional[int] = None
    team_name_snapshot: Optional[str] = None
    campaign_id: Optional[int] = None
    campaign_name_snapshot: Optional[str] = None
    employee_id: Optional[int] = None
    agent_name_snapshot: Optional[str] = None
    call_id: Optional[int] = None
    parent_note_id: Optional[int] = None
    title: str
    body: str
    note_type: str
    priority: str
    status: str
    kpi_key: Optional[str] = None
    kpi_label: Optional[str] = None
    current_value: Optional[float] = None
    target_value: Optional[float] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    read_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolved_by_id: Optional[int] = None
    resolved_by_name: Optional[str] = None
    deleted_at: Optional[datetime] = None
    deleted_by_id: Optional[int] = None
    delete_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class RoleNoteThreadOut(BaseModel):
    note: RoleNoteOut
    replies: List[RoleNoteOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ===========================
#  Operations Schemas
# ===========================

class OpsFilters(BaseModel):
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    campaign_id: Optional[int] = None
    department: Optional[str] = None
    segment: Optional[str] = None
    limit: int = 50
    offset: int = 0

class OpsMetricSummary(BaseModel):
    metric: str
    value: float
    target_value: Optional[float] = None
    delta: Optional[float] = None
    trend: str
    status: str

class OpsCampaignRow(BaseModel):
    campaign_id: int
    campaign_name: str
    total_calls: int
    attends: int
    sales: int
    revenue: float
    conversion_rate: float
    avg_qa_score: float
    violations_count: int

class OpsAttendanceRow(BaseModel):
    employee_id: int
    employee_name: str
    employee_code: str
    attendance_date: date
    status: str
    scheduled_minutes: Optional[int] = None
    worked_minutes: Optional[int] = None
    late_minutes: Optional[int] = None

class OpsTopViolationRow(BaseModel):
    violation_id: str
    count: int
    total_deductions: float

class OpsQAOverviewOut(BaseModel):
    avg_score: float
    reviewed_calls: int
    pending_reviews: int
    qa_alarm_count: int
    top_violations: List[OpsTopViolationRow]

class OpsViolationsOverviewOut(BaseModel):
    total_violations: int
    high_count: int
    medium_count: int
    low_count: int
    hr_flagged_count: int
    total_deductions: float

class OpsAlertRow(BaseModel):
    id: int
    error_type: str
    error_message: str
    severity: str
    resolved: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OpsDashboardOut(BaseModel):
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    totals: List[OpsMetricSummary]
    campaigns: List[OpsCampaignRow]
    alerts: List[OpsAlertRow]
    segments: List[str]
    updated_at: datetime


