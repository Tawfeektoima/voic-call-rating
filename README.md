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

## Database Requirements

- **Development:** SQLite is supported for local testing only.
- **Production:** PostgreSQL 16+ is required. Set `ENVIRONMENT=production` in your `.env` file to enforce this. The application will refuse to start with SQLite if `ENVIRONMENT=production` is set.
- **Multi-worker:** SQLite will cause `database is locked` errors with multiple Celery workers. Always use PostgreSQL for any multi-worker setup.

## Running the Platform
Use the provided batch file:
`run_platform.bat`

Or start services manually:
1. **Backend:** `uvicorn app.main:app --reload`
2. **Worker:** `celery -A app.worker.celery_app worker --loglevel=info -P solo`
3. **Frontend:** `cd "AI Call Center Platform" && npm run dev`

## Utility Scripts

All utility scripts are located in the `scripts/` directory.

### Operations (scripts/ops/)
| Script | Purpose | Destructive? |
|---|---|---|
| `clear_calls.py` | Removes all call records from the database | ⚠️ Yes — requires --confirm |
| `purge_db.py` | Wipes entire database | ⚠️ Yes — requires --confirm |
| `migrate_db.py` | Runs Alembic migrations manually | No |
| `fix_roles.py` | Fixes user role assignments | No |

### Development (scripts/dev/)
| Script | Purpose |
|---|---|
| `check_db.py` | Inspect database state |
| `demo.py` | Load demo data for testing |
