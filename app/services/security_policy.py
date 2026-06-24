import hashlib
import secrets
import json
from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import EmployeeShift, TrustedDevice, UserSession


# ---------------------------------------------------------------------------
# Decision Shape & Codes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SecurityDecision:
    allowed: bool
    code: str
    message: str
    audit_only: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


SECURITY_OK = "SECURITY_OK"
SECURITY_POLICY_OFF = "SECURITY_POLICY_OFF"
DEVICE_REQUIRED = "DEVICE_REQUIRED"
DEVICE_NOT_TRUSTED = "DEVICE_NOT_TRUSTED"
ACTIVE_SESSION_EXISTS = "ACTIVE_SESSION_EXISTS"
SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
SESSION_REVOKED = "SESSION_REVOKED"
SESSION_EXPIRED = "SESSION_EXPIRED"
SESSION_DEVICE_MISMATCH = "SESSION_DEVICE_MISMATCH"
SHIFT_NOT_FOUND = "SHIFT_NOT_FOUND"
SHIFT_ACCESS_DENIED = "SHIFT_ACCESS_DENIED"
ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"


# ---------------------------------------------------------------------------
# Settings Helpers
# ---------------------------------------------------------------------------

def get_policy_mode() -> str:
    settings = get_settings()
    return settings.SECURITY_POLICY_MODE.lower()


def is_policy_off() -> bool:
    return get_policy_mode() == "off"


def is_policy_audit() -> bool:
    return get_policy_mode() == "audit"


def is_policy_enforce() -> bool:
    return get_policy_mode() == "enforce"


def get_security_timezone() -> ZoneInfo:
    settings = get_settings()
    return ZoneInfo(settings.SECURITY_TIMEZONE)


# ---------------------------------------------------------------------------
# Hash Helpers
# ---------------------------------------------------------------------------

def hash_security_value(value: str) -> str | None:
    if not value or not value.strip():
        return None
    settings = get_settings()
    combined = f"{value}{settings.SECRET_KEY}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


def hash_device_id(device_id: str | None) -> str | None:
    return hash_security_value(device_id)


def hash_user_agent(user_agent: str | None) -> str | None:
    return hash_security_value(user_agent)


# ---------------------------------------------------------------------------
# Shift Helpers
# ---------------------------------------------------------------------------

def check_shift_time_allowance(shift: EmployeeShift, local_now: datetime) -> bool:
    if shift.status != "scheduled":
        return False
        
    if not shift.shift_start or not shift.shift_end:
        return False

    tz = local_now.tzinfo
    shift_start_dt = datetime.combine(shift.work_date, shift.shift_start).replace(tzinfo=tz)
    
    if shift.shift_end <= shift.shift_start:
        shift_end_dt = datetime.combine(shift.work_date + timedelta(days=1), shift.shift_end).replace(tzinfo=tz)
    else:
        shift_end_dt = datetime.combine(shift.work_date, shift.shift_end).replace(tzinfo=tz)

    grace_before = timedelta(minutes=shift.grace_before_minutes)
    grace_after = timedelta(minutes=shift.grace_after_minutes)

    allowed_start = shift_start_dt - grace_before
    allowed_end = shift_end_dt + grace_after

    return allowed_start <= local_now <= allowed_end


def get_employee_shift_for_now(db: Session, employee_id: int, now: datetime | None = None) -> EmployeeShift | None:
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    tz = get_security_timezone()
    local_now = now.astimezone(tz)
    
    today_date = local_now.date()
    yesterday_date = today_date - timedelta(days=1)
    
    shifts = db.query(EmployeeShift).filter(
        EmployeeShift.employee_id == employee_id,
        EmployeeShift.work_date.in_([yesterday_date, today_date])
    ).all()
    
    for shift in shifts:
        if check_shift_time_allowance(shift, local_now):
            return shift
            
    for shift in shifts:
        if shift.work_date == today_date:
            return shift
            
    if shifts:
        return shifts[0]
        
    return None


def is_shift_allowed(db: Session, employee_id: int, now: datetime | None = None) -> SecurityDecision:
    mode = get_policy_mode()
    if mode == "off":
        return SecurityDecision(allowed=True, code=SECURITY_POLICY_OFF, message="Security policy is disabled.")

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    tz = get_security_timezone()
    local_now = now.astimezone(tz)
    
    today_date = local_now.date()
    yesterday_date = today_date - timedelta(days=1)
    
    shifts = db.query(EmployeeShift).filter(
        EmployeeShift.employee_id == employee_id,
        EmployeeShift.work_date.in_([yesterday_date, today_date])
    ).all()
    
    active_shift = None
    for shift in shifts:
        if shift.status == "scheduled" and check_shift_time_allowance(shift, local_now):
            active_shift = shift
            break
            
    if active_shift:
        return SecurityDecision(
            allowed=True,
            code=SECURITY_OK,
            message="Access allowed by shift policy.",
            metadata={"shift_id": active_shift.id, "work_date": str(active_shift.work_date)}
        )

    today_shift = next((s for s in shifts if s.work_date == today_date), None)
    yesterday_shift = next((s for s in shifts if s.work_date == yesterday_date), None)
    target_shift = today_shift or yesterday_shift
    
    if target_shift:
        allowed = (mode == "audit")
        if target_shift.status in ("day_off", "leave", "absent"):
            return SecurityDecision(
                allowed=allowed,
                code=SHIFT_ACCESS_DENIED,
                message=f"Access denied: Employee shift status is '{target_shift.status}'.",
                audit_only=(mode == "audit"),
                metadata={"shift_id": target_shift.id, "status": target_shift.status, "work_date": str(target_shift.work_date)}
            )
        else:
            return SecurityDecision(
                allowed=allowed,
                code=SHIFT_ACCESS_DENIED,
                message="Access denied: Current time is outside shift hours.",
                audit_only=(mode == "audit"),
                metadata={"shift_id": target_shift.id, "status": target_shift.status, "work_date": str(target_shift.work_date)}
            )
            
    allowed = (mode == "audit")
    return SecurityDecision(
        allowed=allowed,
        code=SHIFT_NOT_FOUND,
        message="Access denied: No shift scheduled for this date.",
        audit_only=(mode == "audit")
    )


# ---------------------------------------------------------------------------
# Device Helpers
# ---------------------------------------------------------------------------

def get_trusted_device(db: Session, employee_id: int, device_id: str | None) -> TrustedDevice | None:
    if not device_id or not device_id.strip():
        return None
    h = hash_device_id(device_id)
    return db.query(TrustedDevice).filter(
        TrustedDevice.employee_id == employee_id,
        TrustedDevice.device_id_hash == h
    ).first()


def enroll_trusted_device(
    db: Session,
    employee_id: int,
    device_id: str,
    user_agent: str | None = None,
    approved_by_id: int | None = None,
    label: str | None = None,
) -> TrustedDevice:
    dev_hash = hash_device_id(device_id)
    ua_hash = hash_user_agent(user_agent)
    now = datetime.now(timezone.utc)
    
    # Auto-enrolled first trusted devices get approved_at = now
    is_first = (label == "First Trusted Device" or "first" in (label or "").lower())
    approved_at = now if (approved_by_id or is_first) else None
    
    device = TrustedDevice(
        employee_id=employee_id,
        device_id_hash=dev_hash,
        user_agent_hash=ua_hash,
        device_label=label or "Auto-enrolled Device",
        first_seen_at=now,
        last_seen_at=now,
        approved_at=approved_at,
        approved_by_id=approved_by_id,
        is_trusted=True
    )
    db.add(device)
    db.flush()
    return device


def is_device_trusted(db: Session, employee_id: int, device_id: str | None) -> SecurityDecision:
    mode = get_policy_mode()
    if mode == "off":
        return SecurityDecision(allowed=True, code=SECURITY_POLICY_OFF, message="Security policy is disabled.")
        
    if not device_id or not device_id.strip():
        allowed = (mode == "audit")
        return SecurityDecision(
            allowed=allowed,
            code=DEVICE_REQUIRED,
            message="Access denied: Device ID is required.",
            audit_only=(mode == "audit")
        )
        
    dev = get_trusted_device(db, employee_id, device_id)
    if not dev:
        allowed = (mode == "audit")
        return SecurityDecision(
            allowed=allowed,
            code=DEVICE_NOT_TRUSTED,
            message="Access denied: Device is not trusted.",
            audit_only=(mode == "audit")
        )
            
    if not dev.is_trusted or dev.revoked_at is not None:
        allowed = (mode == "audit")
        return SecurityDecision(
            allowed=allowed,
            code=DEVICE_NOT_TRUSTED,
            message=f"Access denied: Device has been revoked. Reason: {dev.revoke_reason or 'No reason provided'}",
            audit_only=(mode == "audit"),
            metadata={"device_id": dev.id}
        )
        
    dev.last_seen_at = datetime.now(timezone.utc)
    
    return SecurityDecision(
        allowed=True,
        code=SECURITY_OK,
        message="Device is trusted.",
        metadata={"device_id": dev.id}
    )


def auto_enroll_first_trusted_device(
    db: Session,
    employee_id: int,
    device_id: str,
    user_agent: str | None = None,
    label: str = "First Trusted Device",
) -> TrustedDevice | None:
    existing_count = db.query(TrustedDevice).filter(TrustedDevice.employee_id == employee_id).count()
    if existing_count == 0:
        dev = enroll_trusted_device(
            db=db,
            employee_id=employee_id,
            device_id=device_id,
            user_agent=user_agent,
            label=label
        )
        audit_decision = SecurityDecision(
            allowed=True,
            code="TRUSTED_DEVICE_ENROLLED",
            message=f"Auto-enrolled first trusted device for employee {employee_id}."
        )
        audit_security_decision(db, audit_decision, employee_id=employee_id)
        return dev
    return None


# ---------------------------------------------------------------------------
# Session Helpers
# ---------------------------------------------------------------------------

def is_session_active(session: UserSession, now: datetime | None = None) -> bool:
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
        
    expires_at = session.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
        
    return session.is_active and session.revoked_at is None and expires_at > now


def get_active_session_by_claims(db: Session, employee_id: int, sid: str | None, jti: str | None) -> UserSession | None:
    if not sid or not jti:
        return None
    now = datetime.now(timezone.utc)
    session = db.query(UserSession).filter(
        UserSession.employee_id == employee_id,
        UserSession.sid == sid,
        UserSession.jti == jti
    ).first()
    if session and is_session_active(session, now):
        return session
    return None


def get_active_session_for_employee(db: Session, employee_id: int) -> UserSession | None:
    now = datetime.now(timezone.utc)
    sessions = db.query(UserSession).filter(
        UserSession.employee_id == employee_id,
        UserSession.is_active == True,
        UserSession.revoked_at == None
    ).all()
    for session in sessions:
        if is_session_active(session, now):
            return session
    return None


def has_other_active_session(db: Session, employee_id: int, device_id: str | None = None) -> SecurityDecision:
    mode = get_policy_mode()
    if mode == "off":
        return SecurityDecision(allowed=True, code=SECURITY_POLICY_OFF, message="Security policy is disabled.")
        
    active_session = get_active_session_for_employee(db, employee_id)
    if active_session:
        allowed = (mode == "audit")
        return SecurityDecision(
            allowed=allowed,
            code=ACTIVE_SESSION_EXISTS,
            message="Access denied: An active session already exists for this employee.",
            audit_only=(mode == "audit"),
            metadata={"session_id": active_session.id}
        )
        
    return SecurityDecision(
        allowed=True,
        code=SECURITY_OK,
        message="No other active session exists."
    )


def create_user_session(
    db: Session,
    employee_id: int,
    device_id: str | None,
    user_agent: str | None,
    ip_address: str | None,
    expires_at: datetime,
    trusted_device_id: int | None = None,
) -> UserSession:
    sid = secrets.token_hex(32)
    jti = secrets.token_hex(32)
    dev_hash = hash_device_id(device_id)
    ua_hash = hash_user_agent(user_agent)
    
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
        
    if not trusted_device_id and device_id:
        trusted_dev = get_trusted_device(db, employee_id, device_id)
        if trusted_dev:
            trusted_device_id = trusted_dev.id
            
    session = UserSession(
        employee_id=employee_id,
        trusted_device_id=trusted_device_id,
        sid=sid,
        jti=jti,
        device_id_hash=dev_hash,
        device_fingerprint_hash=None,
        user_agent_hash=ua_hash,
        ip_address=ip_address,
        issued_at=now,
        last_seen_at=now,
        expires_at=expires_at,
        is_active=True
    )
    db.add(session)
    db.flush()
    
    target_str = f"UserSession id={session.id}; employee_id={employee_id}" if session.id else f"UserSession employee_id={employee_id}"
    audit_decision = SecurityDecision(
        allowed=True,
        code="SESSION_CREATED",
        message=f"Session created for employee {employee_id}."
    )
    audit_security_decision(db, audit_decision, employee_id=employee_id, target=target_str)
    
    return session


def revoke_session(db: Session, session: UserSession, reason: str) -> UserSession:
    session.is_active = False
    session.revoked_at = datetime.now(timezone.utc)
    session.revoke_reason = reason
    db.flush()
    
    target_str = f"UserSession id={session.id}; employee_id={session.employee_id}" if session.id else f"UserSession employee_id={session.employee_id}"
    audit_decision = SecurityDecision(
        allowed=True,
        code="SESSION_REVOKED",
        message=f"Session revoked. Reason: {reason}"
    )
    audit_security_decision(db, audit_decision, employee_id=session.employee_id, target=target_str, reason=reason)
    
    return session


def revoke_current_session(db: Session, employee_id: int, sid: str, reason: str = "logout") -> UserSession | None:
    session = db.query(UserSession).filter(
        UserSession.employee_id == employee_id,
        UserSession.sid == sid
    ).first()

    if session:
        if not session.is_active or session.revoked_at is not None:
            metadata = {
                "reason": reason,
                "policy_mode": get_policy_mode(),
                "session_found": True,
                "already_revoked": True,
            }
            target_str = f"UserSession id={session.id}; employee_id={employee_id}"
            audit_decision = SecurityDecision(
                allowed=True,
                code="SESSION_REVOKED",
                message=f"Session already revoked: {reason}.",
                metadata=metadata
            )
            audit_security_decision(db, audit_decision, employee_id=employee_id, target=target_str, reason=reason)
            return session

        session.is_active = False
        session.revoked_at = datetime.now(timezone.utc)
        session.revoke_reason = reason
        db.flush()

        metadata = {
            "reason": reason,
            "policy_mode": get_policy_mode(),
            "session_found": True,
            "already_revoked": False,
        }
        target_str = f"UserSession id={session.id}; employee_id={employee_id}"
        audit_decision = SecurityDecision(
            allowed=True,
            code="SESSION_REVOKED",
            message=f"Session revoked: {reason}.",
            metadata=metadata
        )
        audit_security_decision(db, audit_decision, employee_id=employee_id, target=target_str, reason=reason)
        return session
    else:
        metadata = {
            "reason": reason,
            "policy_mode": get_policy_mode(),
            "session_found": False,
            "already_revoked": False,
        }
        audit_decision = SecurityDecision(
            allowed=True,
            code="SESSION_REVOKED",
            message="Session revocation requested but session not found.",
            metadata=metadata
        )
        audit_security_decision(db, audit_decision, employee_id=employee_id, target="UserSession", reason=reason)
        return None


def validate_request_session(
    db: Session,
    employee_id: int,
    sid: str | None,
    jti: str | None,
    device_id_hash: str | None = None
) -> SecurityDecision:
    mode = get_policy_mode()
    if mode == "off":
        return SecurityDecision(allowed=True, code=SECURITY_POLICY_OFF, message="Security policy is disabled.")

    if not sid or not jti:
        allowed = (mode == "audit")
        return SecurityDecision(
            allowed=allowed,
            code="SESSION_CLAIMS_MISSING",
            message="Session claims (sid/jti) are missing from token.",
            audit_only=(mode == "audit")
        )

    session = db.query(UserSession).filter(
        UserSession.employee_id == employee_id,
        UserSession.sid == sid,
        UserSession.jti == jti
    ).first()

    if not session:
        allowed = (mode == "audit")
        return SecurityDecision(
            allowed=allowed,
            code=SESSION_NOT_FOUND,
            message="Session not found in server-side session store.",
            audit_only=(mode == "audit")
        )

    if not session.is_active or session.revoked_at is not None:
        allowed = (mode == "audit")
        return SecurityDecision(
            allowed=allowed,
            code=SESSION_REVOKED,
            message=f"Session is inactive or revoked. Reason: {session.revoke_reason or 'No reason provided'}",
            audit_only=(mode == "audit"),
            metadata={"session_id": session.id}
        )

    now = datetime.now(timezone.utc)
    expires_at = session.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        allowed = (mode == "audit")
        return SecurityDecision(
            allowed=allowed,
            code=SESSION_EXPIRED,
            message="Session has expired.",
            audit_only=(mode == "audit"),
            metadata={"session_id": session.id}
        )

    if not device_id_hash or session.device_id_hash != device_id_hash:
        allowed = (mode == "audit")
        return SecurityDecision(
            allowed=allowed,
            code=SESSION_DEVICE_MISMATCH,
            message="Token device hash mismatch or missing from session token.",
            audit_only=(mode == "audit"),
            metadata={"session_id": session.id}
        )

    return SecurityDecision(
        allowed=True,
        code=SECURITY_OK,
        message="Session validation passed.",
        metadata={"session_id": session.id}
    )


def touch_session_last_seen(db: Session, session: UserSession, now: datetime | None = None) -> None:
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    session.last_seen_at = now
    db.flush()


def get_trusted_device_by_hash(db: Session, employee_id: int, device_id_hash: str | None) -> TrustedDevice | None:
    if not device_id_hash:
        return None
    return db.query(TrustedDevice).filter(
        TrustedDevice.employee_id == employee_id,
        TrustedDevice.device_id_hash == device_id_hash
    ).first()


def validate_protected_access_policy(
    db: Session,
    employee_id: int,
    session: UserSession | None,
    device_id_hash: str | None,
    now: datetime | None = None
) -> list[SecurityDecision]:
    mode = get_policy_mode()
    if mode == "off":
        return [SecurityDecision(allowed=True, code=SECURITY_POLICY_OFF, message="Security policy is disabled.")]

    decisions = []

    # 1. Shift check
    shift_decision = is_shift_allowed(db, employee_id, now=now)
    if not shift_decision.allowed or shift_decision.code not in (SECURITY_OK, SECURITY_POLICY_OFF):
        decisions.append(shift_decision)

    # 2. Device trust check
    device_ok = False
    if session and device_id_hash and device_id_hash == session.device_id_hash:
        dev = get_trusted_device_by_hash(db, employee_id, device_id_hash)
        if (dev and dev.employee_id == employee_id 
                and dev.device_id_hash == device_id_hash 
                and dev.is_trusted 
                and dev.revoked_at is None):
            device_ok = True

    if not device_ok:
        allowed = (mode == "audit")
        device_decision = SecurityDecision(
            allowed=allowed,
            code=DEVICE_NOT_TRUSTED,
            message="Access denied: Device is not trusted.",
            audit_only=(mode == "audit"),
            metadata={"session_id": session.id if session else None}
        )
        decisions.append(device_decision)

    return decisions


# ---------------------------------------------------------------------------
# Audit Helper
# ---------------------------------------------------------------------------

def add_security_audit_event(
    db: Session,
    action: str,
    actor_id: int | None = None,
    actor_email: str | None = None,
    target: str | None = None,
    after_state: str | None = None,
    reason: str | None = None,
    success: bool = True
) -> Any:
    from app.models import AuditEvent
    event = AuditEvent(
        actor_id=actor_id,
        actor_email=actor_email,
        action=action,
        target=target,
        after_state=after_state,
        reason=reason,
        success=success
    )
    db.add(event)
    db.flush()
    return event


def audit_security_decision(
    db: Session,
    decision: SecurityDecision,
    employee_id: int | None = None,
    employee_email: str | None = None,
    target: str | None = None,
    reason: str | None = None,
) -> None:
    action = "SECURITY_POLICY_DENIAL" if not decision.allowed else "SECURITY_POLICY_AUDIT"
    if decision.code == "SESSION_CREATED":
        action = "SESSION_CREATED"
    elif decision.code == "SESSION_REVOKED":
        action = "SESSION_REVOKED"
    elif decision.code == "TRUSTED_DEVICE_ENROLLED":
        action = "TRUSTED_DEVICE_ENROLLED"

    # Identify any sensitive values to redact
    redact_values = set()
    sensitive_keys = {
        "device_id", "raw_device_id", "token", "otp", "password", 
        "national_id", "transcript", "code_challenge", "secret", 
        "credentials", "session_token", "sid", "jti", "jwt"
    }
    
    if decision.metadata:
        for k, v in decision.metadata.items():
            if k.lower() in sensitive_keys and isinstance(v, str) and v.strip():
                redact_values.add(v)

    # Helper to redact sensitive values from any string
    def redact(text: str | None) -> str | None:
        if not text:
            return text
        for val in redact_values:
            text = text.replace(val, "[REDACTED]")
        return text

    # Build sanitized metadata dict
    metadata_dict = {
        "code": decision.code,
        "message": redact(decision.message),
        "audit_only": decision.audit_only,
    }
    if decision.metadata:
        for k, v in decision.metadata.items():
            if k.lower() not in sensitive_keys:
                if isinstance(v, str):
                    metadata_dict[k] = redact(v)
                else:
                    metadata_dict[k] = v
            else:
                metadata_dict[k] = "[REDACTED]"
                
    metadata_json = json.dumps(metadata_dict)
    raw_reason = reason or decision.message
    sanitized_reason = redact(raw_reason)
    
    add_security_audit_event(
        db=db,
        action=action,
        actor_id=employee_id,
        actor_email=employee_email,
        target=target,
        after_state=metadata_json,
        reason=sanitized_reason,
        success=decision.allowed
    )


def revoke_session_by_id(
    db: Session,
    session_id: int,
    reason: str,
    actor_id: int | None = None,
    actor_email: str | None = None
) -> UserSession | None:
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not session:
        return None

    already_revoked = not session.is_active or session.revoked_at is not None

    if not already_revoked:
        session.is_active = False
        session.revoked_at = datetime.now(timezone.utc)
        session.revoke_reason = reason
        db.flush()

    target_str = f"UserSession id={session.id}; employee_id={session.employee_id}"
    after_state = {
        "code": "SESSION_REVOKED",
        "message": "Session already revoked." if already_revoked else "Session revoked.",
        "session_id": session.id,
        "employee_id": session.employee_id,
        "already_revoked": already_revoked,
        "reason": reason
    }

    add_security_audit_event(
        db=db,
        action="SESSION_REVOKED",
        actor_id=actor_id if actor_id is not None else session.employee_id,
        actor_email=actor_email,
        target=target_str,
        after_state=json.dumps(after_state),
        reason=reason,
        success=True
    )
    return session


def approve_device_by_id(db: Session, device_id: int, actor_id: int, reason: str = "Admin approved device") -> TrustedDevice | None:
    dev = db.query(TrustedDevice).filter(TrustedDevice.id == device_id).first()
    if not dev:
        return None

    dev.is_trusted = True
    dev.approved_at = datetime.now(timezone.utc)
    dev.approved_by_id = actor_id
    dev.revoked_at = None
    dev.revoke_reason = None
    db.flush()

    after_state = {
        "is_trusted": True,
        "approved_by_id": actor_id,
        "device_id": dev.id,
        "employee_id": dev.employee_id,
        "reason": reason
    }
    
    add_security_audit_event(
        db=db,
        action="DEVICE_APPROVED",
        actor_id=actor_id,
        target=f"TrustedDevice id={dev.id}; employee_id={dev.employee_id}",
        after_state=json.dumps(after_state),
        reason=reason,
        success=True
    )
    return dev


def revoke_device_by_id(db: Session, device_id: int, reason: str, actor_id: int | None = None) -> TrustedDevice | None:
    dev = db.query(TrustedDevice).filter(TrustedDevice.id == device_id).first()
    if not dev:
        return None

    already_revoked = dev.revoked_at is not None and not dev.is_trusted

    if not already_revoked:
        dev.is_trusted = False
        dev.revoked_at = datetime.now(timezone.utc)
        dev.revoke_reason = reason
        db.flush()

    after_state = {
        "is_trusted": False,
        "revoked_at": str(dev.revoked_at),
        "revoke_reason": reason,
        "device_id": dev.id,
        "employee_id": dev.employee_id,
        "already_revoked": already_revoked,
        "reason": reason
    }

    add_security_audit_event(
        db=db,
        action="DEVICE_REVOKED",
        actor_id=actor_id,
        target=f"TrustedDevice id={dev.id}; employee_id={dev.employee_id}",
        after_state=json.dumps(after_state),
        reason=reason,
        success=True
    )
    return dev


class WebSocketSecurityError(Exception):
    def __init__(
        self,
        code: int,
        message: str,
        *,
        employee_id: int | None = None,
        reason_code: str | None = None,
        audit_only: bool = False,
        session_id: int | None = None,
    ):
        self.code = code
        self.message = message
        self.employee_id = employee_id
        self.reason_code = reason_code
        self.audit_only = audit_only
        self.session_id = session_id
        super().__init__(message)


@dataclass
class WebSocketSecurityContext:
    employee_id: int
    sid: str | None
    jti: str | None
    device_id_hash: str | None
    last_validated_at: datetime
    legacy_missing_claims: bool = False


def _serialize_websocket_close_metadata(
    *,
    close_code: int,
    message: str,
    reason_code: str | None = None,
    employee_id: int | None = None,
    session_id: int | None = None,
    audit_only: bool = False,
) -> str:
    metadata: dict[str, Any] = {
        "close_code": close_code,
        "message": message,
        "target": "websocket",
        "audit_only": audit_only,
    }
    if reason_code:
        metadata["reason_code"] = reason_code
    if employee_id is not None:
        metadata["employee_id"] = employee_id
    if session_id is not None:
        metadata["session_id"] = session_id
    return json.dumps(metadata)


def record_websocket_security_close(
    db: Session,
    *,
    close_code: int,
    message: str,
    employee_id: int | None = None,
    reason_code: str | None = None,
    audit_only: bool = False,
    session_id: int | None = None,
) -> None:
    after_state = _serialize_websocket_close_metadata(
        close_code=close_code,
        message=message,
        reason_code=reason_code,
        employee_id=employee_id,
        session_id=session_id,
        audit_only=audit_only,
    )
    try:
        add_security_audit_event(
            db=db,
            action="WEBSOCKET_SECURITY_CLOSE",
            actor_id=employee_id,
            target="websocket",
            after_state=after_state,
            reason=message,
            success=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        try:
            from app.models import AuditEvent

            bind = db.get_bind()
            with bind.begin() as connection:
                connection.execute(
                    AuditEvent.__table__.insert().values(
                        actor_id=employee_id,
                        action="WEBSOCKET_SECURITY_CLOSE",
                        target="websocket",
                        after_state=after_state,
                        reason=message,
                        success=False,
                        created_at=datetime.now(timezone.utc),
                    )
                )
        except Exception:
            # Best-effort only: if the database itself is unavailable, the close still proceeds.
            pass


def validate_websocket_security_context(db: Session, token: str | None) -> tuple[Any, WebSocketSecurityContext]:
    """
    Validates token, session status, shift access, and trusted device state for WebSockets.
    Returns both the employee and a WebSocketSecurityContext.
    Raises WebSocketSecurityError if validation fails in enforce mode.
    """
    if not token:
        raise WebSocketSecurityError(4401, "Auth token is missing", reason_code="AUTH_TOKEN_MISSING")

    from fastapi import HTTPException
    from app.models import Employee
    from app.routers.auth import get_user_from_token
    try:
        user = get_user_from_token(token, db)
    except HTTPException as he:
        code = 4403 if he.status_code == 403 else 4401
        raise WebSocketSecurityError(code, he.detail, reason_code="TOKEN_REJECTED")
    except Exception:
        raise WebSocketSecurityError(4401, "Invalid token", reason_code="INVALID_TOKEN")

    policy_mode = get_policy_mode()
    if policy_mode == "off":
        context = WebSocketSecurityContext(
            employee_id=user.id,
            sid=None,
            jti=None,
            device_id_hash=None,
            last_validated_at=datetime.now(timezone.utc),
            legacy_missing_claims=False
        )
        return user, context

    payload = getattr(user, "jwt_payload", {})
    sid = payload.get("sid")
    jti = payload.get("jti")
    device_id_hash = payload.get("device_id_hash")

    # 1. Validate request session
    decision = validate_request_session(
        db=db,
        employee_id=user.id,
        sid=sid,
        jti=jti,
        device_id_hash=device_id_hash
    )

    if not decision.allowed:
        audit_security_decision(db, decision, employee_id=user.id, target="websocket")
        try:
            db.commit()
        except Exception:
            db.rollback()

        code = 4403 if decision.code == "SESSION_DEVICE_MISMATCH" else 4401
        raise WebSocketSecurityError(
            code,
            decision.message,
            employee_id=user.id,
            reason_code=decision.code,
            audit_only=decision.audit_only,
            session_id=decision.metadata.get("session_id"),
        )

    # In audit mode, if sid or jti is missing, log the session-claims audit event.
    # Do not also run device/shift validation with a fake missing session.
    if not sid or not jti:
        if decision.code not in (SECURITY_OK, SECURITY_POLICY_OFF):
            audit_security_decision(db, decision, employee_id=user.id, target="websocket")
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise WebSocketSecurityError(
                1011,
                "Security validation commit failed",
                employee_id=user.id,
                reason_code="SECURITY_VALIDATION_COMMIT_FAILED",
            )
        
        context = WebSocketSecurityContext(
            employee_id=user.id,
            sid=None,
            jti=None,
            device_id_hash=device_id_hash,
            last_validated_at=datetime.now(timezone.utc),
            legacy_missing_claims=True
        )
        return user, context

    if decision.code not in (SECURITY_OK, SECURITY_POLICY_OFF):
        audit_security_decision(db, decision, employee_id=user.id, target="websocket")

    # 2. Retrieve session
    session = db.query(UserSession).filter(
        UserSession.employee_id == user.id,
        UserSession.sid == sid,
        UserSession.jti == jti
    ).first()

    # 3. Shift and device revalidation
    decisions = validate_protected_access_policy(
        db=db,
        employee_id=user.id,
        session=session,
        device_id_hash=device_id_hash
    )

    for dec in decisions:
        if not dec.allowed:
            audit_security_decision(db, dec, employee_id=user.id, target="websocket")
            try:
                db.commit()
            except Exception:
                db.rollback()
            
            raise WebSocketSecurityError(
                4403,
                dec.message,
                employee_id=user.id,
                reason_code=dec.code,
                audit_only=dec.audit_only,
                session_id=session.id if session else None,
            )

    # Log audit warnings for allowed violations in audit mode
    for dec in decisions:
        if dec.code not in (SECURITY_OK, SECURITY_POLICY_OFF):
            audit_security_decision(db, dec, employee_id=user.id, target="websocket")

    # 4. Touch last_seen_at if session is valid and exists
    if session and decision.code == SECURITY_OK:
        touch_session_last_seen(db, session)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise WebSocketSecurityError(
            1011,
            "Security validation commit failed",
            employee_id=user.id,
            reason_code="SECURITY_VALIDATION_COMMIT_FAILED",
            session_id=session.id if session else None,
        )

    context = WebSocketSecurityContext(
        employee_id=user.id,
        sid=sid,
        jti=jti,
        device_id_hash=device_id_hash,
        last_validated_at=datetime.now(timezone.utc),
        legacy_missing_claims=False
    )
    return user, context


def validate_websocket_security(db: Session, token: str | None) -> Any:
    """
    Validates token, session status, shift access, and trusted device state for WebSockets.
    Raises WebSocketSecurityError if validation fails in enforce mode.
    """
    user, _ = validate_websocket_security_context(db, token)
    return user


def revalidate_websocket_security(
    db: Session,
    context: WebSocketSecurityContext,
    *,
    force: bool = False,
) -> None:
    """
    Performs mid-connection WebSocket security revalidation.
    """
    now = datetime.now(timezone.utc)
    if not force:
        settings = get_settings()
        elapsed = (now - context.last_validated_at).total_seconds()
        if elapsed < settings.SECURITY_WS_REVALIDATION_INTERVAL_SECONDS:
            return

    policy_mode = get_policy_mode()
    if policy_mode == "off":
        context.last_validated_at = now
        return

    if context.legacy_missing_claims:
        context.last_validated_at = now
        return

    # 1. Validate session
    decision = validate_request_session(
        db=db,
        employee_id=context.employee_id,
        sid=context.sid,
        jti=context.jti,
        device_id_hash=context.device_id_hash
    )

    if not decision.allowed:
        audit_security_decision(db, decision, employee_id=context.employee_id, target="websocket")
        try:
            db.commit()
        except Exception:
            db.rollback()
        
        code = 4403 if decision.code == "SESSION_DEVICE_MISMATCH" else 4401
        raise WebSocketSecurityError(
            code,
            decision.message,
            employee_id=context.employee_id,
            reason_code=decision.code,
            audit_only=decision.audit_only,
            session_id=decision.metadata.get("session_id"),
        )

    if decision.code not in (SECURITY_OK, SECURITY_POLICY_OFF):
        audit_security_decision(db, decision, employee_id=context.employee_id, target="websocket")

    # 2. Retrieve session
    session = db.query(UserSession).filter(
        UserSession.employee_id == context.employee_id,
        UserSession.sid == context.sid,
        UserSession.jti == context.jti
    ).first()

    # 3. Shift and device revalidation
    decisions = validate_protected_access_policy(
        db=db,
        employee_id=context.employee_id,
        session=session,
        device_id_hash=context.device_id_hash,
        now=now
    )

    for dec in decisions:
        if not dec.allowed:
            audit_security_decision(db, dec, employee_id=context.employee_id, target="websocket")
            try:
                db.commit()
            except Exception:
                db.rollback()
            
            raise WebSocketSecurityError(
                4403,
                dec.message,
                employee_id=context.employee_id,
                reason_code=dec.code,
                audit_only=dec.audit_only,
                session_id=session.id if session else None,
            )

    # Log audit warnings for allowed violations in audit mode
    for dec in decisions:
        if dec.code not in (SECURITY_OK, SECURITY_POLICY_OFF):
            audit_security_decision(db, dec, employee_id=context.employee_id, target="websocket")

    # 4. Touch last_seen_at if session is valid and exists
    if session and decision.code == SECURITY_OK:
        touch_session_last_seen(db, session, now)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise WebSocketSecurityError(
            1011,
            "Security validation commit failed",
            employee_id=context.employee_id,
            reason_code="SECURITY_VALIDATION_COMMIT_FAILED",
            session_id=session.id if session else None,
        )

    context.last_validated_at = now
