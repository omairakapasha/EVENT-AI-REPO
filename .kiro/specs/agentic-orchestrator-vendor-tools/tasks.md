# Implementation Plan: agentic-orchestrator-vendor-tools

## Overview

Extend `packages/agentic_event_orchestrator` with three new `@function_tool` definitions (`check_vendor_availability`, `get_vendor_services`, `compare_vendors`), upgrade `search_vendors` with a configurable `mode` parameter and service-auth headers, add auth headers to `get_vendor_details`, wire all new tools into the correct agents, update instruction strings, and write property-based tests using `hypothesis` + `respx`.

All changes are confined to `packages/agentic_event_orchestrator`. No backend schema changes are required.

## Tasks

- [x] 1. Add internal helper functions to `tools/vendor_tools.py`
  - Add `async def _fetch_vendor_details(vendor_id: str, backend_url: str) -> dict` — raw GET to `/api/v1/public_vendors/{vendor_id}` with `make_service_headers`; returns parsed `data` dict or `{}` on any failure; no `@function_tool` decorator
  - Add `async def _fetch_vendor_availability(vendor_id: str, event_date: str, backend_url: str) -> bool` — raw GET to `/api/v1/vendors/{vendor_id}/availability` with `start_date=event_date`, `end_date=event_date`, and `make_service_headers`; returns `True` if slots list is non-empty, `False` on any failure
  - Import `service_auth` at the top of `vendor_tools.py` (`from service_auth import make_service_headers`)
  - Import `asyncio` and `datetime` (needed by later tasks)
  - _Requirements: 7.1, 7.2, 1.2, 2.2_

- [x] 2. Upgrade `search_vendors` in `tools/vendor_tools.py`
  - [x] 2.1 Add `mode: str = "hybrid"` parameter to `search_vendors` signature and docstring
    - Update docstring to mention `mode="semantic"` for descriptive queries, `mode="keyword"` for category/name, `mode="hybrid"` as default
    - Pass `mode` as a query parameter to the backend (`params["mode"] = mode`)
    - Merge `make_service_headers("GET", "/api/v1/public_vendors/search")` into the `httpx.AsyncClient` request headers
    - Handle 503 response with `error.code == "AI_EMBEDDING_UNAVAILABLE"`: return `{"vendors": [], "error": "Semantic search is temporarily unavailable. Please try keyword or hybrid search."}`
    - Handle 401/403: return `{"vendors": [], "error": "Service authentication failed. Check SERVICE_SECRET configuration."}`
    - Handle other non-200: return `{"vendors": [], "error": "Vendor service temporarily unavailable (HTTP <status>)"}`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 7.5, 7.8, 8.2_

  - [ ]* 2.2 Write property test: `test_mode_param_passed_to_backend` (Property 8)
    - **Property 8: `search_vendors` passes mode parameter to backend**
    - Use `@given(mode=st.sampled_from(["keyword", "semantic", "hybrid"]))` with `respx.mock`
    - Assert the captured request URL contains `mode=<value>` as a query parameter
    - **Validates: Requirements 4.2**

  - [ ]* 2.3 Write property test: `test_search_vendors_auth_headers_present` (Property 1)
    - **Property 1: service auth headers present on every outbound request**
    - Use `@given(event_type=st.text(min_size=1), location=st.text(min_size=1))` with `respx.mock` returning 200
    - Assert `X-Service-Timestamp`, `X-Service-Signature`, `X-Service-Name` all present in captured request headers
    - **Validates: Requirements 7.1, 7.2, 7.5**

  - [ ]* 2.4 Write property test: `test_search_vendors_always_returns_valid_json` (Property 2)
    - **Property 2: tools always return valid JSON for any backend response**
    - Use `@given(status_code=st.integers(min_value=400, max_value=599))` with `respx.mock`
    - Call `await search_vendors(event_type="wedding", location="Lahore")` and assert `json.loads(result)` does not raise
    - **Validates: Requirements 8.4, 4.5**

  - [ ]* 2.5 Write property test: `test_search_vendors_non_200_returns_error_and_empty_vendors` (Property 3)
    - **Property 3: non-200 responses always produce an error field and empty result list**
    - Use `@given(status_code=st.integers(min_value=400, max_value=599).filter(lambda s: s not in (401, 403, 503)))` with `respx.mock`
    - Assert returned JSON has `"error"` key (non-empty string) and `"vendors"` is `[]`
    - **Validates: Requirements 4.5, 8.2**

  - [ ]* 2.6 Write unit test: `test_semantic_503_returns_specific_message`
    - Mock backend returning 503 with `{"error": {"code": "AI_EMBEDDING_UNAVAILABLE", "message": "..."}}`
    - Assert returned JSON `error` equals `"Semantic search is temporarily unavailable. Please try keyword or hybrid search."`
    - _Requirements: 4.4_

  - [ ]* 2.7 Write unit test: `test_search_vendors_401_403_returns_auth_failure_message` (Property 9)
    - **Property 9: 401/403 responses produce the specific auth failure message**
    - Mock 401 and 403 responses; assert `error == "Service authentication failed. Check SERVICE_SECRET configuration."`
    - **Validates: Requirements 7.8**

- [x] 3. Upgrade `get_vendor_details` in `tools/vendor_tools.py`
  - Merge `make_service_headers("GET", f"/api/v1/public_vendors/{vendor_id}")` into the `httpx.AsyncClient` request headers
  - Handle 401/403: return `{"error": "Service authentication failed. Check SERVICE_SECRET configuration."}`
  - Handle other non-200: return `{"error": "Vendor service temporarily unavailable (HTTP <status>)"}`
  - _Requirements: 7.6, 7.8, 8.1, 8.2_

- [ ] 4. Implement `check_vendor_availability` in `tools/vendor_tools.py`
  - [ ] 4.1 Add `@function_tool async def check_vendor_availability(vendor_id: str, event_date: str, service_id: Optional[str] = None) -> str`
    - Docstring: describe parameters and return shape
    - Call `_fetch_vendor_details` is NOT used here — call the availability endpoint directly via `httpx.AsyncClient`
    - Build params: `start_date=event_date`, `end_date=event_date`; add `service_id` only if provided
    - Merge `make_service_headers("GET", f"/api/v1/vendors/{vendor_id}/availability")` into request headers
    - On 200: parse `data.slots` (or `data` list); set `available = len(slots) > 0`; return `{"vendor_id": vendor_id, "available": available, "slots": slots}`
    - On 401/403: return `{"vendor_id": vendor_id, "available": False, "slots": [], "error": "Service authentication failed. Check SERVICE_SECRET configuration."}`
    - On other non-200: return `{"vendor_id": vendor_id, "available": False, "slots": [], "error": "HTTP <status>: <message>"}`
    - On `httpx.ConnectError`: return `{"vendor_id": vendor_id, "available": False, "slots": [], "error": "Could not connect to vendor service"}`
    - On `httpx.TimeoutException`: return `{"vendor_id": vendor_id, "available": False, "slots": [], "error": "Vendor service request timed out"}`
    - On any other exception: return `{"vendor_id": vendor_id, "available": False, "slots": [], "error": "An unexpected error occurred"}`
    - Wrap entire body in `try/except Exception`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 7.3, 7.8, 8.1, 8.2, 8.4_

  - [ ]* 4.2 Write property test: `test_check_availability_auth_headers_present` (Property 1)
    - **Property 1: service auth headers present on check_vendor_availability**
    - Use `@given(vendor_id=st.text(min_size=1, max_size=50, alphabet=...), event_date=st.dates(...).map(str))` with `respx.mock` returning 200 with empty slots
    - Assert all three auth headers present in captured request
    - **Validates: Requirements 7.1, 7.2, 7.3**

  - [ ]* 4.3 Write property test: `test_available_true_iff_slots_nonempty` (Property 5)
    - **Property 5: `available` flag matches slots non-emptiness**
    - Use `@given(slots=st.lists(st.fixed_dictionaries({...slot fields...}), min_size=0, max_size=10))` with `respx.mock` returning 200 with those slots
    - Assert `parsed["available"] == (len(slots) > 0)`
    - **Validates: Requirements 1.3**

  - [ ]* 4.4 Write property test: `test_check_availability_non_200_returns_available_false` (Property 3)
    - **Property 3: non-200 responses produce error field and available=false**
    - Use `@given(status_code=st.integers(min_value=400, max_value=599).filter(lambda s: s not in (401, 403)))` with `respx.mock`
    - Assert `parsed["available"] is False`, `parsed["slots"] == []`, `"error"` key present
    - **Validates: Requirements 1.4, 8.2**

  - [ ]* 4.5 Write unit test: `test_check_availability_network_exception_returns_safe_json`
    - Use `respx.mock` with `side_effect=httpx.ConnectError("refused")`
    - Assert returned JSON is valid, `available` is `False`, `slots` is `[]`, `error` does not contain stack trace or class name
    - _Requirements: 1.5, 8.1_

  - [ ]* 4.6 Write unit test: `test_check_availability_401_403_returns_auth_failure_message` (Property 9)
    - **Property 9: 401/403 responses produce the specific auth failure message**
    - Mock 401 and 403; assert `error == "Service authentication failed. Check SERVICE_SECRET configuration."`
    - **Validates: Requirements 7.8**

  - [ ]* 4.7 Write property test: `test_check_availability_always_returns_valid_json` (Property 2)
    - **Property 2: tool always returns valid JSON for any backend response**
    - Use `@given(status_code=st.integers(min_value=200, max_value=599))` with `respx.mock`
    - Assert `json.loads(result)` does not raise and result is a `dict`
    - **Validates: Requirements 8.4, 1.5**

- [ ] 5. Checkpoint — Ensure all tests pass so far
  - Run `uv run pytest tests/test_vendor_tools.py -x` from `packages/agentic_event_orchestrator`
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement `get_vendor_services` in `tools/vendor_tools.py`
  - [ ] 6.1 Add `@function_tool async def get_vendor_services(vendor_id: str) -> str`
    - Guard: if `vendor_id == ""`, return `{"vendor_id": "", "services": [], "error": "vendor_id must not be empty"}` immediately without making any HTTP request
    - Call `_fetch_vendor_details(vendor_id, backend_url)` to reuse the raw fetch helper
    - Filter returned `services` list to only entries where `is_active == True`
    - Map each active service to `{"id": ..., "name": ..., "price_min": ..., "price_max": ..., "capacity": ...}`
    - On success with active services: return `{"vendor_id": vendor_id, "services": [...]}`
    - On success with no active services or missing `services` field: return `{"vendor_id": vendor_id, "services": []}`
    - On non-200 or network exception (propagated from `_fetch_vendor_details` returning `{}`): return `{"vendor_id": vendor_id, "services": [], "error": "Could not retrieve vendor services"}`
    - Wrap entire body in `try/except Exception`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.7, 7.4, 8.4_

  - [ ]* 6.2 Write property test: `test_only_active_services_returned` (Property 4)
    - **Property 4: `get_vendor_services` returns only active services**
    - Use `@given(services=st.lists(st.fixed_dictionaries({"id": st.uuids().map(str), "name": st.text(min_size=1), "price_min": st.floats(min_value=0, max_value=1_000_000), "price_max": st.floats(min_value=0, max_value=1_000_000), "capacity": st.integers(min_value=1, max_value=10_000), "is_active": st.booleans()}), min_size=0, max_size=20))`
    - Mock backend returning 200 with those services; assert returned IDs exactly match `{s["id"] for s in services if s["is_active"]}`
    - Assert each returned entry has exactly the fields `id`, `name`, `price_min`, `price_max`, `capacity`
    - **Validates: Requirements 2.3**

  - [ ]* 6.3 Write property test: `test_get_vendor_services_auth_headers_present` (Property 1)
    - **Property 1: service auth headers present on get_vendor_services**
    - Use `@given(vendor_id=st.text(min_size=1, max_size=50, alphabet=...))` with `respx.mock` returning 200
    - Assert all three auth headers present in captured request
    - **Validates: Requirements 7.1, 7.2, 7.4**

  - [ ]* 6.4 Write unit test: `test_empty_vendor_id_returns_error_no_http`
    - Call `await get_vendor_services(vendor_id="")` with `respx.mock` active
    - Assert returned JSON has `error == "vendor_id must not be empty"`, `services == []`
    - Assert no HTTP request was made (route call count == 0)
    - _Requirements: 2.7_

  - [ ]* 6.5 Write property test: `test_get_vendor_services_non_200_returns_error_and_empty_services` (Property 3)
    - **Property 3: non-200 responses produce error field and empty services list**
    - Use `@given(status_code=st.integers(min_value=400, max_value=599))` with `respx.mock`
    - Assert `parsed["services"] == []` and `"error"` key present
    - **Validates: Requirements 2.5, 8.2**

  - [ ]* 6.6 Write property test: `test_get_vendor_services_always_returns_valid_json` (Property 2)
    - **Property 2: tool always returns valid JSON for any backend response**
    - Use `@given(status_code=st.integers(min_value=200, max_value=599))` with `respx.mock`
    - Assert `json.loads(result)` does not raise
    - **Validates: Requirements 8.4, 2.5**

- [ ] 7. Implement `compare_vendors` in `tools/vendor_tools.py`
  - [ ] 7.1 Add `@function_tool async def compare_vendors(vendor_ids: list[str], event_date: str, criteria: Optional[list[str]] = None) -> str`
    - Validate inputs before any HTTP calls:
      - `len(vendor_ids) < 2` → return `{"error": "At least two vendor IDs are required for comparison"}`
      - `len(vendor_ids) > 10` → return `{"error": "vendor_ids must contain between 2 and 10 entries"}`
      - Any `""` in `vendor_ids` → return `{"error": "vendor_ids must not contain empty strings"}`
      - `event_date` before `datetime.utcnow().date()` → return `{"error": "event_date must be a future date"}`
    - Use `asyncio.gather(return_exceptions=True)` to fetch all vendor details and availability concurrently: call `_fetch_vendor_details` and `_fetch_vendor_availability` for each vendor ID
    - Build comparison entry for each vendor: if fetch succeeded, populate `vendor_id`, `business_name`, `rating`, `price_min`, `price_max`, `available`, `city`; if fetch failed (exception or empty dict), set all fields except `vendor_id` to `None`
    - Sort result: `rating` descending (None last), then `business_name` ascending (None last)
    - Return `{"comparison": [...]}`
    - Wrap entire body in `try/except Exception`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 7.1, 8.4_

  - [ ]* 7.2 Write property test: `test_compare_vendors_sorted_by_rating_desc_name_asc` (Property 6)
    - **Property 6: `compare_vendors` output sorted by rating descending, then business_name ascending**
    - Use `@given(vendor_data=st.lists(st.fixed_dictionaries({"rating": st.one_of(st.none(), st.floats(min_value=0, max_value=5)), "business_name": st.text(min_size=1)}), min_size=2, max_size=10))`
    - Mock `_fetch_vendor_details` to return controlled data; assert sort invariant holds
    - **Validates: Requirements 3.3**

  - [ ]* 7.3 Write property test: `test_all_vendor_ids_in_output_on_partial_failure` (Property 7)
    - **Property 7: `compare_vendors` includes all vendor IDs in output even on partial failure**
    - Use `@given(vendor_ids=st.lists(st.text(min_size=1, max_size=20), min_size=2, max_size=10, unique=True), failing_indices=st.frozensets(st.integers(min_value=0, max_value=9)))`
    - Mock some vendor fetches to raise exceptions; assert output `comparison` list has one entry per input vendor ID
    - Assert failed vendors have `None` for all fields except `vendor_id`
    - **Validates: Requirements 3.6**

  - [ ]* 7.4 Write unit test: `test_fewer_than_2_vendors_returns_error`
    - Call `await compare_vendors(vendor_ids=["v1"], event_date="2030-01-01")`
    - Assert `error == "At least two vendor IDs are required for comparison"`, no `comparison` key
    - _Requirements: 3.4_

  - [ ]* 7.5 Write unit test: `test_more_than_10_vendors_returns_error`
    - Call with 11 vendor IDs; assert `error` contains validation message, no `comparison` key
    - _Requirements: 3.5_

  - [ ]* 7.6 Write unit test: `test_empty_string_in_vendor_ids_returns_error`
    - Call with `["v1", "", "v3"]`; assert `error` contains validation message, no `comparison` key
    - _Requirements: 3.5_

  - [ ]* 7.7 Write unit test: `test_past_event_date_returns_error`
    - Call with `event_date="2020-01-01"`; assert `error == "event_date must be a future date"`, no `comparison` key
    - _Requirements: 3.8_

  - [ ]* 7.8 Write property test: `test_compare_vendors_always_returns_valid_json` (Property 2)
    - **Property 2: tool always returns valid JSON for any input**
    - Use `@given(vendor_ids=st.lists(st.text(min_size=1), min_size=2, max_size=10, unique=True), event_date=st.dates(min_value=date.today() + timedelta(days=1)).map(str))` with `respx.mock`
    - Assert `json.loads(result)` does not raise
    - **Validates: Requirements 8.4, 3.4, 3.5**

- [ ] 8. Checkpoint — Ensure all tests pass so far
  - Run `uv run pytest tests/test_vendor_tools.py -x` from `packages/agentic_event_orchestrator`
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Update `tools/__init__.py` to export new tools
  - Add `check_vendor_availability`, `get_vendor_services`, `compare_vendors` to the import from `.vendor_tools`
  - Add all three to `__all__`
  - _Requirements: 1.6, 2.6, 3.7_

- [ ] 10. Update `pipeline/vendor_discovery.py` — wire new tools
  - Import `check_vendor_availability`, `get_vendor_services`, `compare_vendors` from `tools`
  - Add all three to the `tools=[...]` list in `build_vendor_discovery_agent`
  - _Requirements: 1.6, 2.6, 3.7_

- [ ] 11. Update `pipeline/orchestrator.py` — add direct tools
  - Import `search_vendors`, `check_vendor_availability`, `compare_vendors` from `tools`
  - Add `tools=[search_vendors, check_vendor_availability, compare_vendors]` to `build_orchestrator_agent`
  - _Requirements: 3.7, 6.1, 6.2_

- [ ] 12. Update `pipeline/booking.py` — add `get_vendor_services`
  - Import `get_vendor_services` from `tools`
  - Add `get_vendor_services` to the `tools=[...]` list in `build_booking_agent`
  - _Requirements: 2.6_

- [ ] 13. Update `pipeline/instructions.py` — all four instruction strings
  - [ ] 13.1 Update `VENDOR_DISCOVERY_INSTRUCTIONS`
    - Add search mode guidance after the `search_vendors` step: `SEARCH MODE: use mode="semantic" for descriptive queries (e.g. "elegant", "affordable", "outdoor"); use mode="keyword" for category names (e.g. "catering", "photography") or specific vendor names; use mode="hybrid" (default) in all other cases.`
    - Add proactive result format line: `FORMAT: {business_name} — {category} — PKR {price_min}–{price_max} — ⭐ {rating}`
    - Add steps 5–7: check availability via `check_vendor_availability`, compare via `compare_vendors`, list services via `get_vendor_services`
    - Verify `len(VENDOR_DISCOVERY_INSTRUCTIONS) <= 3200` after edit
    - _Requirements: 4.6, 5.5_

  - [ ] 13.2 Update `ORCHESTRATOR_INSTRUCTIONS`
    - Replace the single-line delegation note with the autonomous vendor selection workflow: search → take top 3 → check availability for each → compare → present ranked recommendation with rationale
    - Add: "to book: hand off to BookingAgent — do NOT call create_booking_request directly"
    - Add fallback instructions for all-unavailable and zero-results cases
    - Verify `len(ORCHESTRATOR_INSTRUCTIONS) <= 3200` after edit
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ] 13.3 Update `BOOKING_INSTRUCTIONS`
    - Add `get_vendor_services` hint in the collection step: "Use get_vendor_services(vendor_id) to list available services if service_id is unknown."
    - Add critical violation note: "CRITICAL VIOLATION: calling create_booking_request without prior confirmation."
    - Add: "If user replies anything other than 'confirm' (case-insensitive), treat as cancellation."
    - Verify `len(BOOKING_INSTRUCTIONS) <= 3200` after edit
    - _Requirements: 9.1, 9.2, 9.3, 9.5_

  - [ ] 13.4 Update `EVENT_PLANNER_INSTRUCTIONS`
    - Replace step 5 with: `Ask: "Would you like me to find vendors for this event?" — if yes or no explicit decline, hand off to VendorDiscoveryAgent with event_type, city, and budget as context. If user declines, acknowledge and end the turn.`
    - Verify `len(EVENT_PLANNER_INSTRUCTIONS) <= 3200` after edit
    - _Requirements: 5.1, 5.2, 5.3_

- [ ] 14. Write instruction smoke tests in `tests/test_vendor_tools.py`
  - [ ]* 14.1 Write unit test: `test_all_instructions_under_3200_chars`
    - Import all five instruction strings; assert `len(each) <= 3200`
    - _Requirements: (design constraint — MAX_INSTRUCTION_CHARS)_

  - [ ]* 14.2 Write unit test: `test_vendor_discovery_instructions_contain_mode_guidance`
    - Assert `"mode=\"semantic\""` and `"mode=\"keyword\""` and `"mode=\"hybrid\""` all appear in `VENDOR_DISCOVERY_INSTRUCTIONS`
    - _Requirements: 4.6_

  - [ ]* 14.3 Write unit test: `test_orchestrator_instructions_contain_workflow_steps`
    - Assert `"search_vendors"`, `"check_vendor_availability"`, `"compare_vendors"` all appear in `ORCHESTRATOR_INSTRUCTIONS`
    - _Requirements: 6.2_

  - [ ]* 14.4 Write unit test: `test_booking_instructions_contain_confirmation_gate`
    - Assert `"CRITICAL VIOLATION"` and `"confirm"` appear in `BOOKING_INSTRUCTIONS`
    - _Requirements: 9.5_

- [ ] 15. Write agent wiring smoke tests in `tests/test_vendor_tools.py`
  - [ ]* 15.1 Write unit test: `test_vendor_discovery_agent_has_new_tools`
    - Instantiate `build_vendor_discovery_agent(model="fake")` with a mock model
    - Assert `"check_vendor_availability"`, `"get_vendor_services"`, `"compare_vendors"` all in `[t.name for t in agent.tools]`
    - _Requirements: 1.6, 2.6, 3.7_

  - [ ]* 15.2 Write unit test: `test_orchestrator_agent_has_new_tools`
    - Instantiate `build_orchestrator_agent(model="fake", ...)` with mock agents
    - Assert `"search_vendors"`, `"check_vendor_availability"`, `"compare_vendors"` all in `[t.name for t in agent.tools]`
    - _Requirements: 3.7, 6.1_

  - [ ]* 15.3 Write unit test: `test_booking_agent_has_get_vendor_services`
    - Instantiate `build_booking_agent(model="fake")`
    - Assert `"get_vendor_services"` in `[t.name for t in agent.tools]`
    - _Requirements: 2.6_

- [ ] 16. Final checkpoint — Ensure all tests pass
  - Run `uv run pytest tests/test_vendor_tools.py -v` from `packages/agentic_event_orchestrator`
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Run tests with `uv run pytest` (never `pip` or bare `pytest`)
- All `respx.mock` usage must be inside `with respx.mock:` context managers; no real HTTP calls in tests
- `hypothesis` settings: use `@settings(max_examples=100)` on all property tests
- `_fetch_vendor_details` and `_fetch_vendor_availability` are internal helpers — they are NOT `@function_tool` decorated and are called directly by `compare_vendors`
- `make_service_headers` must be called per-request (not cached) because the HMAC includes a timestamp
- The `validate_instruction_limits()` function in `instructions.py` runs at module import — any instruction over 3200 chars will log an error at startup
- All tools must wrap their entire body in `try/except Exception` and never propagate raw exceptions

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "3"] },
    { "id": 2, "tasks": ["4.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7"] },
    { "id": 3, "tasks": ["6.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7"] },
    { "id": 4, "tasks": ["7.1", "6.2", "6.3", "6.4", "6.5", "6.6"] },
    { "id": 5, "tasks": ["9", "7.2", "7.3", "7.4", "7.5", "7.6", "7.7", "7.8"] },
    { "id": 6, "tasks": ["10", "11", "12"] },
    { "id": 7, "tasks": ["13.1", "13.2", "13.3", "13.4"] },
    { "id": 8, "tasks": ["14.1", "14.2", "14.3", "14.4", "15.1", "15.2", "15.3"] }
  ]
}
```
