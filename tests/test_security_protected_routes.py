import os
import pytest
import secrets
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from jose import jwt

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, UserSession, TrustedDevice, AuditEvent, EmployeeStatus, EmployeeShift
from app.security import get_password_hash, SECRET_KEY, ALGORITHM, create_access_token
from app.services.security_policy import hash_device_id, get_security_timezone
from app.config import get_settings

client = TestClient(app)

def cleanup_test_db():
    db: Session = SessionLocal()
    try:
        emp_ids = [e.id for e in db.query(Employee).filter(Employee.email.like("test_protected_%")).all()]
        if emp_ids:
            db.query(UserSession).filter(UserSession.employee_id.in_(emp_ids)).delete(synchronize_session=False)
            db.query(TrustedDevice).filter(TrustedDevice.employee_id.in_(emp_ids)).delete(synchronize_session=False)
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


def create_test_user(db: Session, email="test_protected_user@example.com", code="TEST_PROTECTED_USER") -> Employee:
    password = "TestPassword123!"
    user = Employee(
        name="Protected Employee",
        email=email,
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


# 1. off mode: old legacy token without sid/jti can still call /api/auth/me.
def test_off_mode_legacy_token_allowed():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        user_email = user.email
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "off"
    get_settings.cache_clear()

    # Create a legacy access token without sid or jti
    legacy_token = create_access_token(
        data={"sub": user_email, "user_id": user_id, "role": "AGENT"}
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {legacy_token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == user_email


# 2. audit mode: legacy token without sid/jti can call /api/auth/me and persists audit.
def test_audit_mode_legacy_token_allowed_and_audited():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        user_email = user.email
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "audit"
    get_settings.cache_clear()

    legacy_token = create_access_token(
        data={"sub": user_email, "user_id": user_id, "role": "AGENT"}
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {legacy_token}"}
    )
    assert response.status_code == 200

    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        assert len(audits) >= 1
        violations = [a for a in audits if "SESSION_CLAIMS_MISSING" in (a.after_state or "")]
        assert len(violations) >= 1
        assert "SESSION_CLAIMS_MISSING" in violations[0].after_state
        assert_no_sensitive_values_in_audits(db, user_id, [legacy_token])
    finally:
        db.close()


# 3. enforce mode: legacy token without sid/jti gets 401 SESSION_CLAIMS_MISSING.
def test_enforce_mode_legacy_token_denied():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        user_email = user.email
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    legacy_token = create_access_token(
        data={"sub": user_email, "user_id": user_id, "role": "AGENT"}
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {legacy_token}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "SESSION_CLAIMS_MISSING"

    db = SessionLocal()
    try:
        # Check audit event is persisted
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        denials = [a for a in audits if a.action == "SECURITY_POLICY_DENIAL"]
        assert len(denials) == 1
        assert "SESSION_CLAIMS_MISSING" in denials[0].after_state
        assert_no_sensitive_values_in_audits(db, user_id, [legacy_token])
    finally:
        db.close()


# 4. Valid session token in enforce mode can call /api/auth/me.
def test_enforce_mode_valid_session_allowed():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        user_email = user.email
        create_valid_shift(db, user_id)
        
        # Create a valid session and enroll device to pass all checks
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_id_hash = hash_device_id("my_device_xyz")
        now = datetime.utcnow()
        session = UserSession(
            employee_id=user_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_id_hash,
            issued_at=now,
            last_seen_at=now - timedelta(minutes=5),
            expires_at=now + timedelta(hours=1),
            is_active=True
        )
        db.add(session)
        
        dev = TrustedDevice(
            employee_id=user_id,
            device_id_hash=device_id_hash,
            device_label="My Device",
            is_trusted=True,
            first_seen_at=now,
            last_seen_at=now,
            approved_at=now
        )
        db.add(dev)
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti,
            "device_id_hash": device_id_hash
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == user_email


# 5. Missing session row in enforce mode gets 401 SESSION_NOT_FOUND.
def test_enforce_mode_missing_session_row_denied():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        user_email = user.email
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    sid = secrets.token_hex(32)
    jti = secrets.token_hex(32)
    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "SESSION_NOT_FOUND"

    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        denials = [a for a in audits if a.action == "SECURITY_POLICY_DENIAL"]
        assert len(denials) == 1
        assert "SESSION_NOT_FOUND" in denials[0].after_state
        assert_no_sensitive_values_in_audits(db, user_id, [sid, jti, token])
    finally:
        db.close()


# 6. Revoked session in enforce mode gets 401 SESSION_REVOKED.
def test_enforce_mode_revoked_session_denied():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        user_email = user.email
        
        # Create a revoked session
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_id_hash = hash_device_id("my_device_xyz")
        now = datetime.utcnow()
        session = UserSession(
            employee_id=user_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_id_hash,
            issued_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(hours=1),
            is_active=False,
            revoked_at=now,
            revoke_reason="logout"
        )
        db.add(session)
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti,
            "device_id_hash": device_id_hash
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "SESSION_REVOKED"

    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        denials = [a for a in audits if a.action in ("SECURITY_POLICY_DENIAL", "SESSION_REVOKED")]
        assert len(denials) == 1
        assert "SESSION_REVOKED" in denials[0].after_state
        assert_no_sensitive_values_in_audits(db, user_id, [sid, jti, token])
    finally:
        db.close()


# 7. Expired session in enforce mode gets 401 SESSION_EXPIRED.
def test_enforce_mode_expired_session_denied():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        user_email = user.email
        
        # Create an expired session
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_id_hash = hash_device_id("my_device_xyz")
        now = datetime.utcnow()
        session = UserSession(
            employee_id=user_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_id_hash,
            issued_at=now - timedelta(hours=2),
            last_seen_at=now - timedelta(hours=2),
            expires_at=now - timedelta(minutes=5),
            is_active=True
        )
        db.add(session)
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti,
            "device_id_hash": device_id_hash
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "SESSION_EXPIRED"

    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        denials = [a for a in audits if a.action == "SECURITY_POLICY_DENIAL"]
        assert len(denials) == 1
        assert "SESSION_EXPIRED" in denials[0].after_state
        assert_no_sensitive_values_in_audits(db, user_id, [sid, jti, token])
    finally:
        db.close()


# 8. Device hash mismatch in enforce mode gets 403 SESSION_DEVICE_MISMATCH.
def test_enforce_mode_device_mismatch_denied():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        user_email = user.email
        
        # Create a session bound to device A
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_a_hash = hash_device_id("device_a")
        now = datetime.utcnow()
        session = UserSession(
            employee_id=user_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_a_hash,
            issued_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(hours=1),
            is_active=True
        )
        db.add(session)
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    # Token represents device B
    device_b_hash = hash_device_id("device_b")
    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti,
            "device_id_hash": device_b_hash
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "SESSION_DEVICE_MISMATCH"

    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        denials = [a for a in audits if a.action == "SECURITY_POLICY_DENIAL"]
        assert len(denials) == 1
        assert "SESSION_DEVICE_MISMATCH" in denials[0].after_state
        assert_no_sensitive_values_in_audits(db, user_id, [sid, jti, token, device_a_hash, device_b_hash])
    finally:
        db.close()


# 9. Valid protected request updates UserSession.last_seen_at.
def test_valid_request_updates_last_seen():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        user_email = user.email
        create_valid_shift(db, user_id)
        
        # Create a valid session with past last_seen_at and valid device
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_id_hash = hash_device_id("my_device_xyz")
        initial_last_seen = datetime.utcnow() - timedelta(minutes=10)
        session = UserSession(
            employee_id=user_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_id_hash,
            issued_at=initial_last_seen,
            last_seen_at=initial_last_seen,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_active=True
        )
        db.add(session)
        
        dev = TrustedDevice(
            employee_id=user_id,
            device_id_hash=device_id_hash,
            device_label="My Device",
            is_trusted=True,
            first_seen_at=initial_last_seen,
            last_seen_at=initial_last_seen,
            approved_at=initial_last_seen
        )
        db.add(dev)
        db.commit()
        session_id = session.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti,
            "device_id_hash": device_id_hash
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

    db = SessionLocal()
    try:
        sess = db.query(UserSession).filter(UserSession.id == session_id).first()
        # Verify that last_seen_at has increased
        assert sess.last_seen_at > initial_last_seen
    finally:
        db.close()


# 10. off mode: protected route works without shift or trusted device.
def test_off_mode_no_shift_or_device_allowed():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        user_email = user.email
        
        # Create a valid session
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_id_hash = hash_device_id("my_device_xyz")
        now = datetime.utcnow()
        session = UserSession(
            employee_id=user_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_id_hash,
            issued_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(hours=1),
            is_active=True
        )
        db.add(session)
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "off"
    get_settings.cache_clear()

    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti,
            "device_id_hash": device_id_hash
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


# 11. audit mode: protected route outside shift logs violation and allows.
def test_audit_mode_outside_shift_allowed_and_audited():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        user_email = user.email
        
        # Create a valid session and enroll device
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_id_hash = hash_device_id("my_device_xyz")
        now = datetime.utcnow()
        session = UserSession(
            employee_id=user_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_id_hash,
            issued_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(hours=1),
            is_active=True
        )
        db.add(session)
        
        dev = TrustedDevice(
            employee_id=user_id,
            device_id_hash=device_id_hash,
            device_label="My Device",
            is_trusted=True,
            first_seen_at=now,
            last_seen_at=now,
            approved_at=now
        )
        db.add(dev)
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "audit"
    get_settings.cache_clear()

    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti,
            "device_id_hash": device_id_hash
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        violations = [a for a in audits if "SHIFT_NOT_FOUND" in (a.after_state or "")]
        assert len(violations) >= 1
        assert_no_sensitive_values_in_audits(db, user_id, [sid, jti, token])
    finally:
        db.close()


# 12. enforce mode: protected route outside shift returns 403 SHIFT_NOT_ALLOWED.
def test_enforce_mode_outside_shift_denied():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        user_email = user.email
        
        # Create valid session and enroll device
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_id_hash = hash_device_id("my_device_xyz")
        now = datetime.utcnow()
        session = UserSession(
            employee_id=user_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_id_hash,
            issued_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(hours=1),
            is_active=True
        )
        db.add(session)
        
        dev = TrustedDevice(
            employee_id=user_id,
            device_id_hash=device_id_hash,
            device_label="My Device",
            is_trusted=True,
            first_seen_at=now,
            last_seen_at=now,
            approved_at=now
        )
        db.add(dev)
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti,
            "device_id_hash": device_id_hash
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "SHIFT_NOT_ALLOWED"

    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        denials = [a for a in audits if a.action == "SECURITY_POLICY_DENIAL" and "SHIFT_NOT_FOUND" in (a.after_state or "")]
        assert len(denials) == 1
        assert_no_sensitive_values_in_audits(db, user_id, [sid, jti, token])
    finally:
        db.close()


# 13. audit mode: revoked trusted device logs violation and allows.
def test_audit_mode_revoked_device_allowed_and_audited():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        user_email = user.email
        create_valid_shift(db, user_id)
        
        # Create session and a revoked device
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_id_hash = hash_device_id("my_device_xyz")
        now = datetime.utcnow()
        session = UserSession(
            employee_id=user_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_id_hash,
            issued_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(hours=1),
            is_active=True
        )
        db.add(session)
        
        dev = TrustedDevice(
            employee_id=user_id,
            device_id_hash=device_id_hash,
            device_label="My Device",
            is_trusted=False,
            revoked_at=now,
            revoke_reason="compromised",
            first_seen_at=now,
            last_seen_at=now,
            approved_at=now
        )
        db.add(dev)
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "audit"
    get_settings.cache_clear()

    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti,
            "device_id_hash": device_id_hash
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        violations = [a for a in audits if "DEVICE_NOT_TRUSTED" in (a.after_state or "")]
        assert len(violations) >= 1
        assert_no_sensitive_values_in_audits(db, user_id, [sid, jti, token])
    finally:
        db.close()


# 14. enforce mode: revoked trusted device returns 403 DEVICE_NOT_TRUSTED.
def test_enforce_mode_revoked_device_denied():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        user_email = user.email
        create_valid_shift(db, user_id)
        
        # Create session and a revoked device
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_id_hash = hash_device_id("my_device_xyz")
        now = datetime.utcnow()
        session = UserSession(
            employee_id=user_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_id_hash,
            issued_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(hours=1),
            is_active=True
        )
        db.add(session)
        
        dev = TrustedDevice(
            employee_id=user_id,
            device_id_hash=device_id_hash,
            device_label="My Device",
            is_trusted=False,
            revoked_at=now,
            revoke_reason="compromised",
            first_seen_at=now,
            last_seen_at=now,
            approved_at=now
        )
        db.add(dev)
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti,
            "device_id_hash": device_id_hash
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "DEVICE_NOT_TRUSTED"

    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        denials = [a for a in audits if a.action == "SECURITY_POLICY_DENIAL" and "DEVICE_NOT_TRUSTED" in (a.after_state or "")]
        assert len(denials) == 1
        assert_no_sensitive_values_in_audits(db, user_id, [sid, jti, token])
    finally:
        db.close()


# 15. Valid shift and valid trusted device allow protected route in enforce mode.
def test_enforce_mode_success():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        user_email = user.email
        create_valid_shift(db, user_id)
        
        # Create session and valid device
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_id_hash = hash_device_id("my_device_xyz")
        now = datetime.utcnow()
        session = UserSession(
            employee_id=user_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_id_hash,
            issued_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(hours=1),
            is_active=True
        )
        db.add(session)
        
        dev = TrustedDevice(
            employee_id=user_id,
            device_id_hash=device_id_hash,
            device_label="My Device",
            is_trusted=True,
            first_seen_at=now,
            last_seen_at=now,
            approved_at=now
        )
        db.add(dev)
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti,
            "device_id_hash": device_id_hash
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == user_email


# 16. Logout still returns 200 OK for already-revoked sessions.
def test_logout_remains_usable_when_revoked():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
        user_email = user.email
        
        # Create a revoked session
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_id_hash = hash_device_id("my_device_xyz")
        now = datetime.utcnow()
        session = UserSession(
            employee_id=user_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_id_hash,
            issued_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(hours=1),
            is_active=False,
            revoked_at=now,
            revoke_reason="logout"
        )
        db.add(session)
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti
        }
    )

    # Even though session is revoked, /logout bypasses revalidation and returns success
    response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Logged out successfully"}


# 17. Enforce-mode outside-shift denial does not change UserSession.last_seen_at.
def test_enforce_mode_outside_shift_does_not_update_last_seen():
    db = SessionLocal()
    try:
        user = create_test_user(db, email="test_protected_17@example.com", code="TEST_P_17")
        user_id = user.id
        user_email = user.email
        
        # Create valid session and enroll device (no shift scheduled)
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_id_hash = hash_device_id("my_device_xyz")
        now = datetime.utcnow()
        initial_last_seen = now - timedelta(minutes=10)
        session = UserSession(
            employee_id=user_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_id_hash,
            issued_at=initial_last_seen,
            last_seen_at=initial_last_seen,
            expires_at=now + timedelta(hours=1),
            is_active=True
        )
        db.add(session)
        
        dev = TrustedDevice(
            employee_id=user_id,
            device_id_hash=device_id_hash,
            device_label="My Device",
            is_trusted=True,
            first_seen_at=now,
            last_seen_at=now,
            approved_at=now
        )
        db.add(dev)
        db.commit()
        session_id = session.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti,
            "device_id_hash": device_id_hash
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "SHIFT_NOT_ALLOWED"

    db = SessionLocal()
    try:
        sess = db.query(UserSession).filter(UserSession.id == session_id).first()
        # last_seen_at must remain initial_last_seen (not updated)
        assert sess.last_seen_at == initial_last_seen
    finally:
        db.close()


# 18. Enforce-mode revoked-device denial does not change UserSession.last_seen_at.
def test_enforce_mode_revoked_device_does_not_update_last_seen():
    db = SessionLocal()
    try:
        user = create_test_user(db, email="test_protected_18@example.com", code="TEST_P_18")
        user_id = user.id
        user_email = user.email
        create_valid_shift(db, user_id)
        
        # Create session and revoked device
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_id_hash = hash_device_id("my_device_xyz")
        now = datetime.utcnow()
        initial_last_seen = now - timedelta(minutes=10)
        session = UserSession(
            employee_id=user_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_id_hash,
            issued_at=initial_last_seen,
            last_seen_at=initial_last_seen,
            expires_at=now + timedelta(hours=1),
            is_active=True
        )
        db.add(session)
        
        dev = TrustedDevice(
            employee_id=user_id,
            device_id_hash=device_id_hash,
            device_label="My Device",
            is_trusted=False,
            revoked_at=now,
            first_seen_at=now,
            last_seen_at=now,
            approved_at=now
        )
        db.add(dev)
        db.commit()
        session_id = session.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti,
            "device_id_hash": device_id_hash
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "DEVICE_NOT_TRUSTED"

    db = SessionLocal()
    try:
        sess = db.query(UserSession).filter(UserSession.id == session_id).first()
        # last_seen_at must remain initial_last_seen (not updated)
        assert sess.last_seen_at == initial_last_seen
    finally:
        db.close()


# 19. Audit-mode outside-shift warning allows request and updates last_seen_at.
def test_audit_mode_outside_shift_updates_last_seen():
    db = SessionLocal()
    try:
        user = create_test_user(db, email="test_protected_19@example.com", code="TEST_P_19")
        user_id = user.id
        user_email = user.email
        
        # Create valid session and enroll device (no shift)
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_id_hash = hash_device_id("my_device_xyz")
        now = datetime.utcnow()
        initial_last_seen = now - timedelta(minutes=10)
        session = UserSession(
            employee_id=user_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_id_hash,
            issued_at=initial_last_seen,
            last_seen_at=initial_last_seen,
            expires_at=now + timedelta(hours=1),
            is_active=True
        )
        db.add(session)
        
        dev = TrustedDevice(
            employee_id=user_id,
            device_id_hash=device_id_hash,
            device_label="My Device",
            is_trusted=True,
            first_seen_at=now,
            last_seen_at=now,
            approved_at=now
        )
        db.add(dev)
        db.commit()
        session_id = session.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "audit"
    get_settings.cache_clear()

    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti,
            "device_id_hash": device_id_hash
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

    db = SessionLocal()
    try:
        sess = db.query(UserSession).filter(UserSession.id == session_id).first()
        # last_seen_at must be updated because request is allowed in audit mode
        assert sess.last_seen_at > initial_last_seen
    finally:
        db.close()


# 20. Enforce-mode token with sid/jti but missing device_id_hash returns 403 SESSION_DEVICE_MISMATCH.
def test_enforce_mode_token_missing_device_id_hash_denied():
    db = SessionLocal()
    try:
        user = create_test_user(db, email="test_protected_20@example.com", code="TEST_P_20")
        user_id = user.id
        user_email = user.email
        create_valid_shift(db, user_id)
        
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_id_hash = hash_device_id("my_device_xyz")
        now = datetime.utcnow()
        session = UserSession(
            employee_id=user_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_id_hash,
            issued_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(hours=1),
            is_active=True
        )
        db.add(session)
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    # Token has sid/jti but no device_id_hash
    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "SESSION_DEVICE_MISMATCH"


# 21. Audit-mode token missing device_id_hash logs SESSION_DEVICE_MISMATCH and allows.
def test_audit_mode_token_missing_device_id_hash_allowed():
    db = SessionLocal()
    try:
        user = create_test_user(db, email="test_protected_21@example.com", code="TEST_P_21")
        user_id = user.id
        user_email = user.email
        create_valid_shift(db, user_id)
        
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_id_hash = hash_device_id("my_device_xyz")
        now = datetime.utcnow()
        session = UserSession(
            employee_id=user_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_id_hash,
            issued_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(hours=1),
            is_active=True
        )
        db.add(session)
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "audit"
    get_settings.cache_clear()

    token = create_access_token(
        data={
            "sub": user_email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti
        }
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        violations = [a for a in audits if "SESSION_DEVICE_MISMATCH" in (a.after_state or "")]
        assert len(violations) >= 1
        assert_no_sensitive_values_in_audits(db, user_id, [sid, jti, token])
    finally:
        db.close()

