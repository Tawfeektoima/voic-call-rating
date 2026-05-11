import sys
import os

# Ensure the root directory is in the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal
from app.models import AgentViolation

def query_violations():
    db = SessionLocal()
    violations = db.query(AgentViolation).all()
    print(f"Found {len(violations)} violations in the database.")
    for v in violations:
        print(f"Call {v.call_id} | Agent {v.employee_id} | "
              f"{v.violation_id} | {v.penalty_tier} | "
              f"-{v.score_deduction}pts | HR: {v.hr_flagged}")
    db.close()

if __name__ == "__main__":
    query_violations()
