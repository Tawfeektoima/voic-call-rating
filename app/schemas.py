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
    mastery_stats: Optional[AgentMasteryOut] = None
    created_at: datetime


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

class WeaknessItem(BaseModel):
    """A single weakness found during the call evaluation."""
    issue: str = Field(..., description="Short label for the problem, e.g. 'Greeting', 'Hold Etiquette'")
    detail: str = Field(..., description="Explanation of what was wrong")
    deduction: float = Field(..., ge=0, description="Points deducted for this weakness")


class EvaluationResult(BaseModel):
    """
    Strict schema that Groq must return.
    This is used both as the prompt instruction AND as the validation model.
    """
    reasoning: str = Field(..., description="Detailed step-by-step reasoning for the evaluation and scoring")
    score: float = Field(..., ge=0, le=100, description="Overall call score from 0 to 100")
    strengths: List[str] = Field(default_factory=list, description="List of positive behaviors found in the call")
    weaknesses: List[WeaknessItem] = Field(
        default_factory=list,
        description="List of identified weaknesses with issues and deductions",
    )
    summary: str = Field(default="", description="One-paragraph overall assessment of the call")


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

class CallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    campaign_id: int
    original_filename: Optional[str]
    status: str
    transcript: Optional[List[TranscriptSegmentSchema]] = None
    reasoning: Optional[str] = None
    evaluation_score: Optional[float] = None
    audio_duration: Optional[float] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[dict]] = None
    error_message: Optional[str] = None
    
    # Review fields
    overridden_score: Optional[float] = None
    reviewer_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    @field_validator("transcript", "strengths", "weaknesses", mode="before")
    @classmethod
    def validate_json_fields(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v

    created_at: datetime
    processed_at: Optional[datetime] = None

    # Deep Analysis Results
    agent_talk_time: Optional[float] = None
    customer_talk_time: Optional[float] = None
    tags: Optional[List[str]] = None
    lead_status: Optional[str] = None
    is_golden_moment: bool = False
    call_summary: Optional[str] = None
    emotion_timeline: Optional[List[dict]] = None


class CallReviewUpdate(BaseModel):
    overridden_score: Optional[float] = None
    reviewer_notes: Optional[str] = None


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
