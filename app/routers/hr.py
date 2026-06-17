from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, cast, Date, Integer, and_, or_, case
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import io
import pandas as pd

from app.config import get_settings
from app.database import get_db
from app.models import AgentViolation, Employee, UserRole, SystemLog, Call, Campaign, EmployeeTeamAssignment, Team
from app.routers.auth import get_current_user
from app.schemas import (
    AgentViolationHistory,
    AgentViolationOut,
    ViolationSummaryRow,
    PendingViolationOut,
    ViolationStats,
    ViolationApprovalUpdate,
    EmployeeCreate,
    BulkEmployeeFailure,
    BulkEmployeeResult,
    EmployeeOut
)
from app.security import get_password_hash
from app.security import validate_password_strength, PASSWORD_STRENGTH_MESSAGE
from app.permissions import normalize_role_value
from app.services.employee_identity import hash_national_id, normalize_contact_email, normalize_employee_code, normalize_employee_email
from app.services.audit import log_audit_event

router = APIRouter(prefix="/api/hr", tags=["HR Violations"])

HR_ROLES = [UserRole.ADMIN, UserRole.HR_MANAGER, UserRole.QA]
QA_APPROVER_ROLES = [UserRole.ADMIN, UserRole.QA]
HR_APPROVER_ROLES = [UserRole.ADMIN, UserRole.HR_MANAGER]
BULK_ONBOARDING_ROLES = (UserRole.AGENT, UserRole.QA, UserRole.HR_MANAGER)


def _parse_bulk_onboarding_role(raw_role: str) -> tuple[Optional[UserRole], Optional[str]]:
    try:
        role = normalize_role_value(raw_role or UserRole.AGENT.value)
    except ValueError:
        valid_roles = ", ".join(role.value for role in BULK_ONBOARDING_ROLES)
        return None, f"Invalid role '{raw_role}'. Must be one of: {valid_roles}"
    if role == UserRole.TEAM_LEADER:
        return None, "TEAM_LEADER is not allowed in HR bulk onboarding."
    if role not in BULK_ONBOARDING_ROLES:
        valid_roles = ", ".join(role.value for role in BULK_ONBOARDING_ROLES)
        return None, f"Invalid role '{role.value}'. Must be one of: {valid_roles}"
    return role, None


def _normalize_bulk_employee_identity(raw_email: str | None, raw_employee_code: str | None) -> tuple[str, str, Optional[str]]:
    employee_code = normalize_employee_code(raw_employee_code or "")
    if not employee_code:
        return str(raw_email or "").strip(), employee_code, "Employee code is required."
    try:
        email = normalize_employee_email(raw_email, employee_code)
    except ValueError as exc:
        return str(raw_email or "").strip(), employee_code, str(exc)
    return email, employee_code, None


def _validate_team_filter(db: Session, team_id: Optional[int]) -> None:
    if team_id is None:
        return
    team = db.query(Team.id).filter(Team.id == team_id).first()
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found.")


def _resolve_violation_scope(current_user: Employee, requested_team_id: Optional[int]) -> tuple[Optional[int], Optional[int]]:
    if current_user.role != UserRole.QA:
        return requested_team_id, None
    assigned_team_id = current_user.qa_scope_team_id
    assigned_campaign_id = current_user.qa_scope_campaign_id
    if requested_team_id is not None and requested_team_id != assigned_team_id:
        raise HTTPException(status_code=403, detail="You do not have permission to view another team's violations.")
    return (assigned_team_id if assigned_team_id is not None else -1), assigned_campaign_id


def _apply_violation_team_filter(query, team_id: Optional[int], campaign_id: Optional[int], assignment_alias):
    query = query.outerjoin(
        assignment_alias,
        and_(
            assignment_alias.employee_id == AgentViolation.employee_id,
            assignment_alias.assigned_at <= AgentViolation.created_at,
            or_(assignment_alias.ended_at == None, assignment_alias.ended_at >= AgentViolation.created_at),
        ),
    )
    if team_id is not None:
        query = query.filter(assignment_alias.team_id == team_id)
    if campaign_id is not None:
        query = query.filter(AgentViolation.campaign_id == campaign_id)
    return query


def _serialize_violation_state(violation: AgentViolation) -> str:
    return (
        f"hr_flagged={violation.hr_flagged};"
        f" qa_approved={violation.qa_approved};"
        f" qa_approved_by_id={violation.qa_approved_by_id};"
        f" qa_approved_at={violation.qa_approved_at};"
        f" qa_approval_note={violation.qa_approval_note};"
        f" hr_approved={violation.hr_approved};"
        f" hr_approved_by_id={violation.hr_approved_by_id};"
        f" hr_approved_at={violation.hr_approved_at};"
        f" hr_approval_note={violation.hr_approval_note}"
    )

@router.get("/violations/summary", response_model=List[ViolationSummaryRow])
def get_violations_summary(
    limit: int = Query(50, ge=1, le=500, description="Maximum agents to return"),
    offset: int = Query(0, ge=0, description="Result offset"),
    team_id: Optional[int] = Query(None, ge=1, description="Optional team filter"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns per-agent violation counts grouped by severity.
    Accessible by: admin, hr_manager only.
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Access denied.")

    _validate_team_filter(db, team_id)
    team_id, campaign_id = _resolve_violation_scope(current_user, team_id)
    assignment_alias = aliased(EmployeeTeamAssignment)
    summary_query = (
        db.query(
            AgentViolation.employee_id,
            Employee.name.label("employee_name"),
            func.count(AgentViolation.id).label("total_violations"),
            func.sum(func.cast(AgentViolation.severity == 'high', Integer)).label("high_count"),
            func.sum(func.cast(AgentViolation.severity == 'medium', Integer)).label("medium_count"),
            func.sum(func.cast(AgentViolation.severity == 'low', Integer)).label("low_count"),
            func.sum(case((and_(AgentViolation.hr_flagged == True, AgentViolation.qa_approved == True, AgentViolation.hr_approved == False), 1), else_=0)).label("hr_flagged_count"),
            func.sum(AgentViolation.score_deduction).label("total_deductions"),
            func.max(AgentViolation.created_at).label("last_violation_at")
        )
        .join(Employee, AgentViolation.employee_id == Employee.id)
    )
    summary_query = _apply_violation_team_filter(summary_query, team_id, campaign_id, assignment_alias)
    summary_query = (
        summary_query
        .group_by(AgentViolation.employee_id, Employee.name)
        .order_by(func.max(AgentViolation.created_at).desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    results = []
    for row in summary_query:
        results.append(ViolationSummaryRow(
            employee_id=row.employee_id,
            employee_name=row.employee_name,
            total_violations=row.total_violations,
            high_count=row.high_count or 0,
            medium_count=row.medium_count or 0,
            low_count=row.low_count or 0,
            hr_flagged_count=row.hr_flagged_count or 0,
            total_deductions=row.total_deductions or 0.0,
            last_violation_at=row.last_violation_at
        ))

    return results

@router.get("/violations/qa-pending", response_model=List[PendingViolationOut])
def get_pending_qa_violations(
    limit: int = Query(50, ge=1, le=500, description="Maximum violations to return"),
    offset: int = Query(0, ge=0, description="Result offset"),
    team_id: Optional[int] = Query(None, ge=1, description="Optional team filter"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns violations awaiting QA approval before they can move to HR.
    Accessible by: admin, qa.
    """
    if current_user.role not in QA_APPROVER_ROLES:
        raise HTTPException(status_code=403, detail="Access denied.")

    _validate_team_filter(db, team_id)
    team_id, campaign_id = _resolve_violation_scope(current_user, team_id)
    assignment_alias = aliased(EmployeeTeamAssignment)
    team_alias = aliased(Team)
    severity_rank = case(
        (AgentViolation.severity == "high", 0),
        (AgentViolation.severity == "medium", 1),
        (AgentViolation.severity == "low", 2),
        else_=3,
    )
    violations = db.query(
        AgentViolation,
        Employee,
        team_alias.id.label("team_id"),
        team_alias.name.label("team_name"),
    ).join(Employee, AgentViolation.employee_id == Employee.id)
    violations = _apply_violation_team_filter(violations, team_id, campaign_id, assignment_alias)
    violations = (
        violations
        .outerjoin(team_alias, assignment_alias.team_id == team_alias.id)
        .filter(AgentViolation.hr_flagged == True)
        .filter(AgentViolation.qa_approved == False)
        .order_by(severity_rank.asc(), AgentViolation.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        PendingViolationOut(
            violation_id=v.id,
            employee_id=v.employee_id,
            employee_name=emp.name,
            team_id=scoped_team_id,
            team_name=scoped_team_name,
            call_id=v.call_id,
            violation_type=v.violation_id,
            severity=v.severity,
            occurrence=v.occurrence,
            penalty_tier=v.penalty_tier,
            evidence=v.evidence,
            created_at=v.created_at,
        )
        for v, emp, scoped_team_id, scoped_team_name in violations
    ]

@router.get("/violations/pending", response_model=List[PendingViolationOut])
def get_pending_hr_violations(
    limit: int = Query(50, ge=1, le=500, description="Maximum violations to return"),
    offset: int = Query(0, ge=0, description="Result offset"),
    team_id: Optional[int] = Query(None, ge=1, description="Optional team filter"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns violations where hr_flagged=True, ordered by severity then date.
    Accessible by: admin, hr_manager only.
    """
    if current_user.role not in HR_APPROVER_ROLES:
        raise HTTPException(status_code=403, detail="Access denied.")

    _validate_team_filter(db, team_id)
    team_id, campaign_id = _resolve_violation_scope(current_user, team_id)
    assignment_alias = aliased(EmployeeTeamAssignment)
    team_alias = aliased(Team)
    severity_rank = case(
        (AgentViolation.severity == "high", 0),
        (AgentViolation.severity == "medium", 1),
        (AgentViolation.severity == "low", 2),
        else_=3,
    )
    violations = (
        db.query(
            AgentViolation,
            Employee,
            team_alias.id.label("team_id"),
            team_alias.name.label("team_name"),
        )
        .join(Employee, AgentViolation.employee_id == Employee.id)
    )
    violations = _apply_violation_team_filter(violations, team_id, campaign_id, assignment_alias)
    violations = (
        violations
        .outerjoin(team_alias, assignment_alias.team_id == team_alias.id)
        .filter(AgentViolation.hr_flagged == True)
        .filter(AgentViolation.qa_approved == True)
        .filter(AgentViolation.hr_approved == False)
        .order_by(severity_rank.asc(), AgentViolation.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    results = []
    for v, emp, scoped_team_id, scoped_team_name in violations:
        results.append(PendingViolationOut(
            violation_id=v.id,
            employee_id=v.employee_id,
            employee_name=emp.name,
            team_id=scoped_team_id,
            team_name=scoped_team_name,
            call_id=v.call_id,
            violation_type=v.violation_id,
            severity=v.severity,
            occurrence=v.occurrence,
            penalty_tier=v.penalty_tier,
            evidence=v.evidence,
            created_at=v.created_at
        ))
    return results

@router.get("/violations/stats", response_model=ViolationStats)
def get_violation_stats(
    team_id: Optional[int] = Query(None, ge=1, description="Optional team filter"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns platform-wide violation statistics for the dashboard.
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Access denied.")

    _validate_team_filter(db, team_id)
    team_id, campaign_id = _resolve_violation_scope(current_user, team_id)
    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = start_of_today - timedelta(days=now.weekday())
    assignment_alias = aliased(EmployeeTeamAssignment)

    total_today = _apply_violation_team_filter(
        db.query(func.count(AgentViolation.id)).filter(AgentViolation.created_at >= start_of_today),
        team_id,
        campaign_id,
        assignment_alias,
    ).scalar() or 0
    total_week = _apply_violation_team_filter(
        db.query(func.count(AgentViolation.id)).filter(AgentViolation.created_at >= start_of_week),
        team_id,
        campaign_id,
        aliased(EmployeeTeamAssignment),
    ).scalar() or 0
    
    most_common_query = db.query(AgentViolation.violation_id, func.count(AgentViolation.id).label("count"))
    most_common = (
        _apply_violation_team_filter(
            most_common_query,
            team_id,
            campaign_id,
            aliased(EmployeeTeamAssignment),
        )
        .group_by(AgentViolation.violation_id)
        .order_by(func.count(AgentViolation.id).desc())
        .first()
    )
    most_common_id = most_common.violation_id if most_common else None
    most_common_count = most_common.count if most_common else 0

    agents_with_hr = _apply_violation_team_filter(
        db.query(func.count(func.distinct(AgentViolation.employee_id))).filter(
            AgentViolation.hr_flagged == True,
            AgentViolation.qa_approved == True,
            AgentViolation.hr_approved == False,
        ),
        team_id,
        campaign_id,
        aliased(EmployeeTeamAssignment),
    ).scalar() or 0
    auto_fails = _apply_violation_team_filter(
        db.query(func.count(AgentViolation.id)).filter(
            AgentViolation.auto_fail == True,
            AgentViolation.created_at >= start_of_today,
        ),
        team_id,
        campaign_id,
        aliased(EmployeeTeamAssignment),
    ).scalar() or 0

    return ViolationStats(
        total_violations_today=total_today,
        total_violations_this_week=total_week,
        most_common_violation=most_common_id,
        most_common_violation_count=most_common_count,
        agents_with_hr_flags=agents_with_hr,
        auto_fails_today=auto_fails
    )

@router.get("/violations/trends")
def get_violation_trends(
    days: int = Query(7, ge=1, le=90, description="Number of days to include"),
    team_id: Optional[int] = Query(None, ge=1, description="Optional team filter"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns violation trends for the last N days.
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Access denied.")

    _validate_team_filter(db, team_id)
    team_id, campaign_id = _resolve_violation_scope(current_user, team_id)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    results_query = db.query(
        cast(AgentViolation.created_at, Date).label("date"),
        AgentViolation.severity,
        func.count(AgentViolation.id).label("count"),
    ).filter(AgentViolation.created_at >= since)
    results = (
        _apply_violation_team_filter(results_query, team_id, campaign_id, aliased(EmployeeTeamAssignment))
        .group_by(cast(AgentViolation.created_at, Date), AgentViolation.severity)
        .order_by(cast(AgentViolation.created_at, Date))
        .all()
    )

    # Build day-by-day structure
    trend_map = {}
    for row in results:
        day = str(row.date)
        if day not in trend_map:
            trend_map[day] = {"date": day, "high": 0, "medium": 0, "low": 0}
        trend_map[day][row.severity] += row.count

    # Fill missing days with zeros
    output = []
    for i in range(days):
        day = str((datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).date())
        output.append(trend_map.get(day, {"date": day, "high": 0, "medium": 0, "low": 0}))

    return output

@router.get("/violations/{employee_id}", response_model=AgentViolationHistory)
def get_agent_violations(
    employee_id: int,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200, description="Maximum violations to return"),
    offset: int = Query(0, ge=0, description="Result offset"),
    team_id: Optional[int] = Query(None, ge=1, description="Optional team filter"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns all violations for an agent, newest first.
    Accessible by: admin, hr_manager, qa.
    Agents can only view their own violations.
    """
    try:
        current_role = normalize_role_value(current_user.role)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied.")

    if current_role == UserRole.AGENT:
        if current_user.id != employee_id:
            raise HTTPException(status_code=403, detail="Agents can only view their own violations.")
    elif current_role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Access denied.")
    
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    _validate_team_filter(db, team_id)
    team_id, campaign_id = _resolve_violation_scope(current_user, team_id)
    query = db.query(AgentViolation).filter(AgentViolation.employee_id == employee_id)
    if team_id is not None:
        query = _apply_violation_team_filter(query, team_id, campaign_id, aliased(EmployeeTeamAssignment))
    elif campaign_id is not None:
        query = query.filter(AgentViolation.campaign_id == campaign_id)
    if severity:
        query = query.filter(AgentViolation.severity == severity)
    
    total_violations = query.count()
    total_deductions = db.query(func.sum(AgentViolation.score_deduction)).filter(AgentViolation.employee_id == employee_id).scalar() or 0.0

    violations = query.order_by(AgentViolation.created_at.desc()).offset(offset).limit(limit).all()

    v_outs = [AgentViolationOut.model_validate(v) for v in violations]

    return AgentViolationHistory(
        employee_id=employee_id,
        employee_name=employee.name,
        total_violations=total_violations,
        total_deductions=total_deductions,
        violations=v_outs
    )


@router.patch("/violations/{violation_id}/approve", response_model=AgentViolationOut)
def approve_violation(
    violation_id: int,
    payload: ViolationApprovalUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Marks a pending HR violation as reviewed/approved by HR.
    Accessible by: admin, hr_manager.
    """
    if current_user.role not in HR_APPROVER_ROLES:
        raise HTTPException(status_code=403, detail="Access denied.")

    violation = db.query(AgentViolation).filter(AgentViolation.id == violation_id).first()
    if violation is None:
        raise HTTPException(status_code=404, detail="Violation not found.")
    if not violation.hr_flagged:
        raise HTTPException(status_code=400, detail="Violation is not marked for HR review.")
    if violation.hr_approved:
        raise HTTPException(status_code=400, detail="Violation already approved.")

    if not violation.qa_approved:
        raise HTTPException(status_code=400, detail="Violation must be approved by QA first.")

    previous_state = _serialize_violation_state(violation)

    violation.hr_approved = True
    violation.hr_approved_by_id = current_user.id
    violation.hr_approved_at = datetime.now(timezone.utc)
    violation.hr_approval_note = (payload.note or "").strip() or None
    db.commit()
    db.refresh(violation)

    log_audit_event(
        db=db,
        action="HR_VIOLATION_APPROVE",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"Violation #{violation.id}",
        before_state=previous_state,
        after_state=_serialize_violation_state(violation),
        reason=violation.hr_approval_note or "HR approval recorded",
        success=True,
    )

    return AgentViolationOut.model_validate(violation)


@router.patch("/violations/{violation_id}/qa-approve", response_model=AgentViolationOut)
def qa_approve_violation(
    violation_id: int,
    payload: ViolationApprovalUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Marks a violation as quality-approved so it can move to HR review.
    Accessible by: admin, qa.
    """
    if current_user.role not in QA_APPROVER_ROLES:
        raise HTTPException(status_code=403, detail="Access denied.")

    violation = db.query(AgentViolation).filter(AgentViolation.id == violation_id).first()
    if violation is None:
        raise HTTPException(status_code=404, detail="Violation not found.")
    if not violation.hr_flagged:
        raise HTTPException(status_code=400, detail="Violation is not marked for HR review.")
    if violation.qa_approved:
        raise HTTPException(status_code=400, detail="Violation already approved by QA.")

    previous_state = _serialize_violation_state(violation)

    violation.qa_approved = True
    violation.qa_approved_by_id = current_user.id
    violation.qa_approved_at = datetime.now(timezone.utc)
    violation.qa_approval_note = (payload.note or "").strip() or None
    db.commit()
    db.refresh(violation)

    log_audit_event(
        db=db,
        action="QA_VIOLATION_APPROVE",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"Violation #{violation.id}",
        before_state=previous_state,
        after_state=_serialize_violation_state(violation),
        reason=violation.qa_approval_note or "QA approval recorded",
        success=True,
    )

    return AgentViolationOut.model_validate(violation)


@router.get("/alarms/pending")
def get_pending_qa_alarms(
    limit: int = Query(50, ge=1, le=500, description="Maximum alarms to return"),
    offset: int = Query(0, ge=0, description="Result offset"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns pending QA alarms (calls where qa_alarm=True and overridden_score is None).
    Accessible by: admin, hr_manager, qa.
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Access denied.")

    # Fetch calls with active alarms
    calls = (
        db.query(Call, Employee)
        .join(Employee, Call.employee_id == Employee.id)
        .filter(Call.qa_alarm == True)
        .filter(Call.overridden_score == None)
        .order_by(Call.created_at.desc())
        .all()
    )

    results = []
    for call, emp in calls[offset:offset + limit]:
        results.append({
            "call_id": call.id,
            "employee_id": call.employee_id,
            "employee_name": emp.name,
            "qa_alarm_reason": call.qa_alarm_reason,
            "qa_alarm_evidence": call.qa_alarm_evidence,
            "created_at": call.created_at,
            "original_score": call.evaluation_score
        })
    return results


@router.get("/template")
def download_template(
    current_user: Employee = Depends(get_current_user)
):
    """
    Returns a downloadable CSV template for bulk importing agents.
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.HR_MANAGER):
        raise HTTPException(status_code=403, detail="Only admins or HR managers can access onboarding templates.")
    
    csv_data = "Name,Email,OTP Email,National ID,Employee Code,Campaign,Phone Number,Role,Department\nJohn Doe,,john.doe@gmail.com,30001011234567,349,Sales,+1234567890,AGENT,Support\n"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=agent_import_template.csv"}
    )


@router.post("/preview")
def preview_bulk_agents(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Accepts a CSV/Excel file, parses it, validates constraints and uniqueness,
    and returns a preview of rows with error messages (without database commits).
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.HR_MANAGER):
        raise HTTPException(status_code=403, detail="Only admins or HR managers can preview onboarding files.")

    filename = file.filename.lower()
    try:
        contents = file.file.read()
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a .csv, .xlsx, or .xls file.")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    df = df.fillna("")
    # Normalize headers
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    # Map possible column names
    col_mapping = {
        "name": "name",
        "email": "email",
        "otp_email": "otp_email",
        "real_email": "otp_email",
        "gmail": "otp_email",
        "personal_email": "otp_email",
        "national_id": "national_id",
        "national_id_number": "national_id",
        "employee_code": "employee_code",
        "code": "employee_code",
        "campaign_name": "campaign_name",
        "campaign": "campaign_name",
        "phone_number": "phone_number",
        "phone": "phone_number",
        "role": "role",
        "department": "department",
        "password": "password"
    }
    df = df.rename(columns={c: col_mapping[c] for c in df.columns if c in col_mapping})

    # Validate that we have the minimum required columns
    required_cols = ["name", "employee_code"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns in file: {', '.join([c.replace('_', ' ').title() for c in missing_cols])}"
        )

    preview_data = []
    seen_codes = set()
    seen_emails = set()
    seen_national_ids = set()

    for i, (_, row) in enumerate(df.iterrows()):
        idx = i + 1
        name = str(row.get("name", "")).strip()
        email, employee_code, identity_error = _normalize_bulk_employee_identity(
            row.get("email", ""),
            row.get("employee_code", "")
        )
        try:
            otp_email = normalize_contact_email(row.get("otp_email", ""))
            otp_email_error = None
        except ValueError as exc:
            otp_email = str(row.get("otp_email", "")).strip()
            otp_email_error = str(exc)
        national_id_hash = hash_national_id(row.get("national_id", ""))
        campaign_name = str(row.get("campaign_name", "")).strip()
        phone_number = str(row.get("phone_number", "")).strip()
        role_input = str(row.get("role", "AGENT")).strip()
        role, role_error = _parse_bulk_onboarding_role(role_input)
        role_value = role.value if role else role_input.upper()
        department = str(row.get("department", "")).strip()

        errors = []

        # Name validation
        if not name:
            errors.append("Name is required.")
        if identity_error:
            errors.append(identity_error)
        if otp_email_error:
            errors.append(otp_email_error)

        # Email validation
        if email and "@" in email:
            normalized_email = email.lower()
            db_emp_email = db.query(Employee).filter(func.lower(Employee.email) == normalized_email).first()
            if db_emp_email:
                errors.append(f"Email '{email}' is already registered.")
            if normalized_email in seen_emails:
                errors.append(f"Duplicate email '{email}' in upload file.")
            seen_emails.add(normalized_email)

        # Employee Code validation
        if employee_code:
            db_emp_code = db.query(Employee).filter(Employee.employee_code == employee_code).first()
            if db_emp_code:
                errors.append(f"Employee code '{employee_code}' is already registered.")
            if employee_code in seen_codes:
                errors.append(f"Duplicate employee code '{employee_code}' in upload file.")
            seen_codes.add(employee_code)
        if national_id_hash:
            db_emp_national_id = db.query(Employee).filter(Employee.national_id_hash == national_id_hash).first()
            if db_emp_national_id:
                errors.append("National ID is already registered.")
            if national_id_hash in seen_national_ids:
                errors.append("Duplicate national ID in upload file.")
            seen_national_ids.add(national_id_hash)

        # Campaign validation
        if campaign_name:
            db_camp = db.query(Campaign).filter(Campaign.name == campaign_name).first()
            if not db_camp:
                errors.append(f"Campaign '{campaign_name}' does not exist.")

        # Role validation
        if role_error:
            errors.append(role_error)

        preview_data.append({
            "index": idx,
            "name": name,
            "email": email,
            "otp_email": otp_email,
            "employee_code": employee_code,
            "campaign_name": campaign_name,
            "phone_number": phone_number,
            "role": role_value,
            "department": department or campaign_name,
            "errors": errors,
            "isValid": len(errors) == 0
        })

    valid_count = sum(1 for item in preview_data if item["isValid"])
    summary = {
        "total": len(preview_data),
        "valid": valid_count,
        "invalid": len(preview_data) - valid_count
    }

    return {
        "data": preview_data,
        "summary": summary
    }


@router.post("/import", response_model=BulkEmployeeResult)
def import_bulk_agents(
    employees: List[dict],
    atomic: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Imports multiple agents. If atomic is True, any validation failure
    causes the entire import to fail. Otherwise, imports valid rows
    and reports failures on a per-row basis.
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.HR_MANAGER):
        raise HTTPException(status_code=403, detail="Only admins or HR managers can bulk import agents.")

    success_list = []
    failed_list = []
    seen_codes = set()
    seen_emails = set()
    seen_national_ids = set()

    # Pre-validation pass (especially important for atomic)
    all_validation_passed = True
    row_validation_errors = []

    for idx, item in enumerate(employees):
        row_num = item.get("index", idx + 1)
        name = str(item.get("name", "")).strip()
        email, employee_code, identity_error = _normalize_bulk_employee_identity(
            item.get("email", ""),
            item.get("employee_code", "")
        )
        try:
            otp_email = normalize_contact_email(item.get("otp_email", ""))
            otp_email_error = None
        except ValueError as exc:
            otp_email = str(item.get("otp_email", "")).strip()
            otp_email_error = str(exc)
        national_id_hash = hash_national_id(item.get("national_id", ""))
        campaign_name = str(item.get("campaign_name", "")).strip()
        phone_number = str(item.get("phone_number", "")).strip()
        role_input = str(item.get("role", "AGENT")).strip()
        role, role_error = _parse_bulk_onboarding_role(role_input)
        department = str(item.get("department", "")).strip()
        password = str(item.get("password", "")).strip()

        errors = []

        if not name:
            errors.append("Name is required.")
        if identity_error:
            errors.append(identity_error)
        if otp_email_error:
            errors.append(otp_email_error)
        if email and "@" in email:
            normalized_email = email.lower()
            db_emp_email = db.query(Employee).filter(func.lower(Employee.email) == normalized_email).first()
            if db_emp_email:
                errors.append(f"Email '{email}' is already registered.")
            if normalized_email in seen_emails:
                errors.append(f"Duplicate email '{email}' in batch.")
            seen_emails.add(normalized_email)

        if employee_code:
            db_emp_code = db.query(Employee).filter(Employee.employee_code == employee_code).first()
            if db_emp_code:
                errors.append(f"Employee code '{employee_code}' is already registered.")
            if employee_code in seen_codes:
                errors.append(f"Duplicate employee code '{employee_code}' in batch.")
            seen_codes.add(employee_code)
        if national_id_hash:
            db_emp_national_id = db.query(Employee).filter(Employee.national_id_hash == national_id_hash).first()
            if db_emp_national_id:
                errors.append("National ID is already registered.")
            if national_id_hash in seen_national_ids:
                errors.append("Duplicate national ID in batch.")
            seen_national_ids.add(national_id_hash)

        if campaign_name:
            db_camp = db.query(Campaign).filter(Campaign.name == campaign_name).first()
            if not db_camp:
                errors.append(f"Campaign '{campaign_name}' does not exist.")

        if role_error:
            errors.append(role_error)

        if password:
            try:
                validate_password_strength(password)
            except ValueError:
                errors.append(PASSWORD_STRENGTH_MESSAGE)

        if errors:
            all_validation_passed = False
            error_str = " | ".join(errors)
            row_validation_errors.append((row_num, employee_code, error_str))

    # If atomic mode is requested and we have failures, fail the entire import
    if atomic and not all_validation_passed:
        failures = [
            BulkEmployeeFailure(index=row_num, employee_code=code, error=err)
            for row_num, code, err in row_validation_errors
        ]
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Atomic import failed. Some rows have validation errors, and no changes were made.",
                "success_count": 0,
                "failed_count": len(failures),
                "failed": [f.model_dump() for f in failures],
                "success": []
            }
        )

    # Now perform the actual inserts
    seen_codes = set()
    seen_emails = set()
    seen_national_ids = set()

    for idx, item in enumerate(employees):
        row_num = item.get("index", idx + 1)
        name = str(item.get("name", "")).strip()
        email, employee_code, identity_error = _normalize_bulk_employee_identity(
            item.get("email", ""),
            item.get("employee_code", "")
        )
        try:
            otp_email = normalize_contact_email(item.get("otp_email", ""))
            otp_email_error = None
        except ValueError as exc:
            otp_email = str(item.get("otp_email", "")).strip()
            otp_email_error = str(exc)
        national_id_hash = hash_national_id(item.get("national_id", ""))
        campaign_name = str(item.get("campaign_name", "")).strip()
        phone_number = str(item.get("phone_number", "")).strip()
        role_input = str(item.get("role", "AGENT")).strip()
        role, role_error = _parse_bulk_onboarding_role(role_input)
        department = str(item.get("department", "")).strip()
        password = str(item.get("password", "")).strip()

        errors = []
        if not name:
            errors.append("Name is required.")
        if identity_error:
            errors.append(identity_error)
        if otp_email_error:
            errors.append(otp_email_error)
        if email and "@" in email:
            normalized_email = email.lower()
            db_emp_email = db.query(Employee).filter(func.lower(Employee.email) == normalized_email).first()
            if db_emp_email:
                errors.append(f"Email '{email}' is already registered.")
            if normalized_email in seen_emails:
                errors.append(f"Duplicate email '{email}' in batch.")
            seen_emails.add(normalized_email)

        if employee_code:
            db_emp_code = db.query(Employee).filter(Employee.employee_code == employee_code).first()
            if db_emp_code:
                errors.append(f"Employee code '{employee_code}' is already registered.")
            if employee_code in seen_codes:
                errors.append(f"Duplicate employee code '{employee_code}' in batch.")
            seen_codes.add(employee_code)
        if national_id_hash:
            db_emp_national_id = db.query(Employee).filter(Employee.national_id_hash == national_id_hash).first()
            if db_emp_national_id:
                errors.append("National ID is already registered.")
            if national_id_hash in seen_national_ids:
                errors.append("Duplicate national ID in batch.")
            seen_national_ids.add(national_id_hash)

        if campaign_name:
            db_camp = db.query(Campaign).filter(Campaign.name == campaign_name).first()
            if not db_camp:
                errors.append(f"Campaign '{campaign_name}' does not exist.")

        if role_error:
            errors.append(role_error)

        if password:
            try:
                validate_password_strength(password)
            except ValueError:
                errors.append(PASSWORD_STRENGTH_MESSAGE)

        if errors:
            failed_list.append(BulkEmployeeFailure(
                index=row_num,
                employee_code=employee_code,
                error=" | ".join(errors)
            ))
            continue

        if not password:
            password = get_settings().DEFAULT_EMPLOYEE_PASSWORD
        try:
            validate_password_strength(password)
        except ValueError as exc:
            failed_list.append(BulkEmployeeFailure(
                index=row_num,
                employee_code=employee_code,
                error=str(exc)
            ))
            continue

        try:
            hashed_pwd = get_password_hash(password)
            db_employee = Employee(
                name=name,
                email=email,
                otp_email=otp_email,
                employee_code=employee_code,
                national_id_hash=national_id_hash,
                hashed_password=hashed_pwd,
                role=role,
                phone_number=phone_number if phone_number else None,
                department=department if department else (campaign_name if campaign_name else None)
            )
            db.add(db_employee)
            db.commit()
            db.refresh(db_employee)
            success_list.append(db_employee)
        except Exception as e:
            db.rollback()
            failed_list.append(BulkEmployeeFailure(
                index=row_num,
                employee_code=employee_code,
                error=f"Database insertion failed: {str(e)}"
            ))

    message = f"Bulk onboarding completed. Successfully imported {len(success_list)} agents."
    if failed_list:
        message += f" Failed to import {len(failed_list)} agents due to errors."

    return BulkEmployeeResult(
        success=success_list,
        failed=failed_list,
        message=message,
        success_count=len(success_list),
        failed_count=len(failed_list)
    )
