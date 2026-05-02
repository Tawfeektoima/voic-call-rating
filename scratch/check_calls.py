from app.database import SessionLocal
from app.models import Call
import sys

db = SessionLocal()
try:
    calls = db.query(Call).order_by(Call.id.desc()).limit(10).all()
    if not calls:
        print("No calls found in database.")
    for c in calls:
        print(f"ID: {c.id}, Status: {c.status.value}, Created: {c.created_at}")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
