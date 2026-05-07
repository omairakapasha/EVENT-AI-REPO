# AGENTS.md

> **Supreme authority:** `.specify/memory/constitution.md` overrides everything, including this file.

---

## Project Overview

**Event-AI** is an AI-powered event planning marketplace for Pakistan. It centralises vendor discovery, booking coordination, payment processing, and AI-assisted orchestration into one unified, event-driven platform.

**Core product areas:**

| Package | Purpose |
|---|---|
| `packages/user` | User portal — AI planning, bookings, vendor discovery |
| `packages/vendor` | Vendor portal — onboarding, service management, bookings |
| `packages/admin` | Admin portal — moderation, approvals, analytics |
| `packages/backend` | REST API — auth, bookings, events, payments, business logic |
| `packages/agentic_event_orchestrator` | AI service — agents, Agentic RAG, MCP tools |
| `packages/ui` | Shared design system and reusable components |

---

## Technology Stack

### Monorepo & Tooling
- Turborepo + pnpm workspaces
- Docker (development only)
- GitHub Actions CI/CD
- Conventional Commits

### Backend (`packages/backend`)
- Python 3.12+, FastAPI, SQLModel
- PostgreSQL via Neon + pgvector
- asyncpg, Pydantic, Structlog
- Custom JWT authentication (`middleware/auth.middleware.py`)
- Package manager: **uv**

### Authentication (Non-Negotiable)
- Custom auth only via `src/middleware/auth.middleware.py`
- Dependency: `get_current_user` / `get_current_user_optional`
- JWT in `Authorization: Bearer <token>` header
- **Banned:** NextAuth, Auth0, Clerk, Firebase Auth, localStorage JWT, sessionStorage JWT

### AI Layer (`packages/agentic_event_orchestrator`)
- FastAPI + OpenAI Agents SDK
- Gemini via LiteLLM (`gemini/gemini-3-flash-preview`)
- LangChain — **Agentic RAG only** (never for orchestration)
- Mem0 (per-user persistent memory), MCP Protocol, SSE / sse-starlette

### Frontend (all portals)
- Next.js 15, TypeScript (strict), Tailwind CSS, shadcn/ui, React Query

### Testing
- Python: pytest, pytest-asyncio, httpx, respx
- JS: Jest, React Testing Library

---

## Directory Structure

```
Event-AI/
│
├── packages/
│   ├── backend/
│   │   ├── src/
│   │   │   ├── models/          # SQLModel DB entities (source of truth)
│   │   │   ├── schemas/         # Pydantic request/response models
│   │   │   ├── services/        # Business logic (singleton classes)
│   │   │   ├── db/
│   │   │   │   └── session.py   # Async DB engine/session
│   │   │   ├── middleware/
│   │   │   │   └── auth.middleware.py  # ← Canonical auth (do not bypass)
│   │   │   ├── api/v1/          # /api/v1/ route handlers
│   │   │   └── config/          # Settings, database lifespan
│   │   ├── alembic/
│   │   │   └── versions/        # Only migration location
│   │   ├── scripts/             # seed.py, reset_db.py, backfill_*.py
│   │   └── tests/               # conftest.py + test_*.py files
│   │
│   ├── agentic_event_orchestrator/
│   │   ├── pipeline/            # TriageAgent + specialist agents
│   │   ├── routers/             # chat, feedback, memory, admin_chat
│   │   ├── services/            # guardrail_service, sse_manager, etc.
│   │   ├── tools/               # @function_tool definitions
│   │   ├── config/settings.py   # Pydantic BaseSettings + @lru_cache
│   │   └── main.py              # FastAPI lifespan + app factory
│   │
│   ├── user/src/
│   │   └── lib/api.ts           # Axios instance + all API helpers
│   ├── frontend/                # Vendor portal
│   ├── admin/                   # Admin portal
│   └── ui/                      # Shared UI library
│
├── docker-compose.yml
├── turbo.json
├── pnpm-workspace.yaml
├── .specify/memory/constitution.md   # Supreme engineering authority
└── README.md
```

### Database organisation rules
- `src/models/` = sole source of truth for schema
- `alembic/versions/` = only place migrations live
- `scripts/` = operational scripts only — never mix schema changes with seed data
- Every schema change requires a reversible Alembic migration

---

## Coding Conventions

### General
- **pnpm** for Node; **uv** for Python — never `npm` or `pip`
- TDD mandatory — write tests before or alongside implementation
- Flat architecture; smallest safe change first
- `constitution.md` overrides README when they conflict

### Python
- Full type hints on all functions; prefer `async def`
- Format and lint with **Ruff**
- **SQLModel** for all DB models; **Pydantic** for all structured data
- Dependency injection via `Depends()`; lifespan via `@asynccontextmanager`
- **Banned:** `sys.path.insert`, `nest_asyncio`, raw `os.environ`

### TypeScript
- Strict mode — no `any`
- PascalCase components, camelCase functions, kebab-case filenames

### Authentication (non-negotiable)
- All auth through `src/middleware/auth.middleware.py` — no exceptions
- Protected routes use `Depends(get_current_user)` or `Depends(get_current_user_optional)`
- **Banned:** NextAuth, Auth0, Clerk, Firebase Auth, localStorage JWT, sessionStorage JWT, route-level custom auth

### AI / Agentic layer
- `TriageAgent` is the sole entry point for all agent interactions
- All external actions wrapped in `@function_tool` with a docstring
- MCP tools are **read-only**; writes go through the backend REST API
- LangChain used **only** for Agentic RAG pipelines
- OpenAI Agents SDK used **only** for orchestration
- Require user confirmation before any destructive agent action

---

## Key Commands

```bash
# Install
pnpm install
cd packages/backend && uv sync
cd packages/agentic_event_orchestrator && uv sync

# Dev servers
pnpm dev              # all packages
pnpm dev:backend      # FastAPI backend only
pnpm dev:user         # User portal
pnpm dev:frontend     # Vendor portal
pnpm dev:admin        # Admin portal

# Database lifecycle
pnpm db:up            # start Postgres (Docker)
pnpm db:down          # stop Postgres
pnpm db:migrate       # apply migrations (production)
pnpm db:migrate:dev   # apply migrations (dev)
pnpm db:studio        # open DB GUI
pnpm db:reset         # wipe and reseed local DB

# Code quality
pnpm lint
pnpm format
pnpm typecheck
cd packages/backend && uv run pytest

# Alembic (always from packages/backend)
uv run alembic revision --autogenerate -m "describe_change"
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic current
```

### Port map
| Service | Port |
|---|---|
| Backend API | 5000 |
| User portal | 3003 (dev) / 3000 (Docker) |
| Vendor portal | 3002 (dev) / 3001 (Docker) |
| Admin portal | 3004 |
| AI orchestrator | 8000 |

### Branching
```
feature/<name>   →   develop   →   main
hotfix/<name>    →   develop   →   main
```

---

## API Conventions

### Base URL & versioning
All backend routes: `/api/v1/<resource>`. No route is registered without this prefix.

### Standard response envelope
```json
{ "success": true,  "data": { ... }, "meta": {} }
{ "success": false, "error": { "code": "ERROR_CODE", "message": "..." } }
```

### Error code taxonomy
| HTTP | Code | When |
|---|---|---|
| 401 | `AUTH_UNAUTHORIZED` | Missing or invalid token |
| 403 | `AUTH_FORBIDDEN` | Authenticated but not permitted |
| 404 | `NOT_FOUND` | Resource not found |
| 409 | `CONFLICT` | State conflict (already booked, duplicate, etc.) |
| 422 | `VALIDATION_ERROR` | Bad request body / params |
| 429 | `AUTH_RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Unhandled server error |

Domain-specific codes are namespaced: `NOT_FOUND_VENDOR`, `CONFLICT_DATE_UNAVAILABLE`, `VALIDATION_PAST_DATE`.

### Route inventory
| Prefix | Purpose |
|---|---|
| `/api/v1/auth` | Register, login, refresh, logout, password reset, Google OAuth |
| `/api/v1/users` | User profile management |
| `/api/v1/vendors` | Vendor CRUD, services, availability |
| `/api/v1/public_vendors` | Public vendor discovery — keyword, semantic, hybrid search (no auth) |
| `/api/v1/bookings` | Booking lifecycle |
| `/api/v1/events` | Event management |
| `/api/v1/services` | Vendor services |
| `/api/v1/categories` | Service categories |
| `/api/v1/inquiries` | Vendor inquiries |
| `/api/v1/uploads` | CDN file uploads |
| `/api/v1/notifications` | User notifications + per-user preferences |
| `/api/v1/sse` | Server-sent events stream |
| `/api/v1/admin/stats` | Platform stats (users, vendors, bookings, revenue) |
| `/api/v1/admin/vendors` | Vendor moderation — list, approve, reject, suspend |
| `/api/v1/admin/users` | User management — list with role/search filters |
| `/api/v1/admin/embeddings` | Trigger background embedding backfill |
| `/api/v1/admin/chat/*` | AI chat session logs, message history, feedback stats |

---

## Data Models

All models in `packages/backend/src/models/`. Pattern: `Base` → `table=True` class → `Create`/`Read` Pydantic classes.

**`users`:** `id` (UUID PK), `email` (unique), `password_hash`, `first_name`, `last_name`, `role` (`user`|`vendor`|`admin`), `is_active`, `email_verified`, `failed_login_attempts`, `locked_until`

**`vendors`:** `id`, `user_id` (FK→users, unique 1:1), `business_name`, `contact_email`, `city`, `region`, `status` (`PENDING`|`ACTIVE`|`SUSPENDED`|`REJECTED`), `rating`, `total_reviews`

**`services`:** `id`, `vendor_id` (FK→vendors), `name`, `price_min`, `price_max`, `capacity`, `is_active`

**`bookings`:** `id`, `user_id`, `vendor_id`, `service_id`, `event_date` (must be future), `status` (see state machine), `payment_status` (`pending`|`partial`|`paid`|`refunded`|`failed`), `unit_price`, `total_price`, `currency` (default `USD`), `event_location` (JSONB)

**`events`:** `id`, `user_id`, `event_type_id`, `name`, `start_date`, `end_date`, `timezone` (default `Asia/Karachi`), `city`, `country` (default `Pakistan`), `status` (`draft`|`planned`|`active`|`completed`|`canceled`), `budget`, `guest_count`

**`domain_events`** (append-only, never delete): `id`, `event_type`, `data` (JSONB), `source`, `user_id`, `correlation_id`, `timestamp`

**Supporting:** `refresh_tokens`, `password_reset_tokens`, `categories`, `vendor_category_link`, `vendor_availability`, `booking_messages`, `approvals`, `inquiries`, `notifications`, `notification_preferences`, `vendor_embeddings`

**AI schema (`ai.*`):** `chat_sessions`, `messages`, `agent_executions`, `message_feedback`

---

## Booking State Machine

```
pending ──confirm──▶ confirmed ──start──▶ in_progress ──complete──▶ completed
   │                    │                      │
   │reject         cancel│               no_show│
   ▼                    ▼                      ▼
rejected            cancelled             no_show
```

| From | Allowed next |
|---|---|
| `pending` | `confirmed`, `rejected`, `cancelled` |
| `confirmed` | `in_progress`, `cancelled` |
| `in_progress` | `completed`, `no_show` |
| `completed`, `cancelled`, `rejected`, `no_show` | ❌ terminal |

Side effects: `cancelled`/`rejected` → releases availability slot + emits domain event. All transitions emit domain events via `event_bus`.

---

## Common Code Patterns

### Service (singleton class)
```python
class MyService:
    async def create_thing(self, session: AsyncSession, data: ThingCreate, user_id: uuid.UUID) -> Thing:
        db_obj = Thing(**data.model_dump(), user_id=user_id)
        session.add(db_obj)
        await session.flush()
        await event_bus.emit(session, "thing.created", payload={...}, user_id=user_id)
        await session.commit()
        await session.refresh(db_obj)
        logger.info("thing.created", id=str(db_obj.id))
        return db_obj

my_service = MyService()  # singleton at bottom of file
```

### Error helper
```python
def _err(code: str, message: str) -> dict:
    return {"code": code, "message": message}

raise HTTPException(status_code=404, detail=_err("NOT_FOUND_VENDOR", "Vendor not found."))
```

### SQLModel query
```python
stmt = select(Booking).where(Booking.user_id == user_id).options(selectinload(Booking.vendor))
result = await session.execute(stmt)
bookings = result.scalars().all()
```

### Domain event emission (outbox pattern — always same session)
```python
from src.services.event_bus_service import event_bus
await event_bus.emit(session, "booking.created", payload={"booking_id": str(id)}, user_id=user_id)
```

---

## Agent Architecture

### Pipeline topology
```
User request (HTTP/SSE)
       ↓
  TriageAgent          ← sole entry point
       ↓
  EventPlannerAgent  ←→  VendorDiscoveryAgent
                              ↓
                        BookingAgent
                              ↓
                        OrchestratorAgent   ← multi-step coordination
```

Files in `packages/agentic_event_orchestrator/pipeline/`:
- `triage.py` → `build_triage_agent()` — entry point
- `event_planner.py`, `vendor_discovery.py`, `booking.py`, `orchestrator.py`
- `instructions.py` — system prompt strings

### Adding a new agent
1. Create `pipeline/<name>.py` with `build_<name>_agent(model, ...)`
2. Add instruction string to `pipeline/instructions.py`
3. Wire into `build_pipeline()` in `pipeline/__init__.py`
4. Add as handoff target to TriageAgent or appropriate parent

### Adding a new tool
```python
from agents import function_tool

@function_tool
async def search_vendors(city: str, category: str) -> list[dict]:
    """Search vendors by city and category."""  # docstring = LLM tool description
    ...
```
Attach via `tools=[...]` on the agent. All tools that call external services must use `@function_tool` — no bare calls inside agent logic.

### Security hooks (wired at startup in `main.py`)
- `PromptFirewall` — blocklist injection detection
- `OutputLeakDetector` — canary token leakage detection
- `GuardrailService` — SDK-native input/output guardrail hooks
- OpenAI tracing disabled (`set_tracing_disabled(True)`) — Gemini runs via LiteLLM

### AI model config (`config/settings.py`)
| Setting | Value |
|---|---|
| Model | `gemini/gemini-3-flash-preview` (via `GEMINI_MODEL` env) |
| Max handoff depth | 5 |
| Max response chars | 2000 |
| Max input chars | 2000 |
| Rate limit | 30 req/min per user |

---

## Testing Patterns

Tests use `sqlite+aiosqlite:///:memory:` — no Neon, no Docker needed.

### Key fixtures (`tests/conftest.py`)
- `test_engine` (session scope) — creates all tables once
- `db_session` (function scope) — rolls back after each test
- `client` (function scope) — `AsyncClient` with DB + rate-limit overrides injected

### Integration test template
```python
class TestMyFeature:
    @pytest.mark.asyncio
    async def test_success(self, client: AsyncClient):
        reg = await client.post("/api/v1/auth/register", json={
            "email": "x@example.com", "password": "StrongPass123!",
            "first_name": "T", "last_name": "U",
        })
        token = reg.json()["access_token"]
        resp = await client.post("/api/v1/things", json={"name": "x"},
                                 headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201
        assert resp.json()["success"] is True
```

### Key rules
- Login endpoint uses **form-encoded** data (`data=`), not JSON
- JSONB → JSON SQLite patch already done in `conftest.py` for `DomainEvent.data`
- New rate limiters must be added to `client` fixture overrides
- Never assert exact token values — assert presence and structure only
- Zero real LLM calls in tests — mock with `respx`
- Zero real MCP calls in tests — mock with `respx` or subprocess mock

---

## SSE / Real-time Pattern

**Stack:** `SSEConnectionManager` → `/api/v1/sse` → browser `EventSource`

Push from a service:
```python
sse_manager = request.app.state.connection_manager  # or Depends(get_connection_manager)
await sse_manager.push(user_id=user_id, event_type="booking.confirmed", data={...})
```

Frontend subscribe:
```ts
const source = new EventSource(`${API_URL}/sse`, { withCredentials: true });
source.addEventListener("booking.confirmed", (e) => { const payload = JSON.parse(e.data); });
```

- Per-user queue, max 50 messages; evicts oldest on overflow
- Singleton on `app.state.connection_manager`

---

## Migration Workflow

```bash
cd packages/backend

# Create
uv run alembic revision --autogenerate -m "add_vendor_rating_column"
# Review alembic/versions/<id>_*.py — verify upgrade() and downgrade()

# Apply
uv run alembic upgrade head

# Rollback
uv run alembic downgrade -1

# Status
uv run alembic current
uv run alembic history --verbose
```

**Rules:** Use `DIRECT_URL` (not pooler) for Alembic. Every migration needs a working `downgrade()`. Never write raw DDL outside Alembic. Enable pgvector before first migration: `CREATE EXTENSION IF NOT EXISTS vector;`

---

## Important Notes

### Security
- Never commit `.env` — keep `.env.example` updated
- No hardcoded secrets; JWT secrets min 32 chars
- Rate limiting mandatory on all public endpoints
- No wildcard CORS in production
- Never store raw payment data

### Database
- Neon PostgreSQL only; pgvector required
- `DIRECT_URL` for Alembic, `DATABASE_URL` (pooler) for runtime
- `selectinload` for relational queries (prevent N+1)
- `domain_events` and `usage_events` are core tables — do not remove

### Known Gotchas
- **asyncpg SSL:** Pass `connect_args={"ssl": "require"}` — not `?sslmode=require` in URL
- **Neon dual URL:** pooler URL → runtime; direct URL → Alembic only; mixing causes pgbouncer errors
- **Next.js 15 cookies:** `await cookies()` — was sync in v14, async in v15
- **Google OAuth:** `GOOGLE_REDIRECT_URI` must match Google Cloud Console exactly (trailing slash matters). The registered redirect URI is `http://localhost:5000/api/v1/auth/google/callback` — backend runs on port **5000**
- **Google OAuth origins:** Registered JS origins are `localhost:5000`, `localhost:3000`, `localhost:3003`, `localhost:3002` — update Google Cloud Console if adding new origins
- **pgvector:** Must be enabled before first migration: `CREATE EXTENSION IF NOT EXISTS vector;` — required for `vendor_embeddings` table
- **uv run:** Always prefix Python commands with `uv run` — don't activate venv manually
- **Agent tracing disabled:** `set_tracing_disabled(True)` — do not re-enable without a real OpenAI key
- **Embedding staleness:** `upsert_vendor_embedding` uses SHA-256 of canonical vendor text — Gemini is only called when content changes

### Banned Practices
`NextAuth` · `Auth0` · `Clerk` · `Firebase Auth` · `localStorage JWT` · `sessionStorage JWT` · `sys.path.insert` · `nest_asyncio` · `npm` · `pip` · direct AI DB writes · real LLM/MCP calls in tests · LangChain for orchestration · raw `os.environ`

---

## Commit & PR Conventions

```
<type>(<scope>): <short description>
```
**Types:** `feat` · `fix` · `chore` · `refactor` · `test` · `docs` · `perf` · `ci`

**Scopes:** `backend` · `user` · `frontend` · `admin` · `agentic_event_orchestrator` · `ui` · `infra` · `db`

```
feat(backend): add vendor rating endpoint
fix(user): correct cookie expiry on logout
test(agentic_event_orchestrator): mock TriageAgent in unit tests
```

PRs target `develop`, never `main` directly. Squash-merge preferred. All CI checks (lint, typecheck, pytest) must pass.

---

## Governance

- `.specify/memory/constitution.md` is the supreme engineering authority
- All code must comply with constitutional standards
- ADR required for any stack deviation

**When unsure:** follow `constitution.md` → use `src/middleware/auth.middleware.py` → prefer simplicity → keep package boundaries strict → make the smallest safe change.
