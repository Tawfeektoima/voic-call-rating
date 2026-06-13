from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import Employee, Team, UserRole, AgentTransferRequest
from app.routers.auth import get_current_user
from app.permissions import require_team_manager_access
from app.services.team_manager_reporting import (
    get_team_manager_dashboard,
    get_team_manager_teams,
    get_team_manager_team_detail,
    get_team_manager_agents,
    get_team_manager_agent_detail,
    get_team_manager_sales_report,
    get_team_manager_revenue_report,
    get_team_manager_conversion_report,
    get_team_manager_attendance_report,
    get_team_manager_kpis
)
from app.schemas import (
    TeamManagerDashboardOut,
    TeamManagerTeamRowOut,
    TeamManagerAgentRowOut,
    TeamManagerAgentDetailOut,
    TeamManagerSalesReportOut,
    TeamManagerRevenueReportOut,
    TeamManagerConversionReportOut,
    TeamManagerAttendanceReportOut,
    TeamManagerKpisOut,
    AgentTransferRequestCreate,
    AgentTransferRequestOut
)

router = APIRouter(prefix="/api/team-manager", tags=["Team Manager"])

@router.get('/dashboard', response_model=TeamManagerDashboardOut)
def get_dashboard(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_manager_access(current_user)
    return get_team_manager_dashboard(db, current_user, start_date, end_date)

@router.get('/teams', response_model=List[TeamManagerTeamRowOut])
def get_teams(
    skip: int = Query(0, ge=0, description='Offset for pagination'),
    limit: int = Query(50, ge=1, le=100, description='Limit for pagination'),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_manager_access(current_user)
    return get_team_manager_teams(db, current_user, skip=skip, limit=limit)

@router.get('/teams/{team_id}', response_model=TeamManagerTeamRowOut)
def get_team_detail(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_manager_access(current_user)
    return get_team_manager_team_detail(db, current_user, team_id)

@router.get('/agents', response_model=List[TeamManagerAgentRowOut])
def get_agents(
    team_id: Optional[int] = Query(None, description='Optional filter by Team ID'),
    skip: int = Query(0, ge=0, description='Offset for pagination'),
    limit: int = Query(50, ge=1, le=100, description='Limit for pagination'),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_manager_access(current_user)
    return get_team_manager_agents(db, current_user, team_id=team_id, skip=skip, limit=limit)

@router.get('/agents/{agent_id}', response_model=TeamManagerAgentDetailOut)
def get_agent_detail(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_manager_access(current_user)
    return get_team_manager_agent_detail(db, current_user, agent_id)

@router.get('/reports/sales', response_model=TeamManagerSalesReportOut)
def get_sales_report(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_manager_access(current_user)
    return get_team_manager_sales_report(db, current_user, start_date, end_date)

@router.get('/reports/revenue', response_model=TeamManagerRevenueReportOut)
def get_revenue_report(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_manager_access(current_user)
    return get_team_manager_revenue_report(db, current_user, start_date, end_date)

@router.get('/reports/conversion', response_model=TeamManagerConversionReportOut)
def get_conversion_report(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_manager_access(current_user)
    return get_team_manager_conversion_report(db, current_user, start_date, end_date)

@router.get('/reports/attendance', response_model=TeamManagerAttendanceReportOut)
def get_attendance_report(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_manager_access(current_user)
    return get_team_manager_attendance_report(db, current_user, start_date, end_date)

@router.get('/kpis', response_model=TeamManagerKpisOut)
def get_kpis(
    month: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_manager_access(current_user)
    return get_team_manager_kpis(db, current_user, month)

@router.post('/transfer-requests', response_model=AgentTransferRequestOut)
def create_transfer_request(
    req: AgentTransferRequestCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_manager_access(current_user)
    if req.to_team_id == req.from_team_id:
        raise HTTPException(status_code=400, detail='Cannot transfer to the same team.')
        
    if current_user.role == UserRole.TEAM_MANAGER:
        from app.services.team_scope import is_agent_in_manager_scope, is_team_in_manager_scope
        if not is_agent_in_manager_scope(db, current_user.id, req.agent_id):
            raise HTTPException(status_code=403, detail='Agent is not in your managed scope.')
        if not is_team_in_manager_scope(db, current_user.id, req.from_team_id):
            raise HTTPException(status_code=403, detail='From team is not in your managed scope.')
            
    from app.services.team_scope import is_agent_assigned_to_team
    if not is_agent_assigned_to_team(db, req.agent_id, req.from_team_id):
        raise HTTPException(status_code=400, detail='Agent is not actively assigned to the from_team.')
        
    target_team = db.query(Team).filter(Team.id == req.to_team_id, Team.is_active == True).first()
    if not target_team:
        raise HTTPException(status_code=400, detail='Target team does not exist or is inactive.')
        
    existing_pending = db.query(AgentTransferRequest).filter(
        AgentTransferRequest.agent_id == req.agent_id,
        AgentTransferRequest.status == 'PENDING'
    ).first()
    if existing_pending:
        raise HTTPException(status_code=400, detail='A pending transfer request already exists for this agent.')
        
    new_req = AgentTransferRequest(
        agent_id=req.agent_id,
        from_team_id=req.from_team_id,
        to_team_id=req.to_team_id,
        requested_by_id=current_user.id,
        status='PENDING',
        reason=req.reason
    )
    db.add(new_req)
    db.commit()
    db.refresh(new_req)
    
    from app.services.audit import log_audit_event
    log_audit_event(
        db=db,
        action='TRANSFER_REQUEST_CREATE',
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f'TransferRequest #{new_req.id}',
        before_state=None,
        after_state=f'Agent #{req.agent_id} from {req.from_team_id} to {req.to_team_id}',
        reason='Transfer request created'
    )
    return new_req

@router.get('/transfer-requests', response_model=List[AgentTransferRequestOut])
def list_transfer_requests(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_manager_access(current_user)
    if current_user.role == UserRole.ADMIN:
        return db.query(AgentTransferRequest).order_by(AgentTransferRequest.id.desc()).all()
        
    from app.services.team_scope import get_managed_team_ids
    managed_team_ids = get_managed_team_ids(db, current_user.id)
    return db.query(AgentTransferRequest).filter(
        (AgentTransferRequest.requested_by_id == current_user.id) |
        AgentTransferRequest.from_team_id.in_(managed_team_ids)
    ).order_by(AgentTransferRequest.id.desc()).all()

@router.get('/transfer-requests/{request_id}', response_model=AgentTransferRequestOut)
def get_transfer_request_detail(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_manager_access(current_user)
    req = db.query(AgentTransferRequest).filter(AgentTransferRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail='Transfer request not found.')
        
    if current_user.role != UserRole.ADMIN:
        from app.services.team_scope import get_managed_team_ids
        managed_team_ids = get_managed_team_ids(db, current_user.id)
        is_creator = req.requested_by_id == current_user.id
        is_from_team_managed = req.from_team_id in managed_team_ids
        if not is_creator and not is_from_team_managed:
            raise HTTPException(status_code=403, detail='Access denied.')
    return req

@router.patch('/transfer-requests/{request_id}/cancel', response_model=AgentTransferRequestOut)
def cancel_transfer_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_team_manager_access(current_user)
    req = db.query(AgentTransferRequest).filter(AgentTransferRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail='Transfer request not found.')
        
    if current_user.role == UserRole.TEAM_MANAGER and req.requested_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot cancel another manager's request.")
        
    if req.status != 'PENDING':
        raise HTTPException(status_code=400, detail='Only pending requests can be canceled.')
        
    req.status = 'CANCELED'
    db.commit()
    db.refresh(req)
    
    from app.services.audit import log_audit_event
    log_audit_event(
        db=db,
        action='TRANSFER_REQUEST_CANCEL',
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f'TransferRequest #{req.id}',
        before_state='PENDING',
        after_state='CANCELED',
        reason='Transfer request canceled'
    )
    return req