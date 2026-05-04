from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
import io
import re
from app.database import get_db
from app.models import Employee, Campaign, UserRole, EmployeeTier
from app.routers.auth import get_current_user
from app.security import get_password_hash

router = APIRouter(prefix="/api/hr", tags=["HR Management"])

# --- Helper Logic ---

def validate_email(email: str) -> bool:
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))

@router.get("/template")
def download_template():
    """Returns an Excel template for bulk agent onboarding."""
    df = pd.DataFrame(columns=["name", "email", "campaign_name", "phone_number"])
    # Add a sample row
    df.loc[0] = ["John Doe", "john@example.com", "Customer Service", "123-456-7890"]
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    
    output.seek(0)
    headers = {
        'Content-Disposition': 'attachment; filename="agent_onboarding_template.xlsx"'
    }
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@router.post("/preview")
def preview_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Parses the file and returns a preview with validation errors highlighted."""
    if current_user.role not in [UserRole.ADMIN, UserRole.HR_MANAGER]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file.file)
        else:
            df = pd.read_excel(file.file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    required_cols = ["name", "email", "campaign_name", "phone_number"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {', '.join(missing)}")

    preview_data = []
    total_valid = 0
    total_invalid = 0

    existing_emails = {e[0] for e in db.query(Employee.email).all()}

    for index, row in df.iterrows():
        errors = []
        name = str(row['name']).strip()
        email = str(row['email']).strip()
        campaign_name = str(row['campaign_name']).strip()
        phone = str(row['phone_number']).strip()

        if not name or name == "nan": errors.append("Name is required")
        if not email or email == "nan": 
            errors.append("Email is required")
        elif not validate_email(email):
            errors.append("Invalid email format")
        elif email in existing_emails:
            errors.append("Email already exists")

        if not campaign_name or campaign_name == "nan": errors.append("Campaign is required")

        is_valid = len(errors) == 0
        if is_valid: total_valid += 1
        else: total_invalid += 1

        preview_data.append({
            "index": index,
            "name": name,
            "email": email,
            "campaign_name": campaign_name,
            "phone_number": phone,
            "errors": errors,
            "isValid": is_valid
        })

    return {
        "data": preview_data,
        "summary": {
            "total": len(df),
            "valid": total_valid,
            "invalid": total_invalid
        }
    }

@router.post("/import")
def finalize_import(
    agents: List[dict],
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Performs bulk creation of valid agents."""
    if current_user.role not in [UserRole.ADMIN, UserRole.HR_MANAGER]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    success_count = 0
    failed_count = 0
    
    # Pre-fetch campaigns to avoid multiple hits
    campaign_map = {c.name: c.id for c in db.query(Campaign).all()}
    
    new_employees = []
    
    for agent_data in agents:
        try:
            # Re-check email uniqueness to avoid race conditions
            existing = db.query(Employee).filter(Employee.email == agent_data['email']).first()
            if existing:
                failed_count += 1
                continue

            # Check campaign
            camp_name = agent_data['campaign_name']
            if camp_name not in campaign_map:
                # Create default campaign if not exists (as per requirements)
                new_camp = Campaign(
                    name=camp_name, 
                    evaluation_prompt="General customer service evaluation prompt...",
                    description="Automatically created during HR bulk import"
                )
                db.add(new_camp)
                db.flush() # Get ID
                campaign_map[camp_name] = new_camp.id

            # Create employee
            # Default password is 'Welcome123!' (In production, we would send an invite email)
            emp = Employee(
                name=agent_data['name'],
                email=agent_data['email'],
                employee_code=f"EMP-{agent_data['email'].split('@')[0].upper()}-{re.sub(r'[^0-9]', '', str(agent_data.get('phone_number','')))[-4:]}",
                hashed_password=get_password_hash("Welcome123!"),
                role=UserRole.AGENT,
                phone_number=agent_data.get('phone_number'),
                department=camp_name,
                tier=EmployeeTier.BRONZE
            )
            new_employees.append(emp)
            success_count += 1
        except Exception as e:
            print(f"Error importing agent {agent_data.get('email')}: {e}")
            failed_count += 1

    if new_employees:
        db.add_all(new_employees)
        db.commit()

    return {
        "message": f"Successfully imported {success_count} agents. {failed_count} failed.",
        "success_count": success_count,
        "failed_count": failed_count
    }
