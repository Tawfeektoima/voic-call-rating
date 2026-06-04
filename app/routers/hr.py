from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, Integer
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import io
import pandas as pd

from app.database import get_db
from app.models import AgentViolation, Employee, UserRole, SystemLog, Call, Campaign
from app.routers.auth import get_current_user
from app.schemas import (
    AgentViolationHistory,
    AgentViolationOut,
    ViolationSummaryRow,
    PendingViolationOut,
    ViolationStats,
    EmployeeCreate,
    BulkEmployeeFailure,
    BulkEmployeeResult,
    EmployeeOut
)
from app.security import get_password_hash

router = APIRouter(prefix="/api/hr", tags=["HR Violations"])

HR_ROLES = [UserRole.ADMIN, UserRole.HR_MANAGER, UserRole.QA]

@router.get("/violations/summary", response_model=List[ViolationSummaryRow])
def get_violations_summary(
    limit: int = Query(50, ge=1, le=500, description="Maximum agents to return"),
    offset: int = Query(0, ge=0, description="Result offset"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns per-agent violation counts grouped by severity.
    Accessible by: admin, hr_manager only.
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Access denied.")

    summary_query = (
        db.query(
            AgentViolation.employee_id,
            Employee.name.label("employee_name"),
            func.count(AgentViolation.id).label("total_violations"),
            func.sum(func.cast(AgentViolation.severity == 'high', Integer)).label("high_count"),
            func.sum(func.cast(AgentViolation.severity == 'medium', Integer)).label("medium_count"),
            func.sum(func.cast(AgentViolation.severity == 'low', Integer)).label("low_count"),
            func.sum(func.cast(AgentViolation.hr_flagged == True, Integer)).label("hr_flagged_count"),
            func.sum(AgentViolation.score_deduction).label("total_deductions"),
            func.max(AgentViolation.created_at).label("last_violation_at")
        )
        .join(Employee, AgentViolation.employee_id == Employee.id)
        .group_by(AgentViolation.employee_id, Employee.name)
        .all()
    )

    results = []
    for row in summary_query[offset:offset + limit]:
        results.append(ViolationSummaryRow(
            employee_id=row.employee_id,
            employee_name=row.employee_name,
            total_violations=row.total_violations,
            high_count=row.high_count or 0,
            medium_count=row.medium_count or 0,
            low_count=row.low_count or 0,
            hr_flagged_count=row.hr_flagged_count or 0,
            total_deductions=row.total_deductions or 0.0,
            last_violation_at=row.last_violation_at
        ))

    return results

@router.get("/violations/pending", response_model=List[PendingViolationOut])
def get_pending_hr_violations(
    limit: int = Query(50, ge=1, le=500, description="Maximum violations to return"),
    offset: int = Query(0, ge=0, description="Result offset"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns violations where hr_flagged=True, ordered by severity then date.
    Accessible by: admin, hr_manager only.
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Access denied.")

    violations = (
        db.query(AgentViolation, Employee)
        .join(Employee, AgentViolation.employee_id == Employee.id)
        .filter(AgentViolation.hr_flagged == True)
        .order_by(AgentViolation.created_at.desc())
        .all()
    )

    results = []
    for v, emp in violations[offset:offset + limit]:
        results.append(PendingViolationOut(
            violation_id=v.id,
            employee_id=v.employee_id,
            employee_name=emp.name,
            call_id=v.call_id,
            violation_type=v.violation_id,
            severity=v.severity,
            occurrence=v.occurrence,
            penalty_tier=v.penalty_tier,
            evidence=v.evidence,
            created_at=v.created_at
        ))
    return results

@router.get("/violations/stats", response_model=ViolationStats)
def get_violation_stats(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns platform-wide violation statistics for the dashboard.
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Access denied.")

    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = start_of_today - timedelta(days=now.weekday())

    total_today = db.query(func.count(AgentViolation.id)).filter(AgentViolation.created_at >= start_of_today).scalar() or 0
    total_week = db.query(func.count(AgentViolation.id)).filter(AgentViolation.created_at >= start_of_week).scalar() or 0
    
    most_common = (
        db.query(AgentViolation.violation_id, func.count(AgentViolation.id).label("count"))
        .group_by(AgentViolation.violation_id)
        .order_by(func.count(AgentViolation.id).desc())
        .first()
    )
    most_common_id = most_common.violation_id if most_common else None
    most_common_count = most_common.count if most_common else 0

    agents_with_hr = db.query(func.count(func.distinct(AgentViolation.employee_id))).filter(AgentViolation.hr_flagged == True).scalar() or 0
    auto_fails = db.query(func.count(AgentViolation.id)).filter(
        AgentViolation.auto_fail == True,
        AgentViolation.created_at >= start_of_today
    ).scalar() or 0

    return ViolationStats(
        total_violations_today=total_today,
        total_violations_this_week=total_week,
        most_common_violation=most_common_id,
        most_common_violation_count=most_common_count,
        agents_with_hr_flags=agents_with_hr,
        auto_fails_today=auto_fails
    )

@router.get("/violations/trends")
def get_violation_trends(
    days: int = Query(7, ge=1, le=90, description="Number of days to include"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns violation trends for the last N days.
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Access denied.")

    since = datetime.now(timezone.utc) - timedelta(days=days)
    results = (
        db.query(
            cast(AgentViolation.created_at, Date).label("date"),
            AgentViolation.severity,
            func.count(AgentViolation.id).label("count"),
        )
        .filter(AgentViolation.created_at >= since)
        .group_by(cast(AgentViolation.created_at, Date), AgentViolation.severity)
        .order_by(cast(AgentViolation.created_at, Date))
        .all()
    )

    # Build day-by-day structure
    trend_map = {}
    for row in results:
        day = str(row.date)
        if day not in trend_map:
            trend_map[day] = {"date": day, "high": 0, "medium": 0, "low": 0}
        trend_map[day][row.severity] += row.count

    # Fill missing days with zeros
    output = []
    for i in range(days):
        day = str((datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).date())
        output.append(trend_map.get(day, {"date": day, "high": 0, "medium": 0, "low": 0}))

    return output

@router.get("/violations/{employee_id}", response_model=AgentViolationHistory)
def get_agent_violations(
    employee_id: int,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200, description="Maximum violations to return"),
    offset: int = Query(0, ge=0, description="Result offset"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns all violations for an agent, newest first.
    Accessible by: admin, hr_manager
    Agents can only view their own violations.
    """
    if current_user.role == UserRole.AGENT and current_user.id != employee_id:
        raise HTTPException(status_code=403, detail="Agents can only view their own violations.")
    
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    query = db.query(AgentViolation).filter(AgentViolation.employee_id == employee_id)
    if severity:
        query = query.filter(AgentViolation.severity == severity)
    
    total_violations = query.count()
    total_deductions = db.query(func.sum(AgentViolation.score_deduction)).filter(AgentViolation.employee_id == employee_id).scalar() or 0.0

    violations = query.order_by(AgentViolation.created_at.desc()).offset(offset).limit(limit).all()

    v_outs = [AgentViolationOut.model_validate(v) for v in violations]

    return AgentViolationHistory(
        employee_id=employee_id,
        employee_name=employee.name,
        total_violations=total_violations,
        total_deductions=total_deductions,
        violations=v_outs
    )


@router.get("/alarms/pending")
def get_pending_qa_alarms(
    limit: int = Query(50, ge=1, le=500, description="Maximum alarms to return"),
    offset: int = Query(0, ge=0, description="Result offset"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns pending QA alarms (calls where qa_alarm=True and overridden_score is None).
    Accessible by: admin, hr_manager, qa.
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Access denied.")

    # Fetch calls with active alarms
    calls = (
        db.query(Call, Employee)
        .join(Employee, Call.employee_id == Employee.id)
        .filter(Call.qa_alarm == True)
        .filter(Call.overridden_score == None)
        .order_by(Call.created_at.desc())
        .all()
    )

    results = []
    for call, emp in calls[offset:offset + limit]:
        results.append({
            "call_id": call.id,
            "employee_id": call.employee_id,
            "employee_name": emp.name,
            "qa_alarm_reason": call.qa_alarm_reason,
            "qa_alarm_evidence": call.qa_alarm_evidence,
            "created_at": call.created_at,
            "original_score": call.evaluation_score
        })
    return results


@router.get("/template")
def download_template(
    current_user: Employee = Depends(get_current_user)
):
    """
    Returns a downloadable CSV template for bulk importing agents.
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.HR_MANAGER):
        raise HTTPException(status_code=403, detail="Only admins or HR managers can access onboarding templates.")
    
    csv_data = "Name,Email,Employee Code,Campaign,Phone Number,Role,Department\nJohn Doe,john.doe@example.com,EMP001,Sales,+1234567890,AGENT,Support\n"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=agent_import_template.csv"}
    )


@router.post("/preview")
def preview_bulk_agents(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Accepts a CSV/Excel file, parses it, validates constraints and uniqueness,
    and returns a preview of rows with error messages (without database commits).
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.HR_MANAGER):
        raise HTTPException(status_code=403, detail="Only admins or HR managers can preview onboarding files.")

    filename = file.filename.lower()
    try:
        contents = file.file.read()
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a .csv, .xlsx, or .xls file.")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    df = df.fillna("")
    # Normalize headers
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    # Map possible column names
    col_mapping = {
        "name": "name",
        "email": "email",
        "employee_code": "employee_code",
        "code": "employee_code",
        "campaign_name": "campaign_name",
        "campaign": "campaign_name",
        "phone_number": "phone_number",
        "phone": "phone_number",
        "role": "role",
        "department": "department",
        "password": "password"
    }
    df = df.rename(columns={c: col_mapping[c] for c in df.columns if c in col_mapping})

    # Validate that we have the minimum required columns
    required_cols = ["name", "email", "employee_code"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns in file: {', '.join([c.replace('_', ' ').title() for c in missing_cols])}"
        )

    preview_data = []
    seen_codes = set()
    seen_emails = set()

    for i, (_, row) in enumerate(df.iterrows()):
        idx = i + 1
        name = str(row.get("name", "")).strip()
        email = str(row.get("email", "")).strip()
        employee_code = str(row.get("employee_code", "")).strip()
        campaign_name = str(row.get("campaign_name", "")).strip()
        phone_number = str(row.get("phone_number", "")).strip()
        role = str(row.get("role", "AGENT")).strip().upper()
        department = str(row.get("department", "")).strip()

        errors = []

        # Name validation
        if not name:
            errors.append("Name is required.")

        # Email validation
        if not email:
            errors.append("Email is required.")
        elif "@" not in email:
            errors.append("Invalid email format.")
        else:
            db_emp_email = db.query(Employee).filter(Employee.email == email).first()
            if db_emp_email:
                errors.append(f"Email '{email}' is already registered.")
            if email in seen_emails:
                errors.append(f"Duplicate email '{email}' in upload file.")
            seen_emails.add(email)

        # Employee Code validation
        if not employee_code:
            errors.append("Employee code is required.")
        else:
            db_emp_code = db.query(Employee).filter(Employee.employee_code == employee_code).first()
            if db_emp_code:
                errors.append(f"Employee code '{employee_code}' is already registered.")
            if employee_code in seen_codes:
                errors.append(f"Duplicate employee code '{employee_code}' in upload file.")
            seen_codes.add(employee_code)

        # Campaign validation
        if campaign_name:
            db_camp = db.query(Campaign).filter(Campaign.name == campaign_name).first()
            if not db_camp:
                errors.append(f"Campaign '{campaign_name}' does not exist.")

        # Role validation
        valid_roles = [UserRole.AGENT.value, UserRole.QA.value, UserRole.ADMIN.value, UserRole.HR_MANAGER.value]
        if role not in valid_roles:
            errors.append(f"Invalid role '{role}'. Must be one of: {', '.join(valid_roles)}")

        preview_data.append({
            "index": idx,
            "name": name,
            "email": email,
            "employee_code": employee_code,
            "campaign_name": campaign_name,
            "phone_number": phone_number,
            "role": role,
            "department": department or campaign_name,
            "errors": errors,
            "isValid": len(errors) == 0
        })

    valid_count = sum(1 for item in preview_data if item["isValid"])
    summary = {
        "total": len(preview_data),
        "valid": valid_count,
        "invalid": len(preview_data) - valid_count
    }

    return {
        "data": preview_data,
        "summary": summary
    }


@router.post("/import", response_model=BulkEmployeeResult)
def import_bulk_agents(
    employees: List[dict],
    atomic: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Imports multiple agents. If atomic is True, any validation failure
    causes the entire import to fail. Otherwise, imports valid rows
    and reports failures on a per-row basis.
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.HR_MANAGER):
        raise HTTPException(status_code=403, detail="Only admins or HR managers can bulk import agents.")

    success_list = []
    failed_list = []
    seen_codes = set()
    seen_emails = set()

    # Pre-validation pass (especially important for atomic)
    all_validation_passed = True
    row_validation_errors = []

    for idx, item in enumerate(employees):
        row_num = item.get("index", idx + 1)
        name = str(item.get("name", "")).strip()
        email = str(item.get("email", "")).strip()
        employee_code = str(item.get("employee_code", "")).strip()
        campaign_name = str(item.get("campaign_name", "")).strip()
        phone_number = str(item.get("phone_number", "")).strip()
        role = str(item.get("role", "AGENT")).strip().upper()
        department = str(item.get("department", "")).strip()
        password = str(item.get("password", "")).strip()

        errors = []

        if not name:
            errors.append("Name is required.")
        if not email:
            errors.append("Email is required.")
        elif "@" not in email:
            errors.append("Invalid email format.")
        else:
            db_emp_email = db.query(Employee).filter(Employee.email == email).first()
            if db_emp_email:
                errors.append(f"Email '{email}' is already registered.")
            if email in seen_emails:
                errors.append(f"Duplicate email '{email}' in batch.")
            seen_emails.add(email)

        if not employee_code:
            errors.append("Employee code is required.")
        else:
            db_emp_code = db.query(Employee).filter(Employee.employee_code == employee_code).first()
            if db_emp_code:
                errors.append(f"Employee code '{employee_code}' is already registered.")
            if employee_code in seen_codes:
                errors.append(f"Duplicate employee code '{employee_code}' in batch.")
            seen_codes.add(employee_code)

        if campaign_name:
            db_camp = db.query(Campaign).filter(Campaign.name == campaign_name).first()
            if not db_camp:
                errors.append(f"Campaign '{campaign_name}' does not exist.")

        valid_roles = [UserRole.AGENT.value, UserRole.QA.value, UserRole.ADMIN.value, UserRole.HR_MANAGER.value]
        if role not in valid_roles:
            errors.append(f"Invalid role '{role}'. Must be one of: {', '.join(valid_roles)}")

        if password and len(password) < 6:
            errors.append("Password must be at least 6 characters long.")

        if errors:
            all_validation_passed = False
            error_str = " | ".join(errors)
            row_validation_errors.append((row_num, employee_code, error_str))

    # If atomic mode is requested and we have failures, fail the entire import
    if atomic and not all_validation_passed:
        failures = [
            BulkEmployeeFailure(index=row_num, employee_code=code, error=err)
            for row_num, code, err in row_validation_errors
        ]
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Atomic import failed. Some rows have validation errors, and no changes were made.",
                "success_count": 0,
                "failed_count": len(failures),
                "failed": [f.model_dump() for f in failures],
                "success": []
            }
        )

    # Now perform the actual inserts
    seen_codes = set()
    seen_emails = set()

    for idx, item in enumerate(employees):
        row_num = item.get("index", idx + 1)
        name = str(item.get("name", "")).strip()
        email = str(item.get("email", "")).strip()
        employee_code = str(item.get("employee_code", "")).strip()
        campaign_name = str(item.get("campaign_name", "")).strip()
        phone_number = str(item.get("phone_number", "")).strip()
        role = str(item.get("role", "AGENT")).strip().upper()
        department = str(item.get("department", "")).strip()
        password = str(item.get("password", "")).strip()

        errors = []
        if not name:
            errors.append("Name is required.")
        if not email:
            errors.append("Email is required.")
        elif "@" not in email:
            errors.append("Invalid email format.")
        else:
            db_emp_email = db.query(Employee).filter(Employee.email == email).first()
            if db_emp_email:
                errors.append(f"Email '{email}' is already registered.")
            if email in seen_emails:
                errors.append(f"Duplicate email '{email}' in batch.")
            seen_emails.add(email)

        if not employee_code:
            errors.append("Employee code is required.")
        else:
            db_emp_code = db.query(Employee).filter(Employee.employee_code == employee_code).first()
            if db_emp_code:
                errors.append(f"Employee code '{employee_code}' is already registered.")
            if employee_code in seen_codes:
                errors.append(f"Duplicate employee code '{employee_code}' in batch.")
            seen_codes.add(employee_code)

        if campaign_name:
            db_camp = db.query(Campaign).filter(Campaign.name == campaign_name).first()
            if not db_camp:
                errors.append(f"Campaign '{campaign_name}' does not exist.")

        valid_roles = [UserRole.AGENT.value, UserRole.QA.value, UserRole.ADMIN.value, UserRole.HR_MANAGER.value]
        if role not in valid_roles:
            errors.append(f"Invalid role '{role}'. Must be one of: {', '.join(valid_roles)}")

        if password and len(password) < 6:
            errors.append("Password must be at least 6 characters long.")

        if errors:
            failed_list.append(BulkEmployeeFailure(
                index=row_num,
                employee_code=employee_code,
                error=" | ".join(errors)
            ))
            continue

        if not password:
            password = f"Welcome_{employee_code}"

        try:
            hashed_pwd = get_password_hash(password)
            db_employee = Employee(
                name=name,
                email=email,
                employee_code=employee_code,
                hashed_password=hashed_pwd,
                role=UserRole(role),
                phone_number=phone_number if phone_number else None,
                department=department if department else (campaign_name if campaign_name else None)
            )
            db.add(db_employee)
            db.commit()
            db.refresh(db_employee)
            success_list.append(db_employee)
        except Exception as e:
            db.rollback()
            failed_list.append(BulkEmployeeFailure(
                index=row_num,
                employee_code=employee_code,
                error=f"Database insertion failed: {str(e)}"
            ))

    message = f"Bulk onboarding completed. Successfully imported {len(success_list)} agents."
    if failed_list:
        message += f" Failed to import {len(failed_list)} agents due to errors."

    return BulkEmployeeResult(
        success=success_list,
        failed=failed_list,
        message=message,
        success_count=len(success_list),
        failed_count=len(failed_list)
    )
