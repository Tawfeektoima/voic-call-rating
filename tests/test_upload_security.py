import io
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.main import app
from app.models import Campaign, Employee, UserRole
from app.routers.auth import get_current_user

client = TestClient(app)
settings = get_settings()


def _seed_upload_entities():
    db: Session = SessionLocal()
    try:
        admin = Employee(
            name="Upload Admin",
            email="upload_admin@example.com",
            role=UserRole.ADMIN,
            employee_code="UPLOAD_ADMIN",
            hashed_password="fake",
            status="active",
        )
        agent = Employee(
            name="Upload Agent",
            email="upload_agent@example.com",
            role=UserRole.AGENT,
            employee_code="UPLOAD_AGENT",
            hashed_password="fake",
            status="active",
        )
        other_agent = Employee(
            name="Upload Agent Two",
            email="upload_agent2@example.com",
            role=UserRole.AGENT,
            employee_code="UPLOAD_AGENT2",
            hashed_password="fake",
            status="active",
        )
        campaign = Campaign(
            name="UPLOAD_SECURITY_CAMPAIGN",
            evaluation_prompt="Check upload safety.",
            color="#222222",
        )
        db.add_all([admin, agent, other_agent, campaign])
        db.commit()
        db.refresh(admin)
        db.refresh(agent)
        db.refresh(other_agent)
        db.refresh(campaign)
        return admin, agent, other_agent, campaign
    finally:
        db.close()


def test_upload_rejects_empty_file_before_queueing():
    admin, _, _, campaign = _seed_upload_entities()
    app.dependency_overrides[get_current_user] = lambda: admin

    with patch("app.routers.audio.process_call_audio_task.delay") as mock_delay:
        response = client.post(
            "/api/audio/upload",
            files={"file": ("empty.wav", io.BytesIO(b""), "audio/wav")},
            data={"employee_id": admin.id, "campaign_id": campaign.id},
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()
        mock_delay.assert_not_called()

    app.dependency_overrides.clear()


def test_upload_rejects_invalid_extension_before_queueing():
    admin, _, _, campaign = _seed_upload_entities()
    app.dependency_overrides[get_current_user] = lambda: admin

    with patch("app.routers.audio.process_call_audio_task.delay") as mock_delay:
        response = client.post(
            "/api/audio/upload",
            files={"file": ("notes.txt", io.BytesIO(b"not audio"), "text/plain")},
            data={"employee_id": admin.id, "campaign_id": campaign.id},
        )
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
        mock_delay.assert_not_called()

    app.dependency_overrides.clear()


def test_upload_rejects_agent_uploading_for_other_employee():
    _, agent, other_agent, campaign = _seed_upload_entities()
    app.dependency_overrides[get_current_user] = lambda: agent

    with patch("app.routers.audio.process_call_audio_task.delay") as mock_delay:
        response = client.post(
            "/api/audio/upload",
            files={"file": ("owned.wav", io.BytesIO(b"valid audio"), "audio/wav")},
            data={"employee_id": other_agent.id, "campaign_id": campaign.id},
        )
        assert response.status_code == 403
        assert "themselves" in response.json()["detail"]
        mock_delay.assert_not_called()

    app.dependency_overrides.clear()


def test_upload_rejects_oversized_file_before_queueing(monkeypatch):
    admin, _, _, campaign = _seed_upload_entities()
    app.dependency_overrides[get_current_user] = lambda: admin
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 0)

    with patch("app.routers.audio.process_call_audio_task.delay") as mock_delay:
        response = client.post(
            "/api/audio/upload",
            files={"file": ("big.wav", io.BytesIO(b"1234"), "audio/wav")},
            data={"employee_id": admin.id, "campaign_id": campaign.id},
        )
        assert response.status_code == 400
        assert "exceeds max size" in response.json()["detail"].lower()
        mock_delay.assert_not_called()

    app.dependency_overrides.clear()


def test_bulk_upload_rejects_metadata_mismatch():
    admin, agent, _, campaign = _seed_upload_entities()
    app.dependency_overrides[get_current_user] = lambda: admin

    with patch("app.routers.audio.process_call_audio_task.delay") as mock_delay:
        response = client.post(
            "/api/audio/bulk-upload",
            files=[("files", ("mismatch.wav", io.BytesIO(b"audio bytes"), "audio/wav"))],
            data={"metadata": '[{"filename":"other.wav","employee_id":%d,"campaign_id":%d}]' % (agent.id, campaign.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 0
        assert data["failed_count"] == 1
        assert "No metadata found" in data["results"][0]["error"]
        mock_delay.assert_not_called()

    app.dependency_overrides.clear()
