from sqlalchemy import func, case, distinct, or_
from sqlalchemy.orm import Session
from datetime import datetime, timezone, date
from typing import List, Optional
from fastapi import HTTPException

from app.models import Call, Campaign, CallStatus, CallOutcome, Employee, AgentViolation, AttendanceRecord, OperationalTarget, SystemLog, CampaignType
from app.schemas import (
    OpsFilters,
    OpsMetricSummary,
    OpsCampaignRow,
    OpsAttendanceRow,
    OpsTopViolationRow,
    OpsQAOverviewOut,
    OpsViolationsOverviewOut,
    OpsAlertRow,
    OpsDashboardOut
)

# SQL Case statement defining whether an evaluated call counts as a successful outcome (a "sale")
is_success_case = case(
    (
        (Campaign.type == CampaignType.SALES) & (CallOutcome.primary_outcome == "Sale Closed"),
        1
    ),
    (
        (Campaign.type == CampaignType.CUSTOMER_SERVICE) & (CallOutcome.primary_outcome == "Resolved"),
        1
    ),
    (
        (Campaign.type == CampaignType.COLLECTIONS) & (CallOutcome.primary_outcome.in_(["Promise to Pay", "Payment Arranged"])),
        1
    ),
    (
        (Campaign.type == CampaignType.TECHNICAL) & (CallOutcome.primary_outcome.in_(["Resolved", "Workaround Provided"])),
        1
    ),
    else_=0
)

def parse_ops_filters(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    campaign_id: Optional[int] = None,
    department: Optional[str] = None,
    segment: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> OpsFilters:
    """Normalize and return a validated OpsFilters object."""
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    return OpsFilters(
        date_from=date_from,
        date_to=date_to,
        campaign_id=campaign_id,
        department=department,
        segment=segment,
        limit=limit,
        offset=offset
    )

def _get_target_with_fallback(
    db: Session,
    metric_name: str,
    campaign_id: Optional[int] = None,
    segment: Optional[str] = None
) -> Optional[OperationalTarget]:
    """Helper to retrieve an active OperationalTarget with hierarchical fallbacks:
    1. Exact Match (campaign + segment)
    2. Campaign Match (campaign, no segment)
    3. Segment Match (company-wide, segment)
    4. Global Match (company-wide, no segment)
    """
    now = datetime.now(timezone.utc)
    base_q = db.query(OperationalTarget).filter(
        OperationalTarget.metric_name == metric_name,
        OperationalTarget.effective_from <= now,
        (OperationalTarget.effective_to.is_(None) | (OperationalTarget.effective_to >= now))
    ).order_by(OperationalTarget.effective_from.desc())
    
    # 1. Exact Match (campaign + segment)
    if campaign_id is not None and segment is not None:
        target = base_q.filter(
            OperationalTarget.campaign_id == campaign_id,
            OperationalTarget.segment == segment
        ).first()
        if target:
            return target
            
    # 2. Campaign Match (campaign, no segment) - fallback if segment is not found/specified
    if campaign_id is not None:
        target = base_q.filter(
            OperationalTarget.campaign_id == campaign_id,
            OperationalTarget.segment.is_(None)
        ).first()
        if target:
            return target
            
    # 3. Segment Match (company-wide, segment) - fallback if campaign is not found/specified
    if segment is not None:
        target = base_q.filter(
            OperationalTarget.campaign_id.is_(None),
            OperationalTarget.segment == segment
        ).first()
        if target:
            return target
            
    # 4. Global Match (company-wide, no segment)
    target = base_q.filter(
        OperationalTarget.campaign_id.is_(None),
        OperationalTarget.segment.is_(None)
    ).first()
    return target

def _compute_status(metric: str, value: float, target: Optional[OperationalTarget]) -> str:
    """Determine operational threshold status: good, warning, or critical."""
    if not target:
        return "good"
        
    critical = target.critical_threshold
    warning = target.warning_threshold
    
    if metric == "violations":
        # For violations, higher is worse
        if critical is not None and value >= critical:
            return "critical"
        if warning is not None and value >= warning:
            return "warning"
        return "good"
    else:
        # For other metrics (sales, revenue, conversion, attendance, QA score), lower is worse
        if critical is not None and value <= critical:
            return "critical"
        if warning is not None and value <= warning:
            return "warning"
        return "good"

def _get_totals(db: Session, filters: OpsFilters, is_prev: bool) -> dict:
    """Helper to query database-wide totals for the 6 core dashboard metrics."""
    date_from = filters.date_from
    date_to = filters.date_to
    if is_prev and date_from and date_to:
        delta = date_to - date_from
        date_from = date_from - delta
        date_to = date_to - delta
        
    call_q = db.query(
        func.count(Call.id).label('total_calls'),
        func.sum(is_success_case).label('sales'),
        func.sum(func.coalesce(CallOutcome.outcome_value, 0.0)).label('revenue'),
        func.avg(func.coalesce(Call.overridden_score, Call.evaluation_score)).label('qa_score')
    ).select_from(Call).join(Campaign, Call.campaign_id == Campaign.id).outerjoin(
        CallOutcome, Call.id == CallOutcome.call_id
    ).filter(Call.status == CallStatus.EVALUATED)
    
    if filters.campaign_id is not None:
        call_q = call_q.filter(Call.campaign_id == filters.campaign_id)
    if date_from:
        call_q = call_q.filter(Call.created_at >= date_from)
    if date_to:
        call_q = call_q.filter(Call.created_at <= date_to)
    if filters.department:
        call_q = call_q.join(Employee, Call.employee_id == Employee.id).filter(
            Employee.department == filters.department
        )
        
    call_res = call_q.first()
    total_calls = call_res.total_calls if call_res and call_res.total_calls else 0
    sales = call_res.sales if call_res and call_res.sales else 0
    revenue = float(call_res.revenue) if call_res and call_res.revenue else 0.0
    qa_score = float(call_res.qa_score) if call_res and call_res.qa_score else 0.0
    
    conversion = float(sales * 100.0 / total_calls) if total_calls > 0 else 0.0
    
    attendance_total_q = db.query(func.count(AttendanceRecord.id))
    attendance_present_q = db.query(func.count(AttendanceRecord.id)).filter(
        func.lower(AttendanceRecord.status).in_(['present', 'attended', 'late'])
    )
    
    if date_from:
        attendance_total_q = attendance_total_q.filter(AttendanceRecord.attendance_date >= date_from.date())
        attendance_present_q = attendance_present_q.filter(AttendanceRecord.attendance_date >= date_from.date())
    if date_to:
        attendance_total_q = attendance_total_q.filter(AttendanceRecord.attendance_date <= date_to.date())
        attendance_present_q = attendance_present_q.filter(AttendanceRecord.attendance_date <= date_to.date())
    if filters.department:
        attendance_total_q = attendance_total_q.join(Employee, AttendanceRecord.employee_id == Employee.id).filter(
            Employee.department == filters.department
        )
        attendance_present_q = attendance_present_q.join(Employee, AttendanceRecord.employee_id == Employee.id).filter(
            Employee.department == filters.department
        )
        
    if filters.campaign_id is not None:
        emp_ids_subquery = db.query(Call.employee_id).filter(Call.campaign_id == filters.campaign_id).distinct().subquery()
        attendance_total_q = attendance_total_q.filter(AttendanceRecord.employee_id.in_(emp_ids_subquery))
        attendance_present_q = attendance_present_q.filter(AttendanceRecord.employee_id.in_(emp_ids_subquery))
        
    att_total = attendance_total_q.scalar() or 0
    att_present = attendance_present_q.scalar() or 0
    attendance_rate = float(att_present * 100.0 / att_total) if att_total > 0 else 0.0
    
    violation_q = db.query(func.count(AgentViolation.id))
    if filters.campaign_id is not None:
        violation_q = violation_q.filter(AgentViolation.campaign_id == filters.campaign_id)
    if date_from:
        violation_q = violation_q.filter(AgentViolation.created_at >= date_from)
    if date_to:
        violation_q = violation_q.filter(AgentViolation.created_at <= date_to)
    if filters.department:
        violation_q = violation_q.join(Employee, AgentViolation.employee_id == Employee.id).filter(
            Employee.department == filters.department
        )
        
    violations = violation_q.scalar() or 0
    
    return {
        'sales': float(sales),
        'revenue': float(revenue),
        'conversion': float(conversion),
        'attendance': float(attendance_rate),
        'qa_score': float(qa_score),
        'violations': float(violations)
    }

def _build_campaign_rows(
    db: Session,
    filters: OpsFilters,
    campaign_id: Optional[int] = None
) -> List[OpsCampaignRow]:
    """Helper to aggregate operational metrics at the campaign level."""
    camp_q = db.query(Campaign)
    if campaign_id is not None:
        camp_q = camp_q.filter(Campaign.id == campaign_id)
    elif filters.campaign_id is not None:
        camp_q = camp_q.filter(Campaign.id == filters.campaign_id)
        
    campaigns = camp_q.all()
    
    call_q = db.query(
        Call.campaign_id.label('campaign_id'),
        func.count(Call.id).label('total_calls'),
        func.sum(is_success_case).label('sales'),
        func.sum(func.coalesce(CallOutcome.outcome_value, 0.0)).label('revenue'),
        func.avg(func.coalesce(Call.overridden_score, Call.evaluation_score)).label('avg_qa_score')
    ).select_from(Call).join(Campaign, Call.campaign_id == Campaign.id).outerjoin(
        CallOutcome, Call.id == CallOutcome.call_id
    ).filter(Call.status == CallStatus.EVALUATED)
    
    if filters.date_from:
        call_q = call_q.filter(Call.created_at >= filters.date_from)
    if filters.date_to:
        call_q = call_q.filter(Call.created_at <= filters.date_to)
    if filters.department:
        call_q = call_q.join(Employee, Call.employee_id == Employee.id).filter(
            Employee.department == filters.department
        )
        
    call_stats = {r.campaign_id: r for r in call_q.group_by(Call.campaign_id).all()}
    
    viol_q = db.query(
        AgentViolation.campaign_id.label('campaign_id'),
        func.count(AgentViolation.id).label('count')
    )
    if filters.date_from:
        viol_q = viol_q.filter(AgentViolation.created_at >= filters.date_from)
    if filters.date_to:
        viol_q = viol_q.filter(AgentViolation.created_at <= filters.date_to)
    if filters.department:
        viol_q = viol_q.join(Employee, AgentViolation.employee_id == Employee.id).filter(
            Employee.department == filters.department
        )
        
    viol_stats = {r.campaign_id: r.count for r in viol_q.group_by(AgentViolation.campaign_id).all()}
    
    att_q = db.query(
        Call.campaign_id.label('campaign_id'),
        func.count(distinct(AttendanceRecord.id)).label('attends')
    ).select_from(Call).join(
        AttendanceRecord, Call.employee_id == AttendanceRecord.employee_id
    ).filter(
        func.lower(AttendanceRecord.status).in_(['present', 'attended', 'late'])
    )
    if filters.date_from:
        att_q = att_q.filter(AttendanceRecord.attendance_date >= filters.date_from.date())
    if filters.date_to:
        att_q = att_q.filter(AttendanceRecord.attendance_date <= filters.date_to.date())
    if filters.department:
        att_q = att_q.join(Employee, Call.employee_id == Employee.id).filter(
            Employee.department == filters.department
        )
        
    att_stats = {r.campaign_id: r.attends for r in att_q.group_by(Call.campaign_id).all()}
    
    rows = []
    for camp in campaigns:
        stats = call_stats.get(camp.id)
        total_calls = stats.total_calls if stats and stats.total_calls else 0
        sales = stats.sales if stats and stats.sales else 0
        revenue = float(stats.revenue) if stats and stats.revenue else 0.0
        avg_qa_score = float(stats.avg_qa_score) if stats and stats.avg_qa_score else 0.0
        
        conversion_rate = float(sales * 100.0 / total_calls) if total_calls > 0 else 0.0
        violations_count = viol_stats.get(camp.id, 0)
        attends = att_stats.get(camp.id, 0)
        
        rows.append(
            OpsCampaignRow(
                campaign_id=camp.id,
                campaign_name=camp.name,
                total_calls=total_calls,
                attends=attends,
                sales=sales,
                revenue=revenue,
                conversion_rate=conversion_rate,
                avg_qa_score=avg_qa_score,
                violations_count=violations_count
            )
        )
    return rows

def get_ops_dashboard(db: Session, filters: OpsFilters) -> OpsDashboardOut:
    """Build the top-level operational dashboard response payload."""
    current_totals = _get_totals(db, filters, is_prev=False)
    prev_totals = _get_totals(db, filters, is_prev=True)
    totals_summaries = []
    metrics = ['sales', 'revenue', 'conversion', 'attendance', 'qa_score', 'violations']
    for m in metrics:
        val = current_totals[m]
        prev_val = prev_totals[m]
        target = _get_target_with_fallback(db, m, filters.campaign_id, filters.segment)
        target_val = target.target_value if target else None
        delta = val - target_val if target_val is not None else None
        
        if val > prev_val:
            trend = 'up'
        elif val < prev_val:
            trend = 'down'
        else:
            trend = 'flat'
            
        status = _compute_status(m, val, target)
        totals_summaries.append(
            OpsMetricSummary(
                metric=m,
                value=val,
                target_value=target_val,
                delta=delta,
                trend=trend,
                status=status
            )
        )
        
    campaigns = _build_campaign_rows(db, filters)
    campaigns = campaigns[filters.offset : filters.offset + filters.limit]
    
    alerts = get_ops_alerts(db, filters)
    alerts = alerts[:10]
    
    segments_query = db.query(OperationalTarget.segment).distinct().filter(
        OperationalTarget.segment.isnot(None)
    ).order_by(OperationalTarget.segment.asc()).all()
    segments = [r[0] for r in segments_query]
    
    return OpsDashboardOut(
        date_from=filters.date_from,
        date_to=filters.date_to,
        totals=totals_summaries,
        campaigns=campaigns,
        alerts=alerts,
        segments=segments,
        updated_at=datetime.now(timezone.utc)
    )

def get_ops_sales_report(db: Session, filters: OpsFilters) -> List[OpsCampaignRow]:
    """Get campaign-level sales metrics rows."""
    return get_ops_campaigns(db, filters)

def get_ops_revenue_report(db: Session, filters: OpsFilters) -> List[OpsCampaignRow]:
    """Get campaign-level revenue metrics rows."""
    return get_ops_campaigns(db, filters)

def get_ops_conversion_report(db: Session, filters: OpsFilters) -> List[OpsCampaignRow]:
    """Get campaign-level conversion metrics rows."""
    return get_ops_campaigns(db, filters)

def get_ops_attendance_report(db: Session, filters: OpsFilters) -> List[OpsAttendanceRow]:
    """Get a detailed report of agents' daily attendance tracking records."""
    query = db.query(
        AttendanceRecord.employee_id.label('employee_id'),
        Employee.name.label('employee_name'),
        Employee.employee_code.label('employee_code'),
        AttendanceRecord.attendance_date.label('attendance_date'),
        AttendanceRecord.status.label('status'),
        AttendanceRecord.scheduled_minutes.label('scheduled_minutes'),
        AttendanceRecord.worked_minutes.label('worked_minutes'),
        AttendanceRecord.late_minutes.label('late_minutes')
    ).join(Employee, AttendanceRecord.employee_id == Employee.id)
    
    if filters.date_from:
        query = query.filter(AttendanceRecord.attendance_date >= filters.date_from.date())
    if filters.date_to:
        query = query.filter(AttendanceRecord.attendance_date <= filters.date_to.date())
    if filters.department:
        query = query.filter(Employee.department == filters.department)
        
    if filters.campaign_id is not None:
        emp_ids_subquery = db.query(Call.employee_id).filter(Call.campaign_id == filters.campaign_id).distinct().subquery()
        query = query.filter(AttendanceRecord.employee_id.in_(emp_ids_subquery))
        
    results = query.order_by(AttendanceRecord.attendance_date.desc(), Employee.name.asc()).offset(filters.offset).limit(filters.limit).all()
    
    return [
        OpsAttendanceRow(
            employee_id=r.employee_id,
            employee_name=r.employee_name,
            employee_code=r.employee_code,
            attendance_date=r.attendance_date,
            status=r.status,
            scheduled_minutes=r.scheduled_minutes,
            worked_minutes=r.worked_minutes,
            late_minutes=r.late_minutes
        )
        for r in results
    ]

def get_ops_qa_overview(db: Session, filters: OpsFilters) -> OpsQAOverviewOut:
    """Build the operational QA overview metrics summary report."""
    call_q = db.query(Call)
    if filters.campaign_id is not None:
        call_q = call_q.filter(Call.campaign_id == filters.campaign_id)
    if filters.date_from:
        call_q = call_q.filter(Call.created_at >= filters.date_from)
    if filters.date_to:
        call_q = call_q.filter(Call.created_at <= filters.date_to)
    if filters.department:
        call_q = call_q.join(Employee, Call.employee_id == Employee.id).filter(Employee.department == filters.department)
        
    reviewed_calls = call_q.filter(Call.status == CallStatus.EVALUATED).count()
    pending_reviews = call_q.filter(Call.status.in_([CallStatus.PENDING, CallStatus.PROCESSING])).count()
    qa_alarm_count = call_q.filter(Call.qa_alarm == True).count()
    
    avg_score_val = db.query(func.avg(func.coalesce(Call.overridden_score, Call.evaluation_score))).filter(
        Call.status == CallStatus.EVALUATED
    )
    if filters.campaign_id is not None:
        avg_score_val = avg_score_val.filter(Call.campaign_id == filters.campaign_id)
    if filters.date_from:
        avg_score_val = avg_score_val.filter(Call.created_at >= filters.date_from)
    if filters.date_to:
        avg_score_val = avg_score_val.filter(Call.created_at <= filters.date_to)
    if filters.department:
        avg_score_val = avg_score_val.join(Employee, Call.employee_id == Employee.id).filter(Employee.department == filters.department)
        
    avg_score = avg_score_val.scalar() or 0.0
    
    violation_q = db.query(
        AgentViolation.violation_id.label('violation_id'),
        func.count(AgentViolation.id).label('count'),
        func.sum(AgentViolation.score_deduction).label('total_deductions')
    )
    if filters.campaign_id is not None:
        violation_q = violation_q.filter(AgentViolation.campaign_id == filters.campaign_id)
    if filters.date_from:
        violation_q = violation_q.filter(AgentViolation.created_at >= filters.date_from)
    if filters.date_to:
        violation_q = violation_q.filter(AgentViolation.created_at <= filters.date_to)
    if filters.department:
        violation_q = violation_q.join(Employee, AgentViolation.employee_id == Employee.id).filter(
            Employee.department == filters.department
        )
        
    violation_results = violation_q.group_by(AgentViolation.violation_id).order_by(
        func.count(AgentViolation.id).desc()
    ).limit(5).all()
    
    top_violations = [
        OpsTopViolationRow(
            violation_id=r.violation_id,
            count=r.count,
            total_deductions=float(r.total_deductions or 0.0)
        )
        for r in violation_results
    ]
    
    return OpsQAOverviewOut(
        avg_score=float(avg_score),
        reviewed_calls=reviewed_calls,
        pending_reviews=pending_reviews,
        qa_alarm_count=qa_alarm_count,
        top_violations=top_violations
    )

def get_ops_violations_overview(db: Session, filters: OpsFilters) -> OpsViolationsOverviewOut:
    """Build the operational Agent Violation metrics overview report."""
    violation_q = db.query(
        func.count(AgentViolation.id).label('total_violations'),
        func.sum(case((AgentViolation.severity == 'high', 1), else_=0)).label('high_count'),
        func.sum(case((AgentViolation.severity == 'medium', 1), else_=0)).label('medium_count'),
        func.sum(case((AgentViolation.severity == 'low', 1), else_=0)).label('low_count'),
        func.sum(case((AgentViolation.hr_flagged == True, 1), else_=0)).label('hr_flagged_count'),
        func.sum(AgentViolation.score_deduction).label('total_deductions')
    )
    if filters.campaign_id is not None:
        violation_q = violation_q.filter(AgentViolation.campaign_id == filters.campaign_id)
    if filters.date_from:
        violation_q = violation_q.filter(AgentViolation.created_at >= filters.date_from)
    if filters.date_to:
        violation_q = violation_q.filter(AgentViolation.created_at <= filters.date_to)
    if filters.department:
        violation_q = violation_q.join(Employee, AgentViolation.employee_id == Employee.id).filter(
            Employee.department == filters.department
        )
        
    row = violation_q.first()
    
    total_violations = row.total_violations if row and row.total_violations else 0
    high_count = row.high_count if row and row.high_count else 0
    medium_count = row.medium_count if row and row.medium_count else 0
    low_count = row.low_count if row and row.low_count else 0
    hr_flagged_count = row.hr_flagged_count if row and row.hr_flagged_count else 0
    total_deductions = float(row.total_deductions) if row and row.total_deductions else 0.0
    
    return OpsViolationsOverviewOut(
        total_violations=total_violations,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        hr_flagged_count=hr_flagged_count,
        total_deductions=total_deductions
    )

def get_ops_campaigns(db: Session, filters: OpsFilters) -> List[OpsCampaignRow]:
    """Get paginated and filtered campaign performance rows."""
    campaign_rows = _build_campaign_rows(db, filters)
    return campaign_rows[filters.offset : filters.offset + filters.limit]

def get_ops_campaign_detail(db: Session, campaign_id: int, filters: OpsFilters) -> OpsCampaignRow:
    """Get detailed operational metrics for a single campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    campaign_rows = _build_campaign_rows(db, filters, campaign_id=campaign_id)
    if not campaign_rows:
        return OpsCampaignRow(
            campaign_id=campaign.id,
            campaign_name=campaign.name,
            total_calls=0,
            attends=0,
            sales=0,
            revenue=0.0,
            conversion_rate=0.0,
            avg_qa_score=0.0,
            violations_count=0
        )
    return campaign_rows[0]

def get_ops_alerts(db: Session, filters: OpsFilters) -> List[OpsAlertRow]:
    """Get system log alerts relevant for operational monitoring."""
    query = db.query(SystemLog).order_by(SystemLog.created_at.desc())
    if filters.date_from:
        query = query.filter(SystemLog.created_at >= filters.date_from)
    if filters.date_to:
        query = query.filter(SystemLog.created_at <= filters.date_to)
        
    results = query.offset(filters.offset).limit(filters.limit).all()
    
    return [
        OpsAlertRow(
            id=r.id,
            error_type=r.error_type,
            error_message=r.error_message,
            severity=r.severity or "medium",
            resolved=r.resolved or False,
            created_at=r.created_at
        )
        for r in results
    ]