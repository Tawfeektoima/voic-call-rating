import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import Employee, UserRole, Campaign, Team, KpiThresholdConfig, AuditEvent
from app.routers.auth import get_current_user
from app.database import SessionLocal

client = TestClient(app)

# Mock admin user
mock_admin = Employee(
    id=9900,
    name="Admin User",
    email="admin_kpi_test@example.com",
    role=UserRole.ADMIN,
    employee_code="ADM_KPI",
    hashed_password="fake",
    status="active"
)

# Mock agent user
mock_agent = Employee(
    id=9901,
    name="Agent User",
    email="agent_kpi_test@example.com",
    role=UserRole.AGENT,
    employee_code="AGT_KPI",
    hashed_password="fake",
    status="active"
)

def setup_db_fixtures():
    db = SessionLocal()
    try:
        # Create mock admin
        admin = db.query(Employee).filter(Employee.id == mock_admin.id).first()
        if not admin:
            admin = Employee(
                id=mock_admin.id,
                name=mock_admin.name,
                email=mock_admin.email,
                role=mock_admin.role,
                employee_code=mock_admin.employee_code,
                hashed_password=mock_admin.hashed_password,
                status=mock_admin.status
            )
            db.add(admin)

        # Create mock agent
        agent = db.query(Employee).filter(Employee.id == mock_agent.id).first()
        if not agent:
            agent = Employee(
                id=mock_agent.id,
                name=mock_agent.name,
                email=mock_agent.email,
                role=mock_agent.role,
                employee_code=mock_agent.employee_code,
                hashed_password=mock_agent.hashed_password,
                status=mock_agent.status
            )
            db.add(agent)

        # Create mock campaign
        campaign = Campaign(
            id=1900,
            name="KPI_TEST_CAMPAIGN",
            evaluation_prompt="Dummy prompt of sufficient length",
            color="#000000"
        )
        
        # Create mock team
        team = Team(
            id=1901,
            name="KPI_TEST_TEAM",
            campaign_id=1900,
            is_active=True
        )

        db.add_all([campaign, team])
        db.commit()
    finally:
        db.close()


def test_admin_can_list_kpi_catalog():
    setup_db_fixtures()
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        response = client.get("/api/admin/kpi-catalog")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 15
        keys = [item["key"] for item in data]
        assert "conversion_rate" in keys
        assert "total_sales" in keys
        assert "violation_rate" in keys
    finally:
        app.dependency_overrides.clear()


def test_admin_can_create_team_scoped_threshold():
    setup_db_fixtures()
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    db = SessionLocal()
    try:
        response = client.post("/api/admin/kpi-thresholds", json={
            "team_id": 1901,
            "kpi_key": "conversion_rate",
            "kpi_label": "My Custom Conversion Rate",
            "threshold_type": "MINIMUM",
            "target_value": 0.15,
            "is_active": True
        })
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == 1901
        assert data["campaign_id"] is None
        assert data["kpi_key"] == "conversion_rate"
        assert data["kpi_label"] == "My Custom Conversion Rate"
        assert data["threshold_type"] == "MINIMUM"
        assert data["target_value"] == 0.15
        assert data["is_active"] is True
        assert data["created_by_id"] == mock_admin.id

        # Verify Audit Log
        audit = db.query(AuditEvent).filter(AuditEvent.action == "KPI_THRESHOLD_CREATE").first()
        assert audit is not None
        assert "KPI_THRESHOLD_CREATE" in audit.action
        assert "conversion_rate" in audit.target
    finally:
        db.close()
        app.dependency_overrides.clear()


def test_admin_can_create_campaign_scoped_threshold():
    setup_db_fixtures()
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    db = SessionLocal()
    try:
        response = client.post("/api/admin/kpi-thresholds", json={
            "campaign_id": 1900,
            "kpi_key": "call_handle_time",
            "kpi_label": "Handle Time Limit",
            "threshold_type": "MAXIMUM",
            "target_value": 300.0,
            "is_active": True
        })
        assert response.status_code == 200
        data = response.json()
        assert data["campaign_id"] == 1900
        assert data["team_id"] is None
        assert data["kpi_key"] == "call_handle_time"
        assert data["kpi_label"] == "Handle Time Limit"
        assert data["threshold_type"] == "MAXIMUM"
        assert data["target_value"] == 300.0

        # Verify Audit Log
        audit = db.query(AuditEvent).filter(AuditEvent.action == "KPI_THRESHOLD_CREATE").first()
        assert audit is not None
        assert "call_handle_time" in audit.target
    finally:
        db.close()
        app.dependency_overrides.clear()


def test_create_threshold_rejects_invalid_kpi_key():
    setup_db_fixtures()
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        response = client.post("/api/admin/kpi-thresholds", json={
            "team_id": 1901,
            "kpi_key": "invalid_kpi_name",
            "threshold_type": "MINIMUM",
            "target_value": 1.0
        })
        assert response.status_code == 400
        assert "Invalid KPI key" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_create_threshold_rejects_missing_scope():
    setup_db_fixtures()
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        response = client.post("/api/admin/kpi-thresholds", json={
            "kpi_key": "conversion_rate",
            "threshold_type": "MINIMUM",
            "target_value": 0.10
        })
        assert response.status_code == 400
        assert "Must specify either team_id or campaign_id" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_create_threshold_rejects_both_team_and_campaign_scope():
    setup_db_fixtures()
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        response = client.post("/api/admin/kpi-thresholds", json={
            "team_id": 1901,
            "campaign_id": 1900,
            "kpi_key": "conversion_rate",
            "threshold_type": "MINIMUM",
            "target_value": 0.10
        })
        assert response.status_code == 400
        assert "Cannot scope to both team and campaign simultaneously" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_create_threshold_rejects_duplicate_active_team_scope():
    setup_db_fixtures()
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        # Create first active threshold
        response = client.post("/api/admin/kpi-thresholds", json={
            "team_id": 1901,
            "kpi_key": "conversion_rate",
            "threshold_type": "MINIMUM",
            "target_value": 0.10,
            "is_active": True
        })
        assert response.status_code == 200

        # Attempt to create duplicate active threshold
        response = client.post("/api/admin/kpi-thresholds", json={
            "team_id": 1901,
            "kpi_key": "conversion_rate",
            "threshold_type": "MINIMUM",
            "target_value": 0.15,
            "is_active": True
        })
        assert response.status_code == 400
        assert "An active threshold configuration already exists" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_create_threshold_rejects_duplicate_active_campaign_scope():
    setup_db_fixtures()
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        # Create first active threshold
        response = client.post("/api/admin/kpi-thresholds", json={
            "campaign_id": 1900,
            "kpi_key": "conversion_rate",
            "threshold_type": "MINIMUM",
            "target_value": 0.10,
            "is_active": True
        })
        assert response.status_code == 200

        # Attempt to create duplicate active threshold
        response = client.post("/api/admin/kpi-thresholds", json={
            "campaign_id": 1900,
            "kpi_key": "conversion_rate",
            "threshold_type": "MINIMUM",
            "target_value": 0.15,
            "is_active": True
        })
        assert response.status_code == 400
        assert "An active threshold configuration already exists" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_reactivate_threshold_rejects_duplicate_active_scope():
    setup_db_fixtures()
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    db = SessionLocal()
    try:
        # Create active threshold
        t1 = KpiThresholdConfig(
            team_id=1901,
            kpi_key="conversion_rate",
            kpi_label="Conversion Rate",
            threshold_type="MINIMUM",
            target_value=0.10,
            is_active=True,
            created_by_id=mock_admin.id
        )
        # Create inactive duplicate threshold
        t2 = KpiThresholdConfig(
            team_id=1901,
            kpi_key="conversion_rate",
            kpi_label="Conversion Rate",
            threshold_type="MINIMUM",
            target_value=0.15,
            is_active=False,
            created_by_id=mock_admin.id
        )
        db.add_all([t1, t2])
        db.commit()
        db.refresh(t2)

        # Attempt to update t2 to is_active=True
        response = client.patch(f"/api/admin/kpi-thresholds/{t2.id}", json={
            "is_active": True
        })
        assert response.status_code == 400
        assert "An active threshold configuration already exists" in response.json()["detail"]
    finally:
        db.close()
        app.dependency_overrides.clear()


def test_create_threshold_defaults_label_from_catalog():
    setup_db_fixtures()
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        response = client.post("/api/admin/kpi-thresholds", json={
            "team_id": 1901,
            "kpi_key": "conversion_rate",
            "threshold_type": "MINIMUM",
            "target_value": 0.10,
            "is_active": True
        })
        assert response.status_code == 200
        data = response.json()
        assert data["kpi_label"] == "Conversion Rate"  # defaulted from catalog
    finally:
        app.dependency_overrides.clear()


def test_admin_can_update_threshold():
    setup_db_fixtures()
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    db = SessionLocal()
    try:
        t = KpiThresholdConfig(
            team_id=1901,
            kpi_key="conversion_rate",
            kpi_label="Conversion Rate",
            threshold_type="MINIMUM",
            target_value=0.10,
            is_active=True,
            created_by_id=mock_admin.id
        )
        db.add(t)
        db.commit()
        db.refresh(t)

        response = client.patch(f"/api/admin/kpi-thresholds/{t.id}", json={
            "kpi_label": "New Label",
            "target_value": 0.22,
            "threshold_type": "MAXIMUM",
            "is_active": False
        })
        assert response.status_code == 200
        data = response.json()
        assert data["kpi_label"] == "New Label"
        assert data["target_value"] == 0.22
        assert data["threshold_type"] == "MAXIMUM"
        assert data["is_active"] is False

        # Verify Audit Log
        audit = db.query(AuditEvent).filter(AuditEvent.action == "KPI_THRESHOLD_UPDATE").first()
        assert audit is not None
        assert "KPI_THRESHOLD_UPDATE" in audit.action
        assert "conversion_rate" in audit.target
    finally:
        db.close()
        app.dependency_overrides.clear()


def test_non_admin_cannot_manage_thresholds():
    setup_db_fixtures()
    app.dependency_overrides[get_current_user] = lambda: mock_agent
    try:
        response = client.post("/api/admin/kpi-thresholds", json={
            "team_id": 1901,
            "kpi_key": "conversion_rate",
            "threshold_type": "MINIMUM",
            "target_value": 0.10
        })
        assert response.status_code == 403

        response = client.get("/api/admin/kpi-catalog")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_thresholds_list_supports_filters_and_total_count():
    setup_db_fixtures()
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    db = SessionLocal()
    try:
        t1 = KpiThresholdConfig(
            team_id=1901,
            kpi_key="conversion_rate",
            kpi_label="Conversion Rate",
            threshold_type="MINIMUM",
            target_value=0.10,
            is_active=True,
            created_by_id=mock_admin.id
        )
        t2 = KpiThresholdConfig(
            campaign_id=1900,
            kpi_key="call_handle_time",
            kpi_label="Call Handle Time",
            threshold_type="MAXIMUM",
            target_value=300.0,
            is_active=False,
            created_by_id=mock_admin.id
        )
        db.add_all([t1, t2])
        db.commit()

        # List all
        response = client.get("/api/admin/kpi-thresholds")
        assert response.status_code == 200
        assert response.headers["X-Total-Count"] == "2"
        assert len(response.json()) == 2

        # Filter by active
        response = client.get("/api/admin/kpi-thresholds", params={"is_active": True})
        assert response.status_code == 200
        assert response.headers["X-Total-Count"] == "1"
        assert len(response.json()) == 1
        assert response.json()[0]["kpi_key"] == "conversion_rate"

        # Filter by kpi_key
        response = client.get("/api/admin/kpi-thresholds", params={"kpi_key": "call_handle_time"})
        assert response.status_code == 200
        assert response.headers["X-Total-Count"] == "1"
        assert len(response.json()) == 1
        assert response.json()[0]["kpi_key"] == "call_handle_time"
    finally:
        db.close()
        app.dependency_overrides.clear()
