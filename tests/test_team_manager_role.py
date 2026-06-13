from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import pytest

from app.main import app
from app.models import Employee, UserRole
from app.routers.auth import get_current_user
from app.database import SessionLocal
from app.security import get_password_hash

client = TestClient(app)

# Mock admin user
mock_admin = Employee(
    id=9001,
    name="Admin Test",
    email="admin_test@example.com",
    role=UserRole.ADMIN,
    employee_code="ADMIN_TST",
    hashed_password="fake",
    status="active"
)

# Mock team manager user
mock_team_manager = Employee(
    id=9002,
    name="Team Manager Test",
    email="team_manager_test@example.com",
    role=UserRole.TEAM_MANAGER,
    employee_code="TM_TST",
    hashed_password="fake",
    status="active"
)



def test_admin_can_create_team_manager():
    """Verify that an ADMIN can create a new employee with the TEAM_MANAGER role."""
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    db: Session = SessionLocal()
    try:
        # Verify the role TEAM_MANAGER works in Employee creation
        response = client.post("/api/admin/employees", json={
            "name": "Team Manager Bob",
            "email": "tm_bob@example.com",
            "employee_code": "TM_BOB_001",
            "password": "password123",
            "role": "TEAM_MANAGER"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["role"] == "TEAM_MANAGER"
        
        # Verify it was written to database as TEAM_MANAGER
        db_emp = db.query(Employee).filter(Employee.employee_code == "TM_BOB_001").first()
        assert db_emp is not None
        assert db_emp.role == UserRole.TEAM_MANAGER
    finally:
        db.close()
        app.dependency_overrides.clear()


def test_admin_can_update_employee_to_team_manager():
    """Verify that an ADMIN can update an existing employee's role to TEAM_MANAGER."""
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    db: Session = SessionLocal()
    try:
        # Create an agent first
        agent = Employee(
            name="Agent To Update",
            email="agent_to_update@example.com",
            employee_code="AG_UPD_001",
            role=UserRole.AGENT,
            hashed_password="fake"
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        # Update the role to TEAM_MANAGER
        response = client.put(f"/api/admin/employees/{agent.id}", json={
            "role": "TEAM_MANAGER"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["role"] == "TEAM_MANAGER"
        
        # Verify it is updated in the database
        db.refresh(agent)
        assert agent.role == UserRole.TEAM_MANAGER
    finally:
        db.close()
        app.dependency_overrides.clear()


def test_auth_me_serializes_team_manager():
    """Verify that /api/auth/me returns role 'TEAM_MANAGER' for an authenticated Team Manager."""
    app.dependency_overrides[get_current_user] = lambda: mock_team_manager
    try:
        response = client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "TEAM_MANAGER"
        assert data["email"] == "team_manager_test@example.com"
    finally:
        app.dependency_overrides.clear()


def test_login_serializes_team_manager():
    """Verify that login returns role 'TEAM_MANAGER' for a Team Manager user."""
    db: Session = SessionLocal()
    try:
        password = "tmmanagerpass123"
        hashed_pwd = get_password_hash(password)
        user = Employee(
            name="Login Team Manager",
            email="tm_login_test@example.com",
            hashed_password=hashed_pwd,
            role=UserRole.TEAM_MANAGER,
            employee_code="TM_LOGIN_TST",
            status="active"
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    # Attempt Login
    response = client.post(
        "/api/auth/login",
        json={"email": "tm_login_test@example.com", "password": "tmmanagerpass123"}
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "TEAM_MANAGER"
