import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole
from app.security import get_password_hash
from app.limiter import login_ip_limiter, login_email_limiter
from app.services.employee_identity import hash_national_id

client = TestClient(app)

def cleanup_test_employees():
    db: Session = SessionLocal()
    try:
        db.query(Employee).filter(Employee.email.like("test_status_%")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

@pytest.fixture(autouse=True)
def setup_teardown():
    login_ip_limiter.reset()
    login_email_limiter.reset()
    cleanup_test_employees()
    yield
    cleanup_test_employees()
    login_ip_limiter.reset()
    login_email_limiter.reset()

def test_active_user_login_and_access_succeeds():
    """Verify that an active user can log in and call a protected endpoint."""
    db: Session = SessionLocal()
    try:
        password = "TestPassword123!!"
        hashed_pwd = get_password_hash(password)
        user = Employee(
            name="Test Active User",
            email="test_status_active@example.com",
            hashed_password=hashed_pwd,
            role=UserRole.AGENT,
            employee_code="TEST_STATUS_ACTIVE",
            status="active"
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    # Attempt Login
    response = client.post(
        "/api/auth/login",
        json={"email": "test_status_active@example.com", "password": "TestPassword123!!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["status"] == "active"
    assert data["user"]["account_status"] == "active"

    # Access /me with token
    token = data["access_token"]
    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["status"] == "active"
    assert me_response.json()["account_status"] == "active"


def test_employee_code_login_requires_otp_when_real_email_exists():
    """Verify employee_code login sends an OTP challenge before issuing a token."""
    db: Session = SessionLocal()
    try:
        password = "TestPassword123!!"
        hashed_pwd = get_password_hash(password)
        user = Employee(
            name="Test OTP User",
            email="test_status_otp@example.com",
            otp_email="real.gmail.user@gmail.com",
            hashed_password=hashed_pwd,
            role=UserRole.AGENT,
            employee_code="TEST_STATUS_OTP",
            status="active"
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/auth/login",
        json={"employee_code": "TEST_STATUS_OTP", "password": "TestPassword123!!"}
    )
    assert response.status_code == 200
    challenge_data = response.json()
    assert challenge_data["otp_required"] is True
    assert challenge_data["destination"].endswith("@gmail.com")
    assert "access_token" not in challenge_data
    assert "dev_otp_code" in challenge_data

    verify_response = client.post(
        "/api/auth/login/verify-otp",
        json={
            "challenge_id": challenge_data["challenge_id"],
            "otp_code": challenge_data["dev_otp_code"]
        }
    )
    assert verify_response.status_code == 200
    data = verify_response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "test_status_otp@example.com"


def test_password_reset_with_company_email_and_national_id():
    """Verify password reset requires matching company email and national ID before changing password."""
    db: Session = SessionLocal()
    try:
        user = Employee(
            name="Test Reset User",
            email="test_status_reset@example.com",
            otp_email="reset.gmail.user@gmail.com",
            national_id_hash=hash_national_id("30001011234567"),
            hashed_password=get_password_hash("oldPassword123!"),
            role=UserRole.AGENT,
            employee_code="TEST_STATUS_RESET",
            status="active"
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    request_response = client.post(
        "/api/auth/password-reset/request",
        json={
            "email": "test_status_reset@example.com",
            "national_id": "30001011234567"
        }
    )
    assert request_response.status_code == 200
    reset_data = request_response.json()
    assert reset_data["challenge_id"] is not None
    assert reset_data["destination"].endswith("@gmail.com")
    assert "dev_otp_code" in reset_data

    confirm_response = client.post(
        "/api/auth/password-reset/confirm",
        json={
            "challenge_id": reset_data["challenge_id"],
            "otp_code": reset_data["dev_otp_code"],
            "new_password": "newPassword123!"
        }
    )
    assert confirm_response.status_code == 200

    login_response = client.post(
        "/api/auth/login",
        json={"employee_code": "TEST_STATUS_RESET", "password": "newPassword123!"}
    )
    assert login_response.status_code == 200
    assert login_response.json()["otp_required"] is True

def test_disabled_user_login_fails():
    """Verify that a disabled user cannot log in and gets 403 Forbidden."""
    db: Session = SessionLocal()
    try:
        password = "TestPassword123!!"
        hashed_pwd = get_password_hash(password)
        user = Employee(
            name="Test Disabled User",
            email="test_status_disabled@example.com",
            hashed_password=hashed_pwd,
            role=UserRole.AGENT,
            employee_code="TEST_STATUS_DISABLED",
            status="disabled"
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    # Attempt Login
    response = client.post(
        "/api/auth/login",
        json={"email": "test_status_disabled@example.com", "password": "TestPassword123!!"}
    )
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()

def test_suspended_user_login_fails():
    """Verify that a suspended user cannot log in and gets 403 Forbidden."""
    db: Session = SessionLocal()
    try:
        password = "TestPassword123!!"
        hashed_pwd = get_password_hash(password)
        user = Employee(
            name="Test Suspended User",
            email="test_status_suspended@example.com",
            hashed_password=hashed_pwd,
            role=UserRole.AGENT,
            employee_code="TEST_STATUS_SUSPENDED",
            status="suspended"
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    # Attempt Login
    response = client.post(
        "/api/auth/login",
        json={"email": "test_status_suspended@example.com", "password": "TestPassword123!!"}
    )
    assert response.status_code == 403
    assert "suspended" in response.json()["detail"].lower()

def test_active_token_rejection_if_user_becomes_inactive():
    """Verify that an existing token is immediately rejected if status changes to disabled or suspended."""
    db: Session = SessionLocal()
    try:
        password = "TestPassword123!!"
        hashed_pwd = get_password_hash(password)
        user = Employee(
            name="Test Status Transition User",
            email="test_status_transition@example.com",
            hashed_password=hashed_pwd,
            role=UserRole.AGENT,
            employee_code="TEST_STATUS_TRANSITION",
            status="active"
        )
        db.add(user)
        db.commit()
        user_id = user.id
    finally:
        db.close()

    # Get valid token
    response = client.post(
        "/api/auth/login",
        json={"email": "test_status_transition@example.com", "password": "TestPassword123!!"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    # Verify we can access /me
    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200

    # Modify user status to disabled in database
    db = SessionLocal()
    try:
        db_user = db.query(Employee).filter(Employee.id == user_id).first()
        db_user.status = "disabled"
        db.commit()
    finally:
        db.close()

    # Verify token is now rejected with 403
    me_response2 = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response2.status_code == 403
    assert "disabled" in me_response2.json()["detail"].lower()

    # Modify user status to suspended in database
    db = SessionLocal()
    try:
        db_user = db.query(Employee).filter(Employee.id == user_id).first()
        db_user.status = "suspended"
        db.commit()
    finally:
        db.close()

    # Verify token is now rejected with 403
    me_response3 = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response3.status_code == 403
    assert "suspended" in me_response3.json()["detail"].lower()

