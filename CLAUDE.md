# CLAUDE.md

> **Supreme authority:** `constitution.md` overrides everything else, including this file.

---

## 1. Project Overview

**Event-AI** is an AI-powered event planning marketplace for Pakistan. It centralises vendor discovery, booking coordination, payment processing, and AI-assisted orchestration into one unified, event-driven platform.

### Problem it solves
Traditional event planning is fragmented across disconnected workflows — discovery, booking, scheduling, payments, communication, and personalised planning. Event-AI stitches all of these together with:

- AI-powered planning and vendor recommendations
- Dedicated User, Vendor, and Admin portals
- Real-time event-driven backend architecture
- Monetised subscription-based AI services
- Unified event lifecycle management

### Core product areas

| Package | Purpose |
|---|---|
| `packages/user` | User portal — AI planning, bookings, vendor discovery |
| `packages/vendor` | Vendor portal — onboarding, service management, bookings |
| `packages/admin` | Admin portal — moderation, approvals, analytics |
| `packages/backend` | REST API — auth, bookings, events, payments, business logic |
| `packages/agentic_event_orchestrator` | AI service — agents, Agentic RAG, MCP tools |
| `packages/ui` | Shared design system and reusable components |

---

## 2. Technology Stack

### Monorepo & Tooling
- **Turborepo** + **pnpm workspaces**
- Docker (development only)
- GitHub Actions CI/CD
- Conventional Commits

### Backend (`packages/backend`)
- Python 3.12+, **FastAPI**, **SQLModel**
- PostgreSQL via **Neon** + **pgvector**
- **asyncpg**, **Pydantic**, **Structlog**
- Custom JWT authentication (`middleware/auth.py`)
- Package manager: **uv**

### AI Layer (`packages/agentic_event_orchestrator`)
- FastAPI + **OpenAI Agents SDK**
- **Gemini** (OpenAI-compatible endpoint)
- **LangChain** (Agentic RAG pipelines only)
- **Mem0** (memory), **MCP Protocol**, **SSE** / sse-starlette

### Frontend (all portals)
- **Next.js 15**, **TypeScript** (strict mode)
- **Tailwind CSS**, **shadcn/ui**, **React Query**

### Testing
- Python: **pytest**, pytest-asyncio, httpx, **respx**
- JavaScript: **Jest**, React Testing Library

---

## 3. Directory Structure

```
Event-AI/
│
├── packages/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── models/          # SQLModel DB entities (source of truth)
│   │   │   ├── schemas/         # Pydantic request/response models
│   │   │   ├── services/        # Business logic
│   │   │   ├── db/
│   │   │   │   ├── session.py   # Async DB engine/session
│   │   │   │   ├── base.py      # Shared metadata
│   │   │   │   └── repositories/
│   │   │   ├── middleware/
│   │   │   │   └── auth.py      # ← Canonical custom auth (do not bypass)
│   │   │   ├── api/             # /api/v1/ routes
│   │   │   └── core/            # Config, security, logging
│   │   ├── alembic/
│   │   │   └── versions/        # Only migration location
│   │   ├── scripts/
│   │   │   ├── seed.py
│   │   │   ├── reset_db.py
│   │   │   └── backfill_*.py
│   │   └── tests/
│   │       ├── test_models/
│   │       ├── test_services/
│   │       ├── test_api/
│   │       ├── test_auth/
│   │       └── test_migrations/
│   │
│   ├── agentic_event_orchestrator/   # AI service
│   ├── user/                         # User portal
│   ├── frontend/                     # Vendor portal
│   ├── admin/                        # Admin portal
│   └── ui/                           # Shared UI library
│
├── docker-compose.yml
├── turbo.json
├── pnpm-workspace.yaml
├── constitution.md                   # Supreme engineering authority
└── README.md
```

### Database organisation rules
- `app/models/` is the single source of truth for schema
- `alembic/versions/` is the only place migrations live
- `scripts/` is for operational scripts only — never mix schema changes with seed data
- Every schema change requires a reversible Alembic migration

---

## 4. Coding Conventions

### General
- Use **pnpm** for Node packages; use **uv** for Python packages — never `npm` or `pip`
- **TDD is mandatory** — write tests before or alongside implementation
- Prefer flat architecture; make the smallest safe change first
- `constitution.md` overrides README when they conflict

### Python
- Full type hints required on all functions
- Prefer `async def`; use `@asynccontextmanager` for lifespan
- Format and lint with **Ruff**
- Use **SQLModel** for all DB models; **Pydantic** for all structured data
- Dependency injection via `Depends()`
- **Banned:** `sys.path.insert`, `nest_asyncio`, raw `os.environ`

### TypeScript
- Strict mode — no `any`
- PascalCase for components, camelCase for functions, kebab-case for filenames

### Authentication (non-negotiable)
- **All auth flows through `middleware/auth.py`** — no exceptions
- Protected routes must use `@require_auth` or `@require_admin` decorators
- JWT stored in **httpOnly cookies only** — never localStorage or sessionStorage
- **Banned:** NextAuth, Auth0, Clerk, Firebase Auth, any route-level custom auth logic

### AI / Agentic layer
- `TriageAgent` is the sole entry point for all agent interactions
- All external actions wrapped in `@function_tool`
- MCP tools are **read-only**
- LangChain used **only** for Agentic RAG pipelines
- OpenAI Agents SDK used **only** for orchestration
- Require user confirmation before any destructive agent action

---

## 5. Key Commands

```bash
# Install dependencies
pnpm install
uv sync

# Run local dev servers
pnpm dev              # all packages
pnpm dev:backend      # FastAPI backend only
pnpm dev:user         # User portal only
pnpm dev:frontend     # Vendor portal only
pnpm dev:admin        # Admin portal only

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
pytest                # Python tests
```

### Branching strategy
```
feature/<name>
hotfix/<name>
develop
main
```

---

## 6. Important Notes

### Security
- Never commit `.env` — keep `.env.example` up to date
- No hardcoded secrets or tokens anywhere in the codebase
- JWT secrets must be cryptographically secure
- httpOnly cookie auth only; CSRF protection required
- Rate limiting is mandatory on all public endpoints
- No wildcard CORS in production
- Never store raw payment data

### Testing constraints
- **Zero** real LLM calls in tests — always mock
- **Zero** real MCP calls in tests — always mock
- Mock all external HTTP with `respx`
- Test `middleware/auth.py` directly and test decorator enforcement
- Test migration integrity in `test_migrations/`

### Database
- Neon PostgreSQL only; pgvector extension required
- Alembic mandatory for all schema changes — no manual DDL
- Async DB sessions only; use `selectinload` for relational queries
- `domain_events` and `usage_events` are core tables — do not remove

### Banned practices
`NextAuth` · `Auth0` · `Clerk` · `Firebase Auth` · `localStorage JWT` · `sessionStorage JWT` · `sys.path.insert` · `nest_asyncio` · `npm` · `pip` · direct AI DB writes · real external API calls in tests

### Governance & final rule
- `constitution.md` is the supreme engineering authority
- All code must comply with constitutional standards
- An ADR is required for any stack deviation

**When unsure:** follow `constitution.md` → use `middleware/auth.py` → prefer simplicity → keep package boundaries strict → make the smallest safe change.

---

## 7. Environment Setup

Each package that needs env vars has its own `.env.example`. Copy and fill before starting.

### Bootstrap order
```bash
# 1. Install all deps
pnpm install          # Node packages (all portals)
cd packages/backend && uv sync          # Backend Python deps
cd packages/agentic_event_orchestrator && uv sync   # AI service deps

# 2. Create env files
cp packages/backend/.env.example packages/backend/.env
cp packages/agentic_event_orchestrator/.env.example packages/agentic_event_orchestrator/.env
# Fill in DATABASE_URL, JWT_SECRET_KEY, GEMINI_API_KEY, etc.

# 3. Start database (Docker required)
pnpm db:up

# 4. Run migrations
pnpm db:migrate

# 5. Start all services
pnpm dev
```

### Required env vars per package

**`packages/backend/.env`** — minimum to boot:
| Variable | Notes |
|---|---|
| `DATABASE_URL` | Neon/Postgres pooler URL (`?pgbouncer=true`) |
| `DIRECT_URL` | Direct connection URL (migrations only) |
| `JWT_SECRET_KEY` | Min 32 chars — generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `CORS_ORIGIN` | Comma-separated — `http://localhost:3002,http://localhost:3003` |
| `FRONTEND_URL` | Used in email links — `http://localhost:3003` |

Optional: `SMTP_*` (email), `GOOGLE_CLIENT_*` (OAuth), `S3_*` (file uploads), `REDIS_URL` (rate limiting).

**`packages/agentic_event_orchestrator/.env`** — minimum to boot:
| Variable | Notes |
|---|---|
| `GEMINI_API_KEY` | Google AI key restricted to Generative Language API |
| `AI_SERVICE_API_KEY` | 32+ byte random token for service-to-service auth |
| `SERVICE_SECRET` | Must match `AGENT_SERVICE_SECRET` in backend `.env` |
| `BACKEND_API_URL` | `http://localhost:3001/api/v1` for local dev |
| `CORS_ORIGINS` | Comma-separated allowed origins |

### Port map
| Service | Port |
|---|---|
| Backend API | `3001` |
| User portal | `3003` |
| Vendor portal | `3002` |
| Admin portal | `3004` |
| AI orchestrator | `8000` |

---

## 8. API Conventions

### Base URL & versioning
All backend routes are prefixed `/api/v1/`. No route should be registered without this prefix.

### Route inventory (from `src/main.py`)
| Prefix | Router |
|---|---|
| `/api/v1/auth` | Authentication (login, register, refresh, OAuth) |
| `/api/v1/users` | User profile management |
| `/api/v1/vendors` | Vendor portal — CRUD, services, availability |
| `/api/v1/public_vendors` | Public vendor discovery (no auth) |
| `/api/v1/categories` | Service categories |
| `/api/v1/bookings` | Booking lifecycle |
| `/api/v1/services` | Vendor services |
| `/api/v1/events` | Event management |
| `/api/v1/inquiries` | Vendor inquiries |
| `/api/v1/uploads` | CDN file uploads |
| `/api/v1/notifications` | User notifications |
| `/api/v1/sse` | Server-sent events stream |
| `/api/v1/admin/*` | Admin-only routes (approvals, stats, vendors, users) |

### Standard response envelope
All responses follow this shape:
```json
// Success
{ "success": true, "data": { ... }, "meta": {} }

// Error
{ "success": false, "error": { "code": "ERROR_CODE", "message": "Human message" } }
```

### Error code taxonomy
| HTTP | Code | Meaning |
|---|---|---|
| 401 | `AUTH_UNAUTHORIZED` | Missing or invalid token |
| 403 | `AUTH_FORBIDDEN` | Authenticated but not permitted |
| 404 | `NOT_FOUND` | Resource does not exist |
| 409 | `CONFLICT` | State conflict (already booked, duplicate, etc.) |
| 422 | `VALIDATION_ERROR` | Bad request body / params |
| 429 | `AUTH_RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Unhandled server error |

Domain-specific codes are namespaced: `NOT_FOUND_VENDOR`, `CONFLICT_DATE_UNAVAILABLE`, `VALIDATION_PAST_DATE`, etc.

### Auth dependency usage
```python
from src.middleware.auth.middleware import get_current_user

@router.get("/protected")
async def protected_route(current_user = Depends(get_current_user)):
    ...

# Optional auth (public endpoints that can benefit from user context)
from src.middleware.auth.middleware import get_current_user_optional
```

---

## 9. Common Code Patterns

### Service class pattern
Services are singleton class instances at module level. All methods are `async` and take `session: AsyncSession` as their first argument.

```python
# src/services/my_service.py
class MyService:
    async def create_thing(self, session: AsyncSession, data: ThingCreate, user_id: uuid.UUID) -> Thing:
        db_obj = Thing(**data.model_dump(), user_id=user_id)
        session.add(db_obj)
        await session.flush()                   # get ID without committing
        await event_bus.emit(session, "thing.created", payload={...}, user_id=user_id)
        await session.commit()
        await session.refresh(db_obj)
        logger.info("thing.created", id=str(db_obj.id))
        return db_obj

my_service = MyService()                        # ← singleton at bottom of file
```

### Domain event emission
Always emit events via `event_bus` **within the same session** (outbox pattern):
```python
from src.services.event_bus_service import event_bus

await event_bus.emit(
    session,
    "booking.created",                          # event type string
    payload={"booking_id": str(id), ...},
    user_id=user_id,
)
```
The event bus persists events to the `domain_events` table and fires any registered in-process listeners.

### Error helper
```python
def _err(code: str, message: str) -> dict:
    return {"code": code, "message": message}

raise HTTPException(status_code=404, detail=_err("NOT_FOUND_VENDOR", "Vendor not found."))
```

### SQLModel query pattern
```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Single row
result = await session.get(Booking, booking_id)

# Filtered list with eager loading
stmt = select(Booking).where(Booking.user_id == user_id).options(selectinload(Booking.vendor))
result = await session.execute(stmt)
bookings = result.scalars().all()
```

---

## 10. Agent Architecture

### Pipeline topology
```
User request (HTTP/SSE)
       │
       ▼
  TriageAgent          ← sole entry point; classifies intent
       │
   ┌───┴────────────────────┐
   ▼                        ▼
EventPlannerAgent     VendorDiscoveryAgent
   │                        │
   └──────────┬─────────────┘
              ▼
        BookingAgent        ← handles booking actions
              │
        OrchestratorAgent   ← coordinates multi-step flows
```

Built in `packages/agentic_event_orchestrator/pipeline/`:
- `triage.py` — `build_triage_agent()` — entry point
- `event_planner.py` — `build_event_planner_agent()`
- `vendor_discovery.py` — `build_vendor_discovery_agent()`
- `booking.py` — `build_booking_agent()`
- `orchestrator.py` — `build_orchestrator_agent()`
- `instructions.py` — system prompt strings for each agent

### Adding a new agent
1. Create `pipeline/<name>.py` with a `build_<name>_agent(model, ...)` function
2. Add its instruction string to `pipeline/instructions.py`
3. Wire it into `build_pipeline()` in `pipeline/__init__.py`
4. Pass it as a handoff target to `TriageAgent` or the appropriate parent agent

### Adding a new tool
```python
from agents import function_tool

@function_tool
async def search_vendors(city: str, category: str) -> list[dict]:
    """Search vendors by city and category."""
    ...
```
Attach to an agent via its `tools=[...]` list. All tools that call external services must be `@function_tool` — no bare function calls inside agent logic.

### Security hooks (startup wiring)
At startup `main.py` initialises and wires:
- `PromptFirewall` — blocks injection patterns before they reach the model
- `OutputLeakDetector` — detects canary token leakage in responses
- `GuardrailService` — SDK-native input/output guardrail hooks
- OpenAI tracing is **disabled** (`set_tracing_disabled(True)`) — Gemini runs via LiteLLM

---

## 11. Migration Workflow

```bash
cd packages/backend

# 1. Create a new migration (auto-detect model changes)
uv run alembic revision --autogenerate -m "add_vendor_rating_column"

# 2. Review the generated file in alembic/versions/ — verify upgrade() and downgrade()

# 3. Apply to local DB
uv run alembic upgrade head

# 4. Roll back one step
uv run alembic downgrade -1

# 5. Show current revision
uv run alembic current

# 6. Show full history
uv run alembic history --verbose
```

### Rules
- Always review autogenerated migrations — SQLAlchemy misses some changes (e.g., column type changes, index renames)
- Every migration must have a working `downgrade()` — no `pass`
- Use `DIRECT_URL` (not pooler) when running Alembic — set in `.env` as `DIRECT_URL`
- Never write raw DDL outside of Alembic
- pgvector extension must exist before first migration: `CREATE EXTENSION IF NOT EXISTS vector;`

---

## 12. Known Gotchas

### asyncpg SSL — wrong parameter kills the connection
asyncpg does **not** accept `sslmode=require` in the URL query string. Pass SSL via `connect_args`:
```python
# ✅ Correct
engine = create_async_engine(url, connect_args={"ssl": "require"})

# ❌ Wrong — causes ClientConfigurationError
engine = create_async_engine("postgresql+asyncpg://...?sslmode=require")
```

### Neon — two URLs, two purposes
- `DATABASE_URL` (pooler, port 6543) — use at runtime in the app
- `DIRECT_URL` (direct, port 5432) — use for Alembic migrations only
  Mixing them causes "prepared statement already exists" errors under pgbouncer.

### pgvector — must be enabled before first migration
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
Run this manually on a fresh Neon database before `alembic upgrade head`.

### Next.js 15 App Router — cookies are async
In Next.js 15 the `cookies()` helper is async. Always `await cookies()`:
```ts
// ✅
const cookieStore = await cookies();
// ❌ — was sync in Next.js 14, breaks in 15
const cookieStore = cookies();
```

### Google OAuth — redirect URI must match exactly
The `GOOGLE_REDIRECT_URI` in `.env` must be character-for-character identical to the URI registered in Google Cloud Console. A trailing slash difference = OAuth failure.

### Agent tracing disabled
OpenAI Agents SDK tracing is explicitly disabled at startup because the service uses Gemini via LiteLLM, not a native OpenAI key. Do not re-enable tracing without providing a valid OpenAI API key.

### `uv run` vs activating venv
Always prefix Python commands with `uv run` inside each package directory — do not activate the venv manually or the wrong Python may be used.

---

## 13. Commit & PR Conventions

### Conventional Commits format
```
<type>(<scope>): <short description>

[optional body]
[optional footer]
```

**Types:** `feat` · `fix` · `chore` · `refactor` · `test` · `docs` · `perf` · `ci`

**Scopes** (use the package name):
```
feat(backend): add vendor rating endpoint
fix(user): correct cookie expiry on logout
chore(infra): update docker-compose postgres version
test(agentic_event_orchestrator): mock TriageAgent in unit tests
docs(admin): document approval workflow
```

### Branch → PR flow
```
feature/<short-name>   →   develop   →   main
hotfix/<short-name>    →   develop   →   main
```
- PRs always target `develop`, never `main` directly
- Squash-merge preferred to keep `develop` history clean
- PR description must reference the spec or task being addressed
- All CI checks (lint, typecheck, pytest) must pass before merge

---

## 14. Data Model Overview

All models live in `packages/backend/src/models/`. Each file follows the SQLModel pattern: a `Base` class (shared fields), a `table=True` DB class, and separate `Create`/`Read` Pydantic models.

### Core tables

**`users`** — authentication identity
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `email` | str unique | indexed |
| `password_hash` | str | bcrypt |
| `first_name`, `last_name` | str? | |
| `role` | str | `"user"` \| `"vendor"` \| `"admin"` |
| `is_active` | bool | default `True` |
| `email_verified` | bool | default `False` |
| `failed_login_attempts` | int | brute-force tracking |
| `locked_until` | datetime? | account lockout |

**`vendors`** — vendor profiles (one per user)
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | unique (1:1) |
| `business_name` | str | indexed |
| `contact_email` | str unique | |
| `city`, `region` | str? | indexed |
| `status` | enum | `PENDING` \| `ACTIVE` \| `SUSPENDED` \| `REJECTED` |
| `rating` | float | default `0.0` |
| `total_reviews` | int | default `0` |

**`services`** — services offered by a vendor
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `vendor_id` | UUID FK → vendors | |
| `name` | str | indexed |
| `price_min`, `price_max` | float? | price range |
| `capacity` | int? | max guests |
| `is_active` | bool | default `True` |

**`bookings`** — core transactional entity
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `vendor_id` | UUID FK → vendors | |
| `service_id` | UUID FK → services | |
| `event_date` | date | must be future |
| `status` | enum | see state machine §15 |
| `payment_status` | enum | `pending` \| `partial` \| `paid` \| `refunded` \| `failed` |
| `unit_price`, `total_price` | float | |
| `currency` | str | default `"USD"` |
| `event_location` | JSONB | `{address, city, ...}` |

**`events`** — user-created event plans
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `event_type_id` | UUID FK → event_types | |
| `name` | str | |
| `start_date`, `end_date` | datetime (UTC) | default tz `Asia/Karachi` |
| `city`, `country` | str | default `"Pakistan"` |
| `status` | enum | `draft` \| `planned` \| `active` \| `completed` \| `canceled` |
| `budget` | float? | |
| `guest_count` | int? | |

**`domain_events`** — append-only event log (do not delete)
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `event_type` | str | e.g. `"booking.created"` |
| `data` | JSONB | arbitrary payload |
| `source` | str | `"backend_service"` |
| `user_id` | UUID? | actor |
| `correlation_id` | str? | trace grouping |

**Supporting tables:** `refresh_tokens`, `password_reset_tokens`, `categories`, `vendor_category_link`, `vendor_availability`, `booking_messages`, `approvals`, `inquiries`, `notifications`, `notification_preferences`

---

## 15. Booking State Machine

```
                    ┌─────────────┐
          ┌────────▶│  cancelled  │◀──────────┐
          │         └─────────────┘           │
          │                                   │
  ┌───────┴──────┐   confirm    ┌─────────────┴────┐
  │   pending    │─────────────▶│   confirmed      │
  └──────────────┘              └──────────────────┘
          │                             │
          │ reject                      │ start
          ▼                             ▼
  ┌───────────────┐           ┌─────────────────┐
  │   rejected    │           │   in_progress   │
  └───────────────┘           └─────────────────┘
                                       │              │
                               complete│         no_show│
                                       ▼              ▼
                              ┌──────────────┐ ┌──────────┐
                              │  completed   │ │ no_show  │
                              └──────────────┘ └──────────┘
```

**Valid transitions** (enforced in `BookingService.update_status()`):
| From | Allowed next states |
|---|---|
| `pending` | `confirmed`, `rejected`, `cancelled` |
| `confirmed` | `in_progress`, `cancelled` |
| `in_progress` | `completed`, `no_show` |
| `completed`, `cancelled`, `rejected`, `no_show` | ❌ terminal — no transitions |

**Side effects on transition:**
- `confirmed` → sets `confirmed_at`, `confirmed_by`
- `rejected` / `cancelled` → releases availability slot, sets `cancelled_at`, `cancelled_by`, optional `cancellation_reason`
- All transitions → emit domain event via `event_bus`

---

## 16. Testing Patterns

### Setup — SQLite in-memory, no real DB
Tests use `sqlite+aiosqlite:///:memory:` via `conftest.py`. No Neon, no Docker needed for the test suite.

```python
# conftest.py pattern — already exists, do not duplicate
# Key fixtures:
#   test_engine  (session scope) — creates all tables once
#   db_session   (function scope) — rolls back after each test
#   client       (function scope) — AsyncClient with DB + rate-limit overrides
```

### Writing an integration test
```python
import pytest
from httpx import AsyncClient

class TestMyFeature:
    @pytest.mark.asyncio
    async def test_create_thing_success(self, client: AsyncClient):
        # 1. Register + get token
        reg = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "StrongPass123!",
            "first_name": "Test", "last_name": "User",
        })
        token = reg.json()["access_token"]

        # 2. Make authenticated request
        resp = await client.post(
            "/api/v1/things",
            json={"name": "my thing"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # 3. Assert response envelope
        assert resp.status_code == 201
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["name"] == "my thing"

    @pytest.mark.asyncio
    async def test_create_thing_unauthenticated(self, client: AsyncClient):
        resp = await client.post("/api/v1/things", json={"name": "x"})
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "AUTH_UNAUTHORIZED"
```

### Writing a service unit test
```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_my_service_method(db_session):
    from src.services.my_service import my_service
    result = await my_service.create_thing(db_session, data=..., user_id=uuid.uuid4())
    assert result.name == "expected"
```

### Key rules
- Login uses **form-encoded** data (`data=`, not `json=`) — `OAuth2PasswordRequestForm`
- All test classes group by feature; use descriptive method names
- JSONB columns must be patched to JSON for SQLite: already done in `conftest.py` for `DomainEvent.data`
- Rate limiters are overridden to `no_rate_limit` in the `client` fixture — do not add new limiters without adding an override
- Never assert exact token values — assert presence and structure only

### Running tests
```bash
cd packages/backend
uv run pytest                          # all tests
uv run pytest tests/test_auth_routes.py  # single file
uv run pytest -k "test_login"          # by name pattern
uv run pytest -v --tb=short            # verbose with short tracebacks
```

---

## 17. Frontend Data Fetching Pattern

### API client — `packages/user/src/lib/api.ts`
All HTTP calls go through a single **axios** instance:

```ts
import { api } from "@/lib/api";

// api is pre-configured with:
//   baseURL = NEXT_PUBLIC_API_URL  (defaults to http://localhost:3001/api/v1)
//   request interceptor  → attaches Bearer token from localStorage
//   response interceptor → clears auth and redirects to /login on 401
```

> ⚠️ **Note:** The current `api.ts` stores the JWT in `localStorage` (`userToken` key). This predates the architecture decision to use httpOnly cookies. When refactoring auth, update the interceptors — do not add a second storage mechanism.

### Calling the API from a component
```ts
// Direct call (for mutations / one-offs)
const data = await getUserBookings();

// With React Query (preferred for data that needs caching/refetching)
import { useQuery, useMutation } from "@tanstack/react-query";
import { getUserBookings, cancelBooking } from "@/lib/api";

function BookingsList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["bookings"],
    queryFn: getUserBookings,
  });

  const cancel = useMutation({
    mutationFn: (id: string) => cancelBooking(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["bookings"] }),
  });
}
```

### Available API helpers (from `lib/api.ts`)
| Function | Endpoint | Auth? |
|---|---|---|
| `getVendors(params?)` | `GET /public_vendors/` | No |
| `getVendorById(id)` | `GET /public_vendors/:id` | No |
| `createEvent(data)` | `POST /events` | Yes |
| `getUserEvents()` | `GET /events` | Yes |
| `createBooking(data)` | `POST /bookings` | Yes |
| `getUserBookings()` | `GET /bookings` | Yes |
| `cancelBooking(id)` | `PATCH /bookings/:id/cancel` | Yes |
| `getUserNotifications()` | `GET /notifications/` | Yes |
| `markNotificationAsRead(id)` | `PATCH /notifications/:id/read` | Yes |
| `getUserProfile()` | `GET /users/me` | Yes |
| `updateUserProfile(data)` | `PATCH /users/me` | Yes |

---

## 18. SSE / Real-time Pattern

Server-sent events power live notifications. The stack is: `SSEConnectionManager` (backend) → `/api/v1/sse` route → browser `EventSource`.

### How it works
1. Client opens a persistent `GET /api/v1/sse` connection (authenticated)
2. Backend registers the user's queue via `SSEConnectionManager.connect(user_id)`
3. Any service that needs to push a real-time update calls `sse_manager.push(...)`
4. The SSE route streams queued events as `text/event-stream`

### Pushing an event from a service
```python
from src.services.sse_manager import get_connection_manager  # use as Depends()
# OR access directly if you have request.app.state:
sse_manager = request.app.state.connection_manager

await sse_manager.push(
    user_id=user_id,
    event_type="booking.confirmed",
    data={"booking_id": str(booking_id), "vendor_name": "ABC Events"},
)
```

### Frontend — subscribing to events
```ts
const source = new EventSource(
  `${process.env.NEXT_PUBLIC_API_URL}/sse`,
  { withCredentials: true }   // sends cookies / auth header
);

source.addEventListener("booking.confirmed", (e) => {
  const payload = JSON.parse(e.data);
  // update UI
});

source.onerror = () => source.close();
```

### SSE manager characteristics
- Per-user queue, max 50 messages (`DEFAULT_QUEUE_MAXSIZE`)
- On overflow: evicts oldest message, inserts newest (no blocking)
- Singleton stored on `app.state.connection_manager`
- Dependency injection: `Depends(get_connection_manager)`

---

## 19. AI Model & Guardrails Config

### Model
The orchestrator uses **Gemini via LiteLLM** (not OpenAI directly):

| Setting | Value | Source |
|---|---|---|
| Model | `gemini/gemini-3-flash-preview` | `GEMINI_MODEL` env var |
| Base URL | `https://generativelanguage.googleapis.com/v1beta/openai/` | `settings.gemini_base_url` |
| API Key | `GEMINI_API_KEY` | env var |
| Tracing | Disabled | `set_tracing_disabled(True)` at startup |

### Agent safety limits (from `config/settings.py`)
| Setting | Default | Purpose |
|---|---|---|
| `max_handoff_depth` | `5` | Prevents infinite agent loops |
| `max_response_chars` | `2000` | Keeps responses concise |
| `max_input_chars` | `2000` | Input size cap for firewall |
| `rate_limit_per_minute` | `30` | Per-user request throttle |

### Guardrail stack (startup order)
1. **`PromptFirewall`** — blocklist-based injection detection (`data/injection_blocklist.yaml`)
2. **`OutputLeakDetector`** — canary token injected at startup; detects prompt leakage in responses
3. **`GuardrailService`** — wires SDK-native `input_guardrail` / `output_guardrail` hooks
4. **ShieldGemma** — optional LLM-based safety classifier (`SHIELDGEMMA_ENABLED=false` in dev, `true` in prod)

### Mem0 memory
- Configured via `MEM0_API_KEY`
- Provides per-user persistent memory across sessions
- Session TTL: 30 days (`session_ttl_days`)

### Changing the model
To switch Gemini model versions, update `GEMINI_MODEL` in `.env`. The `gemini/` prefix is required by LiteLLM to route to Google AI.

---

## 20. Turborepo Pipeline

### `turbo.json` task graph
```json
{
  "build":  { "dependsOn": ["^build"], "outputs": [".next/**", "dist/**"] },
  "lint":   { "dependsOn": ["^lint"] },
  "dev":    { "cache": false, "persistent": true }
}
```

| Task | Behaviour |
|---|---|
| `build` | Builds all packages; a package only builds after its dependencies build (`^build`) |
| `lint` | Runs ESLint / Ruff across all packages in dependency order |
| `dev` | Starts all dev servers concurrently; never cached; persistent (long-running) |

### Running tasks
```bash
pnpm turbo build                    # build all packages
pnpm turbo build --filter=user      # build only the user portal
pnpm turbo lint --filter=backend... # lint backend and everything it depends on
pnpm turbo dev                      # equivalent to pnpm dev
```

### Adding a new package
1. Create `packages/<name>/package.json` with a `"name"` field matching the workspace
2. Add scripts (`dev`, `build`, `lint`) — Turbo picks these up automatically
3. Add to `pnpm-workspace.yaml` if not already covered by the glob
4. If it has build outputs, add them to the `turbo.json` `outputs` array
