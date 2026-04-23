from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Employee, Campaign
from app.schemas import EmployeeCreate, EmployeeOut, CampaignCreate, CampaignOut

router = APIRouter(prefix="/api/admin", tags=["Admin (Setup)"])

# --- Employees ---

@router.post("/employees", response_model=EmployeeOut)
def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
    db_emp = db.query(Employee).filter(Employee.employee_code == employee.employee_code).first()
    if db_emp:
        raise HTTPException(status_code=400, detail="Employee code already registered")
    
    new_emp = Employee(**employee.model_dump())
    db.add(new_emp)
    db.commit()
    db.refresh(new_emp)
    return new_emp

@router.get("/employees", response_model=List[EmployeeOut])
def get_employees(db: Session = Depends(get_db)):
    return db.query(Employee).all()


# --- Campaigns ---

@router.post("/campaigns", response_model=CampaignOut)
def create_campaign(campaign: CampaignCreate, db: Session = Depends(get_db)):
    db_camp = db.query(Campaign).filter(Campaign.name == campaign.name).first()
    if db_camp:
        raise HTTPException(status_code=400, detail="Campaign name already exists")
    
    new_camp = Campaign(**campaign.model_dump())
    db.add(new_camp)
    db.commit()
    db.refresh(new_camp)
    return new_camp

@router.get("/campaigns", response_model=List[CampaignOut])
def get_campaigns(db: Session = Depends(get_db)):
    return db.query(Campaign).all()
