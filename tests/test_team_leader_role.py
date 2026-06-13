import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import Employee, UserRole
from app.routers.auth import get_current_user
from app.database import SessionLocal
from app.security import get_password_hash

client = TestClient(app)

# Mock admin user
mock_admin = Employee(
    id=9101,
    name="Admin Test",
    email="admin_tl_test@example.com",
    role=UserRole.ADMIN,
    employee_code="ADMIN_TL",
    hashed_password="fake",
    status="active"
)

# Mock team leader user
mock_team_leader = Employee(
    id=9102,
    name="Team Leader Test",
    email="team_leader_test@example.com",
    role=UserRole.TEAM_LEADER,
    employee_code="TL_TST",
    hashed_password="fake",
    status="active"
)


def test_admin_can_create_team_leader():
    """Verify that an ADMIN can create a new employee with the TEAM_LEADER role."""
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    db: Session = SessionLocal()
    try:
        response = client.post("/api/admin/employees", json={
            "name": "Team Leader Alice",
            "email": "tl_alice@example.com",
            "employee_code": "TL_ALICE_001",
            "password": "password123",
            "role": "TEAM_LEADER"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["role"] == "TEAM_LEADER"
        
        # Verify it was written to database
        db_emp = db.query(Employee).filter(Employee.employee_code == "TL_ALICE_001").first()
        assert db_emp is not None
        assert db_emp.role == UserRole.TEAM_LEADER
    finally:
        db.close()
        app.dependency_overrides.clear()


def test_admin_can_update_employee_to_team_leader():
    """Verify that an ADMIN can update an existing employee's role to TEAM_LEADER."""
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    db: Session = SessionLocal()
    try:
        agent = Employee(
            name="Agent To Update TL",
            email="agent_to_update_tl@example.com",
            employee_code="AG_UPD_TL",
            role=UserRole.AGENT,
            hashed_password="fake"
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        response = client.put(f"/api/admin/employees/{agent.id}", json={
            "role": "TEAM_LEADER"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["role"] == "TEAM_LEADER"
        
        db.refresh(agent)
        assert agent.role == UserRole.TEAM_LEADER
    finally:
        db.close()
        app.dependency_overrides.clear()


def test_auth_me_serializes_team_leader():
    """Verify that /api/auth/me returns role 'TEAM_LEADER' for an authenticated Team Leader."""
    app.dependency_overrides[get_current_user] = lambda: mock_team_leader
    try:
        response = client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "TEAM_LEADER"
        assert data["email"] == "team_leader_test@example.com"
    finally:
        app.dependency_overrides.clear()


def test_hr_bulk_preview_rejects_team_leader():
    """Verify HR bulk preview rejects TEAM_LEADER."""
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        csv_content = (
            "name,email,employee_code,role,password\n"
            "Alice Leader,alice_tl@example.com,TL_CSV_01,TEAM_LEADER,password123\n"
        )
        files = {"file": ("agents.csv", csv_content, "text/csv")}
        response = client.post("/api/hr/preview", files=files)
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert "TEAM_LEADER is not allowed in HR bulk onboarding." in data["data"][0]["errors"]
        assert data["data"][0]["isValid"] is False
    finally:
        app.dependency_overrides.clear()


def test_hr_bulk_import_rejects_team_leader():
    """Verify HR bulk import rejects TEAM_LEADER."""
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        # Request body is List[dict]
        payload = [{
            "name": "Alice Leader",
            "email": "alice_tl@example.com",
            "employee_code": "TL_CSV_01",
            "role": "TEAM_LEADER",
            "password": "password123"
        }]
        response = client.post("/api/hr/import", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 0
        assert data["failed_count"] == 1
        assert "TEAM_LEADER is not allowed in HR bulk onboarding." in data["failed"][0]["error"]
    finally:
        app.dependency_overrides.clear()
