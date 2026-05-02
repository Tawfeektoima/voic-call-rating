from app.database import SessionLocal
from app.models import SystemLog
import sys

db = SessionLocal()
try:
    logs = db.query(SystemLog).order_by(SystemLog.id.desc()).limit(10).all()
    if not logs:
        print("No logs found.")
    for l in logs:
        print(f"ID: {l.id}, Call ID: {l.call_id}, Error Type: {l.error_type}, Message: {l.error_message[:100]}")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
