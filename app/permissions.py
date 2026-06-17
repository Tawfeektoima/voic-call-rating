import enum
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models import Employee, UserRole


class Permission(str, enum.Enum):
    VIEW_OWN_DASHBOARD = "dashboard.view_own"
    VIEW_GLOBAL_DASHBOARD = "dashboard.view_global"
    VIEW_OWN_PROFILE = "profile.view_own"
    VIEW_AGENT_PROFILES = "profiles.view_agents"
    VIEW_OWN_CALLS = "calls.view_own"
    VIEW_RAW_CALLS = "calls.view_raw"
    UPLOAD_OWN_CALLS = "calls.upload_own"
    REVIEW_CALLS = "calls.review"
    UPDATE_LEADS = "calls.update_leads"
    VIEW_CAMPAIGNS = "campaigns.view"
    MANAGE_CAMPAIGNS = "campaigns.manage"
    VIEW_SUCCESS_LIBRARY = "success_library.view"
    VIEW_BI = "business_intelligence.view"
    VIEW_DATA_CENTER = "data_center.view"
    VIEW_HR_DASHBOARD = "hr.dashboard.view"
    MANAGE_HR_ONBOARDING = "hr.onboarding.manage"
    VIEW_EMPLOYEES = "employees.view"
    MANAGE_EMPLOYEES = "employees.manage"
    CHANGE_EMPLOYEE_ROLE = "employees.change_role"
    CHANGE_EMPLOYEE_STATUS = "employees.change_status"
    VIEW_AUDIT_LOGS = "audit.view"
    EXPORT_DATA = "exports.run"
    VIEW_SYSTEM_HEALTH = "system.health.view"
    RESOLVE_SYSTEM_ALERTS = "system.alerts.resolve"
    VIEW_OPS_REPORTS = "ops.reports.view"
    VIEW_TEAM_MANAGER_WORKSPACE = "team_manager.workspace.view"
    VIEW_TEAM_LEADER_WORKSPACE = "team_leader.workspace.view"
    VIEW_NOTES = "notes.view"
    MANAGE_KPI_THRESHOLDS = "kpi_thresholds.manage"
    MANAGE_INTERVIEW_JOBS = "hr.interviews.jobs.manage"
    VIEW_INTERVIEW_CANDIDATES = "hr.interviews.candidates.view"
    MANAGE_INTERVIEW_CANDIDATES = "hr.interviews.candidates.manage"
    REVIEW_INTERVIEW_EVALUATIONS = "hr.interviews.evaluations.review"
    CONVERT_INTERVIEW_CANDIDATES = "hr.interviews.candidates.convert"
    EXPORT_INTERVIEW_DATA = "hr.interviews.export"


APPROVED_ROLE_ORDER: tuple[UserRole, ...] = (
    UserRole.AGENT,
    UserRole.TEAM_LEADER,
    UserRole.TEAM_MANAGER,
    UserRole.HR_MANAGER,
    UserRole.QA,
    UserRole.OPS_MANAGER,
    UserRole.ADMIN,
)

ROLE_LABELS: dict[UserRole, str] = {
    UserRole.AGENT: "Agent",
    UserRole.TEAM_LEADER: "Team Leader",
    UserRole.TEAM_MANAGER: "Team Manager",
    UserRole.HR_MANAGER: "HR Manager",
    UserRole.QA: "QA Analyst",
    UserRole.OPS_MANAGER: "Ops Manager",
    UserRole.ADMIN: "Administrator",
}

ROLE_DESCRIPTIONS: dict[UserRole, str] = {
    UserRole.AGENT: "Self-service access to own calls, dashboard, profile, violations, and notes.",
    UserRole.TEAM_LEADER: "Scoped access to assigned team performance, agents, calls, KPIs, and notes.",
    UserRole.TEAM_MANAGER: "Scoped access to managed teams, reports, transfer requests, and notes.",
    UserRole.HR_MANAGER: "Personnel, onboarding, HR violations, people analytics, and role administration.",
    UserRole.QA: "Quality review, campaigns, HR alarms, raw call review, and redacted exports.",
    UserRole.OPS_MANAGER: "Operations dashboards and reporting without raw call or employee mutation access.",
    UserRole.ADMIN: "Full platform administration.",
}

ROLE_ALIASES: dict[str, UserRole] = {
    "HR": UserRole.HR_MANAGER,
    "HUMAN_RESOURCES": UserRole.HR_MANAGER,
    "HR_ADMIN": UserRole.HR_MANAGER,
    "TEAMLEADER": UserRole.TEAM_LEADER,
    "TEAM_LEAD": UserRole.TEAM_LEADER,
    "TEAMMANAGER": UserRole.TEAM_MANAGER,
    "OPS": UserRole.OPS_MANAGER,
    "OPERATIONS": UserRole.OPS_MANAGER,
    "OPERATIONS_MANAGER": UserRole.OPS_MANAGER,
}

ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.AGENT: frozenset({
        Permission.VIEW_OWN_DASHBOARD,
        Permission.VIEW_OWN_PROFILE,
        Permission.VIEW_OWN_CALLS,
        Permission.UPLOAD_OWN_CALLS,
        Permission.VIEW_SUCCESS_LIBRARY,
        Permission.VIEW_NOTES,
    }),
    UserRole.TEAM_LEADER: frozenset({
        Permission.VIEW_TEAM_LEADER_WORKSPACE,
        Permission.VIEW_AGENT_PROFILES,
        Permission.VIEW_SUCCESS_LIBRARY,
        Permission.VIEW_NOTES,
    }),
    UserRole.TEAM_MANAGER: frozenset({
        Permission.VIEW_TEAM_MANAGER_WORKSPACE,
        Permission.VIEW_AGENT_PROFILES,
        Permission.VIEW_NOTES,
    }),
    UserRole.HR_MANAGER: frozenset({
        Permission.VIEW_HR_DASHBOARD,
        Permission.MANAGE_HR_ONBOARDING,
        Permission.VIEW_EMPLOYEES,
        Permission.MANAGE_EMPLOYEES,
        Permission.CHANGE_EMPLOYEE_ROLE,
        Permission.CHANGE_EMPLOYEE_STATUS,
        Permission.MANAGE_INTERVIEW_JOBS,
        Permission.VIEW_INTERVIEW_CANDIDATES,
        Permission.MANAGE_INTERVIEW_CANDIDATES,
        Permission.REVIEW_INTERVIEW_EVALUATIONS,
        Permission.CONVERT_INTERVIEW_CANDIDATES,
        Permission.EXPORT_INTERVIEW_DATA,
        Permission.VIEW_NOTES,
    }),
    UserRole.QA: frozenset({
        Permission.VIEW_GLOBAL_DASHBOARD,
        Permission.VIEW_RAW_CALLS,
        Permission.REVIEW_CALLS,
        Permission.UPDATE_LEADS,
        Permission.VIEW_CAMPAIGNS,
        Permission.VIEW_SUCCESS_LIBRARY,
        Permission.VIEW_AGENT_PROFILES,
        Permission.EXPORT_DATA,
        Permission.VIEW_NOTES,
    }),
    UserRole.OPS_MANAGER: frozenset({
        Permission.VIEW_OPS_REPORTS,
        Permission.VIEW_NOTES,
    }),
    UserRole.ADMIN: frozenset(Permission),
}

HR_ASSIGNABLE_ROLES: frozenset[UserRole] = frozenset(role for role in APPROVED_ROLE_ORDER if role != UserRole.ADMIN)


def normalize_role_value(role_value) -> UserRole:
    if isinstance(role_value, UserRole):
        return role_value
    normalized = str(role_value or "").strip().upper().replace("-", "_").replace(" ", "_")
    if normalized in ROLE_ALIASES:
        return ROLE_ALIASES[normalized]
    return UserRole(normalized)


def _get_static_role_permissions(role_value) -> tuple[str, ...]:
    role = normalize_role_value(role_value)
    return tuple(permission.value for permission in sorted(ROLE_PERMISSIONS.get(role, frozenset()), key=lambda p: p.value))


def get_role_permissions(role_value, db: Session | None = None) -> tuple[str, ...]:
    role = normalize_role_value(role_value)
    if db is not None:
        try:
            from app.services.role_permissions import get_role_permission_values

            return get_role_permission_values(db, role)
        except SQLAlchemyError:
            return _get_static_role_permissions(role)

    try:
        from app.database import SessionLocal
        from app.services.role_permissions import get_role_permission_values

        local_db = SessionLocal()
        try:
            permissions = get_role_permission_values(local_db, role)
            local_db.commit()
            return permissions
        finally:
            local_db.close()
    except SQLAlchemyError:
        return _get_static_role_permissions(role)


def get_role_definition(role_value, db: Session | None = None) -> dict:
    role = normalize_role_value(role_value)
    return {
        "role": role.value,
        "label": ROLE_LABELS[role],
        "description": ROLE_DESCRIPTIONS[role],
        "permissions": list(get_role_permissions(role, db=db)),
        "assignable_by_hr": role in HR_ASSIGNABLE_ROLES,
    }


def list_role_definitions(roles: Iterable[UserRole] | None = None, db: Session | None = None) -> list[dict]:
    return [get_role_definition(role, db=db) for role in (roles or APPROVED_ROLE_ORDER)]


def has_permission(current_user: Employee, permission: Permission) -> bool:
    try:
        role = normalize_role_value(current_user.role)
    except ValueError:
        return False
    return permission.value in get_role_permissions(role)


def require_permission(current_user: Employee, permission: Permission, detail: str = "Access denied.") -> None:
    if not has_permission(current_user, permission):
        raise HTTPException(status_code=403, detail=detail)


def can_assign_role(current_user: Employee, target_role: UserRole) -> bool:
    try:
        actor_role = normalize_role_value(current_user.role)
    except ValueError:
        return False
    if actor_role == UserRole.ADMIN:
        return True
    if actor_role == UserRole.HR_MANAGER:
        return target_role in HR_ASSIGNABLE_ROLES
    return False

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
    require_permission(current_user, Permission.VIEW_OPS_REPORTS, detail=detail)

def require_qa_review_access(current_user: Employee, detail: str = "Access denied.") -> None:
    """Helper to require that the current user is an ADMIN, QA, or HR_MANAGER."""
    require_permission(current_user, Permission.REVIEW_CALLS, detail=detail)

def require_raw_export_access(current_user: Employee, detail: str = "Only admins, QA, and HR managers are authorized to export data.") -> None:
    """Helper to require that the current user is an ADMIN, QA, or HR_MANAGER."""
    require_permission(current_user, Permission.EXPORT_DATA, detail=detail)

def can_view_global_reports(current_user: Employee) -> bool:
    """Returns True if the current user has rights to view global reporting (ADMIN, QA, HR_MANAGER, OPS_MANAGER)."""
    return current_user.role in (UserRole.ADMIN, UserRole.QA, UserRole.HR_MANAGER, UserRole.OPS_MANAGER)

def can_view_raw_call_data(current_user: Employee) -> bool:
    """Returns True if the current user has rights to view raw call data (ADMIN, QA, HR_MANAGER)."""
    return current_user.role in (UserRole.ADMIN, UserRole.QA, UserRole.HR_MANAGER)

def can_view_people_analytics(current_user: Employee) -> bool:
    """Returns True if the current user has rights to view people/agent analytics (ADMIN, QA, HR_MANAGER)."""
    return current_user.role in (UserRole.ADMIN, UserRole.QA, UserRole.HR_MANAGER)

def require_team_manager_access(current_user: Employee) -> None:
    """Raises HTTPException 403 if the current user is not ADMIN or TEAM_MANAGER."""
    require_permission(current_user, Permission.VIEW_TEAM_MANAGER_WORKSPACE)

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
    require_permission(current_user, Permission.VIEW_TEAM_LEADER_WORKSPACE)

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
