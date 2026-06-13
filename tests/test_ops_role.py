from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import Employee, UserRole
from app.routers.auth import get_current_user

client = TestClient(app)

# Mock users
mock_ops_manager = Employee(
    id=8001,
    name="Ops Manager Test",
    email="ops_manager_test@example.com",
    role=UserRole.OPS_MANAGER,
    employee_code="OPS_MGR_TST",
    hashed_password="fake"
)

mock_admin = Employee(
    id=8002,
    name="Admin Test",
    email="admin_test@example.com",
    role=UserRole.ADMIN,
    employee_code="ADMIN_TST",
    hashed_password="fake"
)

mock_agent = Employee(
    id=8003,
    name="Agent Test",
    email="agent_test@example.com",
    role=UserRole.AGENT,
    employee_code="AGENT_TST",
    hashed_password="fake"
)

def test_ops_manager_admin_mutations_denied():
    """Verify that an OPS_MANAGER cannot perform admin mutation operations."""
    app.dependency_overrides[get_current_user] = lambda: mock_ops_manager
    try:
        # Create Employee
        response = client.post("/api/admin/employees", json={
            "name": "New User",
            "email": "new.user@example.com",
            "employee_code": "NEW_USER_001",
            "password": "password123",
            "role": "AGENT"
        })
        assert response.status_code == 403

        # Update Employee
        response = client.put("/api/admin/employees/1", json={
            "role": "QA"
        })
        assert response.status_code == 403

        # Create Campaign
        response = client.post("/api/admin/campaigns", json={
            "name": "Test Campaign",
            "evaluation_prompt": "This is a test evaluation prompt that is long enough.",
            "color": "#123456"
        })
        assert response.status_code == 403

        # Update Campaign
        response = client.put("/api/admin/campaigns/1", json={
            "name": "Test Campaign",
            "evaluation_prompt": "This is a test evaluation prompt that is long enough.",
            "color": "#123456"
        })
        assert response.status_code == 403

        # Delete Campaign
        response = client.delete("/api/admin/campaigns/1")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()

def test_ops_manager_review_mutations_denied():
    """Verify that an OPS_MANAGER cannot access or modify review queue/HITL review endpoints."""
    app.dependency_overrides[get_current_user] = lambda: mock_ops_manager
    try:
        response_queue = client.get("/api/review/queue")
        assert response_queue.status_code == 403

        response_approve = client.post("/api/review/1/approve")
        assert response_approve.status_code == 403

        response_reject = client.post("/api/review/1/reject")
        assert response_reject.status_code == 403
    finally:
        app.dependency_overrides.clear()

def test_unauthenticated_review_endpoints_denied():
    """Verify that unauthenticated requests to review endpoints are rejected with 401 Unauthorized."""
    app.dependency_overrides.clear()
    
    response_queue = client.get("/api/review/queue")
    assert response_queue.status_code == 401

    response_approve = client.post("/api/review/1/approve")
    assert response_approve.status_code == 401

    response_reject = client.post("/api/review/1/reject")
    assert response_reject.status_code == 401

def test_admin_review_endpoints_permitted():
    """Verify that an ADMIN can access review endpoints successfully."""
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        response_queue = client.get("/api/review/queue")
        assert response_queue.status_code == 200
        assert isinstance(response_queue.json(), list)
    finally:
        app.dependency_overrides.clear()

def test_ops_manager_denied_from_exports():
    """Verify that an OPS_MANAGER is denied from all export endpoints."""
    app.dependency_overrides[get_current_user] = lambda: mock_ops_manager
    try:
        response_csv = client.get("/api/export/csv")
        assert response_csv.status_code == 403

        response_xlsx = client.get("/api/export/xlsx")
        assert response_xlsx.status_code == 403

        response_transcripts = client.get("/api/export/transcripts")
        assert response_transcripts.status_code == 403
    finally:
        app.dependency_overrides.clear()

def test_agent_self_only_access():
    """Verify that AGENT users can only view their own records, while others are blocked."""
    app.dependency_overrides[get_current_user] = lambda: mock_agent
    try:
        # My-performance: self access (mocked Employee id is 8003)
        # Should NOT return 403 (might return 404 since employee doesn't exist in mock DB, which is fine)
        response_self = client.get("/api/analytics/my-performance?employee_id=8003")
        assert response_self.status_code != 403

        # My-performance: other agent access -> 403 Forbidden
        response_other = client.get("/api/analytics/my-performance?employee_id=9999")
        assert response_other.status_code == 403

        # Profile details: self access
        response_profile_self = client.get("/api/analytics/agents/8003")
        assert response_profile_self.status_code != 403

        # Profile details: other agent access -> 403 Forbidden
        response_profile_other = client.get("/api/analytics/agents/9999")
        assert response_profile_other.status_code == 403
    finally:
        app.dependency_overrides.clear()

mock_qa = Employee(
    id=8004,
    name="QA Test",
    email="qa_test@example.com",
    role=UserRole.QA,
    employee_code="QA_TST",
    hashed_password="fake"
)

mock_hr_manager = Employee(
    id=8005,
    name="HR Test",
    email="hr_test@example.com",
    role=UserRole.HR_MANAGER,
    employee_code="HR_TST",
    hashed_password="fake"
)

def test_unauthenticated_ops_endpoints_denied():
    """Verify that unauthenticated requests to /api/ops/* endpoints get 401."""
    app.dependency_overrides.clear()
    endpoints = [
        "/api/ops/dashboard",
        "/api/ops/reports/sales",
        "/api/ops/reports/revenue",
        "/api/ops/reports/conversion",
        "/api/ops/reports/attendance",
        "/api/ops/campaigns",
        "/api/ops/campaigns/1",
        "/api/ops/qa-overview",
        "/api/ops/violations-overview",
        "/api/ops/alerts"
    ]
    for url in endpoints:
        response = client.get(url)
        assert response.status_code == 401

def test_role_ops_endpoints_denied():
    """Verify that AGENT, QA, and HR_MANAGER get 403 Forbidden on /api/ops/* endpoints."""
    endpoints = [
        "/api/ops/dashboard",
        "/api/ops/reports/sales",
        "/api/ops/reports/revenue",
        "/api/ops/reports/conversion",
        "/api/ops/reports/attendance",
        "/api/ops/campaigns",
        "/api/ops/campaigns/1",
        "/api/ops/qa-overview",
        "/api/ops/violations-overview",
        "/api/ops/alerts"
    ]
    for mock_user in [mock_agent, mock_qa, mock_hr_manager]:
        app.dependency_overrides[get_current_user] = lambda u=mock_user: u
        try:
            for url in endpoints:
                response = client.get(url)
                assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

def test_ops_manager_and_admin_permitted():
    """Verify that OPS_MANAGER and ADMIN can access operations endpoints successfully."""
    endpoints = [
        "/api/ops/dashboard",
        "/api/ops/reports/sales",
        "/api/ops/reports/revenue",
        "/api/ops/reports/conversion",
        "/api/ops/reports/attendance",
        "/api/ops/campaigns",
        "/api/ops/qa-overview",
        "/api/ops/violations-overview",
        "/api/ops/alerts"
    ]
    for mock_user in [mock_ops_manager, mock_admin]:
        app.dependency_overrides[get_current_user] = lambda u=mock_user: u
        try:
            for url in endpoints:
                response = client.get(url)
                assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

def test_ops_campaign_detail_not_found():
    """Verify that campaign detail returns 404 for missing IDs."""
    app.dependency_overrides[get_current_user] = lambda: mock_ops_manager
    try:
        response = client.get("/api/ops/campaigns/9999")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()

def test_ops_filters_passed():
    """Verify that ops reporting endpoints accept and parse filters successfully."""
    app.dependency_overrides[get_current_user] = lambda: mock_ops_manager
    try:
        # Pass filter query parameters and verify they are parsed with 200 OK
        params = {
            "date_from": "2026-06-01T00:00:00",
            "date_to": "2026-06-05T23:59:59",
            "campaign_id": 1,
            "department": "Operations",
            "segment": "A",
            "limit": 100,
            "offset": 10
        }
        response = client.get("/api/ops/dashboard", params=params)
        assert response.status_code == 200
        
        # Verify pagination limit cap is respected (200 le limit returns 422 validation error for 999)
        params_cap = {"limit": 999}
        response_cap = client.get("/api/ops/dashboard", params=params_cap)
        assert response_cap.status_code == 422
    finally:
        app.dependency_overrides.clear()

def test_ops_manager_login_and_auth_me_success():
    """Verify that an OPS_MANAGER can log in and call /api/auth/me successfully returning OPS_MANAGER role."""
    from app.database import SessionLocal
    from app.security import get_password_hash
    
    db: Session = SessionLocal()
    try:
        password = "opsmanagerpass123"
        hashed_pwd = get_password_hash(password)
        user = Employee(
            name="Login Ops Manager",
            email="ops_login_test@example.com",
            hashed_password=hashed_pwd,
            role=UserRole.OPS_MANAGER,
            employee_code="OPS_LOGIN_TST",
            status="active"
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    # Attempt Login
    response = client.post(
        "/api/auth/login",
        json={"email": "ops_login_test@example.com", "password": "opsmanagerpass123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "OPS_MANAGER"

    # Access /api/auth/me with token
    token = data["access_token"]
    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["role"] == "OPS_MANAGER"
    assert me_data["email"] == "ops_login_test@example.com"

def test_ops_manager_denied_from_raw_analytics_and_audio():
    """Verify that an OPS_MANAGER is denied from raw call data, audio files, and people analytics."""
    from app.database import SessionLocal
    from app.models import Campaign, Call
    db = SessionLocal()
    try:
        # Seed a campaign and call
        campaign = Campaign(id=9876, name="Dummy Campaign", evaluation_prompt="Dummy prompt of sufficient length", color="#111111")
        call = Call(id=9876, employee_id=8001, campaign_id=9876, audio_file_path="fake_path", original_filename="fake_name")
        db.add_all([campaign, call])
        db.commit()
    finally:
        db.close()

    app.dependency_overrides[get_current_user] = lambda: mock_ops_manager
    try:
        # Analytics endpoints
        assert client.get("/api/analytics/ranking").status_code == 403
        assert client.get("/api/analytics/search").status_code == 403
        assert client.get("/api/analytics/leads").status_code == 403
        assert client.get("/api/analytics/golden-moments").status_code == 403
        assert client.get("/api/analytics/dashboard").status_code == 403
        assert client.get("/api/analytics/my-performance?employee_id=8001").status_code == 403
        assert client.get("/api/analytics/agents/8001").status_code == 403
        
        # Audio endpoints
        assert client.get("/api/audio/9876").status_code == 403
        assert client.get("/api/audio/9876/file").status_code == 403
    finally:
        app.dependency_overrides.clear()

def test_common_errors_endpoint_security():
    """Verify auth and role restriction on the common-errors endpoint (ADMIN and HR_MANAGER only)."""
    # 1. Unauthenticated gets 401
    app.dependency_overrides.clear()
    assert client.get("/api/analytics/common-errors").status_code == 401
    
    # 2. Denied roles (AGENT, QA, OPS_MANAGER) get 403
    for mock_user in [mock_agent, mock_qa, mock_ops_manager]:
        app.dependency_overrides[get_current_user] = lambda u=mock_user: u
        try:
            assert client.get("/api/analytics/common-errors").status_code == 403
        finally:
            app.dependency_overrides.clear()

    # 3. Allowed roles (ADMIN, HR_MANAGER) get 200
    for mock_user in [mock_admin, mock_hr_manager]:
        app.dependency_overrides[get_current_user] = lambda u=mock_user: u
        try:
            assert client.get("/api/analytics/common-errors").status_code == 200
        finally:
            app.dependency_overrides.clear()


