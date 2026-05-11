# ⚠️ DESTRUCTIVE OPERATION — This script deletes data permanently.
import argparse
import sys
import os

# Add project root to sys.path to allow running from within scripts/ops/
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def clear_calls():
    from app.database import engine
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM calls"))
            conn.commit()
            print("Successfully cleared calls table.")
    except Exception as e:
        print(f"Error clearing calls: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required: confirms you intend to clear all call data."
    )
    args = parser.parse_args()

    if not args.confirm:
        print("Aborted. This is a destructive operation.")
        print("Pass --confirm to execute: python scripts/ops/clear_calls.py --confirm")
        sys.exit(1)
        
    clear_calls()
