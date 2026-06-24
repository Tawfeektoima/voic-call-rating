import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, date, time, timezone, timedelta
from zoneinfo import ZoneInfo
from jose import jwt

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, EmployeeShift, TrustedDevice, UserSession, LoginOtpChallenge, AuditEvent, EmployeeStatus
from app.security import get_password_hash, SECRET_KEY, ALGORITHM
from app.services.security_policy import hash_device_id, get_security_timezone
from app.config import get_settings

client = TestClient(app)

def cleanup_test_db():
    db: Session = SessionLocal()
    try:
        emp_ids = [e.id for e in db.query(Employee).filter(Employee.email.like("test_policy_%")).all()]
        if emp_ids:
            db.query(UserSession).filter(UserSession.employee_id.in_(emp_ids)).delete(synchronize_session=False)
            db.query(TrustedDevice).filter(TrustedDevice.employee_id.in_(emp_ids)).delete(synchronize_session=False)
            db.query(LoginOtpChallenge).filter(LoginOtpChallenge.employee_id.in_(emp_ids)).delete(synchronize_session=False)
            db.query(EmployeeShift).filter(EmployeeShift.employee_id.in_(emp_ids)).delete(synchronize_session=False)
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


def create_test_user(db: Session, email="test_policy_user@example.com", code="TEST_POLICY_USER", otp_email=None) -> Employee:
    password = "TestPassword123!"
    user = Employee(
        name="Policy Employee",
        email=email,
        otp_email=otp_email,
        hashed_password=get_password_hash(password),
        role=UserRole.AGENT,
        employee_code=code,
        status=EmployeeStatus.ACTIVE.value
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_valid_shift(db: Session, employee_id: int):
    tz = get_security_timezone()
    now_local = datetime.now(tz)
    start_dt = now_local - timedelta(hours=2)
    end_dt = now_local + timedelta(hours=2)

    shift = EmployeeShift(
        employee_id=employee_id,
        work_date=start_dt.date(),
        shift_start=start_dt.time(),
        shift_end=end_dt.time(),
        grace_before_minutes=10,
        grace_after_minutes=10,
        status="scheduled"
    )
    db.add(shift)
    db.commit()
    return shift


def test_off_mode_login_works_without_setup():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "off"
    get_settings.cache_clear()

    # Login without device_id, shift, or trusted devices
    response = client.post(
        "/api/auth/login",
        json={"email": "test_policy_user@example.com", "password": "TestPassword123!"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_audit_mode_login_logs_and_allows():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "audit"
    get_settings.cache_clear()

    # Login without allowed shift or device ID
    response = client.post(
        "/api/auth/login",
        json={"email": "test_policy_user@example.com", "password": "TestPassword123!"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

    # Assert audit events exist and contain the correct violation codes in their metadata
    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        after_states = [a.after_state for a in audits if a.after_state]
        assert any("SHIFT_NOT_FOUND" in s for s in after_states) is True
        assert any("DEVICE_REQUIRED" in s for s in after_states) is True
    finally:
        db.close()


def test_enforce_mode_blocks_shift_denial():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    # Login with no shift in DB (should return SHIFT_NOT_ALLOWED)
    response = client.post(
        "/api/auth/login",
        json={"email": "test_policy_user@example.com", "password": "TestPassword123!", "device_id": "some_device_id"}
    )
    assert response.status_code == 403
    data = response.json()
    assert data["detail"]["code"] == "SHIFT_NOT_ALLOWED"

    # Verify no session created
    db = SessionLocal()
    try:
        db_sessions = db.query(UserSession).filter(UserSession.employee_id == user_id).all()
        assert len(db_sessions) == 0
    finally:
        db.close()


def test_enforce_mode_first_device_auto_enrolls():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        create_valid_shift(db, user_id)
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    # Login with a device ID (first login, no trusted devices exist)
    response = client.post(
        "/api/auth/login",
        json={"email": "test_policy_user@example.com", "password": "TestPassword123!", "device_id": "first_device_id"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

    # Verify device is auto-enrolled and approved
    db = SessionLocal()
    try:
        dev = db.query(TrustedDevice).filter(TrustedDevice.employee_id == user_id).first()
        assert dev is not None
        assert dev.device_id_hash == hash_device_id("first_device_id")
        assert dev.approved_at is not None
        assert dev.is_trusted is True
    finally:
        db.close()


def test_enforce_mode_second_device_blocked():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        create_valid_shift(db, user_id)

        # Manually enroll a device so user already has one
        dev = TrustedDevice(
            employee_id=user_id,
            device_id_hash=hash_device_id("device_one"),
            device_label="First Device",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
            approved_at=datetime.now(timezone.utc),
            is_trusted=True
        )
        db.add(dev)
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    # Login with a DIFFERENT device ID
    response = client.post(
        "/api/auth/login",
        json={"email": "test_policy_user@example.com", "password": "TestPassword123!", "device_id": "device_two"}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "DEVICE_NOT_TRUSTED"


def test_enforce_mode_active_session_blocked():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        create_valid_shift(db, user_id)

        # Enroll device first
        dev = TrustedDevice(
            employee_id=user_id,
            device_id_hash=hash_device_id("my_device"),
            device_label="My Device",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
            approved_at=datetime.now(timezone.utc),
            is_trusted=True
        )
        db.add(dev)
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    # First login succeeds
    response1 = client.post(
        "/api/auth/login",
        json={"email": "test_policy_user@example.com", "password": "TestPassword123!", "device_id": "my_device"}
    )
    assert response1.status_code == 200

    # Second login with same device fails due to session conflict
    response2 = client.post(
        "/api/auth/login",
        json={"email": "test_policy_user@example.com", "password": "TestPassword123!", "device_id": "my_device"}
    )
    assert response2.status_code == 409
    assert response2.json()["detail"]["code"] == "ACTIVE_SESSION_EXISTS"


def test_invalid_credentials_no_policy_side_effects():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    # Login with wrong password
    response = client.post(
        "/api/auth/login",
        json={"email": "test_policy_user@example.com", "password": "WrongPassword", "device_id": "device_xyz"}
    )
    assert response.status_code == 401

    # Verify no trusted devices are created (no auto-enrollment occurred)
    # and no audit events for security policy decisions were logged.
    db = SessionLocal()
    try:
        devs = db.query(TrustedDevice).filter(TrustedDevice.employee_id == user_id).all()
        assert len(devs) == 0

        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        # Verify no policy audits (e.g. SHIFT_ACCESS_DENIED, etc.)
        for audit in audits:
            assert audit.action not in ("SHIFT_ACCESS_DENIED", "TRUSTED_DEVICE_ENROLLED", "DEVICE_REQUIRED")
    finally:
        db.close()


def test_otp_challenge_stores_device_hash():
    db = SessionLocal()
    try:
        user = create_test_user(db, otp_email="test_otp_dest@example.com")
        user_id = user.id
        create_valid_shift(db, user_id)
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    device_id = "otp_device_id"
    response = client.post(
        "/api/auth/login",
        json={"email": "test_policy_user@example.com", "password": "TestPassword123!", "device_id": device_id}
    )
    assert response.status_code == 200
    challenge_data = response.json()
    assert challenge_data["otp_required"] is True

    # Query DB to ensure the challenge is bound to the device's hash
    db = SessionLocal()
    try:
        challenge = db.query(LoginOtpChallenge).filter(LoginOtpChallenge.id == challenge_data["challenge_id"]).first()
        assert challenge is not None
        assert challenge.device_id_hash == hash_device_id(device_id)
    finally:
        db.close()


def test_otp_verify_device_mismatch():
    db = SessionLocal()
    try:
        user = create_test_user(db, otp_email="test_otp_dest@example.com")
        user_id = user.id
        create_valid_shift(db, user_id)
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    # Login with device_a
    response = client.post(
        "/api/auth/login",
        json={"email": "test_policy_user@example.com", "password": "TestPassword123!", "device_id": "device_a"}
    )
    assert response.status_code == 200
    challenge_data = response.json()

    # Verify with device_b
    verify_response = client.post(
        "/api/auth/login/verify-otp",
        json={
            "challenge_id": challenge_data["challenge_id"],
            "otp_code": challenge_data["dev_otp_code"],
            "device_id": "device_b"
        }
    )
    assert verify_response.status_code == 403
    assert verify_response.json()["detail"]["code"] == "OTP_DEVICE_MISMATCH"


def test_otp_verify_session_recheck():
    db = SessionLocal()
    try:
        user = create_test_user(db, otp_email="test_otp_dest@example.com")
        user_id = user.id
        create_valid_shift(db, user_id)

        # Enroll device first so it is trusted
        dev = TrustedDevice(
            employee_id=user_id,
            device_id_hash=hash_device_id("my_device"),
            device_label="My Device",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
            approved_at=datetime.now(timezone.utc),
            is_trusted=True
        )
        db.add(dev)
        db.commit()
        dev_id = dev.id
        dev_hash = dev.device_id_hash
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    # Start OTP login
    response = client.post(
        "/api/auth/login",
        json={"email": "test_policy_user@example.com", "password": "TestPassword123!", "device_id": "my_device"}
    )
    assert response.status_code == 200
    challenge_data = response.json()

    # Simulate another session getting created for this user before they verify their OTP
    db = SessionLocal()
    try:
        session = UserSession(
            employee_id=user_id,
            trusted_device_id=dev_id,
            sid="simulated_sid_123",
            jti="simulated_jti_123",
            device_id_hash=dev_hash,
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_active=True
        )
        db.add(session)
        db.commit()
    finally:
        db.close()

    # Try verifying OTP now, which should fail because a session conflict now exists
    verify_response = client.post(
        "/api/auth/login/verify-otp",
        json={
            "challenge_id": challenge_data["challenge_id"],
            "otp_code": challenge_data["dev_otp_code"],
            "device_id": "my_device"
        }
    )
    assert verify_response.status_code == 409
    assert verify_response.json()["detail"]["code"] == "ACTIVE_SESSION_EXISTS"
