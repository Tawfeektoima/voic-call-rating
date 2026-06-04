# Production Readiness Checklist

This document is the handoff checklist for deploying the Voice Call Rating Platform safely.

## Required Environment Variables

- `SECRET_KEY`
- `ENVIRONMENT=production`
- `DATABASE_URL`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `REDIS_PASSWORD`
- `HF_TOKEN`
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `UPLOAD_DIR`
- `MAX_FILE_SIZE_MB`
- `ALLOWED_EXTENSIONS`
- `FRONTEND_URL`

## Required Services

- PostgreSQL 16+
- Redis 7+ with authentication enabled
- FastAPI API process
- Celery worker process
- Frontend static build output from `npm run build`

## Deployment Steps

1. Copy `.env.example` to `.env` and replace every placeholder secret.
2. Start infrastructure:
   `docker compose -f docker-compose.prod.yml up -d postgres redis`
3. Run migrations:
   `docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head`
4. Start the API and worker:
   `docker compose -f docker-compose.prod.yml up -d api worker`
5. Build the frontend:
   `cd "AI Call Center Platform" && npm ci && npm run build`

## Local Production-Like Commands

- API:
  `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Worker:
  `celery -A app.worker.celery_app worker --loglevel=info`
- Backend verification:
  `python -m compileall app`
  `python -m pytest -q tests`

## Health Checks

- API root:
  `GET /`
- Authenticated system metrics:
  `GET /api/system/metrics`
- Container health:
  `docker compose -f docker-compose.prod.yml ps`
- PostgreSQL readiness:
  `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB`
- Redis readiness:
  `redis-cli -a $REDIS_PASSWORD ping`

## Smoke Path

Run the in-process smoke test after dependencies are installed:

`python run_smoke_test.py`

The smoke runner verifies:
- login
- protected `/api/auth/me`
- audio upload
- call result retrieval
- CSV export

## Security and Data Protection Markers

- Production startup does not call `Base.metadata.create_all(...)`.
- Production rejects SQLite.
- Production rejects unauthenticated Redis URLs.
- `ADMIN` receives raw export content.
- `QA` and `HR_MANAGER` receive redacted export content.
- `AGENT` is denied export access.
- Successful exports are logged with `success=true`.
- Denied export attempts are logged with `success=false`.
