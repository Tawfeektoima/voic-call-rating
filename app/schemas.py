"""
Pydantic schemas for request/response validation and the Groq structured output.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict, field_validator
import json


# ===========================
#  Employee Schemas
# ===========================

class EmployeeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6)
    role: str = "AGENT"
    department: Optional[str] = None
    employee_code: str = Field(..., min_length=1, max_length=50)
    avatar: Optional[str] = None
    tier: str = "bronze"
    skills: Optional[dict] = None
    emotion_history: Optional[List[float]] = None
    phone_number: Optional[str] = None






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
    role: str
    department: Optional[str]
    employee_code: str
    avatar: Optional[str]
    tier: str
    skills: Optional[dict]
    emotion_history: Optional[List[float]]
    phone_number: Optional[str] = None
    agent_tenure_days: Optional[int] = 0
    mastery_stats: Optional[AgentMasteryOut] = None
    created_at: datetime


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

class UserLogin(BaseModel):
    email: str
    password: str

class MeResponse(BaseModel):
    id: int
    name: str
    campaign_id: int
    role: str

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
    call_id: int
    violation_type: str
    severity: str
    occurrence: int
    penalty_tier: str
    evidence: Optional[str]
    created_at: datetime

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
