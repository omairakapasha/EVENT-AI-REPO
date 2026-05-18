# Design Document: Agentic Orchestrator Chat Fix

## Overview

The AI chat system in `packages/agentic_event_orchestrator` is non-functional for event creation and booking due to six compounding defects. All event and booking tools make unauthenticated HTTP calls to the backend, which returns 401 responses that are silently swallowed. Even if auth were present, the payloads use wrong field names (camelCase vs snake_case), wrong types, and omit required pricing fields. Tool errors are returned as opaque `{"success": false}` JSON strings the LLM cannot act on. Vendor tools attach dead HMAC headers to public endpoints. And `query_event_types` returns hardcoded fake UUIDs instead of real database rows.

The fix eliminates the HTTP layer entirely for event and booking tools by replacing it with direct SQLAlchemy database access via the OpenAI Agents SDK `RunContext[AgentContext]` pattern. Vendor tools are corrected by stripping dead HMAC headers from public-endpoint calls. The `AgentContext` dataclass threads the authenticated `AsyncSession` and `user_id` from the chat router through to every tool call, eliminating the auth problem at its root.

## Bug Details

Six compounding defects in `packages/agentic_event_orchestrator`:

**Defect 1 — Unauthenticated HTTP calls (event tools):** `event_tools.py` uses `httpx.AsyncClient` with no `Authorization` header. The backend returns 401, which is caught by the bare `except Exception` block and returned as `{"success": false, "error": "HTTP 401"}`. The LLM receives this as a completed tool call and produces no further action.

**Defect 2 — Wrong field names/types in `create_event`:** The tool sends `{"eventType": "wedding", "eventName": "...", "eventDate": "2026-10-01", "location": "Lahore", "attendees": 200}`. The backend `EventCreate` schema expects `{"event_type_id": "<uuid>", "name": "...", "start_date": "2026-10-01T00:00:00+05:00", "city": "Lahore", "guest_count": 200}`. This produces a 422 even if auth were present.

**Defect 3 — Unauthenticated HTTP calls + wrong fields (booking tools):** `booking_tools.py` sends `{"vendorId": ..., "serviceId": ..., "eventDate": ..., "eventName": ..., "guestCount": 100}` with no auth header. The backend `BookingCreate` schema requires snake_case fields plus mandatory `unit_price` and `total_price`. Both 401 and 422 errors are silently swallowed.

**Defect 4 — Errors swallowed as opaque JSON strings:** All tool `except` blocks return `{"success": false, "error": "..."}` as a JSON string. The LLM interprets this as a successful tool call with a failure payload and takes no corrective action, leaving the chat stuck.

**Defect 5 — Dead HMAC headers on public vendor endpoints:** `search_vendors`, `get_vendor_details`, and `check_vendor_availability` call `make_service_headers()` for public endpoints (`/api/v1/public_vendors/*`) that have no HMAC verification middleware. The headers are dead code that adds unnecessary complexity and could cause confusion.

**Defect 6 — `query_event_types` returns hardcoded fake UUIDs:** The tool returns a static list with string IDs like `"id": "wedding"` instead of querying the `event_types` table. This makes it impossible to resolve a valid `event_type_id` UUID for event creation.

## Hypothesized Root Cause

The root cause is an architectural mismatch: the tools were written as if they were standalone microservice clients, but the orchestrator and backend share the same database. There is no mechanism to pass the authenticated user's session or identity into tool functions — the OpenAI Agents SDK `RunContext` pattern was not used. This forced the tools to make HTTP calls with no way to attach a user JWT, and the schema mismatches accumulated because the tool payloads were never validated against the actual SQLModel definitions.

The secondary cause is that the `except Exception` catch-all pattern converts all failures into opaque success-shaped JSON, removing the LLM's ability to distinguish between a completed action and a failed one.

## Expected Behavior

After the fix:

- `create_event` resolves the event type name to a UUID via direct DB lookup, inserts into `events` with correct snake_case fields, and returns `{"success": true, "event_id": "<uuid>"}`.
- `create_booking_request` looks up `service.price_min`, computes `total_price`, inserts into `bookings` with all required fields, and returns `{"success": true, "booking_id": "<uuid>", "status": "pending"}`.
- `query_event_types` queries `event_types WHERE is_active = true` and returns real UUIDs.
- All event and booking tools use `ctx.context.db` (AsyncSession) and `ctx.context.user_id` from `RunContext[AgentContext]`.
- `search_vendors`, `get_vendor_details`, `check_vendor_availability` make HTTP calls to public endpoints without HMAC headers.
- Tool errors return structured JSON with actionable messages the LLM can use to ask the user for corrections.

## Fix Implementation

The fix touches six files and adds one new file:

1. **New `services/agent_context.py`** — `AgentContext` dataclass with `db: AsyncSession` and `user_id: uuid.UUID`.
2. **`routers/chat.py`** — construct `AgentContext` and pass as `context=` to `Runner.run()` and `Runner.run_streamed()`.
3. **`tools/event_tools.py`** — rewrite all 5 tools to use `ctx: RunContext[AgentContext]` with direct SQLAlchemy queries.
4. **`tools/booking_tools.py`** — rewrite all 4 tools to use `ctx: RunContext[AgentContext]` with direct SQLAlchemy queries.
5. **`tools/vendor_tools.py`** — strip `make_service_headers()` from 4 public-endpoint calls; retain on `_fetch_vendor_availability`.
6. **`pipeline/booking.py`** — update wrapper to accept and forward `ctx: RunContext[AgentContext]`.

## Architecture

### Current (Broken) Architecture

```
Chat Router
    │
    ▼
Runner.run(triage_agent, input, run_config=run_config)
    │                                    ▲
    │                                    │ no context=
    ▼                                    │
EventPlannerAgent / BookingAgent
    │
    ▼
event_tools.py / booking_tools.py
    │
    ▼  httpx (no auth header)
Backend REST API ──→ 401 / 422 silently swallowed
```

### Fixed Architecture

```
Chat Router
    │
    ├── AgentContext(db=session, user_id=user_id)
    │
    ▼
Runner.run(triage_agent, input, run_config=run_config, context=agent_ctx)
    │
    ▼
EventPlannerAgent / BookingAgent
    │
    ▼
event_tools.py / booking_tools.py
    │  ctx: RunContext[AgentContext]
    ▼
ctx.context.db (AsyncSession) ──→ Direct DB queries (no HTTP)
ctx.context.user_id            ──→ Ownership checks

VendorDiscoveryAgent
    │
    ▼
vendor_tools.py
    │  HTTP (no HMAC on public endpoints)
    ▼
Backend /api/v1/public_vendors/* (no auth required)
```

### Key Design Decisions

**Direct DB access over HTTP for event/booking tools.** The orchestrator and backend share the same Neon PostgreSQL database. Bypassing HTTP eliminates the auth problem entirely, removes the schema mismatch surface, and makes tool calls faster and more reliable. Vendor tools remain HTTP-based because vendor data is served by the backend and the public endpoints require no auth.

**`AgentContext` dataclass as the context carrier.** The OpenAI Agents SDK's `RunContext[T]` pattern is the idiomatic way to thread request-scoped state (DB session, user identity) into tool functions without global state or environment variables. The `context=` kwarg on `Runner.run()` and `Runner.run_streamed()` is the injection point.

**`pipeline/booking.py` wrapper passes `ctx` through.** The `create_booking_request` wrapper in `pipeline/booking.py` applies tool-level guardrails (`tool_injection_guard`, `tool_pii_redact`) and must forward the `RunContext` to the underlying tool function. The wrapper signature is updated to accept `ctx: RunContext[AgentContext]` and pass it through.

**HMAC stripped from public vendor endpoints only.** `_fetch_vendor_availability` calls `/api/v1/vendors/{id}/availability` (a non-public, authenticated endpoint) and retains HMAC. The four public-endpoint tools (`search_vendors`, `get_vendor_details`, `check_vendor_availability`, `get_vendor_recommendations`) have HMAC removed. `compare_vendors` and `get_vendor_services` are unchanged.

## Components and Interfaces

### New: `services/agent_context.py`

```python
import uuid
import dataclasses
from sqlalchemy.ext.asyncio import AsyncSession

@dataclasses.dataclass
class AgentContext:
    db: AsyncSession
    user_id: uuid.UUID
```

This is the sole context type threaded through `RunContext[AgentContext]`. It is a plain dataclass — no Pydantic, no SQLModel — because the SDK's `RunContext` wrapper handles serialization.

### Modified: `routers/chat.py`

Two changes only:

1. Import `AgentContext` from `services.agent_context` and `RunContext` from `agents`.
2. Construct `AgentContext(db=db, user_id=uuid.UUID(user_id))` before each `Runner.run()` / `Runner.run_streamed()` call and pass it as `context=agent_ctx`.

The `_get_user_id` helper already extracts a 32-char hex string from the JWT or `X-User-Id` header. This is converted to a proper `uuid.UUID` when constructing `AgentContext`. If the string is not a valid UUID (e.g. the fallback `"0" * 32`), the conversion produces `UUID('00000000-0000-0000-0000-000000000000')` which is safe — no DB rows will match it.

All existing guardrail, memory, session, and SSE logic is untouched.

### Modified: `tools/event_tools.py`

All five tools are rewritten to accept `ctx: RunContext[AgentContext]` as their first parameter and use `ctx.context.db` for all database operations and `ctx.context.user_id` for ownership checks. The `httpx` import is removed entirely.

| Tool | DB operation |
|---|---|
| `query_event_types` | `SELECT * FROM event_types WHERE is_active = true` |
| `create_event` | Case-insensitive lookup of `event_type_id` from `event_types`, then `INSERT INTO events` |
| `get_user_events` | `SELECT * FROM events WHERE user_id = ctx.context.user_id` |
| `get_event_details` | `SELECT * FROM events WHERE id = event_id AND user_id = ctx.context.user_id` |
| `update_event_status` | Validate against `EventStatus` enum, then `UPDATE events SET status = ...` |

`create_event` field mapping (old → new):

| Old (broken) | New (correct) |
|---|---|
| `eventType: str` | resolved to `event_type_id: UUID` via case-insensitive lookup |
| `eventName: str` | `name: str` |
| `eventDate: str` | `start_date: datetime` (parsed from ISO-8601, timezone-aware) |
| `location: str` | `city: str` |
| `attendees: int` | `guest_count: int` |
| `budget: float` | `budget: float` |

### Modified: `tools/booking_tools.py`

All four tools are rewritten to accept `ctx: RunContext[AgentContext]` and use direct DB access. The `httpx` import is removed.

| Tool | DB operation |
|---|---|
| `create_booking_request` | Lookup `service.price_min` → `unit_price`, compute `total_price = unit_price * quantity`, `INSERT INTO bookings` |
| `get_my_bookings` | `SELECT * FROM bookings WHERE user_id = ctx.context.user_id` |
| `get_booking_details` | `SELECT * FROM bookings WHERE id = booking_id AND user_id = ctx.context.user_id` |
| `cancel_booking` | Validate terminal state, `UPDATE bookings SET status = 'cancelled'` |

`create_booking_request` field mapping (old → new):

| Old (broken) | New (correct) |
|---|---|
| `vendorId` | `vendor_id` |
| `serviceId` | `service_id` |
| `eventDate` | `event_date` |
| `eventName` | `event_name` |
| `guestCount` | `guest_count` |
| *(missing)* | `unit_price` (from `service.price_min`) |
| *(missing)* | `total_price` (`unit_price * quantity`) |

### Modified: `tools/vendor_tools.py`

Four tools have `make_service_headers(...)` removed from their HTTP calls:

- `search_vendors` — calls `/api/v1/public_vendors/search` (public)
- `get_vendor_details` — calls `/api/v1/public_vendors/{vendor_id}` (public)
- `check_vendor_availability` — calls `/api/v1/vendors/{vendor_id}/availability` (public)
- `get_vendor_recommendations` — calls `/api/v1/public_vendors/search` (already had no HMAC, no change needed)

`_fetch_vendor_details` (internal helper used by `compare_vendors`) also has HMAC removed since it calls the same public endpoint.

`_fetch_vendor_availability` (internal helper) **retains** HMAC because it calls `/api/v1/vendors/{id}/availability` which is a non-public endpoint.

`compare_vendors` and `get_vendor_services` are unchanged.

### Modified: `pipeline/booking.py`

The `create_booking_request` wrapper function is updated to accept and forward `ctx: RunContext[AgentContext]`:

```python
@function_tool(
    tool_input_guardrails=[tool_injection_guard],
    tool_output_guardrails=[tool_pii_redact],
)
async def create_booking_request(
    ctx: RunContext[AgentContext],
    vendor_id: str,
    service_id: str,
    event_date: str,
    event_name: str,
    guest_count: int,
    notes: str = "",
) -> str:
    return await _create_booking_request(
        ctx=ctx,
        vendor_id=vendor_id,
        ...
    )
```

### Unchanged: `pipeline/event_planner.py`

No structural change needed. The `EventPlannerAgent` already lists the five event tools. Once those tools accept `RunContext[AgentContext]`, the SDK automatically injects the context.

### Unchanged: `pipeline/__init__.py`, `pipeline/triage.py`, `pipeline/orchestrator.py`, `pipeline/vendor_discovery.py`

The pipeline topology is unchanged. `build_pipeline(model)` remains the sole entry point.

## Data Models

### `AgentContext` (new)

```python
@dataclasses.dataclass
class AgentContext:
    db: AsyncSession       # sqlalchemy.ext.asyncio.AsyncSession
    user_id: uuid.UUID     # authenticated user from JWT / X-User-Id header
```

### `EventType` (existing, read-only from orchestrator)

```
event_types
  id          UUID PK
  name        str (unique, case-insensitive lookup target)
  is_active   bool
```

### `Event` (existing, written by orchestrator)

```
events
  id              UUID PK (generated)
  user_id         UUID FK → users.id
  event_type_id   UUID FK → event_types.id
  name            str
  start_date      DateTime(timezone=True)
  city            str (optional)
  guest_count     int (optional)
  budget          float (optional)
  status          EventStatus enum (default: draft)
```

### `Booking` (existing, written by orchestrator)

```
bookings
  id            UUID PK (generated)
  vendor_id     UUID FK → vendors.id
  service_id    UUID FK → services.id
  user_id       UUID FK → users.id
  event_date    date
  event_name    str (optional)
  guest_count   int (optional)
  unit_price    float (required — from service.price_min)
  total_price   float (required — unit_price * quantity)
  quantity      int (default: 1)
  notes         str (optional)
  status        BookingStatus (default: pending)
```

### `Service` (existing, read-only from orchestrator)

```
services
  id          UUID PK
  vendor_id   UUID FK → vendors.id
  price_min   float
  price_max   float
  is_active   bool
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

**Property Reflection:** Properties from 1.1/2.1 merged into Property 1; 1.2/2.2 merged into Property 2; 1.3/1.4/2.3 merged into Property 3; 1.7/2.7 merged into Property 4. Properties 2.4 and 2.8 kept separate (different tables). Properties 1.5 and 2.6 kept as Properties 7 and 8 respectively.

---

### Property 1: create_event inserts a row with correct fields

*For any* valid combination of event type name, event name, ISO-8601 date string, city, guest count, and budget, calling `create_event` with a `RunContext[AgentContext]` carrying a real `AsyncSession` SHALL insert exactly one row into the `events` table with `user_id` matching `ctx.context.user_id`, `event_type_id` matching the resolved UUID from `event_types`, and all other fields correctly mapped from the tool arguments.

**Validates: Requirements 1.1, 2.1**

---

### Property 2: Event type name lookup is case-insensitive

*For any* event type name that exists in the `event_types` table, calling `create_event` with that name in any casing (lowercase, uppercase, mixed) SHALL resolve to the same `event_type_id` UUID and succeed.

**Validates: Requirements 1.2, 2.2**

---

### Property 3: create_booking_request inserts a row with correct pricing

*For any* valid `service_id` with a known `price_min` and any `quantity` ≥ 1, calling `create_booking_request` with a `RunContext[AgentContext]` SHALL insert exactly one row into the `bookings` table where `unit_price = service.price_min` and `total_price = unit_price * quantity`.

**Validates: Requirements 1.3, 1.4, 2.3**

---

### Property 4: query_event_types returns real database rows

*For any* set of active event types seeded in the `event_types` table, calling `query_event_types` with a `RunContext[AgentContext]` SHALL return a list where every `id` is a valid UUID matching a real row in `event_types` and no hardcoded fake IDs are present.

**Validates: Requirements 1.7, 2.7**

---

### Property 5: `get_user_events` returns only the requesting user's events

*For any* two distinct users A and B, each with one or more events in the `events` table, calling `get_user_events` with user A's `RunContext[AgentContext]` SHALL return only events where `user_id = A` and SHALL NOT return any event belonging to user B.

**Validates: Requirements 2.4**

---

### Property 6: Booking tools enforce user ownership

*For any* booking belonging to user A, calling `get_booking_details` or `cancel_booking` with user B's `RunContext[AgentContext]` (where B ≠ A) SHALL return a not-found or error result and SHALL NOT expose or modify user A's booking data.

**Validates: Requirements 2.5, 2.8**

---

### Property 7: create_event returns a structured error for unknown event types

*For any* event type name string that does not exist in the `event_types` table, calling `create_event` SHALL return a JSON string containing `"success": false` and a non-empty `"error"` field describing the failure, rather than silently inserting a row with a null or invalid `event_type_id`.

**Validates: Requirements 1.5, 2.1**

---

### Property 8: update_event_status rejects invalid status values

*For any* string that is not a member of the `EventStatus` enum (`draft`, `planned`, `active`, `completed`, `canceled`), calling `update_event_status` SHALL return a JSON string containing `"success": false` and SHALL NOT modify the event row in the database.

**Validates: Requirements 2.6**

## Error Handling

### Event type not found

When `create_event` receives an event type name that has no match in `event_types` (case-insensitive), the tool returns:

```json
{"success": false, "error": "Event type 'X' not found. Available types: wedding, birthday, ..."}
```

This gives the LLM actionable information to ask the user for a valid event type.

### Service not found for booking

When `create_booking_request` receives a `service_id` that does not exist or is inactive, the tool returns:

```json
{"success": false, "error": "Service not found or unavailable"}
```

### Ownership violation

When `get_event_details`, `get_booking_details`, or `cancel_booking` is called with an ID that exists but belongs to a different user, the tool returns a not-found error (same as if the record didn't exist) to avoid leaking existence information:

```json
{"error": "Event/Booking not found"}
```

### Invalid status transition

When `update_event_status` receives a status string not in `EventStatus`, the tool returns:

```json
{"success": false, "error": "Invalid status 'X'. Must be one of: draft, planned, active, completed, canceled"}
```

When `cancel_booking` is called on a booking already in a terminal state (`completed`, `cancelled`, `rejected`, `no_show`), the tool returns:

```json
{"success": false, "error": "Booking is already in terminal state 'X' and cannot be cancelled"}
```

### Database errors

All tool functions wrap their DB operations in `try/except Exception`. On unexpected DB errors, the tool returns a structured error JSON with a generic message and logs the full exception at `ERROR` level. This ensures the LLM always receives a parseable JSON string rather than a Python traceback.

### UUID parsing for user_id

In `routers/chat.py`, the `_get_user_id` helper may return a 32-char hex string (from the SHA-256 fallback path) that is not a standard UUID format. The `AgentContext` constructor wraps the conversion in a try/except and falls back to `uuid.UUID(int=0)` (the nil UUID) if parsing fails. No DB rows will match the nil UUID, so ownership checks will correctly return not-found for unauthenticated requests.

## Testing Strategy

### Test framework

- `pytest` + `pytest-asyncio` (already in use in `packages/backend`)
- `sqlite+aiosqlite:///:memory:` for in-memory DB (no Neon, no Docker)
- No real LLM calls — tools are called directly with a constructed `RunContext[AgentContext]`
- Property-based testing via **Hypothesis** (Python's standard PBT library)

### Unit tests (example-based)

Located in `packages/agentic_event_orchestrator/tests/`:

- `test_agent_context.py` — verify `AgentContext` dataclass construction and UUID fallback
- `test_vendor_tools.py` — mock HTTP client, verify HMAC headers absent from public endpoint calls, verify `_fetch_vendor_availability` retains HMAC
- `test_chat_router_context.py` — verify `Runner.run` is called with `context=AgentContext(...)` kwarg (mock `Runner.run`)

### Property-based tests (Hypothesis)

Located in `packages/agentic_event_orchestrator/tests/test_properties.py`:

Each property test:
- Uses `@given` from Hypothesis with appropriate strategies
- Runs minimum 100 iterations (Hypothesis default)
- Tags the test with a comment referencing the design property
- Uses an in-memory SQLite session via a shared `pytest-asyncio` fixture

**Property 1 test** — `test_create_event_inserts_correct_row`
- Strategy: `st.text(min_size=1)` for event name, `st.dates()` for start date, `st.integers(min_value=1, max_value=10000)` for guest count, `st.floats(min_value=0, max_value=10_000_000)` for budget
- Seed one `EventType` row before each run; generate event inputs; call `create_event`; assert row exists with correct fields
- Tag: `# Feature: agentic-orchestrator-chat-fix, Property 1: create_event inserts a row with correct fields`

**Property 2 test** — `test_event_type_lookup_case_insensitive`
- Strategy: `st.sampled_from(["wedding", "birthday", "corporate"])` then `st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll")))` applied to vary casing
- Seed event types; call `create_event` with varied casing; assert same `event_type_id` UUID each time
- Tag: `# Feature: agentic-orchestrator-chat-fix, Property 2: event type name lookup is case-insensitive`

**Property 3 test** — `test_create_booking_request_pricing_invariant`
- Strategy: `st.floats(min_value=0.01, max_value=1_000_000)` for `price_min`, `st.integers(min_value=1, max_value=100)` for quantity
- Seed a `Service` row with the generated `price_min`; call `create_booking_request`; assert `total_price == unit_price * quantity`
- Tag: `# Feature: agentic-orchestrator-chat-fix, Property 3: create_booking_request inserts a row with correct pricing`

**Property 4 test** — `test_query_event_types_returns_real_uuids`
- Strategy: `st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10, unique=True)` for event type names
- Seed N active `EventType` rows; call `query_event_types`; assert all returned IDs are valid UUIDs matching seeded rows; assert no hardcoded strings like `"wedding"` appear as IDs
- Tag: `# Feature: agentic-orchestrator-chat-fix, Property 4: query_event_types returns real database rows`

**Property 5 test** — `test_get_user_events_isolation`
- Strategy: `st.integers(min_value=1, max_value=5)` for number of events per user
- Seed events for two distinct users; call `get_user_events` for user A; assert all returned events have `user_id == A`; assert no events from user B appear
- Tag: `# Feature: agentic-orchestrator-chat-fix, Property 5: get_user_events returns only the requesting user's events`

**Property 6 test** — `test_booking_ownership_enforcement`
- Strategy: generate two distinct user UUIDs
- Seed a booking for user A; call `get_booking_details` with user B's context; assert error/not-found result
- Tag: `# Feature: agentic-orchestrator-chat-fix, Property 6: booking tools enforce user ownership`

**Property 7 test** — `test_create_event_unknown_type_returns_error`
- Strategy: `st.text(min_size=1)` filtered to exclude any seeded event type names
- Call `create_event` with unknown type name; assert result contains `"success": false` and non-empty `"error"`
- Tag: `# Feature: agentic-orchestrator-chat-fix, Property 7: create_event raises a structured error for unknown event types`

**Property 8 test** — `test_update_event_status_rejects_invalid_values`
- Strategy: `st.text(min_size=1)` filtered to exclude valid `EventStatus` values
- Seed an event; call `update_event_status` with invalid status; assert result contains `"success": false`; assert DB row status is unchanged
- Tag: `# Feature: agentic-orchestrator-chat-fix, Property 8: update_event_status rejects invalid status values`

### Integration tests (regression)

- `test_vendor_tools_regression.py` — mock `httpx.AsyncClient`, verify `search_vendors`, `get_vendor_details`, `compare_vendors`, `get_vendor_services` still return correct shapes
- `test_booking_pipeline_wrapper.py` — verify the `pipeline/booking.py` wrapper correctly forwards `ctx` to the underlying tool and that guardrails still fire

### Test fixture pattern

```python
# conftest.py (agentic_event_orchestrator/tests/)
import pytest
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel
from agents import RunContextWrapper
from services.agent_context import AgentContext

@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(engine):
    async with async_sessionmaker(engine, class_=AsyncSession)() as session:
        yield session
        await session.rollback()

@pytest.fixture
def make_ctx(db_session):
    def _make(user_id: uuid.UUID = None):
        uid = user_id or uuid.uuid4()
        ctx = AgentContext(db=db_session, user_id=uid)
        return RunContextWrapper(context=ctx)
    return _make
```

## Glossary

| Term | Definition |
|---|---|
| `AgentContext` | New dataclass in `services/agent_context.py` carrying `db: AsyncSession` and `user_id: uuid.UUID` for use in tool functions |
| `RunContext[T]` | OpenAI Agents SDK wrapper that carries request-scoped context into `@function_tool` functions via the `ctx` parameter |
| `context=` kwarg | The `Runner.run()` / `Runner.run_streamed()` parameter that injects an `AgentContext` instance into the agent run |
| HMAC | Hash-based Message Authentication Code — the signing scheme used by `make_service_headers()` for service-to-service auth |
| Public vendor endpoint | `/api/v1/public_vendors/*` routes that require no authentication and no HMAC verification |
| `EventStatus` | Enum with values `draft`, `planned`, `active`, `completed`, `canceled` — the only valid values for `events.status` |
| `BookingStatus` | Enum with values `pending`, `confirmed`, `in_progress`, `completed`, `cancelled`, `rejected`, `no_show` |
| `unit_price` | The per-unit price for a booking, sourced from `services.price_min` |
| `total_price` | Computed as `unit_price * quantity` — required field on the `bookings` table |
| `event_type_id` | UUID foreign key on `events` referencing `event_types.id` — resolved from a human-readable name via case-insensitive lookup |
