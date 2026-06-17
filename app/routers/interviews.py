import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Optional

import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.database import get_db
from app.models import (
    Employee,
    EmployeeStatus,
    InterviewAnswer,
    InterviewCandidate,
    InterviewCandidateDocument,
    InterviewMcqSubmission,
    InterviewCandidateStatus,
    InterviewJob,
    InterviewJobStatus,
    InterviewQuestion,
    InterviewQuestionSource,
    InterviewSession,
    InterviewSessionStatus,
    Team,
    Campaign,
    UserRole,
    InterviewWorkflowEvent,
)
from app.permissions import Permission, has_permission, normalize_role_value, require_permission
from app.routers.auth import get_current_user
from app.schemas import (
    InterviewAnswerOut,
    InterviewCandidateCreate,
    InterviewCandidateBulkActionOut,
    InterviewCandidateBulkActionRequest,
    InterviewCandidateIdentitySummaryOut,
    InterviewCandidateConversionOut,
    InterviewCandidateDecisionUpdate,
    InterviewCandidateDocumentOut,
    InterviewCandidateInviteOut,
    InterviewCandidateInviteRequest,
    InterviewCandidateOnboardingReadinessOut,
    InterviewEmployeeMatchOut,
    InterviewCandidateOut,
    InterviewCandidateConvertRequest,
    InterviewCandidateRecommendationOut,
    InterviewCandidateReviewAnswerOut,
    InterviewCandidateReviewMcqSummaryOut,
    InterviewCandidateReviewMetricsOut,
    InterviewCandidateReviewOut,
    InterviewMcqQuestionOut,
    InterviewMcqReviewOut,
    InterviewMcqSubmissionOut,
    InterviewJobCreate,
    InterviewJobOut,
    InterviewRetentionPurgeOut,
    InterviewRetentionPurgeRequest,
    InterviewJobUpdate,
    CandidateTimelineEventOut,
)
from app.services.audit import log_audit_event
from app.services.employee_identity import (
    generate_employee_email,
    hash_national_id,
    normalize_contact_email,
    normalize_employee_code,
    normalize_employee_email,
    validate_employee_code,
)
from app.services.interview_documents import extract_text_from_document
from app.services.interview_file_crypto import decrypt_text_value, encrypt_file_in_place, encrypt_text_value
from app.services.interview_identity import (
    generate_interview_session_token,
    hash_interview_session_token,
    national_id_last4,
    normalize_interview_email,
    normalize_interview_phone,
)
from app.services.interview_mcq import (
    DEFAULT_INTERVIEW_MCQ_BANK,
    format_mcq_results_for_review,
    get_safe_mcq_bank,
    normalize_mcq_bank,
)
from app.services.interview_question_builder import build_hybrid_interview_questions
from app.services.public_links import build_interview_invite_url
from app.services.interview_retention import purge_archived_interview_candidates
from app.services.interview_workflow import create_interview_workflow_event
from app.security import get_password_hash, validate_password_strength

router = APIRouter(prefix="/api/hr/interviews", tags=["HR Interviews"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_active_staff(current_user: Employee) -> None:
    if (current_user.status or "").lower() != EmployeeStatus.ACTIVE.value:
        raise HTTPException(status_code=403, detail=f"Account is {current_user.status}")


def _serialize_enum(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _mask_export_email(email: str | None) -> str:
    if not email:
        return ""
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    if len(local) <= 2:
        masked_local = local[:1] + "*"
    else:
        masked_local = local[:2] + "*" * max(len(local) - 2, 1)
    return f"{masked_local}@{domain}"


def _mask_export_phone(phone: str | None) -> str:
    if not phone:
        return ""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not digits:
        return ""
    keep = digits[-4:] if len(digits) >= 4 else digits
    return f"{'*' * max(len(digits) - len(keep), 4)}{keep}"


def _mask_candidate_email(email: str | None) -> str | None:
    if not email:
        return None
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    if len(local) <= 2:
        masked_local = local[:1] + "*"
    else:
        masked_local = local[:2] + "*" * max(len(local) - 2, 1)
    return f"{masked_local}@{domain}"


def _suggest_employee_code(candidate: InterviewCandidate) -> str:
    candidate_code = normalize_employee_code(str(candidate.id))
    return candidate_code or str(candidate.id)


def _build_candidate_onboarding_readiness(
    db: Session,
    candidate: InterviewCandidate,
) -> InterviewCandidateOnboardingReadinessOut:
    job_title = candidate.job.title if candidate.job else None
    suggested_employee_code = _suggest_employee_code(candidate)
    suggested_company_email = normalize_employee_email(None, suggested_employee_code)
    blocking_reasons: list[str] = []
    blocking_categories: list[str] = []
    existing_employee_match = None

    if candidate.status != InterviewCandidateStatus.ACCEPTED:
        blocking_reasons.append("Candidate must be accepted before onboarding.")
        blocking_categories.append("status")

    if candidate.converted_employee_id is not None:
        blocking_reasons.append("Candidate is already converted to an employee.")
        blocking_categories.append("already_converted")
        existing_employee = db.query(Employee).filter(Employee.id == candidate.converted_employee_id).first()
        if existing_employee is not None:
            existing_employee_match = InterviewEmployeeMatchOut(
                employee_id=existing_employee.id,
                employee_code=existing_employee.employee_code,
                employee_email=existing_employee.email,
                role=_serialize_enum(existing_employee.role),
                status=existing_employee.status,
            )

    if not candidate.full_name.strip():
        blocking_reasons.append("Candidate full name is required.")

    if not candidate.contact_email_normalized:
        blocking_reasons.append("Candidate contact email is required.")

    if db.query(Employee).filter(Employee.employee_code == suggested_employee_code).first() is not None:
        blocking_reasons.append(f"Employee code '{suggested_employee_code}' is already registered.")
        blocking_categories.append("employee_code")
        if existing_employee_match is None:
            employee = db.query(Employee).filter(Employee.employee_code == suggested_employee_code).first()
            if employee is not None:
                existing_employee_match = InterviewEmployeeMatchOut(
                    employee_id=employee.id,
                    employee_code=employee.employee_code,
                    employee_email=employee.email,
                    role=_serialize_enum(employee.role),
                    status=employee.status,
                )

    if db.query(Employee).filter(func.lower(Employee.email) == suggested_company_email.lower()).first() is not None:
        blocking_reasons.append(f"Generated company email '{suggested_company_email}' is already registered.")
        blocking_categories.append("email")
        if existing_employee_match is None:
            employee = db.query(Employee).filter(func.lower(Employee.email) == suggested_company_email.lower()).first()
            if employee is not None:
                existing_employee_match = InterviewEmployeeMatchOut(
                    employee_id=employee.id,
                    employee_code=employee.employee_code,
                    employee_email=employee.email,
                    role=_serialize_enum(employee.role),
                    status=employee.status,
                )

    if candidate.national_id_hash and db.query(Employee).filter(Employee.national_id_hash == candidate.national_id_hash).first() is not None:
        blocking_reasons.append("Candidate national ID is already linked to an employee.")
        blocking_categories.append("national_id")

    return InterviewCandidateOnboardingReadinessOut(
        candidate_id=candidate.id,
        status=_serialize_enum(candidate.status),
        is_ready=not blocking_reasons,
        blocking_reasons=blocking_reasons,
        blocking_categories=blocking_categories,
        suggested_employee_code=suggested_employee_code,
        suggested_company_email=suggested_company_email,
        candidate_identity_summary=InterviewCandidateIdentitySummaryOut(
            candidate_id=candidate.id,
            full_name=candidate.full_name,
            job_id=candidate.job_id,
            job_title=job_title,
            department=candidate.job.department if candidate.job else None,
            status=_serialize_enum(candidate.status),
            phone_last4=candidate.phone_number[-4:] if candidate.phone_number else None,
            national_id_last4=candidate.national_id_last4,
            contact_email_masked=_mask_candidate_email(candidate.contact_email_normalized),
            converted_employee_id=candidate.converted_employee_id,
        ),
        existing_employee_match=existing_employee_match,
    )


def _serialize_candidate_with_submission(
    candidate: InterviewCandidate,
    latest_submission: Optional[InterviewMcqSubmission] = None,
) -> InterviewCandidateOut:
    return InterviewCandidateOut(
        id=candidate.id,
        job_id=candidate.job_id,
        full_name=candidate.full_name,
        contact_email=candidate.contact_email,
        contact_email_normalized=candidate.contact_email_normalized,
        phone_number=candidate.phone_number,
        phone_normalized=candidate.phone_normalized,
        national_id_last4=candidate.national_id_last4,
        status=_serialize_enum(candidate.status),
        final_score=candidate.final_score,
        global_percentile=candidate.global_percentile,
        applied_at=candidate.applied_at,
        completed_at=candidate.completed_at,
        archived_at=candidate.archived_at,
        converted_employee_id=candidate.converted_employee_id,
        created_by_id=candidate.created_by_id,
        mcq_score=latest_submission.score if latest_submission else None,
        mcq_total_questions=latest_submission.total_questions if latest_submission else None,
        mcq_percentage=latest_submission.percentage if latest_submission else None,
        mcq_completed_at=latest_submission.completed_at if latest_submission else None,
    )


def _resolve_interview_evaluation_state(answers: list[InterviewAnswer]) -> str:
    if any(answer.status == "failed" for answer in answers):
        return "Needs review"
    if any(answer.status in {"pending", "processing"} for answer in answers):
        return "Running"
    if answers:
        return "Ready"
    return "Not started"


def _build_candidate_recommendation(
    candidate: InterviewCandidate,
    answers: list[InterviewAnswer],
    latest_submission: Optional[InterviewMcqSubmission],
) -> InterviewCandidateRecommendationOut:
    answer_scores = [answer.overall_score for answer in answers if answer.overall_score is not None]
    average_answer_score = round(sum(answer_scores) / len(answer_scores), 1) if answer_scores else None
    interview_signal_score = candidate.final_score if candidate.final_score is not None else average_answer_score
    mcq_percentage = latest_submission.percentage if latest_submission is not None else None
    evaluation_state = _resolve_interview_evaluation_state(answers)

    strengths: list[str] = []
    concerns: list[str] = []
    weighted_components: list[tuple[float, float]] = []

    if interview_signal_score is not None:
        weighted_components.append((float(interview_signal_score), 0.7))
        if interview_signal_score >= 80:
            strengths.append("Interview responses show strong communication and answer quality.")
        elif interview_signal_score >= 65:
            strengths.append("Interview responses are generally within the expected range.")
        elif interview_signal_score < 55:
            concerns.append("Interview answer quality is below the current hiring bar.")
    else:
        concerns.append("Interview answers have not finished scoring yet.")

    if mcq_percentage is not None:
        weighted_components.append((float(mcq_percentage), 0.3))
        if mcq_percentage >= 75:
            strengths.append("Written assessment performance is above target.")
        elif mcq_percentage < 55:
            concerns.append("Written assessment score is below target.")
    else:
        concerns.append("Written assessment has not been submitted yet.")

    if latest_submission is not None:
        personality_breakdown = (latest_submission.breakdown or {}).get("traits") or {}
        if personality_breakdown:
            top_trait = max(personality_breakdown.items(), key=lambda item: item[1])
            if top_trait[0] == "collaborative" and top_trait[1] > 0:
                strengths.append("Situational choices lean collaborative.")
            if top_trait[0] in {"aggressive", "impulsive"} and top_trait[1] > 0:
                concerns.append(f"Situational choices skew {top_trait[0].replace('_', ' ')}.")

    if evaluation_state == "Running":
        concerns.append("One or more answers are still being evaluated.")
    elif evaluation_state == "Needs review":
        concerns.append("One or more answers failed automated evaluation and need manual review.")

    unique_strengths = list(dict.fromkeys(strengths))
    unique_concerns = list(dict.fromkeys(concerns))
    composite_score: Optional[float] = None
    if weighted_components:
        total_weight = sum(weight for _score, weight in weighted_components)
        composite_score = round(sum(score * weight for score, weight in weighted_components) / total_weight, 1)

    if evaluation_state in {"Running", "Needs review"} and composite_score is not None:
        label = "Provisional Review"
        rationale = "Interview evaluation is not fully complete yet, so the recommendation is provisional."
    elif composite_score is None:
        label = "Pending Review"
        rationale = "Not enough evaluated interview data is available yet to produce a recommendation."
    elif composite_score >= 82:
        label = "Strong Hire"
        rationale = "The candidate is performing strongly across interview and written assessment signals."
    elif composite_score >= 70:
        label = "Proceed"
        rationale = "The candidate is meeting the current bar with a balanced interview and assessment profile."
    elif composite_score >= 55:
        label = "Hold"
        rationale = "The candidate has mixed signals and would benefit from deeper review before a final decision."
    else:
        label = "Do Not Proceed"
        rationale = "Current interview and assessment signals are below the expected bar for this role."

    return InterviewCandidateRecommendationOut(
        label=label,
        score=composite_score,
        rationale=rationale,
        strengths=unique_strengths,
        concerns=unique_concerns,
    )


def _load_job_or_404(db: Session, job_id: int) -> InterviewJob:
    job = db.query(InterviewJob).filter(InterviewJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Interview job not found.")
    return job


def _load_candidate_or_404(db: Session, candidate_id: int) -> InterviewCandidate:
    candidate = db.query(InterviewCandidate).filter(InterviewCandidate.id == candidate_id).first()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Interview candidate not found.")
    return candidate


def _parse_candidate_status(status: str | None) -> InterviewCandidateStatus:
    try:
        return InterviewCandidateStatus(str(status or InterviewCandidateStatus.APPLIED.value).strip().lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid interview candidate status.") from exc


def _validate_job_scope(db: Session, team_id: Optional[int], campaign_id: Optional[int]) -> tuple[Optional[Team], Optional[Campaign]]:
    team = None
    campaign = None
    if team_id is not None:
        team = db.query(Team).filter(Team.id == team_id).first()
        if team is None:
            raise HTTPException(status_code=404, detail="Team not found.")
        if not team.is_active:
            raise HTTPException(status_code=400, detail="Selected team must be active.")
    if campaign_id is not None:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign is None:
            raise HTTPException(status_code=404, detail="Campaign not found.")
    if team is not None and campaign is not None and team.campaign_id not in (None, campaign.id):
        raise HTTPException(status_code=400, detail="Selected campaign must match the team's campaign.")
    return team, campaign


def _parse_job_status(status: str | None) -> InterviewJobStatus:
    try:
        return InterviewJobStatus(str(status or InterviewJobStatus.DRAFT.value).strip().lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid interview job status.") from exc


@router.post("/jobs", response_model=InterviewJobOut)
def create_interview_job(
    payload: InterviewJobCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.MANAGE_INTERVIEW_JOBS, detail="Only HR managers and admins can manage interview jobs.")
    _validate_job_scope(db, payload.team_id, payload.campaign_id)

    job = InterviewJob(
        title=payload.title.strip(),
        description=payload.description.strip(),
        department=(payload.department or None),
        team_id=payload.team_id,
        campaign_id=payload.campaign_id,
        status=_parse_job_status(payload.status),
        base_questions=[item.strip() for item in payload.base_questions if str(item).strip()],
        scoring_weights=payload.scoring_weights,
        mcq_enabled=payload.mcq_enabled,
        mcq_questions=normalize_mcq_bank(payload.mcq_questions) if payload.mcq_questions else [],
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    log_audit_event(
        db=db,
        action="INTERVIEW_JOB_CREATE",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"InterviewJob #{job.id}",
        after_state=f"title={job.title}; status={job.status.value}",
        reason="Interview job created",
        success=True,
    )
    return job


@router.get("/jobs", response_model=list[InterviewJobOut])
def list_interview_jobs(
    status: Optional[str] = Query(None),
    team_id: Optional[int] = Query(None, ge=1),
    campaign_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.MANAGE_INTERVIEW_JOBS, detail="Only HR managers and admins can view interview jobs.")
    query = db.query(InterviewJob).order_by(InterviewJob.created_at.desc())
    if status:
        query = query.filter(InterviewJob.status == _parse_job_status(status))
    if team_id is not None:
        query = query.filter(InterviewJob.team_id == team_id)
    if campaign_id is not None:
        query = query.filter(InterviewJob.campaign_id == campaign_id)
    return query.all()


@router.get("/mcq-bank/default", response_model=list[InterviewMcqQuestionOut])
def get_default_interview_mcq_bank(
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.MANAGE_INTERVIEW_JOBS, detail="Only HR managers and admins can view interview jobs.")
    return normalize_mcq_bank(DEFAULT_INTERVIEW_MCQ_BANK)


@router.put("/jobs/{job_id}", response_model=InterviewJobOut)
def update_interview_job(
    job_id: int,
    payload: InterviewJobUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.MANAGE_INTERVIEW_JOBS, detail="Only HR managers and admins can manage interview jobs.")
    job = _load_job_or_404(db, job_id)

    new_team_id = payload.team_id if payload.team_id is not None else job.team_id
    new_campaign_id = payload.campaign_id if payload.campaign_id is not None else job.campaign_id
    _validate_job_scope(db, new_team_id, new_campaign_id)

    before_state = f"title={job.title}; status={_serialize_enum(job.status)}"
    if payload.title is not None:
        job.title = payload.title.strip()
    if payload.description is not None:
        job.description = payload.description.strip()
    if payload.department is not None:
        job.department = payload.department
    if payload.team_id is not None:
        job.team_id = payload.team_id
    if payload.campaign_id is not None:
        job.campaign_id = payload.campaign_id
    if payload.status is not None:
        job.status = _parse_job_status(payload.status)
    if payload.base_questions is not None:
        job.base_questions = [item.strip() for item in payload.base_questions if str(item).strip()]
    if payload.scoring_weights is not None:
        job.scoring_weights = payload.scoring_weights
    if payload.mcq_enabled is not None:
        job.mcq_enabled = payload.mcq_enabled
    if payload.mcq_questions is not None:
        job.mcq_questions = normalize_mcq_bank(payload.mcq_questions)
    job.updated_by_id = current_user.id
    db.commit()
    db.refresh(job)
    log_audit_event(
        db=db,
        action="INTERVIEW_JOB_UPDATE",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"InterviewJob #{job.id}",
        before_state=before_state,
        after_state=f"title={job.title}; status={job.status.value}",
        reason="Interview job updated",
        success=True,
    )
    return job


@router.post("/candidates", response_model=InterviewCandidateOut)
def create_interview_candidate(
    payload: InterviewCandidateCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.MANAGE_INTERVIEW_CANDIDATES, detail="Only HR managers and admins can manage interview candidates.")
    job = _load_job_or_404(db, payload.job_id)
    if job.status == InterviewJobStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Cannot add candidates to a closed interview job.")

    try:
        normalized_email = normalize_interview_email(payload.contact_email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    normalized_phone = normalize_interview_phone(payload.phone_number)
    hashed_national_id = hash_national_id(payload.national_id)

    existing = (
        db.query(InterviewCandidate)
        .filter(
            InterviewCandidate.job_id == payload.job_id,
            func.lower(InterviewCandidate.contact_email_normalized) == normalized_email,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Candidate email already exists for this interview job.")

    candidate = InterviewCandidate(
        job_id=payload.job_id,
        full_name=payload.full_name.strip(),
        contact_email=normalized_email,
        contact_email_normalized=normalized_email,
        phone_number=payload.phone_number,
        phone_normalized=normalized_phone,
        national_id_hash=hashed_national_id,
        national_id_last4=national_id_last4(payload.national_id),
        status=InterviewCandidateStatus.APPLIED,
        created_by_id=current_user.id,
    )
    db.add(candidate)
    db.flush()
    create_interview_workflow_event(
        db,
        candidate_id=candidate.id,
        actor_id=current_user.id,
        event_type="CANDIDATE_CREATED",
        to_status=InterviewCandidateStatus.APPLIED.value,
        note="Candidate added by HR",
        event_payload={"job_id": payload.job_id},
    )
    db.commit()
    db.refresh(candidate)
    log_audit_event(
        db=db,
        action="INTERVIEW_CANDIDATE_CREATE",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"InterviewCandidate #{candidate.id}",
        reason="Interview candidate created",
        success=True,
    )
    return candidate


def validate_and_transition_candidate_status(
    db: Session,
    candidate: InterviewCandidate,
    to_status: InterviewCandidateStatus,
    actor: Employee | None = None,
    note: str | None = None,
    send_email: bool = False,
) -> InterviewCandidate:
    from_status = candidate.status
    if from_status == to_status:
        return candidate  # No transition needed

    VALID_TRANSITIONS = {
        InterviewCandidateStatus.APPLIED: {
            InterviewCandidateStatus.SCREENING,
            InterviewCandidateStatus.INTERVIEWING,
            InterviewCandidateStatus.REJECTED,
            InterviewCandidateStatus.ARCHIVED,
        },
        InterviewCandidateStatus.SCREENING: {
            InterviewCandidateStatus.INTERVIEWING,
            InterviewCandidateStatus.REJECTED,
            InterviewCandidateStatus.ARCHIVED,
        },
        InterviewCandidateStatus.INTERVIEWING: {
            InterviewCandidateStatus.EVALUATED,
            InterviewCandidateStatus.REJECTED,
            InterviewCandidateStatus.ARCHIVED,
        },
        InterviewCandidateStatus.EVALUATED: {
            InterviewCandidateStatus.SHORTLISTED,
            InterviewCandidateStatus.ACCEPTED,
            InterviewCandidateStatus.REJECTED,
            InterviewCandidateStatus.ARCHIVED,
        },
        InterviewCandidateStatus.SHORTLISTED: {
            InterviewCandidateStatus.ACCEPTED,
            InterviewCandidateStatus.REJECTED,
            InterviewCandidateStatus.ARCHIVED,
        },
        InterviewCandidateStatus.ACCEPTED: {
            InterviewCandidateStatus.REJECTED,
            InterviewCandidateStatus.ARCHIVED,
        },
        InterviewCandidateStatus.REJECTED: {
            InterviewCandidateStatus.APPLIED,
            InterviewCandidateStatus.SCREENING,
            InterviewCandidateStatus.SHORTLISTED,
            InterviewCandidateStatus.ACCEPTED,
            InterviewCandidateStatus.ARCHIVED,
        },
        InterviewCandidateStatus.ARCHIVED: {
            InterviewCandidateStatus.APPLIED,  # via restore
            InterviewCandidateStatus.ACCEPTED, # via convert
        },
    }

    allowed = VALID_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid candidate status transition from {from_status.value} to {to_status.value}."
        )

    # Apply state changes
    candidate.status = to_status
    if to_status == InterviewCandidateStatus.ARCHIVED:
        candidate.archived_at = _utcnow()
    elif to_status == InterviewCandidateStatus.ACCEPTED:
        candidate.completed_at = candidate.completed_at or _utcnow()

    # Log workflow event
    event_type = f"CANDIDATE_{to_status.value.upper()}"
    create_interview_workflow_event(
        db,
        candidate_id=candidate.id,
        actor_id=actor.id if actor else None,
        event_type=event_type,
        from_status=from_status.value,
        to_status=to_status.value,
        note=note,
    )

    # Log audit event
    actor_id = actor.id if actor else None
    actor_email = actor.email if actor else "system"
    action_name = f"INTERVIEW_CANDIDATE_{to_status.value.upper()}"
    if to_status == InterviewCandidateStatus.INTERVIEWING:
        action_name = "INTERVIEW_CANDIDATE_INVITE"

    log_audit_event(
        db=db,
        action=action_name,
        actor_id=actor_id,
        actor_email=actor_email,
        target=f"InterviewCandidate #{candidate.id}",
        before_state=from_status.value,
        after_state=to_status.value,
        reason=note or f"Candidate transitioned to {to_status.value}",
        success=True,
    )

    # Handle automatic notification dispatch
    if send_email:
        template_map = {
            InterviewCandidateStatus.ACCEPTED: "accepted",
            InterviewCandidateStatus.REJECTED: "rejected",
            InterviewCandidateStatus.ARCHIVED: "archived",
            InterviewCandidateStatus.INTERVIEWING: "interview_invite",
        }
        template = template_map.get(to_status)
        if template:
            context = {"job_title": candidate.job.title if candidate.job else "Position"}
            
            # For interview_invite, we must supply invite_url and expires_at
            if template == "interview_invite":
                session = db.query(InterviewSession).filter(
                    InterviewSession.candidate_id == candidate.id
                ).order_by(InterviewSession.created_at.desc()).first()
                
                # If no session exists, we auto-create one (just like invite endpoint)
                if not session:
                    session_token = generate_interview_session_token()
                    expires_at = _utcnow() + timedelta(hours=12)
                    session = InterviewSession(
                        candidate_id=candidate.id,
                        job_id=candidate.job_id,
                        session_token_hash=hash_interview_session_token(session_token),
                        status=InterviewSessionStatus.INVITED,
                        expires_at=expires_at,
                    )
                    db.add(session)
                    db.flush()

                    latest_cv = (
                        db.query(InterviewCandidateDocument)
                        .filter(
                            InterviewCandidateDocument.candidate_id == candidate.id,
                            InterviewCandidateDocument.document_type == "cv",
                            InterviewCandidateDocument.extraction_status == "complete",
                            InterviewCandidateDocument.extracted_text.isnot(None),
                        )
                        .order_by(InterviewCandidateDocument.uploaded_at.desc(), InterviewCandidateDocument.id.desc())
                        .first()
                    )
                    cv_text = decrypt_text_value(latest_cv.extracted_text) if latest_cv else ""
                    combined_questions = build_hybrid_interview_questions(
                        candidate.job.base_questions or [],
                        cv_text or "",
                    )
                    
                    # Add questions to DB
                    for index, (question_text, source) in enumerate(combined_questions, start=1):
                        db.add(
                            InterviewQuestion(
                                job_id=candidate.job_id,
                                session_id=session.id,
                                candidate_id=candidate.id,
                                question_text=question_text,
                                source=source,
                                display_order=index,
                            )
                        )
                    session.question_count = len(combined_questions)
                    db.flush()
                    
                    try:
                        invite_url = build_interview_invite_url(session_token, get_settings())
                        context["invite_url"] = invite_url
                        context["expires_at"] = expires_at
                    except Exception:
                        pass
                else:
                    # Session exists, but we only have its hash.
                    # Since we can't recover raw token from hash, if they need to send it, we can create a new session.
                    session_token = generate_interview_session_token()
                    expires_at = _utcnow() + timedelta(hours=12)
                    new_session = InterviewSession(
                        candidate_id=candidate.id,
                        job_id=candidate.job_id,
                        session_token_hash=hash_interview_session_token(session_token),
                        status=InterviewSessionStatus.INVITED,
                        expires_at=expires_at,
                    )
                    db.add(new_session)
                    db.flush()

                    latest_cv = (
                        db.query(InterviewCandidateDocument)
                        .filter(
                            InterviewCandidateDocument.candidate_id == candidate.id,
                            InterviewCandidateDocument.document_type == "cv",
                            InterviewCandidateDocument.extraction_status == "complete",
                            InterviewCandidateDocument.extracted_text.isnot(None),
                        )
                        .order_by(InterviewCandidateDocument.uploaded_at.desc(), InterviewCandidateDocument.id.desc())
                        .first()
                    )
                    cv_text = decrypt_text_value(latest_cv.extracted_text) if latest_cv else ""
                    combined_questions = build_hybrid_interview_questions(
                        candidate.job.base_questions or [],
                        cv_text or "",
                    )
                    for index, (question_text, source) in enumerate(combined_questions, start=1):
                        db.add(
                            InterviewQuestion(
                                job_id=candidate.job_id,
                                session_id=new_session.id,
                                candidate_id=candidate.id,
                                question_text=question_text,
                                source=source,
                                display_order=index,
                            )
                        )
                    new_session.question_count = len(combined_questions)
                    db.flush()
                    try:
                        invite_url = build_interview_invite_url(session_token, get_settings())
                        context["invite_url"] = invite_url
                        context["expires_at"] = expires_at
                    except Exception:
                        pass

            send_interview_candidate_email(
                destination_email=candidate.contact_email_normalized,
                candidate_name=candidate.full_name,
                template=template,
                context=context,
            )

    return candidate


@router.get("/candidates", response_model=list[InterviewCandidateOut])
def list_interview_candidates(
    job_id: Optional[int] = Query(None, ge=1),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.VIEW_INTERVIEW_CANDIDATES, detail="Only HR managers and admins can view interview candidates.")
    query = db.query(InterviewCandidate).order_by(InterviewCandidate.applied_at.desc())
    if job_id is not None:
        query = query.filter(InterviewCandidate.job_id == job_id)
    if status is not None:
        query = query.filter(InterviewCandidate.status == _parse_candidate_status(status))
    candidates = query.all()
    if not candidates:
        return []

    candidate_ids = [candidate.id for candidate in candidates]
    submissions = (
        db.query(InterviewMcqSubmission)
        .filter(InterviewMcqSubmission.candidate_id.in_(candidate_ids))
        .order_by(InterviewMcqSubmission.candidate_id.asc(), InterviewMcqSubmission.completed_at.desc(), InterviewMcqSubmission.id.desc())
        .all()
    )
    latest_submission_by_candidate: dict[int, InterviewMcqSubmission] = {}
    for submission in submissions:
        latest_submission_by_candidate.setdefault(submission.candidate_id, submission)

    return [
        _serialize_candidate_with_submission(candidate, latest_submission_by_candidate.get(candidate.id))
        for candidate in candidates
    ]


@router.post("/candidates/{candidate_id}/invite", response_model=InterviewCandidateInviteOut)
def invite_interview_candidate(
    candidate_id: int,
    payload: InterviewCandidateInviteRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.MANAGE_INTERVIEW_CANDIDATES, detail="Only HR managers and admins can invite interview candidates.")
    candidate = _load_candidate_or_404(db, candidate_id)
    job = candidate.job
    settings = get_settings()
    if job is None:
        raise HTTPException(status_code=400, detail="Interview candidate is not linked to a valid job.")

    session_token = generate_interview_session_token()
    session = InterviewSession(
        candidate_id=candidate.id,
        job_id=job.id,
        session_token_hash=hash_interview_session_token(session_token),
        status=InterviewSessionStatus.INVITED,
        expires_at=_utcnow() + timedelta(hours=payload.expires_in_hours),
    )
    db.add(session)
    db.flush()

    latest_cv_document = (
        db.query(InterviewCandidateDocument)
        .filter(
            InterviewCandidateDocument.candidate_id == candidate.id,
            InterviewCandidateDocument.document_type == "cv",
            InterviewCandidateDocument.extraction_status == "complete",
            InterviewCandidateDocument.extracted_text.isnot(None),
        )
        .order_by(InterviewCandidateDocument.uploaded_at.desc(), InterviewCandidateDocument.id.desc())
        .first()
    )
    cv_source_text = decrypt_text_value(latest_cv_document.extracted_text) if latest_cv_document is not None else ""
    combined_questions = build_hybrid_interview_questions(
        job.base_questions or [],
        cv_source_text or "",
        manual_questions=payload.questions if payload.questions else None,
    )
    if not combined_questions:
        raise HTTPException(status_code=400, detail="Interview job must have at least one question before inviting a candidate.")
    cv_question_count = sum(1 for _question, source in combined_questions if source == InterviewQuestionSource.CV_AI)

    for index, (question_text, source) in enumerate(combined_questions, start=1):
        db.add(
            InterviewQuestion(
                job_id=job.id,
                session_id=session.id,
                candidate_id=candidate.id,
                question_text=question_text,
                source=source,
                display_order=index,
            )
        )

    session.question_count = len(combined_questions)
    
    validate_and_transition_candidate_status(
        db=db,
        candidate=candidate,
        to_status=InterviewCandidateStatus.INTERVIEWING,
        actor=current_user,
        note="Interview session created",
    )
    
    try:
        invite_url = build_interview_invite_url(session_token, settings)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    db.commit()
    db.refresh(session)
    return InterviewCandidateInviteOut(
        candidate_id=candidate.id,
        session_id=session.id,
        session_token=session_token,
        invite_url=invite_url,
        expires_at=session.expires_at,
        question_count=session.question_count,
    )


@router.post("/candidates/{candidate_id}/reject", response_model=InterviewCandidateOut)
def reject_interview_candidate(
    candidate_id: int,
    payload: InterviewCandidateDecisionUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.MANAGE_INTERVIEW_CANDIDATES, detail="Only HR managers and admins can reject interview candidates.")
    candidate = _load_candidate_or_404(db, candidate_id)
    
    validate_and_transition_candidate_status(
        db=db,
        candidate=candidate,
        to_status=InterviewCandidateStatus.REJECTED,
        actor=current_user,
        note=payload.note,
        send_email=payload.send_email,
    )
    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/candidates/{candidate_id}/archive", response_model=InterviewCandidateOut)
def archive_interview_candidate(
    candidate_id: int,
    payload: InterviewCandidateDecisionUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.MANAGE_INTERVIEW_CANDIDATES, detail="Only HR managers and admins can archive interview candidates.")
    candidate = _load_candidate_or_404(db, candidate_id)
    
    validate_and_transition_candidate_status(
        db=db,
        candidate=candidate,
        to_status=InterviewCandidateStatus.ARCHIVED,
        actor=current_user,
        note=payload.note,
        send_email=payload.send_email,
    )
    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/candidates/{candidate_id}/shortlist", response_model=InterviewCandidateOut)
def shortlist_interview_candidate(
    candidate_id: int,
    payload: InterviewCandidateDecisionUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.MANAGE_INTERVIEW_CANDIDATES, detail="Only HR managers and admins can shortlist interview candidates.")
    candidate = _load_candidate_or_404(db, candidate_id)
    
    validate_and_transition_candidate_status(
        db=db,
        candidate=candidate,
        to_status=InterviewCandidateStatus.SHORTLISTED,
        actor=current_user,
        note=payload.note,
        send_email=payload.send_email,
    )
    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/candidates/{candidate_id}/accept", response_model=InterviewCandidateOut)
def accept_interview_candidate(
    candidate_id: int,
    payload: InterviewCandidateDecisionUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.MANAGE_INTERVIEW_CANDIDATES, detail="Only HR managers and admins can accept interview candidates.")
    candidate = _load_candidate_or_404(db, candidate_id)
    
    validate_and_transition_candidate_status(
        db=db,
        candidate=candidate,
        to_status=InterviewCandidateStatus.ACCEPTED,
        actor=current_user,
        note=payload.note,
        send_email=payload.send_email,
    )
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get("/candidates/{candidate_id}/onboarding-readiness", response_model=InterviewCandidateOnboardingReadinessOut)
def get_candidate_onboarding_readiness(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.VIEW_INTERVIEW_CANDIDATES, detail="Only HR managers and admins can view onboarding readiness.")
    candidate = _load_candidate_or_404(db, candidate_id)
    return _build_candidate_onboarding_readiness(db, candidate)


@router.post("/candidates/{candidate_id}/restore", response_model=InterviewCandidateOut)
def restore_interview_candidate(
    candidate_id: int,
    payload: InterviewCandidateDecisionUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.MANAGE_INTERVIEW_CANDIDATES, detail="Only HR managers and admins can restore interview candidates.")
    candidate = _load_candidate_or_404(db, candidate_id)
    
    from_status = candidate.status
    if from_status != InterviewCandidateStatus.ARCHIVED:
        raise HTTPException(
            status_code=400,
            detail="Only archived candidates can be restored."
        )
        
    candidate.status = InterviewCandidateStatus.APPLIED
    candidate.archived_at = None
    
    create_interview_workflow_event(
        db,
        candidate_id=candidate.id,
        actor_id=current_user.id,
        event_type="CANDIDATE_RESTORED",
        from_status=from_status.value,
        to_status=candidate.status.value,
        note=payload.note or "Candidate restored from archive",
    )
    
    log_audit_event(
        db=db,
        action="INTERVIEW_CANDIDATE_RESTORE",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"InterviewCandidate #{candidate.id}",
        before_state=from_status.value,
        after_state=candidate.status.value,
        reason=payload.note or "Candidate restored from archive",
        success=True,
    )
    
    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/candidates/bulk-archive", response_model=InterviewCandidateBulkActionOut)
def bulk_archive_interview_candidates(
    payload: InterviewCandidateBulkActionRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.MANAGE_INTERVIEW_CANDIDATES, detail="Only HR managers and admins can archive interview candidates.")
    unique_ids = list(dict.fromkeys(payload.candidate_ids))
    candidates = (
        db.query(InterviewCandidate)
        .filter(InterviewCandidate.id.in_(unique_ids))
        .all()
    )
    candidate_by_id = {candidate.id: candidate for candidate in candidates}
    updated_ids: list[int] = []

    for candidate_id in unique_ids:
        candidate = candidate_by_id.get(candidate_id)
        if candidate is None or candidate.status == InterviewCandidateStatus.ARCHIVED:
            continue
        before_status = candidate.status.value
        candidate.status = InterviewCandidateStatus.ARCHIVED
        candidate.archived_at = _utcnow()
        updated_ids.append(candidate.id)
        create_interview_workflow_event(
            db,
            candidate_id=candidate.id,
            actor_id=current_user.id,
            event_type="CANDIDATE_BULK_ARCHIVED",
            from_status=before_status,
            to_status=candidate.status.value,
            note=payload.note,
            event_payload={"bulk_size": len(unique_ids)},
        )

    db.commit()
    log_audit_event(
        db=db,
        action="INTERVIEW_CANDIDATE_BULK_ARCHIVE",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target="InterviewCandidate bulk archive",
        before_state=f"requested={len(unique_ids)}",
        after_state=f"updated={len(updated_ids)}",
        reason=payload.note or "Interview candidates bulk archived",
        success=True,
    )
    return InterviewCandidateBulkActionOut(
        requested=len(unique_ids),
        updated=len(updated_ids),
        skipped=len(unique_ids) - len(updated_ids),
        candidate_ids=updated_ids,
    )


@router.post("/candidates/{candidate_id}/convert", response_model=InterviewCandidateConversionOut)
def convert_interview_candidate_to_employee(
    candidate_id: int,
    payload: InterviewCandidateConvertRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.CONVERT_INTERVIEW_CANDIDATES, detail="Only HR managers and admins can convert interview candidates.")
    candidate = _load_candidate_or_404(db, candidate_id)
    if candidate.converted_employee_id is not None:
        existing_employee = db.query(Employee).filter(Employee.id == candidate.converted_employee_id).first()
        if existing_employee is None:
            raise HTTPException(status_code=409, detail="Candidate is already linked to a converted employee.")
        return InterviewCandidateConversionOut(
            candidate_id=candidate.id,
            employee_id=existing_employee.id,
            employee_code=existing_employee.employee_code,
            employee_email=existing_employee.email,
            role=_serialize_enum(existing_employee.role),
        )

    if candidate.status != InterviewCandidateStatus.ACCEPTED:
        raise HTTPException(status_code=400, detail="Only accepted candidates can be converted to employees.")

    before_status = candidate.status.value
    try:
        role_to_assign = normalize_role_value(payload.role or UserRole.AGENT.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid employee role for conversion.") from exc

    try:
        employee_code = validate_employee_code(payload.employee_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    generated_email = generate_employee_email(employee_code)
    otp_email = normalize_contact_email(payload.otp_email) if payload.otp_email is not None else candidate.contact_email_normalized
    raw_password = (payload.password or get_settings().DEFAULT_EMPLOYEE_PASSWORD).strip()
    try:
        validate_password_strength(raw_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing_code = db.query(Employee).filter(Employee.employee_code == employee_code).first()
    if existing_code:
        raise HTTPException(status_code=409, detail="Conflict on employee_code: this code is already registered to another employee.")

    existing_email = db.query(Employee).filter(func.lower(Employee.email) == generated_email.lower()).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="Conflict on company email: this generated company email is already registered to another employee.")

    if candidate.national_id_hash:
        existing_national = db.query(Employee).filter(Employee.national_id_hash == candidate.national_id_hash).first()
        if existing_national:
            raise HTTPException(status_code=409, detail="Conflict on national ID: this national ID is already linked to another employee.")

    employee = Employee(
        name=candidate.full_name,
        email=generated_email,
        otp_email=otp_email,
        department=payload.department or candidate.job.department,
        employee_code=employee_code,
        national_id_hash=candidate.national_id_hash,
        hashed_password=get_password_hash(raw_password),
        role=role_to_assign,
        phone_number=payload.phone_number or candidate.phone_number,
        status=EmployeeStatus.ACTIVE.value,
    )
    db.add(employee)
    db.flush()

    candidate.converted_employee_id = employee.id
    validate_and_transition_candidate_status(
        db=db,
        candidate=candidate,
        to_status=InterviewCandidateStatus.ACCEPTED,
        actor=current_user,
        note=f"Converted to employee {employee.employee_code}",
        send_email=False,
    )
    create_interview_workflow_event(
        db,
        candidate_id=candidate.id,
        actor_id=current_user.id,
        event_type="CANDIDATE_CONVERTED_TO_EMPLOYEE",
        from_status=before_status,
        to_status=candidate.status.value,
        note=f"Converted to employee {employee.employee_code}",
        event_payload={
            "employee_id": employee.id,
            "employee_code": employee.employee_code,
            "employee_email": employee.email,
            "role": _serialize_enum(employee.role),
        },
    )
    create_interview_workflow_event(
        db,
        candidate_id=candidate.id,
        actor_id=current_user.id,
        event_type="ONBOARDING_HANDOFF",
        note=f"Employee {employee.employee_code} ready for onboarding handoff",
        event_payload={
            "employee_id": employee.id,
            "employee_code": employee.employee_code,
            "employee_email": employee.email,
            "otp_email": otp_email,
            "department": payload.department or (candidate.job.department if candidate.job else None),
            "role": _serialize_enum(employee.role),
        },
    )
    db.commit()
    db.refresh(employee)
    db.refresh(candidate)
    log_audit_event(
        db=db,
        action="INTERVIEW_CANDIDATE_CONVERT",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"InterviewCandidate #{candidate.id}",
        before_state=before_status,
        after_state=f"accepted; employee_id={employee.id}; employee_code={employee.employee_code}; employee_email={employee.email}; role={_serialize_enum(employee.role)}",
        reason="Interview candidate converted to employee",
        success=True,
    )
    return InterviewCandidateConversionOut(
        candidate_id=candidate.id,
        employee_id=employee.id,
        employee_code=employee.employee_code,
        employee_email=employee.email,
        role=_serialize_enum(employee.role),
    )


@router.post("/candidates/{candidate_id}/documents", response_model=InterviewCandidateDocumentOut)
async def upload_interview_candidate_document(
    candidate_id: int,
    document_type: str = Form(default="cv"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.MANAGE_INTERVIEW_CANDIDATES, detail="Only HR managers and admins can upload interview documents.")
    candidate = _load_candidate_or_404(db, candidate_id)

    settings = get_settings()
    documents_dir = os.path.join(settings.UPLOAD_DIR, "interview_documents")
    os.makedirs(documents_dir, exist_ok=True)
    safe_name = file.filename or "document.bin"
    extension = os.path.splitext(safe_name)[1].lower()
    if extension not in settings.interview_document_allowed_extensions_list:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document type. Allowed: {settings.INTERVIEW_DOCUMENT_ALLOWED_EXTENSIONS}",
        )
    storage_name = f"{candidate.id}_{int(_utcnow().timestamp())}_{safe_name}"
    storage_path = os.path.join(documents_dir, storage_name)
    content = await file.read()
    if len(content) > settings.interview_document_max_file_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Document exceeds max size of {settings.INTERVIEW_DOCUMENT_MAX_FILE_SIZE_MB}MB",
        )
    with open(storage_path, "wb") as output_file:
        output_file.write(content)

    document = InterviewCandidateDocument(
        candidate_id=candidate.id,
        document_type=document_type.strip() or "cv",
        original_filename=safe_name,
        storage_path=storage_path,
        content_type=file.content_type,
        file_size_bytes=len(content),
        extraction_status="pending",
    )
    db.add(document)
    db.flush()
    try:
        extracted_text = extract_text_from_document(storage_path, file.content_type, safe_name)
        document.extracted_text = encrypt_text_value(extracted_text)
        document.extraction_status = "complete" if extracted_text else "empty"
        document.extraction_error = None
    except ValueError as exc:
        document.extraction_status = "failed"
        document.extraction_error = str(exc)
    try:
        encrypt_file_in_place(storage_path)
        document.is_encrypted = True
    except Exception as exc:
        try:
            if os.path.isfile(storage_path):
                os.remove(storage_path)
        except OSError:
            pass
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to secure uploaded interview document: {exc}") from exc
    create_interview_workflow_event(
        db,
        candidate_id=candidate.id,
        actor_id=current_user.id,
        event_type="CANDIDATE_DOCUMENT_UPLOADED",
        note=f"Uploaded {document.document_type}",
        event_payload={
            "document_id": document.id,
            "filename": safe_name,
            "extraction_status": document.extraction_status,
        },
    )
    db.commit()
    db.refresh(document)
    log_audit_event(
        db=db,
        action="INTERVIEW_CANDIDATE_DOCUMENT_UPLOAD",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"InterviewCandidate #{candidate.id}",
        after_state=f"document_id={document.id}; type={document.document_type}",
        reason="Interview candidate document uploaded",
        success=True,
    )
    return document


@router.get("/candidates/{candidate_id}/documents", response_model=list[InterviewCandidateDocumentOut])
def list_interview_candidate_documents(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.VIEW_INTERVIEW_CANDIDATES, detail="Only HR managers and admins can view interview documents.")
    _load_candidate_or_404(db, candidate_id)
    return (
        db.query(InterviewCandidateDocument)
        .filter(InterviewCandidateDocument.candidate_id == candidate_id)
        .order_by(InterviewCandidateDocument.uploaded_at.desc(), InterviewCandidateDocument.id.desc())
        .all()
    )


@router.get("/candidates/{candidate_id}/answers", response_model=list[InterviewAnswerOut])
def list_interview_candidate_answers(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.VIEW_INTERVIEW_CANDIDATES, detail="Only HR managers and admins can review interview answers.")
    _load_candidate_or_404(db, candidate_id)
    return (
        db.query(InterviewAnswer)
        .filter(InterviewAnswer.candidate_id == candidate_id)
        .order_by(InterviewAnswer.submitted_at.asc().nullslast(), InterviewAnswer.id.asc())
        .all()
    )


@router.get("/candidates/{candidate_id}/mcq", response_model=InterviewMcqSubmissionOut | None)
def get_interview_candidate_mcq_submission(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.VIEW_INTERVIEW_CANDIDATES, detail="Only HR managers and admins can review interview answers.")
    _load_candidate_or_404(db, candidate_id)
    return (
        db.query(InterviewMcqSubmission)
        .filter(InterviewMcqSubmission.candidate_id == candidate_id)
        .order_by(InterviewMcqSubmission.completed_at.desc(), InterviewMcqSubmission.id.desc())
        .first()
    )


@router.get("/candidates/{candidate_id}/mcq-results", response_model=InterviewMcqReviewOut)
def get_interview_candidate_mcq_results(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.VIEW_INTERVIEW_CANDIDATES, detail="Only HR managers and admins can review interview answers.")
    candidate = _load_candidate_or_404(db, candidate_id)
    submission = (
        db.query(InterviewMcqSubmission)
        .filter(InterviewMcqSubmission.candidate_id == candidate_id)
        .order_by(InterviewMcqSubmission.completed_at.desc(), InterviewMcqSubmission.id.desc())
        .first()
    )
    if submission is None:
        return InterviewMcqReviewOut(
            status="no_results",
            candidate_id=candidate.id,
            candidate_name=candidate.full_name,
            score=0.0,
            total_questions=0,
            percentage=0.0,
            completed_at=None,
            iq=[],
            computer=[],
            personality=[],
            personality_breakdown={},
        )
    return InterviewMcqReviewOut(**format_mcq_results_for_review(submission, candidate_name=candidate.full_name))


@router.get("/candidates/{candidate_id}/review", response_model=InterviewCandidateReviewOut)
def get_interview_candidate_review(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(current_user, Permission.VIEW_INTERVIEW_CANDIDATES, detail="Only HR managers and admins can review interview answers.")
    candidate = _load_candidate_or_404(db, candidate_id)
    latest_submission = (
        db.query(InterviewMcqSubmission)
        .filter(InterviewMcqSubmission.candidate_id == candidate_id)
        .order_by(InterviewMcqSubmission.completed_at.desc(), InterviewMcqSubmission.id.desc())
        .first()
    )
    answers = (
        db.query(InterviewAnswer)
        .options(selectinload(InterviewAnswer.question))
        .filter(InterviewAnswer.candidate_id == candidate_id)
        .order_by(InterviewAnswer.submitted_at.asc().nullslast(), InterviewAnswer.id.asc())
        .all()
    )

    answer_scores = [answer.overall_score for answer in answers if answer.overall_score is not None]
    interview_metrics = InterviewCandidateReviewMetricsOut(
        evaluation_state=_resolve_interview_evaluation_state(answers),
        submitted_answers=len(answers),
        evaluated_answers=len(answer_scores),
        average_answer_score=round(sum(answer_scores) / len(answer_scores), 1) if answer_scores else None,
        strongest_answer_score=max(answer_scores) if answer_scores else None,
        weakest_answer_score=min(answer_scores) if answer_scores else None,
    )

    breakdown = latest_submission.breakdown or {} if latest_submission is not None else {}
    objective_breakdown_raw = breakdown.get("objective") or {}
    personality_breakdown = breakdown.get("traits") or {}
    mcq_summary = InterviewCandidateReviewMcqSummaryOut(
        completed=latest_submission is not None,
        score=latest_submission.score if latest_submission is not None else None,
        total_questions=latest_submission.total_questions if latest_submission is not None else None,
        percentage=latest_submission.percentage if latest_submission is not None else None,
        completed_at=latest_submission.completed_at if latest_submission is not None else None,
        objective_breakdown={key: float(value) for key, value in objective_breakdown_raw.items()},
        personality_breakdown={key: int(value) for key, value in personality_breakdown.items()},
    )

    return InterviewCandidateReviewOut(
        candidate=_serialize_candidate_with_submission(candidate, latest_submission),
        interview_metrics=interview_metrics,
        mcq_summary=mcq_summary,
        recommendation=_build_candidate_recommendation(candidate, answers, latest_submission),
        answers=[
            InterviewCandidateReviewAnswerOut(
                answer_id=answer.id,
                question_id=answer.question_id,
                question_text=answer.question.question_text if answer.question is not None else f"Question #{answer.question_id}",
                overall_score=answer.overall_score,
                status=answer.status,
                ai_summary=answer.ai_summary,
                transcribed_text=answer.transcribed_text,
                submitted_at=answer.submitted_at,
                evaluated_at=answer.evaluated_at,
                error_message=answer.error_message,
            )
            for answer in answers
        ],
    )


def _sanitize_payload(payload: dict | None) -> dict | None:
    if not payload:
        return payload
    sensitive_keys = {"token", "email", "phone", "password", "key", "secret", "cv", "resume", "ssn", "national_id"}
    sanitized = {}
    for k, v in payload.items():
        k_lower = k.lower()
        if any(sk in k_lower for sk in sensitive_keys):
            sanitized[k] = "[MASKED]"
        elif isinstance(v, dict):
            sanitized[k] = _sanitize_payload(v)
        else:
            sanitized[k] = v
    return sanitized


@router.get("/candidates/{candidate_id}/timeline", response_model=list[CandidateTimelineEventOut])
def get_candidate_timeline(
    candidate_id: int,
    limit: Optional[int] = Query(default=None, ge=1),
    event_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(
        current_user,
        Permission.VIEW_INTERVIEW_CANDIDATES,
        detail="Only HR managers and admins can view candidate timeline.",
    )
    _load_candidate_or_404(db, candidate_id)
    
    query = db.query(InterviewWorkflowEvent).filter(InterviewWorkflowEvent.candidate_id == candidate_id)
    if event_type:
        query = query.filter(InterviewWorkflowEvent.event_type == event_type)
    
    query = query.order_by(InterviewWorkflowEvent.created_at.desc(), InterviewWorkflowEvent.id.desc())
    
    if limit is not None:
        query = query.limit(limit)
        
    events = query.all()
    
    result = []
    for event in events:
        actor_name = event.actor.name if event.actor else None
        sanitized_payload = _sanitize_payload(event.event_payload)
        result.append(
            CandidateTimelineEventOut(
                id=event.id,
                candidate_id=event.candidate_id,
                actor_id=event.actor_id,
                actor_name=actor_name,
                event_type=event.event_type,
                from_status=event.from_status,
                to_status=event.to_status,
                note=event.note,
                event_payload=sanitized_payload,
                created_at=event.created_at,
            )
        )
    return result


@router.get("/export/candidates.csv")
def export_interview_candidates_csv(
    job_id: Optional[int] = Query(None, ge=1),
    status: Optional[str] = Query(None),
    include_pii: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    if not has_permission(current_user, Permission.EXPORT_INTERVIEW_DATA):
        log_audit_event(
            db=db,
            action="EXPORT",
            actor_id=current_user.id,
            actor_email=current_user.email,
            target="Interview Candidate Export",
            after_state=f"job_id={job_id or 'all'}; status={status or 'all'}; include_pii={include_pii}",
            reason="Access denied",
            success=False,
        )
        raise HTTPException(status_code=403, detail="Only HR managers and admins can export interview candidate data.")

    if include_pii and current_user.role != UserRole.ADMIN:
        log_audit_event(
            db=db,
            action="EXPORT",
            actor_id=current_user.id,
            actor_email=current_user.email,
            target="Interview Candidate Export",
            after_state=f"job_id={job_id or 'all'}; status={status or 'all'}; include_pii={include_pii}",
            reason="PII export requires admin role",
            success=False,
        )
        raise HTTPException(status_code=403, detail="Full PII interview exports require admin access.")

    query = (
        db.query(InterviewCandidate)
        .options(
            selectinload(InterviewCandidate.job),
            selectinload(InterviewCandidate.sessions),
            selectinload(InterviewCandidate.documents),
        )
        .order_by(InterviewCandidate.applied_at.desc(), InterviewCandidate.id.desc())
    )
    if job_id is not None:
        query = query.filter(InterviewCandidate.job_id == job_id)
    if status is not None:
        query = query.filter(InterviewCandidate.status == _parse_candidate_status(status))
    candidates = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "candidate_id",
        "job_id",
        "job_title",
        "department",
        "status",
        "full_name",
        "contact_email",
        "phone_number",
        "national_id_last4",
        "final_score",
        "applied_at",
        "completed_at",
        "converted_employee_id",
        "document_count",
        "latest_session_status",
    ])

    for candidate in candidates:
        latest_session = max(candidate.sessions, key=lambda item: item.created_at, default=None)
        writer.writerow([
            candidate.id,
            candidate.job_id,
            candidate.job.title if candidate.job is not None else "",
            candidate.job.department if candidate.job is not None and candidate.job.department else "",
            _serialize_enum(candidate.status),
            candidate.full_name,
            candidate.contact_email_normalized if include_pii else _mask_export_email(candidate.contact_email_normalized),
            candidate.phone_number if include_pii else _mask_export_phone(candidate.phone_number),
            candidate.national_id_last4 if include_pii else "",
            f"{candidate.final_score:.2f}" if candidate.final_score is not None else "",
            candidate.applied_at.isoformat() if candidate.applied_at else "",
            candidate.completed_at.isoformat() if candidate.completed_at else "",
            candidate.converted_employee_id or "",
            len(candidate.documents),
            _serialize_enum(latest_session.status) if latest_session is not None else "",
        ])

    log_audit_event(
        db=db,
        action="EXPORT",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target="Interview Candidate Export",
        after_state=f"job_id={job_id or 'all'}; status={status or 'all'}; include_pii={include_pii}; rows={len(candidates)}",
        reason="Interview candidate export",
        success=True,
    )

    output.seek(0)
    filename = f"interview_candidates_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/retention/purge-archived", response_model=InterviewRetentionPurgeOut)
def purge_archived_interview_candidates_endpoint(
    payload: InterviewRetentionPurgeRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    if normalize_role_value(current_user.role) not in {UserRole.ADMIN, UserRole.HR_MANAGER}:
        raise HTTPException(status_code=403, detail="Only HR managers and admins can manage interview retention.")

    summary = purge_archived_interview_candidates(
        db,
        older_than_days=payload.older_than_days,
        dry_run=payload.dry_run,
    )
    log_audit_event(
        db=db,
        action="INTERVIEW_RETENTION_PURGE",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target="Interview Archived Candidate Retention",
        after_state=(
            f"older_than_days={payload.older_than_days}; dry_run={payload.dry_run}; "
            f"matched={summary.archived_candidates_matched}; deleted={summary.candidates_deleted}; "
            f"document_rows={summary.document_rows_deleted}; document_files={summary.document_files_deleted}; "
            f"answer_audio_files={summary.answer_audio_files_deleted}"
        ),
        reason="Interview archived candidate retention cleanup",
        success=True,
    )
    if not payload.dry_run:
        db.commit()

    return InterviewRetentionPurgeOut(
        archived_candidates_matched=summary.archived_candidates_matched,
        candidates_deleted=summary.candidates_deleted,
        document_rows_deleted=summary.document_rows_deleted,
        answer_audio_files_deleted=summary.answer_audio_files_deleted,
        document_files_deleted=summary.document_files_deleted,
        dry_run=summary.dry_run,
    )


from pydantic import BaseModel
from app.services.email_delivery import send_interview_candidate_email


class CandidateNotifyRequest(BaseModel):
    template: str
    context: Optional[dict] = None


class CandidateBulkNotifyRequest(BaseModel):
    candidate_ids: list[int]
    template: str
    context: Optional[dict] = None


@router.post("/candidates/{candidate_id}/notify")
def notify_interview_candidate(
    candidate_id: int,
    payload: CandidateNotifyRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(
        current_user,
        Permission.MANAGE_INTERVIEW_CANDIDATES,
        detail="Only HR managers and admins can notify interview candidates.",
    )
    candidate = _load_candidate_or_404(db, candidate_id)

    # 1. Prepare template and context
    template = payload.template
    context = payload.context or {}

    # Auto-populate job_title
    if "job_title" not in context:
        context["job_title"] = candidate.job.title if candidate.job else "Position"

    # Handle invite template URL generation
    if template == "interview_invite":
        # Check if we have invite_url in context
        invite_url = context.get("invite_url")
        expires_at = context.get("expires_at")
        
        if not invite_url:
            # Let's generate a new session token and session
            session_token = generate_interview_session_token()
            settings = get_settings()
            
            # Use 12 hours as default expiry
            expires_at = _utcnow() + timedelta(hours=12)
            session = InterviewSession(
                candidate_id=candidate.id,
                job_id=candidate.job_id,
                session_token_hash=hash_interview_session_token(session_token),
                status=InterviewSessionStatus.INVITED,
                expires_at=expires_at,
            )
            db.add(session)
            db.flush()
            
            # Load candidate CV (if any) and build hybrid questions
            latest_cv = (
                db.query(InterviewCandidateDocument)
                .filter(
                    InterviewCandidateDocument.candidate_id == candidate.id,
                    InterviewCandidateDocument.document_type == "cv",
                    InterviewCandidateDocument.extraction_status == "complete",
                    InterviewCandidateDocument.extracted_text.isnot(None),
                )
                .order_by(InterviewCandidateDocument.uploaded_at.desc(), InterviewCandidateDocument.id.desc())
                .first()
            )
            cv_text = decrypt_text_value(latest_cv.extracted_text) if latest_cv else ""
            combined_questions = build_hybrid_interview_questions(
                candidate.job.base_questions or [],
                cv_text or "",
            )
            if not combined_questions:
                raise HTTPException(
                    status_code=400,
                    detail="Interview job must have at least one question before inviting.",
                )
            
            for index, (question_text, source) in enumerate(combined_questions, start=1):
                db.add(
                    InterviewQuestion(
                        job_id=candidate.job_id,
                        session_id=session.id,
                        candidate_id=candidate.id,
                        question_text=question_text,
                        source=source,
                        display_order=index,
                    )
                )
            session.question_count = len(combined_questions)
            
            # Transition candidate status
            previous_status = candidate.status
            candidate.status = InterviewCandidateStatus.INTERVIEWING
            
            create_interview_workflow_event(
                db,
                candidate_id=candidate.id,
                actor_id=current_user.id,
                event_type="CANDIDATE_INVITED",
                from_status=previous_status.value,
                to_status=candidate.status.value,
                note="Interview session created during notify",
                event_payload={"session_id": session.id, "question_count": len(combined_questions)},
            )
            
            try:
                invite_url = build_interview_invite_url(session_token, settings)
            except ValueError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            context["invite_url"] = invite_url
            context["expires_at"] = expires_at

    # Send the email
    email_success = send_interview_candidate_email(
        destination_email=candidate.contact_email_normalized,
        candidate_name=candidate.full_name,
        template=template,
        context=context,
    )

    # Logging events
    event_type = "INTERVIEW_EMAIL_SENT" if email_success else "INTERVIEW_EMAIL_FAILED"
    note = f"Sent {template} email to {candidate.contact_email}" if email_success else f"Failed to send {template} email to {candidate.contact_email}"
    
    create_interview_workflow_event(
        db,
        candidate_id=candidate.id,
        actor_id=current_user.id,
        event_type=event_type,
        from_status=candidate.status.value,
        to_status=candidate.status.value,
        note=note,
        event_payload={"template": template, "recipient": candidate.contact_email_normalized},
    )
    
    log_audit_event(
        db=db,
        action=event_type,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"InterviewCandidate #{candidate.id}",
        before_state=f"template={template}",
        after_state=f"success={email_success}; recipient={candidate.contact_email_normalized}",
        reason=note,
        success=email_success,
    )

    db.commit()
    db.refresh(candidate)

    return {
        "success": email_success,
        "candidate_id": candidate.id,
        "template": template,
        "message": note,
    }


@router.post("/candidates/bulk-notify")
def bulk_notify_interview_candidates(
    payload: CandidateBulkNotifyRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_active_staff(current_user)
    require_permission(
        current_user,
        Permission.MANAGE_INTERVIEW_CANDIDATES,
        detail="Only HR managers and admins can notify interview candidates.",
    )
    
    unique_ids = list(dict.fromkeys(payload.candidate_ids))
    candidates = (
        db.query(InterviewCandidate)
        .filter(InterviewCandidate.id.in_(unique_ids))
        .all()
    )
    candidate_by_id = {c.id: c for c in candidates}
    
    sent_count = 0
    failed_count = 0
    results = []

    for candidate_id in unique_ids:
        candidate = candidate_by_id.get(candidate_id)
        if not candidate:
            continue
        
        # 1. Prepare template and context
        template = payload.template
        context = payload.context or {}
        
        # Copy context so candidates don't share mutation
        candidate_context = dict(context)
        if "job_title" not in candidate_context:
            candidate_context["job_title"] = candidate.job.title if candidate.job else "Position"

        # Handle invite template URL generation for bulk
        if template == "interview_invite":
            invite_url = candidate_context.get("invite_url")
            expires_at = candidate_context.get("expires_at")
            
            if not invite_url:
                # Generate new session
                session_token = generate_interview_session_token()
                settings = get_settings()
                expires_at = _utcnow() + timedelta(hours=12)
                session = InterviewSession(
                    candidate_id=candidate.id,
                    job_id=candidate.job_id,
                    session_token_hash=hash_interview_session_token(session_token),
                    status=InterviewSessionStatus.INVITED,
                    expires_at=expires_at,
                )
                db.add(session)
                db.flush()
                
                latest_cv = (
                    db.query(InterviewCandidateDocument)
                    .filter(
                        InterviewCandidateDocument.candidate_id == candidate.id,
                        InterviewCandidateDocument.document_type == "cv",
                        InterviewCandidateDocument.extraction_status == "complete",
                        InterviewCandidateDocument.extracted_text.isnot(None),
                    )
                    .order_by(InterviewCandidateDocument.uploaded_at.desc(), InterviewCandidateDocument.id.desc())
                    .first()
                )
                cv_text = decrypt_text_value(latest_cv.extracted_text) if latest_cv else ""
                combined_questions = build_hybrid_interview_questions(
                    candidate.job.base_questions or [],
                    cv_text or "",
                )
                if not combined_questions:
                    failed_count += 1
                    results.append({
                        "candidate_id": candidate.id,
                        "success": False,
                        "error": "No questions configured for job."
                    })
                    continue
                
                for index, (question_text, source) in enumerate(combined_questions, start=1):
                    db.add(
                        InterviewQuestion(
                            job_id=candidate.job_id,
                            session_id=session.id,
                            candidate_id=candidate.id,
                            question_text=question_text,
                            source=source,
                            display_order=index,
                        )
                    )
                session.question_count = len(combined_questions)
                
                previous_status = candidate.status
                candidate.status = InterviewCandidateStatus.INTERVIEWING
                
                create_interview_workflow_event(
                    db,
                    candidate_id=candidate.id,
                    actor_id=current_user.id,
                    event_type="CANDIDATE_INVITED",
                    from_status=previous_status.value,
                    to_status=candidate.status.value,
                    note="Interview session created during bulk notify",
                    event_payload={"session_id": session.id, "question_count": len(combined_questions)},
                )
                
                try:
                    invite_url = build_interview_invite_url(session_token, settings)
                except ValueError as exc:
                    failed_count += 1
                    results.append({
                        "candidate_id": candidate.id,
                        "success": False,
                        "error": f"Failed to generate invite URL: {exc}"
                    })
                    continue
                candidate_context["invite_url"] = invite_url
                candidate_context["expires_at"] = expires_at

        # Send email
        email_success = send_interview_candidate_email(
            destination_email=candidate.contact_email_normalized,
            candidate_name=candidate.full_name,
            template=template,
            context=candidate_context,
        )
        
        # Logging events
        event_type = "INTERVIEW_EMAIL_SENT" if email_success else "INTERVIEW_EMAIL_FAILED"
        note = f"Sent {template} email to {candidate.contact_email} (bulk)" if email_success else f"Failed to send {template} email to {candidate.contact_email} (bulk)"
        
        create_interview_workflow_event(
            db,
            candidate_id=candidate.id,
            actor_id=current_user.id,
            event_type=event_type,
            from_status=candidate.status.value,
            to_status=candidate.status.value,
            note=note,
            event_payload={"template": template, "recipient": candidate.contact_email_normalized, "bulk": True},
        )
        
        log_audit_event(
            db=db,
            action=event_type,
            actor_id=current_user.id,
            actor_email=current_user.email,
            target=f"InterviewCandidate #{candidate.id}",
            before_state=f"template={template}; bulk=True",
            after_state=f"success={email_success}; recipient={candidate.contact_email_normalized}",
            reason=note,
            success=email_success,
        )
        
        if email_success:
            sent_count += 1
        else:
            failed_count += 1
            
        results.append({
            "candidate_id": candidate.id,
            "success": email_success,
        })
        
    db.commit()

    return {
        "success_count": sent_count,
        "failed_count": failed_count,
        "total": len(unique_ids),
        "results": results,
    }
