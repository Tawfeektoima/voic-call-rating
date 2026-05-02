import os
from app.database import SessionLocal, engine, Base
from app.models import Call
from app.config import get_settings

# Create any missing tables (like the new SystemLog)
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
    print("WARNING: This will delete ALL call records and audio files.")
    confirm = input("Type 'YES' to confirm: ")
    if confirm == "YES":
        purge_data()
        print("Purge complete.")
    else:
        print("Operation cancelled.")
