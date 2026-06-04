from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.database import get_db
from app.models import Employee, Campaign, Call, CallStatus, SystemLog, UserRole, EmployeeStatus, AuditEvent
from app.schemas import EmployeeCreate, EmployeeOut, EmployeeUpdate, EmployeeStatusUpdate, CampaignCreate, CampaignOut, SystemMetrics, SystemLogOut, SystemMetricPoint, AlertCreate, AuditEventOut
from app.routers.auth import get_current_user
from app.services.audit import log_audit_event
from app.security import get_password_hash

router = APIRouter(prefix="/api/admin", tags=["Admin (Setup)"])


def _serialize_enum_value(value):
    return value.value if hasattr(value, "value") else str(value)


def _validate_role(role_value: str) -> UserRole:
    normalized = role_value.upper().replace("-", "_").replace(" ", "_")
    try:
        return UserRole(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}"
        ) from exc


def _validate_status(status_value: str) -> EmployeeStatus:
    try:
        return EmployeeStatus(status_value.lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {[s.value for s in EmployeeStatus]}"
        ) from exc


def _prevent_self_lockout(current_user: Employee, employee: Employee, role: Optional[UserRole] = None, status: Optional[EmployeeStatus] = None):
    if current_user.id != employee.id:
        return

    role_changed = role is not None and role != current_user.role
    status_changed = status is not None and status.value != current_user.status
    if role_changed or status_changed:
        raise HTTPException(
            status_code=400,
            detail="Admins cannot change their own role or status to prevent lockout."
        )


def _audit_employee_update(
    db: Session,
    current_user: Employee,
    employee: Employee,
    action: str,
    before_state: str,
    after_state: str,
    reason: str,
):
    log_audit_event(
        db=db,
        action=action,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"Employee {employee.email} (ID: {employee.id})",
        before_state=before_state,
        after_state=after_state,
        reason=reason,
        success=True,
    )

# --- Employees ---

@router.post("/employees", response_model=EmployeeOut)
def create_employee(
    employee: EmployeeCreate, 
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    # Role Check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can create employees.")

    db_emp = db.query(Employee).filter(Employee.employee_code == employee.employee_code).first()
    if db_emp:
        raise HTTPException(status_code=400, detail="Employee code already registered")
    
    # Hash password if provided
    emp_data = employee.model_dump()
    if "password" in emp_data:
        emp_data["hashed_password"] = get_password_hash(emp_data.pop("password"))
    
    new_emp = Employee(**emp_data)
    db.add(new_emp)
    db.commit()
    db.refresh(new_emp)

    log_audit_event(
        db=db,
        action="REGISTER",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"Employee {new_emp.email} (ID: {new_emp.id})",
        after_state=f"role={new_emp.role.value if hasattr(new_emp.role, 'value') else new_emp.role}; status={new_emp.status}",
        reason="Admin panel employee creation",
        success=True,
    )
    return new_emp

@router.get("/employees", response_model=List[EmployeeOut])
def get_employees(
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    role: Optional[str] = None,
    status: Optional[str] = None,
    department: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    # Role Check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can view the employee list.")

    query = db.query(Employee)

    # Apply filters
    if role:
        query = query.filter(Employee.role == role.upper())
    if status:
        query = query.filter(Employee.status == status.lower())
    if department:
        query = query.filter(Employee.department == department)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Employee.name.like(search_filter)) |
            (Employee.email.like(search_filter)) |
            (Employee.employee_code.like(search_filter))
        )

    # Calculate total count before pagination
    total_count = query.count()
    response.headers["X-Total-Count"] = str(total_count)

    # Apply pagination
    employees = query.offset(skip).limit(limit).all()
    return employees


@router.put("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    # Role Check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can update employees.")

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")

    # Prevent self-lockout
    if current_user.id == employee.id:
        if (data.role and data.role != current_user.role.value) or (data.status and data.status != current_user.status):
            raise HTTPException(
                status_code=400,
                detail="Admins cannot change their own role or status to prevent lockout."
            )

    # Validate and apply role
    if data.role is not None:
        new_role = _validate_role(data.role)
        if employee.role != new_role:
            old_role = employee.role
            employee.role = new_role
            
            # Log role change in DB SystemLog
            log_msg = f"Admin {current_user.email} changed role of employee {employee.email} from {old_role} to {new_role}"
            db_log = SystemLog(
                error_type="ROLE_CHANGE",
                error_message=log_msg,
                severity="info"
            )
            db.add(db_log)

            # Log audit event (Task 0.8)
            _audit_employee_update(
                db=db,
                current_user=current_user,
                employee=employee,
                action="ROLE_CHANGE",
                before_state=_serialize_enum_value(old_role),
                after_state=_serialize_enum_value(new_role),
                reason="Admin panel update",
            )

    # Validate and apply status
    if data.status is not None:
        new_status = _validate_status(data.status)
        if employee.status != new_status.value:
            old_status = employee.status
            employee.status = new_status.value
            
            # Log status change in DB SystemLog
            log_msg = f"Admin {current_user.email} changed status of employee {employee.email} from {old_status} to {new_status.value}"
            db_log = SystemLog(
                error_type="STATUS_CHANGE",
                error_message=log_msg,
                severity="info"
            )
            db.add(db_log)

            # Log audit event (Task 0.8)
            _audit_employee_update(
                db=db,
                current_user=current_user,
                employee=employee,
                action="STATUS_CHANGE",
                before_state=old_status,
                after_state=new_status.value,
                reason="Admin panel update",
            )

    db.commit()
    db.refresh(employee)
    return employee


@router.put("/employees/{employee_id}/status", response_model=EmployeeOut)
def update_employee_status(
    employee_id: int,
    payload: EmployeeStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    if current_user.role not in (UserRole.ADMIN, UserRole.HR_MANAGER):
        raise HTTPException(status_code=403, detail="Only admins and HR managers can update employee status.")

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")

    new_status = _validate_status(payload.status)
    _prevent_self_lockout(current_user, employee, status=new_status)

    if employee.status == new_status.value:
        return employee

    old_status = employee.status
    employee.status = new_status.value

    db_log = SystemLog(
        error_type="STATUS_CHANGE",
        error_message=f"{current_user.role.value} {current_user.email} changed status of employee {employee.email} from {old_status} to {new_status.value}",
        severity="info"
    )
    db.add(db_log)

    _audit_employee_update(
        db=db,
        current_user=current_user,
        employee=employee,
        action="STATUS_CHANGE",
        before_state=old_status,
        after_state=new_status.value,
        reason="HR/admin status update",
    )

    db.commit()
    db.refresh(employee)
    return employee


@router.get("/audits", response_model=List[AuditEventOut])
def get_audit_logs(
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    # Role Check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can view audit logs.")

    query = db.query(AuditEvent).order_by(AuditEvent.created_at.desc())
    total_count = query.count()
    response.headers["X-Total-Count"] = str(total_count)

    return query.offset(skip).limit(limit).all()


# --- Campaigns ---

@router.post("/campaigns", response_model=CampaignOut)
def create_campaign(
    campaign: CampaignCreate, 
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    # Role Check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can create campaigns.")

    db_camp = db.query(Campaign).filter(Campaign.name == campaign.name).first()
    if db_camp:
        raise HTTPException(status_code=400, detail="Campaign name already exists")
    
    new_camp = Campaign(**campaign.model_dump())
    db.add(new_camp)
    db.commit()
    db.refresh(new_camp)
    return new_camp

@router.get("/campaigns", response_model=List[CampaignOut])
def get_campaigns(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    # Role Check
    if current_user.role == UserRole.AGENT:
         raise HTTPException(status_code=403, detail="Agents cannot view campaigns.")

    campaigns = db.query(Campaign).all()
    results = []

    for c in campaigns:
        # Calculate stats
        total_calls = db.query(func.count(Call.id)).filter(Call.campaign_id == c.id).scalar()
        agent_count = db.query(func.count(func.distinct(Call.employee_id))).filter(Call.campaign_id == c.id).scalar()
        avg_score = db.query(func.avg(func.coalesce(Call.overridden_score, Call.evaluation_score))).filter(
            Call.campaign_id == c.id, 
            Call.status == CallStatus.EVALUATED
        ).scalar() or 0.0

        # Create response model manually to include computed fields
        camp_out = CampaignOut.model_validate(c)
        camp_out.total_calls = total_calls
        camp_out.agent_count = agent_count
        camp_out.avg_score = round(float(avg_score), 1)
        results.append(camp_out)

    return results


@router.put("/campaigns/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    campaign_id: int,
    campaign_data: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    # Role Check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can update campaigns.")

    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Update fields
    for key, value in campaign_data.model_dump().items():
        setattr(campaign, key, value)

    db.commit()
    db.refresh(campaign)
    
    # Return with computed fields (mocked or calculated)
    camp_out = CampaignOut.model_validate(campaign)
    camp_out.total_calls = db.query(func.count(Call.id)).filter(Call.campaign_id == campaign.id).scalar()
    return camp_out


@router.delete("/campaigns/{campaign_id}")
def delete_campaign(
    campaign_id: int, 
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    # Role Check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can delete campaigns.")

    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Check for associated calls
    has_calls = db.query(Call).filter(Call.campaign_id == campaign_id).first()
    if has_calls:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete campaign with associated call records. Please archive it or delete the calls first."
        )

    db.delete(campaign)
    db.commit()
    return {"message": "Campaign deleted successfully"}
