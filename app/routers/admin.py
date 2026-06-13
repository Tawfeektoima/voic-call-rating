from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.database import get_db
from app.models import Employee, Campaign, Call, CallStatus, SystemLog, UserRole, EmployeeStatus, AuditEvent, Team, AgentTransferRequest, EmployeeTeamAssignment, KpiThresholdConfig
from app.schemas import EmployeeCreate, EmployeeOut, EmployeeUpdate, EmployeeStatusUpdate, CampaignCreate, CampaignOut, SystemMetrics, SystemLogOut, SystemMetricPoint, AlertCreate, AuditEventOut, KpiThresholdCreate, KpiThresholdUpdate, KpiThresholdOut, AgentTransferRequestOut
from app.routers.auth import get_current_user
from app.services.audit import log_audit_event
from app.services.kpi_catalog import get_kpi_catalog, get_kpi_definition, is_valid_kpi_key
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


def _require_admin(current_user: Employee) -> None:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can perform this action.")


def _validate_kpi_threshold_scope(team_id: Optional[int], campaign_id: Optional[int]) -> None:
    if team_id is None and campaign_id is None:
        raise HTTPException(status_code=400, detail="Must specify either team_id or campaign_id.")
    if team_id is not None and campaign_id is not None:
        raise HTTPException(status_code=400, detail="Cannot scope to both team and campaign simultaneously.")


def _check_duplicate_active_threshold(db: Session, *, team_id: Optional[int], campaign_id: Optional[int], kpi_key: str, exclude_id: Optional[int] = None) -> None:
    query = db.query(KpiThresholdConfig).filter(KpiThresholdConfig.kpi_key == kpi_key, KpiThresholdConfig.is_active == True)
    if team_id is not None:
        query = query.filter(KpiThresholdConfig.team_id == team_id)
    if campaign_id is not None:
        query = query.filter(KpiThresholdConfig.campaign_id == campaign_id)
    if exclude_id is not None:
        query = query.filter(KpiThresholdConfig.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=400, detail="An active threshold configuration already exists for this scope and KPI.")

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
    
    # Validate and normalize role
    if "role" in emp_data and emp_data["role"] is not None:
        emp_data["role"] = _validate_role(emp_data["role"])
    
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


@router.get("/kpi-catalog")
def list_kpi_catalog(current_user: Employee = Depends(get_current_user)):
    _require_admin(current_user)
    return get_kpi_catalog()


@router.post("/kpi-thresholds", response_model=KpiThresholdOut)
def create_kpi_threshold(
    payload: KpiThresholdCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    _validate_kpi_threshold_scope(payload.team_id, payload.campaign_id)
    if not is_valid_kpi_key(payload.kpi_key):
        raise HTTPException(status_code=400, detail="Invalid KPI key.")
    if payload.target_value < 0:
        raise HTTPException(status_code=400, detail="target_value must be non-negative.")
    if payload.team_id is not None and db.query(Team).filter(Team.id == payload.team_id).first() is None:
        raise HTTPException(status_code=400, detail="Team not found.")
    if payload.campaign_id is not None and db.query(Campaign).filter(Campaign.id == payload.campaign_id).first() is None:
        raise HTTPException(status_code=400, detail="Campaign not found.")
    if payload.is_active:
        _check_duplicate_active_threshold(db, team_id=payload.team_id, campaign_id=payload.campaign_id, kpi_key=payload.kpi_key)
    definition = get_kpi_definition(payload.kpi_key)
    threshold = KpiThresholdConfig(
        team_id=payload.team_id,
        campaign_id=payload.campaign_id,
        kpi_key=payload.kpi_key,
        kpi_label=(payload.kpi_label or (definition["label"] if definition else payload.kpi_key)).strip(),
        threshold_type=payload.threshold_type,
        target_value=payload.target_value,
        is_active=payload.is_active,
        created_by_id=current_user.id,
    )
    db.add(threshold)
    db.commit()
    db.refresh(threshold)
    log_audit_event(
        db=db,
        action="KPI_THRESHOLD_CREATE",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"KpiThresholdConfig {threshold.id} ({threshold.kpi_key})",
        after_state=f"kpi_key={threshold.kpi_key}; active={threshold.is_active}",
        reason="Admin KPI threshold create",
        success=True,
    )
    return threshold


@router.get("/kpi-thresholds", response_model=List[KpiThresholdOut])
def list_kpi_thresholds(
    response: Response,
    team_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    kpi_key: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    query = db.query(KpiThresholdConfig)
    if team_id is not None:
        query = query.filter(KpiThresholdConfig.team_id == team_id)
    if campaign_id is not None:
        query = query.filter(KpiThresholdConfig.campaign_id == campaign_id)
    if kpi_key is not None:
        query = query.filter(KpiThresholdConfig.kpi_key == kpi_key)
    if is_active is not None:
        query = query.filter(KpiThresholdConfig.is_active == is_active)
    response.headers["X-Total-Count"] = str(query.count())
    return query.order_by(KpiThresholdConfig.id.asc()).offset(skip).limit(limit).all()


@router.patch("/kpi-thresholds/{threshold_id}", response_model=KpiThresholdOut)
def update_kpi_threshold(
    threshold_id: int,
    payload: KpiThresholdUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    threshold = db.query(KpiThresholdConfig).filter(KpiThresholdConfig.id == threshold_id).first()
    if threshold is None:
        raise HTTPException(status_code=404, detail="Threshold not found.")
    if payload.target_value is not None:
        if payload.target_value < 0:
            raise HTTPException(status_code=400, detail="target_value must be non-negative.")
        threshold.target_value = payload.target_value
    if hasattr(payload, "kpi_label") and payload.kpi_label is not None:
        threshold.kpi_label = payload.kpi_label
    if hasattr(payload, "threshold_type") and payload.threshold_type is not None:
        threshold.threshold_type = payload.threshold_type
    if payload.is_active is not None:
        if payload.is_active:
            _check_duplicate_active_threshold(db, team_id=threshold.team_id, campaign_id=threshold.campaign_id, kpi_key=threshold.kpi_key, exclude_id=threshold.id)
        threshold.is_active = payload.is_active
    db.commit()
    db.refresh(threshold)
    log_audit_event(
        db=db,
        action="KPI_THRESHOLD_UPDATE",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"KpiThresholdConfig {threshold.id} ({threshold.kpi_key})",
        after_state=f"kpi_key={threshold.kpi_key}; active={threshold.is_active}",
        reason="Admin KPI threshold update",
        success=True,
    )
    return threshold


@router.patch("/transfer-requests/{request_id}/review", response_model=AgentTransferRequestOut)
def review_transfer_request(
    request_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    request = db.query(AgentTransferRequest).filter(AgentTransferRequest.id == request_id).first()
    if request is None:
        raise HTTPException(status_code=404, detail="Transfer request not found.")
    if request.status != "PENDING":
        raise HTTPException(status_code=400, detail="Transfer request already reviewed.")
    new_status = str(payload.get("status", "")).upper()
    if new_status not in {"APPROVED", "REJECTED"}:
        raise HTTPException(status_code=400, detail="Invalid review status.")
    if new_status == "APPROVED":
        active_assignments = db.query(EmployeeTeamAssignment).filter(
            EmployeeTeamAssignment.employee_id == request.agent_id,
            EmployeeTeamAssignment.is_active == True,
        ).all()
        if len(active_assignments) != 1 or active_assignments[0].team_id != request.from_team_id:
            raise HTTPException(status_code=400, detail="Agent must have exactly one active assignment on the from team.")
        active_assignments[0].is_active = False
        active_assignments[0].ended_at = func.now()
        db.add(
            EmployeeTeamAssignment(
                employee_id=request.agent_id,
                team_id=request.to_team_id,
                is_active=True,
                created_by_id=current_user.id,
            )
        )
    request.status = new_status
    request.review_note = payload.get("review_note")
    request.reviewed_by_id = current_user.id
    request.reviewed_at = func.now()
    db.commit()
    db.refresh(request)
    return request
