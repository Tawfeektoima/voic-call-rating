from datetime import datetime, timedelta, timezone
from app.database import SessionLocal
from app.models import Call, CallStatus
from app.worker import process_call_audio_task

def recover_stuck_tasks():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        timeout_threshold = now - timedelta(minutes=5)

        stuck_processing = db.query(Call).filter(Call.status == CallStatus.PROCESSING).all()
        failed_tasks = db.query(Call).filter(Call.status == CallStatus.FAILED).all()
        pending_timeouts = db.query(Call).filter(
            Call.status == CallStatus.PENDING,
            Call.created_at < timeout_threshold
        ).all()

        vulnerable_calls = stuck_processing + failed_tasks + pending_timeouts

        if not vulnerable_calls:
            print("Summary: 0 stuck or failed calls found. System is clean.")
            return

        for call in stuck_processing + failed_tasks:
            call.status = CallStatus.PENDING
        
        db.commit()

        for call in vulnerable_calls:
            process_call_audio_task.delay(call.id)

    except Exception as e:
        db.rollback()
        print(f"Error during task recovery: {str(e)}")
    finally:
        db.close()
