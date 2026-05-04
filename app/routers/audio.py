import os
import shutil
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks, Form
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models import Call, Employee, Campaign, CallStatus
from app.schemas import CallUploadResponse, CallOut, CallReviewUpdate
from app.config import get_settings
from app.services.transcription import transcriber
from app.services.analysis import evaluate_transcript
from app.worker import process_call_audio_task
from app.routers.auth import get_current_user
from app.models import UserRole

settings = get_settings()

router = APIRouter(prefix="/api/audio", tags=["Audio Processing"])

# Ensure upload dir exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)



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
                os.remove(file_path)
                raise HTTPException(status_code=400, detail=f"File exceeds max size of {settings.MAX_FILE_SIZE_MB}MB")
            f.write(chunk)

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


@router.get("/{call_id}", response_model=CallOut)
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
        
    return call


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
    
    call.overridden_score = review.overridden_score
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
