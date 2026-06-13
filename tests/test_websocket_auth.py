import pytest
from starlette.websockets import WebSocketDisconnect
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Campaign, Employee, LiveSession, UserRole
from app.config import get_settings
from app.security import get_password_hash

client = TestClient(app)


def test_call_websocket_requires_auth_token():
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/calls/123"):
            pass


def test_live_websocket_requires_auth_token():
    settings = get_settings()
    original_live_flag = settings.LIVE_PIPELINE_ENABLED
    settings.LIVE_PIPELINE_ENABLED = True

    db = SessionLocal()
    try:
        employee = Employee(
            name="WS Auth User",
            email="ws_auth_user@example.com",
            hashed_password=get_password_hash("Password123!"),
            role=UserRole.AGENT,
            employee_code="WS_AUTH_USER",
            status="active",
        )
        campaign = Campaign(
            name="WS_AUTH_CAMPAIGN",
            evaluation_prompt="Test prompt for websocket auth",
            color="#000000",
        )
        db.add_all([employee, campaign])
        db.commit()
        db.refresh(employee)
        db.refresh(campaign)

        session = LiveSession(
            id="ws-auth-session",
            agent_id=employee.id,
            campaign_id=campaign.id,
            reconnect_token="reconnect-token",
            gpu_id=0,
        )
        db.add(session)
        db.commit()

        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/live/ws-auth-session?token=reconnect-token"):
                pass
    finally:
        db.query(LiveSession).filter(LiveSession.id == "ws-auth-session").delete()
        db.query(Campaign).filter(Campaign.name == "WS_AUTH_CAMPAIGN").delete()
        db.query(Employee).filter(Employee.email == "ws_auth_user@example.com").delete()
        db.commit()
        db.close()
        settings.LIVE_PIPELINE_ENABLED = original_live_flag

