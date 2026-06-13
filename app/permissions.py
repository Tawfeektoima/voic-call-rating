from fastapi import HTTPException
from app.models import Employee, UserRole

def require_roles(current_user: Employee, allowed_roles: tuple[UserRole, ...], detail: str = "Access denied.") -> None:
    """Helper to check if the current user has one of the allowed roles.
    Raises HTTPException 403 if they do not.
    """
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail=detail)

def require_admin(current_user: Employee, detail: str = "Access denied.") -> None:
    """Helper to require that the current user has the ADMIN role."""
    require_roles(current_user, (UserRole.ADMIN,), detail=detail)

def require_ops_reporting_access(current_user: Employee, detail: str = "Access denied.") -> None:
    """Helper to require that the current user is an ADMIN or an OPS_MANAGER."""
    require_roles(current_user, (UserRole.ADMIN, UserRole.OPS_MANAGER), detail=detail)

def require_qa_review_access(current_user: Employee, detail: str = "Access denied.") -> None:
    """Helper to require that the current user is an ADMIN, QA, or HR_MANAGER."""
    require_roles(current_user, (UserRole.ADMIN, UserRole.QA, UserRole.HR_MANAGER), detail=detail)

def require_raw_export_access(current_user: Employee, detail: str = "Only admins, QA, and HR managers are authorized to export data.") -> None:
    """Helper to require that the current user is an ADMIN, QA, or HR_MANAGER."""
    require_roles(current_user, (UserRole.ADMIN, UserRole.QA, UserRole.HR_MANAGER), detail=detail)

def can_view_global_reports(current_user: Employee) -> bool:
    """Returns True if the current user has rights to view global reporting (ADMIN, QA, HR_MANAGER, OPS_MANAGER)."""
    return current_user.role in (UserRole.ADMIN, UserRole.QA, UserRole.HR_MANAGER, UserRole.OPS_MANAGER)

def can_view_raw_call_data(current_user: Employee) -> bool:
    """Returns True if the current user has rights to view raw call data (ADMIN, QA, HR_MANAGER)."""
    return current_user.role in (UserRole.ADMIN, UserRole.QA, UserRole.HR_MANAGER)

def can_view_people_analytics(current_user: Employee) -> bool:
    """Returns True if the current user has rights to view people/agent analytics (ADMIN, QA, HR_MANAGER)."""
    return current_user.role in (UserRole.ADMIN, UserRole.QA, UserRole.HR_MANAGER)

from sqlalchemy.orm import Session

def require_team_manager_access(current_user: Employee) -> None:
    """Raises HTTPException 403 if the current user is not ADMIN or TEAM_MANAGER."""
    if current_user.role not in (UserRole.ADMIN, UserRole.TEAM_MANAGER):
        raise HTTPException(status_code=403, detail="Access denied.")

def can_view_team_reports(current_user: Employee) -> bool:
    """Returns True if the role is ADMIN or TEAM_MANAGER."""
    return current_user.role in (UserRole.ADMIN, UserRole.TEAM_MANAGER)

def can_view_team(db: Session, current_user: Employee, team_id: int) -> bool:
    """Returns True if ADMIN, or if TEAM_MANAGER and team is in their scope."""
    if current_user.role == UserRole.ADMIN:
        return True
    if current_user.role == UserRole.TEAM_MANAGER:
        from app.services.team_scope import is_team_in_manager_scope
        return is_team_in_manager_scope(db, current_user.id, team_id)
    return False

def can_view_team_agent(db: Session, current_user: Employee, agent_id: int) -> bool:
    """Returns True if ADMIN, or if TEAM_MANAGER and agent is in their scope."""
    if current_user.role == UserRole.ADMIN:
        return True
    if current_user.role == UserRole.TEAM_MANAGER:
        from app.services.team_scope import is_agent_in_manager_scope
        return is_agent_in_manager_scope(db, current_user.id, agent_id)
    return False

def can_request_agent_transfer(db: Session, current_user: Employee, agent_id: int) -> bool:
    """Returns True if ADMIN, or if TEAM_MANAGER and agent is in their scope."""
    if current_user.role == UserRole.ADMIN:
        return True
    if current_user.role == UserRole.TEAM_MANAGER:
        from app.services.team_scope import is_agent_in_manager_scope
        return is_agent_in_manager_scope(db, current_user.id, agent_id)
    return False

def can_view_team_call(db: Session, current_user: Employee, call_id: int) -> bool:
    """Returns True if ADMIN, or if TEAM_MANAGER and call's agent is in their scope."""
    if current_user.role == UserRole.ADMIN:
        return True
    if current_user.role == UserRole.TEAM_MANAGER:
        from app.models import Call
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            return False
        from app.services.team_scope import is_agent_in_manager_scope
        return is_agent_in_manager_scope(db, current_user.id, call.employee_id)
    return False

def require_team_leader_access(current_user: Employee) -> None:
    """Raises HTTPException 403 if the current user is not ADMIN or TEAM_LEADER."""
    if current_user.role not in (UserRole.ADMIN, UserRole.TEAM_LEADER):
        raise HTTPException(status_code=403, detail="Access denied.")

def can_view_led_team(db: Session, current_user: Employee, team_id: int) -> bool:
    """Returns True if ADMIN, or if TEAM_LEADER and team is in their scope."""
    if current_user.role == UserRole.ADMIN:
        return True
    if current_user.role == UserRole.TEAM_LEADER:
        from app.services.team_scope import is_team_in_leader_scope
        return is_team_in_leader_scope(db, current_user.id, team_id)
    return False

def can_view_led_team_agent(db: Session, current_user: Employee, agent_id: int) -> bool:
    """Returns True if ADMIN, or if TEAM_LEADER and agent is in their scope."""
    if current_user.role == UserRole.ADMIN:
        return True
    if current_user.role == UserRole.TEAM_LEADER:
        from app.services.team_scope import is_agent_in_leader_scope
        return is_agent_in_leader_scope(db, current_user.id, agent_id)
    return False

def can_view_led_team_call(db: Session, current_user: Employee, call_id: int) -> bool:
    """Returns True if ADMIN, or if TEAM_LEADER and call's agent is in their scope."""
    if current_user.role == UserRole.ADMIN:
        return True
    if current_user.role == UserRole.TEAM_LEADER:
        from app.models import Call
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            return False
        from app.services.team_scope import is_agent_in_leader_scope
        return is_agent_in_leader_scope(db, current_user.id, call.employee_id)
    return False