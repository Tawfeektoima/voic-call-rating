from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.database import get_db
from app.models import Employee, Campaign, Call, CallStatus, SystemLog, UserRole
from app.schemas import EmployeeCreate, EmployeeOut, CampaignCreate, CampaignOut, SystemMetrics, SystemLogOut, SystemMetricPoint, AlertCreate
from app.routers.auth import get_current_user
from app.security import get_password_hash

router = APIRouter(prefix="/api/admin", tags=["Admin (Setup)"])

# --- Employees ---

@router.post("/employees", response_model=EmployeeOut)
def create_employee(
    employee: EmployeeCreate, 
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    # Role Check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can create employees.")

    db_emp = db.query(Employee).filter(Employee.employee_code == employee.employee_code).first()
    if db_emp:
        raise HTTPException(status_code=400, detail="Employee code already registered")
    
    # Hash password if provided
    emp_data = employee.model_dump()
    if "password" in emp_data:
        emp_data["hashed_password"] = get_password_hash(emp_data.pop("password"))
    
    new_emp = Employee(**emp_data)
    db.add(new_emp)
    db.commit()
    db.refresh(new_emp)
    return new_emp

@router.get("/employees", response_model=List[EmployeeOut])
def get_employees(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    # Role Check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can view the employee list.")

    return db.query(Employee).all()


# --- Campaigns ---

@router.post("/campaigns", response_model=CampaignOut)
def create_campaign(
    campaign: CampaignCreate, 
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    # Role Check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can create campaigns.")

    db_camp = db.query(Campaign).filter(Campaign.name == campaign.name).first()
    if db_camp:
        raise HTTPException(status_code=400, detail="Campaign name already exists")
    
    new_camp = Campaign(**campaign.model_dump())
    db.add(new_camp)
    db.commit()
    db.refresh(new_camp)
    return new_camp

@router.get("/campaigns", response_model=List[CampaignOut])
def get_campaigns(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    # Role Check
    if current_user.role == UserRole.AGENT:
         raise HTTPException(status_code=403, detail="Agents cannot view campaigns.")

    campaigns = db.query(Campaign).all()
    results = []

    for c in campaigns:
        # Calculate stats
        total_calls = db.query(func.count(Call.id)).filter(Call.campaign_id == c.id).scalar()
        agent_count = db.query(func.count(func.distinct(Call.employee_id))).filter(Call.campaign_id == c.id).scalar()
        avg_score = db.query(func.avg(func.coalesce(Call.overridden_score, Call.evaluation_score))).filter(
            Call.campaign_id == c.id, 
            Call.status == CallStatus.EVALUATED
        ).scalar() or 0.0

        # Create response model manually to include computed fields
        camp_out = CampaignOut.model_validate(c)
        camp_out.total_calls = total_calls
        camp_out.agent_count = agent_count
        camp_out.avg_score = round(float(avg_score), 1)
        results.append(camp_out)

    return results


@router.put("/campaigns/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    campaign_id: int,
    campaign_data: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    # Role Check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can update campaigns.")

    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Update fields
    for key, value in campaign_data.model_dump().items():
        setattr(campaign, key, value)

    db.commit()
    db.refresh(campaign)
    
    # Return with computed fields (mocked or calculated)
    camp_out = CampaignOut.model_validate(campaign)
    camp_out.total_calls = db.query(func.count(Call.id)).filter(Call.campaign_id == campaign.id).scalar()
    return camp_out


@router.delete("/campaigns/{campaign_id}")
def delete_campaign(
    campaign_id: int, 
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    # Role Check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can delete campaigns.")

    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Check for associated calls
    has_calls = db.query(Call).filter(Call.campaign_id == campaign_id).first()
    if has_calls:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete campaign with associated call records. Please archive it or delete the calls first."
        )

    db.delete(campaign)
    db.commit()
    return {"message": "Campaign deleted successfully"}
