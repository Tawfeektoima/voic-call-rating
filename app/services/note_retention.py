from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import RoleNote, RoleNoteStatus


def should_auto_archive(note: RoleNote, now: datetime) -> bool:
    status = note.status.value if hasattr(note.status, "value") else str(note.status)
    if status != RoleNoteStatus.RESOLVED.value:
        return False
    if note.resolved_at is None:
        return False
    return note.resolved_at <= now


def archive_resolved_notes(db, older_than_days: int = 30) -> int:
    now = datetime.now(timezone.utc)
    count = 0
    for note in db.query(RoleNote).filter(RoleNote.deleted_at.is_(None)).all():
        if should_auto_archive(note, now - timedelta(days=max(0, older_than_days))):
            note.status = RoleNoteStatus.ARCHIVED
            count += 1
    if count:
        db.commit()
    return count


def soft_delete_note(db, note: RoleNote, current_user, reason: str) -> RoleNote:
    note.status = RoleNoteStatus.DELETED
    note.deleted_at = datetime.now(timezone.utc)
    note.deleted_by_id = current_user.id
    note.delete_reason = reason
    db.commit()
    db.refresh(note)
    return note
