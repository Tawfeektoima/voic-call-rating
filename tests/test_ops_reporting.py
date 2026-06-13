import pytest
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta, timezone
from fastapi import HTTPException

from app.models import Employee, Campaign, Call, CallStatus, CallOutcome, AgentViolation, AttendanceRecord, OperationalTarget, SystemLog, CampaignType, UserRole
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
from app.database import SessionLocal

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_parse_ops_filters():
    filters = parse_ops_filters(limit=10, offset=5)
    assert filters.limit == 10
    assert filters.offset == 5
    
    # Check limit boundaries
    filters_large = parse_ops_filters(limit=999)
    assert filters_large.limit == 500
    
    filters_small = parse_ops_filters(limit=-10)
    assert filters_small.limit == 1

def test_ops_reporting_metrics(db_session: Session):
    # Seed data
    # 1. Create campaigns
    sales_camp = Campaign(
        name="Sales Campaign",
        type=CampaignType.SALES,
        evaluation_prompt="Test evaluation prompt (length >= 10)",
        color="#123456"
    )
    support_camp = Campaign(
        name="Support Campaign",
        type=CampaignType.CUSTOMER_SERVICE,
        evaluation_prompt="Test evaluation prompt (length >= 10)",
        color="#abcdef"
    )
    db_session.add_all([sales_camp, support_camp])
    db_session.commit()
    db_session.refresh(sales_camp)
    db_session.refresh(support_camp)

    # 2. Create employees
    emp_agent = Employee(
        name="Agent User",
        email="agent.test@example.com",
        role=UserRole.AGENT,
        employee_code="AGENT_001",
        hashed_password="fake",
        status="active",
        department="Operations"
    )
    db_session.add(emp_agent)
    db_session.commit()
    db_session.refresh(emp_agent)

    # 3. Create Calls and Outcomes
    # Call 1: Sales, Sale Closed, outcome_value=100.0
    c1 = Call(
        employee_id=emp_agent.id,
        campaign_id=sales_camp.id,
        status=CallStatus.EVALUATED,
        evaluation_score=85.0,
        audio_file_path="fake",
        original_filename="fake"
    )
    db_session.add(c1)
    db_session.commit()
    db_session.refresh(c1)
    out1 = CallOutcome(
        call_id=c1.id,
        campaign_type="sales",
        primary_outcome="Sale Closed",
        outcome_value=100.0
    )
    db_session.add(out1)

    # Call 2: Sales, Sale Lost, outcome_value=0.0
    c2 = Call(
        employee_id=emp_agent.id,
        campaign_id=sales_camp.id,
        status=CallStatus.EVALUATED,
        evaluation_score=90.0,
        audio_file_path="fake",
        original_filename="fake"
    )
    db_session.add(c2)
    db_session.commit()
    db_session.refresh(c2)
    out2 = CallOutcome(
        call_id=c2.id,
        campaign_type="sales",
        primary_outcome="Sale Lost",
        outcome_value=0.0
    )
    db_session.add(out2)

    # Call 3: Support, Resolved, outcome_value=0.0
    c3 = Call(
        employee_id=emp_agent.id,
        campaign_id=support_camp.id,
        status=CallStatus.EVALUATED,
        evaluation_score=95.0,
        audio_file_path="fake",
        original_filename="fake"
    )
    db_session.add(c3)
    db_session.commit()
    db_session.refresh(c3)
    out3 = CallOutcome(
        call_id=c3.id,
        campaign_type="customer_service",
        primary_outcome="Resolved",
        outcome_value=0.0
    )
    db_session.add(out3)
    db_session.commit()

    # 4. Create Attendance records
    att1 = AttendanceRecord(
        employee_id=emp_agent.id,
        attendance_date=date.today(),
        status="present"
    )
    db_session.add(att1)

    # 5. Create Agent Violations
    v1 = AgentViolation(
        employee_id=emp_agent.id,
        campaign_id=sales_camp.id,
        call_id=c1.id,
        violation_id="script_compliance",
        severity="medium",
        occurrence=1,
        penalty_tier="Warning",
        score_deduction=10.0
    )
    db_session.add(v1)

    # 6. Create Operational Targets
    t1 = OperationalTarget(
        campaign_id=sales_camp.id,
        metric_name="sales",
        target_value=5.0,
        effective_from=datetime.now(timezone.utc) - timedelta(days=10)
    )
    db_session.add(t1)
    db_session.commit()

    # Run service function checks
    filters = parse_ops_filters()
    
    # Campaigns report
    c_rows = get_ops_campaigns(db_session, filters)
    assert len(c_rows) == 2
    
    sales_row = next(r for r in c_rows if r.campaign_id == sales_camp.id)
    assert sales_row.total_calls == 2
    assert sales_row.sales == 1
    assert sales_row.revenue == 100.0
    assert sales_row.conversion_rate == 50.0
    assert sales_row.avg_qa_score == 87.5
    assert sales_row.attends == 1
    assert sales_row.violations_count == 1

    support_row = next(r for r in c_rows if r.campaign_id == support_camp.id)
    assert support_row.total_calls == 1
    assert support_row.sales == 1  # "Resolved" is success for customer_service
    assert support_row.revenue == 0.0
    assert support_row.conversion_rate == 100.0
    assert support_row.avg_qa_score == 95.0

    # Campaign detail check
    detail = get_ops_campaign_detail(db_session, sales_camp.id, filters)
    assert detail.campaign_id == sales_camp.id
    assert detail.sales == 1
    
    # 404 check
    with pytest.raises(HTTPException) as exc:
        get_ops_campaign_detail(db_session, 9999, filters)
    assert exc.value.status_code == 404

    # Attendance report check
    att_rows = get_ops_attendance_report(db_session, filters)
    assert len(att_rows) == 1
    assert att_rows[0].employee_name == "Agent User"
    assert att_rows[0].status == "present"

    # QA Overview check
    qa_overview = get_ops_qa_overview(db_session, filters)
    assert qa_overview.reviewed_calls == 3
    assert qa_overview.avg_score == 90.0 # (85+90+95)/3
    assert len(qa_overview.top_violations) == 1
    assert qa_overview.top_violations[0].violation_id == "script_compliance"
    assert qa_overview.top_violations[0].count == 1
    assert qa_overview.top_violations[0].total_deductions == 10.0

    # Violations overview check
    viol_overview = get_ops_violations_overview(db_session, filters)
    assert viol_overview.total_violations == 1
    assert viol_overview.medium_count == 1
    assert viol_overview.total_deductions == 10.0

    # Dashboard check
    dashboard = get_ops_dashboard(db_session, filters)
    assert len(dashboard.campaigns) == 2
    assert len(dashboard.totals) == 6
    
    sales_total = next(t for t in dashboard.totals if t.metric == "sales")
    assert sales_total.value == 2.0  # 1 from sales, 1 from support
    
    revenue_total = next(t for t in dashboard.totals if t.metric == "revenue")
    assert revenue_total.value == 100.0

def test_operational_target_active_window(db_session: Session):
    """Verify that _get_target_with_fallback only considers active targets and respects window rules."""
    from app.services.ops_reporting import _get_target_with_fallback
    from datetime import timedelta
    
    now = datetime.now(timezone.utc)
    
    # 1. Seed targets:
    # Target A: Expired (effective_from = now - 10d, effective_to = now - 2d)
    expired_target = OperationalTarget(
        metric_name="sales",
        target_value=10.0,
        effective_from=now - timedelta(days=10),
        effective_to=now - timedelta(days=2)
    )
    # Target B: Future (effective_from = now + 2d, effective_to = now + 10d)
    future_target = OperationalTarget(
        metric_name="sales",
        target_value=12.0,
        effective_from=now + timedelta(days=2),
        effective_to=now + timedelta(days=10)
    )
    # Target C: Active Older (effective_from = now - 5d, effective_to = now + 5d)
    active_older_target = OperationalTarget(
        metric_name="sales",
        target_value=15.0,
        effective_from=now - timedelta(days=5),
        effective_to=now + timedelta(days=5)
    )
    # Target D: Active Newer (effective_from = now - 1d, effective_to = now + 1d) - should be preferred!
    active_newer_target = OperationalTarget(
        metric_name="sales",
        target_value=20.0,
        effective_from=now - timedelta(days=1),
        effective_to=now + timedelta(days=1)
    )
    
    db_session.add_all([expired_target, future_target, active_older_target, active_newer_target])
    db_session.commit()
    
    # Run target lookup helper (company-wide, no segment)
    target = _get_target_with_fallback(db_session, "sales", campaign_id=None, segment=None)
    
    # Assert active_newer_target is selected because it is active and has the latest effective_from
    assert target is not None
    assert target.id == active_newer_target.id
    assert target.target_value == 20.0

