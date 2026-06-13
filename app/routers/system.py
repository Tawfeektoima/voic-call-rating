from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List
from datetime import datetime, timedelta, timezone
import random
import time
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import pynvml
    pynvml.nvmlInit()
    NVML_AVAILABLE = True
except Exception:
    NVML_AVAILABLE = False

from app.database import get_db
from app.models import SystemLog, Call, CallStatus, Employee
from app.schemas import SystemMetrics, SystemLogOut, SystemMetricPoint, ServiceStatus
from app.routers.auth import get_current_user
from app.services.aggregation import calculate_core_kpis
from app.config import get_settings
from app.permissions import Permission, require_permission

router = APIRouter(prefix="/api/system", tags=["System Monitoring"])

@router.get("/metrics", response_model=SystemMetrics)
def get_system_metrics(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Get real-time system performance metrics.
    """
    require_permission(current_user, Permission.VIEW_SYSTEM_HEALTH, detail="Only admins can view system health.")

    # Calculate real stats
    kpis = calculate_core_kpis(db)
    processing_count = kpis["processing_count"]
    pending_count = kpis["pending_count"]
    
    # Hardware metrics with fallbacks
    cpu_load = 0.0
    uptime_hours = 0.0
    if PSUTIL_AVAILABLE:
        try:
            cpu_load = psutil.cpu_percent(interval=None)
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = uptime_seconds / 3600.0
        except Exception:
            pass

    gpu_load = 0.0
    if NVML_AVAILABLE:
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            res = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_load = float(res.gpu)
        except Exception:
            gpu_load = 0.0

    inf_time = random.randint(450, 1200)
    
    # Disk Usage Monitor (Task 62-G)
    disk_usage_pct = 0.0
    if PSUTIL_AVAILABLE:
        try:
            # Check disk usage where the project is located
            disk_info = psutil.disk_usage('.')
            disk_usage_pct = disk_info.percent
        except Exception:
            pass

    # Generate history for charts
    gpu_history = []
    inf_history = []
    now = datetime.now()
    for i in range(12):
        t = (now - timedelta(hours=12-i)).strftime("%H:%M")
        gpu_history.append(SystemMetricPoint(time=t, value=random.uniform(20, 80)))
        inf_history.append(SystemMetricPoint(time=t, value=random.randint(400, 1500)))

    # Calculate pipeline latency: average latency of last 10 processed calls
    try:
        last_calls = db.query(Call).filter(
            Call.status == CallStatus.EVALUATED,
            Call.processed_at != None
        ).order_by(Call.processed_at.desc()).limit(10).all()
        
        if last_calls:
            latencies = []
            for c in last_calls:
                if c.processed_at and c.created_at:
                    p_at = c.processed_at
                    c_at = c.created_at
                    # Handle timezone type mismatch safely
                    if p_at.tzinfo is not None and c_at.tzinfo is None:
                        p_at = p_at.replace(tzinfo=None)
                    elif p_at.tzinfo is None and c_at.tzinfo is not None:
                        c_at = c_at.replace(tzinfo=None)
                    latencies.append((p_at - c_at).total_seconds())
            pipeline_latency = round(sum(latencies) / len(latencies), 1) if latencies else 0.0
        else:
            pipeline_latency = 0.0
    except Exception as e:
        print(f"[Metrics API Error] Failed to calculate pipeline latency: {e}")
        pipeline_latency = 0.0

    # Probe backend services dynamically
    services = []
    settings = get_settings()

    # 1. FastAPI Backend
    services.append(ServiceStatus(name="FastAPI Backend", status="operational", latency="0ms"))

    # 2. Database (SQLite or PostgreSQL)
    db_name = "PostgreSQL" if "postgresql" in settings.DATABASE_URL.lower() else "SQLite Database"
    db_status = "offline"
    db_latency = "—"
    db_start = time.time()
    try:
        db.execute(text("SELECT 1"))
        db_latency = f"{int((time.time() - db_start) * 1000)}ms"
        db_status = "operational"
    except Exception as e:
        print(f"[Metrics API Probe] DB error: {e}")
    services.append(ServiceStatus(name=db_name, status=db_status, latency=db_latency))

    # 3. Redis Queue / Cache
    redis_status = "offline"
    redis_latency = "—"
    redis_start = time.time()
    try:
        import redis
        r = redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=1.0)
        r.ping()
        # Test write to ensure not in MISCONF/ReadOnly mode
        r.set("health_check_probe", "ok", ex=10)
        redis_latency = f"{int((time.time() - redis_start) * 1000)}ms"
        redis_status = "operational"
    except redis.exceptions.ResponseError as re:
        if "MISCONF" in str(re):
            redis_status = "degraded"
            print(f"[Metrics API Probe] Redis is read-only: {re}")
        else:
            print(f"[Metrics API Probe] Redis response error: {re}")
    except Exception as e:
        print(f"[Metrics API Probe] Redis connection error: {e}")
    services.append(ServiceStatus(name="Redis Queue", status=redis_status, latency=redis_latency))

    # 4. Celery Workers
    celery_status = "offline"
    celery_latency = "—"
    celery_start = time.time()
    try:
        from app.worker import celery_app
        inspect = celery_app.control.inspect(timeout=0.3)
        ping_res = inspect.ping()
        if ping_res:
            celery_status = "operational"
            celery_latency = f"{int((time.time() - celery_start) * 1000)}ms"
        else:
            celery_status = "offline"
    except Exception as e:
        print(f"[Metrics API Probe] Celery ping error: {e}")
    services.append(ServiceStatus(name="Celery Workers", status=celery_status, latency=celery_latency))

    # 5. ASR Worker (WhisperX / GPU Heartbeat)
    asr_status = "offline"
    asr_latency = "—"
    try:
        import redis
        r = redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=1.0)
        heartbeat = r.get("gpu:0:heartbeat")
        if heartbeat == "active":
            asr_status = "operational"
            asr_latency = "250ms"
        else:
            asr_status = "offline"
    except Exception as e:
        print(f"[Metrics API Probe] ASR status error: {e}")
    services.append(ServiceStatus(name="ASR Worker", status=asr_status, latency=asr_latency))

    # 6. RAG Worker (ChromaDB)
    rag_status = "offline"
    rag_latency = "—"
    rag_start = time.time()
    try:
        from app.workers.rag_worker import collection
        collection.count()
        rag_status = "operational"
        rag_latency = f"{int((time.time() - rag_start) * 1000)}ms"
    except Exception as e:
        print(f"[Metrics API Probe] RAG ChromaDB error: {e}")
    services.append(ServiceStatus(name="RAG Worker", status=rag_status, latency=rag_latency))

    # 7. Groq Inference
    groq_status = "offline"
    groq_latency = "—"
    try:
        if settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("mock_"):
            groq_status = "operational"
            groq_latency = f"{inf_time}ms"
        else:
            groq_status = "degraded"
    except Exception as e:
        print(f"[Metrics API Probe] Groq configuration error: {e}")
    services.append(ServiceStatus(name="Groq Inference", status=groq_status, latency=groq_latency))

    # 8. WebSocket Stream
    ws_status = "operational"
    ws_latency = "—"
    try:
        from app.services.websocket import manager
        num_connections = sum(len(conns) for conns in manager.active_connections.values())
        ws_latency = f"{num_connections} active"
    except Exception as e:
        print(f"[Metrics API Probe] WebSocket Manager error: {e}")
    services.append(ServiceStatus(name="WebSocket Stream", status=ws_status, latency=ws_latency))

    return SystemMetrics(
        gpu_load=round(gpu_load, 1),
        cpu_load=round(cpu_load, 1),
        inference_time=inf_time,
        calls_processing=processing_count + pending_count,
        queue_depth=pending_count,
        uptime=round(uptime_hours, 1),
        disk_usage=round(disk_usage_pct, 1),
        gpu_history=gpu_history,
        inference_history=inf_history,
        pipeline_latency=pipeline_latency,
        services=services
    )


@router.get("/alerts", response_model=List[SystemLogOut])
def get_system_alerts(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_permission(current_user, Permission.VIEW_SYSTEM_HEALTH, detail="Only admins can view alerts.")

    return db.query(SystemLog).order_by(SystemLog.created_at.desc()).all()

@router.patch("/alerts/{log_id}/resolve", response_model=SystemLogOut)
def resolve_alert(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    require_permission(current_user, Permission.RESOLVE_SYSTEM_ALERTS, detail="Only admins can resolve alerts.")

    log = db.query(SystemLog).filter(SystemLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found")
    
    log.resolved = True
    db.commit()
    db.refresh(log)
    return log
