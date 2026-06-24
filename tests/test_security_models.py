from datetime import date, time, datetime, timezone
import pytest
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal, Base
from app.models import Employee, EmployeeShift, TrustedDevice, UserSession, UserRole, EmployeeStatus

def create_test_employee(db, email="test_sec_emp@example.com", code="SEC_EMP"):
    emp = Employee(
        name="Security Test Employee",
        email=email,
        employee_code=code,
        hashed_password="fake",
        role=UserRole.AGENT,
        status=EmployeeStatus.ACTIVE.value
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


def test_tables_registered_in_metadata():
    """Verify that the new tables exist in SQLAlchemy metadata."""
    assert "employee_shifts" in Base.metadata.tables
    assert "trusted_devices" in Base.metadata.tables
    assert "user_sessions" in Base.metadata.tables


def test_create_employee_shift_success():
    """Verify that we can successfully create an EmployeeShift."""
    db = SessionLocal()
    try:
        emp = create_test_employee(db)
        
        shift = EmployeeShift(
            employee_id=emp.id,
            work_date=date(2026, 6, 18),
            shift_start=time(9, 0),
            shift_end=time(17, 0),
            grace_before_minutes=15,
            grace_after_minutes=15,
            status="scheduled"
        )
        db.add(shift)
        db.commit()
        db.refresh(shift)
        
        assert shift.id is not None
        assert shift.employee_id == emp.id
        assert shift.work_date == date(2026, 6, 18)
        assert shift.shift_start == time(9, 0)
        assert shift.grace_before_minutes == 15
        assert shift.status == "scheduled"
    finally:
        db.close()


def test_duplicate_employee_shift_fails():
    """Verify that unique constraint on (employee_id, work_date) is enforced."""
    db = SessionLocal()
    try:
        emp = create_test_employee(db)
        
        shift1 = EmployeeShift(
            employee_id=emp.id,
            work_date=date(2026, 6, 18),
            shift_start=time(9, 0),
            shift_end=time(17, 0),
            status="scheduled"
        )
        db.add(shift1)
        db.commit()
        
        shift2 = EmployeeShift(
            employee_id=emp.id,
            work_date=date(2026, 6, 18),
            shift_start=time(10, 0),
            shift_end=time(18, 0),
            status="scheduled"
        )
        db.add(shift2)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_create_trusted_device_success():
    """Verify that we can create a TrustedDevice with hashed identifiers."""
    db = SessionLocal()
    try:
        emp = create_test_employee(db)
        
        device = TrustedDevice(
            employee_id=emp.id,
            device_id_hash="hashed_dev_id",
            device_fingerprint_hash="hashed_fingerprint",
            user_agent_hash="hashed_ua",
            device_label="Test Agent Laptop",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
            is_trusted=True
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        
        assert device.id is not None
        assert device.device_id_hash == "hashed_dev_id"
        assert device.is_trusted is True
    finally:
        db.close()


def test_duplicate_trusted_device_fails():
    """Verify that unique constraint on (employee_id, device_id_hash) is enforced."""
    db = SessionLocal()
    try:
        emp = create_test_employee(db)
        
        device1 = TrustedDevice(
            employee_id=emp.id,
            device_id_hash="hashed_dev_id",
            first_seen_at=datetime.now(timezone.utc),
            is_trusted=True
        )
        db.add(device1)
        db.commit()
        
        device2 = TrustedDevice(
            employee_id=emp.id,
            device_id_hash="hashed_dev_id",
            first_seen_at=datetime.now(timezone.utc),
            is_trusted=True
        )
        db.add(device2)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_create_user_session_success():
    """Verify that we can create a UserSession linked to employee and trusted device."""
    db = SessionLocal()
    try:
        emp = create_test_employee(db)
        device = TrustedDevice(
            employee_id=emp.id,
            device_id_hash="hashed_dev_id",
            first_seen_at=datetime.now(timezone.utc),
            is_trusted=True
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        
        session = UserSession(
            employee_id=emp.id,
            trusted_device_id=device.id,
            sid="session_id_123",
            jti="token_jti_123",
            device_id_hash="hashed_dev_id",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            is_active=True
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        assert session.id is not None
        assert session.sid == "session_id_123"
        assert session.jti == "token_jti_123"
        assert session.trusted_device_id == device.id
    finally:
        db.close()


def test_duplicate_session_sid_fails():
    """Verify unique constraint on sid."""
    db = SessionLocal()
    try:
        emp = create_test_employee(db)
        
        sess1 = UserSession(
            employee_id=emp.id,
            sid="duplicate_sid",
            jti="jti_1",
            device_id_hash="hashed_dev_id",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc)
        )
        sess2 = UserSession(
            employee_id=emp.id,
            sid="duplicate_sid",
            jti="jti_2",
            device_id_hash="hashed_dev_id",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc)
        )
        db.add_all([sess1, sess2])
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_duplicate_session_jti_fails():
    """Verify unique constraint on jti."""
    db = SessionLocal()
    try:
        emp = create_test_employee(db)
        
        sess1 = UserSession(
            employee_id=emp.id,
            sid="sid_1",
            jti="duplicate_jti",
            device_id_hash="hashed_dev_id",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc)
        )
        sess2 = UserSession(
            employee_id=emp.id,
            sid="sid_2",
            jti="duplicate_jti",
            device_id_hash="hashed_dev_id",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc)
        )
        db.add_all([sess1, sess2])
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()
