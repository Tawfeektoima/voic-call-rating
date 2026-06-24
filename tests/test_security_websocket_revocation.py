import os
import pytest
import secrets
import asyncio
import time
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi import WebSocketDisconnect
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, UserSession, TrustedDevice, AuditEvent, EmployeeStatus, EmployeeShift, LiveSession, Campaign
from app.security import get_password_hash, create_access_token
from app.config import get_settings
from app.services.security_policy import hash_device_id

client = TestClient(app)

def cleanup_test_db():
    db: Session = SessionLocal()
    try:
        emp_ids = [e.id for e in db.query(Employee).filter(Employee.email.like("test_ws_revoc_%")).all()]
        if emp_ids:
            db.query(LiveSession).filter(LiveSession.agent_id.in_(emp_ids)).delete(synchronize_session=False)
            db.query(EmployeeShift).filter(EmployeeShift.employee_id.in_(emp_ids)).delete(synchronize_session=False)
            db.query(UserSession).filter(UserSession.employee_id.in_(emp_ids)).delete(synchronize_session=False)
            db.query(TrustedDevice).filter(TrustedDevice.employee_id.in_(emp_ids)).delete(synchronize_session=False)
            db.query(Employee).filter(Employee.id.in_(emp_ids)).delete(synchronize_session=False)
        db.query(Campaign).filter(Campaign.name == "test_ws_revoc_campaign").delete(synchronize_session=False)
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
        name="Test WS Revoc Employee",
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


def create_test_shift(db: Session, employee_id: int, status="scheduled") -> EmployeeShift:
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
        status=status
    )
    db.add(shift)
    db.commit()
    return shift


def create_valid_session_and_token(
    db: Session, user: Employee, device_id="ws_revoc_device", shift_status="scheduled", skip_shift=False
) -> tuple[str, UserSession, TrustedDevice]:
    if not skip_shift:
        create_test_shift(db, user.id, status=shift_status)
    
    device_id_hash = hash_device_id(device_id)
    now = datetime.utcnow()
    dev = TrustedDevice(
        employee_id=user.id,
        device_id_hash=device_id_hash,
        device_label="WS Revoc Device",
        is_trusted=True,
        first_seen_at=now,
        last_seen_at=now,
        approved_at=now
    )
    db.add(dev)
    db.flush()

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


def test_ws_enforce_revoked_session():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_revoc_session@example.com", UserRole.AGENT)
        token, session, _ = create_valid_session_and_token(db, user)
        session_id = session.id
        user_id = user.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    os.environ["SECURITY_WS_REVALIDATION_INTERVAL_SECONDS"] = "0"
    get_settings.cache_clear()

    with client.websocket_connect(f"/ws/calls/123?auth_token={token}") as ws:
        db = SessionLocal()
        try:
            sess = db.query(UserSession).filter(UserSession.id == session_id).first()
            sess.is_active = False
            sess.revoked_at = datetime.utcnow()
            db.commit()
        finally:
            db.close()

        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
        assert exc.value.code == 4401

    db = SessionLocal()
    try:
        audit = db.query(AuditEvent).filter(
            AuditEvent.actor_id == user_id,
            AuditEvent.action == "SESSION_REVOKED"
        ).first()
        assert audit is not None
        assert "SESSION_REVOKED" in audit.after_state
    finally:
        db.close()


def test_ws_enforce_expired_session():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_revoc_expired@example.com", UserRole.AGENT)
        token, session, _ = create_valid_session_and_token(db, user)
        session_id = session.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    os.environ["SECURITY_WS_REVALIDATION_INTERVAL_SECONDS"] = "0"
    get_settings.cache_clear()

    with client.websocket_connect(f"/ws/calls/123?auth_token={token}") as ws:
        db = SessionLocal()
        try:
            sess = db.query(UserSession).filter(UserSession.id == session_id).first()
            sess.expires_at = datetime.utcnow() - timedelta(minutes=10)
            db.commit()
        finally:
            db.close()

        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
        assert exc.value.code == 4401


def test_ws_enforce_revoked_device():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_revoc_device@example.com", UserRole.AGENT)
        token, _, dev = create_valid_session_and_token(db, user)
        dev_id = dev.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    os.environ["SECURITY_WS_REVALIDATION_INTERVAL_SECONDS"] = "0"
    get_settings.cache_clear()

    with client.websocket_connect(f"/ws/calls/123?auth_token={token}") as ws:
        db = SessionLocal()
        try:
            device = db.query(TrustedDevice).filter(TrustedDevice.id == dev_id).first()
            device.is_trusted = False
            device.revoked_at = datetime.utcnow()
            db.commit()
        finally:
            db.close()

        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
        assert exc.value.code == 4403


def test_ws_enforce_cancelled_shift():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_revoc_shift@example.com", UserRole.AGENT)
        token, _, _ = create_valid_session_and_token(db, user)
        employee_id = user.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    os.environ["SECURITY_WS_REVALIDATION_INTERVAL_SECONDS"] = "0"
    get_settings.cache_clear()

    with client.websocket_connect(f"/ws/calls/123?auth_token={token}") as ws:
        db = SessionLocal()
        try:
            shift = db.query(EmployeeShift).filter(EmployeeShift.employee_id == employee_id).first()
            shift.status = "cancelled"
            db.commit()
        finally:
            db.close()

        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
        assert exc.value.code == 4403


def test_ws_silent_socket_revalidation():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_revoc_silent@example.com", UserRole.AGENT)
        token, session, _ = create_valid_session_and_token(db, user)
        session_id = session.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    os.environ["SECURITY_WS_REVALIDATION_INTERVAL_SECONDS"] = "1"
    get_settings.cache_clear()

    with client.websocket_connect(f"/ws/calls/123?auth_token={token}") as ws:
        db = SessionLocal()
        try:
            sess = db.query(UserSession).filter(UserSession.id == session_id).first()
            sess.is_active = False
            sess.revoked_at = datetime.utcnow()
            db.commit()
        finally:
            db.close()

        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
        assert exc.value.code == 4401


def test_ws_success_updates_last_seen():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_revoc_touch@example.com", UserRole.AGENT)
        token, session, _ = create_valid_session_and_token(db, user)
        session_id = session.id
        initial_last_seen = session.last_seen_at
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    os.environ["SECURITY_WS_REVALIDATION_INTERVAL_SECONDS"] = "0"
    get_settings.cache_clear()

    with client.websocket_connect(f"/ws/calls/123?auth_token={token}") as ws:
        ws.send_text("hello")
        time.sleep(0.1)

    db = SessionLocal()
    try:
        sess = db.query(UserSession).filter(UserSession.id == session_id).first()
        assert sess.last_seen_at > initial_last_seen
    finally:
        db.close()


def test_ws_audit_mode_legacy_token():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_revoc_legacy@example.com", UserRole.AGENT)
        token = create_access_token(
            data={
                "sub": user.email,
                "user_id": user.id,
                "role": user.role.value if hasattr(user.role, "value") else str(user.role)
            }
        )
        user_id = user.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "audit"
    get_settings.cache_clear()

    with client.websocket_connect(f"/ws/calls/123?auth_token={token}") as ws:
        pass

    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(AuditEvent.actor_id == user_id).all()
        assert len(audits) >= 1
        actions = [a.action for a in audits]
        assert "SECURITY_POLICY_AUDIT" in actions
        for a in audits:
            assert "DEVICE_NOT_TRUSTED" not in (a.after_state or "")
    finally:
        db.close()


def test_ws_live_revocation_integration():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_revoc_live@example.com", UserRole.AGENT)
        token, session, _ = create_valid_session_and_token(db, user)
        session_id = session.id
        
        campaign = Campaign(
            name="test_ws_revoc_campaign",
            evaluation_prompt="Test evaluation prompt",
            color="#FFFFFF"
        )
        db.add(campaign)
        db.flush()

        live_sess = LiveSession(
            id=f"live-sess-{secrets.token_hex(4)}",
            campaign_id=campaign.id,
            agent_id=user.id,
            reconnect_token="my_reconnect_token",
            gpu_id=0,
            status="active"
        )
        db.add(live_sess)
        db.commit()
        live_sess_id = live_sess.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    os.environ["SECURITY_WS_REVALIDATION_INTERVAL_SECONDS"] = "0"
    get_settings.cache_clear()

    original_live_flag = get_settings().LIVE_PIPELINE_ENABLED
    get_settings().LIVE_PIPELINE_ENABLED = True

    try:
        with client.websocket_connect(
            f"/api/live/ws/live/{live_sess_id}?token=my_reconnect_token&auth_token={token}"
        ) as ws:
            ws.receive_json()
            db = SessionLocal()
            try:
                sess = db.query(UserSession).filter(UserSession.id == session_id).first()
                sess.is_active = False
                sess.revoked_at = datetime.utcnow()
                db.commit()
            finally:
                db.close()

            with pytest.raises(WebSocketDisconnect) as exc:
                ws.receive_bytes()
            assert exc.value.code == 4401
    finally:
        get_settings().LIVE_PIPELINE_ENABLED = original_live_flag


def test_ws_live_device_revocation_integration():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_revoc_live_dev@example.com", UserRole.AGENT)
        token, _, dev = create_valid_session_and_token(db, user)
        dev_id = dev.id
        
        campaign = Campaign(
            name="test_ws_revoc_campaign",
            evaluation_prompt="Test evaluation prompt",
            color="#FFFFFF"
        )
        db.add(campaign)
        db.flush()

        live_sess = LiveSession(
            id=f"live-sess-{secrets.token_hex(4)}",
            campaign_id=campaign.id,
            agent_id=user.id,
            reconnect_token="my_reconnect_token",
            gpu_id=0,
            status="active"
        )
        db.add(live_sess)
        db.commit()
        live_sess_id = live_sess.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    os.environ["SECURITY_WS_REVALIDATION_INTERVAL_SECONDS"] = "0"
    get_settings.cache_clear()

    original_live_flag = get_settings().LIVE_PIPELINE_ENABLED
    get_settings().LIVE_PIPELINE_ENABLED = True

    try:
        with client.websocket_connect(
            f"/api/live/ws/live/{live_sess_id}?token=my_reconnect_token&auth_token={token}"
        ) as ws:
            ws.receive_json()
            db = SessionLocal()
            try:
                device = db.query(TrustedDevice).filter(TrustedDevice.id == dev_id).first()
                device.is_trusted = False
                device.revoked_at = datetime.utcnow()
                db.commit()
            finally:
                db.close()

            with pytest.raises(WebSocketDisconnect) as exc:
                ws.receive_bytes()
            assert exc.value.code == 4403
    finally:
        get_settings().LIVE_PIPELINE_ENABLED = original_live_flag


def test_ws_internal_validation_failure_code():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_revoc_commit_err@example.com", UserRole.AGENT)
        token, _, _ = create_valid_session_and_token(db, user)
        user_id = user.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    os.environ["SECURITY_WS_REVALIDATION_INTERVAL_SECONDS"] = "0"
    get_settings.cache_clear()

    with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("Database error")):
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(f"/ws/calls/123?auth_token={token}"):
                pass
        assert exc.value.code == 1011

    db = SessionLocal()
    try:
        close_event = db.query(AuditEvent).filter(
            AuditEvent.actor_id == user_id,
            AuditEvent.action == "WEBSOCKET_SECURITY_CLOSE"
        ).order_by(AuditEvent.id.desc()).first()
        assert close_event is not None
        assert '"close_code": 1011' in (close_event.after_state or "")
        assert "SECURITY_VALIDATION_COMMIT_FAILED" in (close_event.after_state or "")
    finally:
        db.close()
