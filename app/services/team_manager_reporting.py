from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models import (
    AttendanceRecord,
    Call,
    CallOutcome,
    CallStatus,
    Campaign,
    CampaignType,
    Employee,
    EmployeeTeamAssignment,
    Team,
    UserRole,
)
from app.schemas import (
    TeamManagerAgentDetailOut,
    TeamManagerAgentRowOut,
    TeamManagerAlertOut,
    TeamManagerAttendanceReportOut,
    TeamManagerAttendanceRow,
    TeamManagerConversionReportOut,
    TeamManagerConversionRow,
    TeamManagerDashboardOut,
    TeamManagerKpisOut,
    TeamManagerRevenueReportOut,
    TeamManagerRevenueRow,
    TeamManagerSalesReportOut,
    TeamManagerSalesRow,
    TeamManagerTeamRowOut,
)
from app.services.team_scope import (
    get_managed_team_ids,
    is_agent_in_manager_scope,
    is_team_in_manager_scope,
)

is_success_case = case(
    ((Campaign.type == CampaignType.SALES) & (CallOutcome.primary_outcome == "Sale Closed"), 1),
    ((Campaign.type == CampaignType.CUSTOMER_SERVICE) & (CallOutcome.primary_outcome == "Resolved"), 1),
    ((Campaign.type == CampaignType.COLLECTIONS) & (CallOutcome.primary_outcome.in_(["Promise to Pay", "Payment Arranged"])), 1),
    ((Campaign.type == CampaignType.TECHNICAL) & (CallOutcome.primary_outcome.in_(["Resolved", "Workaround Provided"])), 1),
    else_=0,
)


def _team_ids_for_user(db: Session, current_user: Employee) -> list[int]:
    if current_user.role == UserRole.ADMIN:
        return [row[0] for row in db.query(Team.id).filter(Team.is_active == True).order_by(Team.id.asc()).all()]
    return get_managed_team_ids(db, current_user.id)


def _assignment_query(db: Session, team_ids: list[int]):
    return db.query(EmployeeTeamAssignment).filter(
        EmployeeTeamAssignment.team_id.in_(team_ids),
        EmployeeTeamAssignment.is_active == True,
    )


def _agent_ids_for_teams(db: Session, team_ids: list[int]) -> list[int]:
    if not team_ids:
        return []
    return [row[0] for row in _assignment_query(db, team_ids).with_entities(EmployeeTeamAssignment.employee_id).distinct().order_by(EmployeeTeamAssignment.employee_id.asc()).all()]


def _call_stats_for_agents(db: Session, agent_ids: list[int], start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    query = (
        db.query(
            func.count(Call.id).label("total_calls"),
            func.sum(is_success_case).label("sales"),
            func.sum(func.coalesce(CallOutcome.outcome_value, 0.0)).label("revenue"),
            func.avg(func.coalesce(Call.overridden_score, Call.evaluation_score)).label("avg_qa_score"),
        )
        .select_from(Call)
        .join(Campaign, Call.campaign_id == Campaign.id)
        .outerjoin(CallOutcome, Call.id == CallOutcome.call_id)
        .filter(Call.status == CallStatus.EVALUATED)
    )
    if agent_ids:
        query = query.filter(Call.employee_id.in_(agent_ids))
    else:
        query = query.filter(Call.id == -1)
    if start_date is not None:
        query = query.filter(Call.created_at >= start_date)
    if end_date is not None:
        query = query.filter(Call.created_at <= end_date)
    return query.first()


def _attendance_rate_for_agents(db: Session, agent_ids: list[int], start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> float:
    if not agent_ids:
        return 0.0
    query = db.query(AttendanceRecord).filter(AttendanceRecord.employee_id.in_(agent_ids))
    if start_date is not None:
        query = query.filter(AttendanceRecord.attendance_date >= start_date.date())
    if end_date is not None:
        query = query.filter(AttendanceRecord.attendance_date <= end_date.date())
    records = query.all()
    if not records:
        return 0.0
    present = sum(1 for record in records if (record.status or "").lower() in {"present", "attended", "late"})
    return round((present / len(records)) * 100.0, 2)


def _build_team_rows(db: Session, team_ids: list[int], start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, skip: int = 0, limit: int = 50) -> list[TeamManagerTeamRowOut]:
    if not team_ids:
        return []
    teams = (
        db.query(Team)
        .filter(Team.id.in_(team_ids))
        .order_by(Team.name.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    rows: list[TeamManagerTeamRowOut] = []
    for team in teams:
        agent_ids = [row[0] for row in _assignment_query(db, [team.id]).with_entities(EmployeeTeamAssignment.employee_id).all()]
        stats = _call_stats_for_agents(db, agent_ids, start_date, end_date)
        total_calls = int(stats.total_calls or 0) if stats else 0
        sales = int(stats.sales or 0) if stats else 0
        rows.append(
            TeamManagerTeamRowOut(
                team_id=team.id,
                team_name=team.name,
                campaign_id=team.campaign_id,
                campaign_name=team.campaign.name if team.campaign else None,
                leader_id=team.leader_id,
                leader_name=team.leader.name if team.leader else None,
                agent_count=len(agent_ids),
                sales=sales,
                revenue=float(stats.revenue or 0.0) if stats else 0.0,
                conversion_rate=round((sales / total_calls) * 100.0, 2) if total_calls else 0.0,
                average_qa_score=round(float(stats.avg_qa_score or 0.0), 2) if stats else 0.0,
                attendance_rate=_attendance_rate_for_agents(db, agent_ids, start_date, end_date),
            )
        )
    return rows


def get_team_manager_dashboard(db: Session, current_user: Employee, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> TeamManagerDashboardOut:
    team_ids = _team_ids_for_user(db, current_user)
    agent_ids = _agent_ids_for_teams(db, team_ids)
    stats = _call_stats_for_agents(db, agent_ids, start_date, end_date)
    total_calls = int(stats.total_calls or 0) if stats else 0
    total_sales = int(stats.sales or 0) if stats else 0
    teams = _build_team_rows(db, team_ids, start_date, end_date)
    return TeamManagerDashboardOut(
        total_teams=len(team_ids),
        total_agents=len(agent_ids),
        total_sales=total_sales,
        total_revenue=float(stats.revenue or 0.0) if stats else 0.0,
        average_conversion_rate=round((total_sales / total_calls) * 100.0, 2) if total_calls else 0.0,
        average_qa_score=round(float(stats.avg_qa_score or 0.0), 2) if stats else 0.0,
        attendance_rate=_attendance_rate_for_agents(db, agent_ids, start_date, end_date),
        teams=teams,
        alerts=[],
    )


def get_team_manager_teams(db: Session, current_user: Employee, skip: int = 0, limit: int = 50) -> list[TeamManagerTeamRowOut]:
    return _build_team_rows(db, _team_ids_for_user(db, current_user), skip=skip, limit=limit)


def get_team_manager_team_detail(db: Session, current_user: Employee, team_id: int) -> TeamManagerTeamRowOut:
    if current_user.role != UserRole.ADMIN and not is_team_in_manager_scope(db, current_user.id, team_id):
        raise HTTPException(status_code=403, detail="Access denied.")
    rows = _build_team_rows(db, [team_id], skip=0, limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="Team not found.")
    return rows[0]


def get_team_manager_agents(db: Session, current_user: Employee, team_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> list[TeamManagerAgentRowOut]:
    team_ids = _team_ids_for_user(db, current_user)
    if team_id is not None:
        if current_user.role != UserRole.ADMIN and team_id not in team_ids:
            raise HTTPException(status_code=403, detail="Access denied.")
        team_ids = [team_id]
    if not team_ids:
        return []

    assignments = (
        db.query(EmployeeTeamAssignment)
        .join(Employee, Employee.id == EmployeeTeamAssignment.employee_id)
        .filter(EmployeeTeamAssignment.team_id.in_(team_ids), EmployeeTeamAssignment.is_active == True)
        .order_by(Employee.name.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    rows: list[TeamManagerAgentRowOut] = []
    for assignment in assignments:
        agent = assignment.employee
        team = assignment.team
        stats = _call_stats_for_agents(db, [agent.id])
        total_calls = int(stats.total_calls or 0) if stats else 0
        sales = int(stats.sales or 0) if stats else 0
        rows.append(
            TeamManagerAgentRowOut(
                agent_id=agent.id,
                agent_name=agent.name,
                email=agent.email,
                team_id=team.id,
                team_name=team.name,
                campaign_id=team.campaign_id,
                campaign_name=team.campaign.name if team.campaign else None,
                sales=sales,
                revenue=float(stats.revenue or 0.0) if stats else 0.0,
                conversion_rate=round((sales / total_calls) * 100.0, 2) if total_calls else 0.0,
                qa_score=round(float(stats.avg_qa_score or 0.0), 2) if stats and total_calls else None,
                attendance_rate=_attendance_rate_for_agents(db, [agent.id]),
                status=agent.status or "active",
            )
        )
    return rows


def get_team_manager_agent_detail(db: Session, current_user: Employee, agent_id: int) -> TeamManagerAgentDetailOut:
    if current_user.role != UserRole.ADMIN and not is_agent_in_manager_scope(db, current_user.id, agent_id):
        raise HTTPException(status_code=403, detail="Access denied.")
    agent = db.query(Employee).filter(Employee.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    assignment = (
        db.query(EmployeeTeamAssignment)
        .filter(EmployeeTeamAssignment.employee_id == agent_id, EmployeeTeamAssignment.is_active == True)
        .first()
    )
    team = assignment.team if assignment else None
    stats = _call_stats_for_agents(db, [agent.id])
    total_calls = int(stats.total_calls or 0) if stats else 0
    sales = int(stats.sales or 0) if stats else 0
    return TeamManagerAgentDetailOut(
        agent_id=agent.id,
        agent_name=agent.name,
        email=agent.email,
        employee_code=agent.employee_code,
        team_id=team.id if team else 0,
        team_name=team.name if team else "No Team",
        campaign_id=team.campaign_id if team else None,
        campaign_name=team.campaign.name if team and team.campaign else None,
        sales=sales,
        revenue=float(stats.revenue or 0.0) if stats else 0.0,
        conversion_rate=round((sales / total_calls) * 100.0, 2) if total_calls else 0.0,
        qa_score=round(float(stats.avg_qa_score or 0.0), 2) if stats and total_calls else None,
        attendance_rate=_attendance_rate_for_agents(db, [agent.id]),
        status=agent.status or "active",
        created_at=agent.created_at,
    )


def get_team_manager_sales_report(db: Session, current_user: Employee, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> TeamManagerSalesReportOut:
    teams = _build_team_rows(db, _team_ids_for_user(db, current_user), start_date, end_date)
    rows = [TeamManagerSalesRow(team_id=team.team_id, team_name=team.team_name, sales=team.sales, total_calls=0) for team in teams]
    return TeamManagerSalesReportOut(teams=rows, total_sales=sum(row.sales for row in rows))


def get_team_manager_revenue_report(db: Session, current_user: Employee, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> TeamManagerRevenueReportOut:
    teams = _build_team_rows(db, _team_ids_for_user(db, current_user), start_date, end_date)
    rows = [TeamManagerRevenueRow(team_id=team.team_id, team_name=team.team_name, revenue=team.revenue) for team in teams]
    return TeamManagerRevenueReportOut(teams=rows, total_revenue=round(sum(row.revenue for row in rows), 2))


def get_team_manager_conversion_report(db: Session, current_user: Employee, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> TeamManagerConversionReportOut:
    teams = _build_team_rows(db, _team_ids_for_user(db, current_user), start_date, end_date)
    rows = [TeamManagerConversionRow(team_id=team.team_id, team_name=team.team_name, sales=team.sales, total_calls=0, conversion_rate=team.conversion_rate) for team in teams]
    average = round(sum(row.conversion_rate for row in rows) / len(rows), 2) if rows else 0.0
    return TeamManagerConversionReportOut(teams=rows, average_conversion_rate=average)


def get_team_manager_attendance_report(db: Session, current_user: Employee, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> TeamManagerAttendanceReportOut:
    agent_ids = _agent_ids_for_teams(db, _team_ids_for_user(db, current_user))
    query = db.query(AttendanceRecord).filter(AttendanceRecord.employee_id.in_(agent_ids)) if agent_ids else db.query(AttendanceRecord).filter(AttendanceRecord.id == -1)
    if start_date is not None:
        query = query.filter(AttendanceRecord.attendance_date >= start_date.date())
    if end_date is not None:
        query = query.filter(AttendanceRecord.attendance_date <= end_date.date())
    records = query.order_by(AttendanceRecord.attendance_date.desc()).all()
    rows = [
        TeamManagerAttendanceRow(
            agent_id=record.employee_id,
            agent_name=record.employee.name if record.employee else "Unknown",
            attendance_date=record.attendance_date.isoformat(),
            status=record.status,
            scheduled_minutes=record.scheduled_minutes,
            worked_minutes=record.worked_minutes,
            late_minutes=record.late_minutes,
        )
        for record in records
    ]
    return TeamManagerAttendanceReportOut(records=rows, attendance_rate=_attendance_rate_for_agents(db, agent_ids, start_date, end_date))


def get_team_manager_kpis(db: Session, current_user: Employee, month: Optional[str] = None) -> TeamManagerKpisOut:
    if not month:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
    dashboard = get_team_manager_dashboard(db, current_user)
    return TeamManagerKpisOut(
        month=month,
        total_sales=dashboard.total_sales,
        total_revenue=dashboard.total_revenue,
        average_qa_score=dashboard.average_qa_score,
        average_conversion_rate=dashboard.average_conversion_rate,
        attendance_rate=dashboard.attendance_rate,
    )
