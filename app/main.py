import os
import uvicorn
import json
import asyncio
import redis.asyncio as aioredis
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure FFmpeg is in PATH for torchcodec/hardware decoding
# Ensure .venv/Scripts is in PATH if it exists locally
base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scripts_path = os.path.join(base_path, ".venv", "Scripts")
if os.path.exists(scripts_path) and scripts_path not in os.environ["PATH"]:
    os.environ["PATH"] = scripts_path + os.pathsep + os.environ["PATH"]

# Load environment variables
load_dotenv()

from app.database import engine, Base
from app.routers import audio, analytics, admin, auth, system, export, hr, websocket_router
from app.recovery import recover_stuck_tasks
from app.services.websocket import manager
from app.config import get_settings

# Create database tables automatically
Base.metadata.create_all(bind=engine)

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    recover_stuck_tasks()
    listener_task = asyncio.create_task(redis_listener())
    yield
    listener_task.cancel()

app = FastAPI(
    title="Call Rating Platform API",
    description="Local automated call transcription and AI evaluation platform.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
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
app.include_router(websocket_router.router)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Welcome to the Call Rating Platform API.",
        "docs": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
