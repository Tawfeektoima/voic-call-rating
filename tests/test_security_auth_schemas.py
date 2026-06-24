import pytest
from pydantic import ValidationError
from app.schemas import UserLogin, UserOtpVerify

# ---------------------------------------------------------------------------
# UserLogin Schema Tests
# ---------------------------------------------------------------------------

def test_user_login_valid_without_device_id():
    # Valid login with employee_code and password, no device_id
    login = UserLogin(employee_code="AGENT01", password="Password123!")
    assert login.employee_code == "AGENT01"
    assert login.password == "Password123!"
    assert login.device_id is None


def test_user_login_valid_with_device_id():
    # Valid login with valid device_id
    login = UserLogin(employee_code="AGENT01", password="Password123!", device_id="valid_device_id")
    assert login.device_id == "valid_device_id"


def test_user_login_device_id_normalization():
    # White space trimming and blank handling
    login_blank = UserLogin(employee_code="AGENT01", password="Password123!", device_id="   ")
    assert login_blank.device_id is None
    
    login_trim = UserLogin(employee_code="AGENT01", password="Password123!", device_id="  valid_device_id  ")
    assert login_trim.device_id == "valid_device_id"


def test_user_login_device_id_too_short():
    # device_id shorter than 8 characters fails
    with pytest.raises(ValidationError) as exc_info:
        UserLogin(employee_code="AGENT01", password="Password123!", device_id="short")
    assert "device_id" in str(exc_info.value)


def test_user_login_missing_identifiers_fails():
    # Login fails if neither email nor employee_code is provided
    with pytest.raises(ValidationError) as exc_info:
        UserLogin(password="Password123!", device_id="valid_device_id")
    assert "Employee code is required" in str(exc_info.value)


# ---------------------------------------------------------------------------
# UserOtpVerify Schema Tests
# ---------------------------------------------------------------------------

def test_user_otp_verify_valid_without_device_id():
    # Valid verify without device_id
    verify = UserOtpVerify(challenge_id=42, otp_code="1234")
    assert verify.challenge_id == 42
    assert verify.otp_code == "1234"
    assert verify.device_id is None


def test_user_otp_verify_valid_with_device_id():
    # Valid verify with device_id
    verify = UserOtpVerify(challenge_id=42, otp_code="1234", device_id="valid_device_id")
    assert verify.device_id == "valid_device_id"


def test_user_otp_verify_device_id_normalization():
    # Normalization of device_id in verify
    verify_blank = UserOtpVerify(challenge_id=42, otp_code="1234", device_id="   ")
    assert verify_blank.device_id is None
    
    verify_trim = UserOtpVerify(challenge_id=42, otp_code="1234", device_id="  valid_device_id  ")
    assert verify_trim.device_id == "valid_device_id"


def test_user_otp_verify_device_id_too_short():
    # Too short device_id in verify fails
    with pytest.raises(ValidationError) as exc_info:
        UserOtpVerify(challenge_id=42, otp_code="1234", device_id="short")
    assert "device_id" in str(exc_info.value)
