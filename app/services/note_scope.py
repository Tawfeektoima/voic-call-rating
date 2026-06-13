from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Campaign, Call, Employee, RoleNote, RoleNoteStatus, RoleNoteVisibility, Team, UserRole
from app.services.team_scope import (
    is_agent_in_leader_scope,
    is_agent_in_manager_scope,
    is_team_in_leader_scope,
    is_team_in_manager_scope,
)


def _has_value(value: Optional[int]) -> bool:
    return value is not None


def _user_role_value(user: Employee) -> str:
    return user.role.value if hasattr(user.role, "value") else str(user.role)


def _is_admin(user: Employee) -> bool:
    return _user_role_value(user) == UserRole.ADMIN.value


def _is_agent(user: Employee) -> bool:
    return _user_role_value(user) == UserRole.AGENT.value


def _load_team(db: Session, team_id: int) -> Optional[Team]:
    return db.query(Team).filter(Team.id == team_id).first()


def _load_campaign(db: Session, campaign_id: int) -> Optional[Campaign]:
    return db.query(Campaign).filter(Campaign.id == campaign_id).first()


def _load_employee(db: Session, employee_id: int) -> Optional[Employee]:
    return db.query(Employee).filter(Employee.id == employee_id).first()


def _load_call(db: Session, call_id: int) -> Optional[Call]:
    return db.query(Call).filter(Call.id == call_id).first()


def _can_access_team(db: Session, current_user: Employee, team_id: int) -> bool:
    team = _load_team(db, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found.")
    if _is_admin(current_user):
        return True
    role = _user_role_value(current_user)
    if role == UserRole.TEAM_MANAGER.value:
        return is_team_in_manager_scope(db, current_user.id, team_id)
    if role == UserRole.TEAM_LEADER.value:
        return is_team_in_leader_scope(db, current_user.id, team_id)
    return role in {UserRole.OPS_MANAGER.value, UserRole.QA.value, UserRole.HR_MANAGER.value}


def _can_access_campaign(db: Session, current_user: Employee, campaign_id: int) -> bool:
    campaign = _load_campaign(db, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    if _is_admin(current_user):
        return True
    return not _is_agent(current_user)


def _can_access_employee(db: Session, current_user: Employee, employee_id: int) -> bool:
    employee = _load_employee(db, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found.")
    if _is_admin(current_user):
        return True
    role = _user_role_value(current_user)
    if role == UserRole.TEAM_MANAGER.value:
        return is_agent_in_manager_scope(db, current_user.id, employee_id)
    if role == UserRole.TEAM_LEADER.value:
        return is_agent_in_leader_scope(db, current_user.id, employee_id)
    if role == UserRole.AGENT.value:
        return current_user.id == employee_id
    return True


def _can_access_call(db: Session, current_user: Employee, call_id: int) -> bool:
    call = _load_call(db, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found.")
    if _is_admin(current_user):
        return True
    role = _user_role_value(current_user)
    if role == UserRole.TEAM_MANAGER.value:
        return is_agent_in_manager_scope(db, current_user.id, call.employee_id)
    if role == UserRole.TEAM_LEADER.value:
        return is_agent_in_leader_scope(db, current_user.id, call.employee_id)
    if role == UserRole.AGENT.value:
        return call.employee_id == current_user.id
    return True


def validate_note_context(db: Session, current_user: Employee, payload) -> None:
    if _has_value(getattr(payload, "team_id", None)) and not _can_access_team(db, current_user, payload.team_id):
        raise HTTPException(status_code=403, detail="You do not have access to this team context.")
    if _has_value(getattr(payload, "campaign_id", None)) and not _can_access_campaign(db, current_user, payload.campaign_id):
        raise HTTPException(status_code=403, detail="You do not have access to this campaign context.")
    if _has_value(getattr(payload, "employee_id", None)) and not _can_access_employee(db, current_user, payload.employee_id):
        raise HTTPException(status_code=403, detail="You do not have access to this employee context.")
    if _has_value(getattr(payload, "call_id", None)) and not _can_access_call(db, current_user, payload.call_id):
        raise HTTPException(status_code=403, detail="You do not have access to this call context.")


def can_user_access_note_context(db: Session, current_user: Employee, note: RoleNote) -> bool:
    try:
        validate_note_context(db, current_user, note)
        return True
    except HTTPException:
        return False


def can_user_read_note(db: Session, current_user: Employee, note: RoleNote) -> bool:
    if _is_admin(current_user):
        return True
    note_status = note.status.value if hasattr(note.status, "value") else str(note.status)
    if note_status == RoleNoteStatus.DELETED.value:
        return False
    if note.sender_id == current_user.id or note.recipient_id == current_user.id:
        return True
    recipient_role = note.recipient_role.value if hasattr(note.recipient_role, "value") else note.recipient_role
    if recipient_role and recipient_role == _user_role_value(current_user):
        return can_user_access_note_context(db, current_user, note)
    visibility = note.visibility.value if hasattr(note.visibility, "value") else str(note.visibility)
    return visibility == RoleNoteVisibility.AGENT_VISIBLE.value and _is_agent(current_user) and note.employee_id == current_user.id


def can_user_reply_to_note(db: Session, current_user: Employee, note: RoleNote) -> bool:
    return can_user_read_note(db, current_user, note)


def can_user_resolve_note(db: Session, current_user: Employee, note: RoleNote) -> bool:
    return can_user_read_note(db, current_user, note)


def build_note_snapshots(db: Session, payload) -> dict:
    employee = _load_employee(db, payload.employee_id) if _has_value(getattr(payload, "employee_id", None)) else None
    team = _load_team(db, payload.team_id) if _has_value(getattr(payload, "team_id", None)) else None
    call = _load_call(db, payload.call_id) if _has_value(getattr(payload, "call_id", None)) else None
    campaign = _load_campaign(db, payload.campaign_id) if _has_value(getattr(payload, "campaign_id", None)) else None

    return {
        "agent_name_snapshot": employee.name if employee is not None else (call.employee.name if call is not None and call.employee is not None else None),
        "team_name_snapshot": team.name if team is not None else None,
        "campaign_name_snapshot": campaign.name if campaign is not None else (call.campaign.name if call is not None and call.campaign is not None else None),
    }


def root_note_id(note: RoleNote) -> int:
    return note.parent_note_id or note.id


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
