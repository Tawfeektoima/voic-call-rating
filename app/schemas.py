"""
Pydantic schemas for request/response validation and the Groq structured output.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


# ===========================
#  Employee Schemas
# ===========================

class EmployeeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    department: Optional[str] = None
    employee_code: str = Field(..., min_length=1, max_length=50)


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    department: Optional[str]
    employee_code: str
    created_at: datetime


# ===========================
#  Campaign Schemas
# ===========================

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    evaluation_prompt: str = Field(..., min_length=10)


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    evaluation_prompt: str
    created_at: datetime


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

class CallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    campaign_id: int
    original_filename: Optional[str]
    status: str
    transcript: Optional[str]
    evaluation_score: Optional[float]
    audio_duration: Optional[float]
    weaknesses: Optional[List[dict]]
    error_message: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]


class CallUploadResponse(BaseModel):
    """Returned immediately after a successful upload."""
    call_id: int
    status: str = "pending"
    message: str = "Audio uploaded successfully. Processing has started in the background."


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
