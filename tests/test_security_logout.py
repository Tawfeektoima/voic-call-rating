import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from jose import jwt

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, UserSession, TrustedDevice, AuditEvent, EmployeeStatus, EmployeeShift
from app.security import get_password_hash, SECRET_KEY, ALGORITHM, create_access_token
from app.config import get_settings

client = TestClient(app)

def cleanup_test_db():
    db: Session = SessionLocal()
    try:
        emp_ids = [e.id for e in db.query(Employee).filter(Employee.email.like("test_logout_%")).all()]
        if emp_ids:
            db.query(UserSession).filter(UserSession.employee_id.in_(emp_ids)).delete(synchronize_session=False)
            db.query(TrustedDevice).filter(TrustedDevice.employee_id.in_(emp_ids)).delete(synchronize_session=False)
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


def create_test_user(db: Session, email="test_logout_user@example.com", code="TEST_LOGOUT_USER") -> Employee:
    password = "TestPassword123!"
    user = Employee(
        name="Logout Employee",
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


def test_logout_revokes_current_session():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
    finally:
        db.close()

    # Login
    response = client.post(
        "/api/auth/login",
        json={"email": "test_logout_user@example.com", "password": "TestPassword123!"}
    )
    assert response.status_code == 200
    data = response.json()
    token = data["access_token"]
    session_id = data["session"]["session_id"]

    # Assert session is active in DB
    db = SessionLocal()
    try:
        sess = db.query(UserSession).filter(UserSession.id == session_id).first()
        assert sess is not None
        assert sess.is_active is True
        assert sess.revoked_at is None
    finally:
        db.close()

    # Logout
    logout_response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert logout_response.status_code == 200
    assert logout_response.json() == {"message": "Logged out successfully"}

    # Assert session is revoked in DB
    db = SessionLocal()
    try:
        sess = db.query(UserSession).filter(UserSession.id == session_id).first()
        assert sess.is_active is False
        assert sess.revoked_at is not None
        assert sess.revoke_reason == "logout"
    finally:
        db.close()


def test_logout_idempotency():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
    finally:
        db.close()

    # Login
    response = client.post(
        "/api/auth/login",
        json={"email": "test_logout_user@example.com", "password": "TestPassword123!"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    # Logout 1
    logout1 = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert logout1.status_code == 200

    # Logout 2
    logout2 = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert logout2.status_code == 200
    assert logout2.json() == {"message": "Logged out successfully"}


def test_logout_legacy_token_without_sid():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
    finally:
        db.close()

    # Create a legacy token without sid or jti
    legacy_token = create_access_token(
        data={"sub": user.email, "user_id": user_id, "role": "AGENT"}
    )

    # Logout
    logout_response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {legacy_token}"}
    )
    assert logout_response.status_code == 200
    assert logout_response.json() == {"message": "Logged out successfully"}


def test_logout_with_missing_session_row():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
    finally:
        db.close()

    # Create token with a dummy sid that doesn't exist in DB
    dummy_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user_id,
            "role": "AGENT",
            "sid": "does_not_exist_sid_123",
            "jti": "does_not_exist_jti_123"
        }
    )

    # Logout
    logout_response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {dummy_token}"}
    )
    assert logout_response.status_code == 200
    assert logout_response.json() == {"message": "Logged out successfully"}


def test_logout_no_cross_session_impact():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id

        # Create first session
        sess1 = UserSession(
            employee_id=user_id,
            sid="sid_one_12345",
            jti="jti_one_12345",
            device_id_hash="hash_one",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_active=True
        )
        db.add(sess1)

        # Create second session
        sess2 = UserSession(
            employee_id=user_id,
            sid="sid_two_12345",
            jti="jti_two_12345",
            device_id_hash="hash_two",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_active=True
        )
        db.add(sess2)
        db.commit()
        
        sess1_id = sess1.id
        sess2_id = sess2.id
    finally:
        db.close()

    # Generate token for session 1
    token1 = create_access_token(
        data={
            "sub": "test_logout_user@example.com",
            "user_id": user_id,
            "role": "AGENT",
            "sid": "sid_one_12345",
            "jti": "jti_one_12345"
        }
    )

    # Logout session 1
    response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token1}"}
    )
    assert response.status_code == 200

    # Assert session 1 is revoked, session 2 is still active
    db = SessionLocal()
    try:
        s1 = db.query(UserSession).filter(UserSession.id == sess1_id).first()
        s2 = db.query(UserSession).filter(UserSession.id == sess2_id).first()
        assert s1.is_active is False
        assert s2.is_active is True
    finally:
        db.close()


def test_logout_no_sensitive_leak_in_audit_logs():
    db = SessionLocal()
    try:
        user = create_test_user(db)
        user_id = user.id
    finally:
        db.close()

    # Login
    response = client.post(
        "/api/auth/login",
        json={"email": "test_logout_user@example.com", "password": "TestPassword123!"}
    )
    assert response.status_code == 200
    data = response.json()
    token = data["access_token"]
    session_meta = data["session"]
    
    # Extract sid and jti from token to check they are not leaked
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    sid = payload["sid"]
    jti = payload["jti"]

    # Logout
    logout_response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert logout_response.status_code == 200

    # Query audit logs for the user
    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        assert len(audits) > 0
        
        for audit in audits:
            for field in [audit.target, audit.before_state, audit.after_state, audit.reason]:
                if field:
                    # Assert no raw sid, jti, token is written
                    assert sid not in field
                    assert jti not in field
                    assert token not in field
    finally:
        db.close()


def create_valid_shift(db: Session, employee_id: int):
    from app.services.security_policy import get_security_timezone
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


@pytest.mark.parametrize("policy_mode", ["off", "audit", "enforce"])
def test_logout_works_in_all_modes(policy_mode):
    db = SessionLocal()
    try:
        user = create_test_user(db, email=f"test_logout_{policy_mode}@example.com", code=f"TEST_LOGOUT_{policy_mode.upper()}")
        user_id = user.id
        create_valid_shift(db, user_id)
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = policy_mode
    get_settings.cache_clear()

    # Login
    response = client.post(
        "/api/auth/login",
        json={
            "email": f"test_logout_{policy_mode}@example.com",
            "password": "TestPassword123!",
            "device_id": "logout_mode_device_123"
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    # Logout
    logout_response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert logout_response.status_code == 200
    assert logout_response.json() == {"message": "Logged out successfully"}
