from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import AuditEvent


SENSITIVE_AUDIT_KEYS = {
    "access_token",
    "device_id",
    "device_id_hash",
    "jwt",
    "jti",
    "otp",
    "password",
    "raw_device_id",
    "secret",
    "session_token",
    "sid",
    "token",
}

SENSITIVE_TOKEN_PATTERN = re.compile(
    r"(?i)\b(sid|jti|jwt|device_id|raw_device_id|device_id_hash|access_token|refresh_token|session_token|token)\b\s*[:=]\s*([^\s,;\"']+)"
)
JWT_PATTERN = re.compile(r"\beyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b")
HEX_HASH_PATTERN = re.compile(r"\b[a-fA-F0-9]{64}\b")
EMPLOYEE_ID_PATTERN = re.compile(r"(?i)\bemployee_id\s*[:=]\s*(\d+)\b")


def _redact_text(value: str | None) -> str | None:
    if value is None:
        return None

    redacted = value
    redacted = SENSITIVE_TOKEN_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
    redacted = JWT_PATTERN.sub("[REDACTED]", redacted)
    redacted = HEX_HASH_PATTERN.sub("[REDACTED]", redacted)
    return redacted


def _redact_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, inner_value in value.items():
            if key.lower() in SENSITIVE_AUDIT_KEYS:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact_json_value(inner_value)
        return redacted
    if isinstance(value, list):
        return [_redact_json_value(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _safe_stringified_state(raw_state: str | None) -> str | None:
    if not raw_state:
        return None
    try:
        parsed = json.loads(raw_state)
    except (TypeError, ValueError, json.JSONDecodeError):
        return _redact_text(raw_state)
    return json.dumps(_redact_json_value(parsed), ensure_ascii=False)


def _extract_subject_employee_id(event: AuditEvent) -> int | None:
    candidates = [event.target, event.after_state, event.before_state, event.reason]
    for candidate in candidates:
        if not candidate:
            continue

        match = EMPLOYEE_ID_PATTERN.search(candidate)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass

        try:
            parsed = json.loads(candidate)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue

        if isinstance(parsed, dict):
            for key in ("employee_id", "employeeId", "employee"):
                value = parsed.get(key)
                if isinstance(value, int):
                    return value
                if isinstance(value, str) and value.isdigit():
                    return int(value)
                if isinstance(value, dict):
                    nested_id = value.get("id")
                    if isinstance(nested_id, int):
                        return nested_id
                    if isinstance(nested_id, str) and nested_id.isdigit():
                        return int(nested_id)
    return None


def _summarize_event(event: AuditEvent, safe_after_state: str | None) -> str:
    if safe_after_state:
        try:
            parsed = json.loads(safe_after_state)
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = None
        if isinstance(parsed, dict):
            for key in ("message", "reason", "summary"):
                value = parsed.get(key)
                if isinstance(value, str) and value.strip():
                    return _redact_text(value) or value

    if event.reason and event.reason.strip():
        return _redact_text(event.reason) or event.reason

    if event.action == "SESSION_REVOKED":
        return "Session revoked"
    if event.action == "DEVICE_REVOKED":
        return "Device revoked"
    if event.action == "DEVICE_APPROVED":
        return "Device approved"
    if event.action == "WEBSOCKET_SECURITY_CLOSE":
        return "WebSocket security close"
    if event.action.startswith("SHIFT_"):
        return event.action.replace("_", " ").title()
    if event.action == "SECURITY_POLICY_DENIAL":
        return "Security policy denial"
    if event.action == "SECURITY_POLICY_AUDIT":
        return "Security policy audit"
    return event.action.replace("_", " ").title()


def get_security_summary(db: Session, hours: int = 24) -> dict:
    """
    Aggregates security observability counts for a given time window (in hours).
    Returns only non-sensitive aggregate counts.
    """
    if not (1 <= hours <= 720):  # Bounded to max 30 days
        raise ValueError("Time window must be between 1 and 720 hours.")

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)

    # Denied Logins (target='login', action='SECURITY_POLICY_DENIAL')
    denied_logins = db.query(AuditEvent).filter(
        AuditEvent.created_at >= since,
        AuditEvent.action == "SECURITY_POLICY_DENIAL",
        AuditEvent.target == "login"
    ).count()

    # Denied Protected Requests (target='protected_request', action='SECURITY_POLICY_DENIAL')
    denied_protected_requests = db.query(AuditEvent).filter(
        AuditEvent.created_at >= since,
        AuditEvent.action == "SECURITY_POLICY_DENIAL",
        AuditEvent.target == "protected_request"
    ).count()

    audit_policy_violations = db.query(AuditEvent).filter(
        AuditEvent.created_at >= since,
        AuditEvent.action == "SECURITY_POLICY_AUDIT",
    ).count()

    enforced_policy_denials = db.query(AuditEvent).filter(
        AuditEvent.created_at >= since,
        AuditEvent.action == "SECURITY_POLICY_DENIAL",
    ).count()

    # Revoked Sessions (action='SESSION_REVOKED')
    revoked_sessions = db.query(AuditEvent).filter(
        AuditEvent.created_at >= since,
        AuditEvent.action == "SESSION_REVOKED"
    ).count()

    # Revoked Devices (action='DEVICE_REVOKED')
    revoked_devices = db.query(AuditEvent).filter(
        AuditEvent.created_at >= since,
        AuditEvent.action == "DEVICE_REVOKED"
    ).count()

    # Cancelled Shifts (action='SHIFT_CANCEL')
    cancelled_shifts = db.query(AuditEvent).filter(
        AuditEvent.created_at >= since,
        AuditEvent.action == "SHIFT_CANCEL"
    ).count()

    # WebSocket Security Closes (target='websocket', action='WEBSOCKET_SECURITY_CLOSE')
    websocket_security_closes = db.query(AuditEvent).filter(
        AuditEvent.created_at >= since,
        AuditEvent.action == "WEBSOCKET_SECURITY_CLOSE",
        AuditEvent.target == "websocket"
    ).count()

    return {
        "audit_policy_violations": audit_policy_violations,
        "enforced_policy_denials": enforced_policy_denials,
        "denied_logins": denied_logins,
        "denied_protected_requests": denied_protected_requests,
        "revoked_sessions": revoked_sessions,
        "revoked_devices": revoked_devices,
        "cancelled_shifts": cancelled_shifts,
        "websocket_security_closes": websocket_security_closes,
    }


def get_security_audit_feed(
    db: Session,
    *,
    hours: int = 24,
    limit: int = 50,
    offset: int = 0,
    action: str | None = None,
    employee_id: int | None = None,
    target: str | None = None,
    success: bool | None = None,
    q: str | None = None,
) -> dict[str, Any]:
    if not (1 <= hours <= 720):
        raise ValueError("Time window must be between 1 and 720 hours.")
    if not (1 <= limit <= 100):
        raise ValueError("Limit must be between 1 and 100.")
    if offset < 0:
        raise ValueError("Offset must be zero or greater.")

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = db.query(AuditEvent).filter(AuditEvent.created_at >= since)

    if action:
        query = query.filter(AuditEvent.action == action)
    if target:
        query = query.filter(AuditEvent.target.ilike(f"%{target.strip()}%"))
    if success is not None:
        query = query.filter(AuditEvent.success == success)
    if q:
        search = f"%{q.strip()}%"
        query = query.filter(
            or_(
                AuditEvent.actor_email.ilike(search),
                AuditEvent.action.ilike(search),
                AuditEvent.target.ilike(search),
                AuditEvent.reason.ilike(search),
                AuditEvent.after_state.ilike(search),
                AuditEvent.before_state.ilike(search),
            )
        )
    if employee_id is not None:
        employee_pattern = f"%employee_id={employee_id}%"
        query = query.filter(
            or_(
                AuditEvent.actor_id == employee_id,
                AuditEvent.target.ilike(employee_pattern),
                AuditEvent.after_state.ilike(employee_pattern),
                AuditEvent.before_state.ilike(employee_pattern),
                AuditEvent.reason.ilike(f"%Employee {employee_id}%"),
            )
        )

    total = query.count()
    events = (
        query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for event in events:
        safe_target = _redact_text(event.target)
        safe_reason = _redact_text(event.reason)
        safe_before_state = _safe_stringified_state(event.before_state)
        safe_after_state = _safe_stringified_state(event.after_state)
        items.append({
            "id": event.id,
            "actor_id": event.actor_id,
            "actor_email": event.actor_email,
            "action": event.action,
            "target": safe_target,
            "subject_employee_id": _extract_subject_employee_id(event),
            "summary": _summarize_event(event, safe_after_state),
            "details": safe_after_state or safe_before_state,
            "reason": safe_reason,
            "success": event.success,
            "created_at": event.created_at,
        })

    return {
        "hours": hours,
        "limit": limit,
        "offset": offset,
        "total": total,
        "items": items,
    }
