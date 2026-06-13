from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole
from app.routers.auth import get_current_user

client = TestClient(app)

def cleanup_test_employees():
    db: Session = SessionLocal()
    try:
        db.query(Employee).filter(Employee.email.like("test_reg_%")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

mock_admin = Employee(
    id=8888,
    name="Mock Admin",
    email="mock_admin_reg@example.com",
    role=UserRole.ADMIN,
    employee_code="MOCK_ADMIN_REG",
    hashed_password="fake"
)

mock_agent = Employee(
    id=8887,
    name="Mock Agent",
    email="mock_agent_reg@example.com",
    role=UserRole.AGENT,
    employee_code="MOCK_AGENT_REG",
    hashed_password="fake"
)

def test_unauthenticated_registration_rejected():
    """Verify that unauthenticated POST requests to /api/auth/register are rejected with 401."""
    app.dependency_overrides.clear()
    cleanup_test_employees()
    try:
        response = client.post(
            "/api/auth/register",
            json={
                "name": "Register Test User",
                "email": "test_reg_unauth@example.com",
                "password": "Password123!",
                "role": "AGENT"
            }
        )
        assert response.status_code == 401
    finally:
        cleanup_test_employees()

def test_non_admin_register_admin_rejected():
    """Verify that authenticated non-admins cannot register a user with role=ADMIN."""
    app.dependency_overrides[get_current_user] = lambda: mock_agent
    cleanup_test_employees()
    try:
        response = client.post(
            "/api/auth/register",
            json={
                "name": "Exploit User",
                "email": "test_reg_exploit@example.com",
                "password": "Password123!",
                "role": "ADMIN"
            }
        )
        assert response.status_code == 403
        assert "Only admins can register new users" in response.json()["detail"]
    finally:
        cleanup_test_employees()
        app.dependency_overrides.clear()

def test_non_admin_register_other_role_rejected():
    """Verify that authenticated non-admins cannot assign other roles like QA or HR_MANAGER."""
    app.dependency_overrides[get_current_user] = lambda: mock_agent
    cleanup_test_employees()
    try:
        response = client.post(
            "/api/auth/register",
            json={
                "name": "QA User",
                "email": "test_reg_qa@example.com",
                "password": "Password123!",
                "role": "QA"
            }
        )
        assert response.status_code == 403
        assert "Only admins can register new users" in response.json()["detail"]
    finally:
        cleanup_test_employees()
        app.dependency_overrides.clear()

def test_admin_register_valid_role_permitted():
    """Verify that authenticated admins can register a user with a valid role (e.g. QA or ADMIN)."""
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    cleanup_test_employees()
    try:
        response = client.post(
            "/api/auth/register",
            json={
                "name": "QA New User",
                "email": "test_reg_valid_qa@example.com",
                "password": "Password123!",
                "role": "QA"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "QA"
        assert data["email"] == "test_reg_valid_qa@example.com"
        
        # Test registering an admin
        response_admin = client.post(
            "/api/auth/register",
            json={
                "name": "Admin New User",
                "email": "test_reg_valid_admin@example.com",
                "password": "Password123!",
                "role": "ADMIN"
            }
        )
        assert response_admin.status_code == 200
        data_admin = response_admin.json()
        assert data_admin["role"] == "ADMIN"
    finally:
        cleanup_test_employees()
        app.dependency_overrides.clear()

def test_non_admin_registration_rejected():
    """Verify that authenticated non-admins cannot register new users."""
    app.dependency_overrides[get_current_user] = lambda: mock_agent
    cleanup_test_employees()
    try:
        response = client.post(
            "/api/auth/register",
            json={
                "name": "Agent User 1",
                "email": "test_reg_agent1@example.com",
                "password": "Password123!",
                "role": "AGENT"
            }
        )
        assert response.status_code == 403
        assert "Only admins can register new users" in response.json()["detail"]
    finally:
        cleanup_test_employees()
        app.dependency_overrides.clear()


def test_admin_register_weak_password_rejected():
    """Verify weak passwords are rejected during registration."""
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    cleanup_test_employees()
    try:
        response = client.post(
            "/api/auth/register",
            json={
                "name": "Weak Password User",
                "email": "test_reg_weak@example.com",
                "password": "password123",
                "role": "AGENT"
            }
        )
        assert response.status_code == 422
        assert "uppercase" in str(response.json()).lower()
    finally:
        cleanup_test_employees()
        app.dependency_overrides.clear()

