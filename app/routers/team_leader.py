from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timezone
from typing import List, Optional

from app.database import get_db
from app.models import (
    Employee,
    UserRole,
    Team,
    EmployeeTeamAssignment,
    Call,
    CallStatus,
    Campaign,
    CampaignType,
    CallOutcome,
    AgentTransferRequest,
    RoleNote
)
from app.schemas import (
    TeamLeaderDashboardOut,
    TeamLeaderTeamRowOut,
    TeamLeaderAgentRowOut,
    TeamLeaderCallRowOut,
    TeamLeaderKpisOut
)
from app.routers.auth import get_current_user
from app.permissions import require_team_leader_access
from app.services.team_scope import get_led_team_ids, get_team_leader_agent_ids

router = APIRouter(prefix="/api/team-leader", tags=["Team Leader Scoped Endpoints"])

is_success_case = case(
    (
        (Campaign.type == CampaignType.SALES) & (CallOutcome.primary_outcome == 'Sale Closed'),
        1
    ),
    (
        (Campaign.type == CampaignType.CUSTOMER_SERVICE) & (CallOutcome.primary_outcome == 'Resolved'),
        1
    ),
    (
        (Campaign.type == CampaignType.COLLECTIONS) & (CallOutcome.primary_outcome.in_(['Promise to Pay', 'Payment Arranged'])),
        1
    ),
    (
        (Campaign.type == CampaignType.TECHNICAL) & (CallOutcome.primary_outcome.in_(['Resolved', 'Workaround Provided'])),
        1
    ),
    else_=0
)

def _get_leader_team_ids(db: Session, current_user: Employee) -> List[int]:
    if current_user.role == UserRole.ADMIN:
        teams = db.query(Team.id).filter(Team.is_active == True).all()
        return [t[0] for t in teams]
    return get_led_team_ids(db, current_user.id)

@router.get('/dashboard', response_model=TeamLeaderDashboardOut)
def get_team_leader_dashboard(db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    require_team_leader_access(current_user)
    team_ids = _get_leader_team_ids(db, current_user)
    if not team_ids:
        return TeamLeaderDashboardOut(
            team_count=0,
            agent_count=0,
            average_qa_score=0.0,
            attendance_rate=0.0,
            sales=0,
            revenue=0.0,
            conversion_rate=0.0,
            pending_notes_count=0,
            pending_transfer_requests_count=0
        )
        
    active_assignments = db.query(EmployeeTeamAssignment.employee_id).filter(
        EmployeeTeamAssignment.team_id.in_(team_ids),
        EmployeeTeamAssignment.is_active == True
    ).distinct().all()
    agent_ids = [a[0] for a in active_assignments]
    team_count = len(team_ids)
    agent_count = len(agent_ids)
    
    sales = 0
    revenue = 0.0
    average_qa_score = 0.0
    conversion_rate = 0.0
    
    if agent_ids:
        call_q = db.query(
            func.count(Call.id).label('total_calls'),
            func.sum(is_success_case).label('sales'),
            func.sum(func.coalesce(CallOutcome.outcome_value, 0.0)).label('revenue'),
            func.avg(func.coalesce(Call.overridden_score, Call.evaluation_score)).label('qa_score')
        ).select_from(Call).join(Campaign, Call.campaign_id == Campaign.id).outerjoin(
            CallOutcome, Call.id == CallOutcome.call_id
        ).filter(
            Call.status == CallStatus.EVALUATED,
            Call.employee_id.in_(agent_ids)
        )
        res = call_q.first()
        total_calls = res.total_calls if res and res.total_calls else 0
        sales = res.sales if res and res.sales else 0
        revenue = float(res.revenue) if res and res.revenue else 0.0
        average_qa_score = float(res.qa_score) if res and res.qa_score else 0.0
        conversion_rate = float(sales * 100.0 / total_calls) if total_calls > 0 else 0.0
        
    led_camp_ids_query = db.query(Team.campaign_id).filter(
        Team.id.in_(team_ids)
    ).all()
    led_camp_ids = [t[0] for t in led_camp_ids_query if t[0] is not None]
    
    notes_q = db.query(RoleNote).filter(
        RoleNote.parent_note_id.is_(None),
        RoleNote.status != 'RESOLVED'
    )
    if current_user.role != UserRole.ADMIN:
        notes_q = notes_q.filter(
            (RoleNote.recipient_id == current_user.id) | (
                (RoleNote.recipient_role == 'TEAM_LEADER') & (
                    RoleNote.team_id.in_(team_ids) |
                    RoleNote.employee_id.in_(agent_ids) |
                    RoleNote.campaign_id.in_(led_camp_ids)
                )
            )
        )
    else:
        notes_q = notes_q.filter(
            (RoleNote.recipient_id == current_user.id) | (RoleNote.recipient_role == 'ADMIN')
        )
    pending_notes_count = notes_q.count()
    
    pending_transfer_requests_count = db.query(AgentTransferRequest).filter(
        AgentTransferRequest.status == 'PENDING',
        AgentTransferRequest.agent_id.in_(agent_ids)
    ).count()
    
    return TeamLeaderDashboardOut(
        team_count=team_count,
        agent_count=agent_count,
        average_qa_score=average_qa_score,
        attendance_rate=0.0,
        sales=sales,
        revenue=revenue,
        conversion_rate=conversion_rate,
        pending_notes_count=pending_notes_count,
        pending_transfer_requests_count=pending_transfer_requests_count
    )

@router.get('/teams', response_model=List[TeamLeaderTeamRowOut])
def get_team_leader_teams(db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    require_team_leader_access(current_user)
    team_ids = _get_leader_team_ids(db, current_user)
    if not team_ids:
        return []
        
    team_records = db.query(Team).filter(Team.id.in_(team_ids)).order_by(Team.name.asc()).all()
    team_rows = []
    
    for team in team_records:
        team_agents = db.query(EmployeeTeamAssignment.employee_id).filter(
            EmployeeTeamAssignment.team_id == team.id,
            EmployeeTeamAssignment.is_active == True
        ).all()
        t_agent_ids = [ta[0] for ta in team_agents]
        agent_count = len(t_agent_ids)
        
        t_sales = 0
        t_revenue = 0.0
        t_qa_score = 0.0
        t_conversion = 0.0
        
        if t_agent_ids:
            t_call_q = db.query(
                func.count(Call.id).label('total_calls'),
                func.sum(is_success_case).label('sales'),
                func.sum(func.coalesce(CallOutcome.outcome_value, 0.0)).label('revenue'),
                func.avg(func.coalesce(Call.overridden_score, Call.evaluation_score)).label('qa_score')
            ).select_from(Call).join(Campaign, Call.campaign_id == Campaign.id).outerjoin(
                CallOutcome, Call.id == CallOutcome.call_id
            ).filter(
                Call.status == CallStatus.EVALUATED,
                Call.employee_id.in_(t_agent_ids)
            )
            t_res = t_call_q.first()
            t_total_calls = t_res.total_calls if t_res and t_res.total_calls else 0
            t_sales = t_res.sales if t_res and t_res.sales else 0
            t_revenue = float(t_res.revenue) if t_res and t_res.revenue else 0.0
            t_qa_score = float(t_res.qa_score) if t_res and t_res.qa_score else 0.0
            t_conversion = float(t_sales * 100.0 / t_total_calls) if t_total_calls > 0 else 0.0
            
        team_rows.append(
            TeamLeaderTeamRowOut(
                team_id=team.id,
                team_name=team.name,
                campaign_id=team.campaign_id,
                campaign_name=team.campaign.name if team.campaign else None,
                leader_id=team.leader_id,
                leader_name=team.leader.name if team.leader else None,
                agent_count=agent_count,
                sales=t_sales,
                revenue=t_revenue,
                conversion_rate=t_conversion,
                average_qa_score=t_qa_score,
                attendance_rate=0.0
            )
        )
    return team_rows

@router.get('/agents', response_model=List[TeamLeaderAgentRowOut])
def get_team_leader_agents(
    team_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_leader_access(current_user)
    team_ids = _get_leader_team_ids(db, current_user)
    
    if team_id is not None:
        if team_id not in team_ids:
            raise HTTPException(status_code=403, detail="Access denied.")
        target_team_ids = [team_id]
    else:
        target_team_ids = team_ids
        
    if not target_team_ids:
        return []
        
    assignments = db.query(EmployeeTeamAssignment).join(
        Employee, EmployeeTeamAssignment.employee_id == Employee.id
    ).filter(
        EmployeeTeamAssignment.team_id.in_(target_team_ids),
        EmployeeTeamAssignment.is_active == True
    ).order_by(Employee.name.asc()).all()
    
    agent_rows = []
    for assign in assignments:
        agent = assign.employee
        team = assign.team
        if not agent or not team:
            continue
            
        call_q = db.query(
            func.count(Call.id).label('total_calls'),
            func.sum(is_success_case).label('sales'),
            func.sum(func.coalesce(CallOutcome.outcome_value, 0.0)).label('revenue'),
            func.avg(func.coalesce(Call.overridden_score, Call.evaluation_score)).label('qa_score')
        ).select_from(Call).join(Campaign, Call.campaign_id == Campaign.id).outerjoin(
            CallOutcome, Call.id == CallOutcome.call_id
        ).filter(
            Call.status == CallStatus.EVALUATED,
            Call.employee_id == agent.id
        )
        res = call_q.first()
        total_calls = res.total_calls if res and res.total_calls else 0
        sales = res.sales if res and res.sales else 0
        revenue = float(res.revenue) if res and res.revenue else 0.0
        qa_score = float(res.qa_score) if total_calls > 0 and res and res.qa_score else None
        conversion = float(sales * 100.0 / total_calls) if total_calls > 0 else 0.0
        
        agent_rows.append(
            TeamLeaderAgentRowOut(
                agent_id=agent.id,
                agent_name=agent.name,
                email=agent.email,
                team_id=team.id,
                team_name=team.name,
                campaign_id=team.campaign_id,
                campaign_name=team.campaign.name if team.campaign else None,
                sales=sales,
                revenue=revenue,
                conversion_rate=conversion,
                qa_score=qa_score,
                attendance_rate=0.0,
                status=agent.status or 'active'
            )
        )
    return agent_rows

@router.get('/agents/{agent_id}', response_model=TeamLeaderAgentRowOut)
def get_team_leader_agent_detail(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_leader_access(current_user)
    if current_user.role != UserRole.ADMIN:
        from app.services.team_scope import is_agent_in_leader_scope
        if not is_agent_in_leader_scope(db, current_user.id, agent_id):
            raise HTTPException(status_code=403, detail="Access denied.")
            
    agent = db.query(Employee).filter(Employee.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
        
    assign = db.query(EmployeeTeamAssignment).filter(
        EmployeeTeamAssignment.employee_id == agent_id,
        EmployeeTeamAssignment.is_active == True
    ).first()
    
    if assign:
        team_id = assign.team.id
        team_name = assign.team.name
        campaign_id = assign.team.campaign_id
        campaign_name = assign.team.campaign.name if assign.team.campaign else None
    else:
        team_id = 0
        team_name = 'No Team'
        campaign_id = None
        campaign_name = None
        
    call_q = db.query(
        func.count(Call.id).label('total_calls'),
        func.sum(is_success_case).label('sales'),
        func.sum(func.coalesce(CallOutcome.outcome_value, 0.0)).label('revenue'),
        func.avg(func.coalesce(Call.overridden_score, Call.evaluation_score)).label('qa_score')
    ).select_from(Call).join(Campaign, Call.campaign_id == Campaign.id).outerjoin(
        CallOutcome, Call.id == CallOutcome.call_id
    ).filter(
        Call.status == CallStatus.EVALUATED,
        Call.employee_id == agent.id
    )
    res = call_q.first()
    total_calls = res.total_calls if res and res.total_calls else 0
    sales = res.sales if res and res.sales else 0
    revenue = float(res.revenue) if res and res.revenue else 0.0
    qa_score = float(res.qa_score) if total_calls > 0 and res and res.qa_score else None
    conversion = float(sales * 100.0 / total_calls) if total_calls > 0 else 0.0
    
    return TeamLeaderAgentRowOut(
        agent_id=agent.id,
        agent_name=agent.name,
        email=agent.email,
        team_id=team_id,
        team_name=team_name,
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        sales=sales,
        revenue=revenue,
        conversion_rate=conversion,
        qa_score=qa_score,
        attendance_rate=0.0,
        status=agent.status or 'active'
    )

@router.get('/calls', response_model=List[TeamLeaderCallRowOut])
def get_team_leader_calls(
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_leader_access(current_user)
    team_ids = _get_leader_team_ids(db, current_user)
    if not team_ids:
        response.headers["X-Total-Count"] = "0"
        return []
        
    active_assignments = db.query(EmployeeTeamAssignment.employee_id).filter(
        EmployeeTeamAssignment.team_id.in_(team_ids),
        EmployeeTeamAssignment.is_active == True
    ).distinct().all()
    agent_ids = [a[0] for a in active_assignments]
    
    if not agent_ids:
        response.headers["X-Total-Count"] = "0"
        return []
        
    query = db.query(Call).filter(
        Call.employee_id.in_(agent_ids),
        Call.status == CallStatus.EVALUATED
    )
    total_count = query.count()
    response.headers["X-Total-Count"] = str(total_count)
    
    calls = query.order_by(Call.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        TeamLeaderCallRowOut(
            id=c.id,
            employee_id=c.employee_id,
            employee_name=c.employee.name if c.employee else None,
            campaign_id=c.campaign_id,
            campaign_name=c.campaign.name if c.campaign else None,
            status=c.status.value if hasattr(c.status, 'value') else str(c.status),
            evaluation_score=c.evaluation_score,
            overridden_score=c.overridden_score,
            audio_duration=c.audio_duration,
            created_at=c.created_at
        )
        for c in calls
    ]

@router.get('/calls/{call_id}', response_model=TeamLeaderCallRowOut)
def get_team_leader_call_detail(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_leader_access(current_user)
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found.")
    if current_user.role != UserRole.ADMIN:
        from app.services.team_scope import is_agent_in_leader_scope
        if not is_agent_in_leader_scope(db, current_user.id, call.employee_id):
            raise HTTPException(status_code=403, detail="Access denied.")
    return TeamLeaderCallRowOut(
        id=call.id,
        employee_id=call.employee_id,
        employee_name=call.employee.name if call.employee else None,
        campaign_id=call.campaign_id,
        campaign_name=call.campaign.name if call.campaign else None,
        status=call.status.value if hasattr(call.status, 'value') else str(call.status),
        evaluation_score=call.evaluation_score,
        overridden_score=call.overridden_score,
        audio_duration=call.audio_duration,
        created_at=call.created_at
    )

@router.get('/kpis', response_model=TeamLeaderKpisOut)
def get_team_leader_kpis(
    month: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_leader_access(current_user)
    if not month:
        now = datetime.now(timezone.utc)
        month = now.strftime('%Y-%m')
        
    try:
        year_str, month_str = month.split('-')
        year = int(year_str)
        mon = int(month_str)
        start_date = datetime(year, mon, 1, 0, 0, 0, tzinfo=timezone.utc)
        if mon == 12:
            end_date = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        else:
            end_date = datetime(year, mon + 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    except:
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM.")
        
    team_ids = _get_leader_team_ids(db, current_user)
    if not team_ids:
        return TeamLeaderKpisOut(
            month=month,
            total_sales=0,
            total_revenue=0.0,
            average_qa_score=0.0,
            average_conversion_rate=0.0,
            attendance_rate=0.0
        )
        
    active_assignments = db.query(EmployeeTeamAssignment.employee_id).filter(
        EmployeeTeamAssignment.team_id.in_(team_ids),
        EmployeeTeamAssignment.is_active == True
    ).distinct().all()
    agent_ids = [a[0] for a in active_assignments]
    
    if not agent_ids:
        return TeamLeaderKpisOut(
            month=month,
            total_sales=0,
            total_revenue=0.0,
            average_qa_score=0.0,
            average_conversion_rate=0.0,
            attendance_rate=0.0
        )
        
    call_q = db.query(
        func.count(Call.id).label('total_calls'),
        func.sum(is_success_case).label('sales'),
        func.sum(func.coalesce(CallOutcome.outcome_value, 0.0)).label('revenue'),
        func.avg(func.coalesce(Call.overridden_score, Call.evaluation_score)).label('qa_score')
    ).select_from(Call).join(Campaign, Call.campaign_id == Campaign.id).outerjoin(
        CallOutcome, Call.id == CallOutcome.call_id
    ).filter(
        Call.status == CallStatus.EVALUATED,
        Call.employee_id.in_(agent_ids),
        Call.created_at >= start_date,
        Call.created_at < end_date
    )
    res = call_q.first()
    total_calls = res.total_calls if res and res.total_calls else 0
    sales = res.sales if res and res.sales else 0
    revenue = float(res.revenue) if res and res.revenue else 0.0
    qa_score = float(res.qa_score) if res and res.qa_score else 0.0
    conversion = float(sales * 100.0 / total_calls) if total_calls > 0 else 0.0
    
    return TeamLeaderKpisOut(
        month=month,
        total_sales=sales,
        total_revenue=revenue,
        average_qa_score=qa_score,
        average_conversion_rate=conversion,
        attendance_rate=0.0
    )