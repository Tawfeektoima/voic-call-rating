from app.database import engine
from sqlalchemy import text

def fix_roles():
    try:
        with engine.connect() as conn:
            conn.execute(text("UPDATE employees SET role = UPPER(role)"))
            conn.commit()
            print("Successfully updated roles to uppercase in DB.")
    except Exception as e:
        print(f"Error updating roles: {e}")

if __name__ == "__main__":
    fix_roles()
