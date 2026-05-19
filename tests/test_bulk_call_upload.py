import io
import json
import os
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, Campaign, Call
from app.routers.auth import get_current_user
from app.config import get_settings

client = TestClient(app)
settings = get_settings()

TEST_PREFIX = "TEST_BULK_CALL_"

def get_test_entities():
    db: Session = SessionLocal()
    try:
        # Create campaign
        camp = db.query(Campaign).filter(Campaign.name == f"{TEST_PREFIX}CAMP").first()
        if not camp:
            camp = Campaign(
                name=f"{TEST_PREFIX}CAMP",
                evaluation_prompt="Test evaluation prompt",
                color="#ffffff"
            )
            db.add(camp)
            db.commit()
            db.refresh(camp)

        # Create Admin
        admin = db.query(Employee).filter(Employee.employee_code == f"{TEST_PREFIX}ADMIN").first()
        if not admin:
            admin = Employee(
                name="Test Bulk Call Admin",
                email="test_bulk_call_admin@example.com",
                role=UserRole.ADMIN,
                employee_code=f"{TEST_PREFIX}ADMIN",
                hashed_password="fake"
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        # Create Agent
        agent = db.query(Employee).filter(Employee.employee_code == f"{TEST_PREFIX}AGENT").first()
        if not agent:
            agent = Employee(
                name="Test Bulk Call Agent",
                email="test_bulk_call_agent@example.com",
                role=UserRole.AGENT,
                employee_code=f"{TEST_PREFIX}AGENT",
                hashed_password="fake"
            )
            db.add(agent)
            db.commit()
            db.refresh(agent)

        # Create another Agent (for testing permission restrictions)
        other_agent = db.query(Employee).filter(Employee.employee_code == f"{TEST_PREFIX}AGENT2").first()
        if not other_agent:
            other_agent = Employee(
                name="Test Bulk Call Agent 2",
                email="test_bulk_call_agent2@example.com",
                role=UserRole.AGENT,
                employee_code=f"{TEST_PREFIX}AGENT2",
                hashed_password="fake"
            )
            db.add(other_agent)
            db.commit()
            db.refresh(other_agent)

        return (
            camp.id,
            (admin.id, admin.name, admin.email, admin.role, admin.employee_code),
            (agent.id, agent.name, agent.email, agent.role, agent.employee_code),
            (other_agent.id, other_agent.name, other_agent.email, other_agent.role, other_agent.employee_code)
        )
    finally:
        db.close()

def cleanup_test_entities():
    db: Session = SessionLocal()
    try:
        # Fetch the calls first to clean up physical files
        calls = db.query(Call).filter(Call.original_filename.like(f"{TEST_PREFIX}%")).all()
        for call in calls:
            if call.audio_file_path and os.path.exists(call.audio_file_path):
                try:
                    os.remove(call.audio_file_path)
                except Exception:
                    pass
        
        # Delete calls from DB
        db.query(Call).filter(Call.original_filename.like(f"{TEST_PREFIX}%")).delete(synchronize_session=False)
        # Delete employees from DB
        db.query(Employee).filter(Employee.employee_code.like(f"{TEST_PREFIX}%")).delete(synchronize_session=False)
        # Delete campaign from DB
        db.query(Campaign).filter(Campaign.name.like(f"{TEST_PREFIX}%")).delete(synchronize_session=False)
        
        db.commit()
    finally:
        db.close()

def test_bulk_call_upload_success():
    """Verify that an admin can bulk upload calls successfully and enqueues tasks."""
    print("Running test_bulk_call_upload_success...")
    camp_id, admin_info, agent_info, _ = get_test_entities()
    
    admin = Employee(id=admin_info[0], name=admin_info[1], email=admin_info[2], role=admin_info[3], employee_code=admin_info[4])
    agent_id = agent_info[0]

    app.dependency_overrides[get_current_user] = lambda: admin

    # Prepare file payloads and metadata
    files = [
        ("files", (f"{TEST_PREFIX}file1.mp3", io.BytesIO(b"dummy audio content 1"), "audio/mpeg")),
        ("files", (f"{TEST_PREFIX}file2.wav", io.BytesIO(b"dummy audio content 2"), "audio/wav")),
    ]
    metadata = [
        {"filename": f"{TEST_PREFIX}file1.mp3", "employee_id": agent_id, "campaign_id": camp_id},
        {"filename": f"{TEST_PREFIX}file2.wav", "employee_id": agent_id, "campaign_id": camp_id},
    ]

    with patch("app.routers.audio.process_call_audio_task.delay") as mock_delay:
        response = client.post(
            "/api/audio/bulk-upload",
            files=files,
            data={"metadata": json.dumps(metadata)}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        res_data = response.json()
        assert res_data["success_count"] == 2
        assert res_data["failed_count"] == 0
        assert len(res_data["results"]) == 2
        
        assert res_data["results"][0]["filename"] == f"{TEST_PREFIX}file1.mp3"
        assert res_data["results"][0]["success"] is True
        assert res_data["results"][0]["call_id"] is not None
        
        assert res_data["results"][1]["filename"] == f"{TEST_PREFIX}file2.wav"
        assert res_data["results"][1]["success"] is True
        assert res_data["results"][1]["call_id"] is not None

        assert mock_delay.call_count == 2
    print("test_bulk_call_upload_success passed!")

def test_bulk_call_upload_agent_restrictions():
    """Verify that agents can upload calls only for themselves, and other rows fail."""
    print("Running test_bulk_call_upload_agent_restrictions...")
    camp_id, admin_info, agent_info, other_agent_info = get_test_entities()

    agent = Employee(id=agent_info[0], name=agent_info[1], email=agent_info[2], role=agent_info[3], employee_code=agent_info[4])
    agent_id = agent_info[0]
    other_agent_id = other_agent_info[0]

    app.dependency_overrides[get_current_user] = lambda: agent

    files = [
        ("files", (f"{TEST_PREFIX}self.mp3", io.BytesIO(b"my call"), "audio/mpeg")),
        ("files", (f"{TEST_PREFIX}other.mp3", io.BytesIO(b"someone else's call"), "audio/mpeg")),
    ]
    metadata = [
        {"filename": f"{TEST_PREFIX}self.mp3", "employee_id": agent_id, "campaign_id": camp_id},
        {"filename": f"{TEST_PREFIX}other.mp3", "employee_id": other_agent_id, "campaign_id": camp_id},
    ]

    with patch("app.routers.audio.process_call_audio_task.delay") as mock_delay:
        response = client.post(
            "/api/audio/bulk-upload",
            files=files,
            data={"metadata": json.dumps(metadata)}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        res_data = response.json()
        assert res_data["success_count"] == 1
        assert res_data["failed_count"] == 1
        
        results = {r["filename"]: r for r in res_data["results"]}
        
        assert results[f"{TEST_PREFIX}self.mp3"]["success"] is True
        assert results[f"{TEST_PREFIX}other.mp3"]["success"] is False
        assert "Agents can only upload calls for themselves" in results[f"{TEST_PREFIX}other.mp3"]["error"]
        
        assert mock_delay.call_count == 1
    print("test_bulk_call_upload_agent_restrictions passed!")

def test_bulk_call_upload_invalid_metadata():
    """Verify that malformed metadata format results in a 400 bad request."""
    print("Running test_bulk_call_upload_invalid_metadata...")
    camp_id, admin_info, agent_info, _ = get_test_entities()
    
    admin = Employee(id=admin_info[0], name=admin_info[1], email=admin_info[2], role=admin_info[3], employee_code=admin_info[4])

    app.dependency_overrides[get_current_user] = lambda: admin

    files = [
        ("files", (f"{TEST_PREFIX}file1.mp3", io.BytesIO(b"dummy"), "audio/mpeg")),
    ]

    response = client.post(
        "/api/audio/bulk-upload",
        files=files,
        data={"metadata": "not-a-json-list"}
    )
    assert response.status_code == 400
    assert "Invalid metadata format" in response.json()["detail"]
    print("test_bulk_call_upload_invalid_metadata passed!")

def test_bulk_call_upload_partial_failure():
    """Verify partial failure handling (e.g. invalid employee, invalid file extension)."""
    print("Running test_bulk_call_upload_partial_failure...")
    camp_id, admin_info, agent_info, _ = get_test_entities()

    admin = Employee(id=admin_info[0], name=admin_info[1], email=admin_info[2], role=admin_info[3], employee_code=admin_info[4])
    agent_id = agent_info[0]

    app.dependency_overrides[get_current_user] = lambda: admin

    files = [
        ("files", (f"{TEST_PREFIX}valid.mp3", io.BytesIO(b"valid"), "audio/mpeg")),
        ("files", (f"{TEST_PREFIX}invalid_emp.mp3", io.BytesIO(b"invalid emp"), "audio/mpeg")),
        ("files", (f"{TEST_PREFIX}invalid_ext.txt", io.BytesIO(b"invalid ext"), "text/plain")),
    ]
    metadata = [
        {"filename": f"{TEST_PREFIX}valid.mp3", "employee_id": agent_id, "campaign_id": camp_id},
        {"filename": f"{TEST_PREFIX}invalid_emp.mp3", "employee_id": 999999, "campaign_id": camp_id}, # non-existent agent
        {"filename": f"{TEST_PREFIX}invalid_ext.txt", "employee_id": agent_id, "campaign_id": camp_id}, # invalid ext
    ]

    with patch("app.routers.audio.process_call_audio_task.delay") as mock_delay:
        response = client.post(
            "/api/audio/bulk-upload",
            files=files,
            data={"metadata": json.dumps(metadata)}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        res_data = response.json()
        assert res_data["success_count"] == 1
        assert res_data["failed_count"] == 2
        
        results = {r["filename"]: r for r in res_data["results"]}
        
        assert results[f"{TEST_PREFIX}valid.mp3"]["success"] is True
        
        assert results[f"{TEST_PREFIX}invalid_emp.mp3"]["success"] is False
        assert "Employee with ID 999999 not found" in results[f"{TEST_PREFIX}invalid_emp.mp3"]["error"]
        
        assert results[f"{TEST_PREFIX}invalid_ext.txt"]["success"] is False
        assert "Invalid file type" in results[f"{TEST_PREFIX}invalid_ext.txt"]["error"]
        
        assert mock_delay.call_count == 1
    print("test_bulk_call_upload_partial_failure passed!")

if __name__ == "__main__":
    try:
        cleanup_test_entities()
        
        test_bulk_call_upload_success()
        test_bulk_call_upload_agent_restrictions()
        test_bulk_call_upload_invalid_metadata()
        test_bulk_call_upload_partial_failure()
        
        print("\nAll bulk call upload tests passed successfully!")
    finally:
        cleanup_test_entities()
        app.dependency_overrides.clear()
