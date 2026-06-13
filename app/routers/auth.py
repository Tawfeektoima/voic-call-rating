import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from sqlalchemy import func

from app.config import get_settings
from app.database import get_db
from app.models import Employee, LoginOtpChallenge, UserRole, EmployeeStatus
from app.schemas import PasswordResetConfirm, PasswordResetRequest, UserRegister, UserLogin, UserOtpVerify, EmployeeOut, MeResponse, RoleDefinitionOut
from app.security import verify_password, get_password_hash, create_access_token, SECRET_KEY, ALGORITHM
from app.limiter import login_ip_limiter, login_email_limiter
from app.services.audit import log_audit_event
from app.permissions import get_role_permissions, list_role_definitions, normalize_role_value
from app.services.employee_identity import hash_national_id, normalize_employee_email
from app.services.email_delivery import send_login_otp_email, send_password_reset_otp_email

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _is_active(user: Employee) -> bool:
    return (user.status or "").lower() == EmployeeStatus.ACTIVE.value


def _serialize_role(role) -> str:
    return role.value if hasattr(role, "value") else str(role)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _hash_otp(otp_code: str) -> str:
    return hashlib.sha256(f"{SECRET_KEY}:{otp_code}".encode("utf-8")).hexdigest()


def _issue_login_token(user: Employee, db: Session) -> dict:
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "role": _serialize_role(user.role)}
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": _serialize_role(user.role),
            "permissions": list(get_role_permissions(user.role, db=db)),
            "account_status": user.status,
            "status": user.status
        }
    }


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        masked_local = local[:1] + "*"
    else:
        masked_local = f"{local[:2]}{'*' * max(2, len(local) - 2)}"
    return f"{masked_local}@{domain}"


def _create_login_otp_challenge(user: Employee, request: Request, db: Session) -> dict:
    settings = get_settings()
    destination_email = (user.otp_email or "").strip().lower()
    if not destination_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No verified OTP email is configured for this employee."
        )

    otp_code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = LoginOtpChallenge(
        employee_id=user.id,
        otp_hash=_hash_otp(otp_code),
        purpose="LOGIN",
        destination_email=destination_email,
        max_attempts=settings.LOGIN_OTP_MAX_ATTEMPTS,
        expires_at=_utcnow() + timedelta(minutes=settings.LOGIN_OTP_EXPIRE_MINUTES),
        ip_address=request.client.host if request.client else None,
    )
    db.add(challenge)
    db.flush()

    delivered = False
    try:
        delivered = send_login_otp_email(destination_email, user.name, otp_code)
    except Exception:
        delivered = False

    log_audit_event(
        db=db,
        action="LOGIN_OTP_REQUEST",
        actor_id=user.id,
        actor_email=user.email,
        target=f"Employee {user.employee_code}",
        after_state=f"destination={_mask_email(destination_email)}; delivered={delivered}",
        reason="Login OTP challenge created",
        success=True,
    )
    db.commit()
    db.refresh(challenge)

    response = {
        "otp_required": True,
        "challenge_id": challenge.id,
        "delivery": "email",
        "destination": _mask_email(destination_email),
        "expires_in_seconds": settings.LOGIN_OTP_EXPIRE_MINUTES * 60,
    }
    if not settings.is_production and not delivered:
        response["dev_otp_code"] = otp_code
    return response


def get_user_from_token(token: str, db: Session) -> Employee:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(Employee).filter(Employee.email == email).first()
    if user is None:
        raise credentials_exception
    if not _is_active(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status}",
        )
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    return get_user_from_token(token, db)


@router.post("/register", response_model=EmployeeOut)
def register_user(
    user_data: UserRegister, 
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can register new users."
        )

    try:
        role_to_assign = normalize_role_value(user_data.role or UserRole.AGENT.value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {user_data.role}"
        )

    try:
        normalized_email = normalize_employee_email(user_data.email)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Check if user exists
    existing_user = db.query(Employee).filter(func.lower(Employee.email) == normalized_email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_pwd = get_password_hash(user_data.password)
    
    # Create user
    new_user = Employee(
        name=user_data.name,
        email=normalized_email,
        hashed_password=hashed_pwd,
        role=role_to_assign,
        employee_code=f"EMP-{normalized_email.split('@')[0].upper()}" # Legacy fallback path
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_audit_event(
        db=db,
        action="REGISTER",
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"Employee {new_user.email} (ID: {new_user.id})",
        after_state=f"role={_serialize_role(new_user.role)}; status={new_user.status}",
        reason="Admin registration",
        success=True,
    )
    
    return new_user


@router.post("/login")
def login_user(request: Request, credentials: UserLogin, db: Session = Depends(get_db)):
    settings = get_settings()
    client_ip = request.client.host if request.client else "127.0.0.1"
    employee_code = (credentials.employee_code or "").strip()
    identifier = employee_code

    user = None
    if employee_code:
        user = db.query(Employee).filter(Employee.employee_code == employee_code).first()
    elif credentials.email:
        try:
            normalized_email = normalize_employee_email(credentials.email)
        except ValueError:
            normalized_email = credentials.email.strip().lower()
        identifier = normalized_email
        user = db.query(Employee).filter(func.lower(Employee.email) == normalized_email).first()

    if login_ip_limiter.is_limited(client_ip) or login_email_limiter.is_limited(identifier):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later."
        )
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        login_ip_limiter.record_failure(client_ip)
        login_email_limiter.record_failure(identifier)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect employee code or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not _is_active(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status}",
        )

    login_ip_limiter.reset_key(client_ip)
    login_email_limiter.reset_key(identifier)

    if user.otp_email or settings.LOGIN_OTP_REQUIRED:
        return _create_login_otp_challenge(user, request, db)

    return _issue_login_token(user, db)


@router.post("/login/verify-otp")
def verify_login_otp(payload: UserOtpVerify, db: Session = Depends(get_db)):
    challenge = db.query(LoginOtpChallenge).filter(LoginOtpChallenge.id == payload.challenge_id).first()
    if not challenge or challenge.purpose != "LOGIN" or challenge.used_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired login code.")

    user = db.query(Employee).filter(Employee.id == challenge.employee_id).first()
    if not user or not _is_active(user):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired login code.")

    if _as_aware_utc(challenge.expires_at) < _utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired login code.")

    if challenge.attempts >= challenge.max_attempts:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many OTP attempts.")

    if _hash_otp(payload.otp_code.strip()) != challenge.otp_hash:
        challenge.attempts += 1
        db.commit()
        log_audit_event(
            db=db,
            action="LOGIN_OTP_VERIFY_FAILED",
            actor_id=user.id,
            actor_email=user.email,
            target=f"Employee {user.employee_code}",
            reason="Invalid login OTP",
            success=False,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired login code.")

    challenge.used_at = _utcnow()
    challenge.attempts += 1
    log_audit_event(
        db=db,
        action="LOGIN_OTP_VERIFY",
        actor_id=user.id,
        actor_email=user.email,
        target=f"Employee {user.employee_code}",
        reason="Login OTP verified",
        success=True,
    )
    db.commit()
    login_email_limiter.reset_key(user.employee_code)
    return _issue_login_token(user, db)


@router.post("/password-reset/request")
def request_password_reset(request: Request, payload: PasswordResetRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    client_ip = request.client.host if request.client else "127.0.0.1"
    try:
        company_email = normalize_employee_email(payload.email)
    except ValueError:
        company_email = payload.email.strip().lower()
    national_id_hash = hash_national_id(payload.national_id)

    rate_key = f"password-reset:{company_email}"
    if login_ip_limiter.is_limited(f"password-reset:{client_ip}") or login_email_limiter.is_limited(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset attempts. Please try again later."
        )

    generic_response = {
        "message": "If the employee email and national ID match, a reset code will be sent.",
        "otp_required": True,
        "challenge_id": None,
    }
    user = None
    if national_id_hash:
        user = (
            db.query(Employee)
            .filter(func.lower(Employee.email) == company_email)
            .filter(Employee.national_id_hash == national_id_hash)
            .first()
        )

    if not user or not _is_active(user):
        login_ip_limiter.record_failure(f"password-reset:{client_ip}")
        login_email_limiter.record_failure(rate_key)
        return generic_response

    destination_email = (user.otp_email or user.email or "").strip().lower()
    if not destination_email:
        login_ip_limiter.record_failure(f"password-reset:{client_ip}")
        login_email_limiter.record_failure(rate_key)
        return generic_response

    otp_code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = LoginOtpChallenge(
        employee_id=user.id,
        otp_hash=_hash_otp(otp_code),
        purpose="PASSWORD_RESET",
        destination_email=destination_email,
        max_attempts=settings.LOGIN_OTP_MAX_ATTEMPTS,
        expires_at=_utcnow() + timedelta(minutes=settings.LOGIN_OTP_EXPIRE_MINUTES),
        ip_address=client_ip,
    )
    db.add(challenge)
    db.flush()

    delivered = False
    try:
        delivered = send_password_reset_otp_email(destination_email, user.name, otp_code)
    except Exception:
        delivered = False

    log_audit_event(
        db=db,
        action="PASSWORD_RESET_OTP_REQUEST",
        actor_id=user.id,
        actor_email=user.email,
        target=f"Employee {user.employee_code}",
        after_state=f"destination={_mask_email(destination_email)}; delivered={delivered}",
        reason="Password reset OTP challenge created",
        success=True,
    )
    db.commit()
    db.refresh(challenge)
    login_ip_limiter.reset_key(f"password-reset:{client_ip}")
    login_email_limiter.reset_key(rate_key)

    response = {
        "message": generic_response["message"],
        "otp_required": True,
        "challenge_id": challenge.id,
        "delivery": "email",
        "destination": _mask_email(destination_email),
        "expires_in_seconds": settings.LOGIN_OTP_EXPIRE_MINUTES * 60,
    }
    if not settings.is_production and not delivered:
        response["dev_otp_code"] = otp_code
    return response


@router.post("/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    challenge = db.query(LoginOtpChallenge).filter(LoginOtpChallenge.id == payload.challenge_id).first()
    if not challenge or challenge.purpose != "PASSWORD_RESET" or challenge.used_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired reset code.")

    user = db.query(Employee).filter(Employee.id == challenge.employee_id).first()
    if not user or not _is_active(user):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired reset code.")

    if _as_aware_utc(challenge.expires_at) < _utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired reset code.")

    if challenge.attempts >= challenge.max_attempts:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many reset code attempts.")

    if _hash_otp(payload.otp_code.strip()) != challenge.otp_hash:
        challenge.attempts += 1
        log_audit_event(
            db=db,
            action="PASSWORD_RESET_VERIFY_FAILED",
            actor_id=user.id,
            actor_email=user.email,
            target=f"Employee {user.employee_code}",
            reason="Invalid password reset OTP",
            success=False,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired reset code.")

    user.hashed_password = get_password_hash(payload.new_password)
    challenge.used_at = _utcnow()
    challenge.attempts += 1
    log_audit_event(
        db=db,
        action="PASSWORD_RESET",
        actor_id=user.id,
        actor_email=user.email,
        target=f"Employee {user.employee_code}",
        reason="Password reset completed with OTP verification",
        success=True,
    )
    db.commit()
    return {"message": "Password has been reset successfully."}


@router.get("/me", response_model=MeResponse)
def get_me(db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    """
    Returns the currently authenticated employee's details,
    including an assigned campaign_id for auto-starting sessions.
    """
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": _serialize_role(current_user.role),
        "permissions": list(get_role_permissions(current_user.role, db=db)),
        "campaign_id": None,
        "avatar": current_user.avatar,
        "account_status": current_user.status,
        "status": current_user.status
    }


@router.get("/roles", response_model=list[RoleDefinitionOut])
def get_approved_roles(db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    """
    Returns the approved role catalog and permission bindings used by the UI.
    """
    return list_role_definitions(db=db)
