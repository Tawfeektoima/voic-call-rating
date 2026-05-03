from app.database import engine
from sqlalchemy import text

def clear_calls():
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM calls"))
            conn.commit()
            print("Successfully cleared calls table.")
    except Exception as e:
        print(f"Error clearing calls: {e}")

if __name__ == "__main__":
    clear_calls()
