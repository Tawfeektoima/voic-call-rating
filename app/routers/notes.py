from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee, RoleNote, RoleNoteStatus, UserRole
from app.routers.auth import get_current_user
from app.schemas import (
    RoleNoteCreate,
    RoleNoteOut,
    RoleNoteRecipientOut,
    RoleNoteStatusUpdate,
    RoleNoteThreadOut,
    RoleNoteUpdate,
)
from app.services.audit import log_audit_event
from app.services.note_recipients import get_allowed_note_recipients, validate_note_recipient
from app.services.note_retention import soft_delete_note
from app.services.note_scope import (
    _load_employee,
    build_note_snapshots,
    can_user_read_note,
    can_user_reply_to_note,
    can_user_resolve_note,
    root_note_id,
    utcnow,
    validate_note_context,
)

router = APIRouter(prefix="/api/notes", tags=["Notes"])


def _note_status_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _visibility_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _note_type_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _priority_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


ALLOWED_STATUS_TRANSITIONS = {
    RoleNoteStatus.OPEN.value: {RoleNoteStatus.READ.value, RoleNoteStatus.IN_PROGRESS.value, RoleNoteStatus.WAITING_REPLY.value, RoleNoteStatus.RESOLVED.value, RoleNoteStatus.ARCHIVED.value},
    RoleNoteStatus.READ.value: {RoleNoteStatus.IN_PROGRESS.value, RoleNoteStatus.WAITING_REPLY.value, RoleNoteStatus.RESOLVED.value, RoleNoteStatus.ARCHIVED.value},
    RoleNoteStatus.IN_PROGRESS.value: {RoleNoteStatus.WAITING_REPLY.value, RoleNoteStatus.RESOLVED.value, RoleNoteStatus.ARCHIVED.value},
    RoleNoteStatus.WAITING_REPLY.value: {RoleNoteStatus.IN_PROGRESS.value, RoleNoteStatus.RESOLVED.value, RoleNoteStatus.ARCHIVED.value},
    RoleNoteStatus.RESOLVED.value: {RoleNoteStatus.ARCHIVED.value},
    RoleNoteStatus.ARCHIVED.value: set(),
    RoleNoteStatus.DELETED.value: set(),
}


def _get_note_or_404(db: Session, note_id: int) -> RoleNote:
    note = db.query(RoleNote).filter(RoleNote.id == note_id).first()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found.")
    return note


def _get_root_note(db: Session, note_id: int) -> RoleNote:
    note = _get_note_or_404(db, note_id)
    root_id = root_note_id(note)
    return _get_note_or_404(db, root_id)


def _load_thread(db: Session, root: RoleNote) -> RoleNoteThreadOut:
    replies = (
        db.query(RoleNote)
        .filter(RoleNote.parent_note_id == root.id)
        .order_by(RoleNote.created_at.asc())
        .all()
    )
    return RoleNoteThreadOut(note=RoleNoteOut.model_validate(root), replies=[RoleNoteOut.model_validate(reply) for reply in replies])


def _ensure_can_view(db: Session, current_user: Employee, note: RoleNote) -> None:
    if not can_user_read_note(db, current_user, note):
        raise HTTPException(status_code=403, detail="You do not have access to this note.")


def _role_value(role) -> str:
    return role.value if hasattr(role, "value") else str(role)


@router.post("", response_model=RoleNoteOut)
def create_note(
    payload: RoleNoteCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    validate_note_context(db, current_user, payload)
    validate_note_recipient(db, current_user, payload)
    snapshots = build_note_snapshots(db, payload)

    note = RoleNote(
        sender_id=current_user.id,
        recipient_id=payload.recipient_id,
        recipient_role=payload.recipient_role,
        visibility=payload.visibility,
        team_id=payload.team_id,
        campaign_id=payload.campaign_id,
        employee_id=payload.employee_id,
        call_id=payload.call_id,
        parent_note_id=payload.parent_note_id,
        title=payload.title,
        body=payload.body,
        note_type=payload.note_type,
        priority=payload.priority,
        status=RoleNoteStatus.OPEN,
        kpi_key=payload.kpi_key,
        kpi_label=payload.kpi_label,
        current_value=payload.current_value,
        target_value=payload.target_value,
        period_start=payload.period_start,
        period_end=payload.period_end,
        **snapshots,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    log_audit_event(
        db=db,
        action="NOTE_CREATED",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"RoleNote {note.id}",
        after_state=f"status={_note_status_value(note.status)}; note_type={_note_type_value(note.note_type)}",
        reason="Workflow note created",
        success=True,
    )
    return note


@router.get("/recipients", response_model=List[RoleNoteRecipientOut])
def list_allowed_recipients(
    note_type: str = Query(...),
    team_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    call_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    recipients = get_allowed_note_recipients(
        db=db,
        current_user=current_user,
        note_type=note_type,
        team_id=team_id,
        campaign_id=campaign_id,
        employee_id=employee_id,
        call_id=call_id,
    )
    return [
        RoleNoteRecipientOut(
            id=recipient["recipient_id"],
            name=recipient["name"],
            role=recipient["recipient_role"],
            reason=recipient.get("reason"),
        )
        for recipient in recipients
    ]


@router.get("/inbox", response_model=List[RoleNoteOut])
def get_inbox(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    note_type: Optional[str] = None,
    priority: Optional[str] = None,
    visibility: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    notes = (
        db.query(RoleNote)
        .order_by(RoleNote.created_at.desc())
        .all()
    )
    items = []
    for note in notes:
        if not can_user_read_note(db, current_user, note):
            continue
        if note.parent_note_id is not None:
            continue
        if status and _note_status_value(note.status) != status.upper():
            continue
        if note_type and _note_type_value(note.note_type) != note_type.upper():
            continue
        if priority and _priority_value(note.priority) != priority.upper():
            continue
        if visibility and _visibility_value(note.visibility) != visibility.upper():
            continue
        items.append(note)
    return items[skip:skip + limit]


@router.get("/sent", response_model=List[RoleNoteOut])
def get_sent(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    note_type: Optional[str] = None,
    priority: Optional[str] = None,
    visibility: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    query = db.query(RoleNote).filter(RoleNote.sender_id == current_user.id).order_by(RoleNote.created_at.desc())
    notes = query.all()
    items = []
    for note in notes:
        if _note_status_value(note.status) == RoleNoteStatus.DELETED.value and _role_value(current_user.role) != UserRole.ADMIN.value:
            continue
        if status and _note_status_value(note.status) != status.upper():
            continue
        if note_type and _note_type_value(note.note_type) != note_type.upper():
            continue
        if priority and _priority_value(note.priority) != priority.upper():
            continue
        if visibility and _visibility_value(note.visibility) != visibility.upper():
            continue
        items.append(note)
    return items[skip:skip + limit]


@router.get("/{note_id}", response_model=RoleNoteThreadOut)
def get_note_thread(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    root = _get_root_note(db, note_id)
    _ensure_can_view(db, current_user, root)
    replies = (
        db.query(RoleNote)
        .filter(RoleNote.parent_note_id == root.id)
        .order_by(RoleNote.created_at.asc())
        .all()
    )
    for reply in replies:
        _ensure_can_view(db, current_user, reply)
    return _load_thread(db, root)


@router.post("/{note_id}/reply", response_model=RoleNoteOut)
def reply_to_note(
    note_id: int,
    payload: RoleNoteCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    root = _get_root_note(db, note_id)
    if not can_user_reply_to_note(db, current_user, root):
        raise HTTPException(status_code=403, detail="You do not have access to reply to this note.")
    auto_resolved_recipient = False
    if payload.recipient_id is None and payload.recipient_role is None:
        payload.recipient_id = root.sender_id if root.sender_id != current_user.id else root.recipient_id
        auto_resolved_recipient = True
    validate_note_context(db, current_user, payload)
    if auto_resolved_recipient:
        if payload.recipient_id is None or _load_employee(db, payload.recipient_id) is None:
            raise HTTPException(status_code=400, detail="Reply recipient could not be resolved.")
    else:
        validate_note_recipient(db, current_user, payload)
    snapshots = build_note_snapshots(db, payload)

    reply = RoleNote(
        sender_id=current_user.id,
        recipient_id=payload.recipient_id,
        recipient_role=payload.recipient_role,
        visibility=payload.visibility,
        team_id=payload.team_id if payload.team_id is not None else root.team_id,
        campaign_id=payload.campaign_id if payload.campaign_id is not None else root.campaign_id,
        employee_id=payload.employee_id if payload.employee_id is not None else root.employee_id,
        call_id=payload.call_id if payload.call_id is not None else root.call_id,
        parent_note_id=root.id,
        title=payload.title,
        body=payload.body,
        note_type=payload.note_type,
        priority=payload.priority,
        status=RoleNoteStatus.OPEN,
        kpi_key=payload.kpi_key if payload.kpi_key is not None else root.kpi_key,
        kpi_label=payload.kpi_label if payload.kpi_label is not None else root.kpi_label,
        current_value=payload.current_value if payload.current_value is not None else root.current_value,
        target_value=payload.target_value if payload.target_value is not None else root.target_value,
        period_start=payload.period_start if payload.period_start is not None else root.period_start,
        period_end=payload.period_end if payload.period_end is not None else root.period_end,
        **snapshots,
    )
    db.add(reply)
    root.status = RoleNoteStatus.WAITING_REPLY
    db.commit()
    db.refresh(reply)

    log_audit_event(
        db=db,
        action="NOTE_REPLIED",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"RoleNote {root.id}",
        after_state=f"reply_id={reply.id}",
        reason="Workflow note reply",
        success=True,
    )
    return reply


@router.patch("/{note_id}/read", response_model=RoleNoteOut)
def mark_note_read(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    note = _get_note_or_404(db, note_id)
    _ensure_can_view(db, current_user, note)
    if note.read_at is None:
        note.read_at = utcnow()
    if _note_status_value(note.status) == RoleNoteStatus.OPEN.value:
        note.status = RoleNoteStatus.READ
    db.commit()
    db.refresh(note)

    log_audit_event(
        db=db,
        action="NOTE_READ",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"RoleNote {note.id}",
        after_state=f"status={_note_status_value(note.status)}",
        reason="Workflow note marked as read",
        success=True,
    )
    return note


@router.patch("/{note_id}/status", response_model=RoleNoteOut)
def update_note_status(
    note_id: int,
    payload: RoleNoteStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    note = _get_note_or_404(db, note_id)
    _ensure_can_view(db, current_user, note)
    new_status = payload.status.upper()
    current_status = _note_status_value(note.status)
    if new_status not in ALLOWED_STATUS_TRANSITIONS.get(current_status, set()):
        raise HTTPException(status_code=400, detail="Invalid status transition.")
    note.status = new_status
    if new_status == RoleNoteStatus.READ.value and note.read_at is None:
        note.read_at = utcnow()
    db.commit()
    db.refresh(note)

    log_audit_event(
        db=db,
        action="NOTE_STATUS_CHANGED",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"RoleNote {note.id}",
        before_state=current_status,
        after_state=new_status,
        reason="Workflow note status update",
        success=True,
    )
    return note


@router.patch("/{note_id}/resolve", response_model=RoleNoteOut)
def resolve_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    note = _get_note_or_404(db, note_id)
    if not can_user_resolve_note(db, current_user, note):
        raise HTTPException(status_code=403, detail="You do not have access to resolve this note.")
    note.status = RoleNoteStatus.RESOLVED
    note.resolved_at = utcnow()
    note.resolved_by_id = current_user.id
    db.commit()
    db.refresh(note)

    log_audit_event(
        db=db,
        action="NOTE_RESOLVED",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"RoleNote {note.id}",
        after_state=f"status={_note_status_value(note.status)}",
        reason="Workflow note resolved",
        success=True,
    )
    return note


@router.patch("/{note_id}/archive", response_model=RoleNoteOut)
def archive_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    if _role_value(current_user.role) != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Only admins can archive notes.")
    note = _get_note_or_404(db, note_id)
    note.status = RoleNoteStatus.ARCHIVED
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}", response_model=RoleNoteOut)
def delete_note(
    note_id: int,
    reason: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    if _role_value(current_user.role) != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Only admins can delete notes.")
    note = _get_note_or_404(db, note_id)
    note = soft_delete_note(db, note, current_user, reason)
    return note
