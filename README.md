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

## Production Hardening

- Production startup does not create tables automatically. Run Alembic migrations before starting the API:
```bash
alembic upgrade head
```
- Production Redis must be authenticated. Set `REDIS_PASSWORD` and point the app at the protected Redis service, or provide fully authenticated Redis URLs directly.
- The app builds Redis defaults only outside production. In production, use authenticated Redis settings only.

## Running the Platform
Use the provided batch file:
`run_platform.bat`

For external interview testing through Cloudflare Tunnel:
`start_public_tunnel.bat`

Or start services manually:
1. **Backend:** `uvicorn app.main:app --reload`
2. **Worker:** `celery -A app.worker.celery_app worker --loglevel=info -P solo`
3. **Frontend:** `cd "AI Call Center Platform" && npm run dev`

### Public Interview Tunnel

- For external interview links, expose the frontend through a public host such as Cloudflare Tunnel and set `PUBLIC_BASE_URL` to that origin.
- The frontend now serves the public candidate route at `/interview-portal`, and Vite proxies `/api` and `/ws` back to the local backend during development.
- If you want invite creation to fail whenever no public host is configured, set `REQUIRE_PUBLIC_BASE_URL_FOR_INTERVIEWS=true`.
- `start_public_tunnel.bat` starts backend, worker, frontend, and `cloudflared.exe` in separate windows. After Cloudflare shows the public URL, place it in `PUBLIC_BASE_URL` and restart the backend so generated invite links use that public origin.

## Production Deployment

Use the production compose file for API, worker, PostgreSQL, and Redis services:

```bash
docker compose -f docker-compose.prod.yml up -d postgres redis
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
docker compose -f docker-compose.prod.yml up -d api worker
```

The production stack expects PostgreSQL and Redis credentials in the environment.

## Release Verification

- Backend compile check:
  `python -m compileall app`
- Backend test suite:
  `python -m pytest -q tests`
- Frontend test and build:
  `cd "AI Call Center Platform" && npm ci && npm test && npm run build`
- Basic product smoke path:
  `python run_smoke_test.py`

See `docs/production_readiness.md` for the full deployment checklist, required environment variables, health checks, and smoke-test expectations.

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
