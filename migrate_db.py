import sqlite3
import os

db_path = 'call_rating.db'

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Adding review columns to 'calls' table...")
        cursor.execute("ALTER TABLE calls ADD COLUMN overridden_score FLOAT")
        cursor.execute("ALTER TABLE calls ADD COLUMN reviewer_notes TEXT")
        cursor.execute("ALTER TABLE calls ADD COLUMN reviewed_at DATETIME")
        conn.commit()
        print("Columns added successfully.")
    except sqlite3.OperationalError as e:
        print(f"Notice: {e} (Columns might already exist)")
    finally:
        conn.close()
else:
    print(f"Database {db_path} not found. It will be created by SQLAlchemy with the correct schema.")
