from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.main import app
from app.models import Call, CallStatus, Campaign, Employee, LeadStatus, UserRole
from app.routers.auth import get_current_user

client = TestClient(app)


def _seed_scale_dataset(count: int = 60):
    db: Session = SessionLocal()
    try:
        employee = Employee(
            name="Scale Agent",
            email="scale_agent@example.com",
            role=UserRole.AGENT,
            employee_code="SCALE_AGENT",
            hashed_password="fake",
            status="active",
        )
        campaign = Campaign(
            name="SCALE_CAMPAIGN",
            evaluation_prompt="Evaluate the call for performance testing.",
            color="#111111",
        )
        db.add_all([employee, campaign])
        db.commit()
        db.refresh(employee)
        db.refresh(campaign)

        now = datetime.now(timezone.utc)
        for i in range(count):
            db.add(
                Call(
                    employee_id=employee.id,
                    campaign_id=campaign.id,
                    status=CallStatus.EVALUATED,
                    evaluation_score=80.0,
                    audio_file_path=f"scale_{i}.wav",
                    original_filename=f"scale_{i}.wav",
                    created_at=now - timedelta(minutes=i),
                    processed_at=now - timedelta(minutes=i),
                    lead_status=LeadStatus.HOT,
                    is_golden_moment=True,
                    qa_alarm=True,
                )
            )
        db.commit()
        return employee.id, campaign.id
    finally:
        db.close()


def test_bounded_list_endpoints_and_export_limits():
    admin = Employee(
        id=9901,
        name="Scale Admin",
        email="scale_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="SCALE_ADMIN",
        hashed_password="fake",
        status="active",
    )
    _, campaign_id = _seed_scale_dataset()
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        leads_response = client.get("/api/analytics/leads")
        assert leads_response.status_code == 200
        assert len(leads_response.json()) == 50

        golden_response = client.get("/api/analytics/golden-moments")
        assert golden_response.status_code == 200
        assert len(golden_response.json()) == 50

        alarms_response = client.get("/api/hr/alarms/pending")
        assert alarms_response.status_code == 200
        assert len(alarms_response.json()) == 50

        search_response = client.get(f"/api/analytics/search?campaign_id={campaign_id}&limit=10&offset=5")
        assert search_response.status_code == 200
        assert len(search_response.json()) == 10

        csv_response = client.get(f"/api/export/csv?campaign_id={campaign_id}&limit=10")
        assert csv_response.status_code == 200
        rows = [row for row in csv_response.text.strip().splitlines() if row.strip()]
        assert len(rows) == 11
    finally:
        app.dependency_overrides.clear()
        db = SessionLocal()
        try:
            db.query(Call).filter(Call.original_filename.like("scale_%")).delete(synchronize_session=False)
            db.query(Employee).filter(Employee.email.in_(["scale_agent@example.com"])).delete(synchronize_session=False)
            db.query(Campaign).filter(Campaign.name == "SCALE_CAMPAIGN").delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()
