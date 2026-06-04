import io
import json
import zipfile
from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import (
    Employee, UserRole, Campaign, Call, CallStatus,
    CallOutcome, CallQAPair, CallAnnotation, AuditEvent
)
from app.routers.auth import get_current_user

client = TestClient(app)

def cleanup_db():
    db: Session = SessionLocal()
    try:
        # Delete test audit events
        db.query(AuditEvent).delete(synchronize_session=False)
        # Delete test call annotations
        db.query(CallAnnotation).delete(synchronize_session=False)
        # Delete test call QA pairs
        db.query(CallQAPair).delete(synchronize_session=False)
        # Delete test call outcomes
        db.query(CallOutcome).delete(synchronize_session=False)
        # Delete test calls
        db.query(Call).filter(Call.original_filename.like("test_export_%")).delete(synchronize_session=False)
        # Delete test campaigns
        db.query(Campaign).filter(Campaign.name.like("test_export_%")).delete(synchronize_session=False)
        # Delete test employees
        db.query(Employee).filter(Employee.email.like("test_export_%")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

@pytest.fixture(autouse=True)
def setup_teardown():
    cleanup_db()
    yield
    cleanup_db()

def create_test_data(db: Session):
    # Create Campaigns
    camp_sales = Campaign(
        name="test_export_sales_campaign",
        evaluation_prompt="Sales evaluation prompt",
        color="#111111"
    )
    camp_support = Campaign(
        name="test_export_support_campaign",
        evaluation_prompt="Support evaluation prompt",
        color="#222222"
    )
    db.add_all([camp_sales, camp_support])
    db.commit()
    db.refresh(camp_sales)
    db.refresh(camp_support)

    # Create Agents/Users
    agent_sales = Employee(
        name="Sales Agent",
        email="test_export_agent_sales@example.com",
        role=UserRole.AGENT,
        employee_code="test_export_sales_code",
        department="Sales",
        hashed_password="fake"
    )
    agent_support = Employee(
        name="Support Agent",
        email="test_export_agent_support@example.com",
        role=UserRole.AGENT,
        employee_code="test_export_support_code",
        department="Support",
        hashed_password="fake"
    )
    qa_user = Employee(
        name="QA Auditor",
        email="test_export_qa@example.com",
        role=UserRole.QA,
        employee_code="test_export_qa_code",
        department="Quality Assurance",
        hashed_password="fake"
    )
    db.add_all([agent_sales, agent_support, qa_user])
    db.commit()
    db.refresh(agent_sales)
    db.refresh(agent_support)
    db.refresh(qa_user)

    # Create Call 1 (Sales Agent, Sales Camp, evaluated yesterday)
    call_1 = Call(
        employee_id=agent_sales.id,
        campaign_id=camp_sales.id,
        audio_file_path="fake_path_1.wav",
        original_filename="test_export_call_1.wav",
        status=CallStatus.EVALUATED,
        evaluation_score=90.0,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
        call_summary="This is a hot lead summary for agent_sales@example.com."
    )
    # Create Call 2 (Support Agent, Support Camp, evaluated today)
    call_2 = Call(
        employee_id=agent_support.id,
        campaign_id=camp_support.id,
        audio_file_path="fake_path_2.wav",
        original_filename="test_export_call_2.wav",
        status=CallStatus.EVALUATED,
        evaluation_score=80.0,
        created_at=datetime.now(timezone.utc),
        call_summary="Standard support call with phone number +1-234-567-8901 and SSN 123-45-6789.",
        transcript=[
            {"id": "s1", "start": 0.0, "end": 5.0, "speaker": "Agent", "text": "Hello, my email is support@test.com."},
            {"id": "s2", "start": 5.0, "end": 10.0, "speaker": "Customer", "text": "Hi, check card 1234-5678-1234-5678."}
        ]
    )
    db.add_all([call_1, call_2])
    db.commit()
    db.refresh(call_1)
    db.refresh(call_2)

    # Add outcome for call 1
    outcome_1 = CallOutcome(
        call_id=call_1.id,
        campaign_type="sales",
        primary_outcome="Sale Closed",
        outcome_value=100.0,
        talk_ratio=0.45
    )
    db.add(outcome_1)

    # Add QA pair for call 2
    qa_pair = CallQAPair(
        call_id=call_2.id,
        objection="I need help with card 1111-2222-3333-4444.",
        response="Please send email to verification@test.com."
    )
    db.add(qa_pair)

    # Add annotation for call 2
    annotation = CallAnnotation(
        call_id=call_2.id,
        supervisor_id=qa_user.id,
        timestamp=2.5,
        note="Agent asked for SSN 987-65-4321.",
        tag="pii_leak"
    )
    db.add(annotation)
    db.commit()

    return {
        "camp_sales_id": camp_sales.id,
        "camp_support_id": camp_support.id,
        "agent_sales_id": agent_sales.id,
        "agent_support_id": agent_support.id,
        "qa_user_id": qa_user.id
    }

def test_export_unauthorized_roles():
    """Verify that AGENT is unauthorized for export endpoints."""
    mock_agent = Employee(
        id=8801,
        name="Ordinary Agent",
        email="test_export_agent@example.com",
        role=UserRole.AGENT,
        employee_code="TEST_EXPORT_AGENT",
        hashed_password="fake"
    )
    app.dependency_overrides[get_current_user] = lambda: mock_agent

    try:
        response_csv = client.get("/api/export/csv")
        assert response_csv.status_code == 403

        response_xlsx = client.get("/api/export/xlsx")
        assert response_xlsx.status_code == 403

        response_transcripts = client.get("/api/export/transcripts")
        assert response_transcripts.status_code == 403
    finally:
        app.dependency_overrides.clear()

def test_export_filters():
    """Verify that export endpoints filter by campaign, department, date range, and role."""
    db: Session = SessionLocal()
    ids = create_test_data(db)
    db.close()

    # Authenticate as admin
    mock_admin = Employee(
        id=8800,
        name="Admin User",
        email="test_export_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="TEST_EXPORT_ADMIN",
        hashed_password="fake"
    )
    app.dependency_overrides[get_current_user] = lambda: mock_admin

    try:
        # 1. Filter by Campaign — every data row must belong to camp_sales_id
        res_csv_camp = client.get(f"/api/export/csv?campaign_id={ids['camp_sales_id']}")
        assert res_csv_camp.status_code == 200
        lines = [l.rstrip('\r') for l in res_csv_camp.text.strip().split("\n") if l.strip().rstrip('\r')]
        assert len(lines) >= 2  # at least header + 1 call
        for row in lines[1:]:  # skip header
            cols = row.split(",")
            assert cols[3] == str(ids['camp_sales_id']), f"Expected campaign {ids['camp_sales_id']}, got {cols[3]}"

        # 2. Filter by Department — every data row must belong to the Support department
        res_csv_dept = client.get("/api/export/csv?department=Support")
        assert res_csv_dept.status_code == 200
        lines_dept = [l.rstrip('\r') for l in res_csv_dept.text.strip().split("\n") if l.strip().rstrip('\r')]
        assert len(lines_dept) >= 2
        for row in lines_dept[1:]:
            cols = row.split(",")
            assert cols[2] == str(ids['agent_support_id']), f"Expected support agent, got agent_id {cols[2]}"

        # 3. Filter by Date Range — only Call 1 (yesterday) and Call 2 (today) should be returned
        yesterday_str = (datetime.now() - timedelta(days=2)).isoformat()
        midpoint_str = (datetime.now() - timedelta(hours=12)).isoformat()
        tomorrow_str = (datetime.now() + timedelta(days=1)).isoformat()

        # Only Call 1 (created yesterday) should appear in this range
        res_date_1 = client.get(f"/api/export/csv?campaign_id={ids['camp_sales_id']}&start_date={yesterday_str}&end_date={midpoint_str}")
        assert res_date_1.status_code == 200
        lines_date_1 = [l.rstrip('\r') for l in res_date_1.text.strip().split("\n") if l.strip().rstrip('\r')]
        assert len(lines_date_1) >= 2  # Header + Call 1

        # Only Call 2 (created today) should appear in this range
        res_date_2 = client.get(f"/api/export/csv?campaign_id={ids['camp_support_id']}&start_date={midpoint_str}&end_date={tomorrow_str}")
        assert res_date_2.status_code == 200
        lines_date_2 = [l.rstrip('\r') for l in res_date_2.text.strip().split("\n") if l.strip().rstrip('\r')]
        assert len(lines_date_2) >= 2  # Header + Call 2
        # Call 2 must belong to camp_support_id
        for row in lines_date_2[1:]:
            cols = row.split(",")
            assert cols[3] == str(ids['camp_support_id']), f"Expected support campaign, got {cols[3]}"

        # 4. Filter by Agent Role — filtering by QA returns only QA agents (none in sales/support test data)
        res_csv_role = client.get(f"/api/export/csv?campaign_id={ids['camp_sales_id']}&agent_role=QA")
        assert res_csv_role.status_code == 200
        lines_role = [l.rstrip('\r') for l in res_csv_role.text.strip().split("\n") if l.strip().rstrip('\r')]
        # All test agents under camp_sales_id are UserRole.AGENT, so only the header row should appear
        assert len(lines_role) == 1  # Only header

    finally:
        app.dependency_overrides.clear()

def test_export_pii_redaction_for_non_admins():
    """Verify that restricted roles receive redacted data, while admins receive raw data."""
    db: Session = SessionLocal()
    ids = create_test_data(db)
    db.close()

    mock_admin = Employee(
        id=8800,
        name="Admin User",
        email="test_export_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="TEST_EXPORT_ADMIN",
        hashed_password="fake"
    )
    
    mock_qa = Employee(
        id=8802,
        name="QA User",
        email="test_export_qa@example.com",
        role=UserRole.QA,
        employee_code="TEST_EXPORT_QA",
        hashed_password="fake"
    )

    # Test Transcripts ZIP export
    # ADMIN Transcripts
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        response_admin = client.get(f"/api/export/transcripts?campaign_id={ids['camp_support_id']}")
        assert response_admin.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response_admin.content)) as zip_file:
            names = zip_file.namelist()
            assert len(names) == 1
            # Read Support call transcript file (call_2)
            for name in names:
                data = json.loads(zip_file.read(name))
                # Check that SSN and Card are not redacted
                assert "123-45-6789" in data["summary"]
                assert "support@test.com" in data["transcript"][0]["text"]
                assert "1234-5678-1234-5678" in data["transcript"][1]["text"]
    finally:
        app.dependency_overrides.clear()

    # QA Transcripts (Redacted)
    app.dependency_overrides[get_current_user] = lambda: mock_qa
    try:
        response_qa = client.get(f"/api/export/transcripts?campaign_id={ids['camp_support_id']}")
        assert response_qa.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response_qa.content)) as zip_file:
            names = zip_file.namelist()
            assert len(names) == 1
            for name in names:
                data = json.loads(zip_file.read(name))
                # Check that PII fields are redacted
                assert "123-45-6789" not in data["summary"]
                assert "[SSN_REDACTED]" in data["summary"]
                assert "support@test.com" not in data["transcript"][0]["text"]
                assert "[EMAIL_REDACTED]" in data["transcript"][0]["text"]
                assert "1234-5678-1234-5678" not in data["transcript"][1]["text"]
                assert "[CARD_REDACTED]" in data["transcript"][1]["text"]
    finally:
        app.dependency_overrides.clear()

    # Test XLSX export
    # ADMIN XLSX
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        response_admin_xlsx = client.get(f"/api/export/xlsx?campaign_id={ids['camp_support_id']}")
        assert response_admin_xlsx.status_code == 200
        xls = pd.ExcelFile(io.BytesIO(response_admin_xlsx.content))
        df_qa = pd.read_excel(xls, 'RAG QA Pairs')
        df_ann = pd.read_excel(xls, 'Supervisor Annotations')

        # Check raw QA pair objection and response
        assert "1111-2222-3333-4444" in df_qa.iloc[0]["objection"]
        assert "verification@test.com" in df_qa.iloc[0]["response"]
        # Check raw annotation note
        assert "987-65-4321" in df_ann.iloc[0]["note"]
    finally:
        app.dependency_overrides.clear()

    # QA XLSX (Redacted)
    app.dependency_overrides[get_current_user] = lambda: mock_qa
    try:
        response_qa_xlsx = client.get(f"/api/export/xlsx?campaign_id={ids['camp_support_id']}")
        assert response_qa_xlsx.status_code == 200
        xls = pd.ExcelFile(io.BytesIO(response_qa_xlsx.content))
        df_qa = pd.read_excel(xls, 'RAG QA Pairs')
        df_ann = pd.read_excel(xls, 'Supervisor Annotations')

        # Check redacted QA pair objection and response
        assert "1111-2222-3333-4444" not in df_qa.iloc[0]["objection"]
        assert "[CARD_REDACTED]" in df_qa.iloc[0]["objection"]
        assert "verification@test.com" not in df_qa.iloc[0]["response"]
        assert "[EMAIL_REDACTED]" in df_qa.iloc[0]["response"]
        # Check redacted annotation note
        assert "987-65-4321" not in df_ann.iloc[0]["note"]
        assert "[SSN_REDACTED]" in df_ann.iloc[0]["note"]
    finally:
        app.dependency_overrides.clear()

def test_export_audit_trail():
    """Verify that export triggers audit events including the filters applied."""
    mock_admin = Employee(
        id=8800,
        name="Admin User",
        email="test_export_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="TEST_EXPORT_ADMIN",
        hashed_password="fake"
    )
    app.dependency_overrides[get_current_user] = lambda: mock_admin

    try:
        # Trigger CSV export with filters
        response = client.get("/api/export/csv?campaign_id=99&department=Sales")
        assert response.status_code == 200

        # Query audit log via API
        audits_response = client.get("/api/admin/audits")
        assert audits_response.status_code == 200
        audits = audits_response.json()
        assert len(audits) == 1
        audit = audits[0]
        assert audit["action"] == "EXPORT"
        assert audit["actor_email"] == "test_export_admin@example.com"
        assert audit["target"] == "CSV Export"
        assert "Campaign ID: 99" in audit["after_state"]
        assert "Department: Sales" in audit["after_state"]
    finally:
        app.dependency_overrides.clear()
