# Voice Call Rating Platform — System Architecture

> Version: 1.2  
> Last updated: 2026-06-27  
> Stack: FastAPI · PostgreSQL · Redis · Celery · WhisperX · Groq · ChromaDB · Google Sheets API · ClamAV/clamd · FFprobe · React/TypeScript  
> Deployment: Docker Compose inside an isolated Linux VM, with Cloudflare Tunnel only for approved public surfaces

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Topology](#2-system-topology)
3. [Repository Structure](#3-repository-structure)
4. [Backend Architecture](#4-backend-architecture)
   - 4.1 [API Layer](#41-api-layer)
   - 4.2 [Authentication, Sessions, and RBAC](#42-authentication-sessions-and-rbac)
   - 4.3 [Database Layer](#43-database-layer)
   - 4.4 [Celery and Worker Topology](#44-celery-and-worker-topology)
   - 4.5 [Secure Recording Ingestion Pipeline](#45-secure-recording-ingestion-pipeline)
5. [AI Processing Pipeline](#5-ai-processing-pipeline)
6. [Frontend Architecture](#6-frontend-architecture)
7. [Infrastructure and Deployment](#7-infrastructure-and-deployment)
8. [Security Model](#8-security-model)
   - 8.1 [Protect Architecture](#81-protect-architecture)
   - 8.2 [Recording Ingestion Isolation Boundary](#82-recording-ingestion-isolation-boundary)
9. [Core Data Model Additions](#9-core-data-model-additions)
10. [Migration History Highlights](#10-migration-history-highlights)
11. [Quality and Delivery Tooling](#11-quality-and-delivery-tooling)

---

## 1. Project Overview

The Voice Call Rating Platform is a production-oriented QA platform for call-center operations. It now has two major secure input paths:

- direct call uploads into the existing AI evaluation pipeline
- scheduled recording ingestion from a private spreadsheet-based source, designed for VICIdial-style reporting workflows

At a high level, the platform:

- collects call audio
- transcribes and diarizes speech
- scores calls against campaign-specific rubrics
- surfaces results to role-based operational dashboards
- enforces runtime security controls around user sessions, trusted devices, and shift eligibility
- contains untrusted external recordings inside an isolated VM before they can enter the main AI pipeline

In addition to QA, the platform includes HR/compliance workflows, interview workflows, team management, system observability, and security admin tooling.

---

## 2. System Topology

```text
React SPA / Live Browser Client
  -> HTTPS / WebSocket
  -> FastAPI API

FastAPI API
  -> PostgreSQL
  -> Redis
  -> Celery tasks

Celery workers
  -> GPU worker for call processing
  -> downloader worker for source ingestion
  -> inspector worker for quarantine inspection
  -> scheduler worker for timed ingestion runs

Secure ingestion side path
  -> Google Sheet reader
  -> allowlisted download
  -> quarantine
  -> malware scan
  -> media verification
  -> accepted storage
  -> Call creation
  -> existing process_call_audio_task
```

Operationally, the system is split into:

- control plane: API, admin actions, security decisions, audit records
- processing plane: Celery workers, transcription, evaluation, feature extraction
- containment plane: isolated recording ingestion, quarantine storage, scanner, media verifier

---

## 3. Repository Structure

```text
project-root/
|
|-- app/
|   |-- main.py                         # FastAPI startup, router registration, startup validation
|   |-- config.py                       # Settings + production/runtime safety validation
|   |-- models.py                       # ORM models for calls, security, interview, ingestion
|   |-- schemas.py                      # Safe request/response contracts
|   |-- worker.py                       # Main Celery app and task routing
|   |
|   |-- routers/
|   |   |-- auth.py
|   |   |-- live.py
|   |   |-- recording_ingestion.py      # Secure ingestion operations API
|   |   |-- security_admin.py           # Shifts/sessions/devices admin plane
|   |   `-- ...
|   |
|   `-- services/
|       |-- recording_ingestion.py      # Source read, download, scan, verify, handoff
|       |-- media_verifier_server.py    # Isolated ffprobe verification service
|       |-- security_policy.py          # Protect policy engine
|       |-- security_observability.py   # Safe security monitoring helpers
|       `-- transcription.py            # Transcript sanitization and processing support
|
|-- alembic/versions/                   # Schema history
|-- deploy/ingestion-vm/                # Guest bootstrap and VM hardening
|-- docs/                               # Runbooks, rollout docs, VM evidence
|-- scripts/                            # Helper utilities, including standalone downloader CLI
|-- specs/001-call-recording-ingestion/ # Spec Kit artifacts for secure ingestion
|-- tests/                              # Backend/security/ingestion regression tests
|-- tests/fixtures/recording_ingestion/ # Synthetic source/audio fixtures
|-- AI Call Center Platform/src/app/    # Frontend application
|   |-- pages/AdminSecurity.tsx         # Security control plane UI
|   |-- lib/deviceIdentity.ts           # Stable browser device identity
|   `-- __tests__/                      # Frontend security regressions
|-- docker-compose.prod.yml             # Production topology with split roles
|-- Dockerfile
`-- ARCHITECTURE.md
```

---

## 4. Backend Architecture

### 4.1 API Layer

The backend is a FastAPI application composed of domain routers and dependency-driven authorization.

Common dependencies:

- `get_db` for request-scoped database sessions
- `get_current_user` for authentication and current employee resolution
- permission gates for RBAC-protected operations

Key route groups:

| Prefix | Responsibility |
|---|---|
| `/api/auth` | login, OTP, identity, logout |
| `/api/calls` | call upload, retrieval, review, scoring flows |
| `/api/live` / WebSocket routes | real-time/live-call workflows |
| `/api/interview` | interview jobs, sessions, answers, workflow state |
| `/api/hr` | compliance, HR, violations, attendance |
| `/api/system` | health, metrics, service readiness |
| `/api/recording-ingestion` | manual ingestion run, run list/detail, record pagination, retry |
| `/api/security-admin` | shift management, session revocation, trusted-device lifecycle |

The ingestion API is intentionally sanitized: raw recording URLs, secrets, scanner output, and absolute guest paths are not part of response contracts.

### 4.2 Authentication, Sessions, and RBAC

Authentication combines:

- password verification
- OTP challenge flow
- JWT bearer tokens
- server-side session state
- trusted-device enforcement
- shift-based access control

This means access is not granted by JWT alone. Protected HTTP and WebSocket access are revalidated against database-backed security state.

Permissions are stored in database-backed role/permission tables, not only in static code. That allows operational role updates without redeploying the application.

### 4.3 Database Layer

Primary database:

- PostgreSQL in production
- SQLite only for isolated development/tests

The schema is managed with Alembic and now includes three notable groups:

- core QA / HR / interview tables
- Protect Architecture security tables
- recording ingestion run/record/attempt tracking tables

The ingestion tables provide durable idempotency and auditability independent of the source dialer database.

### 4.4 Celery and Worker Topology

Redis acts as:

- Celery broker
- operational cache/state store
- lightweight heartbeat store

Worker roles are split by trust boundary and workload:

| Worker / Service | Queue / Role | Responsibility |
|---|---|---|
| `worker` | primary/GPU | existing call audio processing, transcription, evaluation |
| `ingestion-downloader` | `ingestion-download` | read source, validate rows, download new recordings into quarantine |
| `ingestion-inspector` | `ingestion-inspection` | inspect quarantine files, promote accepted files, hand off to call pipeline |
| `ingestion-scheduler` | Celery beat | periodic ingestion runs |

This split prevents network-bound ingestion from starving the GPU-backed AI path.

### 4.5 Secure Recording Ingestion Pipeline

The new ingestion subsystem is implemented in `app/services/recording_ingestion.py` and orchestrated through `app/worker.py`.

Flow:

```text
Private Google Sheet
  -> read configured worksheet/range
  -> validate headers and row fields
  -> derive source identity and dedupe fingerprint
  -> resolve employee/campaign
  -> allowlisted HTTPS download
  -> stream to quarantine temp file
  -> compute SHA-256 + byte count
  -> commit quarantine file atomically
  -> signature validation
  -> ClamAV/clamd malware scan
  -> isolated media verification via FFprobe service
  -> promote to accepted storage
  -> create Call
  -> queue process_call_audio_task exactly once
```

Core guarantees:

- one active run per source
- durable duplicate protection by source key and URL fingerprint
- retries only for eligible failure classes
- rejected or uninspected files never become `Call` records
- accepted files enter the existing call-processing pipeline without exposing the external recording source

The system also keeps a standalone CLI downloader in `scripts/download_call_recordings.py` for migration and diagnostics, but production ingestion uses database state rather than a local manifest file.

---

## 5. AI Processing Pipeline

The accepted ingestion path converges into the same downstream call pipeline used by normal uploads.

Main stages:

1. call enters the system in `PENDING`
2. transcription/diarization runs through WhisperX-style processing
3. transcript is treated as untrusted content and sanitized before evaluation
4. evaluation output is validated against application schemas
5. structured results, violations, KPIs, and summaries are persisted
6. dashboards, exports, and live updates consume the stored safe outputs

Important new invariant:

- recording ingestion is a pre-processing boundary, not a replacement pipeline
- only accepted recordings can cross into the existing AI stages

---

## 6. Frontend Architecture

The frontend is a React/TypeScript application under `AI Call Center Platform/src/app`.

Recent architecture additions include:

- stable browser device identity via `lib/deviceIdentity.ts`
- forced-logout handling for revoked sessions/devices or invalid shifts
- admin security APIs via `lib/securityAdminApi.ts`
- admin security UI in `pages/AdminSecurity.tsx`
- secure HR conversion UX that avoids shipping shared default credentials in the browser

Frontend responsibilities now include both product UX and security-state UX:

- preserving device identity across logout/login
- responding to security denial codes cleanly
- exposing admin controls for sessions, shifts, and trusted devices
- treating onboarding/password fields as sensitive inputs with safer defaults

---

## 7. Infrastructure and Deployment

Production deployment is centered on `docker-compose.prod.yml`, but the secure ingestion feature assumes the stack runs inside a dedicated Linux guest VM.

Current service topology:

```yaml
services:
  postgres:
  redis:
  api:
  worker:
  ingestion-downloader:
  ingestion-inspector:
  ingestion-scheduler:
  scanner-updater:
  scanner:
  media-verifier:
```

Important deployment rules:

- `api` exposes only the approved guest-local management port
- `worker` handles accepted call processing only
- `ingestion-downloader` cannot directly promote files into accepted storage
- `ingestion-inspector` is the promotion boundary
- `scanner` and `media-verifier` remain on internal-only networks

Production startup safety checks in `app/config.py` and `app/main.py` enforce:

- PostgreSQL-only production database usage
- Redis authentication / writable broker expectations
- explicit ingestion role splitting
- required scanner/media-verifier configuration
- safe guest-local storage layout for quarantine/accepted/rejected/state

The VM runbook and validation evidence live in:

- `docs/vm-ingestion-runbook.md`
- `docs/vm-isolation-verification.md`
- `deploy/ingestion-vm/bootstrap.sh`
- `scripts/provision-ingestion-vm.ps1`

For local code-quality analysis, the repository also includes a separate SonarQube stack and coverage helpers:

- `docker-compose.sonarqube.yml` for local SonarQube orchestration
- `scripts/run-backend-coverage.ps1` for Python coverage export
- `scripts/run-frontend-coverage.ps1` for Vitest/V8 coverage export
- `scripts/run-sonarqube.ps1` for end-to-end local scan execution
- `sonar-project.properties` and `AI Call Center Platform/tsconfig.sonar.json` for source/test scoping

These quality-analysis assets are intentionally local/developer-facing and are not part of the production runtime topology.

---

## 8. Security Model

### 8.1 Protect Architecture

The Protect Architecture adds runtime access control around sensitive HTTP and WebSocket paths.

Core capabilities:

- one active server-side session per employee
- shift-based access control
- trusted-device enforcement
- admin control plane for shifts, sessions, and devices
- audit-safe denial/revocation evidence
- environment-driven bootstrap admin credential provisioning instead of hard-coded credentials

The rollout is policy-mode driven:

| Mode | Meaning |
|---|---|
| `off` | legacy behavior allowed |
| `audit` | evaluate and log security decisions without blocking |
| `enforce` | block requests and connections that fail policy |

This policy layer applies to:

- login/session issuance
- protected HTTP routes
- WebSocket connect and revalidation
- frontend forced logout behavior

### 8.2 Recording Ingestion Isolation Boundary

The recording ingestion feature treats external audio as untrusted input until inspection completes.

Isolation controls:

- source access is guest-initiated only
- only HTTPS and allowlisted hosts are accepted
- redirects must remain allowlisted
- downloads land in quarantine first
- promotion requires:
  - file-signature validation
  - ClamAV/clamd scan
  - bounded FFprobe/media verification
- rejected files never enter accepted storage, never create a `Call`, and never queue the downstream AI pipeline

Guest-level containment assumptions:

- no host-drive mounts
- no shared folders
- no clipboard sharing
- no drag-and-drop
- no USB passthrough
- NAT/default-deny inbound network posture

Audit/logging controls:

- no raw recording URLs in API output
- no scanner output in normal responses
- no absolute guest paths in public or operator-facing status payloads
- retries remain bounded and safe by category

Credential-handling controls now also require:

- `setup_admin.py` to read `VOICEQA_BOOTSTRAP_ADMIN_CREDENTIAL` from the environment at execution time
- password-strength validation before bootstrap credential use
- no shared/default onboarding password rendered directly into frontend defaults
- no credential values echoed back in bootstrap/admin setup logs

---

## 9. Core Data Model Additions

Two major data-model expansions were added recently.

### Protect Architecture tables

- `employee_shifts`
- `trusted_devices`
- `user_sessions`

These support runtime security decisions and admin enforcement actions.

### Recording ingestion tables

- `recording_ingestion_runs`
- `recording_ingestion_records`
- `recording_ingestion_attempts`

These tables track:

- source identity
- dedupe state
- retry state
- inspection stage outcomes
- hashes and storage references
- linkage from accepted recording to final `Call`

---

## 10. Migration History Highlights

Important recent Alembic revisions:

| Revision | Description |
|---|---|
| `c3a07b8b4092` | Adds Protect Architecture tables: `employee_shifts`, `trusted_devices`, `user_sessions` |
| `b2c9a1d8e4f7` | Adds recording ingestion runs, records, attempts, inspection statuses, retry state, and `Call` linkage |

Older migrations continue to cover the core call, HR, role, notes, KPI, and interview modules.

---

## 11. Quality and Delivery Tooling

The repository now maintains a local static-analysis and coverage workflow alongside application tests.

Main pieces:

- backend coverage via `pytest`, `pytest-cov`, and `.coveragerc`
- frontend coverage via `vitest`, `@vitest/coverage-v8`, and `AI Call Center Platform/vitest.config.ts`
- local SonarQube scanning through Docker with repository-scoped helper scripts
- targeted regression tests for security-sensitive onboarding and bootstrap-admin flows

Recent verification additions include:

- `tests/test_setup_admin.py` for bootstrap-admin credential and logging behavior
- `AI Call Center Platform/src/app/__tests__/callPresentationCoverage.test.tsx`
- expanded launcher and HR interview regression coverage for modified frontend paths

This quality layer is designed to:

- catch hard-coded credential regressions early
- track new-code coverage separately from legacy code coverage
- give maintainers a repeatable local scan path before pushing or releasing changes

---

This document is intended to reflect the implemented architecture, not only the original design intent. For the most detailed secure-ingestion design artifacts, see `specs/001-call-recording-ingestion/`.
