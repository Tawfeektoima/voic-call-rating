import os
import pytest
import secrets
from fastapi.testclient import TestClient
from fastapi import WebSocketDisconnect
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta, date, time

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
        emp_ids = [e.id for e in db.query(Employee).filter(Employee.email.like("test_ws_policy_%")).all()]
        if emp_ids:
            db.query(LiveSession).filter(LiveSession.agent_id.in_(emp_ids)).delete(synchronize_session=False)
            db.query(EmployeeShift).filter(EmployeeShift.employee_id.in_(emp_ids)).delete(synchronize_session=False)
            db.query(UserSession).filter(UserSession.employee_id.in_(emp_ids)).delete(synchronize_session=False)
            db.query(TrustedDevice).filter(TrustedDevice.employee_id.in_(emp_ids)).delete(synchronize_session=False)
            db.query(Employee).filter(Employee.id.in_(emp_ids)).delete(synchronize_session=False)
        db.query(Campaign).filter(Campaign.name == "test_ws_policy_campaign").delete(synchronize_session=False)
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
        name="Test WS Employee",
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
    db: Session, user: Employee, device_id="ws_device", shift_status="scheduled", skip_shift=False
) -> tuple[str, UserSession, TrustedDevice]:
    if not skip_shift:
        create_test_shift(db, user.id, status=shift_status)
    
    device_id_hash = hash_device_id(device_id)
    now = datetime.utcnow()
    dev = TrustedDevice(
        employee_id=user.id,
        device_id_hash=device_id_hash,
        device_label="WS Device",
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


def create_token_with_missing_claims(user: Employee) -> str:
    return create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        }
    )


def test_ws_off_mode():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_policy_off@example.com", UserRole.AGENT)
        token = create_token_with_missing_claims(user)
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "off"
    get_settings.cache_clear()

    with client.websocket_connect(f"/ws/calls/123?auth_token={token}") as ws:
        pass


def test_ws_audit_mode_missing_claims():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_policy_audit@example.com", UserRole.AGENT)
        token = create_token_with_missing_claims(user)
        user_id = user.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "audit"
    get_settings.cache_clear()

    with client.websocket_connect(f"/ws/calls/123?auth_token={token}") as ws:
        pass

    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(
            AuditEvent.actor_id == user_id,
            AuditEvent.action == "SECURITY_POLICY_AUDIT"
        ).all()
        assert len(audits) >= 1
        assert "SESSION_CLAIMS_MISSING" in audits[0].after_state
    finally:
        db.close()


def test_ws_enforce_mode_missing_claims():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_policy_enc_missing@example.com", UserRole.AGENT)
        token = create_token_with_missing_claims(user)
        user_id = user.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/calls/123?auth_token={token}"):
            pass
    assert exc.value.code == 4401

    db = SessionLocal()
    try:
        close_event = db.query(AuditEvent).filter(
            AuditEvent.actor_id == user_id,
            AuditEvent.action == "WEBSOCKET_SECURITY_CLOSE"
        ).order_by(AuditEvent.id.desc()).first()
        assert close_event is not None
        assert '"close_code": 4401' in (close_event.after_state or "")
        assert "SESSION_CLAIMS_MISSING" in (close_event.after_state or "")
    finally:
        db.close()


def test_ws_enforce_mode_revoked_session():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_policy_enc_revoked@example.com", UserRole.AGENT)
        token, session, _ = create_valid_session_and_token(db, user)
        session.is_active = False
        session.revoked_at = datetime.utcnow()
        session.revoke_reason = "admin force"
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/calls/123?auth_token={token}"):
            pass
    assert exc.value.code == 4401


def test_ws_enforce_mode_expired_session():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_policy_enc_expired@example.com", UserRole.AGENT)
        token, session, _ = create_valid_session_and_token(db, user)
        session.expires_at = datetime.utcnow() - timedelta(minutes=10)
        db.commit()
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/calls/123?auth_token={token}"):
            pass
    assert exc.value.code == 4401


def test_ws_enforce_mode_untrusted_device():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_policy_enc_untrusted@example.com", UserRole.AGENT)
        token, _, dev = create_valid_session_and_token(db, user)
        dev.is_trusted = False
        dev.revoked_at = datetime.utcnow()
        db.commit()
        user_id = user.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/calls/123?auth_token={token}"):
            pass
    assert exc.value.code == 4403

    db = SessionLocal()
    try:
        close_event = db.query(AuditEvent).filter(
            AuditEvent.actor_id == user_id,
            AuditEvent.action == "WEBSOCKET_SECURITY_CLOSE"
        ).order_by(AuditEvent.id.desc()).first()
        assert close_event is not None
        assert '"close_code": 4403' in (close_event.after_state or "")
        assert "DEVICE_NOT_TRUSTED" in (close_event.after_state or "")
    finally:
        db.close()


def test_ws_enforce_mode_outside_shift():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_policy_enc_outside_shift@example.com", UserRole.AGENT)
        token, _, _ = create_valid_session_and_token(db, user, shift_status="cancelled")
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/calls/123?auth_token={token}"):
            pass
    assert exc.value.code == 4403


def test_ws_enforce_mode_success():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_policy_enc_success@example.com", UserRole.AGENT)
        token, session, _ = create_valid_session_and_token(db, user)
        session_id = session.id
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    db = SessionLocal()
    try:
        sess = db.query(UserSession).filter(UserSession.id == session_id).first()
        initial_last_seen = sess.last_seen_at
    finally:
        db.close()

    with client.websocket_connect(f"/ws/calls/123?auth_token={token}") as ws:
        pass

    db = SessionLocal()
    try:
        sess = db.query(UserSession).filter(UserSession.id == session_id).first()
        assert sess.last_seen_at > initial_last_seen
    finally:
        db.close()


def test_ws_enforce_mode_denied_no_last_seen_update():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_policy_enc_denied_no_touch@example.com", UserRole.AGENT)
        token, session, _ = create_valid_session_and_token(db, user, shift_status="cancelled")
        session_id = session.id
        initial_last_seen = session.last_seen_at
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/calls/123?auth_token={token}"):
            pass

    db = SessionLocal()
    try:
        sess = db.query(UserSession).filter(UserSession.id == session_id).first()
        assert sess.last_seen_at == initial_last_seen
    finally:
        db.close()


def test_ws_audit_log_sanitization():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_policy_sanitization@example.com", UserRole.AGENT)
        token, session, _ = create_valid_session_and_token(db, user, shift_status="cancelled")
        user_id = user.id
        sid = session.sid
        jti = session.jti
        device_id_hash = session.device_id_hash
    finally:
        db.close()

    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    get_settings.cache_clear()

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/calls/123?auth_token={token}"):
            pass

    db = SessionLocal()
    try:
        audits = db.query(AuditEvent).filter(
            AuditEvent.actor_id == user_id,
            AuditEvent.action.in_(("SECURITY_POLICY_DENIAL", "WEBSOCKET_SECURITY_CLOSE"))
        ).all()
        assert len(audits) >= 1
        for audit in audits:
            for val in [sid, jti, token, device_id_hash]:
                assert val not in (audit.after_state or "")
                assert val not in (audit.reason or "")
    finally:
        db.close()


def test_ws_live_endpoint_integration():
    db = SessionLocal()
    try:
        user = create_user(db, "test_ws_policy_live_int@example.com", UserRole.AGENT)
        token, _, _ = create_valid_session_and_token(db, user)
        
        campaign = Campaign(
            name="test_ws_policy_campaign",
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
    get_settings.cache_clear()

    # Enabled live pipeline
    original_live_flag = get_settings().LIVE_PIPELINE_ENABLED
    get_settings().LIVE_PIPELINE_ENABLED = True

    try:
        with client.websocket_connect(
            f"/api/live/ws/live/{live_sess_id}?token=my_reconnect_token&auth_token={token}"
        ) as ws:
            resp = ws.receive_json()
            assert resp["event"] == "connected"
    finally:
        get_settings().LIVE_PIPELINE_ENABLED = original_live_flag
