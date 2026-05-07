# Event-AI — Project Status
**Last Updated:** May 3, 2026  
**Platform:** AI-powered event planning marketplace for Pakistan  
**Stack:** FastAPI (Python/uv) + Next.js 15 + Neon PostgreSQL + pgvector + OpenAI Agents SDK

---

## Build Order & Status

| Phase | Module | Name | Status | Spec |
|---|---|---|---|---|
| 1 | 003 | Database Setup | ✅ Done | phase1-completion |
| 1 | 013 | FastAPI JWT Auth | ✅ Done | phase1-completion |
| 1 | 002 | User Auth + Google OAuth | ✅ Done | phase1-completion |
| 2 | 004 | Vendor Marketplace | ✅ Done | phase2-vendor-marketplace |
| 2 | 005 | Event Management | ✅ Done | event-management |
| 3 | 009 | Booking System | ✅ Done | phase3-booking-system |
| 3 | 010 | Notification System | ✅ Done | notification-system |
| 3 | 008 | Real-Time Updates (SSE) | ✅ Done | (infra + frontend integration) |
| 4 | 011 | RAG & Semantic Search | ✅ Done | rag-semantic-search |
| 4 | 006 | AI Agent Chat | ✅ Done (core) | ai-agent-chat |
| 4 | 009 | Admin Dashboard | ✅ Done | admin-dashboard |
| 5 | 012 | Vendor Portal (Frontend) | ✅ Done (phases 1–2) / 🔄 Phase 3 checkpoint | vendor-portal-complete |
| 5 | 006 | AI Agent Security Hardening | 🔄 In Progress | ai-agent-chat (tasks 5e–5g + 13–17) |
| 5 | 001 | Spec Generator (Tooling) | ❌ Not Started | — |

**Test suite:** 241 tests passing (backend) — zero real LLM/API calls in tests.

---

## What Is Done ✅

### Backend — `packages/backend`

#### Auth & Users (Phase 1)
- JWT access + refresh token pair (HS256, 15min/7day TTL)
- `POST /api/v1/auth/register` — email/password registration
- `POST /api/v1/auth/login` — OAuth2 form-encoded (Swagger-compatible)
- `POST /api/v1/users/login` — JSON login for frontend portal
- `GET /api/v1/auth/me` — authenticated user profile
- `POST /api/v1/auth/refresh` — token rotation
- `POST /api/v1/auth/logout` — refresh token revocation
- `POST /api/v1/auth/password-reset-request` + `/confirm`
- Google OAuth2 (`GET /api/v1/auth/google` + `/callback`) — full flow with CSRF state JWT
- Account locking after 5 failed attempts (15min lockout)
- Standardised error envelope `{"success", "data/error", "meta"}` on all routes
- Global `HTTPException` + `RequestValidationError` handlers in `main.py`
- Admin seed script (`uv run python -m src.scripts.seed`)
- `GET /api/v1/health/db` — DB health with pool stats + pgvector check

#### Vendor Marketplace (Phase 2)
- `POST /api/v1/vendors/register` — vendor registration with approval workflow
- `GET/PUT /api/v1/vendors/profile/me` — vendor self-service profile
- `DELETE /api/v1/vendors/profile/me` — soft-delete (SUSPENDED)
- `GET /api/v1/vendors/me/bookings` — vendor booking list
- `PATCH /api/v1/vendors/me/bookings/{id}/status` — vendor confirms/rejects
- Category assignment on registration + update (M2M via `vendor_categories`)
- Admin approval workflow (`GET/POST /api/v1/admin/approvals/`)
- Vendor search with trigram + ILIKE (`GET /api/v1/public_vendors/`)
- Autocomplete suggestions (`GET /api/v1/public_vendors/suggestions`)
- `GET /api/v1/categories/` — seeded with 8 Pakistani event categories

#### Event Management (Phase 2 / Module 005)
- `EventStatus` state machine: `draft → planned → active → completed`, any → `canceled`
- `EventService` with full business logic (create, get, list, update, cancel, duplicate, list_bookings, admin_list)
- All CRUD routes + `PATCH /status`, `POST /duplicate`, `GET /{id}/bookings`, `GET /admin/all`
- Domain events: `event.created`, `event.status_changed`, `event.cancelled`
- Rate limiting: 10/min create, 60/min reads
- 42 tests (20 unit + 22 integration), all passing

#### Booking System (Phase 3 / Module 009)
- Acquire-lock → create-booking → confirm-lock pattern (30s TTL)
- Full booking CRUD + state machine enforcement
- `GET /api/v1/bookings/availability` — check vendor/service/date availability
- Booking messages CRUD
- Domain events: `booking.created`, `booking.confirmed`, `booking.cancelled`, `booking.completed`
- Background task: expired lock cleanup every 60 seconds

#### Notification System (Module 010)
- `Notification` model + `notifications` table
- `NotificationService.handle()` — event bus listener for all `booking.*`, `event.*`, `vendor.*` events
- Real-time SSE push on notification creation
- `GET /api/v1/notifications/` — paginated list
- `GET /api/v1/notifications/unread-count`
- `PATCH /api/v1/notifications/read-all`
- `PATCH /api/v1/notifications/{id}/read`
- `DELETE /api/v1/notifications/{id}` — delete single
- `DELETE /api/v1/notifications/read` — bulk delete read notifications
- `GET/PUT /api/v1/notifications/preferences/{type}` — per-user notification preferences
- `NotificationPreference` model + Alembic migration
- Rate limiting on all notification endpoints (60/min reads, 10/min writes)
- SSE queue: evict-oldest strategy, `dropped_count()` observable
- Full test suite: service unit tests + route integration tests + property-based tests

#### RAG & Semantic Search (Module 011) — NEW ✅
- `vendor_embeddings` table with `vector(768)` column + HNSW index (Alembic migration)
- `VendorEmbedding` SQLModel with SHA-256 content hash for staleness detection
- `EmbeddingService`:
  - `generate_vendor_text()` — canonical text from vendor profile + services (pure function)
  - `embed_text()` — Gemini `text-embedding-004` via OpenAI-compatible endpoint
  - `upsert_vendor_embedding()` — SHA-256 staleness check, skips Gemini if unchanged
  - `embed_batch()` — per-vendor error isolation, returns success count
  - `handle_vendor_approved()` — auto-embed on approval
  - `handle_vendor_deactivated()` — delete embedding on reject/suspend
- Domain event handlers registered in lifespan for `vendor.approved/rejected/suspended`
- `SearchService.semantic_search()` — pgvector `<=>` cosine distance query
- `SearchService.hybrid_search()` — weighted fusion: 30% trigram + 70% semantic
- `GET /api/v1/public_vendors/semantic` — natural language search, 60/min rate limit
- `GET /api/v1/public_vendors/search?mode=keyword|semantic|hybrid` — unified search (default: hybrid)
- `POST /api/v1/admin/embeddings/backfill` — admin bulk re-embedding (background task), 10/min rate limit
- `get_http_client` FastAPI dependency in `src/api/deps.py`
- `httpx.AsyncClient` on `app.state` with proper lifecycle (init + aclose in lifespan)
- Settings: `gemini_embedding_model`, `gemini_base_url`, `embedding_dimensions`, `hybrid_trigram_weight`, `hybrid_semantic_weight`
- Tests: 22 unit (EmbeddingService + Hypothesis PBT) + 20 unit (hybrid scoring + PBT) + 22 integration (semantic endpoint) + 12 integration (admin backfill) + 16 integration (hybrid search) = **92 new tests**

#### Admin Dashboard (Module 009-admin) — NEW ✅
- `GET /api/v1/admin/stats` — platform stats (total_users, active_vendors, pending_vendors, total_bookings, confirmed_bookings, pending_bookings, total_revenue) — single DB round-trip via scalar subqueries
- `GET /api/v1/admin/vendors` — paginated vendor list with `status` + `q` filters
- `PATCH /api/v1/admin/vendors/{id}/status` — approve/reject/suspend + domain event emission
- `GET /api/v1/admin/users` — paginated user list with `role` + `q` filters, LEFT JOIN on vendors
- Full integration test suite (stats, vendors, users endpoints)

#### Infrastructure
- Neon PostgreSQL (serverless) with pgvector extension
- Alembic migrations for all tables (reversible `downgrade()` on every migration)
- Structlog structured JSON logging throughout
- `rate_limit_dependency` middleware (in-memory sliding window)
- Event bus (`EventBusService`) with outbox pattern (persists to `domain_events` table)
- CORS configured from `Settings.cors_origins`
- Backend running on port **5000**

### AI Agent Service — `packages/agentic_event_orchestrator` — NEW ✅

#### Agent Pipeline
- `TriageAgent` → `EventPlannerAgent` → `VendorDiscoveryAgent` → `BookingAgent` → `OrchestratorAgent`
- Built with OpenAI Agents SDK + Gemini via LiteLLM (`gemini/gemini-3-flash-preview`)
- `RunConfig(tracing_disabled=True)` — works with Gemini key, no OpenAI tracing

#### Security Stack
- `PromptFirewall` — 3-layer injection detection (YAML blocklist → regex 6 threat categories → heuristics)
- Sandwich defense context builder with canary token injection (MINJA protection)
- `OutputLeakDetector` — canary token + stack trace + internal tool name detection
- `GuardrailService` — SDK-native `@input_guardrail` (blocking) + `@output_guardrail`
- PII redaction on output (email, phone, CNIC patterns)
- Rate limiting: 30 req/min per user

#### Database (ai schema)
- `chat_sessions`, `messages`, `agent_executions`, `message_feedback` tables
- Alembic migration with reversible `downgrade()`

#### Services
- `ChatService` — session management, message persistence, history injection
- `MemoryService` — Mem0 per-user persistent memory with graceful degradation
- `GuardrailService` — input pipeline (rate limit → length → firewall → topic scope)

#### Endpoints (port 8000)
- `POST /api/v1/ai/chat` — non-streaming
- `POST /api/v1/ai/chat/stream` — SSE token-by-token streaming
- `POST /api/v1/ai/feedback` — thumbs up/down per message
- `DELETE /api/v1/ai/memory/{user_id}` — GDPR right-to-forget
- `GET /api/v1/admin/chat/sessions` — paginated session log
- `GET /api/v1/admin/chat/sessions/{id}/messages` — message history
- `GET /api/v1/admin/chat/feedback/stats` — aggregate feedback per agent

#### Tools
- `vendor_tools.py` — `search_vendors`, `get_vendor_details`, `get_vendor_recommendations`
- `booking_tools.py` — `create_booking_request`, `get_my_bookings`, `get_booking_details`, `cancel_booking`
- `event_tools.py` — `get_user_events`, `create_event`, `get_event_details`, `update_event_status`, `query_event_types`
- All tools call backend REST API via `httpx.AsyncClient` — no direct DB access

### Frontend

#### User Portal — `packages/user`
- Next.js 15 App Router
- SSE streaming chat with token-by-token rendering
- Agent badge updates per streaming event
- Thumbs up/down feedback per message
- Session persistence via `localStorage`
- Error handling for SSE connection drops with retry button
- Next.js API proxy for AI service (`/api/ai/[...path]/route.ts`)

#### Vendor Portal — `packages/vendor` — UPDATED ✅
- Login page with email/password + Google OAuth button
- Google OAuth callback page — reads `?token=` from redirect
- Auth store with token refresh interceptor + `_mapUser` / `_mapVendor` field mapping
- Token refresh interceptor: catches 401, retries original request, redirects to `/login` on failure
- Shared `VendorLayout` — sidebar nav (Dashboard, Services, Bookings, Availability, Profile), status badge, logout
- `useSSE` hook — `booking.created/confirmed/cancelled` toasts, exponential backoff reconnect
- All React Query hooks: dashboard, bookings, booking detail, messages, services, availability, profile, notifications, unread count + all mutation hooks
- Dashboard page — stat cards, recent bookings table, skeleton loading, retry on error
- Bookings page — filter tabs, confirm/reject with optimistic updates, reject modal
- Booking Detail page — message thread (vendor right-aligned, customer left-aligned), send message
- Services page — CRUD with React Hook Form + Zod, delete confirmation dialog
- Availability page — monthly calendar grid, day-click modal, optimistic updates, SSE-triggered refresh
- Profile page — pre-populated form, edit/cancel, Zod validation, success toast
- Notifications — bell icon with unread badge, dropdown, mark read, mark all read
- Route guards — unauthenticated → `/login`, authenticated vendor → `/dashboard`
- MSW test infrastructure + 15+ property-based tests + full integration test suite
- Running on port 3002 (dev) / 3001 (Docker)
- **Pending:** Task 23 — `pnpm test` + `pnpm typecheck` final checkpoint

#### Admin Portal — `packages/admin`
- Dashboard with stats cards (users, vendors, bookings, revenue)
- Booking status breakdown with progress bars
- Vendors page with status filter + search + pagination + suspend action
- Users page with role filter + search + pagination
- Settings page with platform info + categories management (create/delete)
- All data via React Query with proper cache invalidation

---

## What Is In Progress 🔄

### Vendor Portal Frontend Checkpoint (vendor-portal-complete spec, task 23)

All pages and features are implemented. The final checkpoint requires:
- `pnpm test` passes with zero failures (15+ property tests + all integration tests)
- `pnpm typecheck` passes with zero TypeScript strict-mode errors
- No `any` types remaining

### AI Agent Security Hardening (ai-agent-chat spec, tasks 5e–5g + 13–17)

**Remaining tasks:**

**5e — Agent Instruction Hardening + AlignmentCheck:**
- Move all agent instruction strings to `agents/instructions.py` as module-level constants
- Add `SECURITY_PREAMBLE` to every agent instruction
- Sync injection trigger phrases from firewall blocklist into TriageAgent instructions
- Startup assertion: each instruction ≤ 800 tokens
- LlamaFirewall `AlignmentCheck` as per-handoff validator (abort if drift ≥ threshold)
- LlamaFirewall `CodeShield` — scan code blocks in responses for SQL injection patterns
- `POST /api/v1/admin/guardrails/test` — live injection probe battery endpoint

**5f — TruLens RAG Faithfulness Evaluation:**
- `TruLensEvaluator` service — RAG Triad (context relevance, groundedness, answer relevance)
- Background evaluation in VendorDiscoveryAgent response path
- `HALLUCINATION_RISK` audit event when groundedness < threshold
- `GET /api/v1/admin/chat/faithfulness` endpoint

**5g — CI Security Testing:**
- `promptfoo.config.yaml` with ≥20 adversarial prompts
- `promptfoo eval` step in CI pipeline
- `.garak.yaml` for weekly red-team runs
- Zero real Gemini calls in all security tests

**13–17 — Test Suites:**
- Unit tests for all tools (vendor, booking, event) with `respx` mocks
- Unit tests for GuardrailService, PromptFirewall, ContextBuilder, OutputLeakDetector
- Hypothesis property-based tests for firewall and guardrail correctness
- Integration tests for chat endpoints (streaming + non-streaming)
- Integration tests for admin and feedback endpoints
- Dependency wiring verification + full smoke test

### Notification System Polish (notification-system spec)

All sub-tasks are fully implemented (tasks 4–10 code complete). Parent task status markers in the spec file show `[-]` (in-progress) rather than `[x]` (complete) — no code changes needed, just a spec file sync.

---

## What Is Not Started ❌

### Module 001 — Spec Generator (Tooling)
Developer tooling — can be built anytime, no dependencies.

---

## Dependency Chain

```
✅ 003 Database
✅ 013 JWT Auth
✅ 002 User Auth + Google OAuth
✅ 004 Vendor Marketplace
✅ 005 Event Management
✅ 009 Booking System
✅ 010 Notification System
✅ 008 Real-Time SSE
✅ 011 RAG & Semantic Search
✅ 006 AI Agent Chat (core)
✅ 009 Admin Dashboard
✅ 012 Vendor Portal (phases 1–2 complete)
🔄 012 Vendor Portal (task 23 — test/typecheck checkpoint)
🔄 006 AI Agent Security Hardening  ← in progress
❌ 001 Spec Generator               ← anytime
```

---

## Port Map

| Service | Port |
|---------|------|
| Backend API | 5000 (dev + Docker) |
| User portal | 3003 (dev) / 3000 (Docker) |
| Vendor portal | 3002 (dev) / 3001 (Docker) |
| Admin portal | 3004 |
| AI orchestrator | 8000 |

---

## Google OAuth Configuration

**Authorized JavaScript origins** (registered in Google Cloud Console):
- `http://localhost:5000`
- `http://localhost:3000`
- `http://localhost:3003`
- `http://localhost:3002`

**Authorized redirect URI:**
- `http://localhost:5000/api/v1/auth/google/callback`

---

## Quick Commands

```bash
# Backend (port 5000)
cd packages/backend
uv run uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload

# AI service (port 8000)
cd packages/agentic_event_orchestrator
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# All portals via Turborepo
pnpm dev

# Run all backend tests (241 passing)
cd packages/backend
uv run pytest -v

# Run specific test file
uv run pytest tests/test_semantic_search.py -v

# Seed database
SEED_ADMIN_EMAIL=admin@eventai.pk SEED_ADMIN_PASSWORD=AdminPass123! \
  uv run python -m src.scripts.seed

# Run migrations
uv run alembic upgrade head

# Admin embedding backfill
curl -X POST http://localhost:5000/api/v1/admin/embeddings/backfill \
  -H "Authorization: Bearer <admin_token>"
```

---

## Environment Variables

```env
# packages/backend/.env
DATABASE_URL=postgresql://...?sslmode=require
DIRECT_URL=postgresql://...?sslmode=require   # migrations only
JWT_SECRET_KEY=<256-bit random>
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
GOOGLE_REDIRECT_URI=http://localhost:5000/api/v1/auth/google/callback
FRONTEND_URL=http://localhost:3003
CORS_ORIGINS=http://localhost:3000,http://localhost:3002,http://localhost:3003,http://localhost:3004
GEMINI_API_KEY=<from Google AI Studio>

# packages/agentic_event_orchestrator/.env
GEMINI_API_KEY=<from Google AI Studio>
GEMINI_MODEL=gemini/gemini-3-flash-preview
AI_SERVICE_API_KEY=<32+ byte random token>
SERVICE_SECRET=<must match AGENT_SERVICE_SECRET in backend .env>
BACKEND_API_URL=http://localhost:5000/api/v1
CORS_ORIGINS=http://localhost:3003
MEM0_API_KEY=<from mem0.ai>

# packages/user/.env
NEXT_PUBLIC_API_URL=http://localhost:5000/api/v1
AI_SERVICE_URL=http://localhost:8000

# packages/vendor/.env / packages/admin/.env
NEXT_PUBLIC_API_URL=http://localhost:5000/api/v1
```
