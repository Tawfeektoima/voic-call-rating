from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, timedelta, timezone
import random

from app.database import get_db
from app.models import SystemLog, Call, CallStatus, UserRole, Employee
from app.schemas import SystemMetrics, SystemLogOut, SystemMetricPoint
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/system", tags=["System Monitoring"])

@router.get("/metrics", response_model=SystemMetrics)
def get_system_metrics(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Get real-time system performance metrics.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can view system health.")

    # Calculate real stats
    processing_count = db.query(func.count(Call.id)).filter(Call.status == CallStatus.PROCESSING).scalar()
    pending_count = db.query(func.count(Call.id)).filter(Call.status == CallStatus.PENDING).scalar()
    
    # Mock some dynamic metrics for hardware (simulating real sensors)
    gpu_load = random.uniform(20.0, 85.0)
    cpu_load = random.uniform(10.0, 45.0)
    inf_time = random.randint(450, 1200)
    
    # Generate history for charts
    gpu_history = []
    inf_history = []
    now = datetime.now()
    for i in range(12):
        t = (now - timedelta(hours=12-i)).strftime("%H:%M")
        gpu_history.append(SystemMetricPoint(time=t, value=random.uniform(20, 80)))
        inf_history.append(SystemMetricPoint(time=t, value=random.randint(400, 1500)))

    return SystemMetrics(
        gpu_load=round(gpu_load, 1),
        cpu_load=round(cpu_load, 1),
        inference_time=inf_time,
        calls_processing=processing_count + pending_count, # Matches Dashboard Queue Depth
        queue_depth=pending_count,
        uptime=168.5, # Mock static for now
        gpu_history=gpu_history,
        inference_history=inf_history
    )

@router.get("/alerts", response_model=List[SystemLogOut])
def get_system_alerts(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can view alerts.")

    return db.query(SystemLog).order_by(SystemLog.created_at.desc()).all()

@router.patch("/alerts/{log_id}/resolve", response_model=SystemLogOut)
def resolve_alert(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can resolve alerts.")

    log = db.query(SystemLog).filter(SystemLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found")
    
    log.resolved = True
    db.commit()
    db.refresh(log)
    return log
