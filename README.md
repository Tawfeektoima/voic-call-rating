# Voice Call Rating Platform

Production-ready platform for automated call quality assurance and business intelligence.

## Prerequisites

### 1. FFmpeg Installation (Required for Audio Decoding)
The system requires FFmpeg for audio processing. If you see `torchcodec` warnings or audio decoding errors, ensure FFmpeg is installed and in your PATH.

**Windows:**
1. Download the latest build from [Gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or [BtbN](https://github.com/BtbN/FFmpeg-Builds/releases).
2. Extract the ZIP to a folder (e.g., `C:\ffmpeg`).
3. Add the `bin` folder (`C:\ffmpeg\bin`) to your System Environment Variables **PATH**.
4. Restart your terminal and verify with `ffmpeg -version`.

**Linux (Ubuntu/Debian):**
```bash
sudo apt update && sudo apt install ffmpeg
```

### 2. Python Environment
1. Create a virtual environment: `python -m venv .venv`
2. Activate it: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Linux)
3. Install dependencies: `pip install -r requirements.txt`

## Running the Platform
Use the provided batch file:
`run_platform.bat`

Or start services manually:
1. **Backend:** `uvicorn app.main:app --reload`
2. **Worker:** `celery -A app.worker.celery_app worker --loglevel=info -P solo`
3. **Frontend:** `cd "AI Call Center Platform" && npm run dev`
