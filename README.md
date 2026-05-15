<p align="center">
  <h1 align="center">Event-AI</h1>
  <p align="center">AI-powered event planning marketplace for Pakistan</p>
  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white" alt="Python 3.13" />
    <img src="https://img.shields.io/badge/FastAPI-0.135-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/Next.js-16-black?logo=next.js&logoColor=white" alt="Next.js 16" />
    <img src="https://img.shields.io/badge/PostgreSQL-pgvector-336791?logo=postgresql&logoColor=white" alt="PostgreSQL" />
    <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker" />
    <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License" />
  </p>
</p>

---

## Overview

Event-AI is a full-stack, AI-native marketplace that connects clients with verified vendors for weddings, mehndi, baraat, walima, corporate events, conferences, birthdays, and parties across Pakistan.

The platform combines a production-grade REST API, three Next.js portals, and a multi-agent AI orchestrator into a single Turborepo monorepo. AI agents handle event planning, vendor discovery, and booking coordination — all backed by semantic search via pgvector, real-time SSE notifications, and a 7-layer prompt injection firewall.

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Status](#project-status)
- [Getting Started](#getting-started)
  - [Docker (recommended)](#option-a-docker-recommended)
  - [Native development](#option-b-native-development)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [AI Agent System](#ai-agent-system)
- [Database Migrations](#database-migrations)
- [Testing](#testing)
- [Key Commands](#key-commands)
- [Google OAuth Setup](#google-oauth-setup)
- [Windows Support](#windows-support)
- [Contributing](#contributing)

---

## Architecture

```
Event-AI/
├── packages/
│   ├── backend/                     # FastAPI REST API — auth, bookings, events, payments
│   ├── vendor/                      # Vendor portal (Next.js) — onboarding, services, bookings
│   ├── user/                        # User portal (Next.js) — AI planning, vendor discovery
│   ├── admin/                       # Admin portal (Next.js) — moderation, analytics
│   ├── agentic_event_orchestrator/  # AI service — agents, RAG, MCP tools, SSE streaming
│   └── ui/                          # Shared design system and component library
├── docker-compose.yml               # Full-stack container orchestration
├── turbo.json                       # Turborepo pipeline config
└── pnpm-workspace.yaml              # pnpm workspace definition
```

### Service Port Map

| Service | Dev Port | Docker Port |
|---------|----------|-------------|
| Backend API | 5000 | 5000 |
| AI Orchestrator | 8000 | 8000 |
| Vendor portal | 3002 | 3002 → 3000 |
| User portal | 3003 | 3003 → 3000 |
| Admin portal | 3004 | 3004 → 3000 |

### Agent Pipeline

```
User request (HTTP / SSE)
        ↓
   TriageAgent              ← sole entry point; classifies intent
        ↓
   EventPlannerAgent  ←→   VendorDiscoveryAgent
                                  ↓
                            BookingAgent
                                  ↓
                            OrchestratorAgent    ← multi-step coordination
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend API** | Python 3.13 · FastAPI · SQLModel · asyncpg · Alembic · Structlog |
| **Database** | Neon Serverless PostgreSQL · pgvector (768-dim embeddings) |
| **Authentication** | Custom JWT (HS256) · Google OAuth2 · bcrypt · httpOnly cookies |
| **Frontend** | Next.js 16 · TypeScript (strict) · Tailwind CSS · shadcn/ui · React Query |
| **AI / Agents** | OpenAI Agents SDK · Gemini via LiteLLM · Mem0 · SSE streaming |
| **Search** | pgvector cosine similarity · trigram · hybrid (30/70 weighted) |
| **Security** | 7-layer injection firewall · canary tokens · output leak detection |
| **Tooling** | Turborepo · pnpm workspaces · uv · Docker · GitHub Actions |

---

## Project Status

| Phase | Module | Status |
|-------|--------|--------|
| 1 | Database & Migrations | ✅ Complete |
| 1 | JWT Auth + Google OAuth | ✅ Complete |
| 2 | Vendor Marketplace | ✅ Complete |
| 2 | Event Management | ✅ Complete |
| 3 | Booking System | ✅ Complete |
| 3 | Real-Time SSE Notifications | ✅ Complete |
| 4 | RAG & Semantic Search | ✅ Complete |
| 4 | AI Agent Chat | ✅ Complete |
| 4 | Admin Dashboard | ✅ Complete |
| 5 | AI Security Hardening | 🔄 In Progress |
| 5 | Notification System Polish | 🔄 In Progress |

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — for the Docker path
- [Node.js 20+](https://nodejs.org/) + [pnpm](https://pnpm.io/) — for native Node development
- [uv](https://docs.astral.sh/uv/) — for native Python development
- A [Neon](https://neon.tech/) PostgreSQL database (or local PostgreSQL with pgvector)
- A [Google Cloud Console](https://console.cloud.google.com/) project for OAuth2

---

### Option A: Docker (recommended)

The fastest way to run the full stack on any OS — Linux, macOS, or Windows.

**1. Clone and configure**

```bash
git clone https://github.com/your-org/event-ai.git
cd event-ai
cp .env.example .env
# Edit .env — fill in DATABASE_URL, JWT_SECRET_KEY, GEMINI_API_KEY at minimum
```

**2. Start all services**

```bash
docker compose up --build
```

All five services start in dependency order. The backend health check gates the other services — allow ~30 seconds on first boot.

| URL | Service |
|-----|---------|
| http://localhost:5000/docs | Backend API (Swagger UI) |
| http://localhost:8000/docs | AI Orchestrator (Swagger UI) |
| http://localhost:3002 | Vendor portal |
| http://localhost:3003 | User portal |
| http://localhost:3004 | Admin portal |

**3. Stop**

```bash
docker compose down
```

---

### Option B: Native Development

**1. Install dependencies**

```bash
pnpm install
cd packages/backend && uv sync && cd ../..
cd packages/agentic_event_orchestrator && uv sync && cd ../..
```

**2. Configure environment**

```bash
cp .env.example .env
# Fill in DATABASE_URL, JWT_SECRET_KEY, GEMINI_API_KEY, and other required values
```

**3. Run database migrations**

```bash
# Requires a running PostgreSQL instance with pgvector enabled
# Enable pgvector first (run once):
#   CREATE EXTENSION IF NOT EXISTS vector;

cd packages/backend
uv run alembic upgrade head
cd ../..
```

**4. Start services**

Open separate terminals for each service, or use the combined dev command:

```bash
# All Node portals at once (via Turborepo)
pnpm dev

# Backend (separate terminal — from packages/backend/)
uv run uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload

# AI orchestrator (separate terminal — from packages/agentic_event_orchestrator/)
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Or start portals individually:

```bash
pnpm dev:vendor    # → http://localhost:3002
pnpm dev:user      # → http://localhost:3003
pnpm dev:admin     # → http://localhost:3004
```

---

## Environment Variables

Copy `.env.example` to `.env` at the repo root and fill in the values below.

### Required

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Neon pooled connection string (runtime) |
| `DIRECT_URL` | Neon direct connection string (Alembic migrations only) |
| `JWT_SECRET_KEY` | Min 32-char random secret — `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `GEMINI_API_KEY` | Google AI Studio API key (embeddings + agent model) |
| `GOOGLE_CLIENT_ID` | Google OAuth2 client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth2 client secret |

### Optional but recommended

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_SERVICE_API_KEY` | — | Service-to-service auth token (backend ↔ orchestrator) |
| `MEM0_API_KEY` | — | Mem0 persistent memory for AI agents |
| `SMTP_HOST` | — | SMTP relay for email notifications |
| `S3_ENDPOINT` | — | S3-compatible CDN for file uploads (e.g. Cloudflare R2) |

See `.env.example` for the full list with descriptions.

---

## API Reference

All endpoints follow a standard response envelope:

```json
{ "success": true,  "data": { ... }, "meta": {} }
{ "success": false, "error": { "code": "ERROR_CODE", "message": "Human-readable message" } }
```

**Base URL:** `http://localhost:5000/api/v1`  
**Interactive docs:** `http://localhost:5000/docs`

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/register` | — | Register with email + password |
| `POST` | `/auth/login` | — | Form-encoded login → JWT pair |
| `POST` | `/users/login` | — | JSON login (portal use) |
| `GET`  | `/auth/me` | ✅ | Authenticated user profile |
| `POST` | `/auth/refresh` | — | Rotate refresh token |
| `POST` | `/auth/logout` | ✅ | Revoke refresh token |
| `POST` | `/auth/password-reset-request` | — | Request password reset |
| `POST` | `/auth/password-reset-confirm` | — | Confirm new password |
| `GET`  | `/auth/google` | — | Initiate Google OAuth2 |
| `GET`  | `/auth/google/callback` | — | Google OAuth2 callback |

### Vendors

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/vendors/register` | ✅ | Register as vendor (triggers approval flow) |
| `GET`  | `/vendors/profile/me` | ✅ | Own vendor profile |
| `PUT`  | `/vendors/profile/me` | ✅ | Update vendor profile |
| `GET`  | `/vendors/me/bookings` | ✅ | Vendor's booking list |
| `PATCH`| `/vendors/me/bookings/{id}/status` | ✅ | Confirm or reject booking |
| `GET`  | `/public_vendors/` | — | Keyword search (trigram + ILIKE) |
| `GET`  | `/public_vendors/semantic` | — | Vector similarity search |
| `GET`  | `/public_vendors/search` | — | Unified search (`?mode=keyword\|semantic\|hybrid`) |
| `GET`  | `/public_vendors/{id}` | — | Public vendor profile |
| `GET`  | `/categories/` | — | Event categories |

### Events

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/events/` | ✅ | Create event |
| `GET`  | `/events/` | ✅ | List own events (paginated) |
| `GET`  | `/events/{id}` | ✅ | Single event |
| `PUT`  | `/events/{id}` | ✅ | Update event |
| `DELETE`| `/events/{id}` | ✅ | Cancel event |
| `PATCH`| `/events/{id}/status` | ✅ | Explicit status transition |
| `POST` | `/events/{id}/duplicate` | ✅ | Clone event as draft |

**Status machine:** `draft → planned → active → completed`, any → `cancelled`

### Bookings

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/bookings/` | ✅ | Create booking (atomic slot lock) |
| `GET`  | `/bookings/` | ✅ | List own bookings (paginated) |
| `GET`  | `/bookings/{id}` | ✅ | Single booking |
| `PATCH`| `/bookings/{id}/status` | ✅ | Status transition |
| `PATCH`| `/bookings/{id}/cancel` | ✅ | Cancel + release slot |
| `GET`  | `/bookings/availability` | ✅ | Check vendor/service/date availability |
| `POST` | `/bookings/{id}/messages` | ✅ | Send booking message |
| `GET`  | `/bookings/{id}/messages` | ✅ | List booking messages |

**Status machine:** `pending → confirmed | rejected | cancelled` → `in_progress` → `completed | no_show`

### Notifications & SSE

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET`  | `/notifications/` | ✅ | List notifications (paginated) |
| `GET`  | `/notifications/unread-count` | ✅ | Unread count |
| `PATCH`| `/notifications/read-all` | ✅ | Mark all as read |
| `PATCH`| `/notifications/{id}/read` | ✅ | Mark single as read |
| `DELETE`| `/notifications/{id}` | ✅ | Delete notification |
| `GET`  | `/sse/stream` | ✅ | Real-time SSE event stream |

### Admin

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET`  | `/admin/stats` | ✅ Admin | Platform stats |
| `GET`  | `/admin/vendors` | ✅ Admin | Vendor list with filters |
| `PATCH`| `/admin/vendors/{id}/status` | ✅ Admin | Approve / reject / suspend |
| `GET`  | `/admin/users` | ✅ Admin | User list with filters |
| `POST` | `/admin/embeddings/backfill` | ✅ Admin | Trigger embedding backfill |
| `GET`  | `/admin/chat/sessions` | ✅ Admin | AI chat session log |
| `GET`  | `/admin/chat/feedback/stats` | ✅ Admin | Agent feedback stats |

### AI Orchestrator (port 8000)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/ai/chat` | ✅ | Non-streaming chat |
| `POST` | `/api/v1/ai/chat/stream` | ✅ | SSE token-by-token streaming |
| `POST` | `/api/v1/ai/feedback` | ✅ | Thumbs up/down per message |
| `DELETE`| `/api/v1/ai/memory/{user_id}` | ✅ Admin | GDPR right-to-forget |

---

## AI Agent System

### Security Stack (7 layers)

| Layer | Mechanism |
|-------|-----------|
| 1 | YAML blocklist — exact match |
| 2 | Regex patterns — 6 threat categories (DIRECT_INJECTION, SYSTEM_PROMPT_EXTRACTION, ROLE_ESCALATION, INDIRECT_INJECTION, CONTEXT_OVERFLOW, TOOL_ABUSE) |
| 3 | Heuristics — char density, token repetition, homoglyphs, zero-width chars |
| 4 | Sandwich defense — canary token injection + MINJA protection on history turns |
| 5 | OutputLeakDetector — canary token + stack trace + internal tool name detection |
| 6 | SDK-native guardrails — `@input_guardrail` (blocking) + `@output_guardrail` |
| 7 | Mem0 — per-user persistent memory with GDPR delete support |

### Semantic Search

Vendor profiles are embedded with Gemini `text-embedding-004` (768 dimensions) stored in pgvector. Embeddings are created on vendor approval and deleted on rejection or suspension.

| Search Mode | Description |
|-------------|-------------|
| `keyword` | Trigram + ILIKE — no embedding required |
| `semantic` | pgvector cosine similarity via Gemini embeddings |
| `hybrid` | 30% trigram + 70% semantic (default) |

```bash
# Trigger embedding backfill for all active vendors
curl -X POST http://localhost:5000/api/v1/admin/embeddings/backfill \
  -H "Authorization: Bearer <admin_token>"
```

---

## Database Migrations

All migrations live in `packages/backend/alembic/versions/`. Always use `DIRECT_URL` (not the pooler) for Alembic.

```bash
# From packages/backend/

# Apply all pending migrations
uv run alembic upgrade head

# Create a new migration (after changing a SQLModel)
uv run alembic revision --autogenerate -m "add_vendor_rating_column"

# Rollback one step
uv run alembic downgrade -1

# View history
uv run alembic history --verbose

# Check current revision
uv run alembic current
```

> **First-time setup:** pgvector must be enabled before the first migration:
> ```sql
> CREATE EXTENSION IF NOT EXISTS vector;
> ```

---

## Testing

```bash
# From packages/backend/

# Run all tests
uv run pytest

# Run a specific file
uv run pytest tests/test_booking_routes.py -v

# Run by name pattern
uv run pytest -k "test_semantic" -v

# With coverage report
uv run pytest --cov=src --cov-report=term-missing

# Docker structural assertion tests (from repo root)
# Requires: pytest + pyyaml in a venv
uv run --with pytest --with pyyaml pytest tests/docker/ -v
```

Tests use `sqlite+aiosqlite:///:memory:` — no Neon, no Docker required for the backend test suite.

---

## Key Commands

```bash
# ── Setup ─────────────────────────────────────────────────
pnpm install                          # install all Node dependencies
cd packages/backend && uv sync        # install Python backend deps
cd packages/agentic_event_orchestrator && uv sync  # install AI service deps

# ── Development ───────────────────────────────────────────
pnpm dev                              # all Node portals (Turborepo)
pnpm dev:vendor                       # vendor portal → :3002
pnpm dev:user                         # user portal   → :3003
pnpm dev:admin                        # admin portal  → :3004

# ── Database ──────────────────────────────────────────────
pnpm db:up                            # start Postgres (Docker)
pnpm db:down                          # stop Postgres
pnpm db:migrate                       # apply migrations (production)
pnpm db:migrate:dev                   # apply migrations (dev)
pnpm db:reset                         # wipe and reseed local DB

# ── Docker ────────────────────────────────────────────────
docker compose up --build             # build and start all 5 services
docker compose up --build backend     # single service
docker compose down                   # stop all services
docker compose logs -f backend        # tail logs

# ── Code Quality ──────────────────────────────────────────
pnpm lint                             # lint all packages
pnpm format                           # format with Prettier
pnpm typecheck                        # TypeScript type check
cd packages/backend && uv run pytest  # Python tests
```

---

## Google OAuth Setup

1. Open [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Credentials**
2. Create an **OAuth 2.0 Client ID** (type: Web application)
3. Add **Authorized redirect URI:** `http://localhost:5000/api/v1/auth/google/callback`
4. Add **Authorized JavaScript origins:** `http://localhost:5000`, `http://localhost:3003`, `http://localhost:3002`
5. Copy **Client ID** and **Client Secret** into your `.env`

> The redirect URI must match exactly — trailing slash matters.

---

## Windows Support

The full stack runs on Windows via **Docker Desktop** (recommended) or **WSL2**.

```powershell
# Windows — Docker Desktop required
docker compose up --build
```

For native Windows development or detailed WSL2 setup, see [README-WINDOWS.md](README-WINDOWS.md).

---

## Contributing

### Branch naming

```
feature/<name>    # new features
fix/<name>        # bug fixes
hotfix/<name>     # urgent production fixes
```

### Commit convention ([Conventional Commits](https://www.conventionalcommits.org/))

```
feat(backend): add semantic search endpoint
fix(auth): handle expired Google OAuth state token
test(events): add duplicate event integration tests
chore(infra): update Docker base images to slim variants
```

### Rules

- PRs target `develop`, never `main` directly
- All CI checks must pass: `pnpm lint`, `pnpm typecheck`, `uv run pytest`
- **Package managers:** `uv` for Python, `pnpm` for Node — never `pip` or `npm`
- **Auth:** all routes use `Depends(get_current_user)` — no custom auth logic in routes
- **Tests:** written alongside implementation — zero real LLM or MCP calls in tests
- **Secrets:** never committed — `.env` is in `.gitignore`

---

## License

MIT © Event-AI Contributors
