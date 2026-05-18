# Implementation Plan

## Overview

This plan fixes six compounding defects in `packages/agentic_event_orchestrator` that make the AI chat non-functional for event creation and booking. The workflow follows the exploratory bugfix methodology: write exploration tests first (to confirm bugs exist), write preservation tests (to capture baseline behavior), then implement the fix, and finally verify both test suites pass.

## Task Dependency Graph

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1"] },
    { "wave": 2, "tasks": ["2"] },
    { "wave": 3, "tasks": ["3.1"] },
    { "wave": 4, "tasks": ["3.2"] },
    { "wave": 5, "tasks": ["3.3", "3.4", "3.5"] },
    { "wave": 6, "tasks": ["3.6"] },
    { "wave": 7, "tasks": ["3.7", "3.8"] },
    { "wave": 8, "tasks": ["4"] }
  ]
}
```

## Tasks

- [ ] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Unauthenticated HTTP + Schema Mismatch Bug
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bugs exist
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the six compounding defects exist
  - **Scoped PBT Approach**: Scope the property to the concrete failing cases — `create_event` and `create_booking_request` called with a constructed `RunContext[AgentContext]` carrying a real `AsyncSession` and `user_id`
  - Create `packages/agentic_event_orchestrator/tests/test_properties.py` with Hypothesis-based property tests
  - Create `packages/agentic_event_orchestrator/tests/conftest.py` with the shared `engine`, `db_session`, and `make_ctx` fixtures using `sqlite+aiosqlite:///:memory:`
  - **Property 1 test** — `test_create_event_inserts_correct_row`: seed one `EventType` row; generate event inputs via `st.text(min_size=1)` for name, `st.dates()` for start date, `st.integers(min_value=1, max_value=10000)` for guest count, `st.floats(min_value=0, max_value=10_000_000)` for budget; call `create_event` with `RunContext[AgentContext]`; assert a row is inserted with correct `user_id`, `event_type_id`, and field mapping — this FAILS on unfixed code because the tool makes an unauthenticated HTTP call instead of using `ctx.context.db`
  - **Property 4 test** — `test_query_event_types_returns_real_uuids`: seed N active `EventType` rows via `st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10, unique=True)`; call `query_event_types`; assert all returned `id` values are valid UUIDs matching seeded rows and no hardcoded strings like `"wedding"` appear as IDs — this FAILS on unfixed code because the tool returns a hardcoded static list
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct — it proves the bugs exist)
  - Document counterexamples found (e.g., `create_event` makes HTTP call with no auth, `query_event_types` returns `"id": "wedding"`)
  - Mark task complete when tests are written, run, and failures are documented
  - _Requirements: 1.1, 1.2, 1.7_

- [~] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Vendor HTTP Tools and Pipeline Behavior
  - **IMPORTANT**: Follow observation-first methodology
  - Observe: `search_vendors` on unfixed code makes HTTP calls to `/api/v1/public_vendors/search` and returns vendor results (with dead HMAC headers attached)
  - Observe: `compare_vendors` on unfixed code fetches vendor details and availability concurrently and returns a sorted comparison list
  - Observe: `get_vendor_services` on unfixed code returns active services with pricing from the public vendor endpoint
  - Write property-based tests in `packages/agentic_event_orchestrator/tests/test_properties.py`:
    - **Property 5 test** — `test_get_user_events_isolation`: seed events for two distinct users via `st.integers(min_value=1, max_value=5)` for event count per user; call `get_user_events` with user A's `RunContext[AgentContext]`; assert all returned events have `user_id == A` and no events from user B appear — verify this PASSES on unfixed code (the HTTP path still filters by user via the backend)
    - **Property 6 test** — `test_booking_ownership_enforcement`: generate two distinct user UUIDs; seed a booking for user A; call `get_booking_details` with user B's context; assert error/not-found result — verify this PASSES on unfixed code
    - **Property 7 test** — `test_create_event_unknown_type_returns_error`: generate event type name strings via `st.text(min_size=1)` filtered to exclude any seeded event type names; call `create_event`; assert result contains `"success": false` and non-empty `"error"` — verify this PASSES on unfixed code (HTTP 422 is caught and returned as `{"success": false}`)
    - **Property 8 test** — `test_update_event_status_rejects_invalid_values`: generate invalid status strings via `st.text(min_size=1)` filtered to exclude valid `EventStatus` values; seed an event; call `update_event_status`; assert result contains `"success": false` and DB row status is unchanged
  - Write regression tests in `packages/agentic_event_orchestrator/tests/test_vendor_tools_regression.py`: mock `httpx.AsyncClient`, verify `search_vendors`, `get_vendor_details`, `compare_vendors`, `get_vendor_services` return correct shapes
  - Run all preservation tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9_

- [ ] 3. Fix for six compounding defects in agentic_event_orchestrator

  - [~] 3.1 Create `services/agent_context.py` with `AgentContext` dataclass
    - Create `packages/agentic_event_orchestrator/services/agent_context.py`
    - Define `@dataclasses.dataclass class AgentContext` with `db: AsyncSession` and `user_id: uuid.UUID`
    - Import `uuid`, `dataclasses`, and `sqlalchemy.ext.asyncio.AsyncSession`
    - No Pydantic, no SQLModel — plain dataclass only
    - _Bug_Condition: isBugCondition(input) where tools have no mechanism to receive an authenticated session — `RunContext` pattern was not used_
    - _Expected_Behavior: `AgentContext(db=session, user_id=user_id)` is the sole context type threaded through `RunContext[AgentContext]` into all tool functions_
    - _Preservation: No existing services or pipeline files are modified in this step_
    - _Requirements: 2.10_

  - [~] 3.2 Update `routers/chat.py` to construct and inject `AgentContext`
    - Import `AgentContext` from `services.agent_context` and `RunContextWrapper` from `agents`
    - In both `Runner.run()` and `Runner.run_streamed()` call sites, construct `AgentContext(db=db, user_id=uuid.UUID(user_id))` before the call
    - Pass `context=agent_ctx` kwarg to both `Runner.run()` and `Runner.run_streamed()`
    - Wrap `uuid.UUID(user_id)` conversion in try/except; fall back to `uuid.UUID(int=0)` (nil UUID) if parsing fails
    - All existing guardrail, memory, session, and SSE logic is untouched
    - _Bug_Condition: isBugCondition(input) where `Runner.run()` is called without `context=` kwarg, so tools have no access to the authenticated session_
    - _Expected_Behavior: `Runner.run(triage_agent, input, run_config=run_config, context=agent_ctx)` threads the authenticated session into every tool call_
    - _Preservation: All existing guardrails, Mem0 memory, session persistence, and SSE streaming logic remain unchanged (Requirements 3.6, 3.7, 3.8)_
    - _Requirements: 2.10, 3.6, 3.7, 3.8_

  - [~] 3.3 Rewrite `tools/event_tools.py` to use direct SQLAlchemy DB access
    - Remove `httpx` import entirely
    - Add `ctx: RunContext[AgentContext]` as first parameter to all five tools: `query_event_types`, `create_event`, `get_user_events`, `get_event_details`, `update_event_status`
    - `query_event_types`: execute `SELECT * FROM event_types WHERE is_active = true` via `ctx.context.db`; return real UUIDs and names (fixes Defect 6)
    - `create_event`: perform case-insensitive lookup of `event_type_id` from `event_types` by name; map `eventType→event_type_id (UUID)`, `eventName→name`, `eventDate→start_date (timezone-aware datetime)`, `location→city`, `attendees→guest_count`; INSERT into `events` with `user_id=ctx.context.user_id`; return `{"success": true, "event_id": "<uuid>", "event": {...}}` (fixes Defects 1, 2, 6)
    - `get_user_events`: `SELECT * FROM events WHERE user_id = ctx.context.user_id`
    - `get_event_details`: `SELECT * FROM events WHERE id = event_id AND user_id = ctx.context.user_id`; return not-found error if no match (ownership check)
    - `update_event_status`: validate against `EventStatus` enum; return `{"success": false, "error": "Invalid status 'X'. Must be one of: ..."}` for invalid values; UPDATE record directly in DB
    - All `except` blocks return structured JSON with actionable messages (fixes Defect 4)
    - _Bug_Condition: isBugCondition(input) where `create_event` sends HTTP POST with no auth header and wrong field names (camelCase vs snake_case, string IDs vs UUIDs)_
    - _Expected_Behavior: `create_event` resolves event type name to UUID via direct DB lookup, inserts with correct snake_case fields, returns `{"success": true, "event_id": "<uuid>"}`_
    - _Preservation: `get_user_events`, `get_event_details`, `update_event_status` continue to return correct shapes; user ownership is enforced on all read/write operations (Requirements 2.4, 2.5, 2.6)_
    - _Requirements: 1.1, 1.2, 1.5, 1.7, 2.1, 2.2, 2.4, 2.5, 2.6, 2.7_

  - [~] 3.4 Rewrite `tools/booking_tools.py` to use direct SQLAlchemy DB access
    - Remove `httpx` import entirely
    - Add `ctx: RunContext[AgentContext]` as first parameter to all four tools: `create_booking_request`, `get_my_bookings`, `get_booking_details`, `cancel_booking`
    - `create_booking_request`: look up `service.price_min` from `services` table as `unit_price`; compute `total_price = unit_price * quantity`; map `vendorId→vendor_id`, `serviceId→service_id`, `eventDate→event_date`, `eventName→event_name`, `guestCount→guest_count`; INSERT into `bookings` with all required fields and `user_id=ctx.context.user_id`; return `{"success": true, "booking_id": "<uuid>", "status": "pending"}` (fixes Defects 3, 4)
    - `get_my_bookings`: `SELECT * FROM bookings WHERE user_id = ctx.context.user_id`
    - `get_booking_details`: `SELECT * FROM bookings WHERE id = booking_id AND user_id = ctx.context.user_id`; return not-found error if no match (ownership check)
    - `cancel_booking`: validate booking is not in terminal state (`completed`, `cancelled`, `rejected`, `no_show`); return `{"success": false, "error": "Booking is already in terminal state 'X'..."}` if terminal; UPDATE `status = 'cancelled'` directly in DB
    - All `except` blocks return structured JSON with actionable messages (fixes Defect 4)
    - _Bug_Condition: isBugCondition(input) where `create_booking_request` sends HTTP POST with no auth header, camelCase fields, and missing `unit_price`/`total_price`_
    - _Expected_Behavior: `create_booking_request` looks up `service.price_min`, computes `total_price`, inserts with all required snake_case fields, returns `{"success": true, "booking_id": "<uuid>", "status": "pending"}`_
    - _Preservation: `get_my_bookings`, `get_booking_details`, `cancel_booking` continue to return correct shapes; user ownership enforced; terminal state validation preserved (Requirements 2.8, 3.5)_
    - _Requirements: 1.3, 1.4, 1.5, 2.3, 2.8, 3.5_

  - [~] 3.5 Strip dead HMAC headers from public vendor endpoints in `tools/vendor_tools.py`
    - Remove `make_service_headers(...)` from HTTP calls in `search_vendors`, `get_vendor_details`, `check_vendor_availability`, and `_fetch_vendor_details` (internal helper used by `compare_vendors`) — all call `/api/v1/public_vendors/*` which has no HMAC verification middleware (fixes Defect 5)
    - `get_vendor_recommendations` — already had no HMAC, no change needed
    - `_fetch_vendor_availability` — **retain** `make_service_headers()` because it calls `/api/v1/vendors/{id}/availability` (non-public, authenticated endpoint)
    - `compare_vendors` and `get_vendor_services` — unchanged
    - _Bug_Condition: isBugCondition(input) where `search_vendors`, `get_vendor_details`, `check_vendor_availability` attach dead HMAC headers to public endpoints that have no HMAC verification middleware_
    - _Expected_Behavior: Public endpoint calls send HTTP requests without HMAC headers; `_fetch_vendor_availability` retains HMAC for the non-public endpoint_
    - _Preservation: All four vendor tools continue to return correct shapes from the backend public search endpoint (Requirements 3.1, 3.2, 3.3)_
    - _Requirements: 1.6, 2.9, 3.1, 3.2, 3.3_

  - [~] 3.6 Update `pipeline/booking.py` wrapper to accept and forward `ctx`
    - Update the `create_booking_request` wrapper function signature to accept `ctx: RunContext[AgentContext]` as first parameter
    - Forward `ctx=ctx` to the underlying `_create_booking_request(ctx=ctx, ...)` call
    - All existing guardrails (`tool_injection_guard`, `tool_pii_redact`) remain in place and continue to fire
    - _Bug_Condition: isBugCondition(input) where the pipeline wrapper does not forward `RunContext` to the underlying tool, breaking the context injection chain_
    - _Expected_Behavior: The wrapper correctly forwards `ctx` so the underlying tool can access `ctx.context.db` and `ctx.context.user_id`_
    - _Preservation: `tool_injection_guard` and `tool_pii_redact` guardrails continue to fire on all booking tool calls (Requirements 3.6)_
    - _Requirements: 2.10, 3.6_

  - [~] 3.7 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Unauthenticated HTTP + Schema Mismatch Bug
    - **IMPORTANT**: Re-run the SAME tests from task 1 — do NOT write new tests
    - The tests from task 1 encode the expected behavior
    - When these tests pass, it confirms the expected behavior is satisfied
    - Re-run `test_create_event_inserts_correct_row` and `test_query_event_types_returns_real_uuids` from task 1
    - **EXPECTED OUTCOME**: Tests PASS (confirms bugs are fixed — direct DB access works, real UUIDs returned)
    - _Requirements: 1.1, 1.2, 1.7, 2.1, 2.2, 2.7_

  - [~] 3.8 Verify preservation tests still pass
    - **Property 2: Preservation** - Vendor HTTP Tools and Pipeline Behavior
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run all preservation property tests from step 2: `test_get_user_events_isolation`, `test_booking_ownership_enforcement`, `test_create_event_unknown_type_returns_error`, `test_update_event_status_rejects_invalid_values`, and all vendor regression tests
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions — vendor HTTP tools still work, ownership enforced, error handling correct)
    - Confirm all tests still pass after fix (no regressions)

- [~] 4. Checkpoint — Ensure all tests pass
  - Run the full test suite: `cd packages/agentic_event_orchestrator && uv run pytest tests/ -v`
  - Ensure all property-based tests pass (Properties 1–8 from design)
  - Ensure all vendor regression tests pass
  - Ensure all booking pipeline wrapper tests pass
  - Verify no import errors (httpx removed from event_tools and booking_tools, AgentContext importable from services.agent_context)
  - Ensure all tests pass; ask the user if questions arise

## Notes

- Tests use `sqlite+aiosqlite:///:memory:` — no Neon, no Docker required
- Run tests from `packages/agentic_event_orchestrator`: `uv run pytest tests/ -v`
- Property-based tests use Hypothesis with minimum 100 iterations per property
- Tasks 1 and 2 MUST be completed before any implementation in task 3
- The exploration test (task 1) is expected to FAIL on unfixed code — this is correct behavior
- The preservation tests (task 2) are expected to PASS on unfixed code — this establishes the baseline
- No real LLM calls in tests — tools are called directly with a constructed `RunContext[AgentContext]`
- `pipeline/event_planner.py`, `pipeline/__init__.py`, `pipeline/triage.py`, `pipeline/orchestrator.py`, and `pipeline/vendor_discovery.py` are unchanged
