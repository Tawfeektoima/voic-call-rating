import os
import uvicorn
import json
import asyncio
import importlib
import warnings
import redis.asyncio as aioredis
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Histogram, Gauge

# Suppress noisy torchcodec/pyannote warnings
warnings.filterwarnings("ignore", message="torchcodec is not installed correctly")
warnings.filterwarnings("ignore", module="torchcodec")
warnings.filterwarnings("ignore", category=UserWarning)

# Disable HuggingFace cache warnings (I-08)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Ensure FFmpeg is in PATH for torchcodec/hardware decoding
# Ensure .venv/Scripts is in PATH if it exists locally
base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scripts_path = os.path.join(base_path, ".venv", "Scripts")
if os.path.exists(scripts_path) and scripts_path not in os.environ["PATH"]:
    os.environ["PATH"] = scripts_path + os.pathsep + os.environ["PATH"]

# Load environment variables
load_dotenv()

from app.database import engine, Base, SessionLocal
from app.routers import audio, analytics, admin, auth, system, export, hr, websocket_router, live, review, notes
from app.recovery import recover_stuck_tasks
from app.services.websocket import manager
from app.config import get_settings


def _load_optional_router(module_name: str):
    try:
        module = importlib.import_module(f"app.routers.{module_name}")
    except ModuleNotFoundError:
        return None
    return getattr(module, "router", None)


OPTIONAL_ROUTERS = (
    _load_optional_router("ops"),
    _load_optional_router("team_leader"),
    _load_optional_router("team_manager"),
)

# --- Phase 8: Custom Observability Metrics ---
# Target p95 < 200ms
suggestion_latency = Histogram(
    "voiceqa_suggestion_latency_ms",
    "Latency of RAG suggestions in ms",
    buckets=(50, 100, 150, 200, 300, 500, 1000)
)
# Target p95 < 350ms
asr_latency = Histogram(
    "voiceqa_asr_latency_ms",
    "Latency of ASR transcription cycles in ms",
    buckets=(100, 200, 300, 350, 500, 750, 1000)
)
# Alert if > 22 GB
gpu_vram_used = Gauge(
    "voiceqa_gpu_vram_used_gb",
    "GPU VRAM usage in GB",
    ["gpu_id"]
)
# Capacity monitor (Limit: 200 agents)
active_sessions_metric = Gauge(
    "voiceqa_active_sessions",
    "Total number of active live sessions"
)

async def redis_listener():
    settings = get_settings()
    r = aioredis.from_url(settings.CELERY_BROKER_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe("call_updates")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                call_id = data.get("call_id")
                if call_id:
                    await manager.send_update(call_id, data)
    except Exception as e:
        print(f"Redis listener error: {e}")
    finally:
        await pubsub.unsubscribe("call_updates")
        await r.close()

async def configure_redis_limits():
    """
    Ensures Redis has memory limits and eviction policies to prevent exhaustion (Phase 8).
    Sets maxmemory to 2GB and policy to allkeys-lru.
    """
    settings = get_settings()
    # Use the same redis URL as the broker
    r = aioredis.from_url(settings.CELERY_BROKER_URL)
    try:
        await r.config_set("maxmemory", "2gb")
        await r.config_set("maxmemory-policy", "allkeys-lru")
        print("[Redis] Memory management optimized (2GB / allkeys-lru)")
    except Exception as e:
        # Some managed Redis services or older versions might restrict CONFIG SET
        print(f"[Redis Config Warning] Could not apply dynamic limits: {e}")
    finally:
        await r.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup checks (TASK-C05)
    settings = get_settings()
    if settings.ENVIRONMENT.lower() != "production":
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            from app.services.role_permissions import seed_role_permissions

            seed_role_permissions(db)
            db.commit()
        finally:
            db.close()
    if settings.DATABASE_URL.startswith("sqlite"):
        print("=" * 60)
        print("⚠️  WARNING: Running with SQLite database.")
        print("   SQLite is for local development only.")
        print("   Do NOT use this in production or multi-worker setups.")
        print("=" * 60)
        
    # Startup recovery (TASK-V07 follow-up)
    if settings.ENABLE_STARTUP_RECOVERY:
        print("⚠️  Startup recovery enabled — processing stuck tasks...")
        recover_stuck_tasks()
    else:
        print("ℹ️  Startup recovery DISABLED — skipping stuck task recovery.")
    await configure_redis_limits() # Phase 8: Redis optimization
    listener_task = asyncio.create_task(redis_listener())
    
    # C-5: Start GPU heartbeat so the router knows we're alive
    from app.workers.asr_worker import start_heartbeat_loop
    from app.routers.live import active_asr_sessions
    heartbeat_task = asyncio.create_task(
        start_heartbeat_loop(lambda: len(active_asr_sessions))
    )
    print(f"[Heartbeat] GPU heartbeat loop started.")
    
    yield
    
    heartbeat_task.cancel()
    listener_task.cancel()

app = FastAPI(
    title="Call Rating Platform API",
    description="Local automated call transcription and AI evaluation platform.",
    version="1.0.0",
    lifespan=lifespan
)

# Instrument the app for Prometheus (Phase 8)
Instrumentator().instrument(app).expose(app)

# CORS configuration — allow React frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:5173"),
        "http://localhost:8000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(audio.router)
app.include_router(analytics.router)
app.include_router(system.router)
app.include_router(export.router)
app.include_router(hr.router)
app.include_router(notes.router)
app.include_router(websocket_router.router)
app.include_router(live.router)
app.include_router(review.router)
for router in OPTIONAL_ROUTERS:
    if router is not None:
        app.include_router(router)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Welcome to the Call Rating Platform API.",
        "docs": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
