import os
import shutil
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks, Form
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models import Call, Employee, Campaign, CallStatus
from app.schemas import CallUploadResponse, CallOut
from app.config import get_settings
from app.services.transcription import transcriber
from app.services.evaluation import evaluate_transcript

settings = get_settings()

router = APIRouter(prefix="/api/audio", tags=["Audio Processing"])

# Ensure upload dir exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

def process_call_background(call_id: int):
    """
    Background task to process audio:
    1. Transcribe (WhisperX + Pyannote)
    2. Evaluate (Groq)
    3. Update DB status at each step.
    """
    db = SessionLocal()
    try:
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            print(f"[!] Background Task: Call ID {call_id} not found.")
            return

        # 1. Start Processing
        call.status = CallStatus.PROCESSING
        db.commit()

        # 2. Transcribe & Diarize
        try:
            transcript, duration = transcriber.process_audio(call.audio_file_path)
            call.transcript = transcript
            call.audio_duration = duration
            call.status = CallStatus.TRANSCRIBED
            db.commit()
            print(f"[*] Transcription complete for Call {call_id}")
        except Exception as e:
            call.status = CallStatus.FAILED
            call.error_message = f"Transcription Error: {str(e)}"
            db.commit()
            return

        # 3. Evaluate with Groq
        try:
            # Fetch Campaign for prompt
            campaign = db.query(Campaign).filter(Campaign.id == call.campaign_id).first()
            if not campaign:
                raise ValueError("Campaign not found for evaluation.")

            eval_result = evaluate_transcript(call.transcript, campaign.evaluation_prompt)
            
            call.reasoning = eval_result.reasoning
            call.evaluation_score = eval_result.score
            # Serialize the Pydantic models to dicts for JSON storage
            call.strengths = eval_result.strengths
            call.weaknesses = [w.model_dump() for w in eval_result.weaknesses]
            call.status = CallStatus.EVALUATED
            call.processed_at = datetime.now(timezone.utc)
            db.commit()
            print(f"[*] Evaluation complete for Call {call_id}. Score: {eval_result.score}")
            
        except Exception as e:
            call.status = CallStatus.FAILED
            call.error_message = f"Evaluation Error: {str(e)}"
            db.commit()
            return

    except Exception as e:
        print(f"[!] Unhandled background task error: {e}")
    finally:
        db.close()


@router.post("/upload", response_model=CallUploadResponse)
async def upload_audio(
    background_tasks: BackgroundTasks,
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

    # 5. Trigger Background Task
    background_tasks.add_task(process_call_background, new_call.id)

    return CallUploadResponse(call_id=new_call.id)


@router.get("/{call_id}", response_model=CallOut)
def get_call_status(call_id: int, db: Session = Depends(get_db)):
    """Retrieve the status and results of a call."""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call
