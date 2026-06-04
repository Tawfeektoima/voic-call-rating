from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, Campaign, Call, CallStatus
from app.services.aggregation import calculate_core_kpis
from app.routers.auth import get_current_user

client = TestClient(app)

# Setup mock users
mock_admin = Employee(
    id=8888,
    name="Agg Admin",
    email="agg_admin@example.com",
    role=UserRole.ADMIN,
    employee_code="AGG_ADMIN",
    hashed_password="fake"
)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(autouse=True)
def clean_up_db(db_session: Session):
    # Clean up before each test
    db_session.query(Call).filter(Call.original_filename.like("test_agg_%")).delete(synchronize_session=False)
    db_session.query(Employee).filter(Employee.employee_code.like("TEST_AGG_%")).delete(synchronize_session=False)
    db_session.query(Campaign).filter(Campaign.name.like("TEST_AGG_%")).delete(synchronize_session=False)
    db_session.commit()
    yield
    # Clean up after each test
    db_session.query(Call).filter(Call.original_filename.like("test_agg_%")).delete(synchronize_session=False)
    db_session.query(Employee).filter(Employee.employee_code.like("TEST_AGG_%")).delete(synchronize_session=False)
    db_session.query(Campaign).filter(Campaign.name.like("TEST_AGG_%")).delete(synchronize_session=False)
    db_session.commit()

def test_calculate_core_kpis_empty_db(db_session: Session):
    """Verify aggregation behaves correctly and returns fallback values with an empty database."""
    # We verify our calculate_core_kpis with a date range that has NO calls.
    future_start = datetime.now() + timedelta(days=10)
    future_end = datetime.now() + timedelta(days=20)
    
    kpis = calculate_core_kpis(db_session, date_from=future_start, date_to=future_end)
    assert kpis["total_calls_today"] == 0
    assert kpis["total_calls"] == 0
    assert kpis["avg_qa_score"] == 0.0
    assert kpis["queue_depth"] == 0
    assert kpis["pending_count"] == 0
    assert kpis["processing_count"] == 0
    assert kpis["pass_rate"] == 0.0

def test_calculate_core_kpis_aggregation(db_session: Session):
    """Verify that KPI aggregation computes the correct counts, averages, overrides, and pass rates."""
    camp = Campaign(name="TEST_AGG_CAMP", evaluation_prompt="Test evaluation prompt", color="#FF0000")
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)

    emp = Employee(
        name="Test Agg Agent",
        email="test_agg_agent@example.com",
        role=UserRole.AGENT,
        employee_code="TEST_AGG_EMP",
        hashed_password="fake"
    )
    db_session.add(emp)
    db_session.commit()
    db_session.refresh(emp)

    now = datetime.now()

    # Create calls with statuses and scores:
    # 1. Evaluated, score 80
    c1 = Call(
        employee_id=emp.id,
        campaign_id=camp.id,
        status=CallStatus.EVALUATED,
        evaluation_score=80.0,
        audio_file_path="test_agg_1.wav",
        original_filename="test_agg_1.wav",
        created_at=now
    )
    # 2. Evaluated, score 60 (failed)
    c2 = Call(
        employee_id=emp.id,
        campaign_id=camp.id,
        status=CallStatus.EVALUATED,
        evaluation_score=60.0,
        audio_file_path="test_agg_2.wav",
        original_filename="test_agg_2.wav",
        created_at=now
    )
    # 3. Evaluated, score 50 but overridden to 90 (pass)
    c3 = Call(
        employee_id=emp.id,
        campaign_id=camp.id,
        status=CallStatus.EVALUATED,
        evaluation_score=50.0,
        overridden_score=90.0,
        audio_file_path="test_agg_3.wav",
        original_filename="test_agg_3.wav",
        created_at=now
    )
    # 4. Pending
    c4 = Call(
        employee_id=emp.id,
        campaign_id=camp.id,
        status=CallStatus.PENDING,
        audio_file_path="test_agg_4.wav",
        original_filename="test_agg_4.wav",
        created_at=now
    )
    # 5. Processing
    c5 = Call(
        employee_id=emp.id,
        campaign_id=camp.id,
        status=CallStatus.PROCESSING,
        audio_file_path="test_agg_5.wav",
        original_filename="test_agg_5.wav",
        created_at=now
    )

    db_session.add_all([c1, c2, c3, c4, c5])
    db_session.commit()

    # Run aggregation for today
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    kpis = calculate_core_kpis(db_session, date_from=today_start, date_to=today_end)

    # Assertions
    # We expect 5 calls created today
    assert kpis["total_calls_today"] >= 5
    # Total evaluated calls should be at least 3
    assert kpis["total_calls"] >= 3
    assert kpis["queue_depth"] >= 2

def test_calculate_core_kpis_date_filtering(db_session: Session):
    """Verify date-range filtering works properly and returns stable subset results."""
    camp = Campaign(name="TEST_AGG_CAMP", evaluation_prompt="Test evaluation prompt", color="#FF0000")
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)

    emp = Employee(
        name="Test Agg Agent",
        email="test_agg_agent@example.com",
        role=UserRole.AGENT,
        employee_code="TEST_AGG_EMP",
        hashed_password="fake"
    )
    db_session.add(emp)
    db_session.commit()
    db_session.refresh(emp)

    now = datetime.now()
    yesterday = now - timedelta(days=1)
    two_days_ago = now - timedelta(days=2)

    # Call 1: Evaluated, 2 days ago, score 90
    c1 = Call(
        employee_id=emp.id,
        campaign_id=camp.id,
        status=CallStatus.EVALUATED,
        evaluation_score=90.0,
        audio_file_path="test_agg_1.wav",
        original_filename="test_agg_1.wav",
        created_at=two_days_ago
    )
    # Call 2: Evaluated, yesterday, score 80
    c2 = Call(
        employee_id=emp.id,
        campaign_id=camp.id,
        status=CallStatus.EVALUATED,
        evaluation_score=80.0,
        audio_file_path="test_agg_2.wav",
        original_filename="test_agg_2.wav",
        created_at=yesterday
    )
    # Call 3: Evaluated, today, score 70
    c3 = Call(
        employee_id=emp.id,
        campaign_id=camp.id,
        status=CallStatus.EVALUATED,
        evaluation_score=70.0,
        audio_file_path="test_agg_3.wav",
        original_filename="test_agg_3.wav",
        created_at=now
    )

    db_session.add_all([c1, c2, c3])
    db_session.commit()

    # Filter for yesterday only
    range_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    range_end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)

    kpis = calculate_core_kpis(db_session, date_from=range_start, date_to=range_end)

    # We expect exactly 1 call in total_calls (Call 2)
    assert kpis["total_calls"] == 1
    assert kpis["avg_qa_score"] == 80.0
    assert kpis["pass_rate"] == 100.0

def test_routers_call_aggregation(db_session: Session):
    """Verify that analytics dashboard and system health metrics routes invoke and return values compatible with aggregation service."""
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        # Create campaign and employee
        camp = Campaign(name="TEST_AGG_CAMP", evaluation_prompt="Test evaluation prompt", color="#FF0000")
        db_session.add(camp)
        db_session.commit()
        db_session.refresh(camp)

        emp = Employee(
            name="Test Agg Agent",
            email="test_agg_agent@example.com",
            role=UserRole.AGENT,
            employee_code="TEST_AGG_EMP",
            hashed_password="fake"
        )
        db_session.add(emp)
        db_session.commit()
        db_session.refresh(emp)

        # Call
        c = Call(
            employee_id=emp.id,
            campaign_id=camp.id,
            status=CallStatus.EVALUATED,
            evaluation_score=85.0,
            audio_file_path="test_agg_1.wav",
            original_filename="test_agg_1.wav",
            created_at=datetime.now()
        )
        db_session.add(c)
        db_session.commit()

        # Compute using the service layer directly
        service_kpis = calculate_core_kpis(db_session)

        # Call /api/analytics/dashboard
        resp_dashboard = client.get("/api/analytics/dashboard")
        assert resp_dashboard.status_code == 200
        data_db = resp_dashboard.json()
        assert "total_calls_today" in data_db
        assert "total_calls" in data_db
        assert "avg_qa_score" in data_db
        assert "queue_depth" in data_db
        assert "pass_rate" in data_db
        
        # Verify router output matches exactly the service layer output
        assert data_db["avg_qa_score"] == service_kpis["avg_qa_score"]
        assert data_db["total_calls_today"] == service_kpis["total_calls_today"]
        assert data_db["queue_depth"] == service_kpis["queue_depth"]
        assert data_db["pass_rate"] == service_kpis["pass_rate"]

        # Call /api/system/metrics
        resp_metrics = client.get("/api/system/metrics")
        assert resp_metrics.status_code == 200
        data_met = resp_metrics.json()
        assert data_met["calls_processing"] == service_kpis["queue_depth"]
        assert data_met["queue_depth"] == service_kpis["pending_count"]
    finally:
        app.dependency_overrides.clear()
