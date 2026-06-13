from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from app.database import get_db
from app.models import Employee
from app.routers.auth import get_current_user
from app.permissions import require_ops_reporting_access
from app.schemas import (
    OpsFilters,
    OpsDashboardOut,
    OpsCampaignRow,
    OpsAttendanceRow,
    OpsQAOverviewOut,
    OpsViolationsOverviewOut,
    OpsAlertRow
)
from app.services.ops_reporting import (
    parse_ops_filters,
    get_ops_dashboard,
    get_ops_sales_report,
    get_ops_revenue_report,
    get_ops_conversion_report,
    get_ops_attendance_report,
    get_ops_qa_overview,
    get_ops_violations_overview,
    get_ops_campaigns,
    get_ops_campaign_detail,
    get_ops_alerts
)

router = APIRouter(prefix="/api/ops", tags=["Operations"])

def get_ops_filters(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    campaign_id: Optional[int] = None,
    department: Optional[str] = Query(None),
    segment: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
) -> OpsFilters:
    return parse_ops_filters(
        date_from=date_from,
        date_to=date_to,
        campaign_id=campaign_id,
        department=department,
        segment=segment,
        limit=limit,
        offset=offset
    )

@router.get("/dashboard", response_model=OpsDashboardOut)
def read_ops_dashboard(
    filters: OpsFilters = Depends(get_ops_filters),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_ops_reporting_access(current_user)
    return get_ops_dashboard(db, filters)

@router.get("/reports/sales", response_model=List[OpsCampaignRow])
def read_ops_sales_report(
    filters: OpsFilters = Depends(get_ops_filters),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_ops_reporting_access(current_user)
    return get_ops_sales_report(db, filters)

@router.get("/reports/revenue", response_model=List[OpsCampaignRow])
def read_ops_revenue_report(
    filters: OpsFilters = Depends(get_ops_filters),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_ops_reporting_access(current_user)
    return get_ops_revenue_report(db, filters)

@router.get("/reports/conversion", response_model=List[OpsCampaignRow])
def read_ops_conversion_report(
    filters: OpsFilters = Depends(get_ops_filters),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_ops_reporting_access(current_user)
    return get_ops_conversion_report(db, filters)

@router.get("/reports/attendance", response_model=List[OpsAttendanceRow])
def read_ops_attendance_report(
    filters: OpsFilters = Depends(get_ops_filters),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_ops_reporting_access(current_user)
    return get_ops_attendance_report(db, filters)

@router.get("/campaigns", response_model=List[OpsCampaignRow])
def read_ops_campaigns(
    filters: OpsFilters = Depends(get_ops_filters),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_ops_reporting_access(current_user)
    return get_ops_campaigns(db, filters)

@router.get("/campaigns/{campaign_id}", response_model=OpsCampaignRow)
def read_ops_campaign_detail(
    campaign_id: int,
    filters: OpsFilters = Depends(get_ops_filters),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_ops_reporting_access(current_user)
    return get_ops_campaign_detail(db, campaign_id, filters)

@router.get("/qa-overview", response_model=OpsQAOverviewOut)
def read_ops_qa_overview(
    filters: OpsFilters = Depends(get_ops_filters),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_ops_reporting_access(current_user)
    return get_ops_qa_overview(db, filters)

@router.get("/violations-overview", response_model=OpsViolationsOverviewOut)
def read_ops_violations_overview(
    filters: OpsFilters = Depends(get_ops_filters),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_ops_reporting_access(current_user)
    return get_ops_violations_overview(db, filters)

@router.get("/alerts", response_model=List[OpsAlertRow])
def read_ops_alerts(
    filters: OpsFilters = Depends(get_ops_filters),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_ops_reporting_access(current_user)
    return get_ops_alerts(db, filters)
