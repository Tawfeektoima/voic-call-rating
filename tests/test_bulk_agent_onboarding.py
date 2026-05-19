import io
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, Campaign
from app.routers.auth import get_current_user

client = TestClient(app)

# Test agent details
TEST_ADMIN_CODE = "TEST_BULK_ADMIN"
TEST_AGENT_CODE = "TEST_BULK_AGENT"

def cleanup_test_employees():
    db: Session = SessionLocal()
    try:
        # Delete any test employees created during run
        db.query(Employee).filter(Employee.employee_code.like("TEST_BULK_%")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

def setup_campaigns():
    db: Session = SessionLocal()
    try:
        # Ensure a test campaign exists
        camp = db.query(Campaign).filter(Campaign.name == "TEST_BULK_CAMP").first()
        if not camp:
            camp = Campaign(
                name="TEST_BULK_CAMP",
                evaluation_prompt="Test evaluation prompt",
                color="#ffffff"
            )
            db.add(camp)
            db.commit()
    finally:
        db.close()

def cleanup_campaigns():
    db: Session = SessionLocal()
    try:
        db.query(Campaign).filter(Campaign.name == "TEST_BULK_CAMP").delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

# Mock current users
mock_admin = Employee(
    id=9999,
    name="Test Admin",
    email="test_bulk_admin@example.com",
    role=UserRole.ADMIN,
    employee_code=TEST_ADMIN_CODE,
    hashed_password="fake"
)

mock_agent = Employee(
    id=9998,
    name="Test Agent",
    email="test_bulk_agent@example.com",
    role=UserRole.AGENT,
    employee_code=TEST_AGENT_CODE,
    hashed_password="fake"
)

def test_template_download():
    """Verify that only admins/HR managers can download the template CSV."""
    print("Running test_template_download...")
    # 1. Access denied for Agent
    app.dependency_overrides[get_current_user] = lambda: mock_agent
    response = client.get("/api/hr/template")
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"

    # 2. Access allowed for Admin
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    response = client.get("/api/hr/template")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert "Name,Email,Employee Code,Campaign" in response.text
    print("test_template_download passed!")

def test_preview_parsing():
    """Verify preview parsing, column normalization, and validation rules."""
    print("Running test_preview_parsing...")
    setup_campaigns()
    app.dependency_overrides[get_current_user] = lambda: mock_admin

    # Valid CSV content
    csv_content = (
        "Name,Email,Employee Code,Campaign,Phone Number,Role,Department\n"
        "Alice Smith,alice@example.com,TEST_BULK_001,TEST_BULK_CAMP,+12345,AGENT,Support\n"
        "Bob Jones,bob@example.com,TEST_BULK_002,TEST_BULK_CAMP,+54321,AGENT,Sales\n"
    )
    file_payload = {"file": ("test_agents.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    
    response = client.post("/api/hr/preview", files=file_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    json_data = response.json()
    assert json_data["summary"]["total"] == 2
    assert json_data["summary"]["valid"] == 2
    assert json_data["summary"]["invalid"] == 0
    assert len(json_data["data"]) == 2
    assert json_data["data"][0]["name"] == "Alice Smith"
    assert json_data["data"][0]["employee_code"] == "TEST_BULK_001"
    assert json_data["data"][0]["campaign_name"] == "TEST_BULK_CAMP"

    # CSV with errors (duplicate email inside file, invalid role, non-existent campaign)
    csv_content_err = (
        "Name,Email,Employee Code,Campaign,Phone Number,Role,Department\n"
        "Alice Smith,alice@example.com,TEST_BULK_001,TEST_BULK_CAMP,,AGENT,\n"
        "Bob Jones,alice@example.com,TEST_BULK_002,TEST_BULK_CAMP,,AGENT,\n" # duplicate email
        "Charlie Brown,charlie@example.com,TEST_BULK_001,,,AGENT,\n" # duplicate code
        "David Miller,david@example.com,TEST_BULK_004,NON_EXISTENT_CAMP,,INVALID_ROLE,\n" # invalid camp & role
    )
    file_payload_err = {"file": ("test_agents_err.csv", io.BytesIO(csv_content_err.encode("utf-8")), "text/csv")}
    response = client.post("/api/hr/preview", files=file_payload_err)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    json_data = response.json()
    assert json_data["summary"]["total"] == 4
    assert json_data["summary"]["valid"] == 1 # only Alice is valid
    assert json_data["summary"]["invalid"] == 3
    
    # Check errors
    data_rows = json_data["data"]
    # Row 2 error: duplicate email
    assert any("duplicate email" in err.lower() for err in data_rows[1]["errors"])
    # Row 3 error: duplicate employee code
    assert any("duplicate employee code" in err.lower() for err in data_rows[2]["errors"])
    # Row 4 error: campaign does not exist, invalid role
    errors_r4 = data_rows[3]["errors"]
    assert any("campaign" in err.lower() and "does not exist" in err.lower() for err in errors_r4)
    assert any("invalid role" in err.lower() for err in errors_r4)
    print("test_preview_parsing passed!")

def test_bulk_import_atomic():
    """Verify atomic import fails completely if there are any errors."""
    print("Running test_bulk_import_atomic...")
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    db: Session = SessionLocal()

    # Valid data + 1 invalid row (missing name)
    payload = [
        {
            "index": 1,
            "name": "Alice Smith",
            "email": "alice_atomic@example.com",
            "employee_code": "TEST_BULK_ATOMIC_001",
            "role": "AGENT"
        },
        {
            "index": 2,
            "name": "", # missing name
            "email": "bob_atomic@example.com",
            "employee_code": "TEST_BULK_ATOMIC_002",
            "role": "AGENT"
        }
    ]

    response = client.post("/api/hr/import?atomic=true", json=payload)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    
    # Confirm neither was added to DB
    e1 = db.query(Employee).filter(Employee.employee_code == "TEST_BULK_ATOMIC_001").first()
    e2 = db.query(Employee).filter(Employee.employee_code == "TEST_BULK_ATOMIC_002").first()
    assert e1 is None, "Atomic import failed but still inserted Alice"
    assert e2 is None
    print("test_bulk_import_atomic passed!")

def test_bulk_import_non_atomic():
    """Verify non-atomic import creates valid agents and reports failures."""
    print("Running test_bulk_import_non_atomic...")
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    db: Session = SessionLocal()

    # 1 valid, 1 invalid (missing name)
    payload = [
        {
            "index": 1,
            "name": "Alice Smith",
            "email": "alice_non_atomic@example.com",
            "employee_code": "TEST_BULK_NON_001",
            "role": "AGENT",
            "phone_number": "+12345"
        },
        {
            "index": 2,
            "name": "", # invalid name
            "email": "bob_non_atomic@example.com",
            "employee_code": "TEST_BULK_NON_002",
            "role": "AGENT"
        }
    ]

    response = client.post("/api/hr/import?atomic=false", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    res_data = response.json()
    assert res_data["success_count"] == 1
    assert res_data["failed_count"] == 1
    assert len(res_data["success"]) == 1
    assert len(res_data["failed"]) == 1
    
    # Verify success data
    assert res_data["success"][0]["employee_code"] == "TEST_BULK_NON_001"
    assert res_data["success"][0]["phone_number"] == "+12345"
    
    # Verify failure details
    assert res_data["failed"][0]["index"] == 2
    assert "name is required" in res_data["failed"][0]["error"].lower()

    # Confirm e1 is in DB and e2 is not
    e1 = db.query(Employee).filter(Employee.employee_code == "TEST_BULK_NON_001").first()
    e2 = db.query(Employee).filter(Employee.employee_code == "TEST_BULK_NON_002").first()
    assert e1 is not None, "Valid employee should be inserted"
    assert e2 is None, "Invalid employee should not be inserted"
    print("test_bulk_import_non_atomic passed!")

if __name__ == "__main__":
    try:
        cleanup_test_employees()
        
        test_template_download()
        test_preview_parsing()
        test_bulk_import_atomic()
        test_bulk_import_non_atomic()
        
        print("\nAll bulk onboarding tests passed successfully!")
    finally:
        cleanup_test_employees()
        cleanup_campaigns()
        # Reset overrides
        app.dependency_overrides.clear()
