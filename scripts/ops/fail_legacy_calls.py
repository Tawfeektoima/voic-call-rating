import sys
import os

# Ensure the app directory is in the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal
from app.models import Call, CallStatus

def fail_legacy_calls(cutoff_id=65):
    db = SessionLocal()
    try:
        legacy_calls = db.query(Call).filter(
            Call.status.in_([CallStatus.PENDING, CallStatus.PROCESSING]),
            Call.id <= cutoff_id
        ).all()
        
        if not legacy_calls:
            print(f"No stuck legacy calls found (ID <= {cutoff_id}).")
            return
            
        print(f"Found {len(legacy_calls)} legacy calls to fail.")
        
        for call in legacy_calls:
            call.status = CallStatus.FAILED
            call.error_message = "Legacy call before v2 evaluation pipeline"
            
        db.commit()
        print("Successfully marked legacy calls as FAILED.")
        
    except Exception as e:
        db.rollback()
        print(f"Error failing legacy calls: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fail_legacy_calls()
