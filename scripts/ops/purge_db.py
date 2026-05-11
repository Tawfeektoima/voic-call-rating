# ⚠️ DESTRUCTIVE OPERATION — This script deletes data permanently.
import argparse
import sys
import os

# Add project root to sys.path to allow running from within scripts/ops/
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

parser = argparse.ArgumentParser()
parser.add_argument(
    "--confirm",
    action="store_true",
    help="Required: confirms you intend to delete all call data permanently."
)
args = parser.parse_args()

if not args.confirm:
    print("Aborted. This is a destructive operation.")
    print("Pass --confirm to execute: python scripts/ops/purge_db.py --confirm")
    sys.exit(1)

from app.database import SessionLocal, engine, Base
from app.models import Call
from app.config import get_settings

# Create any missing tables
Base.metadata.create_all(bind=engine)

settings = get_settings()

def purge_data():
    db = SessionLocal()
    try:
        # Delete all calls
        num_deleted = db.query(Call).delete()
        db.commit()
        print(f"Deleted {num_deleted} records from the 'calls' table.")
        
        # Clean uploads folder
        upload_dir = settings.UPLOAD_DIR
        if os.path.exists(upload_dir):
            for filename in os.listdir(upload_dir):
                file_path = os.path.join(upload_dir, filename)
                try:
                    if os.path.isfile(file_path) and not filename.startswith('.'):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")
            print(f"Cleared contents of the '{upload_dir}' directory.")
        else:
            os.makedirs(upload_dir, exist_ok=True)
            print(f"Created '{upload_dir}' directory.")
            
    except Exception as e:
        db.rollback()
        print(f"Error purging data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    purge_data()
    print("Purge complete.")
