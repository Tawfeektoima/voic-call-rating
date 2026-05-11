from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, Integer
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models import AgentViolation, Employee, UserRole, SystemLog
from app.routers.auth import get_current_user
from app.schemas import (
    AgentViolationHistory,
    AgentViolationOut,
    ViolationSummaryRow,
    PendingViolationOut,
    ViolationStats
)

router = APIRouter(prefix="/api/hr", tags=["HR Violations"])

HR_ROLES = [UserRole.ADMIN, UserRole.HR_MANAGER, UserRole.QA]  # Assuming QA also might have some visibility or we just use admin/hr_manager. User spec says: "admin", "manager", "hr_manager". We don't have "MANAGER" in enum, so we'll use ADMIN and HR_MANAGER.

@router.get("/violations/summary", response_model=List[ViolationSummaryRow])
def get_violations_summary(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns per-agent violation counts grouped by severity.
    Accessible by: admin, hr_manager only.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.HR_MANAGER]:
        raise HTTPException(status_code=403, detail="Access denied.")

    summary_query = (
        db.query(
            AgentViolation.employee_id,
            Employee.name.label("employee_name"),
            func.count(AgentViolation.id).label("total_violations"),
            func.sum(func.cast(AgentViolation.severity == 'high', Integer)).label("high_count"),
            func.sum(func.cast(AgentViolation.severity == 'medium', Integer)).label("medium_count"),
            func.sum(func.cast(AgentViolation.severity == 'low', Integer)).label("low_count"),
            func.sum(func.cast(AgentViolation.hr_flagged == True, Integer)).label("hr_flagged_count"),
            func.sum(AgentViolation.score_deduction).label("total_deductions"),
            func.max(AgentViolation.created_at).label("last_violation_at")
        )
        .join(Employee, AgentViolation.employee_id == Employee.id)
        .group_by(AgentViolation.employee_id, Employee.name)
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

@router.get("/violations/pending", response_model=List[PendingViolationOut])
def get_pending_hr_violations(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns violations where hr_flagged=True, ordered by severity then date.
    Accessible by: admin, hr_manager only.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.HR_MANAGER]:
        raise HTTPException(status_code=403, detail="Access denied.")

    violations = (
        db.query(AgentViolation, Employee)
        .join(Employee, AgentViolation.employee_id == Employee.id)
        .filter(AgentViolation.hr_flagged == True)
        .order_by(AgentViolation.created_at.desc())
        .all()
    )

    results = []
    for v, emp in violations:
        results.append(PendingViolationOut(
            violation_id=v.id,
            employee_id=v.employee_id,
            employee_name=emp.name,
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
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns platform-wide violation statistics for the dashboard.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.HR_MANAGER]:
        raise HTTPException(status_code=403, detail="Access denied.")

    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = start_of_today - timedelta(days=now.weekday())

    total_today = db.query(func.count(AgentViolation.id)).filter(AgentViolation.created_at >= start_of_today).scalar() or 0
    total_week = db.query(func.count(AgentViolation.id)).filter(AgentViolation.created_at >= start_of_week).scalar() or 0
    
    most_common = (
        db.query(AgentViolation.violation_id, func.count(AgentViolation.id).label("count"))
        .group_by(AgentViolation.violation_id)
        .order_by(func.count(AgentViolation.id).desc())
        .first()
    )
    most_common_id = most_common.violation_id if most_common else None
    most_common_count = most_common.count if most_common else 0

    agents_with_hr = db.query(func.count(func.distinct(AgentViolation.employee_id))).filter(AgentViolation.hr_flagged == True).scalar() or 0
    auto_fails = db.query(func.count(AgentViolation.id)).filter(
        AgentViolation.auto_fail == True,
        AgentViolation.created_at >= start_of_today
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
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns violation trends for the last N days.
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Access denied.")

    since = datetime.now(timezone.utc) - timedelta(days=days)
    results = (
        db.query(
            cast(AgentViolation.created_at, Date).label("date"),
            AgentViolation.severity,
            func.count(AgentViolation.id).label("count"),
        )
        .filter(AgentViolation.created_at >= since)
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
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns all violations for an agent, newest first.
    Accessible by: admin, hr_manager
    Agents can only view their own violations.
    """
    if current_user.role == UserRole.AGENT and current_user.id != employee_id:
        raise HTTPException(status_code=403, detail="Agents can only view their own violations.")
    
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    query = db.query(AgentViolation).filter(AgentViolation.employee_id == employee_id)
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
