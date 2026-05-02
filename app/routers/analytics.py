from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import Call, Employee, CallStatus
from app.schemas import EmployeeRanking, CommonError, CallOut
from app.services.aggregation import get_common_weaknesses

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Dashboard"])


@router.get("/ranking", response_model=List[EmployeeRanking])
def get_ranking(
    top: Optional[int] = Query(None, description="Number of top employees to fetch"),
    bottom: Optional[int] = Query(None, description="Number of bottom employees to fetch"),
    db: Session = Depends(get_db)
):
    """
    Get employee rankings based on average evaluation scores.
    Specify either 'top' or 'bottom'. If neither is provided, defaults to top 20.
    """
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
    db: Session = Depends(get_db)
):
    """
    Search and filter call records.
    """
    query = db.query(Call)

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
