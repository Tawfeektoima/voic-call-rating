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
- `PUBLIC_BASE_URL` (required if interview invites must always resolve through a public host)
- `INTERVIEW_PORTAL_PATH`

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

## Public Interview Access

- Set `PUBLIC_BASE_URL` to the public frontend origin you expose through Cloudflare Tunnel or your production host.
- Keep `INTERVIEW_PORTAL_PATH=/interview-portal` unless you intentionally move the public candidate route.
- If interview invites must never fall back to localhost-style links, set `REQUIRE_PUBLIC_BASE_URL_FOR_INTERVIEWS=true`.
- Optional startup verification: set `ENABLE_PUBLIC_BASE_URL_HEALTHCHECK=true` to log whether the public host is reachable when the API boots.

## Local Production-Like Commands

- API:
  `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Worker:
  `celery -A app.worker.celery_app worker --loglevel=info`
- Backend verification:
  `python -m compileall app`
  `python -m pytest -q tests`

## External Tunnel Testing

- Use `start_public_tunnel.bat` for local external-access testing through Cloudflare Tunnel.
- Keep `cloudflared.exe` in the project root before launching that script.
- After the tunnel window prints the public `https://...trycloudflare.com` origin, set `PUBLIC_BASE_URL` to that value and restart the backend if HR-generated interview invites should use the public URL.

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
