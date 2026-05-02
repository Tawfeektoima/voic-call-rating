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
from app.services.evaluation import evaluate_transcript
from app.worker import process_call_audio_task

settings = get_settings()

router = APIRouter(prefix="/api/audio", tags=["Audio Processing"])

# Ensure upload dir exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)



@router.post("/upload", response_model=CallUploadResponse)
async def upload_audio(
    employee_id: int = Form(...),
    campaign_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload an audio file. Validates size/format, saves locally, and triggers processing.
    """
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

    # Read file content to check size and save
    file_content = await file.read()
    if len(file_content) > settings.max_file_size_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds max size of {settings.MAX_FILE_SIZE_MB}MB")

    # 3. Save locally
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as f:
        f.write(file_content)

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
def get_call_status(call_id: int, db: Session = Depends(get_db)):
    """Retrieve the status and results of a call."""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@router.get("/{call_id}/file")
def get_call_audio_file(call_id: int, db: Session = Depends(get_db)):
    """Stream the actual audio file for playback."""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call or not call.audio_file_path:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    if not os.path.exists(call.audio_file_path):
        raise HTTPException(status_code=404, detail="File on disk not found")
        
    from fastapi.responses import FileResponse
    return FileResponse(call.audio_file_path)


@router.patch("/{call_id}/review", response_model=CallOut)
def review_call(
    call_id: int, 
    review: CallReviewUpdate, 
    db: Session = Depends(get_db)
):
    """Update a call with supervisor override score and notes."""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    call.overridden_score = review.overridden_score
    call.reviewer_notes = review.reviewer_notes
    call.reviewed_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(call)
    return call
