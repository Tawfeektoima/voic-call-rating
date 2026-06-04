from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, Campaign, Call, CallStatus
from app.routers.auth import get_current_user

client = TestClient(app)

# Mock users
mock_admin = Employee(
    id=7777,
    name="Export Admin",
    email="export_admin@example.com",
    role=UserRole.ADMIN,
    employee_code="EXPORT_ADMIN",
    hashed_password="fake"
)

mock_agent = Employee(
    id=7776,
    name="Export Agent",
    email="export_agent@example.com",
    role=UserRole.AGENT,
    employee_code="EXPORT_AGENT",
    hashed_password="fake"
)

def test_unauthenticated_export_rejected():
    """Verify that unauthenticated calls to export endpoints are rejected with 401."""
    app.dependency_overrides.clear()
    
    response_csv = client.get("/api/export/csv")
    assert response_csv.status_code == 401
    
    response_xlsx = client.get("/api/export/xlsx")
    assert response_xlsx.status_code == 401
    
    response_transcripts = client.get("/api/export/transcripts?campaign_id=1")
    assert response_transcripts.status_code == 401

def test_agent_export_rejected():
    """Verify that an ordinary agent user is rejected with 403 Forbidden on all export endpoints."""
    app.dependency_overrides[get_current_user] = lambda: mock_agent
    try:
        response_csv = client.get("/api/export/csv")
        assert response_csv.status_code == 403
        
        response_xlsx = client.get("/api/export/xlsx")
        assert response_xlsx.status_code == 403
        
        response_transcripts = client.get("/api/export/transcripts?campaign_id=1")
        assert response_transcripts.status_code == 403
    finally:
        app.dependency_overrides.clear()

def test_admin_export_permitted():
    """Verify that an admin can export CSV and Zip transcripts successfully, and pass XLSX guard."""
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    db: Session = SessionLocal()
    try:
        # Create a test campaign and call to ensure we have data if none is present
        camp = db.query(Campaign).first()
        if not camp:
            camp = Campaign(
                name="EXPORT_TEST_CAMP",
                evaluation_prompt="Test evaluation prompt",
                color="#000000"
            )
            db.add(camp)
            db.commit()
            db.refresh(camp)

        call = db.query(Call).filter(Call.campaign_id == camp.id).first()
        if not call:
            # We also need an employee in DB to satisfy foreign key constraints
            emp = db.query(Employee).first()
            if not emp:
                emp = Employee(
                    name="Test Agent DB",
                    email="test_agent_db_export@example.com",
                    role=UserRole.AGENT,
                    employee_code="TEST_AGENT_DB_EXPORT",
                    hashed_password="fake"
                )
                db.add(emp)
                db.commit()
                db.refresh(emp)
            call = Call(
                employee_id=emp.id,
                campaign_id=camp.id,
                status=CallStatus.EVALUATED,
                evaluation_score=90.0,
                audio_file_path="test_file.wav",
                original_filename="test_file.wav"
            )
            db.add(call)
            db.commit()
            db.refresh(call)

        # Test CSV export
        response_csv = client.get(f"/api/export/csv?campaign_id={camp.id}")
        assert response_csv.status_code == 200
        assert "call_id,date,agent_id,campaign_id" in response_csv.text

        # Test Transcripts zip export
        response_transcripts = client.get(f"/api/export/transcripts?campaign_id={camp.id}")
        assert response_transcripts.status_code == 200
        assert response_transcripts.headers["content-type"] == "application/x-zip-compressed"

        # Test XLSX export passes auth guard (might return 404 if data format is empty, but not 403)
        response_xlsx = client.get(f"/api/export/xlsx?campaign_id={camp.id}")
        assert response_xlsx.status_code in (200, 404)
    finally:
        # Cleanup created records if we created any
        db.query(Call).filter(Call.original_filename == "test_file.wav").delete()
        db.query(Employee).filter(Employee.employee_code == "TEST_AGENT_DB_EXPORT").delete()
        db.query(Campaign).filter(Campaign.name == "EXPORT_TEST_CAMP").delete()
        db.commit()
        db.close()
        app.dependency_overrides.clear()
