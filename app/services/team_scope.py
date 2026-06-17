from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import Team, EmployeeTeamAssignment, Employee, Call
from typing import Optional, List

def get_managed_team_ids(db: Session, manager_id: int) -> List[int]:
    """Returns a list of active team IDs where Team.manager_id == manager_id."""
    teams = db.query(Team.id).filter(Team.manager_id == manager_id, Team.is_active == True).all()
    return [t[0] for t in teams]

def get_led_team_ids(db: Session, leader_id: int) -> List[int]:
    """Returns a list of active team IDs where Team.leader_id == leader_id."""
    teams = db.query(Team.id).filter(Team.leader_id == leader_id, Team.is_active == True).all()
    return [t[0] for t in teams]

def get_team_manager_agent_ids(db: Session, manager_id: int) -> List[int]:
    """Return unique active assigned employee IDs using SQL distinct() with deterministic ordering."""
    team_ids = get_managed_team_ids(db, manager_id)
    if not team_ids:
        return []
    assignments = db.query(EmployeeTeamAssignment.employee_id).filter(
        EmployeeTeamAssignment.team_id.in_(team_ids),
        EmployeeTeamAssignment.is_active == True
    ).distinct().order_by(EmployeeTeamAssignment.employee_id).all()
    return [a[0] for a in assignments]

def is_team_in_manager_scope(db: Session, manager_id: int, team_id: int) -> bool:
    """Returns True if the team is active and owned by the manager."""
    team = db.query(Team).filter(
        Team.id == team_id,
        Team.manager_id == manager_id,
        Team.is_active == True
    ).first()
    return team is not None

def is_agent_in_manager_scope(db: Session, manager_id: int, agent_id: int) -> bool:
    """Returns True if the agent is actively assigned to an active team managed by the manager."""
    team_ids = get_managed_team_ids(db, manager_id)
    if not team_ids:
        return False
    assignment = db.query(EmployeeTeamAssignment).filter(
        EmployeeTeamAssignment.employee_id == agent_id,
        EmployeeTeamAssignment.team_id.in_(team_ids),
        EmployeeTeamAssignment.is_active == True
    ).first()
    return assignment is not None

def scope_employee_query_to_team_manager(query, db: Session, manager_id: int):
    """Filter by joining EmployeeTeamAssignment on Employee.id == EmployeeTeamAssignment.employee_id,
    then require active assignments in managed active teams.
    """
    team_ids = get_managed_team_ids(db, manager_id)
    if not team_ids:
        return query.filter(Employee.id == -1)
    return query.join(EmployeeTeamAssignment, Employee.id == EmployeeTeamAssignment.employee_id).filter(
        EmployeeTeamAssignment.team_id.in_(team_ids),
        EmployeeTeamAssignment.is_active == True
    )

def scope_call_query_to_team_manager(query, db: Session, manager_id: int):
    """Filter calls by joining active team assignments through Call.employee_id."""
    team_ids = get_managed_team_ids(db, manager_id)
    if not team_ids:
        return query.filter(Call.id == -1)
    return query.join(EmployeeTeamAssignment, Call.employee_id == EmployeeTeamAssignment.employee_id).filter(
        EmployeeTeamAssignment.team_id.in_(team_ids),
        EmployeeTeamAssignment.is_active == True
    )

def get_active_assignment_for_agent(db: Session, agent_id: int) -> Optional[EmployeeTeamAssignment]:
    """Assume v1 policy: one active team assignment per employee.
    Returns the active assignment if one exists.
    """
    return db.query(EmployeeTeamAssignment).filter(
        EmployeeTeamAssignment.employee_id == agent_id,
        EmployeeTeamAssignment.is_active == True
    ).first()

def is_agent_assigned_to_team(db: Session, agent_id: int, team_id: int) -> bool:
    """Returns True if the agent is actively assigned to team_id."""
    assignment = db.query(EmployeeTeamAssignment).filter(
        EmployeeTeamAssignment.employee_id == agent_id,
        EmployeeTeamAssignment.team_id == team_id,
        EmployeeTeamAssignment.is_active == True
    ).first()
    return assignment is not None

def get_team_leader_agent_ids(db: Session, leader_id: int) -> List[int]:
    """Return unique active assigned employee IDs under teams led by the leader."""
    team_ids = get_led_team_ids(db, leader_id)
    if not team_ids:
        return []
    assignments = db.query(EmployeeTeamAssignment.employee_id).filter(
        EmployeeTeamAssignment.team_id.in_(team_ids),
        EmployeeTeamAssignment.is_active == True
    ).distinct().order_by(EmployeeTeamAssignment.employee_id).all()
    return [a[0] for a in assignments]

def is_team_in_leader_scope(db: Session, leader_id: int, team_id: int) -> bool:
    """Returns True if the team is active and led by the leader."""
    team = db.query(Team).filter(
        Team.id == team_id,
        Team.leader_id == leader_id,
        Team.is_active == True
    ).first()
    return team is not None

def is_agent_in_leader_scope(db: Session, leader_id: int, agent_id: int) -> bool:
    """Returns True if the agent is actively assigned to an active team led by the leader."""
    team_ids = get_led_team_ids(db, leader_id)
    if not team_ids:
        return False
    assignment = db.query(EmployeeTeamAssignment).filter(
        EmployeeTeamAssignment.employee_id == agent_id,
        EmployeeTeamAssignment.team_id.in_(team_ids),
        EmployeeTeamAssignment.is_active == True
    ).first()
    return assignment is not None

def scope_employee_query_to_team_leader(query, db: Session, leader_id: int):
    """Filter employees by joining EmployeeTeamAssignment and checking led teams."""
    team_ids = get_led_team_ids(db, leader_id)
    if not team_ids:
        return query.filter(Employee.id == -1)
    return query.join(EmployeeTeamAssignment, Employee.id == EmployeeTeamAssignment.employee_id).filter(
        EmployeeTeamAssignment.team_id.in_(team_ids),
        EmployeeTeamAssignment.is_active == True
    )

def scope_call_query_to_team_leader(query, db: Session, leader_id: int):
    """Filter calls by joining active team assignments through Call.employee_id under led teams."""
    team_ids = get_led_team_ids(db, leader_id)
    if not team_ids:
        return query.filter(Call.id == -1)
    return query.join(EmployeeTeamAssignment, Call.employee_id == EmployeeTeamAssignment.employee_id).filter(
        EmployeeTeamAssignment.team_id.in_(team_ids),
        EmployeeTeamAssignment.is_active == True
    )


def get_qa_scope(db: Session, qa_id: int) -> tuple[Optional[int], Optional[int]]:
    qa_user = db.query(Employee).filter(Employee.id == qa_id).first()
    if not qa_user:
        return None, None
    return qa_user.qa_scope_team_id, qa_user.qa_scope_campaign_id


def scope_employee_query_to_qa(query, db: Session, qa_id: int):
    """Filter employees to the QA user's assigned active team only."""
    team_id, _ = get_qa_scope(db, qa_id)
    if not team_id:
        return query.filter(Employee.id == -1)
    return query.join(
        EmployeeTeamAssignment,
        and_(
            Employee.id == EmployeeTeamAssignment.employee_id,
            EmployeeTeamAssignment.is_active == True,
        ),
    ).filter(EmployeeTeamAssignment.team_id == team_id)


def scope_call_query_to_qa(query, db: Session, qa_id: int):
    """Filter calls to the QA user's assigned team and optional campaign."""
    team_id, campaign_id = get_qa_scope(db, qa_id)
    if not team_id:
        return query.filter(Call.id == -1)
    query = query.join(
        EmployeeTeamAssignment,
        and_(
            Call.employee_id == EmployeeTeamAssignment.employee_id,
            EmployeeTeamAssignment.is_active == True,
        ),
    ).filter(EmployeeTeamAssignment.team_id == team_id)
    if campaign_id is not None:
        query = query.filter(Call.campaign_id == campaign_id)
    return query


def is_agent_in_qa_scope(db: Session, qa_id: int, agent_id: int) -> bool:
    team_id, _ = get_qa_scope(db, qa_id)
    if not team_id:
        return False
    assignment = db.query(EmployeeTeamAssignment).filter(
        EmployeeTeamAssignment.employee_id == agent_id,
        EmployeeTeamAssignment.team_id == team_id,
        EmployeeTeamAssignment.is_active == True,
    ).first()
    return assignment is not None


def is_call_in_qa_scope(db: Session, qa_id: int, call_id: int) -> bool:
    query = scope_call_query_to_qa(db.query(Call.id), db, qa_id).filter(Call.id == call_id)
    return query.first() is not None
