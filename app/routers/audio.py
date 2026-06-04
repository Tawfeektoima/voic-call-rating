import json
from typing import List
import os
import shutil
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks, Form, Query
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models import Call, Employee, Campaign, CallStatus, ScoreOverrideAudit
from app.schemas import CallUploadResponse, CallOut, CallReviewUpdate, CallDetailResponse, DeductionItem, ViolationItemOut, BulkCallItemResult, BulkCallUploadResponse
from app.config import get_settings
from app.services.transcription import transcriber
from app.services.analysis import evaluate_transcript
from app.worker import process_call_audio_task
from app.routers.auth import get_current_user
from app.models import UserRole, AgentViolation
from app.services.audit import log_audit_event

settings = get_settings()

router = APIRouter(prefix="/api/audio", tags=["Audio Processing"])

# Ensure upload dir exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


def _remove_file_if_exists(file_path: str):
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass



@router.post("/upload", response_model=CallUploadResponse)
async def upload_audio(
    employee_id: int = Form(...),
    campaign_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Upload an audio file. Validates size/format, saves locally, and triggers processing.
    """
    # 0. Role Check: Agent can only upload for themselves
    if current_user.role == UserRole.AGENT and current_user.id != employee_id:
        raise HTTPException(status_code=403, detail="Agents can only upload calls for themselves.")

    # 1. Validate relations
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # 2. Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.allowed_extensions_list:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {settings.ALLOWED_EXTENSIONS}")

    # 3. Save locally using streaming
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    saved_size = 0
    with open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            saved_size += len(chunk)
            if saved_size > settings.max_file_size_bytes:
                f.close()
                _remove_file_if_exists(file_path)
                raise HTTPException(status_code=400, detail=f"File exceeds max size of {settings.MAX_FILE_SIZE_MB}MB")
            f.write(chunk)

    if saved_size == 0:
        _remove_file_if_exists(file_path)
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # 4. Create DB Record
    new_call = Call(
        employee_id=employee_id,
        campaign_id=campaign_id,
        audio_file_path=file_path,
        original_filename=file.filename,
        status=CallStatus.PENDING
    )
    db.add(new_call)
    db.commit()
    db.refresh(new_call)

    # 5. Trigger Celery Task
    process_call_audio_task.delay(new_call.id)

    return CallUploadResponse(call_id=new_call.id)


@router.post("/bulk-upload", response_model=BulkCallUploadResponse)
async def bulk_upload_audio(
    files: List[UploadFile] = File(...),
    metadata: str = Form(...),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Upload multiple audio files. Maps each file to metadata, validates each
    individually, saves valid files, creates Call records, and triggers
    background task processing. Returns a detailed success/failure report.
    """
    try:
        meta_list = json.loads(metadata)
        if not isinstance(meta_list, list):
            raise ValueError()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid metadata format. Must be a JSON-serialized list of mapping objects."
        )

    meta_map = {}
    for item in meta_list:
        fname = item.get("filename")
        if fname:
            meta_map[fname] = item

    results = []
    success_count = 0
    failed_count = 0

    for file in files:
        filename = file.filename
        meta = meta_map.get(filename)
        
        if not meta:
            failed_count += 1
            results.append(BulkCallItemResult(
                filename=filename,
                success=False,
                error=f"No metadata found for file '{filename}'"
            ))
            continue

        employee_id = meta.get("employee_id")
        campaign_id = meta.get("campaign_id")

        if employee_id is None or campaign_id is None:
            failed_count += 1
            results.append(BulkCallItemResult(
                filename=filename,
                success=False,
                error="Metadata must contain both employee_id and campaign_id"
            ))
            continue

        try:
            employee_id = int(employee_id)
            campaign_id = int(campaign_id)
        except ValueError:
            failed_count += 1
            results.append(BulkCallItemResult(
                filename=filename,
                success=False,
                error="employee_id and campaign_id must be integers"
            ))
            continue

        if current_user.role == UserRole.AGENT and current_user.id != employee_id:
            failed_count += 1
            results.append(BulkCallItemResult(
                filename=filename,
                success=False,
                error="Agents can only upload calls for themselves"
            ))
            continue

        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            failed_count += 1
            results.append(BulkCallItemResult(
                filename=filename,
                success=False,
                error=f"Employee with ID {employee_id} not found"
            ))
            continue

        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            failed_count += 1
            results.append(BulkCallItemResult(
                filename=filename,
                success=False,
                error=f"Campaign with ID {campaign_id} not found"
            ))
            continue

        ext = os.path.splitext(filename)[1].lower()
        if ext not in settings.allowed_extensions_list:
            failed_count += 1
            results.append(BulkCallItemResult(
                filename=filename,
                success=False,
                error=f"Invalid file type. Allowed: {settings.ALLOWED_EXTENSIONS}"
            ))
            continue

        unique_filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        
        try:
            saved_size = 0
            size_exceeded = False
            with open(file_path, "wb") as f:
                while chunk := await file.read(1024 * 1024):
                    saved_size += len(chunk)
                    if saved_size > settings.max_file_size_bytes:
                        size_exceeded = True
                        break
                    f.write(chunk)

            if size_exceeded:
                _remove_file_if_exists(file_path)
                failed_count += 1
                results.append(BulkCallItemResult(
                    filename=filename,
                    success=False,
                    error=f"File exceeds max size of {settings.MAX_FILE_SIZE_MB}MB"
                ))
                continue

            if saved_size == 0:
                _remove_file_if_exists(file_path)
                failed_count += 1
                results.append(BulkCallItemResult(
                    filename=filename,
                    success=False,
                    error="Uploaded file is empty"
                ))
                continue

            new_call = Call(
                employee_id=employee_id,
                campaign_id=campaign_id,
                audio_file_path=file_path,
                original_filename=filename,
                status=CallStatus.PENDING
            )
            db.add(new_call)
            db.commit()
            db.refresh(new_call)

            process_call_audio_task.delay(new_call.id)

            success_count += 1
            results.append(BulkCallItemResult(
                filename=filename,
                success=True,
                call_id=new_call.id
            ))

        except Exception as e:
            db.rollback()
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            failed_count += 1
            results.append(BulkCallItemResult(
                filename=filename,
                success=False,
                error=f"Internal error processing file: {str(e)}"
            ))

    message = f"Bulk upload completed. Successfully processed {success_count} files."
    if failed_count > 0:
        message += f" Failed to process {failed_count} files."

    return BulkCallUploadResponse(
        results=results,
        success_count=success_count,
        failed_count=failed_count,
        message=message
    )


@router.get("/{call_id}", response_model=CallDetailResponse)
def get_call_status(
    call_id: int, 
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Retrieve the status and results of a call."""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Role Check
    if current_user.role == UserRole.AGENT and call.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to view this call.")
        
    # Build structured response for UI (Task-UI04)
    violations = db.query(AgentViolation).filter(AgentViolation.call_id == call_id).all()
    
    # Map weaknesses to deductions
    deductions = []
    if call.weaknesses:
        # call.weaknesses is a list of dicts: {"issue": "...", "detail": "...", "deduction": 5}
        # In validate_json_fields it might already be a list
        weaknesses_list = call.weaknesses
        if isinstance(weaknesses_list, str):
            import json
            try: weaknesses_list = json.loads(weaknesses_list)
            except: weaknesses_list = []
            
        for w in weaknesses_list:
            # Try to extract score/max from explicit fields or fallback to string parsing
            score = w.get("score")
            max_val = w.get("max")
            
            if score is None or max_val is None:
                detail = w.get("detail", "")
                if "Score:" in detail and "/" in detail:
                    try:
                        parts = detail.split("Score:")[1].split("/")
                        score = float(parts[0].strip())
                        max_val = float(parts[1].strip())
                    except: 
                        score, max_val = 0.0, 0.0
                else:
                    score, max_val = 0.0, 0.0
            
            deductions.append(DeductionItem(
                category=w.get("issue", "Unknown"),
                deduction=float(w.get("deduction", 0)),
                score=float(score),
                max=float(max_val)
            ))

    # Retrieve score override audits
    audits = db.query(ScoreOverrideAudit).filter(ScoreOverrideAudit.call_id == call_id).order_by(ScoreOverrideAudit.created_at.desc()).all()

    # Prepare base data
    response_data = CallOut.model_validate(call).model_dump()
    
    # Update with structured UI fields (Task-UI04)
    response_data.update({
        "ai_summary": call.call_summary,
        "strengths": call.strengths or [],
        "deductions": deductions,
        "violations": [
            ViolationItemOut(
                violation_id=v.violation_id,
                severity=v.severity,
                timestamp=v.timestamp_in_call,
                evidence=v.evidence
            ) for v in violations
        ],
        "override_audits": audits
    })

    return CallDetailResponse(**response_data)


@router.get("/{call_id}/file")
def get_call_audio_file(
    call_id: int, 
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Stream the actual audio file for playback."""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call or not call.audio_file_path:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Role Check
    if current_user.role == UserRole.AGENT and call.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this file.")
    
    if not os.path.exists(call.audio_file_path):
        raise HTTPException(status_code=404, detail="File on disk not found")
        
    from fastapi.responses import FileResponse
    return FileResponse(call.audio_file_path)


@router.patch("/{call_id}/review", response_model=CallOut)
def review_call(
    call_id: int, 
    review: CallReviewUpdate, 
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Update a call with supervisor override score and notes."""
    # Role Check: Only QA and Admin can review calls
    if current_user.role == UserRole.AGENT:
        raise HTTPException(status_code=403, detail="Agents cannot review calls.")

    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Store audit record if score is being changed/overridden
    if review.overridden_score is not None and review.overridden_score != call.overridden_score:
        old_score = call.overridden_score if call.overridden_score is not None else call.evaluation_score
        audit_log = ScoreOverrideAudit(
            call_id=call.id,
            reviewer_id=current_user.id,
            reviewer_name=current_user.name,
            old_score=old_score,
            new_score=review.overridden_score,
            reason=review.reason or review.reviewer_notes or "Manual override",
            created_at=datetime.now(timezone.utc)
        )
        db.add(audit_log)

        # Log audit event (Task 0.8)
        log_audit_event(
            db=db,
            action="SCORE_OVERRIDE",
            actor_id=current_user.id,
            actor_email=current_user.email,
            target=f"Call #{call.id}",
            before_state=str(old_score),
            after_state=str(review.overridden_score),
            reason=review.reason or review.reviewer_notes or "Manual override"
        )
        
        # Override clears any active QA alarm and sets needs_review to False
        call.needs_review = False
    
    call.overridden_score = review.overridden_score
    if review.reviewer_notes is not None:
        call.reviewer_notes = review.reviewer_notes
    call.reviewed_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(call)
    return call


@router.patch("/{call_id}/lead-status", response_model=CallOut)
def update_lead_status(
    call_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    # Role Check
    if current_user.role == UserRole.AGENT:
        raise HTTPException(status_code=403, detail="Agents cannot update lead status.")

    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    call.lead_status = status.lower()
    db.commit()
    db.refresh(call)
    return call


