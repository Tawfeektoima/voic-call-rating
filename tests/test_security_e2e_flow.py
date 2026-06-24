import os
import pytest
import secrets
from fastapi.testclient import TestClient
from fastapi import WebSocketDisconnect
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta, date, time
from zoneinfo import ZoneInfo

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, EmployeeShift, UserSession, TrustedDevice, AuditEvent, EmployeeStatus, LoginOtpChallenge
from app.security import get_password_hash, create_access_token
from app.config import get_settings
from app.services.security_policy import hash_device_id, get_security_timezone

client = TestClient(app)

# Track sensitive items generated during the test run to assert they never enter database audit trails.
GLOBAL_BLACKLIST = set()

def cleanup_test_db():
    db: Session = SessionLocal()
    try:
        emp_ids = [e.id for e in db.query(Employee).filter(Employee.email.like("test_e2e_%")).all()]
        if emp_ids:
            db.query(EmployeeShift).filter(EmployeeShift.employee_id.in_(emp_ids)).delete(synchronize_session=False)
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


def create_user(db: Session, email: str, role: UserRole, status=EmployeeStatus.ACTIVE.value) -> Employee:
    password = "TestE2EPassword123!"
    employee_code = f"CODE_{secrets.token_hex(4)}"
    
    # Track password in blacklist
    GLOBAL_BLACKLIST.add(password)
    GLOBAL_BLACKLIST.add(employee_code)
    
    user = Employee(
        name="Test E2E Employee",
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
    db.refresh(shift)
    return shift


def create_session_and_token_for_user(db: Session, user: Employee, device_id: str) -> str:
    # 1. Schedule a shift
    create_valid_shift(db, user.id)
    
    # 2. Add trusted device
    device_id_hash = hash_device_id(device_id)
    dev = TrustedDevice(
        employee_id=user.id,
        device_id_hash=device_id_hash,
        device_label="E2E Device",
        is_trusted=True,
        first_seen_at=datetime.utcnow(),
        approved_at=datetime.utcnow()
    )
    db.add(dev)
    db.flush()
    
    # 3. Add active session
    sid = secrets.token_hex(32)
    jti = secrets.token_hex(32)
    session = UserSession(
        employee_id=user.id,
        trusted_device_id=dev.id,
        sid=sid,
        jti=jti,
        device_id_hash=device_id_hash,
        issued_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=1),
        is_active=True
    )
    db.add(session)
    db.commit()
    
    # 4. Generate token with claims
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
    
    GLOBAL_BLACKLIST.add(sid)
    GLOBAL_BLACKLIST.add(jti)
    GLOBAL_BLACKLIST.add(token)
    GLOBAL_BLACKLIST.add(device_id)
    GLOBAL_BLACKLIST.add(device_id_hash)
    
    return token


def assert_audit_sanitization(db: Session):
    """Scans all AuditEvent rows for any leaks of blacklisted sensitive strings."""
    audits = db.query(AuditEvent).all()
    for audit in audits:
        for val in GLOBAL_BLACKLIST:
            if not val or len(val) < 4:
                continue
            assert val not in (audit.action or ""), f"Leaked blacklist key '{val}' in AuditEvent action: {audit.action}"
            assert val not in (audit.target or ""), f"Leaked blacklist key '{val}' in AuditEvent target: {audit.target}"
            assert val not in (audit.before_state or ""), f"Leaked blacklist key '{val}' in AuditEvent before_state: {audit.before_state}"
            assert val not in (audit.after_state or ""), f"Leaked blacklist key '{val}' in AuditEvent after_state: {audit.after_state}"
            assert val not in (audit.reason or ""), f"Leaked blacklist key '{val}' in AuditEvent reason: {audit.reason}"


def test_e2e_happy_path_protect_flow():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_e2e_happy_admin@example.com", UserRole.ADMIN)
        agent = create_user(db, "test_e2e_happy_agent@example.com", UserRole.AGENT)
        admin_id = admin.id
        agent_id = agent.id
        admin_email = admin.email
        agent_email = agent.email
    finally:
        db.close()

    # Step 1: Set mode to enforce
    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    os.environ["SECURITY_WS_REVALIDATION_INTERVAL_SECONDS"] = "0"
    get_settings.cache_clear()

    # Create admin active session so they can authenticate
    db = SessionLocal()
    try:
        admin_row = db.query(Employee).filter(Employee.id == admin_id).first()
        admin_token = create_session_and_token_for_user(db, admin_row, "admin_device_happy")
    finally:
        db.close()

    # Step 2: Admin schedules a shift for the agent
    today_str = datetime.now(get_security_timezone()).date().isoformat()
    payload = {
        "employee_id": agent_id,
        "work_date": today_str,
        "shift_start": "00:00",
        "shift_end": "23:59",
        "grace_before_minutes": 10,
        "grace_after_minutes": 10,
        "status": "scheduled"
    }
    response = client.post("/api/security-admin/shifts", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 201

    # Step 3: Agent logs in with device_id.
    # First device is auto-enrolled and auto-approved during active shift
    device_id = "agent_stable_device_e2e"
    GLOBAL_BLACKLIST.add(device_id)
    GLOBAL_BLACKLIST.add(hash_device_id(device_id))

    login_resp = client.post(
        "/api/auth/login",
        json={"email": agent_email, "password": "TestE2EPassword123!", "device_id": device_id}
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    agent_token = login_data["access_token"]
    GLOBAL_BLACKLIST.add(agent_token)

    # Step 4: Inspect database and assert session properties
    db = SessionLocal()
    try:
        session = db.query(UserSession).filter(UserSession.employee_id == agent_id, UserSession.is_active == True).first()
        assert session is not None
        assert session.sid is not None
        assert session.jti is not None
        assert session.device_id_hash == hash_device_id(device_id)
        
        GLOBAL_BLACKLIST.add(session.sid)
        GLOBAL_BLACKLIST.add(session.jti)
        session_id = session.id
    finally:
        db.close()

    # Step 5: Protected HTTP route works
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {agent_token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == agent_email

    # Step 6: WebSocket connection works
    with client.websocket_connect(f"/ws/calls/123?auth_token={agent_token}") as ws:
        pass

    # Step 7: Logout revokes session
    logout_resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {agent_token}"})
    assert logout_resp.status_code == 200

    # Step 8: Check DB session is revoked
    db = SessionLocal()
    try:
        revoked_session = db.query(UserSession).filter(UserSession.id == session_id).first()
        assert revoked_session.is_active is False
        assert revoked_session.revoked_at is not None
        assert revoked_session.revoke_reason == "logout"
    finally:
        db.close()

    # Step 9: Protected HTTP route fails after logout
    me_after_logout = client.get("/api/auth/me", headers={"Authorization": f"Bearer {agent_token}"})
    assert me_after_logout.status_code == 401

    # Audit sanitization verify
    db = SessionLocal()
    try:
        assert_audit_sanitization(db)
    finally:
        db.close()


def test_e2e_active_session_denial_and_admin_revoke():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_e2e_session_admin@example.com", UserRole.ADMIN)
        agent = create_user(db, "test_e2e_session_agent@example.com", UserRole.AGENT)
        admin_id = admin.id
        agent_id = agent.id
        admin_email = admin.email
        agent_email = agent.email
        create_valid_shift(db, agent_id)
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    db = SessionLocal()
    try:
        admin_row = db.query(Employee).filter(Employee.id == admin_id).first()
        admin_token = create_session_and_token_for_user(db, admin_row, "admin_device_sess")
    finally:
        db.close()

    # First login from Device A
    device_a = "device_a_login"
    GLOBAL_BLACKLIST.add(device_a)
    GLOBAL_BLACKLIST.add(hash_device_id(device_a))

    login_a_resp = client.post(
        "/api/auth/login",
        json={"email": agent_email, "password": "TestE2EPassword123!", "device_id": device_a}
    )
    assert login_a_resp.status_code == 200
    token_a = login_a_resp.json()["access_token"]
    GLOBAL_BLACKLIST.add(token_a)

    # Enroll Device B via DB so device_id policy doesn't block Device B immediately (which would be DEVICE_NOT_TRUSTED)
    db = SessionLocal()
    try:
        device_b = "device_b_login"
        GLOBAL_BLACKLIST.add(device_b)
        GLOBAL_BLACKLIST.add(hash_device_id(device_b))
        
        dev_b = TrustedDevice(
            employee_id=agent_id,
            device_id_hash=hash_device_id(device_b),
            device_label="Device B",
            is_trusted=True,
            first_seen_at=datetime.utcnow(),
            approved_at=datetime.utcnow()
        )
        db.add(dev_b)
        db.commit()
        
        active_sess = db.query(UserSession).filter(UserSession.employee_id == agent_id, UserSession.is_active == True).first()
        GLOBAL_BLACKLIST.add(active_sess.sid)
        GLOBAL_BLACKLIST.add(active_sess.jti)
        session_id = active_sess.id
    finally:
        db.close()

    # Second login from Device B must fail with 409 ACTIVE_SESSION_EXISTS
    login_b_resp = client.post(
        "/api/auth/login",
        json={"email": agent_email, "password": "TestE2EPassword123!", "device_id": device_b}
    )
    assert login_b_resp.status_code == 409
    assert login_b_resp.json()["detail"]["code"] == "ACTIVE_SESSION_EXISTS"

    # Admin revokes first session
    revoke_payload = {"reason": "Revoking session for E2E tests"}
    
    revoke_resp = client.post(
        f"/api/security-admin/sessions/{session_id}/revoke",
        json=revoke_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert revoke_resp.status_code == 200

    # Second login from Device B should now succeed
    login_b_retry = client.post(
        "/api/auth/login",
        json={"email": agent_email, "password": "TestE2EPassword123!", "device_id": device_b}
    )
    assert login_b_retry.status_code == 200
    assert "access_token" in login_b_retry.json()

    db = SessionLocal()
    try:
        # Assert SESSION_REVOKED is logged in audit trail
        audit = db.query(AuditEvent).filter(
            AuditEvent.action == "SESSION_REVOKED",
            AuditEvent.actor_id == admin_id
        ).first()
        assert audit is not None
        assert audit.reason == "Revoking session for E2E tests"
        
        # Verify sanitization
        assert_audit_sanitization(db)
    finally:
        db.close()


def test_e2e_trusted_device_denial_and_approve():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_e2e_dev_admin@example.com", UserRole.ADMIN)
        agent = create_user(db, "test_e2e_dev_agent@example.com", UserRole.AGENT)
        admin_id = admin.id
        agent_id = agent.id
        admin_email = admin.email
        agent_email = agent.email
        create_valid_shift(db, agent_id)
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    os.environ["SECURITY_WS_REVALIDATION_INTERVAL_SECONDS"] = "0"
    get_settings.cache_clear()

    db = SessionLocal()
    try:
        admin_row = db.query(Employee).filter(Employee.id == admin_id).first()
        admin_token = create_session_and_token_for_user(db, admin_row, "admin_device_dev")
    finally:
        db.close()

    # Login and auto-enroll device
    device_id = "e2e_trusted_device_lifecycle"
    GLOBAL_BLACKLIST.add(device_id)
    GLOBAL_BLACKLIST.add(hash_device_id(device_id))

    login_resp = client.post(
        "/api/auth/login",
        json={"email": agent_email, "password": "TestE2EPassword123!", "device_id": device_id}
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    GLOBAL_BLACKLIST.add(token)

    db = SessionLocal()
    try:
        dev_row = db.query(TrustedDevice).filter(TrustedDevice.employee_id == agent_id).first()
        device_row_id = dev_row.id
        
        sess_row = db.query(UserSession).filter(UserSession.employee_id == agent_id, UserSession.is_active == True).first()
        GLOBAL_BLACKLIST.add(sess_row.sid)
        GLOBAL_BLACKLIST.add(sess_row.jti)
    finally:
        db.close()

    # Verify protected route works initially
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200

    # Admin revokes the device
    revoke_payload = {"reason": "Revoking device A"}
    
    revoke_dev_resp = client.post(
        f"/api/security-admin/devices/{device_row_id}/revoke",
        json=revoke_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert revoke_dev_resp.status_code == 200

    # Protected HTTP route must fail with 403 DEVICE_NOT_TRUSTED
    me_after_revoke = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_after_revoke.status_code == 403
    assert me_after_revoke.json()["detail"]["code"] == "DEVICE_NOT_TRUSTED"

    # WebSocket connection must fail
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/calls/123?auth_token={token}"):
            pass
    assert exc.value.code == 4403

    # New login from same device fails with 403 DEVICE_NOT_TRUSTED
    login_fail = client.post(
        "/api/auth/login",
        json={"email": agent_email, "password": "TestE2EPassword123!", "device_id": device_id}
    )
    assert login_fail.status_code == 403
    assert login_fail.json()["detail"]["code"] == "DEVICE_NOT_TRUSTED"

    # Logout to clear the active session before retry login
    logout_resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 200

    # Admin approves device again
    approve_payload = {"reason": "Approving device A"}
    
    approve_dev_resp = client.post(
        f"/api/security-admin/devices/{device_row_id}/approve",
        json=approve_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert approve_dev_resp.status_code == 200

    # Login works again
    login_success = client.post(
        "/api/auth/login",
        json={"email": agent_email, "password": "TestE2EPassword123!", "device_id": device_id}
    )
    assert login_success.status_code == 200
    assert "access_token" in login_success.json()

    db = SessionLocal()
    try:
        assert_audit_sanitization(db)
    finally:
        db.close()


def test_e2e_shift_enforcement_and_lifecycle():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_e2e_shift_admin@example.com", UserRole.ADMIN)
        agent = create_user(db, "test_e2e_shift_agent@example.com", UserRole.AGENT)
        admin_id = admin.id
        agent_id = agent.id
        admin_email = admin.email
        agent_email = agent.email
        
        # Schedule active shift
        shift = create_valid_shift(db, agent_id)
        shift_id = shift.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    os.environ["SECURITY_WS_REVALIDATION_INTERVAL_SECONDS"] = "0"
    get_settings.cache_clear()

    db = SessionLocal()
    try:
        admin_row = db.query(Employee).filter(Employee.id == admin_id).first()
        admin_token = create_session_and_token_for_user(db, admin_row, "admin_device_shift")
    finally:
        db.close()

    # Login agent
    device_id = "agent_shift_device"
    GLOBAL_BLACKLIST.add(device_id)
    GLOBAL_BLACKLIST.add(hash_device_id(device_id))

    login_resp = client.post(
        "/api/auth/login",
        json={"email": agent_email, "password": "TestE2EPassword123!", "device_id": device_id}
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    GLOBAL_BLACKLIST.add(token)

    db = SessionLocal()
    try:
        sess = db.query(UserSession).filter(UserSession.employee_id == agent_id, UserSession.is_active == True).first()
        GLOBAL_BLACKLIST.add(sess.sid)
        GLOBAL_BLACKLIST.add(sess.jti)
    finally:
        db.close()

    # HTTP works
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200

    # Admin cancels/disables shift
    # Shift cancellation requires reason
    cancel_payload = {"reason": "Cancelling shift for test"}
    
    cancel_resp = client.post(
        f"/api/security-admin/shifts/{shift_id}/cancel",
        json=cancel_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert cancel_resp.status_code == 200

    # Protected HTTP route must fail with 403 SHIFT_NOT_ALLOWED
    me_fail = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_fail.status_code == 403
    assert me_fail.json()["detail"]["code"] == "SHIFT_NOT_ALLOWED"

    # WebSocket connection fails
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/calls/123?auth_token={token}"):
            pass
    assert exc.value.code == 4403

    # New login fails
    login_fail = client.post(
        "/api/auth/login",
        json={"email": agent_email, "password": "TestE2EPassword123!", "device_id": device_id}
    )
    assert login_fail.status_code == 403
    assert login_fail.json()["detail"]["code"] == "SHIFT_NOT_ALLOWED"

    # Logout to clear the active session before retry login
    logout_resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 200

    # Admin updates shift to valid active shift again
    today_str = datetime.now(get_security_timezone()).date().isoformat()
    update_payload = {
        "work_date": today_str,
        "shift_start": "00:00:00",
        "shift_end": "23:59:59",
        "status": "scheduled",
        "reason": "Rescheduling shift"
    }
    
    update_resp = client.patch(
        f"/api/security-admin/shifts/{shift_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_resp.status_code == 200

    # Login works again
    login_success = client.post(
        "/api/auth/login",
        json={"email": agent_email, "password": "TestE2EPassword123!", "device_id": device_id}
    )
    assert login_success.status_code == 200

    db = SessionLocal()
    try:
        assert_audit_sanitization(db)
    finally:
        db.close()


def test_e2e_websocket_mid_connection_session_revoke():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_e2e_ws_mid_sess_admin@example.com", UserRole.ADMIN)
        agent = create_user(db, "test_e2e_ws_mid_sess_agent@example.com", UserRole.AGENT)
        admin_id = admin.id
        agent_id = agent.id
        admin_email = admin.email
        agent_email = agent.email
        
        # Schedule active shift
        shift = create_valid_shift(db, agent_id)
        shift_id = shift.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    os.environ["SECURITY_WS_REVALIDATION_INTERVAL_SECONDS"] = "0"
    get_settings.cache_clear()

    db = SessionLocal()
    try:
        admin_row = db.query(Employee).filter(Employee.id == admin_id).first()
        admin_token = create_session_and_token_for_user(db, admin_row, "admin_device_ws_mid_sess")
    finally:
        db.close()

    # Login agent
    device_id = "agent_ws_mid_sess_device"
    GLOBAL_BLACKLIST.add(device_id)
    GLOBAL_BLACKLIST.add(hash_device_id(device_id))

    login_resp = client.post(
        "/api/auth/login",
        json={"email": agent_email, "password": "TestE2EPassword123!", "device_id": device_id}
    )
    assert login_resp.status_code == 200
    agent_token = login_resp.json()["access_token"]
    GLOBAL_BLACKLIST.add(agent_token)

    db = SessionLocal()
    try:
        sess = db.query(UserSession).filter(UserSession.employee_id == agent_id, UserSession.is_active == True).first()
        session_id = sess.id
        GLOBAL_BLACKLIST.add(sess.sid)
        GLOBAL_BLACKLIST.add(sess.jti)
    finally:
        db.close()

    # Connect WebSocket
    with client.websocket_connect(f"/ws/calls/123?auth_token={agent_token}") as ws:
        # Admin revokes the session
        revoke_payload = {"reason": "Revoking session mid-connection E2E"}
        revoke_resp = client.post(
            f"/api/security-admin/sessions/{session_id}/revoke",
            json=revoke_payload,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert revoke_resp.status_code == 200

        # Trigger revalidation
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
        assert exc.value.code == 4401

    db = SessionLocal()
    try:
        assert_audit_sanitization(db)
    finally:
        db.close()


def test_e2e_websocket_mid_connection_device_revoke():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_e2e_ws_mid_dev_admin@example.com", UserRole.ADMIN)
        agent = create_user(db, "test_e2e_ws_mid_dev_agent@example.com", UserRole.AGENT)
        admin_id = admin.id
        agent_id = agent.id
        admin_email = admin.email
        agent_email = agent.email
        
        # Schedule active shift
        shift = create_valid_shift(db, agent_id)
        shift_id = shift.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    os.environ["SECURITY_WS_REVALIDATION_INTERVAL_SECONDS"] = "0"
    get_settings.cache_clear()

    db = SessionLocal()
    try:
        admin_row = db.query(Employee).filter(Employee.id == admin_id).first()
        admin_token = create_session_and_token_for_user(db, admin_row, "admin_device_ws_mid_dev")
    finally:
        db.close()

    # Login agent
    device_id = "agent_ws_mid_dev_device"
    GLOBAL_BLACKLIST.add(device_id)
    GLOBAL_BLACKLIST.add(hash_device_id(device_id))

    login_resp = client.post(
        "/api/auth/login",
        json={"email": agent_email, "password": "TestE2EPassword123!", "device_id": device_id}
    )
    assert login_resp.status_code == 200
    agent_token = login_resp.json()["access_token"]
    GLOBAL_BLACKLIST.add(agent_token)

    db = SessionLocal()
    try:
        dev = db.query(TrustedDevice).filter(TrustedDevice.employee_id == agent_id).first()
        device_row_id = dev.id
    finally:
        db.close()

    # Connect WebSocket
    with client.websocket_connect(f"/ws/calls/123?auth_token={agent_token}") as ws:
        # Admin revokes the device
        revoke_payload = {"reason": "Revoking device mid-connection E2E"}
        revoke_resp = client.post(
            f"/api/security-admin/devices/{device_row_id}/revoke",
            json=revoke_payload,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert revoke_resp.status_code == 200

        # Trigger revalidation
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
        assert exc.value.code == 4403

    db = SessionLocal()
    try:
        assert_audit_sanitization(db)
    finally:
        db.close()


def test_e2e_websocket_mid_connection_shift_cancel():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_e2e_ws_mid_shift_admin@example.com", UserRole.ADMIN)
        agent = create_user(db, "test_e2e_ws_mid_shift_agent@example.com", UserRole.AGENT)
        admin_id = admin.id
        agent_id = agent.id
        admin_email = admin.email
        agent_email = agent.email
        
        # Schedule active shift
        shift = create_valid_shift(db, agent_id)
        shift_id = shift.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    os.environ["SECURITY_WS_REVALIDATION_INTERVAL_SECONDS"] = "0"
    get_settings.cache_clear()

    db = SessionLocal()
    try:
        admin_row = db.query(Employee).filter(Employee.id == admin_id).first()
        admin_token = create_session_and_token_for_user(db, admin_row, "admin_device_ws_mid_shift")
    finally:
        db.close()

    # Login agent
    device_id = "agent_ws_mid_shift_device"
    GLOBAL_BLACKLIST.add(device_id)
    GLOBAL_BLACKLIST.add(hash_device_id(device_id))

    login_resp = client.post(
        "/api/auth/login",
        json={"email": agent_email, "password": "TestE2EPassword123!", "device_id": device_id}
    )
    assert login_resp.status_code == 200
    agent_token = login_resp.json()["access_token"]
    GLOBAL_BLACKLIST.add(agent_token)

    # Connect WebSocket
    with client.websocket_connect(f"/ws/calls/123?auth_token={agent_token}") as ws:
        # Admin cancels the shift
        cancel_payload = {"reason": "Cancelling shift mid-connection E2E"}
        cancel_resp = client.post(
            f"/api/security-admin/shifts/{shift_id}/cancel",
            json=cancel_payload,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert cancel_resp.status_code == 200

        # Trigger revalidation
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
        assert exc.value.code == 4403

    db = SessionLocal()
    try:
        assert_audit_sanitization(db)
    finally:
        db.close()


def test_e2e_audit_logs_sanitization_scanner():
    """Final regression scanner scanning all AuditEvent table rows in the database."""
    db = SessionLocal()
    try:
        assert_audit_sanitization(db)
    finally:
        db.close()
