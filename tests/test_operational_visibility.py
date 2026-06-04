import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, Campaign, Call, CallStatus, SystemLog, LiveSession
from app.routers.auth import get_current_user
from app.workers.asr_worker import SessionASRBuffer
from app.workers.session_flusher import flush_live_session
from app.routers.live import live_audio_websocket

client = TestClient(app)

# Mock admin user for endpoint testing
mock_admin = Employee(
    id=9801,
    name="Admin User",
    email="admin_vis@example.com",
    role=UserRole.ADMIN,
    employee_code="ADMIN_VIS",
    hashed_password="fake"
)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(autouse=True)
def clean_up_db(db_session: Session):
    db_session.query(Call).filter(Call.original_filename.like("test_vis_%")).delete(synchronize_session=False)
    db_session.query(LiveSession).filter(LiveSession.id.like("test_vis_%")).delete(synchronize_session=False)
    db_session.query(SystemLog).filter(
        SystemLog.error_message.like("%test_vis_%") |
        SystemLog.error_message.like("%Live WS session test_vis_%")
    ).delete(synchronize_session=False)
    db_session.query(Campaign).filter(Campaign.name.like("TEST_VIS_%")).delete(synchronize_session=False)
    db_session.commit()
    yield
    db_session.query(Call).filter(Call.original_filename.like("test_vis_%")).delete(synchronize_session=False)
    db_session.query(LiveSession).filter(LiveSession.id.like("test_vis_%")).delete(synchronize_session=False)
    db_session.query(SystemLog).filter(
        SystemLog.error_message.like("%test_vis_%") |
        SystemLog.error_message.like("%Live WS session test_vis_%")
    ).delete(synchronize_session=False)
    db_session.query(Campaign).filter(Campaign.name.like("TEST_VIS_%")).delete(synchronize_session=False)
    db_session.commit()

def test_metrics_endpoint_success(db_session: Session):
    """Verify that `/api/system/metrics` endpoint works and returns the new operational visibility fields."""
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        resp = client.get("/api/system/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "pipeline_latency" in data
        assert "services" in data
        assert isinstance(data["services"], list)
        
        # Verify specific service names exist in response
        services_names = [s["name"] for s in data["services"]]
        assert "FastAPI Backend" in services_names
        assert any("Database" in s for s in services_names)
        assert "Redis Queue" in services_names
    finally:
        app.dependency_overrides.clear()

def test_pipeline_latency_calculation(db_session: Session):
    """Verify that `pipeline_latency` calculates the average processed_at - created_at interval correctly."""
    # Clear all pre-existing Calls to isolate latency calculation
    db_session.query(Call).delete()
    db_session.commit()

    camp = Campaign(name="TEST_VIS_CAMP", evaluation_prompt="Test evaluation prompt", color="#FF0000")
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)
    # Add 2 processed calls with deterministic intervals
    now = datetime.now(timezone.utc)
    c1 = Call(
        employee_id=mock_admin.id,
        campaign_id=camp.id,
        status=CallStatus.EVALUATED,
        audio_file_path="test_vis_1.wav",
        original_filename="test_vis_1.wav",
        created_at=now - timedelta(seconds=120),
        processed_at=now - timedelta(seconds=20)  # 100 seconds latency
    )
    c2 = Call(
        employee_id=mock_admin.id,
        campaign_id=camp.id,
        status=CallStatus.EVALUATED,
        audio_file_path="test_vis_2.wav",
        original_filename="test_vis_2.wav",
        created_at=now - timedelta(seconds=60),
        processed_at=now  # 60 seconds latency
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        resp = client.get("/api/system/metrics")
        assert resp.status_code == 200
        data = resp.json()
        # Average is (100 + 60) / 2 = 80.0 seconds
        assert data["pipeline_latency"] == 80.0
    finally:
        app.dependency_overrides.clear()

def test_metrics_endpoint_fault_tolerance(db_session: Session):
    """Verify that when external/internal dependencies like Redis fail, the health endpoint doesn't crash."""
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    # Mock redis and celery inspect to fail completely
    with patch("redis.from_url") as mock_redis_func:
        mock_redis_func.side_effect = Exception("Redis network error")
        with patch("app.worker.celery_app.control.inspect") as mock_inspect:
            mock_inspect.side_effect = Exception("Celery inspector crashed")
            
            try:
                resp = client.get("/api/system/metrics")
                assert resp.status_code == 200
                data = resp.json()
                assert data["pipeline_latency"] >= 0
                services = {s["name"]: s for s in data["services"]}
                assert services["Redis Queue"]["status"] == "offline"
                assert services["Celery Workers"]["status"] == "offline"
            finally:
                app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_live_websocket_logging_failure(db_session: Session):
    """Verify that failures in the WebSocket handler write a critical log to SystemLog."""
    session_id = "test_vis_session_uuid"
    
    mock_ws = MagicMock()
    # We patch the database session query method to raise an error only for query(LiveSession)
    real_query = Session.query
    def mock_query(self, *args, **kwargs):
        from app.models import LiveSession
        if args and args[0] == LiveSession:
            raise Exception("test_vis_database_crash")
        return real_query(self, *args, **kwargs)
        
    with patch.object(Session, "query", mock_query):
        try:
            await live_audio_websocket(mock_ws, session_id, token="invalid")
        except Exception:
            pass
            
    # Check if a SystemLog was written
    logs = db_session.query(SystemLog).filter(
        SystemLog.error_message.like(f"%Live WS session {session_id} crashed%")
    ).all()
    assert len(logs) > 0
    assert logs[0].severity == "critical"
    assert logs[0].error_type == "processing_failure"

@pytest.mark.asyncio
async def test_asr_worker_logging_failure(db_session: Session):
    """Verify that transcription failures in ASR worker write to SystemLog."""
    asr = SessionASRBuffer("test_vis_session_asr", 1, 1)
    
    # We mock _get_model inside _transcribe to throw an exception
    with patch("app.workers.asr_worker.get_agent_suggestion") as mock_suggest:
        mock_suggest.side_effect = Exception("test_vis_model_error")
        try:
            # We call the internal transcribe method to trigger the except block
            await asr._transcribe(b"\x00" * 3200, 0.0)
        except Exception:
            pass
            
    # Check if a SystemLog was written
    logs = db_session.query(SystemLog).filter(
        SystemLog.error_message.like("%ASR transcription failed for session test_vis_session_asr%")
    ).all()
    assert len(logs) > 0
    assert logs[0].severity == "critical"

@pytest.mark.asyncio
async def test_session_flusher_logging_failure(db_session: Session):
    """Verify that session flushing failures write to SystemLog."""
    # Seed Employee first
    emp = db_session.query(Employee).filter(Employee.id == mock_admin.id).first()
    if not emp:
        emp = Employee(
            id=mock_admin.id,
            name=mock_admin.name,
            email=mock_admin.email,
            role=mock_admin.role,
            employee_code=mock_admin.employee_code,
            hashed_password="fake"
        )
        db_session.add(emp)
        db_session.commit()

    # Seed Campaign
    camp = Campaign(name="TEST_VIS_FLUSH_CAMP", evaluation_prompt="Prompt", color="#FF0000")
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)

    with patch("app.workers.session_flusher.evaluate_live_call_task") as mock_task:
        mock_task.delay.side_effect = Exception("test_vis_celery_dispatch_error")
        
        # Seed LiveSession
        from app.models import LiveSession, LiveSessionStatus
        ls = LiveSession(
            id="test_vis_flush_session",
            agent_id=emp.id,
            campaign_id=camp.id,
            status=LiveSessionStatus.ACTIVE,
            reconnect_token="token"
        )
        db_session.add(ls)
        db_session.commit()
        
        try:
            await flush_live_session("test_vis_flush_session", db_session)
        except Exception:
            pass
            
        # Clean up LiveSession
        db_session.query(LiveSession).filter(LiveSession.id == "test_vis_flush_session").delete()
        db_session.commit()
        
    # Check if a SystemLog was written
    logs = db_session.query(SystemLog).filter(
        SystemLog.error_message.like("%Live session flush failed for test_vis_flush_session%")
    ).all()
    assert len(logs) > 0
    assert logs[0].severity == "critical"
