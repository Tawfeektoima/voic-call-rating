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
        emp_ids = [e.id for e in db.query(Employee).filter(Employee.email.like("test_admin_device_%")).all()]
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
        name="Test Device Employee",
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


def create_valid_session_and_token(db: Session, user: Employee, device_id="my_device_xyz") -> tuple[str, UserSession, TrustedDevice]:
    # Create shift
    create_test_shift(db, user.id)
    
    # Enroll device
    device_id_hash = hash_device_id(device_id)
    now = datetime.utcnow()
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
    db.flush()

    # Create session
    sid = secrets.token_hex(32)
    jti = secrets.token_hex(32)
    session = UserSession(
        employee_id=user.id,
        trusted_device_id=dev.id,
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
    db.refresh(session)
    db.refresh(dev)
    
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
    return token, session, dev


def test_admin_manage_devices():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_admin_device_admin@example.com", UserRole.ADMIN)
        agent1 = create_user(db, "test_admin_device_agent1@example.com", UserRole.AGENT)
        agent2 = create_user(db, "test_admin_device_agent2@example.com", UserRole.AGENT)

        admin_token, _, _ = create_valid_session_and_token(db, admin, "admin_dev")
        _, _, dev1 = create_valid_session_and_token(db, agent1, "agent1_dev")
        _, _, dev2 = create_valid_session_and_token(db, agent2, "agent2_dev")

        # Let's set dev2 to untrusted/revoked
        dev2.is_trusted = False
        dev2.revoked_at = datetime.utcnow()
        dev2.revoke_reason = "lost"
        db.commit()

        admin_id = admin.id
        agent1_id = agent1.id
        agent2_id = agent2.id
        dev1_id = dev1.id
        dev2_id = dev2.id
        dev1_hash = dev1.device_id_hash
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Admin can list devices
    response = client.get("/api/security-admin/devices", headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert len(res_data) >= 3

    # Check that raw device_id and raw token values are NOT exposed
    # And check device_fingerprint is exposed and matches first 8 chars of hash
    for d in res_data:
        assert "device_id" not in d
        assert "sid" not in d
        assert "jti" not in d
        if d["id"] == dev1_id:
            assert d["device_fingerprint"] == dev1_hash[:8]

    # 2. Admin can filter by employee_id
    response_filter = client.get(f"/api/security-admin/devices?employee_id={agent1_id}", headers=headers)
    assert response_filter.status_code == 200
    assert len(response_filter.json()) == 1

    # 3. Admin can rename a device
    rename_payload = {"device_label": "New Label"}
    response_rename = client.patch(f"/api/security-admin/devices/{dev1_id}", json=rename_payload, headers=headers)
    assert response_rename.status_code == 200
    assert response_rename.json()["device_label"] == "New Label"

    # Verify audit event for rename
    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == admin_id, AuditEvent.action == "DEVICE_RENAME").all()
        assert len(audits) == 1
        assert "New Label" in audits[0].reason
    finally:
        db.close()

    # 4. Admin can approve an untrusted/revoked device
    approve_payload = {"reason": "Found it"}
    response_approve = client.post(f"/api/security-admin/devices/{dev2_id}/approve", json=approve_payload, headers=headers)
    assert response_approve.status_code == 200
    assert response_approve.json()["is_trusted"] is True
    assert response_approve.json()["revoked_at"] is None

    # Verify audit event for approve
    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == admin_id, AuditEvent.action == "DEVICE_APPROVED").all()
        assert len(audits) == 1
        assert audits[0].reason == "Found it"
        assert "Found it" in (audits[0].after_state or "")
    finally:
        db.close()


def test_non_admin_forbidden():
    db = SessionLocal()
    try:
        agent = create_user(db, "test_admin_device_agent3@example.com", UserRole.AGENT)
        agent_token, _, _ = create_valid_session_and_token(db, agent, "agent3_dev")
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {agent_token}"}
    response = client.get("/api/security-admin/devices", headers=headers)
    assert response.status_code == 403


def test_admin_revoke_device():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_admin_device_admin4@example.com", UserRole.ADMIN)
        agent = create_user(db, "test_admin_device_agent4@example.com", UserRole.AGENT)

        agent_token, session, dev = create_valid_session_and_token(db, agent, "agent_device_xyz")
        admin_token, _, _ = create_valid_session_and_token(db, admin, "admin_dev")

        admin_id = admin.id
        agent_id = agent.id
        dev_id = dev.id
        sid = session.sid
        jti = session.jti
        device_id_hash = dev.device_id_hash
    finally:
        db.close()

    # Enforce mode on
    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    # Verify route works initially
    response_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {agent_token}"})
    assert response_me.status_code == 200

    # Revoke device via admin API
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    revoke_payload = {"reason": "Stolen phone"}

    response_revoke = client.post(
        f"/api/security-admin/devices/{dev_id}/revoke",
        json=revoke_payload,
        headers=admin_headers
    )
    assert response_revoke.status_code == 200
    assert response_revoke.json()["is_trusted"] is False
    assert response_revoke.json()["revoke_reason"] == "Stolen phone"

    # Verify device is inactive/revoked in DB
    db = SessionLocal()
    try:
        device_row = db.query(TrustedDevice).filter(TrustedDevice.id == dev_id).first()
        assert device_row.is_trusted is False
        assert device_row.revoked_at is not None
        first_revoked_at = device_row.revoked_at

        # Verify audit event
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == admin_id, AuditEvent.action == "DEVICE_REVOKED").all()
        assert len(audits) == 1
        assert "Stolen phone" in audits[0].reason
        # Ensure no raw JWT/secrets leaked
        for s_val in [sid, jti, agent_token, device_id_hash]:
            assert s_val not in (audits[0].after_state or "")
    finally:
        db.close()

    # Verify calling /me now fails with 403 DEVICE_NOT_TRUSTED
    response_me_after = client.get("/api/auth/me", headers={"Authorization": f"Bearer {agent_token}"})
    assert response_me_after.status_code == 403
    assert response_me_after.json()["detail"]["code"] == "DEVICE_NOT_TRUSTED"

    # Verify idempotency: calling revoke again returns success
    response_revoke_again = client.post(
        f"/api/security-admin/devices/{dev_id}/revoke",
        json=revoke_payload,
        headers=admin_headers
    )
    assert response_revoke_again.status_code == 200

    db = SessionLocal()
    try:
        device_row = db.query(TrustedDevice).filter(TrustedDevice.id == dev_id).first()
        assert device_row.revoked_at == first_revoked_at

        audits = (
            db.query(AuditEvent)
            .filter(AuditEvent.actor_id == admin_id, AuditEvent.action == "DEVICE_REVOKED")
            .order_by(AuditEvent.id.asc())
            .all()
        )
        assert len(audits) == 2
        assert '"already_revoked": true' in (audits[1].after_state or "")
        assert "Stolen phone" in (audits[1].reason or "")
        for s_val in [sid, jti, agent_token, device_id_hash]:
            assert s_val not in (audits[1].after_state or "")
            assert s_val not in (audits[1].reason or "")
    finally:
        db.close()


def test_device_missing():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_admin_device_admin5@example.com", UserRole.ADMIN)
        admin_token, _, _ = create_valid_session_and_token(db, admin, "admin_dev")
    finally:
        db.close()

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post(
        "/api/security-admin/devices/999999/revoke",
        json={"reason": "Test"},
        headers=admin_headers
    )
    assert response.status_code == 404
