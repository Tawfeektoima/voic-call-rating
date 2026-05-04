import os
import uvicorn
from dotenv import load_dotenv
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
from app.routers import audio, analytics, admin, auth, system, export, hr

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Call Rating Platform API",
    description="Local automated call transcription and AI evaluation platform.",
    version="1.0.0"
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


@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Welcome to the Call Rating Platform API.",
        "docs": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
