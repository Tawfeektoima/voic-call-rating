import os
import pytest
import secrets
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, AuditEvent, EmployeeStatus
from app.security import get_password_hash, create_access_token
from app.config import get_settings

client = TestClient(app)

def cleanup_test_db():
    db: Session = SessionLocal()
    try:
        # Delete created employees
        emp_ids = [e.id for e in db.query(Employee).filter(Employee.email.like("test_obs_%")).all()]
        if emp_ids:
            # Delete audit events for these employees or clean up test audit events
            db.query(AuditEvent).filter(AuditEvent.actor_id.in_(emp_ids)).delete(synchronize_session=False)
            db.query(Employee).filter(Employee.id.in_(emp_ids)).delete(synchronize_session=False)
        
        # Clean up any audit events with specific action/target/actor_email patterns we created
        db.query(AuditEvent).filter(AuditEvent.actor_email.like("test_obs_%")).delete(synchronize_session=False)
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
        name="Test Observability Employee",
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


def test_observability_summary_non_admin_returns_403():
    db = SessionLocal()
    try:
        agent = create_user(db, "test_obs_agent@example.com", UserRole.AGENT)
        token = create_access_token(data={"sub": agent.email})
    finally:
        db.close()

    response = client.get(
        "/api/security-admin/summary",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_observability_summary_admin_returns_correct_counts():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_obs_admin@example.com", UserRole.ADMIN)
        token = create_access_token(data={"sub": admin.email})

        # Insert some test events
        now = datetime.now(timezone.utc)
        
        # 1 denied login
        db.add(AuditEvent(actor_email=admin.email, action="SECURITY_POLICY_DENIAL", target="login", success=False, created_at=now))

        # 2 denied protected requests
        db.add(AuditEvent(actor_email=admin.email, action="SECURITY_POLICY_DENIAL", target="protected_request", success=False, created_at=now))
        db.add(AuditEvent(actor_email=admin.email, action="SECURITY_POLICY_DENIAL", target="protected_request", success=False, created_at=now))

        # 2 audit-only policy violations
        db.add(AuditEvent(actor_email=admin.email, action="SECURITY_POLICY_AUDIT", target="login", success=True, created_at=now))
        db.add(AuditEvent(actor_email=admin.email, action="SECURITY_POLICY_AUDIT", target="websocket", success=True, created_at=now))

        # 3 revoked sessions
        db.add(AuditEvent(actor_email=admin.email, action="SESSION_REVOKED", target="session", success=True, created_at=now))
        db.add(AuditEvent(actor_email=admin.email, action="SESSION_REVOKED", target="session", success=True, created_at=now))
        db.add(AuditEvent(actor_email=admin.email, action="SESSION_REVOKED", target="session", success=True, created_at=now))

        # 4 revoked devices
        for _ in range(4):
            db.add(AuditEvent(actor_email=admin.email, action="DEVICE_REVOKED", target="device", success=True, created_at=now))

        # 5 cancelled shifts
        for _ in range(5):
            db.add(AuditEvent(actor_email=admin.email, action="SHIFT_CANCEL", target="shift", success=True, created_at=now))

        # 6 websocket closes
        for _ in range(6):
            db.add(AuditEvent(actor_email=admin.email, action="WEBSOCKET_SECURITY_CLOSE", target="websocket", success=False, created_at=now))

        # Other events that shouldn't be counted in our metrics
        db.add(AuditEvent(actor_email=admin.email, action="SHIFT_CREATE", target="shift", success=True, created_at=now))
        db.add(AuditEvent(actor_email=admin.email, action="SECURITY_POLICY_DENIAL", target="other", success=False, created_at=now))

        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/security-admin/summary",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()

    # Validate correct counts
    assert data["audit_policy_violations"] == 2
    assert data["enforced_policy_denials"] == 4
    assert data["denied_logins"] == 1
    assert data["denied_protected_requests"] == 2
    assert data["revoked_sessions"] == 3
    assert data["revoked_devices"] == 4
    assert data["cancelled_shifts"] == 5
    assert data["websocket_security_closes"] == 6

    # Verify summary contains no sensitive identifiers
    expected_keys = {
        "audit_policy_violations",
        "enforced_policy_denials",
        "denied_logins",
        "denied_protected_requests",
        "revoked_sessions",
        "revoked_devices",
        "cancelled_shifts",
        "websocket_security_closes"
    }
    assert set(data.keys()) == expected_keys


def test_observability_summary_time_window_filtering():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_obs_admin_time@example.com", UserRole.ADMIN)
        token = create_access_token(data={"sub": admin.email})

        now = datetime.now(timezone.utc)
        
        # 1 denied login within 24h
        db.add(AuditEvent(actor_email=admin.email, action="SECURITY_POLICY_DENIAL", target="login", success=False, created_at=now - timedelta(hours=2)))
        
        # 1 denied login outside 24h but inside 48h
        db.add(AuditEvent(actor_email=admin.email, action="SECURITY_POLICY_DENIAL", target="login", success=False, created_at=now - timedelta(hours=36)))

        db.commit()
    finally:
        db.close()

    # Default (24 hours)
    response = client.get(
        "/api/security-admin/summary",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["denied_logins"] == 1

    # Bounded 48 hours
    response = client.get(
        "/api/security-admin/summary?hours=48",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["denied_logins"] == 2

    # Invalid hours parameter (le=168 validation check, ge=1)
    response = client.get(
        "/api/security-admin/summary?hours=0",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422

    response = client.get(
        "/api/security-admin/summary?hours=200",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422
