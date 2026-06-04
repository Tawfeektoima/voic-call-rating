from sqlalchemy.orm import Session
from app.models import AuditEvent
from typing import Optional

def log_audit_event(
    db: Session,
    action: str,
    actor_id: Optional[int] = None,
    actor_email: Optional[str] = None,
    target: Optional[str] = None,
    before_state: Optional[str] = None,
    after_state: Optional[str] = None,
    reason: Optional[str] = None,
    success: bool = True
) -> AuditEvent:
    """
    Creates and persists an append-only audit event in the database.
    """
    event = AuditEvent(
        actor_id=actor_id,
        actor_email=actor_email,
        action=action,
        target=target,
        before_state=before_state,
        after_state=after_state,
        reason=reason,
        success=success
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
