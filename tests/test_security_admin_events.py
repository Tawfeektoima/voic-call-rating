import json
import os
import secrets
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.main import app
from app.models import AuditEvent, Employee, EmployeeStatus, UserRole
from app.security import create_access_token, get_password_hash

client = TestClient(app)


def cleanup_test_db():
    db: Session = SessionLocal()
    try:
        db.query(AuditEvent).filter(AuditEvent.actor_email.like("test_events_%")).delete(synchronize_session=False)
        db.query(Employee).filter(Employee.email.like("test_events_%")).delete(synchronize_session=False)
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


def create_user(db: Session, email: str, role: UserRole) -> Employee:
    user = Employee(
        name="Test Events User",
        email=email,
        hashed_password=get_password_hash("TestPassword123!"),
        role=role,
        employee_code=f"CODE_{secrets.token_hex(4)}",
        status=EmployeeStatus.ACTIVE.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_security_audit_feed_requires_admin():
    db = SessionLocal()
    try:
        user = create_user(db, "test_events_agent@example.com", UserRole.AGENT)
        token = create_access_token(data={"sub": user.email})
    finally:
        db.close()

    response = client.get(
        "/api/security-admin/events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_security_audit_feed_redacts_sensitive_values_and_filters_events():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_events_admin@example.com", UserRole.ADMIN)
        subject = create_user(db, "test_events_subject@example.com", UserRole.AGENT)
        subject_id = subject.id
        token = create_access_token(data={"sub": admin.email})

        now = datetime.now(timezone.utc)
        raw_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature"
        raw_device_id = "device-raw-12345"
        raw_device_hash = "a" * 64

        db.add(AuditEvent(
            actor_id=admin.id,
            actor_email=admin.email,
            action="SESSION_REVOKED",
            target=f"UserSession id=77; employee_id={subject_id}; raw_device_id={raw_device_id}; device_id_hash={raw_device_hash}",
            after_state=json.dumps({
                "session_id": 77,
                "employee_id": subject_id,
                "already_revoked": True,
                "reason": f"sid={raw_device_id}; jti={raw_device_hash}; jwt={raw_jwt}",
            }),
            reason=f"Review token sid={raw_device_id} jti={raw_device_hash} jwt={raw_jwt}",
            success=True,
            created_at=now,
        ))

        db.add(AuditEvent(
            actor_id=admin.id,
            actor_email=admin.email,
            action="DEVICE_REVOKED",
            target=f"TrustedDevice id=91; employee_id={subject_id}",
            after_state=json.dumps({
                "device_id": 91,
                "employee_id": subject_id,
                "already_revoked": True,
                "reason": "Device cleanup",
            }),
            reason="Device cleanup",
            success=True,
            created_at=now - timedelta(minutes=5),
        ))

        db.add(AuditEvent(
            actor_id=admin.id,
            actor_email=admin.email,
            action="SHIFT_CREATE",
            target="EmployeeShift id=5; employee_id=999",
            after_state=json.dumps({"employee_id": 999, "work_date": "2026-06-19"}),
            reason="Shift created",
            success=True,
            created_at=now,
        ))
        db.commit()
    finally:
        db.close()

    response = client.get(
        f"/api/security-admin/events?hours=24&action=SESSION_REVOKED&employee_id={subject_id}&success=true&limit=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["total"] == 1
    assert len(body["items"]) == 1
    event = body["items"][0]
    assert event["action"] == "SESSION_REVOKED"
    assert event["subject_employee_id"] == subject_id
    assert event["success"] is True

    response_text = json.dumps(body)
    assert raw_jwt not in response_text
    assert raw_device_id not in response_text
    assert raw_device_hash not in response_text
    assert "sid=" not in response_text or "[REDACTED]" in response_text
    assert "jti=" not in response_text or "[REDACTED]" in response_text
    assert "jwt=" not in response_text or "[REDACTED]" in response_text


def test_security_audit_feed_paginates_recent_events():
    db = SessionLocal()
    try:
        admin = create_user(db, "test_events_admin_page@example.com", UserRole.ADMIN)
        token = create_access_token(data={"sub": admin.email})
        now = datetime.now(timezone.utc)

        for idx in range(3):
            db.add(AuditEvent(
                actor_id=admin.id,
                actor_email=admin.email,
                action="DEVICE_APPROVED",
                target=f"TrustedDevice id={idx}; employee_id={admin.id}",
                after_state=json.dumps({"device_id": idx, "employee_id": admin.id}),
                reason=f"Approval {idx}",
                success=True,
                created_at=now - timedelta(minutes=idx),
            ))
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/security-admin/events?hours=24&limit=2&offset=0&action=DEVICE_APPROVED",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["offset"] == 0
    assert body["limit"] == 2
