import os
import pytest
import secrets
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta, date, time

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, UserSession, TrustedDevice, AuditEvent, EmployeeStatus, EmployeeShift
from app.security import get_password_hash, create_access_token
from app.config import get_settings
from app.services.security_policy import hash_device_id

client = TestClient(app)

def cleanup_test_db():
    db: Session = SessionLocal()
    try:
        emp_ids = [e.id for e in db.query(Employee).filter(Employee.email.like("test_admin_session_%")).all()]
        if emp_ids:
            db.query(EmployeeShift).filter(EmployeeShift.employee_id.in_(emp_ids)).delete(synchronize_session=False)
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


def create_user(db: Session, email: str, role: UserRole, status=EmployeeStatus.ACTIVE.value) -> Employee:
    password = "TestPassword123!"
    employee_code = f"CODE_{secrets.token_hex(4)}"
    user = Employee(
        name="Test Session Employee",
        email=email,
        hashed_password=get_password_hash(password),
        role=role,
        employee_code=employee_code,
        status=status
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_test_shift(db: Session, employee_id: int):
    now_local = datetime.now()
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


def create_valid_session_and_token(db: Session, user: Employee, device_id="my_device_xyz") -> tuple[str, UserSession]:
    # Create shift
    create_test_shift(db, user.id)
    
    # Create session
    sid = secrets.token_hex(32)
    jti = secrets.token_hex(32)
    device_id_hash = hash_device_id(device_id)
    now = datetime.utcnow()
    session = UserSession(
        employee_id=user.id,
        sid=sid,
        jti=jti,
        device_id_hash=device_id_hash,
        issued_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(hours=1),
        is_active=True
    )
    db.add(session)
    
    # Enroll device
    dev = TrustedDevice(
        employee_id=user.id,
        device_id_hash=device_id_hash,
        device_label="My Device",
        is_trusted=True,
        first_seen_at=now,
        last_seen_at=now,
        approved_at=now
    )
    db.add(dev)
    db.commit()
    db.refresh(session)
    
    token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "sid": sid,
            "jti": jti,
            "device_id_hash": device_id_hash
        }
    )
    return token, session


def test_admin_list_sessions():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_admin_session_admin@example.com", UserRole.ADMIN)
        agent1 = create_user(db, "test_admin_session_agent1@example.com", UserRole.AGENT)
        agent2 = create_user(db, "test_admin_session_agent2@example.com", UserRole.AGENT)
        
        # Create session 1 (active)
        token1, sess1 = create_valid_session_and_token(db, agent1, "dev1")

        # Create session 2 (revoked/inactive/expired)
        now = datetime.utcnow()
        sess2 = UserSession(
            employee_id=agent2.id,
            sid=secrets.token_hex(32),
            jti=secrets.token_hex(32),
            device_id_hash=hash_device_id("dev2"),
            issued_at=now - timedelta(hours=5),
            last_seen_at=now - timedelta(hours=5),
            expires_at=now - timedelta(hours=4), # Expired
            is_active=False,
            revoked_at=now - timedelta(hours=5),
            revoke_reason="logout"
        )
        db.add(sess2)
        db.commit()
        
        admin_id = admin.id
        agent1_id = agent1.id
        agent2_id = agent2.id
        
        # Create valid session for admin to request
        admin_token, _ = create_valid_session_and_token(db, admin, "admin_dev")
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Admin can list all sessions
    response = client.get("/api/security-admin/sessions", headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert len(res_data) >= 2

    # Check that sid and jti are NOT exposed
    for s in res_data:
        assert "sid" not in s
        assert "jti" not in s
        assert "device_id_hash" not in s

    # 2. Admin can filter by employee_id
    response_filter_emp = client.get(f"/api/security-admin/sessions?employee_id={agent1_id}", headers=headers)
    assert response_filter_emp.status_code == 200
    res_emp = response_filter_emp.json()
    assert len(res_emp) == 1
    assert res_emp[0]["employee_id"] == agent1_id

    # 3. Admin can filter active sessions only
    response_filter_active = client.get("/api/security-admin/sessions?active_only=true", headers=headers)
    assert response_filter_active.status_code == 200
    res_active = response_filter_active.json()
    # Should only contain session 1 (active) for agent1 or admin, not session 2 (inactive/expired) for agent2
    assert any(s["employee_id"] == agent1_id for s in res_active)
    assert not any(s["employee_id"] == agent2_id for s in res_active)


def test_non_admin_forbidden():
    db = SessionLocal()
    try:
        agent = create_user(db, "test_admin_session_agent3@example.com", UserRole.AGENT)
        agent_token, _ = create_valid_session_and_token(db, agent, "agent3_dev")
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {agent_token}"}

    # Should return 403
    response = client.get("/api/security-admin/sessions", headers=headers)
    assert response.status_code == 403


def test_admin_revoke_session():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_admin_session_admin4@example.com", UserRole.ADMIN)
        agent = create_user(db, "test_admin_session_agent4@example.com", UserRole.AGENT)
        
        # Create active sessions
        agent_token, session = create_valid_session_and_token(db, agent, "my_device_xyz")
        admin_token, _ = create_valid_session_and_token(db, admin, "admin_dev")

        admin_id = admin.id
        agent_id = agent.id
        session_id = session.id
        sid = session.sid
        jti = session.jti
    finally:
        db.close()

    # Enforce mode on
    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    # Verify protected route works initially
    response_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {agent_token}"})
    assert response_me.status_code == 200

    # Revoke session via admin API
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    revoke_payload = {"reason": "Forced logout"}

    response_revoke = client.post(
        f"/api/security-admin/sessions/{session_id}/revoke",
        json=revoke_payload,
        headers=admin_headers
    )
    assert response_revoke.status_code == 200
    assert response_revoke.json() == {"message": "Session revoked successfully"}

    # Verify session is now inactive in DB
    db = SessionLocal()
    try:
        sess = db.query(UserSession).filter(UserSession.id == session_id).first()
        assert sess.is_active is False
        assert sess.revoked_at is not None
        assert sess.revoke_reason == "Forced logout"
        first_revoked_at = sess.revoked_at

        # Verify audit log was recorded correctly and safely
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == admin_id, AuditEvent.action == "SESSION_REVOKED").all()
        assert len(audits) == 1
        assert "Forced logout" in audits[0].reason
        # Ensure no raw tokens/secrets leak in audits
        for s_val in [sid, jti, agent_token]:
            assert s_val not in (audits[0].after_state or "")
            assert s_val not in (audits[0].reason or "")
    finally:
        db.close()

    # Verify calling /me now fails with 401 SESSION_REVOKED
    response_me_after = client.get("/api/auth/me", headers={"Authorization": f"Bearer {agent_token}"})
    assert response_me_after.status_code == 401
    assert response_me_after.json()["detail"]["code"] == "SESSION_REVOKED"

    # Verify idempotency: calling revoke again returns success
    response_revoke_again = client.post(
        f"/api/security-admin/sessions/{session_id}/revoke",
        json=revoke_payload,
        headers=admin_headers
    )
    assert response_revoke_again.status_code == 200

    db = SessionLocal()
    try:
        sess = db.query(UserSession).filter(UserSession.id == session_id).first()
        assert sess.revoked_at == first_revoked_at

        audits = (
            db.query(AuditEvent)
            .filter(AuditEvent.actor_id == admin_id, AuditEvent.action == "SESSION_REVOKED")
            .order_by(AuditEvent.id.asc())
            .all()
        )
        assert len(audits) == 2
        assert '"already_revoked": true' in (audits[1].after_state or "")
        assert "Forced logout" in (audits[1].reason or "")
        for s_val in [sid, jti, agent_token]:
            assert s_val not in (audits[1].after_state or "")
            assert s_val not in (audits[1].reason or "")
    finally:
        db.close()


def test_revoke_missing_session():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_admin_session_admin5@example.com", UserRole.ADMIN)
        admin_token, _ = create_valid_session_and_token(db, admin, "admin_dev")
    finally:
        db.close()

    # Enforce mode on
    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    revoke_payload = {"reason": "Forced logout"}

    response = client.post(
        "/api/security-admin/sessions/999999/revoke",
        json=revoke_payload,
        headers=admin_headers
    )
    assert response.status_code == 404
