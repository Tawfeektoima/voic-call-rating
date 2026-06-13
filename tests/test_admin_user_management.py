import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, EmployeeStatus, SystemLog, AuditEvent
from app.routers.auth import get_current_user
from app.security import verify_password

client = TestClient(app)

def cleanup_test_employees():
    db: Session = SessionLocal()
    try:
        db.query(Employee).filter(Employee.email.like("test_mgmt_%")).delete(synchronize_session=False)
        db.query(Employee).filter(Employee.employee_code == "MGMT_DEFAULT_PASSWORD").delete(synchronize_session=False)
        db.query(SystemLog).filter(SystemLog.error_type.in_(["ROLE_CHANGE", "STATUS_CHANGE"])).delete(synchronize_session=False)
        db.query(AuditEvent).filter(AuditEvent.target.like("Employee test_mgmt_%")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

@pytest.fixture(autouse=True)
def setup_teardown():
    cleanup_test_employees()
    yield
    cleanup_test_employees()

def seed_test_employees():
    db: Session = SessionLocal()
    try:
        # Create a set of 15 agents, 5 QA
        users = []
        for i in range(15):
            users.append(Employee(
                name=f"Test Agent {i}",
                email=f"test_mgmt_agent_{i}@example.com",
                role=UserRole.AGENT,
                employee_code=f"MGMT_AGT_{i}",
                hashed_password="fake",
                status="active" if i % 2 == 0 else "suspended",
                department="Sales" if i % 3 == 0 else "Support"
            ))
        for i in range(5):
            users.append(Employee(
                name=f"Test QA {i}",
                email=f"test_mgmt_qa_{i}@example.com",
                role=UserRole.QA,
                employee_code=f"MGMT_QA_{i}",
                hashed_password="fake",
                status="active" if i % 2 == 0 else "disabled",
                department="Quality"
            ))
        for u in users:
            db.add(u)
        db.commit()
    finally:
        db.close()


def test_admin_create_employee_uses_default_hashed_password_when_omitted():
    """Verify omitted employee password gets the configured default, stored only as a hash."""
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=9001,
        name="Mock Admin User",
        email="test_mgmt_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="TEST_MGMT_ADMIN",
        hashed_password="fake",
        status="active"
    )

    response = client.post(
        "/api/admin/employees",
        json={
            "name": "Default Password User",
            "employee_code": "MGMT_DEFAULT_PASSWORD",
            "role": "AGENT"
        }
    )
    assert response.status_code == 200

    db: Session = SessionLocal()
    try:
        employee = db.query(Employee).filter(Employee.employee_code == "MGMT_DEFAULT_PASSWORD").first()
        assert employee is not None
        assert employee.email == "emp-mgmt_default_password@eiacs.com"
        assert employee.hashed_password != "Eiacs$1234#"
        assert verify_password("Eiacs$1234#", employee.hashed_password)
    finally:
        db.close()
        app.dependency_overrides.clear()

def test_admin_view_employee_list_pagination():
    """Verify that skip and limit correctly paginate employee records and return total headers."""
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=9001,
        name="Mock Admin User",
        email="test_mgmt_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="TEST_MGMT_ADMIN",
        hashed_password="fake",
        status="active"
    )
    seed_test_employees()
    
    # First page
    response = client.get("/api/admin/employees?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 10
    assert "X-Total-Count" in response.headers
    total = int(response.headers["X-Total-Count"])
    assert total >= 20

    # Second page
    response_p2 = client.get("/api/admin/employees?skip=10&limit=10")
    assert response_p2.status_code == 200
    data_p2 = response_p2.json()
    assert len(data_p2) == 10
    
    # Check that they are different
    assert data[0]["id"] != data_p2[0]["id"]

    app.dependency_overrides.clear()

def test_admin_view_employee_list_filtering():
    """Verify that filtering by role, status, search, and department works properly."""
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=9001,
        name="Mock Admin User",
        email="test_mgmt_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="TEST_MGMT_ADMIN",
        hashed_password="fake",
        status="active"
    )
    seed_test_employees()

    # Filter by role
    response = client.get("/api/admin/employees?role=QA")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    assert all(u["role"] == "QA" for u in data)

    # Filter by status
    response_status = client.get("/api/admin/employees?status=suspended")
    assert response_status.status_code == 200
    data_status = response_status.json()
    assert all(u["status"] == "suspended" for u in data_status)

    # Filter by search (name)
    response_search = client.get("/api/admin/employees?search=QA%203")
    assert response_search.status_code == 200
    data_search = response_search.json()
    assert len(data_search) == 1
    assert data_search[0]["name"] == "Test QA 3"

    # Filter by department
    response_dept = client.get("/api/admin/employees?department=Quality")
    assert response_dept.status_code == 200
    data_dept = response_dept.json()
    assert len(data_dept) == 5

    app.dependency_overrides.clear()

def test_non_admin_listing_blocked():
    """Verify that non-admins are blocked from viewing the employee list."""
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=9002,
        name="Mock Agent User",
        email="test_mgmt_agent@example.com",
        role=UserRole.AGENT,
        employee_code="TEST_MGMT_AGENT",
        hashed_password="fake",
        status="active"
    )
    response = client.get("/api/admin/employees")
    assert response.status_code == 403
    assert "Only admins" in response.json()["detail"]
    app.dependency_overrides.clear()

def test_update_employee_role_and_status_success():
    """Verify that admins can update user role/status and that it's audited and persists."""
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=9001,
        name="Mock Admin User",
        email="test_mgmt_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="TEST_MGMT_ADMIN",
        hashed_password="fake",
        status="active"
    )
    
    # First, insert a user to edit
    db: Session = SessionLocal()
    try:
        user = Employee(
            name="Test Edit User",
            email="test_mgmt_edit@example.com",
            role=UserRole.AGENT,
            employee_code="MGMT_EDIT",
            hashed_password="fake",
            status="active"
        )
        db.add(user)
        db.commit()
        user_id = user.id
    finally:
        db.close()

    # Update role to QA and status to suspended
    response = client.put(
        f"/api/admin/employees/{user_id}",
        json={"role": "qa", "status": "suspended"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "QA"
    assert data["status"] == "suspended"

    # Verify persistence in DB
    db = SessionLocal()
    try:
        db_user = db.query(Employee).filter(Employee.id == user_id).first()
        assert db_user.role == UserRole.QA
        assert db_user.status == "suspended"

        # Verify audit logs in SystemLog
        role_logs = db.query(SystemLog).filter(SystemLog.error_type == "ROLE_CHANGE").all()
        assert len(role_logs) == 1
        assert "QA" in role_logs[0].error_message
        
        status_logs = db.query(SystemLog).filter(SystemLog.error_type == "STATUS_CHANGE").all()
        assert len(status_logs) == 1
        assert "suspended" in status_logs[0].error_message
    finally:
        db.close()

    app.dependency_overrides.clear()

def test_self_modification_prevented():
    """Verify that admins cannot update their own role or status to prevent lockouts."""
    db: Session = SessionLocal()
    try:
        db_admin = Employee(
            id=9001,
            name="Mock Admin User",
            email="test_mgmt_admin@example.com",
            role=UserRole.ADMIN,
            employee_code="TEST_MGMT_ADMIN",
            hashed_password="fake",
            status="active"
        )
        db.add(db_admin)
        db.commit()
    finally:
        db.close()

    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=9001,
        name="Mock Admin User",
        email="test_mgmt_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="TEST_MGMT_ADMIN",
        hashed_password="fake",
        status="active"
    )

    # Attempt to demote oneself
    response = client.put(
        "/api/admin/employees/9001",
        json={"role": "agent"}
    )
    assert response.status_code == 400
    assert "lockout" in response.json()["detail"]

    # Attempt to suspend oneself
    response_status = client.put(
        "/api/admin/employees/9001",
        json={"status": "suspended"}
    )
    assert response_status.status_code == 400
    assert "lockout" in response_status.json()["detail"]

    app.dependency_overrides.clear()

def test_invalid_role_or_status_rejected():
    """Verify that invalid role or status values are rejected with 400 Bad Request."""
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=9001,
        name="Mock Admin User",
        email="test_mgmt_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="TEST_MGMT_ADMIN",
        hashed_password="fake",
        status="active"
    )
    
    # Insert user
    db: Session = SessionLocal()
    try:
        user = Employee(
            name="Test Edit Valid User",
            email="test_mgmt_invalid@example.com",
            role=UserRole.AGENT,
            employee_code="MGMT_INVALID",
            hashed_password="fake",
            status="active"
        )
        db.add(user)
        db.commit()
        user_id = user.id
    finally:
        db.close()

    # Invalid role
    response = client.put(
        f"/api/admin/employees/{user_id}",
        json={"role": "SUPER_ADMIN"}
    )
    assert response.status_code == 400
    assert "Invalid role" in response.json()["detail"]

    # Invalid status
    response_status = client.put(
        f"/api/admin/employees/{user_id}",
        json={"status": "inactive"}
    )
    assert response_status.status_code == 400
    assert "Invalid status" in response_status.json()["detail"]

    app.dependency_overrides.clear()

def test_non_admin_update_blocked():
    """Verify that non-admins cannot update employee records."""
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=9002,
        name="Mock Agent User",
        email="test_mgmt_agent@example.com",
        role=UserRole.AGENT,
        employee_code="TEST_MGMT_AGENT",
        hashed_password="fake",
        status="active"
    )
    response = client.put(
        "/api/admin/employees/123",
        json={"role": "qa"}
    )
    assert response.status_code == 403
    app.dependency_overrides.clear()


def test_hr_manager_can_update_employee_status():
    """Verify that HR managers can update employee status and create an audit event."""
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=9003,
        name="Mock HR Manager",
        email="test_mgmt_hr@example.com",
        role=UserRole.HR_MANAGER,
        employee_code="TEST_MGMT_HR",
        hashed_password="fake",
        status="active"
    )

    db: Session = SessionLocal()
    try:
        user = Employee(
            name="Test Status Target",
            email="test_mgmt_status@example.com",
            role=UserRole.AGENT,
            employee_code="MGMT_STATUS",
            hashed_password="fake",
            status="active"
        )
        db.add(user)
        db.commit()
        user_id = user.id
    finally:
        db.close()

    response = client.put(
        f"/api/admin/employees/{user_id}/status",
        json={"status": "disabled"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "disabled"

    db = SessionLocal()
    try:
        db_user = db.query(Employee).filter(Employee.id == user_id).first()
        assert db_user.status == "disabled"

        audit = db.query(AuditEvent).filter(
            AuditEvent.action == "STATUS_CHANGE",
            AuditEvent.actor_email == "test_mgmt_hr@example.com",
            AuditEvent.target.like("Employee test_mgmt_status@example.com%")
        ).first()
        assert audit is not None
        assert audit.success is True
    finally:
        db.close()

    app.dependency_overrides.clear()


def test_non_hr_cannot_update_employee_status():
    """Verify that non-admin and non-HR users cannot update employee status."""
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=9002,
        name="Mock Agent User",
        email="test_mgmt_agent@example.com",
        role=UserRole.AGENT,
        employee_code="TEST_MGMT_AGENT",
        hashed_password="fake",
        status="active"
    )

    response = client.put(
        "/api/admin/employees/123/status",
        json={"status": "disabled"}
    )
    assert response.status_code == 403
    assert "HR managers" in response.json()["detail"]
    app.dependency_overrides.clear()

