# Bugfix Requirements Document

## Introduction

The AI chat system in `packages/agentic_event_orchestrator` has two distinct bug clusters. The first cluster (six compounding defects) makes event creation and booking non-functional: event and booking tools send HTTP requests with no authentication (returning 401 silently), the `create_event` tool sends a payload with completely wrong field names and types that the backend rejects, the `create_booking_request` tool sends camelCase fields and omits mandatory pricing fields, and all tool errors are swallowed and returned as `{"success": false}` JSON strings that the LLM cannot act on. The second cluster is a new hallucination defect: when a user asks a general vendor availability query such as "What photographers are available next week?", the AI responds with a fabricated claim that it will "securely read directly from the database to give you an accurate answer" — but then either fails silently or returns no useful result. This hallucination is caused by a mismatch between the `check_vendor_availability` tool's requirement for a specific `vendor_id` + `event_date` pair and the agent's inability to resolve a general availability query into those parameters without first searching for vendors. The fix for the first cluster replaces HTTP calls for event and booking tools with direct database access via the OpenAI Agents SDK `RunContext` pattern, removes dead HMAC headers from vendor tools, and corrects all schema mismatches. The fix for the second cluster corrects the VendorDiscoveryAgent's instructions and tool routing so that general availability queries follow the correct search-then-check flow and the LLM never fabricates capability claims.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the EventPlannerAgent calls `create_event` after collecting user requirements THEN the system sends an HTTP POST to `/api/v1/events` with no `Authorization` header and receives a 401 response, causing the tool to return `{"success": false, "error": "HTTP 401"}` and the chat to appear stuck with no event created

1.2 WHEN the EventPlannerAgent calls `create_event` with a valid event type string such as `"wedding"` THEN the system sends `{"eventType": "wedding", "eventName": "...", "eventDate": "2026-10-01", "location": "Lahore", "attendees": 200}` to the backend, which expects `{"event_type_id": "<uuid>", "name": "...", "start_date": "2026-10-01T00:00:00+05:00", "city": "Lahore", "guest_count": 200}`, resulting in a 422 validation error even if auth were present

1.3 WHEN the BookingAgent calls `create_booking_request` after user confirmation THEN the system sends an HTTP POST to `/api/v1/bookings` with no `Authorization` header and receives a 401 response, causing the booking to silently fail

1.4 WHEN the BookingAgent calls `create_booking_request` with vendor and service IDs THEN the system sends `{"vendorId": "...", "serviceId": "...", "eventDate": "...", "eventName": "...", "guestCount": 100}` but the backend `BookingCreate` schema requires snake_case fields (`vendor_id`, `service_id`, `event_date`, `event_name`, `guest_count`) plus mandatory `unit_price` and `total_price` fields, resulting in a 422 validation error

1.5 WHEN any event or booking tool call returns a non-2xx HTTP response THEN the system returns `{"success": false, "error": "..."}` as a JSON string, which the LLM interprets as a completed tool call with a failure result and produces no further action, leaving the chat stuck

1.6 WHEN the VendorDiscoveryAgent calls `search_vendors` or `get_vendor_details` THEN the system attaches HMAC `X-Service-Timestamp`, `X-Service-Signature`, and `X-Service-Name` headers to requests targeting public endpoints (`/api/v1/public_vendors/*`) that have no auth requirement and no HMAC verification middleware, making the headers dead code that adds unnecessary complexity

1.7 WHEN the EventPlannerAgent calls `query_event_types` THEN the system returns a hardcoded static list of event type strings with fake IDs (e.g. `"id": "wedding"`) rather than the real UUIDs from the `event_types` database table, making it impossible to resolve a valid `event_type_id` for event creation

### Expected Behavior (Correct)

2.1 WHEN the EventPlannerAgent calls `create_event` after collecting user requirements THEN the system SHALL query the `event_types` table directly via SQLAlchemy to resolve the event type name to a valid UUID, insert a new row into the `events` table with the correct field names (`event_type_id`, `name`, `start_date`, `city`, `guest_count`, `budget`), and return `{"success": true, "event_id": "<uuid>", "event": {...}}` without any HTTP call to the backend

2.2 WHEN the EventPlannerAgent calls `create_event` with a valid event type string THEN the system SHALL accept the human-readable name (e.g. `"wedding"`), perform a case-insensitive lookup against `event_types.name` in the database, and use the resolved UUID as `event_type_id` in the insert — the LLM never needs to know or supply a UUID

2.3 WHEN the BookingAgent calls `create_booking_request` after user confirmation THEN the system SHALL look up the service record directly from the `services` table to obtain `price_min` as `unit_price`, compute `total_price` as `unit_price * quantity`, insert a new row into the `bookings` table with all required fields in snake_case, and return `{"success": true, "booking_id": "<uuid>", "status": "pending"}` without any HTTP call to the backend

2.4 WHEN the EventPlannerAgent calls `get_user_events` THEN the system SHALL execute a direct `SELECT` from the `events` table filtered by `user_id` and return the results without an HTTP call

2.5 WHEN the EventPlannerAgent calls `get_event_details` THEN the system SHALL execute a direct `SELECT` from the `events` table by event ID, verify the requesting user owns the event, and return the full event record without an HTTP call

2.6 WHEN the EventPlannerAgent calls `update_event_status` THEN the system SHALL validate the requested status transition against the allowed `EventStatus` values, update the record directly in the database, and return the updated status without an HTTP call

2.7 WHEN the EventPlannerAgent calls `query_event_types` THEN the system SHALL execute a direct `SELECT` from the `event_types` table and return the real UUIDs and names from the database, not a hardcoded static list

2.8 WHEN the BookingAgent calls `get_my_bookings`, `get_booking_details`, or `cancel_booking` THEN the system SHALL execute direct database queries with user ownership verification instead of unauthenticated HTTP calls

2.9 WHEN the VendorDiscoveryAgent calls `search_vendors`, `get_vendor_details`, `check_vendor_availability`, or `get_vendor_recommendations` THEN the system SHALL send HTTP requests to the public vendor endpoints without HMAC headers, since those endpoints require no authentication

2.10 WHEN any tool receives a `RunContext` carrying an `AgentContext` THEN the system SHALL use `ctx.context.db` as the `AsyncSession` for all database operations and `ctx.context.user_id` for ownership checks, with the context threaded through `Runner.run()` and `Runner.run_streamed()` in the chat router

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the VendorDiscoveryAgent calls `search_vendors` with valid event type and location THEN the system SHALL CONTINUE TO return vendor results from the backend public search endpoint via HTTP, as vendor data is served by the backend and does not require auth

3.2 WHEN the VendorDiscoveryAgent calls `compare_vendors` with multiple vendor IDs and an event date THEN the system SHALL CONTINUE TO fetch vendor details and availability concurrently and return a sorted comparison list

3.3 WHEN the VendorDiscoveryAgent calls `get_vendor_services` for a vendor THEN the system SHALL CONTINUE TO return the list of active services with pricing from the public vendor endpoint

3.4 WHEN the TriageAgent receives a user message THEN the system SHALL CONTINUE TO route to the correct specialist agent (EventPlannerAgent, VendorDiscoveryAgent, BookingAgent, OrchestratorAgent) based on the existing routing rules

3.5 WHEN the BookingAgent calls `create_booking_request` THEN the system SHALL CONTINUE TO require explicit user confirmation (the word "confirm") before inserting the booking record, as mandated by the booking instructions

3.6 WHEN the chat router receives a request THEN the system SHALL CONTINUE TO apply all existing guardrails (PromptFirewall, OutputLeakDetector, GuardrailService, rate limiting) before and after the agent run

3.7 WHEN the chat router processes a request THEN the system SHALL CONTINUE TO persist the conversation turn to the `ai.messages` table and update Mem0 memory after the agent run completes

3.8 WHEN the SSE streaming endpoint processes a request THEN the system SHALL CONTINUE TO stream token-by-token deltas and emit the `done` event with session ID on completion

3.9 WHEN the agent pipeline is built at startup THEN the system SHALL CONTINUE TO use the existing `build_pipeline(model)` entry point and the `TriageAgent` as the sole entry point for all user interactions
