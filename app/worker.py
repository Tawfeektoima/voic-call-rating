import os
import gc
import torch
from celery import Celery
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import Call, Campaign, CallStatus, SystemLog
from app.services.transcription import transcriber
from app.services.evaluation import evaluate_transcript
from app.config import get_settings

settings = get_settings()

# Initialize Celery
celery_app = Celery("call_rating_worker", broker=settings.CELERY_BROKER_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_max_tasks_per_child=1, # CRITICAL: Force worker restart after every task to clear VRAM
    # --- RACE CONDITION PREVENTIONS ---
    broker_transport_options={
        "visibility_timeout": 3600,  # 1 hour (Prevent Redis from re-delivering long tasks)
    },
    task_acks_late=False,            # Acknowledge immediately to remove from queue
    worker_prefetch_multiplier=1,    # Only take one task at a time
)

def print_worker_vram(stage: str):
    import torch
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / (1024**3)
        reserved = torch.cuda.memory_reserved() / (1024**3)
        free_mem, total_mem = torch.cuda.mem_get_info()
        print(f"\n⚙️ [Worker VRAM | {stage}]")
        print(f"   ├─ PyTorch Allocated: {allocated:.2f} GB")
        print(f"   ├─ PyTorch Reserved : {reserved:.2f} GB")
        print(f"   └─ System Free VRAM : {free_mem/(1024**3):.2f} / {total_mem/(1024**3):.2f} GB\n")

@celery_app.task(bind=True, name="process_call_audio")
def process_call_audio_task(self, call_id: int):
    """
    Background task to process audio:
    1. Transcribe (WhisperX + Pyannote)
    2. Evaluate (Groq)
    """
    print_worker_vram(f"PRE-TASK - Call ID {call_id}")
    db = SessionLocal()
    try:
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            print(f"[!] Background Task: Call ID {call_id} not found.")
            return

        # 1. Idempotency Check & Start Processing
        if call.status in [CallStatus.PROCESSING, CallStatus.TRANSCRIBED, CallStatus.EVALUATED]:
            print(f"[*] Call {call_id} is already in state '{call.status.value}'. Skipping duplicate task.")
            return

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
            print_worker_vram(f"POST-TRANSCRIPTION - Call ID {call_id}")
        except Exception as e:
            call.status = CallStatus.FAILED
            call.error_message = f"Transcription Error: {str(e)}"
            
            error_type = "CUDA_OOM" if "CUDA out of memory" in str(e) else "TRANSCRIPTION_ERROR"
            sys_log = SystemLog(call_id=call_id, error_type=error_type, error_message=str(e))
            db.add(sys_log)
            
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
            call.strengths = eval_result.strengths
            call.weaknesses = [w.model_dump() for w in eval_result.weaknesses]
            call.status = CallStatus.EVALUATED
            call.processed_at = datetime.now(timezone.utc)
            db.commit()
            print(f"[*] Evaluation complete for Call {call_id}. Score: {eval_result.score}")
            
        except Exception as e:
            call.status = CallStatus.FAILED
            call.error_message = f"Evaluation Error: {str(e)}"
            
            sys_log = SystemLog(call_id=call_id, error_type="EVALUATION_ERROR", error_message=str(e))
            db.add(sys_log)
            
            db.commit()
            return

    except Exception as e:
        print(f"[!] Unhandled background task error: {e}")
        try:
            sys_log = SystemLog(call_id=call_id, error_type="UNHANDLED_ERROR", error_message=str(e))
            db.add(sys_log)
            db.commit()
        except:
            pass
    finally:
        print_worker_vram(f"END-TASK - Call ID {call_id}")
        db.close()
        # Explicitly clear VRAM and collect garbage before process exit
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
