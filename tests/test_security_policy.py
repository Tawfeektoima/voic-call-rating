import os
import pytest
from datetime import datetime, date, time, timezone, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from app.config import get_settings, Settings
from app.database import SessionLocal
from app.models import Employee, EmployeeShift, TrustedDevice, UserSession, AuditEvent, UserRole, EmployeeStatus
from app.services.security_policy import (
    hash_security_value,
    hash_device_id,
    hash_user_agent,
    get_policy_mode,
    is_policy_off,
    is_policy_audit,
    is_policy_enforce,
    get_security_timezone,
    get_employee_shift_for_now,
    is_shift_allowed,
    enroll_trusted_device,
    is_device_trusted,
    get_trusted_device,
    auto_enroll_first_trusted_device,
    create_user_session,
    revoke_session,
    has_other_active_session,
    get_active_session_by_claims,
    get_active_session_for_employee,
    audit_security_decision,
    SecurityDecision,
    SECURITY_OK,
    SECURITY_POLICY_OFF,
    DEVICE_REQUIRED,
    DEVICE_NOT_TRUSTED,
    ACTIVE_SESSION_EXISTS,
    SESSION_NOT_FOUND,
    SESSION_REVOKED,
    SESSION_EXPIRED,
    SHIFT_NOT_FOUND,
    SHIFT_ACCESS_DENIED,
)


@pytest.fixture(autouse=True)
def manage_settings_and_db_cleanup():
    # Clear settings cache and environment changes
    get_settings.cache_clear()
    original_env = dict(os.environ)
    
    yield
    
    os.environ.clear()
    os.environ.update(original_env)
    get_settings.cache_clear()


def create_test_employee(db: Session, email="policy_emp@example.com", code="POLICY_EMP"):
    emp = Employee(
        name="Policy Employee",
        email=email,
        employee_code=code,
        hashed_password="fake",
        role=UserRole.AGENT,
        status=EmployeeStatus.ACTIVE.value
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


# ---------------------------------------------------------------------------
# 1. Hashing Tests
# ---------------------------------------------------------------------------

def test_hashing_basic():
    val = "my_device_id_123"
    h1 = hash_security_value(val)
    h2 = hash_security_value(val)
    
    assert h1 is not None
    assert h1 == h2
    assert val not in h1  # Raw value is not in output
    assert len(h1) == 64  # SHA-256 is 64 hex characters


def test_hashing_blanks():
    assert hash_security_value(None) is None
    assert hash_security_value("") is None
    assert hash_security_value("   ") is None
    assert hash_device_id(None) is None
    assert hash_user_agent("") is None


# ---------------------------------------------------------------------------
# 2. Settings Helpers Tests
# ---------------------------------------------------------------------------

def test_settings_helpers():
    os.environ["SECURITY_POLICY_MODE"] = "audit"
    os.environ["SECURITY_TIMEZONE"] = "Europe/London"
    get_settings.cache_clear()
    
    assert get_policy_mode() == "audit"
    assert is_policy_off() is False
    assert is_policy_audit() is True
    assert is_policy_enforce() is False
    assert get_security_timezone() == ZoneInfo("Europe/London")


# ---------------------------------------------------------------------------
# 3. Shift Policy Tests
# ---------------------------------------------------------------------------

def test_shift_allowance_scheduled_inside_window():
    db = SessionLocal()
    try:
        emp = create_test_employee(db)
        
        # Shift on 2026-06-18 from 09:00 to 17:00
        shift = EmployeeShift(
            employee_id=emp.id,
            work_date=date(2026, 6, 18),
            shift_start=time(9, 0),
            shift_end=time(17, 0),
            grace_before_minutes=10,
            grace_after_minutes=10,
            status="scheduled"
        )
        db.add(shift)
        db.commit()
        
        # Test time exactly at 09:00 Cairo time
        os.environ["SECURITY_POLICY_MODE"] = "enforce"
        os.environ["SECURITY_TIMEZONE"] = "Africa/Cairo"
        get_settings.cache_clear()
        
        # 09:00 Cairo time is 06:00 UTC
        test_now = datetime(2026, 6, 18, 6, 0, tzinfo=timezone.utc)
        decision = is_shift_allowed(db, emp.id, test_now)
        assert decision.allowed is True
        assert decision.code == SECURITY_OK
        
        # 08:50 Cairo time (05:50 UTC) is inside grace before
        test_now_grace = datetime(2026, 6, 18, 5, 50, tzinfo=timezone.utc)
        decision_grace = is_shift_allowed(db, emp.id, test_now_grace)
        assert decision_grace.allowed is True
        
        # 08:49 Cairo time (05:49 UTC) is outside grace before
        test_now_outside = datetime(2026, 6, 18, 5, 49, tzinfo=timezone.utc)
        decision_outside = is_shift_allowed(db, emp.id, test_now_outside)
        assert decision_outside.allowed is False
        assert decision_outside.code == SHIFT_ACCESS_DENIED
    finally:
        db.close()


def test_shift_allowance_other_statuses():
    db = SessionLocal()
    try:
        emp = create_test_employee(db, "emp_status@example.com", "EMP_STATUS")
        
        shift = EmployeeShift(
            employee_id=emp.id,
            work_date=date(2026, 6, 18),
            shift_start=time(9, 0),
            shift_end=time(17, 0),
            status="day_off"
        )
        db.add(shift)
        db.commit()
        
        os.environ["SECURITY_POLICY_MODE"] = "enforce"
        get_settings.cache_clear()
        
        test_now = datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc)
        decision = is_shift_allowed(db, emp.id, test_now)
        assert decision.allowed is False
        assert decision.code == SHIFT_ACCESS_DENIED
        assert "day_off" in decision.message
    finally:
        db.close()


def test_missing_shift_policy_modes():
    db = SessionLocal()
    try:
        emp = create_test_employee(db, "emp_missing@example.com", "EMP_MISSING")
        test_now = datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc)
        
        # Mode off -> allowed
        os.environ["SECURITY_POLICY_MODE"] = "off"
        get_settings.cache_clear()
        assert is_shift_allowed(db, emp.id, test_now).allowed is True
        
        # Mode audit -> allowed, audit_only=True
        os.environ["SECURITY_POLICY_MODE"] = "audit"
        get_settings.cache_clear()
        decision_audit = is_shift_allowed(db, emp.id, test_now)
        assert decision_audit.allowed is True
        assert decision_audit.audit_only is True
        assert decision_audit.code == SHIFT_NOT_FOUND
        
        # Mode enforce -> denied
        os.environ["SECURITY_POLICY_MODE"] = "enforce"
        get_settings.cache_clear()
        decision_enforce = is_shift_allowed(db, emp.id, test_now)
        assert decision_enforce.allowed is False
        assert decision_enforce.code == SHIFT_NOT_FOUND
    finally:
        db.close()


def test_overnight_shift_allowance():
    db = SessionLocal()
    try:
        emp = create_test_employee(db, "emp_overnight@example.com", "EMP_OVERNIGHT")
        
        # Shift from 22:00 to 06:00 next day
        shift = EmployeeShift(
            employee_id=emp.id,
            work_date=date(2026, 6, 18),
            shift_start=time(22, 0),
            shift_end=time(6, 0),
            grace_before_minutes=10,
            grace_after_minutes=10,
            status="scheduled"
        )
        db.add(shift)
        db.commit()
        
        os.environ["SECURITY_POLICY_MODE"] = "enforce"
        os.environ["SECURITY_TIMEZONE"] = "Africa/Cairo"
        get_settings.cache_clear()
        
        # 1. Check time during June 18th 23:00 Cairo time (20:00 UTC) -> allowed
        test_now_1 = datetime(2026, 6, 18, 20, 0, tzinfo=timezone.utc)
        assert is_shift_allowed(db, emp.id, test_now_1).allowed is True
        
        # 2. Check time during June 19th 02:00 Cairo time (June 18th 23:00 UTC) -> allowed
        test_now_2 = datetime(2026, 6, 18, 23, 0, tzinfo=timezone.utc)
        assert is_shift_allowed(db, emp.id, test_now_2).allowed is True
        
        # 3. Check time during June 19th 06:05 Cairo time (03:05 UTC) -> allowed (inside grace)
        test_now_3 = datetime(2026, 6, 19, 3, 5, tzinfo=timezone.utc)
        assert is_shift_allowed(db, emp.id, test_now_3).allowed is True
        
        # 4. Check time during June 19th 06:15 Cairo time (03:15 UTC) -> denied (outside grace)
        test_now_4 = datetime(2026, 6, 19, 3, 15, tzinfo=timezone.utc)
        assert is_shift_allowed(db, emp.id, test_now_4).allowed is False
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 4. Device Policy Tests
# ---------------------------------------------------------------------------

def test_device_policy_missing_id():
    db = SessionLocal()
    try:
        emp = create_test_employee(db, "emp_dev_miss@example.com", "EMP_DEV_MISS")
        
        os.environ["SECURITY_POLICY_MODE"] = "off"
        get_settings.cache_clear()
        assert is_device_trusted(db, emp.id, None).allowed is True
        
        os.environ["SECURITY_POLICY_MODE"] = "enforce"
        get_settings.cache_clear()
        dec = is_device_trusted(db, emp.id, "  ")
        assert dec.allowed is False
        assert dec.code == DEVICE_REQUIRED
    finally:
        db.close()


def test_device_policy_first_device_auto_enroll():
    db = SessionLocal()
    try:
        emp = create_test_employee(db, "emp_dev_first@example.com", "EMP_DEV_FIRST")
        
        os.environ["SECURITY_POLICY_MODE"] = "enforce"
        get_settings.cache_clear()
        
        # Pure validation: device is not trusted yet
        dec_untrusted = is_device_trusted(db, emp.id, "my_device_1")
        assert dec_untrusted.allowed is False
        assert dec_untrusted.code == DEVICE_NOT_TRUSTED
        
        # Explicit auto-enroll
        dev = auto_enroll_first_trusted_device(db, emp.id, "my_device_1")
        assert dev is not None
        assert dev.device_label == "First Trusted Device"
        assert dev.is_trusted is True
        assert dev.approved_at is not None  # Auto-enrolled gets approved_at set
        
        # Verification: now it is trusted
        dec_trusted = is_device_trusted(db, emp.id, "my_device_1")
        assert dec_trusted.allowed is True
        assert dec_trusted.code == SECURITY_OK
        
        # Subsequent auto-enroll returns None (second device doesn't auto-enroll)
        dev_second = auto_enroll_first_trusted_device(db, emp.id, "my_device_2")
        assert dev_second is None
        
        # Subsequent new device -> denied
        dec_sub = is_device_trusted(db, emp.id, "my_device_2")
        assert dec_sub.allowed is False
        assert dec_sub.code == DEVICE_NOT_TRUSTED
    finally:
        db.close()


def test_device_policy_revoked_device():
    db = SessionLocal()
    try:
        emp = create_test_employee(db, "emp_dev_rev@example.com", "EMP_DEV_REV")
        dev = enroll_trusted_device(db, emp.id, "revoked_dev", label="Revoked one")
        dev.is_trusted = False
        dev.revoked_at = datetime.now(timezone.utc)
        dev.revoke_reason = "Lost device"
        db.commit()
        
        os.environ["SECURITY_POLICY_MODE"] = "enforce"
        get_settings.cache_clear()
        
        dec = is_device_trusted(db, emp.id, "revoked_dev")
        assert dec.allowed is False
        assert dec.code == DEVICE_NOT_TRUSTED
        assert "Lost device" in dec.message
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 5. Session Policy Tests
# ---------------------------------------------------------------------------

def test_session_lifecycle():
    db = SessionLocal()
    try:
        emp = create_test_employee(db, "emp_sess@example.com", "EMP_SESS")
        
        os.environ["SECURITY_POLICY_MODE"] = "enforce"
        get_settings.cache_clear()
        
        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        sess = create_user_session(
            db=db,
            employee_id=emp.id,
            device_id="my_sess_device",
            user_agent="Mozilla",
            ip_address="127.0.0.1",
            expires_at=expiry
        )
        
        assert sess.id is not None
        assert len(sess.sid) == 64
        assert len(sess.jti) == 64
        
        # Check active session lookup
        active_sess = get_active_session_by_claims(db, emp.id, sess.sid, sess.jti)
        assert active_sess is not None
        assert active_sess.id == sess.id
        
        # Duplicate active session check
        dec_dup = has_other_active_session(db, emp.id, "my_sess_device")
        assert dec_dup.allowed is False
        assert dec_dup.code == ACTIVE_SESSION_EXISTS
        
        # Revoke session
        revoke_session(db, sess, "User logged out")
        
        # Lookup should fail
        assert get_active_session_by_claims(db, emp.id, sess.sid, sess.jti) is None
    finally:
        db.close()


def test_session_expired():
    db = SessionLocal()
    try:
        emp = create_test_employee(db, "emp_sess_exp@example.com", "EMP_SESS_EXP")
        
        expiry = datetime.now(timezone.utc) - timedelta(seconds=1)
        sess = create_user_session(
            db=db,
            employee_id=emp.id,
            device_id="device",
            user_agent=None,
            ip_address=None,
            expires_at=expiry
        )
        
        active_sess = get_active_session_by_claims(db, emp.id, sess.sid, sess.jti)
        assert active_sess is None  # Should be treated as expired/inactive
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 6. Audit Logging Tests
# ---------------------------------------------------------------------------

def test_audit_logging_sanitization():
    db = SessionLocal()
    try:
        emp = create_test_employee(db, "emp_audit@example.com", "EMP_AUDIT")
        
        decision = SecurityDecision(
            allowed=False,
            code=DEVICE_NOT_TRUSTED,
            message="Access denied: Device ID 'sensitive_raw_device_id_123' is untrusted.",
            metadata={"raw_device_id": "sensitive_raw_device_id_123", "client_ip": "1.2.3.4", "sid": "sensitive_sid_456"}
        )
        
        audit_security_decision(
            db=db,
            decision=decision,
            employee_id=emp.id,
            employee_email=emp.email,
            target="test_target"
        )
        
        # Verify AuditEvent record
        event = db.query(AuditEvent).filter(
            AuditEvent.actor_id == emp.id,
            AuditEvent.action == "SECURITY_POLICY_DENIAL"
        ).order_by(AuditEvent.id.desc()).first()
        
        assert event is not None
        assert event.actor_email == emp.email
        assert event.success is False
        
        # Check that raw device ID and raw session ID are not logged in the event reason, state, or target
        assert "sensitive_raw_device_id_123" not in event.reason
        assert "sensitive_sid_456" not in event.reason
        
        # Check metadata
        import json
        meta = json.loads(event.after_state)
        assert meta["code"] == DEVICE_NOT_TRUSTED
        assert meta["raw_device_id"] == "[REDACTED]"
        assert meta["sid"] == "[REDACTED]"
    finally:
        db.close()


def test_session_create_no_commit_rollback():
    db = SessionLocal()
    try:
        emp = create_test_employee(db, "roll1@example.com", "ROLL1")
        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Create session (this calls create_user_session, which flushes but does not commit)
        sess = create_user_session(
            db=db,
            employee_id=emp.id,
            device_id="roll_dev",
            user_agent="Mozilla",
            ip_address="127.0.0.1",
            expires_at=expiry
        )
        
        # Verify flushed session has an ID and is in session
        assert sess.id is not None
        
        # Rollback transaction
        db.rollback()
        
        # Verify session is not in database anymore
        db_sess = db.query(UserSession).filter(UserSession.id == sess.id).first()
        assert db_sess is None
        
        # Verify audit event is also rolled back
        event = db.query(AuditEvent).filter(
            AuditEvent.actor_id == emp.id,
            AuditEvent.action == "SESSION_CREATED"
        ).first()
        assert event is None
    finally:
        db.close()


def test_session_revoke_no_commit_rollback():
    db = SessionLocal()
    try:
        emp = create_test_employee(db, "roll2@example.com", "ROLL2")
        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Create and commit session
        sess = create_user_session(
            db=db,
            employee_id=emp.id,
            device_id="roll_dev",
            user_agent="Mozilla",
            ip_address="127.0.0.1",
            expires_at=expiry
        )
        db.commit()
        db.refresh(sess)
        
        # Revoke session (flushes but does not commit)
        revoke_session(db, sess, "Rollback test")
        
        # Rollback revocation
        db.rollback()
        db.refresh(sess)
        
        # Verify session is still active
        assert sess.is_active is True
        assert sess.revoked_at is None
        
        # Verify audit event is rolled back
        event = db.query(AuditEvent).filter(
            AuditEvent.action == "SESSION_REVOKED",
            AuditEvent.reason == "Rollback test"
        ).first()
        assert event is None
    finally:
        db.close()
