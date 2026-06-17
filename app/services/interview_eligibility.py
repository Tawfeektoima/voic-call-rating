from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import InterviewCandidate


@dataclass
class CandidateEligibilityResult:
    candidate: InterviewCandidate | None
    should_reuse_candidate: bool
    duplicate_recent: bool


def parse_candidate_date_of_birth(date_of_birth: str | None) -> date | None:
    value = str(date_of_birth or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Date of birth must use YYYY-MM-DD format.") from exc


def validate_candidate_age(date_of_birth: date | None) -> None:
    if date_of_birth is None:
        return
    today = date.today()
    age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
    if age < 18:
        raise HTTPException(status_code=403, detail="Candidate is under 18 years old. Application rejected.")


def resolve_public_candidate_eligibility(
    db: Session,
    *,
    job_id: int,
    normalized_email: str,
    normalized_phone: str | None,
    national_id_hash: str | None,
) -> CandidateEligibilityResult:
    settings = get_settings()
    conditions = [InterviewCandidate.contact_email_normalized == normalized_email]
    if normalized_phone:
        conditions.append(InterviewCandidate.phone_normalized == normalized_phone)
    if national_id_hash:
        conditions.append(InterviewCandidate.national_id_hash == national_id_hash)

    existing_candidate = (
        db.query(InterviewCandidate)
        .filter(or_(*conditions))
        .order_by(InterviewCandidate.applied_at.desc(), InterviewCandidate.id.desc())
        .first()
    )
    if existing_candidate is None:
        return CandidateEligibilityResult(candidate=None, should_reuse_candidate=False, duplicate_recent=False)

    now = datetime.now(timezone.utc)
    completed_at = existing_candidate.completed_at
    if completed_at is not None:
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)
        days_since_completion = (now - completed_at).days
        if days_since_completion < settings.INTERVIEW_APPLICATION_COOLDOWN_DAYS:
            days_left = settings.INTERVIEW_APPLICATION_COOLDOWN_DAYS - days_since_completion
            raise HTTPException(
                status_code=403,
                detail=f"You have recently completed an interview. Please wait {max(days_left, 1)} days before applying again.",
            )

    applied_at = existing_candidate.applied_at
    if applied_at.tzinfo is None:
        applied_at = applied_at.replace(tzinfo=timezone.utc)
    duplicate_recent = (now - applied_at).total_seconds() < settings.INTERVIEW_DUPLICATE_WINDOW_SECONDS

    same_job = existing_candidate.job_id == job_id
    return CandidateEligibilityResult(
        candidate=existing_candidate,
        should_reuse_candidate=same_job or duplicate_recent,
        duplicate_recent=duplicate_recent,
    )
