import os
import pytest
import secrets
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta, date, time

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, EmployeeShift, AuditEvent, EmployeeStatus, UserSession, TrustedDevice
from app.security import get_password_hash, create_access_token
from app.config import get_settings
from app.services.security_policy import hash_device_id

client = TestClient(app)

def cleanup_test_db():
    db: Session = SessionLocal()
    try:
        emp_ids = [e.id for e in db.query(Employee).filter(Employee.email.like("test_admin_shift_%")).all()]
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
        name="Test Shift Employee",
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


def test_admin_create_normal_shift():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_admin_shift_admin@example.com", UserRole.ADMIN)
        agent = create_user(db, "test_admin_shift_agent@example.com", UserRole.AGENT)
        admin_id = admin.id
        agent_id = agent.id
        admin_email = admin.email
    finally:
        db.close()

    token = create_access_token(data={"sub": admin_email, "user_id": admin_id, "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "employee_id": agent_id,
        "work_date": "2026-06-18",
        "shift_start": "09:00",
        "shift_end": "17:00",
        "grace_before_minutes": 15,
        "grace_after_minutes": 15,
        "status": "scheduled"
    }

    response = client.post("/api/security-admin/shifts", json=payload, headers=headers)
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["employee_id"] == agent_id
    assert res_data["work_date"] == "2026-06-18"
    assert res_data["shift_start"] == "09:00:00"
    assert res_data["shift_end"] == "17:00:00"
    assert res_data["status"] == "scheduled"

    # Verify audit event
    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == admin_id, AuditEvent.action == "SHIFT_CREATE").all()
        assert len(audits) == 1
        assert "SHIFT_CREATE" in audits[0].action
        assert str(agent_id) in audits[0].target
    finally:
        db.close()


def test_admin_create_overnight_shift():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_admin_shift_admin2@example.com", UserRole.ADMIN)
        agent = create_user(db, "test_admin_shift_agent2@example.com", UserRole.AGENT)
        admin_id = admin.id
        agent_id = agent.id
        admin_email = admin.email
    finally:
        db.close()

    token = create_access_token(data={"sub": admin_email, "user_id": admin_id, "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "employee_id": agent_id,
        "work_date": "2026-06-18",
        "shift_start": "22:00",
        "shift_end": "06:00",
        "grace_before_minutes": 10,
        "grace_after_minutes": 10,
        "status": "scheduled"
    }

    response = client.post("/api/security-admin/shifts", json=payload, headers=headers)
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["shift_start"] == "22:00:00"
    assert res_data["shift_end"] == "06:00:00"


def test_admin_update_shift():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_admin_shift_admin3@example.com", UserRole.ADMIN)
        agent = create_user(db, "test_admin_shift_agent3@example.com", UserRole.AGENT)
        admin_id = admin.id
        agent_id = agent.id
        admin_email = admin.email

        shift = EmployeeShift(
            employee_id=agent_id,
            work_date=date(2026, 6, 18),
            shift_start=time(9, 0),
            shift_end=time(17, 0),
            grace_before_minutes=10,
            grace_after_minutes=10,
            status="scheduled"
        )
        db.add(shift)
        db.commit()
        shift_id = shift.id
    finally:
        db.close()

    token = create_access_token(data={"sub": admin_email, "user_id": admin_id, "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    update_payload = {
        "shift_start": "10:30",
        "grace_before_minutes": 20
    }

    response = client.patch(f"/api/security-admin/shifts/{shift_id}", json=update_payload, headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["shift_start"] == "10:30:00"
    assert res_data["shift_end"] == "17:00:00"
    assert res_data["grace_before_minutes"] == 20

    # Verify audit event
    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == admin_id, AuditEvent.action == "SHIFT_UPDATE").all()
        assert len(audits) == 1
        assert "10:30" in audits[0].after_state
    finally:
        db.close()


def test_admin_update_shift_duplicate_date_returns_400_without_audit():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_admin_shift_admin_duplicate@example.com", UserRole.ADMIN)
        agent = create_user(db, "test_admin_shift_agent_duplicate@example.com", UserRole.AGENT)
        admin_id = admin.id
        agent_id = agent.id
        admin_email = admin.email

        shift_one = EmployeeShift(
            employee_id=agent_id,
            work_date=date(2026, 6, 18),
            shift_start=time(9, 0),
            shift_end=time(17, 0),
            grace_before_minutes=10,
            grace_after_minutes=10,
            status="scheduled"
        )
        shift_two = EmployeeShift(
            employee_id=agent_id,
            work_date=date(2026, 6, 19),
            shift_start=time(9, 0),
            shift_end=time(17, 0),
            grace_before_minutes=10,
            grace_after_minutes=10,
            status="scheduled"
        )
        db.add_all([shift_one, shift_two])
        db.commit()
        shift_one_id = shift_one.id
    finally:
        db.close()

    token = create_access_token(data={"sub": admin_email, "user_id": admin_id, "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    response = client.patch(
        f"/api/security-admin/shifts/{shift_one_id}",
        json={"work_date": "2026-06-19"},
        headers=headers
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(
            AuditEvent.actor_id == admin_id,
            AuditEvent.action == "SHIFT_UPDATE"
        ).all()
        assert len(audits) == 0
    finally:
        db.close()


def test_admin_cancel_shift():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_admin_shift_admin4@example.com", UserRole.ADMIN)
        agent = create_user(db, "test_admin_shift_agent4@example.com", UserRole.AGENT)
        admin_id = admin.id
        agent_id = agent.id
        admin_email = admin.email

        shift = EmployeeShift(
            employee_id=agent_id,
            work_date=date(2026, 6, 18),
            shift_start=time(9, 0),
            shift_end=time(17, 0),
            grace_before_minutes=10,
            grace_after_minutes=10,
            status="scheduled"
        )
        db.add(shift)
        db.commit()
        shift_id = shift.id
    finally:
        db.close()

    token = create_access_token(data={"sub": admin_email, "user_id": admin_id, "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    cancel_payload = {"reason": "Sick leave"}

    response = client.post(f"/api/security-admin/shifts/{shift_id}/cancel", json=cancel_payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    # Verify audit event
    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == admin_id, AuditEvent.action == "SHIFT_CANCEL").all()
        assert len(audits) == 1
        assert "Sick leave" in audits[0].reason
    finally:
        db.close()


def test_cancelled_shift_blocks_access():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_admin_shift_admin5@example.com", UserRole.ADMIN)
        agent = create_user(db, "test_admin_shift_agent5@example.com", UserRole.AGENT)
        admin_id = admin.id
        agent_id = agent.id
        agent_email = agent.email
        admin_email = admin.email

        # Create session
        sid = secrets.token_hex(32)
        jti = secrets.token_hex(32)
        device_id_hash = hash_device_id("my_device_xyz")
        now = datetime.utcnow()
        session = UserSession(
            employee_id=agent_id,
            sid=sid,
            jti=jti,
            device_id_hash=device_id_hash,
            issued_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(hours=1),
            is_active=True
        )
        db.add(session)

        # Create a cancelled shift on the work date
        shift = EmployeeShift(
            employee_id=agent_id,
            work_date=now.date(),
            shift_start=(now - timedelta(hours=1)).time(),
            shift_end=(now + timedelta(hours=1)).time(),
            grace_before_minutes=10,
            grace_after_minutes=10,
            status="cancelled" # Cancelled status
        )
        db.add(shift)

        # Enroll device
        dev = TrustedDevice(
            employee_id=agent_id,
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

    # Turn on enforce mode
    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    token = create_access_token(
        data={
            "sub": agent_email,
            "user_id": agent_id,
            "role": "AGENT",
            "sid": sid,
            "jti": jti,
            "device_id_hash": device_id_hash
        }
    )

    # Calling protected endpoint should fail with SHIFT_NOT_ALLOWED
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "SHIFT_NOT_ALLOWED"


def test_non_admin_forbidden():
    db = SessionLocal()
    try:
        agent = create_user(db, "test_admin_shift_agent6@example.com", UserRole.AGENT)
        agent_id = agent.id
        agent_email = agent.email
    finally:
        db.close()

    token = create_access_token(data={"sub": agent_email, "user_id": agent_id, "role": "AGENT"})
    headers = {"Authorization": f"Bearer {token}"}

    # Try listing shifts
    response = client.get("/api/security-admin/shifts", headers=headers)
    assert response.status_code == 403
    assert "Only admins" in response.json()["detail"]


def test_validation_errors():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_admin_shift_admin7@example.com", UserRole.ADMIN)
        admin_id = admin.id
        admin_email = admin.email
    finally:
        db.close()

    token = create_access_token(data={"sub": admin_email, "user_id": admin_id, "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    # Test invalid grace values (ge=0, le=240)
    payload = {
        "employee_id": 99999, # Missing employee
        "work_date": "2026-06-18",
        "shift_start": "09:00",
        "shift_end": "17:00",
        "grace_before_minutes": 250, # Invalid grace
        "grace_after_minutes": -5,   # Invalid grace
        "status": "scheduled"
    }

    response = client.post("/api/security-admin/shifts", json=payload, headers=headers)
    assert response.status_code == 422

    # Test invalid status
    payload2 = {
        "employee_id": 99999,
        "work_date": "2026-06-18",
        "shift_start": "09:00",
        "shift_end": "17:00",
        "grace_before_minutes": 10,
        "grace_after_minutes": 10,
        "status": "invalid_status_xyz"
    }
    response2 = client.post("/api/security-admin/shifts", json=payload2, headers=headers)
    assert response2.status_code == 422

    # Test missing employee
    payload3 = {
        "employee_id": 99999, # Missing employee
        "work_date": "2026-06-18",
        "shift_start": "09:00",
        "shift_end": "17:00",
        "grace_before_minutes": 10,
        "grace_after_minutes": 10,
        "status": "scheduled"
    }
    response3 = client.post("/api/security-admin/shifts", json=payload3, headers=headers)
    assert response3.status_code == 404
