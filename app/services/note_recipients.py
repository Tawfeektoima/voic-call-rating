from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Employee, Team, UserRole
from app.services.note_scope import _is_admin, _load_call, _load_employee


def _active_employees_by_role(db: Session, role_value: str) -> list[Employee]:
    return (
        db.query(Employee)
        .filter(Employee.role == role_value, Employee.status == "active")
        .order_by(Employee.name.asc())
        .all()
    )


def _build_people_results(employees: list[Employee], role_value: str, reason: str) -> list[dict]:
    return [{"recipient_id": employee.id, "recipient_role": role_value, "name": employee.name, "reason": reason} for employee in employees]


def get_allowed_note_recipients(
    db: Session,
    current_user: Employee,
    note_type: str,
    team_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    call_id: Optional[int] = None,
) -> list[dict]:
    note_type = (note_type or "GENERAL").strip().upper()
    role_value = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)

    if note_type in {"QA_REVIEW_REQUEST", "QA_DISPUTE"}:
        return _build_people_results(_active_employees_by_role(db, UserRole.QA.value), UserRole.QA.value, "QA workflow")

    if note_type in {"HR_COMPLIANCE", "HR_ESCALATION"}:
        return _build_people_results(_active_employees_by_role(db, UserRole.HR_MANAGER.value), UserRole.HR_MANAGER.value, "HR workflow")

    if note_type == "KPI_ALERT":
        if team_id is None:
            return []
        team = db.query(Team).filter(Team.id == team_id, Team.is_active == True).first()
        if team is None or team.manager_id is None:
            return []
        manager = _load_employee(db, team.manager_id)
        if manager is None or manager.status != "active":
            return []
        if role_value not in {UserRole.ADMIN.value, UserRole.OPS_MANAGER.value}:
            return []
        return [{"recipient_id": manager.id, "recipient_role": UserRole.TEAM_MANAGER.value, "name": manager.name, "reason": "Team manager for KPI alert"}]

    if note_type == "KPI_FOLLOW_UP":
        if team_id is None:
            return []
        team = db.query(Team).filter(Team.id == team_id, Team.is_active == True).first()
        if team is None:
            return []
        if role_value in {UserRole.ADMIN.value, UserRole.TEAM_MANAGER.value}:
            if team.leader_id is None:
                return []
            leader = _load_employee(db, team.leader_id)
            if leader is None or leader.status != "active":
                return []
            return [{"recipient_id": leader.id, "recipient_role": UserRole.TEAM_LEADER.value, "name": leader.name, "reason": "Team leader for KPI follow-up"}]
        if role_value == UserRole.TEAM_LEADER.value:
            if team.manager_id is None:
                return []
            manager = _load_employee(db, team.manager_id)
            if manager is None or manager.status != "active":
                return []
            return [{"recipient_id": manager.id, "recipient_role": UserRole.TEAM_MANAGER.value, "name": manager.name, "reason": "Team manager for KPI follow-up"}]
        return []

    if note_type in {"GENERAL", "COACHING_NOTE", "COACHING_ESCALATION"}:
        if role_value == UserRole.TEAM_LEADER.value and team_id is not None:
            team = db.query(Team).filter(Team.id == team_id, Team.is_active == True).first()
            if team is None or team.manager_id is None:
                return []
            manager = _load_employee(db, team.manager_id)
            if manager is None or manager.status != "active":
                return []
            return [{"recipient_id": manager.id, "recipient_role": UserRole.TEAM_MANAGER.value, "name": manager.name, "reason": "Team manager for selected team"}]
        if role_value == UserRole.TEAM_MANAGER.value:
            return _build_people_results(_active_employees_by_role(db, UserRole.QA.value), UserRole.QA.value, "Manager escalation to QA")
        if employee_id is not None:
            employee = _load_employee(db, employee_id)
            if employee is not None and employee.status == "active":
                employee_role = employee.role.value if hasattr(employee.role, "value") else str(employee.role)
                return [{"recipient_id": employee.id, "recipient_role": employee_role, "name": employee.name, "reason": "Employee-specific note"}]
        if _is_admin(current_user):
            admins = _active_employees_by_role(db, UserRole.ADMIN.value)
            return _build_people_results(admins, UserRole.ADMIN.value, "Administrative workflow")

    if note_type == "SYSTEM_ISSUE":
        return _build_people_results(_active_employees_by_role(db, UserRole.ADMIN.value), UserRole.ADMIN.value, "Administrative workflow")

    if role_value == UserRole.QA.value and note_type == "GENERAL" and call_id is not None:
        call = _load_call(db, call_id)
        if call is not None:
            return []

    return []


def validate_note_recipient(db: Session, current_user: Employee, payload) -> None:
    if payload.recipient_id is None and payload.recipient_role is None:
        raise HTTPException(status_code=400, detail="A recipient is required.")

    if payload.recipient_id is not None and _is_admin(current_user):
        recipient = _load_employee(db, payload.recipient_id)
        if recipient is None or recipient.status != "active":
            raise HTTPException(status_code=400, detail="Recipient must be an active employee.")
        return

    allowed = get_allowed_note_recipients(
        db=db,
        current_user=current_user,
        note_type=payload.note_type,
        team_id=payload.team_id,
        campaign_id=payload.campaign_id,
        employee_id=payload.employee_id,
        call_id=payload.call_id,
    )

    if payload.recipient_id is not None:
        if not any(item["recipient_id"] == payload.recipient_id for item in allowed):
            raise HTTPException(status_code=400, detail="Recipient is not valid for this note context.")
        return

    if payload.recipient_role is not None:
        if not any(item["recipient_role"] == payload.recipient_role for item in allowed):
            raise HTTPException(status_code=400, detail="Recipient role is not valid for this note context.")
