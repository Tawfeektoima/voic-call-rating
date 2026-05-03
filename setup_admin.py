from app.database import SessionLocal
from app.models import Employee, UserRole
from app.security import get_password_hash

def setup_admin():
    db = SessionLocal()
    try:
        user = db.query(Employee).filter(Employee.email == 'change@me.com').first()
        if not user:
            user = db.query(Employee).filter(Employee.role == UserRole.ADMIN).first()
        
        if user:
            user.email = 'admin@voiceqa.ai'
            user.hashed_password = "$2b$12$Gc8/HRY2/HHtWVF6dxSwrePMCKj/0NU.DgsjaoAhtKo4Kcd2gEk8i"
            user.role = UserRole.ADMIN
            db.commit()
            print("Admin updated: admin@voiceqa.ai / password")
        else:
            new_user = Employee(
                name="Admin",
                email="admin@voiceqa.ai",
                hashed_password=get_password_hash("password"),
                role=UserRole.ADMIN,
                employee_code="ADM-001"
            )
            db.add(new_user)
            db.commit()
            print("Admin created: admin@voiceqa.ai / password")
    except Exception as e:
        print(f"Error setting up admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    setup_admin()
