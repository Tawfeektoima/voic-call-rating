import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from jose import jwt

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, UserSession, TrustedDevice, LoginOtpChallenge, AuditEvent, EmployeeStatus
from app.security import get_password_hash, SECRET_KEY, ALGORITHM
from app.services.security_policy import hash_device_id, get_policy_mode
from app.config import get_settings

client = TestClient(app)

def cleanup_test_db():
    db: Session = SessionLocal()
    try:
        # Query employee IDs that match our test prefix
        emp_ids = [e.id for e in db.query(Employee).filter(Employee.email.like("test_sess_%")).all()]
        if emp_ids:
            # Delete corresponding records
            db.query(UserSession).filter(UserSession.employee_id.in_(emp_ids)).delete(synchronize_session=False)
            db.query(TrustedDevice).filter(TrustedDevice.employee_id.in_(emp_ids)).delete(synchronize_session=False)
            db.query(LoginOtpChallenge).filter(LoginOtpChallenge.employee_id.in_(emp_ids)).delete(synchronize_session=False)
            db.query(Employee).filter(Employee.id.in_(emp_ids)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

@pytest.fixture(autouse=True)
def setup_teardown():
    get_settings.cache_clear()
    original_env = dict(os.environ)
    cleanup_test_db()
    yield
    cleanup_test_db()
    os.environ.clear()
    os.environ.update(original_env)
    get_settings.cache_clear()


def test_direct_login_session_creation():
    db: Session = SessionLocal()
    try:
        password = "TestPassword123!"
        hashed_pwd = get_password_hash(password)
        user = Employee(
            name="Session Employee",
            email="test_sess_direct@example.com",
            hashed_password=hashed_pwd,
            role=UserRole.AGENT,
            employee_code="TEST_SESS_DIRECT",
            status=EmployeeStatus.ACTIVE.value
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    # Configure off mode
    os.environ["SECURITY_POLICY_MODE"] = "off"
    get_settings.cache_clear()

    # Login without device_id
    response = client.post(
        "/api/auth/login",
        json={"email": "test_sess_direct@example.com", "password": "TestPassword123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "session" in data

    session_meta = data["session"]
    assert session_meta["session_id"] is not None
    assert session_meta["expires_at"] is not None
    assert session_meta["policy_mode"] == "off"

    # Decode token and verify claims
    token = data["access_token"]
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "test_sess_direct@example.com"
    assert payload["user_id"] == user_id
    assert payload["employee_id"] == user_id
    assert payload["role"] == "AGENT"
    assert "sid" in payload
    assert "jti" in payload
    assert "device_id_hash" in payload
    assert "iat" in payload
    assert "exp" in payload

    # Verify session in DB
    db = SessionLocal()
    try:
        db_session = db.query(UserSession).filter(UserSession.employee_id == user_id).first()
        assert db_session is not None
        assert db_session.sid == payload["sid"]
        assert db_session.jti == payload["jti"]
        assert db_session.device_id_hash == payload["device_id_hash"]
        assert db_session.is_active is True

        # Fallback device assertion
        expected_fallback_hash = hash_device_id(f"legacy-device:{user_id}")
        assert db_session.device_id_hash == expected_fallback_hash
        # Confirm raw legacy-device value is NOT stored anywhere in plain text
        assert db_session.device_id_hash != f"legacy-device:{user_id}"
    finally:
        db.close()


def test_login_with_device_id():
    db: Session = SessionLocal()
    try:
        password = "TestPassword123!"
        hashed_pwd = get_password_hash(password)
        user = Employee(
            name="Device Employee",
            email="test_sess_device@example.com",
            hashed_password=hashed_pwd,
            role=UserRole.AGENT,
            employee_code="TEST_SESS_DEVICE",
            status=EmployeeStatus.ACTIVE.value
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "off"
    get_settings.cache_clear()

    # Login with a device ID
    device_id = "device_test_12345"
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test_sess_device@example.com",
            "password": "TestPassword123!",
            "device_id": device_id
        }
    )
    assert response.status_code == 200
    data = response.json()
    token = data["access_token"]
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    expected_hash = hash_device_id(device_id)
    assert payload["device_id_hash"] == expected_hash

    # Verify session in DB
    db = SessionLocal()
    try:
        db_session = db.query(UserSession).filter(UserSession.employee_id == user_id).first()
        assert db_session is not None
        assert db_session.device_id_hash == expected_hash

        # Assert no plain text raw device id is stored
        assert device_id not in [db_session.sid, db_session.jti, db_session.device_id_hash]

        # Assert no plain text raw device id is in AuditEvent fields
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        for audit in audits:
            for field in [audit.target, audit.before_state, audit.after_state, audit.reason]:
                if field:
                    assert device_id not in field
    finally:
        db.close()


def test_otp_login_session_creation():
    db: Session = SessionLocal()
    try:
        password = "TestPassword123!"
        hashed_pwd = get_password_hash(password)
        user = Employee(
            name="OTP Employee",
            email="test_sess_otp@example.com",
            otp_email="test_sess_otp_dest@example.com",
            hashed_password=hashed_pwd,
            role=UserRole.AGENT,
            employee_code="TEST_SESS_OTP",
            status=EmployeeStatus.ACTIVE.value
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "off"
    get_settings.cache_clear()

    # Request login (sends OTP challenge)
    device_id = "otp_device_abcde"
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test_sess_otp@example.com",
            "password": "TestPassword123!",
            "device_id": device_id
        }
    )
    assert response.status_code == 200
    challenge_data = response.json()
    assert challenge_data["otp_required"] is True
    assert "dev_otp_code" in challenge_data

    # Verify no session is created in DB yet
    db = SessionLocal()
    try:
        db_sessions = db.query(UserSession).filter(UserSession.employee_id == user_id).all()
        assert len(db_sessions) == 0
    finally:
        db.close()

    # Verify OTP
    verify_response = client.post(
        "/api/auth/login/verify-otp",
        json={
            "challenge_id": challenge_data["challenge_id"],
            "otp_code": challenge_data["dev_otp_code"],
            "device_id": device_id
        }
    )
    assert verify_response.status_code == 200
    data = verify_response.json()
    assert "access_token" in data
    assert "session" in data

    token = data["access_token"]
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert "sid" in payload
    assert "jti" in payload
    assert payload["device_id_hash"] == hash_device_id(device_id)

    # Verify session is now created in DB
    db = SessionLocal()
    try:
        db_session = db.query(UserSession).filter(UserSession.employee_id == user_id).first()
        assert db_session is not None
        assert db_session.sid == payload["sid"]
    finally:
        db.close()


def test_failure_behavior_invalid_password():
    db: Session = SessionLocal()
    try:
        password = "TestPassword123!"
        hashed_pwd = get_password_hash(password)
        user = Employee(
            name="Fail Employee",
            email="test_sess_fail1@example.com",
            hashed_password=hashed_pwd,
            role=UserRole.AGENT,
            employee_code="TEST_SESS_FAIL1",
            status=EmployeeStatus.ACTIVE.value
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    response = client.post(
        "/api/auth/login",
        json={"email": "test_sess_fail1@example.com", "password": "WrongPassword"}
    )
    assert response.status_code == 401

    db = SessionLocal()
    try:
        db_sessions = db.query(UserSession).filter(UserSession.employee_id == user_id).all()
        assert len(db_sessions) == 0
    finally:
        db.close()


def test_failure_behavior_inactive_employee():
    db: Session = SessionLocal()
    try:
        password = "TestPassword123!"
        hashed_pwd = get_password_hash(password)
        user = Employee(
            name="Inactive Employee",
            email="test_sess_fail2@example.com",
            hashed_password=hashed_pwd,
            role=UserRole.AGENT,
            employee_code="TEST_SESS_FAIL2",
            status="inactive"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    response = client.post(
        "/api/auth/login",
        json={"email": "test_sess_fail2@example.com", "password": "TestPassword123!"}
    )
    assert response.status_code in (401, 403)

    db = SessionLocal()
    try:
        db_sessions = db.query(UserSession).filter(UserSession.employee_id == user_id).all()
        assert len(db_sessions) == 0
    finally:
        db.close()


def test_failure_behavior_session_creation_exception():
    db: Session = SessionLocal()
    try:
        password = "TestPassword123!"
        hashed_pwd = get_password_hash(password)
        user = Employee(
            name="Exception Employee",
            email="test_sess_fail3@example.com",
            hashed_password=hashed_pwd,
            role=UserRole.AGENT,
            employee_code="TEST_SESS_FAIL3",
            status=EmployeeStatus.ACTIVE.value
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    # Patch create_user_session to raise an exception
    with patch("app.routers.auth.create_user_session", side_effect=Exception("Database connection failure")):
        response = client.post(
            "/api/auth/login",
            json={"email": "test_sess_fail3@example.com", "password": "TestPassword123!"}
        )
        assert response.status_code == 500
        assert "Session creation failed" in response.json()["detail"]

    # Verify no session is committed
    db = SessionLocal()
    try:
        db_sessions = db.query(UserSession).filter(UserSession.employee_id == user_id).all()
        assert len(db_sessions) == 0
    finally:
        db.close()


def test_regression_me_endpoint_with_new_token():
    db: Session = SessionLocal()
    try:
        password = "TestPassword123!"
        hashed_pwd = get_password_hash(password)
        user = Employee(
            name="Regression Employee",
            email="test_sess_regr@example.com",
            hashed_password=hashed_pwd,
            role=UserRole.AGENT,
            employee_code="TEST_SESS_REGR",
            status=EmployeeStatus.ACTIVE.value
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    response = client.post(
        "/api/auth/login",
        json={"email": "test_sess_regr@example.com", "password": "TestPassword123!"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    # Use token on /me
    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == "test_sess_regr@example.com"
