import csv
import io
import json
import re
import zipfile
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models import Call, Campaign, UserRole, Employee
from app.routers.auth import get_current_user
from app.services.export import ExportService
from app.services.audit import log_audit_event
from app.permissions import Permission, has_permission

router = APIRouter(prefix="/api/export", tags=["Data Export"])

def _export_filters_summary(
    campaign_id: Optional[int] = None,
    department: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    agent_role: Optional[UserRole] = None,
) -> str:
    filters_info = []
    if campaign_id is not None:
        filters_info.append(f"Campaign ID: {campaign_id}")
    if department:
        filters_info.append(f"Department: {department}")
    if start_date:
        filters_info.append(f"Start Date: {start_date}")
    if end_date:
        filters_info.append(f"End Date: {end_date}")
    if agent_role:
        filters_info.append(f"Agent Role: {agent_role}")
    return ", ".join(filters_info) if filters_info else "No filters"

def _audit_export_attempt(
    db: Session,
    current_user: Employee,
    target: str,
    filters_str: str,
    success: bool,
    reason: str,
):
    log_audit_event(
        db=db,
        action="EXPORT",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=target,
        before_state=None,
        after_state=filters_str,
        reason=reason,
        success=success,
    )

def _deny_export(
    db: Session,
    current_user: Employee,
    target: str,
    filters_str: str,
):
    _audit_export_attempt(
        db=db,
        current_user=current_user,
        target=target,
        filters_str=filters_str,
        success=False,
        reason="Access denied",
    )
    raise HTTPException(
        status_code=403,
        detail="Only admins, QA, and HR managers are authorized to export data."
    )

def redact_text(text: str) -> str:
    """Regex-based PII redaction logic for exportable transcript text."""
    if not text:
        return ""
    patterns = [
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]'),
        (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]'),
        (r'\b(?:\d[ -]*?){13,16}\b', '[CARD_REDACTED]'),
        (r'\b(?:\+\d{1,2}[-\s]?)?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}\b', '[PHONE_REDACTED]'),
        (r'(?i)\b(?:dob|date of birth)\b\s*[:#-]?\s*(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})', '[DOB_REDACTED]'),
        (r'(?i)\baccount\s*(?:id|number|no\.?|#)\s*[:#-]?\s*[A-Z0-9-]{3,}\b', '[ACCOUNT_ID_REDACTED]'),
        (r'(?i)\bcustomer\s*(?:id|number|no\.?|#)\s*[:#-]?\s*[A-Z0-9-]{3,}\b', '[CUSTOMER_ID_REDACTED]'),
        (r'(?i)\b(?:transcript|session|call)\s*(?:id|number|no\.?|#)\s*[:#-]?\s*[A-Z0-9-]{3,}\b', '[TRANSCRIPT_ID_REDACTED]'),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text

def redact_transcript(transcript_data, current_user_role) -> any:
    """Helper to redact transcript segment text fields if the user is not an admin."""
    if current_user_role == UserRole.ADMIN:
        return transcript_data
    if not transcript_data:
        return transcript_data
    
    # If transcript_data is a string (legacy)
    if isinstance(transcript_data, str):
        return redact_text(transcript_data)
        
    # If transcript_data is a list of dicts/objects
    if isinstance(transcript_data, list):
        redacted_list = []
        for segment in transcript_data:
            if isinstance(segment, dict):
                segment_copy = dict(segment)
                if "text" in segment_copy and isinstance(segment_copy["text"], str):
                    segment_copy["text"] = redact_text(segment_copy["text"])
                redacted_list.append(segment_copy)
            elif hasattr(segment, "model_dump"):
                segment_copy = segment.model_dump()
                if "text" in segment_copy and isinstance(segment_copy["text"], str):
                    segment_copy["text"] = redact_text(segment_copy["text"])
                redacted_list.append(segment_copy)
            elif hasattr(segment, '__dict__'):
                segment_copy = dict(segment.__dict__)
                if "text" in segment_copy and isinstance(segment_copy["text"], str):
                    segment_copy["text"] = redact_text(segment_copy["text"])
                redacted_list.append(segment_copy)
            else:
                redacted_list.append(segment)
        return redacted_list
    return transcript_data


@router.get("/csv")
def export_calls_csv(
    campaign_id: Optional[int] = None,
    department: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    agent_role: Optional[UserRole] = None,
    offset: int = Query(0, ge=0, description="Result offset"),
    limit: int = Query(5000, ge=1, le=5000, description="Maximum rows to export"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Export all calls metadata to a streamable CSV.
    """
    if not has_permission(current_user, Permission.EXPORT_DATA):
        filters_str = _export_filters_summary(campaign_id, department, start_date, end_date, agent_role)
        _deny_export(db, current_user, "CSV Export", filters_str)

    filters_str = _export_filters_summary(campaign_id, department, start_date, end_date, agent_role)
    _audit_export_attempt(db, current_user, "CSV Export", filters_str, True, "Data Export")

    query = db.query(Call).join(Employee)
    if campaign_id:
        query = query.filter(Call.campaign_id == campaign_id)
    if department:
        query = query.filter(Employee.department == department)
    if agent_role:
        query = query.filter(Employee.role == agent_role)
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(Call.created_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format.")
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(Call.created_at <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO format.")
    
    calls = query.order_by(Call.id).offset(offset).limit(limit).all()

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        "call_id", "date", "agent_id", "campaign_id", "duration", 
        "qa_score", "lead_status", "is_golden_moment", "tags",
        "primary_outcome", "outcome_value", "talk_ratio", "follow_up_required",
        "campaign_specific_data"
    ])

    for call in calls:
        outcome = call.outcome
        writer.writerow([
            call.id,
            call.created_at.isoformat(),
            call.employee_id,
            call.campaign_id,
            call.audio_duration,
            call.overridden_score or call.evaluation_score,
            call.lead_status.value if hasattr(call.lead_status, 'value') else (call.lead_status or "N/A"),
            call.is_golden_moment,
            json.dumps(call.tags) if call.tags else "[]",
            outcome.primary_outcome if outcome else "N/A",
            outcome.outcome_value if outcome else 0.0,
            outcome.talk_ratio if outcome else 0.0,
            outcome.follow_up_required if outcome else False,
            json.dumps(outcome.campaign_specific_data) if outcome and outcome.campaign_specific_data else "{}"
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=voiceqa_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"}
    )


@router.get("/xlsx")
def export_dataset_xlsx(
    campaign_id: Optional[int] = None,
    department: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    agent_role: Optional[UserRole] = None,
    offset: int = Query(0, ge=0, description="Result offset"),
    limit: int = Query(5000, ge=1, le=5000, description="Maximum rows to export"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Export a Data-Science-Ready .xlsx dataset with ~50 columns.
    Includes multi-table joins, JSON flattening, acoustic emotion %,
    temporal features, and formatted headers (Task 64).
    """
    if not has_permission(current_user, Permission.EXPORT_DATA):
        filters_str = _export_filters_summary(campaign_id, department, start_date, end_date, agent_role)
        _deny_export(db, current_user, "XLSX Export", filters_str)

    # Parse date ranges
    start_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format.")
    end_dt = None
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO format.")

    filters_str = _export_filters_summary(campaign_id, department, start_date, end_date, agent_role)
    _audit_export_attempt(db, current_user, "XLSX Export", filters_str, True, "Data Export")

    df_master, df_qa, df_ann = ExportService.build_dataset(
        db,
        campaign_id=campaign_id,
        department=department,
        start_date=start_dt,
        end_date=end_dt,
        agent_role=agent_role,
        current_user_role=current_user.role,
        offset=offset,
        limit=limit,
    )

    if df_master.empty:
        raise HTTPException(status_code=404, detail="No evaluated calls found for export.")

    buffer = ExportService.to_styled_xlsx(df_master, df_qa, df_ann)

    filename = f"voiceqa_dataset_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/transcripts")
def export_transcripts_zip(
    campaign_id: Optional[int] = None,
    department: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    agent_role: Optional[UserRole] = None,
    offset: int = Query(0, ge=0, description="Result offset"),
    limit: int = Query(5000, ge=1, le=5000, description="Maximum rows to export"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Zip all transcripts matching the filters.
    """
    if not has_permission(current_user, Permission.EXPORT_DATA):
        filters_str = _export_filters_summary(campaign_id, department, start_date, end_date, agent_role)
        _deny_export(db, current_user, "ZIP Transcripts Export", filters_str)

    filters_str = _export_filters_summary(campaign_id, department, start_date, end_date, agent_role)
    _audit_export_attempt(db, current_user, "ZIP Transcripts Export", filters_str, True, "Transcript Export")

    query = db.query(Call).join(Employee)
    if campaign_id:
        query = query.filter(Call.campaign_id == campaign_id)
    if department:
        query = query.filter(Employee.department == department)
    if agent_role:
        query = query.filter(Employee.role == agent_role)
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(Call.created_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format.")
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(Call.created_at <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO format.")

    calls = query.order_by(Call.id).offset(offset).limit(limit).all()
    if not calls:
        raise HTTPException(status_code=404, detail="No calls found matching current filters.")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for call in calls:
            transcript = call.transcript
            if transcript:
                transcript = redact_transcript(transcript, current_user.role)
            else:
                transcript = "No transcript available"
            
            summary = call.call_summary or ""
            if current_user.role != UserRole.ADMIN:
                summary = redact_text(summary)
            
            file_name = f"call_{call.id}_transcript.json"
            data = {
                "call_id": call.id,
                "agent_id": call.employee_id,
                "transcript": transcript,
                "summary": summary,
                "score": call.overridden_score or call.evaluation_score
            }
            zip_file.writestr(file_name, json.dumps(data, indent=2))

    zip_buffer.seek(0)
    filename = f"campaign_{campaign_id}_transcripts.zip" if campaign_id else f"transcripts_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
