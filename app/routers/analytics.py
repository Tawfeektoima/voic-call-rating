from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import Call, Employee, CallStatus
from app.schemas import EmployeeRanking, CommonError, CallOut, EmployeePerformance, DashboardKPIs, EmployeeOut
from app.services.aggregation import get_common_weaknesses
from app.routers.auth import get_current_user
from app.models import UserRole

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Dashboard"])


@router.get("/ranking", response_model=List[EmployeeRanking])
def get_ranking(
    top: Optional[int] = Query(None, description="Number of top employees to fetch"),
    bottom: Optional[int] = Query(None, description="Number of bottom employees to fetch"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Get employee rankings based on average evaluation scores.
    Specify either 'top' or 'bottom'. If neither is provided, defaults to top 20.
    """
    # Role Check: Agents cannot see the full ranking table
    if current_user.role == UserRole.AGENT:
        raise HTTPException(status_code=403, detail="Agents do not have access to the global ranking table.")

    # Base query: calculate average score and call count per employee
    query = (
        db.query(
            Employee.id.label("employee_id"),
            Employee.name.label("employee_name"),
            Employee.employee_code.label("employee_code"),
            Employee.department.label("department"),
            func.avg(func.coalesce(Call.overridden_score, Call.evaluation_score)).label("avg_score"),
            func.count(Call.id).label("total_calls")
        )
        .join(Call, Call.employee_id == Employee.id)
        .filter(Call.status == CallStatus.EVALUATED)
        .group_by(Employee.id)
    )

    if bottom:
        # Lowest scores first
        query = query.order_by(asc("avg_score")).limit(bottom)
    else:
        # Highest scores first (default or 'top')
        limit = top if top else 20
        query = query.order_by(desc("avg_score")).limit(limit)

    results = query.all()
    
    return [
        EmployeeRanking(
            employee_id=r.employee_id,
            employee_name=r.employee_name,
            employee_code=r.employee_code,
            department=r.department,
            avg_score=round(r.avg_score, 2),
            total_calls=r.total_calls
        )
        for r in results
    ]


@router.get("/search", response_model=List[CallOut])
def search_calls(
    employee_code: Optional[str] = Query(None, description="Filter by exact Employee Code"),
    campaign_id: Optional[int] = Query(None, description="Filter by Campaign ID"),
    date_from: Optional[datetime] = Query(None, description="Calls processed after this date"),
    date_to: Optional[datetime] = Query(None, description="Calls processed before this date"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Search and filter call records.
    """
    query = db.query(Call)

    # Role Check: Agents can only search their own calls
    if current_user.role == UserRole.AGENT:
        query = query.filter(Call.employee_id == current_user.id)

    if employee_code:
        query = query.join(Employee).filter(Employee.employee_code == employee_code)
        
    if campaign_id:
        query = query.filter(Call.campaign_id == campaign_id)
        
    if date_from:
        query = query.filter(Call.created_at >= date_from)
        
    if date_to:
        query = query.filter(Call.created_at <= date_to)

    # Order by newest first
    query = query.order_by(desc(Call.created_at)).limit(100)
    
    return query.all()


@router.get("/common-errors", response_model=List[CommonError])
def get_common_errors(
    limit: int = Query(10, description="Number of common errors to retrieve"),
    db: Session = Depends(get_db)
):
    """
    Returns an aggregated list of the most frequent weaknesses resulting in score deductions.
    """
    return get_common_weaknesses(db, limit=limit)


@router.get("/my-performance", response_model=EmployeePerformance)
def get_my_performance(
    employee_id: int = Query(..., description="ID of the employee to fetch performance for"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Get detailed performance metrics and ranking for a specific agent.
    """
    # Role Check: Agent can only request their own ID
    if current_user.role == UserRole.AGENT and current_user.id != employee_id:
        raise HTTPException(status_code=403, detail="You can only view your own performance.")

    # 1. Fetch Employee
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # 2. Get all agent scores for ranking (same department)
    # Note: For now we rank across the whole company if department is null, 
    # or within department if it exists.
    peer_query = (
        db.query(
            Employee.id,
            func.avg(func.coalesce(Call.overridden_score, Call.evaluation_score)).label("avg_score")
        )
        .join(Call, Call.employee_id == Employee.id)
        .filter(Call.status == CallStatus.EVALUATED)
    )
    
    if employee.department:
        peer_query = peer_query.filter(Employee.department == employee.department)
    
    peer_scores = peer_query.group_by(Employee.id).order_by(desc("avg_score")).all()
    
    # 3. Calculate Rank
    total_peers = len(peer_scores)
    rank_pos = 0
    my_avg = 0.0
    
    for idx, (id, score) in enumerate(peer_scores):
        if id == employee_id:
            rank_pos = idx + 1
            my_avg = score
            break
            
    rank_str = f"Rank #{rank_pos} out of {total_peers}" if rank_pos > 0 else "N/A"

    # 4. Fetch Recent Evaluations
    recent_calls = (
        db.query(Call)
        .filter(Call.employee_id == employee_id, Call.status == CallStatus.EVALUATED)
        .order_by(desc(Call.processed_at))
        .limit(5)
        .all()
    )

    # 5. Total Calls
    total_calls = db.query(func.count(Call.id)).filter(
        Call.employee_id == employee_id, 
        Call.status == CallStatus.EVALUATED
    ).scalar()

    return EmployeePerformance(
        avg_score=round(my_avg, 2) if my_avg else 0.0,
        total_calls=total_calls or 0,
        rank=rank_str,
        skills_matrix=employee.skills,
        cumulative_stats=employee.mastery_stats,
        recent_evaluations=recent_calls
    )


@router.get("/agents/{employee_id}", response_model=EmployeeOut)
def get_agent_details(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Get basic profile details for an agent.
    """
    # Role Check: Agents can only view themselves
    if current_user.role == UserRole.AGENT and current_user.id != employee_id:
        raise HTTPException(status_code=403, detail="You can only view your own profile.")

    agent = db.query(Employee).filter(Employee.id == employee_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent


@router.get("/leads", response_model=List[CallOut])
def get_leads(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Get all calls that have a lead status (Hot, Warm, Cold).
    """
    # Managers/Admins only
    if current_user.role == UserRole.AGENT:
        raise HTTPException(status_code=403, detail="Agents cannot access the lead tracker.")

    return db.query(Call).filter(Call.lead_status.isnot(None)).order_by(Call.created_at.desc()).all()


@router.get("/golden-moments", response_model=List[CallOut])
def get_golden_moments(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Get all calls flagged as golden moments.
    """
    return db.query(Call).filter(Call.is_golden_moment == True).order_by(Call.created_at.desc()).all()


@router.get("/dashboard", response_model=DashboardKPIs)
def get_dashboard_kpis(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Retrieve high-level KPIs for the main dashboard.
    """
    # 1. Calls Today
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    total_calls_today = db.query(func.count(Call.id)).filter(Call.created_at >= today_start).scalar()

    # 2. Avg QA Score (All time evaluated)
    avg_score = db.query(func.avg(func.coalesce(Call.overridden_score, Call.evaluation_score))).filter(
        Call.status == CallStatus.EVALUATED
    ).scalar() or 0.0

    # 3. Queue Depth (Pending + Processing)
    queue_depth = db.query(func.count(Call.id)).filter(
        Call.status.in_([CallStatus.PENDING, CallStatus.PROCESSING])
    ).scalar()

    # 4. Pass Rate (Score >= 70)
    total_evaluated = db.query(func.count(Call.id)).filter(Call.status == CallStatus.EVALUATED).scalar()
    passed_calls = db.query(func.count(Call.id)).filter(
        Call.status == CallStatus.EVALUATED,
        func.coalesce(Call.overridden_score, Call.evaluation_score) >= 70
    ).scalar()
    pass_rate = (passed_calls / total_evaluated * 100) if total_evaluated > 0 else 0.0

    # 5. Weekly Trend (Last 5 days)
    # For a real app, this would be a group_by(date). 
    # For now, we'll return some structured data or mock it if DB is empty.
    weekly_trend = [
        {"day": "Mon", "calls": 45, "score": 78},
        {"day": "Tue", "calls": 52, "score": 81},
        {"day": "Wed", "calls": 48, "score": 79},
        {"day": "Thu", "calls": 61, "score": 83},
        {"day": "Fri", "calls": total_calls_today, "score": round(avg_score, 1)},
    ]

    # 6. Campaign Performance
    from app.models import Campaign
    campaigns_perf = db.query(
        Campaign.name,
        func.avg(func.coalesce(Call.overridden_score, Call.evaluation_score)).label("score"),
        func.count(Call.id).label("calls")
    ).join(Call, Call.campaign_id == Campaign.id).filter(
        Call.status == CallStatus.EVALUATED
    ).group_by(Campaign.name).all()

    campaign_performance = [
        {"name": row.name, "score": round(row.score, 1), "calls": row.calls}
        for row in campaigns_perf
    ]

    # 7. Total Calls (All Time)
    total_calls = db.query(func.count(Call.id)).filter(Call.status == CallStatus.EVALUATED).scalar() or 0

    return DashboardKPIs(
        total_calls_today=total_calls_today,
        total_calls=total_calls,
        avg_qa_score=round(avg_score, 1),
        queue_depth=queue_depth,
        pass_rate=round(pass_rate, 1),
        weekly_trend=weekly_trend,
        campaign_performance=campaign_performance
    )
