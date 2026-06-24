# ARCHITECTURE.md

# Voice Call Rating Platform — System Architecture

> **Version:** 1.0  
> **Stack:** FastAPI · PostgreSQL · Redis · Celery · WhisperX · Groq · ChromaDB · React/TypeScript  
> **Deployment:** Docker Compose · Cloudflare Tunnel

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Repository Structure](#3-repository-structure)
4. [Backend Architecture](#4-backend-architecture)
   - 4.1 [API Layer (FastAPI)](#41-api-layer-fastapi)
   - 4.2 [Authentication & RBAC](#42-authentication--rbac)
   - 4.3 [Database Layer](#43-database-layer)
   - 4.4 [Task Queue (Celery + Redis)](#44-task-queue-celery--redis)
5. [AI Processing Pipeline](#5-ai-processing-pipeline)
   - 5.1 [Batch Call Pipeline](#51-batch-call-pipeline)
   - 5.2 [Live Streaming Pipeline](#52-live-streaming-pipeline)
   - 5.3 [RAG System & HITL Loop](#53-rag-system--hitl-loop)
6. [Data Models & Schema](#6-data-models--schema)
7. [Role Hierarchy & Permissions](#7-role-hierarchy--permissions)
8. [Module Breakdown](#8-module-breakdown)
   - 8.1 [QA & Call Evaluation](#81-qa--call-evaluation)
   - 8.2 [Operations Reporting](#82-operations-reporting)
   - 8.3 [Team Management](#83-team-management)
   - 8.4 [HR & Compliance](#84-hr--compliance)
   - 8.5 [Interview Module](#85-interview-module)
   - 8.6 [System Monitoring](#86-system-monitoring)
9. [Frontend Architecture](#9-frontend-architecture)
10. [Infrastructure & Deployment](#10-infrastructure--deployment)
11. [Security Model](#11-security-model)
   - 11.1 [Protect Architecture Six-Phase Security Rollout](#111-protect-architecture-six-phase-security-rollout)
12. [Database Migration History](#12-database-migration-history)
13. [End-To-End Protect Architecture QA Checklist](#13-end-to-end-protect-architecture-qa-checklist)
14. [Protect Architecture Production Rollout](#14-protect-architecture-production-rollout)

---

## 1. Project Overview

The **Voice Call Rating Platform** is a production-grade, AI-powered Quality Assurance (QA) system for call centers. It automates the full QA lifecycle:

- **Ingests** audio recordings of agent–customer calls
- **Transcribes** and **diarizes** them (separating speakers)
- **Analyzes** emotion, NLP metrics, and compliance
- **Scores** calls using an LLM (Groq) against campaign-specific rubrics
- **Surfaces** insights to an 8-role management hierarchy via dashboards
- **Coaches** agents in real-time via a WebSocket-powered live call assistant

The platform additionally handles HR workflows, interview/candidate screening, attendance tracking, team management, and operational KPI reporting.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                                  │
│  ┌───────────────────────┐   ┌──────────────────────────────────┐   │
│  │   React SPA (Vite)    │   │  Browser Extension (Live Agent)  │   │
│  │   TypeScript + MUI    │   │  PCM Audio Stream via WebSocket  │   │
│  └──────────┬────────────┘   └─────────────┬────────────────────┘   │
└─────────────┼───────────────────────────────┼───────────────────────┘
              │ REST (HTTPS)                  │ WebSocket (WSS)
              ▼                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     API GATEWAY LAYER                                │
│               FastAPI Application (uvicorn)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  /auth   │ │  /calls  │ │  /ops    │ │   /hr    │ │/interview│  │
│  │  /agents │ │/campaigns│ │ /system  │ │  /teams  │ │ /review  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────────┐  ┌──────────────┐
│  PostgreSQL  │  │  Redis (Broker + │  │  ChromaDB    │
│  (Primary DB)│  │  Cache + State)  │  │  (Vector DB) │
└──────────────┘  └────────┬─────────┘  └──────────────┘
                           │
              ┌────────────▼───────────┐
              │     Celery Workers      │
              │  ┌────────────────────┐│
              │  │  ASR Worker        ││  ← WhisperX + Pyannote (GPU)
              │  │  (GPU-bound)       ││
              │  ├────────────────────┤│
              │  │  Eval Worker       ││  ← Groq LLM Inference
              │  │  (CPU/API-bound)   ││
              │  ├────────────────────┤│
              │  │  RAG Worker        ││  ← sentence-transformers + ChromaDB
              │  │  (Embedding)       ││
              │  ├────────────────────┤│
              │  │  Interview Worker  ││  ← Transcribe + Score Answers
              │  └────────────────────┘│
              └────────────────────────┘
```

---

## 3. Repository Structure

```
project-root/
│
├── app/                          # Backend (FastAPI)
│   ├── main.py                   # App factory, middleware, router registration
│   ├── config.py                 # Settings (Pydantic BaseSettings)
│   ├── database.py               # SQLAlchemy engine & session
│   ├── models.py                 # All ORM models
│   ├── schemas.py                # Pydantic request/response schemas
│   ├── permissions.py            # Permission enum & RBAC logic
│   │
│   ├── routers/                  # API route handlers
│   │   ├── auth.py               # Login, OTP, JWT
│   │   ├── calls.py              # Call upload, retrieval, scoring override
│   │   ├── campaigns.py          # Campaign CRUD + prompt management
│   │   ├── employees.py          # Employee CRUD, bulk onboarding
│   │   ├── teams.py              # Team CRUD, assignments
│   │   ├── review.py             # HITL Golden Pair review queue
│   │   ├── ops.py                # Ops Manager dashboards & reports
│   │   ├── team_leader.py        # Team Leader scoped endpoints
│   │   ├── team_manager.py       # Team Manager scoped endpoints
│   │   ├── hr.py                 # HR dashboard, violations, attendance
│   │   ├── interview.py          # Interview jobs, candidates, sessions
│   │   ├── system.py             # System metrics, alerts, service health
│   │   ├── websocket.py          # Live audio WebSocket endpoint
│   │   └── export.py             # Audit-logged data exports
│   │
│   ├── workers/                  # Celery task definitions
│   │   ├── asr_worker.py         # WhisperX transcription + diarization
│   │   ├── eval_worker.py        # Groq LLM evaluation
│   │   ├── rag_worker.py         # Embedding + ChromaDB indexing
│   │   └── interview_worker.py   # Interview answer evaluation
│   │
│   ├── services/                 # Business logic layer
│   │   ├── ops_reporting.py      # Ops dashboard aggregation queries
│   │   ├── team_manager_reporting.py
│   │   ├── team_scope.py         # Scoped access helpers (team/agent filtering)
│   │   ├── role_permissions.py   # DB-backed permission seeding & management
│   │   ├── aggregation.py        # Core KPI calculation utilities
│   │   ├── public_links.py       # Interview invite URL builder
│   │   └── websocket.py          # WebSocket connection manager
│   │
│   └── middleware/
│       ├── audit.py              # Audit event logging middleware
│       └── pii_redaction.py      # PII redaction for exports
│
├── alembic/                      # Database migrations
│   └── versions/                 # ~20 migration files (chronological)
│
├── frontend/                     # React TypeScript SPA
│   ├── src/
│   │   ├── app/                  # App-level routing and providers
│   │   ├── components/           # Shared UI components
│   │   ├── pages/                # Role-specific page views
│   │   ├── hooks/                # Custom React hooks
│   │   ├── services/             # Axios API client
│   │   └── types/                # TypeScript interfaces
│   ├── vite.config.ts
│   └── package.json
│
├── docs/
│   └── mockData.reference.ts     # Frontend mock data reference
│
└── docker-compose.yml            # Full stack orchestration
```

---

## 4. Backend Architecture

### 4.1 API Layer (FastAPI)

The API is built with **FastAPI** and organized into domain-scoped routers. All routes use **Dependency Injection** for:
- `get_db` — SQLAlchemy session per request
- `get_current_user` — JWT token validation → returns `Employee` ORM object
- `require_permission(Permission.X)` — RBAC gate per endpoint

| Router Prefix | Domain | Key Operations |
|---|---|---|
| `/api/auth` | Authentication | Login, OTP challenge, JWT refresh |
| `/api/calls` | Call Management | Upload, retrieve, score override, export |
| `/api/campaigns` | Campaign Config | CRUD, evaluation prompt management |
| `/api/review` | HITL Review | Golden pair approve/reject, RAG indexing |
| `/api/ops` | Operations | Dashboard, KPIs, campaigns, violations, attendance |
| `/api/team-leader` | Team Leader | Scoped teams/agents/calls view |
| `/api/team-manager` | Team Manager | Cross-team reporting, transfer requests |
| `/api/hr` | HR | Violations, attendance, bulk onboarding, notes |
| `/api/interview` | Interview | Jobs, candidates, sessions, answer evaluation |
| `/api/system` | System Health | Metrics, service probes, alert management |
| `/api/export` | Data Export | Audit-logged CSV exports |
| `ws://` | WebSocket | Live audio stream + RAG coaching push |

### 4.2 Authentication & RBAC

Authentication uses **JWT Bearer tokens** with an **OTP email challenge** layer:

```
POST /api/auth/login
  → Validate email/password (bcrypt)
  → Generate OTP → Send to employee email
  → Return { requires_otp: true }

POST /api/auth/verify-otp
  → Validate OTP hash, expiry (5 attempts max)
  → Return { access_token: JWT }
```

**Permissions** are stored in the database (`app_permissions` + `role_permissions` tables) and seeded on startup. The `Permission` enum has **26 permission keys** covering every action in the system. Admins can reassign permissions per role via the API without redeployment.

### 4.3 Database Layer

- **Primary DB:** PostgreSQL 16 (production) / SQLite (development only)
- **ORM:** SQLAlchemy with **Alembic** migrations
- **Session management:** Per-request sessions via `get_db()` dependency

Performance indexes are defined on all high-frequency filter columns:
- `calls(status, created_at)`, `calls(employee_id, created_at)`, `calls(campaign_id, created_at)`
- `agent_violations(severity, hr_flagged, created_at)`
- `employees(role, status)`

### 4.4 Task Queue (Celery + Redis)

All AI-heavy and async operations run as **Celery tasks** backed by **Redis**:

| Worker | Bound To | Responsibility |
|---|---|---|
| `asr_worker` | GPU queue | WhisperX transcription, Pyannote diarization |
| `eval_worker` | CPU queue | Groq LLM call evaluation, feature engineering |
| `rag_worker` | CPU queue | sentence-transformer embedding, ChromaDB upsert |
| `interview_worker` | CPU queue | Interview answer transcription + scoring |

A GPU heartbeat key (`gpu:0:heartbeat`) is written by the ASR worker to Redis every cycle, allowing the System Health endpoint to probe GPU availability without direct process inspection.

---

## 5. AI Processing Pipeline

### 5.1 Batch Call Pipeline

Every uploaded call file progresses through the following states, managed by Celery:

```
UPLOAD
  │
  ▼
[PENDING] ──► Celery dispatches to ASR Worker
  │
  ▼
[PROCESSING] ──► Stage 1: WhisperX transcription (word-level timestamps)
              ──► Stage 2: Pyannote diarization (SPEAKER_00, SPEAKER_01...)
              ──► Stage 3: Semantic speaker assignment
                          (Heuristic: more talk time = AGENT)
  │
  ▼
              ──► Stage 4: Feature Engineering
                          • call_hour, call_day_of_week
                          • agent_talk_time, customer_talk_time, talk_ratio
                          • calls_before_this (agent workload context)
                          • filler_words, interruptions, response_latency
                          • acoustic_delta (emotion shift metrics)
                          • nlp_metrics (sentiment, keyword density)
  │
  ▼
              ──► Stage 5: Groq LLM Evaluation
                          • Campaign-specific evaluation prompt injected
                          • Returns: score (0–100), strengths[], weaknesses[]
                          • Violations[] with severity/score_deduction/hr_flag
                          • call_summary, call_outcome, lead_status
                          • Golden pair candidates (high-scoring Q&A moments)
                          • QA alarm flag (score below threshold)
  │
  ▼
[EVALUATED] ──► Results written to:
                • calls table (score, transcript, summary, emotion_timeline)
                • call_outcomes table (primary_outcome, outcome_value)
                • agent_violations table (per violation extracted)
                • golden_pair_candidates table (pending HITL review)
                • system_logs (if any errors occurred)
```

### 5.2 Live Streaming Pipeline

A browser extension connects to the WebSocket endpoint and streams raw PCM audio during active calls:

```
Browser Extension
  │ ws://host/ws/live/{agent_id}
  │ Binary frames: PCM 16kHz, 16-bit, Mono, 500ms chunks
  ▼
WebSocket Manager (FastAPI)
  │ Buffer accumulation
  │ Flush every ~3 seconds to ASR
  ▼
ASR Worker (WhisperX — streaming mode)
  │ Incremental transcript segments
  ▼
RAG Worker
  │ Embed latest agent utterance
  │ ChromaDB similarity search (filtered by campaign_id)
  ▼
WebSocket Manager
  │ Push top-3 matching Golden Pair suggestions back to agent UI
  ▼
Agent Browser Extension
  │ Displays real-time coaching card
```

Post-session, the full `agent_audio_path` is uploaded for standard batch evaluation.

### 5.3 RAG System & HITL Loop

The RAG (Retrieval-Augmented Generation) system builds a **campaign-isolated knowledge base** of proven best-practice responses extracted from real calls.

```
Batch Evaluation
  │ LLM identifies high-scoring Q&A exchange
  │ Creates GoldenPairCandidate (status=PENDING)
  ▼
HITL Review Queue (/api/review/queue)
  │ QA reviewer sees call context + candidate score
  │
  ├── APPROVE ──► sentence-transformers encode question
  │               ChromaDB.add(
  │                 embedding=vector,
  │                 metadata={campaign_id: X},   ← I-01 isolation filter
  │                 document=answer_text
  │               )
  │               Status → APPROVED
  │
  └── REJECT ──► Status → REJECTED (removed from queue)

Live Call Query
  │ Agent utterance embedded
  │ ChromaDB.query(
  │   query_embeddings=[...],
  │   where={campaign_id: X},   ← only same campaign's knowledge
  │   n_results=3
  │ )
  └──► Top matches pushed via WebSocket
```

> **Note:** ChromaDB is scoped **per campaign** via metadata filtering to prevent cross-campaign knowledge leakage.

---

## 6. Data Models & Schema

### Core Tables

```
employees              → All platform users (agents, managers, etc.)
  ├── role (ENUM)      → AGENT | QA | TEAMLEADER | TEAMMANAGER |
  │                       HRMANAGER | OPSMANAGER | AIENGINEER | ADMIN
  ├── tier (ENUM)      → BRONZE | SILVER | GOLD | PLATINUM
  ├── skills (JSON)    → empathy, resolution, communication, etc.
  └── emotion_history  → Weekly emotion consistency scores

campaigns              → Call center campaign definitions
  ├── type (ENUM)      → SALES | CUSTOMERSERVICE | COLLECTIONS | TECHNICAL
  ├── evaluation_prompt → LLM scoring rubric (customizable per campaign)
  └── kpis[]           → Campaign-specific KPI labels

calls                  → Central fact table for all evaluated calls
  ├── status           → PENDING | PROCESSING | EVALUATED | FAILED
  ├── transcript (JSON) → [{speaker, text, start, end, emotion, has_pii}]
  ├── emotion_timeline  → [{time, emotion, intensity}]
  ├── evaluation_score  → AI score (0–100)
  ├── overridden_score  → Human override score
  ├── qa_alarm (BOOL)  → True if score below campaign threshold
  ├── lead_status       → HOT | WARM | COLD
  └── nlp_metrics (JSON) → talk ratio, filler words, interruptions

call_outcomes          → Per-call outcome extracted by LLM
agent_violations       → Compliance violations with severity + score deduction
golden_pair_candidates → HITL review queue for RAG knowledge base
```

### Team & HR Tables

```
teams                  → Team definitions (linked to campaign + manager + leader)
employee_team_assignments → Agent ↔ Team membership (with history)
attendance_records     → Daily attendance (scheduled/worked/late minutes)
agent_transfer_requests → Cross-team transfer workflow
coaching_sessions      → Supervisor-agent coaching records (score before/after)
call_annotations       → Timestamped supervisor notes on calls
role_notes             → Internal messaging system across role hierarchy
kpi_threshold_configs  → Configurable KPI targets per team/campaign
operational_targets    → Segment-level metric targets for ops dashboards
```

### Security & Audit Tables

```
app_permissions        → Permission catalog (26 keys)
role_permissions       → Role ↔ Permission mapping (DB-backed, editable)
audit_events           → Full audit trail (actor, action, before/after state)
system_logs            → Pipeline errors and alerts
login_otp_challenges   → OTP state (hash, expiry, attempt count, IP)
```

### Interview Module Tables

```
interview_jobs         → Job postings (with base questions + MCQ config)
interview_candidates   → Applicants per job (with PII hashed fields)
interview_sessions     → Unique interview sessions (token-based access)
interview_questions    → Per-candidate generated questions (base + AI-generated)
interview_answers      → Audio answers with transcription + AI scores
interview_workflow_events → Full state machine audit trail
interview_candidate_documents → CV uploads for AI extraction
```

---

## 7. Role Hierarchy & Permissions

```
ADMIN ─────────────────────────── Full access to all 26 permissions
  │
  ├── AI ENGINEER ─────────────── Prompt tuning, grading config, system health
  │                                (no PII access, no HR data)
  │
  ├── OPS MANAGER ─────────────── ops.reports.view + notes.view
  │   └── (Cross-campaign read-only operational dashboards)
  │
  ├── HR MANAGER ──────────────── Global calls, HR dashboard, onboarding,
  │   │                            employee manage, exports, BI view
  │   └── (Full people-ops scope)
  │
  ├── QA ──────────────────────── Global calls (raw), HITL review,
  │   │                            data center, exports
  │   └── (Campaign-scoped by team assignment)
  │
  ├── TEAM MANAGER ────────────── Team Manager workspace
  │   │                            (multi-team, cross-campaign reporting)
  │   └── TEAM LEADER ──────────── Team Leader workspace
  │       │                         (single team, scoped calls + agents)
  │       └── AGENT ──────────────── Own dashboard, own calls,
  │                                   own profile, success library
  │
  └── RECRUITER ──────────────────── Interview module (jobs, candidates,
                                      evaluations, conversions)
```

Permission checks cascade via `require_permission(current_user, Permission.X)`. Team scoping is enforced at the service layer using `get_led_team_ids()` and `get_managed_team_ids()` helpers — agents outside a manager's scope are invisible even if the manager has the right role.

---

## 8. Module Breakdown

### 8.1 QA & Call Evaluation

The core module. Handles the full lifecycle from upload to scored result.

- **Call Upload:** `POST /api/calls/upload` — accepts audio file + metadata, creates `Call` record, dispatches Celery task
- **Score Override:** `PATCH /api/calls/{id}/score` — QA/Admin can override AI score with audit log
- **Golden Moments:** Calls with `is_golden_moment=True` are surfaced in the Success Library
- **QA Alarms:** Calls with `qa_alarm=True` are flagged in HR and Ops dashboards
- **Call Annotations:** Supervisors can add timestamped notes to specific call moments

### 8.2 Operations Reporting

Campaign-level operational intelligence for Ops Managers and Admins.

**6 Core KPIs tracked with period-over-period trending:**
1. `sales` — Successful outcome count (type-aware: Sale Closed / Resolved / Promise to Pay)
2. `revenue` — Sum of `call_outcome.outcome_value`
3. `conversion` — `sales / total_calls × 100`
4. `attendance` — `present_records / total_records × 100`
5. `qascore` — Average of `COALESCE(overridden_score, evaluation_score)`
6. `violations` — Count of `agent_violations` records

Each metric is compared against `operational_targets` and labeled: `on_target`, `warning`, or `critical`.

### 8.3 Team Management

Two scoped workspace levels:

**Team Leader** — sees only their assigned team:
- Team dashboard (KPIs, agent count, conversion)
- Agent list with individual scores
- Call list for their team's agents
- Pending role notes and transfer requests

**Team Manager** — sees all teams they manage:
- Aggregated multi-team dashboard
- Per-team breakdown
- Cross-team agent transfers
- Sales/revenue/conversion/attendance reports
- KPI threshold configuration

### 8.4 HR & Compliance

Handles people-operations beyond QA scoring:

- **Agent Violations:** Extracted by LLM per call. Each has `severity` (low/medium/high), `score_deduction`, and `hr_flagged` flag. HR can filter, export, and act on them.
- **Attendance Tracking:** Daily records with `scheduled_minutes`, `worked_minutes`, `late_minutes`.
- **Bulk Onboarding:** HR Manager can upload employee CSV for batch creation.
- **Role Notes:** Internal communication system — managers can send targeted notes to specific roles, teams, agents, or campaigns. Notes support threading, priority levels, and soft-delete with reason.
- **Agent Mastery Stats:** Computed scores per agent: `rapport_building`, `emotional_sync`, `ownership_trust`, `process_clarity`.

### 8.5 Interview Module

A self-contained pre-hire screening system:

```
Job Created (HR Manager)
  └── Questions configured (base + MCQ + AI-generated)
      └── Candidate Invited (unique session token URL via Cloudflare)
          └── Candidate records audio answers (browser mic)
              └── Answers transcribed + scored by AI Worker
                  └── Scores: relevance, fluency, grammar, overall
                      └── HR reviews → Accept / Reject / Archive
                          └── Accepted → Convert to Employee record
```

Public interview URLs are built dynamically using `FRONTEND_URL` or `PUBLIC_BASE_URL` setting, routed through Cloudflare Tunnel for external access.

### 8.6 System Monitoring

Admins get a real-time health dashboard with probes for all 8 services:

| Service | Probe Method |
|---|---|
| FastAPI Backend | Always operational if responding |
| PostgreSQL / SQLite | `SELECT 1` latency check |
| Redis Queue | `PING` + write probe (`SET health:check`) |
| Celery Workers | `celery.control.inspect().ping()` |
| ASR Worker (GPU) | Heartbeat key check `gpu:0:heartbeat` in Redis |
| RAG Worker (ChromaDB) | `collection.count()` call |
| Groq Inference | API key presence + format check |
| WebSocket Stream | Active connection count probe |

Disk usage, CPU load (via `psutil`), GPU utilization (via `pynvml`), and pipeline latency (avg of last 10 processed calls) are also reported.

---

## 9. Frontend Architecture

Built with **React 18 + TypeScript + Vite**. Uses a **role-aware routing** model where each role sees a different dashboard layout.

### Key Dependencies

| Library | Purpose |
|---|---|
| `@mui/material` + `@radix-ui/*` | Component library (hybrid) |
| `@tanstack/react-query` | Server state management + caching |
| `axios` | HTTP client with interceptors |
| `recharts` | Charts and data visualizations |
| `react-hook-form` | Form management + validation |
| `motion` (Framer Motion) | Animations |
| `react-dnd` | Drag-and-drop (team board) |
| `date-fns` | Date formatting |
| `sonner` | Toast notifications |
| `next-themes` | Dark/light mode |
| `react-router` v7 | Client-side routing |

### API Proxy

In development, Vite proxies all `/api/*` requests to `http://localhost:8000` and all `/ws/*` WebSocket connections to `ws://localhost:8000`, avoiding CORS issues.

### Role-Based Page Access

Each page checks `current_user.role` and `permissions[]` before rendering. Pages outside a user's permission set redirect to a 403 view. The permission set is fetched on login and cached in React Query.

---

## 10. Infrastructure & Deployment

### Docker Compose Services

```yaml
services:
  backend:      # FastAPI + uvicorn (port 8000)
  celery_asr:   # Celery worker — GPU queue (WhisperX)
  celery_cpu:   # Celery worker — CPU queue (Groq + RAG)
  redis:        # Redis 7 (broker + cache + heartbeat store)
  postgres:     # PostgreSQL 16 (primary database)
  frontend:     # Nginx serving Vite build (port 80/443)
  chromadb:     # ChromaDB server (port 8001)
```

### Cloudflare Tunnel

External access (for interview candidate portals and remote agents) is handled through **Cloudflare Tunnel** (`trycloudflare.com` or configured domain). The `ALLOWED_HOSTS` in Vite and FastAPI CORS settings include `.trycloudflare.com` for tunnel compatibility.

### Environment Configuration (`.env`)

```env
DATABASE_URL=postgresql://user:pass@postgres:5432/voiceqa
CELERY_BROKER_URL=redis://redis:6379/0
GROQ_API_KEY=gsk_...
SECRET_KEY=<JWT signing key>
FRONTEND_URL=https://your-domain.com
PUBLIC_BASE_URL=https://your-public-domain.com       # for interview portals
REQUIRE_PUBLIC_BASE_URL_FOR_INTERVIEWS=true
INTERVIEW_PORTAL_PATH=/interview-portal
```

### Production Constraints

- SQLite is **blocked** in production (must use PostgreSQL)
- `GROQ_API_KEY` must not start with `mock` in production
- Redis must accept write operations (not read-only mode)
- Auto table creation (`Base.metadata.create_all`) is **disabled** — Alembic migrations only

---

## 11. Security Model

### Authentication
- **bcrypt** password hashing
- **JWT** Bearer tokens (configurable expiry)
- **OTP email challenge** on every login (max 5 attempts, IP-logged)
- OTP stored as a **bcrypt hash** in `login_otp_challenges` — plaintext never persisted

### Authorization
- RBAC enforced at **endpoint level** via `require_permission()` dependency
- Team scope enforced at **service level** — managers cannot query outside their scope
- QA reviewers scoped to calls within their team assignments

### PII Protection
- Transcripts contain a `has_pii` flag per segment with `redacted_text` variant
- Export endpoints use `pii_redaction` middleware — raw PII only visible to `calls.view_raw` permission holders
- Export attempts are **audit-logged** (success and failure)
- National ID stored as a **bcrypt hash** + last 4 digits only

### Audit Trail
Every mutating action by a privileged user writes to `audit_events`:
```
actor_id | actor_email | action | target | before_state | after_state | reason | success
```

### 11.1 Protect Architecture Six-Phase Security Rollout

The Protect Architecture adds runtime access control around every sensitive path in the platform. It is designed as a feature-flagged rollout so the team can move from observation to enforcement without breaking active operations.

#### Protect Goals

- Enforce shift-based access for employees.
- Enforce one active server-side session per employee.
- Bind sessions to trusted browser devices.
- Revalidate access on protected HTTP requests.
- Revalidate access on WebSocket connections and live streams.
- Give admins auditable tools to manage shifts, sessions, and trusted devices.
- Keep sensitive security identifiers out of logs, UI, and audit metadata.

#### Control Plane And Data Plane

```
Frontend Browser
  -> device_id stored in localStorage
  -> login request includes device_id
  -> JWT stores sid, jti, and device_id_hash

FastAPI Auth Layer
  -> validates credentials and OTP
  -> checks shift, active session, and device policy
  -> creates UserSession
  -> returns JWT

Protected HTTP / WebSocket Layer
  -> decodes JWT
  -> validates server-side UserSession
  -> validates shift and trusted device
  -> touches last_seen_at
  -> writes safe audit events on denial

Admin Security Plane
  -> manages EmployeeShift records
  -> revokes UserSession records
  -> approves/revokes TrustedDevice records
  -> records admin reason and safe metadata in AuditEvent
```

#### Policy Modes

The rollout is controlled by `SECURITY_POLICY_MODE`.

| Mode | Behavior | Use Case |
|---|---|---|
| `off` | Legacy behavior remains allowed. Security checks return allow decisions. | Emergency rollback or initial deployment. |
| `audit` | Requests are allowed, but security warnings are recorded. | Measure impact before enforcement. |
| `enforce` | Security denials block login, HTTP requests, and WebSocket access. | Production protection. |

Related settings:

- `SECURITY_DEFAULT_TIMEZONE` defines the business timezone for shift checks. Default: `Africa/Cairo`.
- `SECURITY_SESSION_TTL_MINUTES` controls server-side session expiry.
- `SECURITY_WS_REVALIDATION_INTERVAL_SECONDS` controls mid-connection WebSocket revalidation frequency.

#### Phase 1 - Security Foundation

Phase 1 creates the backend foundation that every later phase depends on.

Implemented architecture:

- Add feature-flagged security settings in `app/config.py`.
- Add database models for:
  - `EmployeeShift`
  - `UserSession`
  - `TrustedDevice`
- Add Alembic migration for the security tables and indexes.
- Add `app/services/security_policy.py` as the central policy service.
- Keep policy functions deterministic and testable.
- Write audit events through the existing `AuditEvent` model.

Key responsibilities:

- Calculate whether the employee is inside an allowed shift.
- Hash browser device identifiers before storing or comparing them.
- Create and revoke server-side sessions.
- Evaluate whether another active session already exists.
- Generate safe audit metadata.

Sensitive values that must never be written to audit logs:

- Raw JWT
- Raw `sid`
- Raw `jti`
- Raw browser `device_id`
- Full `device_id_hash`
- Passwords
- OTP values

#### Phase 2 - Login, Session Issuance, And Logout Enforcement

Phase 2 moves authentication from stateless JWT-only access to JWT plus server-side session state.

Login flow:

```
POST /api/auth/login
  -> validate employee credentials
  -> validate or issue OTP challenge
  -> receive browser device_id
  -> evaluate shift policy
  -> evaluate single-active-session policy
  -> evaluate trusted-device policy
  -> create UserSession
  -> issue JWT with sid, jti, and device_id_hash
```

Device policy:

- The first device for an employee may be auto-enrolled.
- Later devices must be trusted before use when enforcement is enabled.
- Revoked devices cannot authenticate or keep protected access.

Session policy:

- One active session is allowed per employee.
- A second login is denied while another active session exists.
- Admin revocation or logout makes the session unusable.

Logout flow:

```
POST /api/auth/logout
  -> decode JWT claims
  -> find UserSession by employee_id + sid
  -> mark session inactive
  -> preserve revoked_at after repeated logout/revoke
  -> write safe SESSION_REVOKED audit event
```

#### Phase 3 - Protected HTTP Request Enforcement

Phase 3 applies Protect checks to authenticated HTTP endpoints after login.

Protected request flow:

```
Authorization: Bearer <JWT>
  -> validate JWT signature and employee status
  -> read sid, jti, and device_id_hash from token
  -> find matching UserSession
  -> ensure session is active and unexpired
  -> ensure token device hash matches session device hash
  -> ensure current shift is allowed
  -> ensure trusted device is still trusted
  -> update last_seen_at
  -> allow request
```

If enforcement denies access:

- `401 Unauthorized` is used for missing, invalid, revoked, or expired sessions.
- `403 Forbidden` is used for shift or trusted-device policy denial.
- A sanitized audit event is written.
- No raw token or raw security claims are exposed in the response.

Audit mode behavior:

- The request is allowed.
- Warning decisions are written to audit logs.
- The response contract remains unchanged.

#### Phase 4 - Admin Security Control Plane

Phase 4 exposes admin APIs for managing the security system.

Router:

- `app/routers/security_admin.py`
- Prefix: `/api/security-admin`
- Admin-only access.

Admin capabilities:

| Area | Endpoint Family | Purpose |
|---|---|---|
| Shifts | `/api/security-admin/shifts` | Create, list, update, and cancel employee shifts. |
| Sessions | `/api/security-admin/sessions` | List and revoke user sessions. |
| Devices | `/api/security-admin/devices` | List, rename, approve, and revoke trusted devices. |

Shift semantics:

- Each employee can have one shift per work date.
- Duplicate employee/date updates must be validated before commit.
- Cancelled or disabled shifts deny access when enforcement is enabled.
- Shift create/update/cancel actions write audit events.

Session revocation semantics:

- Repeating a session revoke returns `200 OK`.
- Repeating a revoke does not change the original `revoked_at`.
- Every admin revoke attempt writes a `SESSION_REVOKED` audit event.
- Audit metadata includes `session_id`, `employee_id`, `already_revoked`, and `reason`.

Device revocation semantics:

- Repeating a device revoke returns `200 OK`.
- Repeating a revoke does not change the original `revoked_at`.
- Every admin revoke attempt writes a `DEVICE_REVOKED` audit event.
- Device approval and revocation preserve the admin-provided reason.

#### Phase 5 - WebSocket Security Parity

Phase 5 brings WebSocket behavior in line with protected HTTP behavior.

Protected WebSocket endpoints:

- `/ws/calls/{call_id}`
- `/api/live/ws/live/{session_id}`

Connection-start validation:

```
WebSocket connect with auth_token
  -> validate JWT
  -> validate UserSession
  -> validate shift access
  -> validate trusted device
  -> touch last_seen_at
  -> accept connection
```

Mid-connection revalidation:

```
while socket is open:
  -> before processing message or audio chunk
  -> on configured timeout for silent sockets
  -> re-check session, shift, and device
  -> close if access is no longer valid
```

Close codes:

| Code | Meaning |
|---|---|
| `4401` | Authentication/session is missing, invalid, expired, or revoked. |
| `4403` | Authenticated user is denied by shift/device policy. |
| `1011` | Internal server error during security validation. |

Important guarantees:

- A revoked session cannot keep an open WebSocket alive past the revalidation interval.
- A revoked device cannot keep an open WebSocket alive past the revalidation interval.
- A cancelled or invalid shift closes already-open sockets.
- Denial audit events remain sanitized.

#### Phase 6 - Frontend Device Identity, Forced Logout, And Admin UI

Phase 6 makes the browser participate in the Protect Architecture and gives admins a usable security console.

Frontend device identity:

- `getOrCreateDeviceId()` stores a stable browser id in `localStorage`.
- Storage key: `call_rating_device_id`.
- Login and OTP verification send `device_id`.
- Logout and forced logout must not delete `call_rating_device_id`.
- The raw device id must not be logged or displayed.

Forced logout behavior:

```
Protected API returns security 401/403
  -> frontend detects session/device/shift denial
  -> auth state is cleared
  -> device id is preserved
  -> user is redirected to /login
  -> safe denial reason is shown
```

Frontend WebSocket handling:

- `4401` stops reconnect loops and logs the user out.
- `4403` stops reconnect loops and shows a security denial.
- `1011` shows a recoverable connection error.

Admin Security UI:

- Route: `/admin/security`
- Admin-only route guard.
- Sidebar entry visible only for admins.
- Tabs:
  - Shifts
  - Sessions
  - Trusted Devices

The UI uses the centralized security admin API client:

- `listSecurityShifts`
- `createSecurityShift`
- `updateSecurityShift`
- `deleteSecurityShift`
- `listSecuritySessions`
- `revokeSecuritySession`
- `listTrustedDevices`
- `approveTrustedDevice`
- `revokeTrustedDevice`

UI safety requirements:

- Display safe backend error details only.
- Do not display raw JWT, `sid`, `jti`, raw `device_id`, or full device hashes.
- Require admin reasons for destructive lifecycle actions.
- Treat repeated revoke `200 OK` responses as success.

#### End-To-End Security Invariants

The six phases are accepted only when these invariants hold:

- A user cannot access protected HTTP routes without a valid server-side session.
- A user cannot keep access after logout or admin session revocation.
- A revoked device cannot log in, use protected HTTP routes, or keep WebSocket access.
- A cancelled, disabled, missing, or out-of-window shift denies protected access.
- Admin actions remain auditable even when repeated.
- Audit metadata is useful but sanitized.
- Frontend forced logout preserves browser device identity.
- WebSocket behavior matches HTTP security behavior.

---

## 12. Database Migration History

Migrations are managed with **Alembic**. Below is the chronological schema evolution:

| Revision | Description |
|---|---|
| `460d2f36` | Initial setup: `employees`, `campaigns`, `calls`, `system_logs`, `audit_events` |
| `e3ab4a70` | Extend Employee: avatar, tier, skills, emotion_history |
| `b374524c` | Extend Call: talk times, tags, lead_status, golden_moment, emotion_timeline |
| `50f4eedc` | Add employee email (unique) |
| `26484e91` | Add auth fields: hashed_password, role ENUM |
| `33ab3b62` | Add system_log severity + resolved flag |
| `45936138` | Add speaker_map to Call model |
| `05668d85` | Add agent_mastery_stats table |
| `4765f94e` | Add HRMANAGER role + phone_number to Employee |
| `a7454af9` | Add call_outcomes table |
| `c42e9d75` | Intelligence Hub: coaching_sessions, call_annotations, call_qa_pairs, NLP/acoustic fields |
| `ea7ab85f` | (intermediary) |
| `497c670a` | Add agent_violations table |
| `9d3c5f7a` | Add audit_event success flag |
| `6f5e4d3c` | Add performance indexes across all high-traffic columns |
| `6ee8b606` | Bridge migration |
| `7ae8b506` | Add OPSMANAGER role |
| `f65b791a` | Add TEAMMANAGER role, teams table, employee_team_assignments |
| `f65b791b` | Add agent_transfer_requests table |
| `f65b791c` | Add role_notes table |
| `f65b791d` | Add TEAMLEADER role |
| `f65b791e` | Add kpi_threshold_configs table |
| `a65b791a` | KPI threshold config |
| `b12c7e9f` | DB-backed role permissions (app_permissions + role_permissions) |
| `c23d4e5f` | Complete role_notes schema (visibility, soft-delete) |
| `e92c3d4e` | (intermediary) |
| `d34e5f6a` | Add login_otp_challenges table + employee.otp_email field |
| `f13d9c4b` | Full Interview Module: jobs, candidates, sessions, questions, answers, workflow_events |

| `c3a07b8b4092` | Add Protect Architecture tables: `employee_shifts`, `trusted_devices`, `user_sessions` |

---

## 13. End-To-End Protect Architecture QA Checklist

This checklist defines the validation gates and E2E regression checks that prove the six-phase Protect Architecture works cohesively as one system.

### E2E Flow Coverage

1. **Happy Path Flow**:
   - Admin schedules a shift for an employee.
   - Employee logs in using credentials and a `device_id`.
   - The first login auto-enrolls and auto-approves the device.
   - Server-side session (`UserSession`) is successfully created and tracks session identifiers (`sid`, `jti`) and the hashed device ID.
   - Protected HTTP routes authorize the session token.
   - WebSocket connections authorize the session token and sustain traffic.
   - Logging out revokes the session in the database.
   - Protected routes and WebSockets immediately reject requests with revoked tokens.

2. **Active Session Concurrency Control**:
   - An active session blocks a subsequent login attempt (fails with `ACTIVE_SESSION_EXISTS`).
   - Admins can revoke the active session via `/api/security-admin/sessions/{session_id}/revoke`.
   - Admin session revocation yields `200 OK` and persists a sanitized `SESSION_REVOKED` audit event.
   - Login succeeds again after revocation.

3. **Trusted Device Lifecycle**:
   - A revoked device immediately denies access to protected HTTP endpoints (fails with `DEVICE_NOT_TRUSTED`).
   - Active WebSockets revalidate and close automatically with code `4403`.
   - New login attempts from the revoked device are rejected.
   - Admins can re-approve the device, which immediately restores authentication.

4. **Shift Enforcement & Attendance**:
   - Out-of-shift logins and protected requests are blocked.
   - Cancelling or disabling an active shift via the Admin Security plane immediately restricts HTTP endpoints (fails with `SHIFT_NOT_ALLOWED`) and closes WebSockets (with code `4403`).
   - Scheduling a new shift or enabling the shift restores access.

5. **Log and Metadata Sanitization**:
   - All audit logs, response payloads, and administrative UI tables are strictly sanitized.
   - No raw tokens (`JWT`), server-side identifiers (`sid`, `jti`), raw browser `device_id`, full `device_id_hash`, passwords, or OTPs are written or displayed.

---

## 14. Protect Architecture Production Rollout

> **Full Runbook**: [docs/protect_rollout_runbook.md](docs/protect_rollout_runbook.md)

This section summarizes the production rollout process for the Protect Architecture. The detailed runbook contains SQL queries, admin console instructions, and step-by-step verification procedures.

### 14.1 Rollout Stages

The rollout follows a strict six-stage sequence. **Never skip directly to `enforce` mode.**

| Stage | Mode | Purpose |
|-------|------|---------|
| 0 | `off` | Deploy codebase. Verify zero regressions. |
| 1 | `audit` | Enable policy evaluation. Log violations without blocking users. |
| 2 | — | Review audit logs. Identify employees missing shifts/devices. |
| 3 | — | Fix data: schedule shifts, approve devices, clear stale sessions. |
| 4 | `enforce` | Block policy violations. Monitor closely for 1–2 hours. |
| 5 | — | Ongoing monitoring of denials, forced logouts, WebSocket closes. |
| 6 | `audit` / `off` | Roll back if enforcement causes disruption. |

### 14.2 Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `SECURITY_POLICY_MODE` | `off` · `audit` · `enforce` | `off` | Master switch for the security policy engine |
| `SECURITY_TIMEZONE` | IANA timezone | `Africa/Cairo` | Timezone for shift window calculations |
| `DEFAULT_SHIFT_GRACE_BEFORE_MINUTES` | `0`–`240` | `10` | Early clock-in grace period |
| `DEFAULT_SHIFT_GRACE_AFTER_MINUTES` | `0`–`240` | `10` | Late clock-out grace period |
| `SECURITY_WS_REVALIDATION_INTERVAL_SECONDS` | `≥ 0` | `15` | WebSocket mid-connection revalidation interval |

### 14.3 Pre-Enforcement Go/No-Go Checklist

Before setting `SECURITY_POLICY_MODE=enforce`:

- [ ] Every active employee has a valid shift for today
- [ ] First devices are enrolled or approved for active employees
- [ ] No stale active sessions block new logins
- [ ] Admin Security UI is accessible at `/admin/security`
- [ ] Admin can revoke sessions and devices from the console
- [ ] Frontend login sends `device_id` in login and OTP payloads
- [ ] WebSocket security validation passes for valid sessions
- [ ] Audit logs contain no raw `sid`, `jti`, JWT, `device_id`, or full `device_id_hash`
- [ ] All backend E2E tests pass: `python -m pytest tests/test_security_e2e_flow.py -v`
- [ ] All frontend E2E tests pass: `npx vitest run src/app/__tests__/securityE2E.test.tsx`
- [ ] Full backend security regression passes: `python -m pytest -k "security" -v`
- [ ] Frontend production build compiles: `npx vite build`

### 14.4 Monitoring Targets

After enabling `audit` or `enforce` mode, monitor these signals:

| Signal | Source | Indicates |
|--------|--------|-----------|
| `SECURITY_POLICY_AUDIT` audit events | `audit_events` table | Audit-only policy violations observed during rollout |
| `SECURITY_POLICY_DENIAL` audit events | `audit_events` table | Policy violations actively blocked in enforce mode |
| `SESSION_REVOKED` audit events | `audit_events` table | Admin or logout session revocations |
| `DEVICE_REVOKED` audit events | `audit_events` table | Admin device revocations |
| `SHIFT_CANCEL` audit events | `audit_events` table | Admin shift cancellations |
| Repeated forced logouts per employee | `audit_events` table | Misconfigured shifts/devices for specific employees |
| `WEBSOCKET_SECURITY_CLOSE` with code `4401` | `audit_events` table and infrastructure logs | Session invalid, expired, revoked, or missing auth |
| `WEBSOCKET_SECURITY_CLOSE` with code `4403` | `audit_events` table and infrastructure logs | Device untrusted, shift expired, or access denied |
| `WEBSOCKET_SECURITY_CLOSE` with code `1011` | `audit_events` table when persistence succeeds, plus infrastructure logs | Internal revalidation failure (DB issue) |

### 14.5 Rollback Procedure

**Standard rollback** (enforcement issues):

1. Set `SECURITY_POLICY_MODE=audit`
2. Restart the backend
3. Confirm users can log in
4. Review audit logs for denial root causes
5. Fix shifts / devices / sessions data
6. Re-enable `enforce` after validation

**Emergency rollback** (system instability):

1. Set `SECURITY_POLICY_MODE=off`
2. Restart the backend immediately
3. Investigate root cause before re-enabling `audit`

### 14.6 Post-Rollout Validation

After enabling `enforce`, verify these behaviors:

1. Agent login succeeds during valid shift with trusted device
2. Duplicate active session login is denied (`409`)
3. Revoked session cannot access `/api/auth/me` (`401`)
4. Revoked device cannot access protected routes (`403`)
5. Cancelled shift blocks login and protected routes
6. WebSocket closes with `4401` after session revoke
7. WebSocket closes with `4403` after device revoke or shift cancel
8. Frontend forced logout message does not contain raw secrets
9. Admin repeated revoke is idempotent and writes an audit event

---

*Last updated: June 2026*
