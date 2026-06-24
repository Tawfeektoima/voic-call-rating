import json
from datetime import date, time, datetime, timezone
from typing import Optional, Literal, List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee, EmployeeShift, UserRole, UserSession, TrustedDevice
from app.routers.auth import get_current_user
from app.services.security_policy import add_security_audit_event, revoke_session_by_id, approve_device_by_id, revoke_device_by_id
from app.services.security_observability import get_security_summary, get_security_audit_feed
from pydantic import BaseModel, Field, model_validator

router = APIRouter(prefix="/api/security-admin", tags=["Security Admin"])


class ShiftCreateSchema(BaseModel):
    employee_id: int
    work_date: date
    shift_start: time
    shift_end: time
    grace_before_minutes: int = Field(10, ge=0, le=240)
    grace_after_minutes: int = Field(10, ge=0, le=240)
    status: Literal["scheduled", "cancelled", "disabled"] = "scheduled"


class ShiftUpdateSchema(BaseModel):
    work_date: Optional[date] = None
    shift_start: Optional[time] = None
    shift_end: Optional[time] = None
    grace_before_minutes: Optional[int] = Field(None, ge=0, le=240)
    grace_after_minutes: Optional[int] = Field(None, ge=0, le=240)
    status: Optional[Literal["scheduled", "cancelled", "disabled"]] = None
    reason: Optional[str] = None


class ShiftCancelSchema(BaseModel):
    reason: str


class ShiftResponseSchema(BaseModel):
    id: int
    employee_id: int
    work_date: date
    shift_start: Optional[time]
    shift_end: Optional[time]
    grace_before_minutes: int
    grace_after_minutes: int
    status: str

    model_config = {
        "from_attributes": True
    }


def require_security_admin(current_user: Employee = Depends(get_current_user)) -> Employee:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins are allowed to manage shifts."
        )
    return current_user


@router.get("/shifts", response_model=List[ShiftResponseSchema])
def list_shifts(
    employee_id: Optional[int] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db),
    admin: Employee = Depends(require_security_admin)
):
    query = db.query(EmployeeShift)
    if employee_id is not None:
        query = query.filter(EmployeeShift.employee_id == employee_id)
    if from_date is not None:
        query = query.filter(EmployeeShift.work_date >= from_date)
    if to_date is not None:
        query = query.filter(EmployeeShift.work_date <= to_date)
    return query.all()


@router.post("/shifts", response_model=ShiftResponseSchema, status_code=status.HTTP_201_CREATED)
def create_shift(
    payload: ShiftCreateSchema,
    db: Session = Depends(get_db),
    admin: Employee = Depends(require_security_admin)
):
    # Validate employee exists and is active
    employee = db.query(Employee).filter(Employee.id == payload.employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found."
        )
    if (employee.status or "").lower() != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee is not active."
        )

    # Check unique constraint (one shift per employee per date)
    existing = db.query(EmployeeShift).filter(
        EmployeeShift.employee_id == payload.employee_id,
        EmployeeShift.work_date == payload.work_date
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A shift already exists for this employee on this date."
        )

    shift = EmployeeShift(
        employee_id=payload.employee_id,
        work_date=payload.work_date,
        shift_start=payload.shift_start,
        shift_end=payload.shift_end,
        grace_before_minutes=payload.grace_before_minutes,
        grace_after_minutes=payload.grace_after_minutes,
        status=payload.status
    )
    db.add(shift)
    db.flush()

    # Log audit event
    after_state = {
        "employee_id": shift.employee_id,
        "work_date": str(shift.work_date),
        "shift_start": str(shift.shift_start),
        "shift_end": str(shift.shift_end),
        "grace_before_minutes": shift.grace_before_minutes,
        "grace_after_minutes": shift.grace_after_minutes,
        "status": shift.status
    }
    add_security_audit_event(
        db=db,
        action="SHIFT_CREATE",
        actor_id=admin.id,
        actor_email=admin.email,
        target=f"EmployeeShift id={shift.id}; employee_id={shift.employee_id}",
        after_state=json.dumps(after_state),
        reason="Admin created employee shift",
        success=True
    )
    db.commit()
    return shift


@router.patch("/shifts/{shift_id}", response_model=ShiftResponseSchema)
def update_shift(
    shift_id: int,
    payload: ShiftUpdateSchema,
    db: Session = Depends(get_db),
    admin: Employee = Depends(require_security_admin)
):
    shift = db.query(EmployeeShift).filter(EmployeeShift.id == shift_id).first()
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shift not found."
        )

    updates = {}
    if payload.work_date is not None:
        if payload.work_date != shift.work_date:
            duplicate = db.query(EmployeeShift).filter(
                EmployeeShift.employee_id == shift.employee_id,
                EmployeeShift.work_date == payload.work_date,
                EmployeeShift.id != shift.id
            ).first()
            if duplicate:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A shift already exists for this employee on this date."
                )
        shift.work_date = payload.work_date
        updates["work_date"] = str(payload.work_date)
    if payload.shift_start is not None:
        shift.shift_start = payload.shift_start
        updates["shift_start"] = str(payload.shift_start)
    if payload.shift_end is not None:
        shift.shift_end = payload.shift_end
        updates["shift_end"] = str(payload.shift_end)
    if payload.grace_before_minutes is not None:
        shift.grace_before_minutes = payload.grace_before_minutes
        updates["grace_before_minutes"] = payload.grace_before_minutes
    if payload.grace_after_minutes is not None:
        shift.grace_after_minutes = payload.grace_after_minutes
        updates["grace_after_minutes"] = payload.grace_after_minutes
    if payload.status is not None:
        shift.status = payload.status
        updates["status"] = payload.status

    db.flush()

    add_security_audit_event(
        db=db,
        action="SHIFT_UPDATE",
        actor_id=admin.id,
        actor_email=admin.email,
        target=f"EmployeeShift id={shift.id}; employee_id={shift.employee_id}",
        after_state=json.dumps(updates),
        reason=payload.reason or "Admin updated employee shift",
        success=True
    )
    db.commit()
    return shift


@router.post("/shifts/{shift_id}/cancel", response_model=ShiftResponseSchema)
def cancel_shift(
    shift_id: int,
    payload: ShiftCancelSchema,
    db: Session = Depends(get_db),
    admin: Employee = Depends(require_security_admin)
):
    shift = db.query(EmployeeShift).filter(EmployeeShift.id == shift_id).first()
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shift not found."
        )

    shift.status = "cancelled"
    db.flush()

    after_state = {
        "status": "cancelled",
        "reason": payload.reason
    }
    add_security_audit_event(
        db=db,
        action="SHIFT_CANCEL",
        actor_id=admin.id,
        actor_email=admin.email,
        target=f"EmployeeShift id={shift.id}; employee_id={shift.employee_id}",
        after_state=json.dumps(after_state),
        reason=payload.reason,
        success=True
    )
    db.commit()
    return shift


class SessionEmployeeSchema(BaseModel):
    id: int
    name: str
    employee_code: str
    email: str

    model_config = {
        "from_attributes": True
    }


class SessionResponseSchema(BaseModel):
    id: int
    employee_id: int
    employee: Optional[SessionEmployeeSchema] = None
    trusted_device_id: Optional[int] = None
    issued_at: datetime
    last_seen_at: Optional[datetime] = None
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    is_active: bool

    model_config = {
        "from_attributes": True
    }


class SessionRevokeSchema(BaseModel):
    reason: str


@router.get("/sessions", response_model=List[SessionResponseSchema])
def list_sessions(
    employee_id: Optional[int] = None,
    active_only: bool = False,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db),
    admin: Employee = Depends(require_security_admin)
):
    query = db.query(UserSession)
    if employee_id is not None:
        query = query.filter(UserSession.employee_id == employee_id)
    if active_only:
        now = datetime.utcnow()
        query = query.filter(
            UserSession.is_active == True,
            UserSession.revoked_at == None,
            UserSession.expires_at > now
        )
    if from_date is not None:
        query = query.filter(UserSession.issued_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date is not None:
        query = query.filter(UserSession.issued_at <= datetime.combine(to_date, datetime.max.time()))
    return query.all()


@router.post("/sessions/{session_id}/revoke")
def revoke_user_session(
    session_id: int,
    payload: SessionRevokeSchema,
    db: Session = Depends(get_db),
    admin: Employee = Depends(require_security_admin)
):
    session = revoke_session_by_id(
        db=db,
        session_id=session_id,
        reason=payload.reason,
        actor_id=admin.id,
        actor_email=admin.email
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )
    db.commit()
    return {"message": "Session revoked successfully"}


class DeviceUpdateSchema(BaseModel):
    device_label: str = Field(..., min_length=1, max_length=255)


class DeviceApproveSchema(BaseModel):
    reason: str


class DeviceRevokeSchema(BaseModel):
    reason: str


class DeviceResponseSchema(BaseModel):
    id: int
    employee_id: int
    employee: Optional[SessionEmployeeSchema] = None
    device_label: Optional[str] = None
    device_fingerprint: Optional[str] = None
    is_trusted: bool
    first_seen_at: datetime
    last_seen_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by_id: Optional[int] = None
    revoked_at: Optional[datetime] = None
    revoke_reason: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

    @model_validator(mode="before")
    @classmethod
    def convert_orm_to_dict(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            device_id_hash = getattr(data, "device_id_hash", None)
            fingerprint = device_id_hash[:8] if device_id_hash else None
            return {
                "id": data.id,
                "employee_id": data.employee_id,
                "employee": data.employee,
                "device_label": data.device_label,
                "device_fingerprint": fingerprint,
                "is_trusted": data.is_trusted,
                "first_seen_at": data.first_seen_at,
                "last_seen_at": data.last_seen_at,
                "approved_at": data.approved_at,
                "approved_by_id": data.approved_by_id,
                "revoked_at": data.revoked_at,
                "revoke_reason": data.revoke_reason
            }
        return data


@router.get("/devices", response_model=List[DeviceResponseSchema])
def list_devices(
    employee_id: Optional[int] = None,
    trusted_only: bool = False,
    include_revoked: bool = True,
    db: Session = Depends(get_db),
    admin: Employee = Depends(require_security_admin)
):
    query = db.query(TrustedDevice)
    if employee_id is not None:
        query = query.filter(TrustedDevice.employee_id == employee_id)
    if trusted_only:
        query = query.filter(TrustedDevice.is_trusted == True)
    if not include_revoked:
        query = query.filter(TrustedDevice.revoked_at == None)
    return query.all()


@router.patch("/devices/{trusted_device_id}", response_model=DeviceResponseSchema)
def rename_device(
    trusted_device_id: int,
    payload: DeviceUpdateSchema,
    db: Session = Depends(get_db),
    admin: Employee = Depends(require_security_admin)
):
    dev = db.query(TrustedDevice).filter(TrustedDevice.id == trusted_device_id).first()
    if not dev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found."
        )

    dev.device_label = payload.device_label
    db.flush()

    after_state = {
        "device_label": payload.device_label,
        "device_id": dev.id
    }
    add_security_audit_event(
        db=db,
        action="DEVICE_RENAME",
        actor_id=admin.id,
        actor_email=admin.email,
        target=f"TrustedDevice id={dev.id}; employee_id={dev.employee_id}",
        after_state=json.dumps(after_state),
        reason=f"Admin renamed device to '{payload.device_label}'",
        success=True
    )
    db.commit()
    return dev


@router.post("/devices/{trusted_device_id}/approve", response_model=DeviceResponseSchema)
def approve_user_device(
    trusted_device_id: int,
    payload: DeviceApproveSchema,
    db: Session = Depends(get_db),
    admin: Employee = Depends(require_security_admin)
):
    dev = approve_device_by_id(
        db=db,
        device_id=trusted_device_id,
        actor_id=admin.id,
        reason=payload.reason
    )
    if not dev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found."
        )
    db.commit()
    return dev


@router.post("/devices/{trusted_device_id}/revoke", response_model=DeviceResponseSchema)
def revoke_user_device(
    trusted_device_id: int,
    payload: DeviceRevokeSchema,
    db: Session = Depends(get_db),
    admin: Employee = Depends(require_security_admin)
):
    dev = revoke_device_by_id(
        db=db,
        device_id=trusted_device_id,
        reason=payload.reason,
        actor_id=admin.id
    )
    if not dev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found."
        )
    db.commit()
    return dev


class SecuritySummarySchema(BaseModel):
    audit_policy_violations: int
    enforced_policy_denials: int
    denied_logins: int
    denied_protected_requests: int
    revoked_sessions: int
    revoked_devices: int
    cancelled_shifts: int
    websocket_security_closes: int


class SecurityAuditEventSchema(BaseModel):
    id: int
    actor_id: Optional[int] = None
    actor_email: Optional[str] = None
    action: str
    target: Optional[str] = None
    subject_employee_id: Optional[int] = None
    summary: Optional[str] = None
    details: Optional[str] = None
    reason: Optional[str] = None
    success: bool = True
    created_at: datetime


class SecurityAuditFeedSchema(BaseModel):
    hours: int
    limit: int
    offset: int
    total: int
    items: List[SecurityAuditEventSchema]


@router.get("/summary", response_model=SecuritySummarySchema)
def get_observability_summary(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    admin: Employee = Depends(require_security_admin)
):
    try:
        summary = get_security_summary(db, hours=hours)
        return summary
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/events", response_model=SecurityAuditFeedSchema)
def list_security_audit_events(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    action: Optional[str] = None,
    employee_id: Optional[int] = None,
    target: Optional[str] = None,
    success: Optional[bool] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: Employee = Depends(require_security_admin)
):
    try:
        feed = get_security_audit_feed(
            db,
            hours=hours,
            limit=limit,
            offset=offset,
            action=action,
            employee_id=employee_id,
            target=target,
            success=success,
            q=q,
        )
        return feed
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
