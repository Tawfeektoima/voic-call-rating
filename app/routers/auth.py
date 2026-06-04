from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from sqlalchemy import func

from app.database import get_db
from app.models import Employee, UserRole, EmployeeStatus
from app.schemas import UserRegister, UserLogin, EmployeeOut, MeResponse
from app.security import verify_password, get_password_hash, create_access_token, SECRET_KEY, ALGORITHM
from app.limiter import login_ip_limiter, login_email_limiter
from app.services.audit import log_audit_event

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _is_active(user: Employee) -> bool:
    return (user.status or "").lower() == EmployeeStatus.ACTIVE.value


def _serialize_role(role) -> str:
    return role.value if hasattr(role, "value") else str(role)


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

    requested_role = (user_data.role or "AGENT").strip().upper()
    try:
        role_to_assign = UserRole(requested_role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {user_data.role}"
        )

    # Check if user exists
    existing_user = db.query(Employee).filter(Employee.email == user_data.email).first()
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
        email=user_data.email,
        hashed_password=hashed_pwd,
        role=role_to_assign,
        employee_code=f"EMP-{user_data.email.split('@')[0].upper()}" # Auto-gen code
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
    # Check rate limit by client IP and email
    client_ip = request.client.host if request.client else "127.0.0.1"
    normalized_email = credentials.email.strip().lower()

    if login_ip_limiter.is_limited(client_ip) or login_email_limiter.is_limited(normalized_email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later."
        )

    user = db.query(Employee).filter(func.lower(Employee.email) == normalized_email).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        login_ip_limiter.record_failure(client_ip)
        login_email_limiter.record_failure(normalized_email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not _is_active(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status}",
        )

    login_ip_limiter.reset_key(client_ip)
    login_email_limiter.reset_key(normalized_email)
    
    # Create JWT
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
            "account_status": user.status,
            "status": user.status
        }
    }


@router.get("/me", response_model=MeResponse)
def get_me(current_user: Employee = Depends(get_current_user)):
    """
    Returns the currently authenticated employee's details,
    including an assigned campaign_id for auto-starting sessions.
    """
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": _serialize_role(current_user.role),
        "campaign_id": None,
        "avatar": current_user.avatar,
        "account_status": current_user.status,
        "status": current_user.status
    }
