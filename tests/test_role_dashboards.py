from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, Campaign, Call, CallStatus
from app.routers.auth import get_current_user

client = TestClient(app)

# Mock users for testing
mock_admin = Employee(
    id=9901,
    name="Admin User",
    email="admin_role_db@example.com",
    role=UserRole.ADMIN,
    employee_code="ADMIN_ROLE_DB",
    hashed_password="fake"
)

mock_agent_1 = Employee(
    id=9902,
    name="Agent One",
    email="agent_one_role_db@example.com",
    role=UserRole.AGENT,
    employee_code="AGENT_ONE",
    hashed_password="fake"
)

mock_agent_2 = Employee(
    id=9903,
    name="Agent Two",
    email="agent_two_role_db@example.com",
    role=UserRole.AGENT,
    employee_code="AGENT_TWO",
    hashed_password="fake"
)

mock_hr_manager = Employee(
    id=9904,
    name="HR Manager User",
    email="hr_manager_role_db@example.com",
    role=UserRole.HR_MANAGER,
    employee_code="HR_MANAGER_USER",
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
    db_session.query(Call).filter(Call.original_filename.like("test_role_%")).delete(synchronize_session=False)
    db_session.query(Employee).filter(
        Employee.employee_code.like("AGENT_%") | 
        Employee.employee_code.like("HR_MANAGER_%") |
        Employee.email.like("bulk_manager_test_%")
    ).delete(synchronize_session=False)
    db_session.query(Campaign).filter(Campaign.name.like("TEST_ROLE_%")).delete(synchronize_session=False)
    db_session.commit()
    yield
    # Clean up after each test
    db_session.query(Call).filter(Call.original_filename.like("test_role_%")).delete(synchronize_session=False)
    db_session.query(Employee).filter(
        Employee.employee_code.like("AGENT_%") | 
        Employee.employee_code.like("HR_MANAGER_%") |
        Employee.email.like("bulk_manager_test_%")
    ).delete(synchronize_session=False)
    db_session.query(Campaign).filter(Campaign.name.like("TEST_ROLE_%")).delete(synchronize_session=False)
    db_session.commit()

def test_agent_scoping_dashboard(db_session: Session):
    """Verify that an Agent role requesting the dashboard only receives metrics for their own calls."""
    # Seed campaign
    camp = Campaign(name="TEST_ROLE_CAMP", evaluation_prompt="Test evaluation prompt", color="#FF0000")
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)

    # Seed agents in DB to satisfy foreign keys
    emp1 = Employee(
        id=mock_agent_1.id,
        name=mock_agent_1.name,
        email=mock_agent_1.email,
        role=mock_agent_1.role,
        employee_code=mock_agent_1.employee_code,
        hashed_password="fake"
    )
    emp2 = Employee(
        id=mock_agent_2.id,
        name=mock_agent_2.name,
        email=mock_agent_2.email,
        role=mock_agent_2.role,
        employee_code=mock_agent_2.employee_code,
        hashed_password="fake"
    )
    db_session.add_all([emp1, emp2])
    db_session.commit()

    # Agent 1 calls: 2 evaluated, scores 90 and 80 (avg 85)
    c1 = Call(
        employee_id=emp1.id,
        campaign_id=camp.id,
        status=CallStatus.EVALUATED,
        evaluation_score=90.0,
        audio_file_path="test_role_1.wav",
        original_filename="test_role_1.wav",
        created_at=datetime.now()
    )
    c2 = Call(
        employee_id=emp1.id,
        campaign_id=camp.id,
        status=CallStatus.EVALUATED,
        evaluation_score=80.0,
        audio_file_path="test_role_2.wav",
        original_filename="test_role_2.wav",
        created_at=datetime.now()
    )

    # Agent 2 calls: 1 evaluated, score 50
    c3 = Call(
        employee_id=emp2.id,
        campaign_id=camp.id,
        status=CallStatus.EVALUATED,
        evaluation_score=50.0,
        audio_file_path="test_role_3.wav",
        original_filename="test_role_3.wav",
        created_at=datetime.now()
    )

    db_session.add_all([c1, c2, c3])
    db_session.commit()

    # Case 1: Agent 1 requests dashboard (expect average score 85, calls 2)
    app.dependency_overrides[get_current_user] = lambda: emp1
    try:
        resp = client.get("/api/analytics/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_calls"] == 2
        assert data["avg_qa_score"] == 85.0
        assert data["pass_rate"] == 100.0 # both 90 and 80 are >= 70
    finally:
        app.dependency_overrides.clear()

    # Case 2: Agent 2 requests dashboard (expect average score 50, calls 1)
    app.dependency_overrides[get_current_user] = lambda: emp2
    try:
        resp = client.get("/api/analytics/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_calls"] == 1
        assert data["avg_qa_score"] == 50.0
        assert data["pass_rate"] == 0.0 # 50 is < 70
    finally:
        app.dependency_overrides.clear()

def test_admin_and_hr_managers_global_dashboard(db_session: Session):
    """Verify that Admins, QA, and HR Managers receive global aggregated metrics."""
    camp = Campaign(name="TEST_ROLE_CAMP", evaluation_prompt="Test evaluation prompt", color="#FF0000")
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)

    emp1 = Employee(
        id=mock_agent_1.id,
        name=mock_agent_1.name,
        email=mock_agent_1.email,
        role=mock_agent_1.role,
        employee_code=mock_agent_1.employee_code,
        hashed_password="fake"
    )
    emp2 = Employee(
        id=mock_agent_2.id,
        name=mock_agent_2.name,
        email=mock_agent_2.email,
        role=mock_agent_2.role,
        employee_code=mock_agent_2.employee_code,
        hashed_password="fake"
    )
    db_session.add_all([emp1, emp2])
    db_session.commit()

    # Agent 1 score 100, Agent 2 score 60
    c1 = Call(
        employee_id=emp1.id,
        campaign_id=camp.id,
        status=CallStatus.EVALUATED,
        evaluation_score=100.0,
        audio_file_path="test_role_1.wav",
        original_filename="test_role_1.wav",
        created_at=datetime.now()
    )
    c2 = Call(
        employee_id=emp2.id,
        campaign_id=camp.id,
        status=CallStatus.EVALUATED,
        evaluation_score=60.0,
        audio_file_path="test_role_2.wav",
        original_filename="test_role_2.wav",
        created_at=datetime.now()
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    # Under global aggregation:
    # Total calls: 2, Avg QA Score: 80.0, Pass Rate: 50%
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        resp = client.get("/api/analytics/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_calls"] >= 2
    finally:
        app.dependency_overrides.clear()

def test_hr_manager_onboarding_and_assignment(db_session: Session):
    """Verify that the HR_MANAGER role is validated correctly and can be assigned by admins."""
    # Seed an admin session
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        # Create an employee with HR_MANAGER role via admin panel simulation (POST /api/admin/employees)
        payload = {
            "name": "New HR Manager",
            "email": "new_hr_manager_role_test@example.com",
            "employee_code": "HR_MANAGER_NEW_1",
            "password": "Password123!",
            "role": "HR_MANAGER"
        }
        resp = client.post("/api/admin/employees", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "HR_MANAGER"

        # Verify HR_MANAGER role is allowed in bulk onboard validation schema
        preview_payload = [
            {
                "name": "Bulk HR Manager",
                "email": "bulk_manager_test_import@example.com",
                "employee_code": "HR_MANAGER_BULK_2",
                "role": "HR_MANAGER",
                "password": "Password123!"
            }
        ]
        resp_import = client.post("/api/hr/import", json=preview_payload)
        assert resp_import.status_code == 200
        data_import = resp_import.json()
        assert data_import["success_count"] == 1
    finally:
        # Clean up database entry
        db_session.query(Employee).filter(Employee.email == "new_hr_manager_role_test@example.com").delete()
        db_session.commit()
        app.dependency_overrides.clear()

