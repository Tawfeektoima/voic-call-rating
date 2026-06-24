import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, date, time, timezone, timedelta
from jose import jwt

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, EmployeeShift, TrustedDevice, UserSession, LoginOtpChallenge, AuditEvent, EmployeeStatus
from app.security import get_password_hash, SECRET_KEY, ALGORITHM, create_access_token
from app.services.security_policy import hash_device_id, get_security_timezone
from app.config import get_settings

client = TestClient(app)

def cleanup_test_db():
    db: Session = SessionLocal()
    try:
        emp_ids = [e.id for e in db.query(Employee).filter(Employee.email.like("test_corrective_%")).all()]
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


def create_test_user(db: Session, email="test_corrective_user@example.com", code="TEST_CORRECTIVE_USER", otp_email=None) -> Employee:
    password = "TestPassword123!"
    user = Employee(
        name="Corrective Employee",
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


def assert_no_sensitive_values_in_audits(db: Session, user_id: int, sensitive_values: list[str]):
    audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
    for audit in audits:
        for val in sensitive_values:
            if not val or len(val) < 4:
                continue
            assert val not in (audit.action or "")
            assert val not in (audit.target or "")
            assert val not in (audit.after_state or "")
            assert val not in (audit.reason or "")


# 1. SECURITY_POLICY_MODE=off login with device_id creates a UserSession but creates no TrustedDevice.
def test_off_mode_login_creates_session_but_no_trusted_device():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "off"
    get_settings.cache_clear()

    device_id = "test_off_device_123"

    response = client.post(
        "/api/auth/login",
        json={"email": "test_corrective_user@example.com", "password": "TestPassword123!", "device_id": device_id}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

    db = SessionLocal()
    try:
        # Check that a UserSession was created
        sessions = db.query(UserSession).filter(UserSession.employee_id == user_id).all()
        assert len(sessions) == 1
        assert sessions[0].device_id_hash == hash_device_id(device_id)

        # Check that no TrustedDevice was created
        devices = db.query(TrustedDevice).filter(TrustedDevice.employee_id == user_id).all()
        assert len(devices) == 0

        # 11. Assert no raw device_id, sid, jti, or token values appear in audit fields
        assert_no_sensitive_values_in_audits(db, user_id, [device_id, sessions[0].sid, sessions[0].jti, data["access_token"]])
    finally:
        db.close()


# 2. Enforce shift denial writes a persisted audit event with SHIFT_NOT_FOUND or normalized SHIFT_NOT_ALLOWED.
def test_enforce_shift_denial_persists_audit():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    device_id = "dev_shift"
    response = client.post(
        "/api/auth/login",
        json={"email": "test_corrective_user@example.com", "password": "TestPassword123!", "device_id": device_id}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "SHIFT_NOT_ALLOWED"

    db = SessionLocal()
    try:
        # Check that the audit event is persisted
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        assert len(audits) >= 1
        denials = [a for a in audits if a.action == "SECURITY_POLICY_DENIAL"]
        assert len(denials) == 1
        assert "SHIFT_NOT_FOUND" in denials[0].after_state
        
        # 11. Assert no raw values
        assert_no_sensitive_values_in_audits(db, user_id, [device_id])
    finally:
        db.close()


# 3. Enforce device denial writes a persisted audit event with DEVICE_NOT_TRUSTED.
def test_enforce_device_denial_persists_audit():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        create_valid_shift(db, user_id)
        # Enroll an initial device so the next device is not auto-enrolled under first-device rule
        other_dev = TrustedDevice(
            employee_id=user_id,
            device_id_hash=hash_device_id("other_device"),
            device_label="First Device",
            is_trusted=True,
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
            approved_at=datetime.now(timezone.utc)
        )
        db.add(other_dev)
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    device_id = "dev_denied"
    response = client.post(
        "/api/auth/login",
        json={"email": "test_corrective_user@example.com", "password": "TestPassword123!", "device_id": device_id}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "DEVICE_NOT_TRUSTED"

    db = SessionLocal()
    try:
        # Check that the audit event is persisted
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        denials = [a for a in audits if a.action == "SECURITY_POLICY_DENIAL"]
        assert len(denials) == 1
        assert "DEVICE_NOT_TRUSTED" in denials[0].after_state
        
        # 11. Assert no raw values
        assert_no_sensitive_values_in_audits(db, user_id, [device_id])
    finally:
        db.close()


# 4. Enforce active-session conflict writes a persisted audit event with ACTIVE_SESSION_EXISTS.
def test_enforce_active_session_conflict_persists_audit():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        create_valid_shift(db, user_id)
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    device_id = "dev_conflict"

    # First login succeeds (enrolls device and creates session)
    response1 = client.post(
        "/api/auth/login",
        json={"email": "test_corrective_user@example.com", "password": "TestPassword123!", "device_id": device_id}
    )
    assert response1.status_code == 200
    token1 = response1.json()["access_token"]

    # Second login with same device fails due to session conflict
    response2 = client.post(
        "/api/auth/login",
        json={"email": "test_corrective_user@example.com", "password": "TestPassword123!", "device_id": device_id}
    )
    assert response2.status_code == 409
    assert response2.json()["detail"]["code"] == "ACTIVE_SESSION_EXISTS"

    db = SessionLocal()
    try:
        # Check that the audit event is persisted
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        denials = [a for a in audits if a.action == "SECURITY_POLICY_DENIAL"]
        assert len(denials) == 1
        assert "ACTIVE_SESSION_EXISTS" in denials[0].after_state
        
        # Get the sid/jti from token1 to make sure they are not logged raw
        payload1 = jwt.decode(token1, SECRET_KEY, algorithms=[ALGORITHM])
        sid1 = payload1["sid"]
        jti1 = payload1["jti"]
        assert_no_sensitive_values_in_audits(db, user_id, [device_id, sid1, jti1, token1])
    finally:
        db.close()


# 5. OTP session re-check denial does not mark the challenge as used.
# 6. OTP session re-check denial does not write a successful LOGIN_OTP_VERIFY audit.
def test_otp_session_recheck_denial_does_not_consume_otp_or_write_success_audit():
    db = SessionLocal()
    try:
        user = create_test_user(db, otp_email="test_otp_corrective@example.com")
        user_id = user.id
        shift = create_valid_shift(db, user_id)
        shift_id = shift.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    device_id = "otp_device_recheck"

    # Request OTP
    response1 = client.post(
        "/api/auth/login",
        json={"email": "test_corrective_user@example.com", "password": "TestPassword123!", "device_id": device_id}
    )
    assert response1.status_code == 200
    challenge_data = response1.json()
    assert challenge_data["otp_required"] is True
    challenge_id = challenge_data["challenge_id"]
    otp_code = challenge_data.get("dev_otp_code") or "000000"

    # Delete the shift to trigger SHIFT_NOT_ALLOWED during OTP verification recheck
    db = SessionLocal()
    try:
        db.query(EmployeeShift).filter(EmployeeShift.id == shift_id).delete()
        db.commit()
    finally:
        db.close()

    # Call verify-otp
    response2 = client.post(
        "/api/auth/login/verify-otp",
        json={"challenge_id": challenge_id, "otp_code": otp_code, "device_id": device_id}
    )
    assert response2.status_code == 403
    assert response2.json()["detail"]["code"] == "SHIFT_NOT_ALLOWED"

    db = SessionLocal()
    try:
        # 5. Assert OTP challenge is NOT marked as used
        challenge = db.query(LoginOtpChallenge).filter(LoginOtpChallenge.id == challenge_id).first()
        assert challenge.used_at is None

        # 6. Assert NO successful LOGIN_OTP_VERIFY audit event is written
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        otp_verify_success = [a for a in audits if a.action == "LOGIN_OTP_VERIFY" and a.success is True]
        assert len(otp_verify_success) == 0

        # Assert the denial is persisted
        denials = [a for a in audits if a.action == "SECURITY_POLICY_DENIAL"]
        assert len(denials) == 1
        assert "SHIFT_NOT_FOUND" in denials[0].after_state

        assert_no_sensitive_values_in_audits(db, user_id, [device_id, otp_code])
    finally:
        db.close()


# 7. OTP device mismatch denial audit is persisted.
def test_otp_device_mismatch_denial_persists_audit():
    db = SessionLocal()
    try:
        user = create_test_user(db, otp_email="test_otp_corrective@example.com")
        user_id = user.id
        create_valid_shift(db, user_id)
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    device_a = "device_a_corrective"
    device_b = "device_b_corrective"

    # Request OTP with device_a
    response1 = client.post(
        "/api/auth/login",
        json={"email": "test_corrective_user@example.com", "password": "TestPassword123!", "device_id": device_a}
    )
    assert response1.status_code == 200
    challenge_data = response1.json()
    challenge_id = challenge_data["challenge_id"]
    otp_code = challenge_data.get("dev_otp_code") or "000000"

    # Verify with device_b
    response2 = client.post(
        "/api/auth/login/verify-otp",
        json={"challenge_id": challenge_id, "otp_code": otp_code, "device_id": device_b}
    )
    assert response2.status_code == 403
    assert response2.json()["detail"]["code"] == "OTP_DEVICE_MISMATCH"

    db = SessionLocal()
    try:
        # Check that OTP mismatch denial audit is written
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        denials = [a for a in audits if "OTP_DEVICE_MISMATCH" in (a.after_state or "")]
        assert len(denials) >= 1
        
        assert_no_sensitive_values_in_audits(db, user_id, [device_a, device_b, otp_code])
    finally:
        db.close()


# 8. Repeated logout keeps the same revoked_at.
# 9. Repeated logout returns 200 OK.
def test_repeated_logout_idempotency():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        create_valid_shift(db, user_id)
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    device_id = "logout_dev"

    # Login
    response = client.post(
        "/api/auth/login",
        json={"email": "test_corrective_user@example.com", "password": "TestPassword123!", "device_id": device_id}
    )
    assert response.status_code == 200
    data = response.json()
    token = data["access_token"]
    session_id = data["session"]["session_id"]

    # Logout 1
    logout1 = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert logout1.status_code == 200

    db = SessionLocal()
    try:
        sess = db.query(UserSession).filter(UserSession.id == session_id).first()
        assert sess.is_active is False
        assert sess.revoked_at is not None
        revoked_at_1 = sess.revoked_at
    finally:
        db.close()

    # Logout 2 (repeated)
    logout2 = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert logout2.status_code == 200

    db = SessionLocal()
    try:
        sess = db.query(UserSession).filter(UserSession.id == session_id).first()
        assert sess.is_active is False
        assert sess.revoked_at == revoked_at_1

        # Check metadata shows already_revoked is true
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id, AuditEvent.action == "SESSION_REVOKED").all()
        assert len(audits) >= 2
        states = [a.after_state for a in audits]
        assert any("already_revoked\": true" in s for s in states)
        assert any("already_revoked\": false" in s for s in states)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert_no_sensitive_values_in_audits(db, user_id, [device_id, sess.sid, sess.jti, token])
    finally:
        db.close()


# 10. Legacy token logout writes a safe audit event.
def test_legacy_token_logout_audits_safely():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
    finally:
        db.close()

    # Create a legacy access token without sid or jti
    legacy_token = create_access_token(
        data={"sub": user.email, "user_id": user_id, "role": "AGENT"}
    )

    # Logout
    response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {legacy_token}"}
    )
    assert response.status_code == 200

    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id, AuditEvent.action == "SESSION_REVOKED").all()
        assert len(audits) == 1
        audit = audits[0]
        assert "legacy_token\": true" in audit.after_state
        assert "session_found\": false" in audit.after_state
        assert "reason\": \"logout\"" in audit.after_state
        
        # Ensure no raw token/sensitive info is logged
        assert_no_sensitive_values_in_audits(db, user_id, [legacy_token])
    finally:
        db.close()
