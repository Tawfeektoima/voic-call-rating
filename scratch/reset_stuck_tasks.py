from app.database import SessionLocal
from app.models import Call, CallStatus

db = SessionLocal()
try:
    # Reset all 'processing' tasks to 'pending' if they were stuck
    stuck_calls = db.query(Call).filter(Call.status == CallStatus.PROCESSING).all()
    if not stuck_calls:
        print("No stuck calls found.")
    else:
        for c in stuck_calls:
            print(f"Resetting Call ID {c.id} from 'processing' to 'pending'")
            c.status = CallStatus.PENDING
        db.commit()
        print(f"Successfully reset {len(stuck_calls)} calls.")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
