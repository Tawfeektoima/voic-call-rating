from sqlalchemy import func

from app.config import get_settings
from app.database import SessionLocal
from app.models import Campaign, Employee, EmployeeStatus, Team, UserRole
from app.security import get_password_hash


VIRTUAL_TEAM_LEADER_EMAIL = "virtual.team.leader@voiceqa.ai"
VIRTUAL_TEAM_LEADER_CODE = "VTL-001"
VIRTUAL_TEAM_LEADER_NAME = "Virtual Team Leader"
VIRTUAL_TEAM_NAME = "Virtual Team"

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


def setup_virtual_team_leader():
    db = SessionLocal()
    try:
        settings = get_settings()
        password_hash = get_password_hash(settings.DEFAULT_EMPLOYEE_PASSWORD)

        leader = (
            db.query(Employee)
            .filter(
                (func.lower(Employee.email) == VIRTUAL_TEAM_LEADER_EMAIL.lower())
                | (Employee.employee_code == VIRTUAL_TEAM_LEADER_CODE)
            )
            .first()
        )

        if leader:
            leader.name = VIRTUAL_TEAM_LEADER_NAME
            leader.email = VIRTUAL_TEAM_LEADER_EMAIL
            leader.employee_code = VIRTUAL_TEAM_LEADER_CODE
            leader.hashed_password = password_hash
            leader.role = UserRole.TEAM_LEADER
            leader.status = EmployeeStatus.ACTIVE.value
            leader.otp_email = VIRTUAL_TEAM_LEADER_EMAIL
            action = "updated"
        else:
            leader = Employee(
                name=VIRTUAL_TEAM_LEADER_NAME,
                email=VIRTUAL_TEAM_LEADER_EMAIL,
                otp_email=VIRTUAL_TEAM_LEADER_EMAIL,
                hashed_password=password_hash,
                role=UserRole.TEAM_LEADER,
                employee_code=VIRTUAL_TEAM_LEADER_CODE,
                status=EmployeeStatus.ACTIVE.value,
            )
            db.add(leader)
            action = "created"

        db.flush()

        team = db.query(Team).filter(Team.leader_id == leader.id).first()
        if team:
            print(f"Virtual team leader {action}: {VIRTUAL_TEAM_LEADER_EMAIL} / {settings.DEFAULT_EMPLOYEE_PASSWORD}")
            print(f"Virtual team already linked: {team.name}")
            db.commit()
            return

        campaign = db.query(Campaign).order_by(Campaign.id.asc()).first()
        if campaign is None:
            db.commit()
            print(f"Virtual team leader {action}: {VIRTUAL_TEAM_LEADER_EMAIL} / {settings.DEFAULT_EMPLOYEE_PASSWORD}")
            print("No campaign found, so no virtual team was created.")
            return

        team = db.query(Team).filter(func.lower(Team.name) == VIRTUAL_TEAM_NAME.lower()).first()
        if team:
            team.campaign_id = campaign.id
            team.leader_id = leader.id
            team.is_active = True
            team.description = "Auto-seeded demo team for the virtual team leader."
            team_action = "updated"
        else:
            team = Team(
                name=VIRTUAL_TEAM_NAME,
                description="Auto-seeded demo team for the virtual team leader.",
                campaign_id=campaign.id,
                leader_id=leader.id,
                is_active=True,
            )
            db.add(team)
            team_action = "created"

        db.commit()
        print(f"Virtual team leader {action}: {VIRTUAL_TEAM_LEADER_EMAIL} / {settings.DEFAULT_EMPLOYEE_PASSWORD}")
        print(f"Virtual team {team_action}: {team.name} (campaign_id={campaign.id})")
    except Exception as e:
        db.rollback()
        print(f"Error setting up virtual team leader: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    setup_admin()
    setup_virtual_team_leader()
