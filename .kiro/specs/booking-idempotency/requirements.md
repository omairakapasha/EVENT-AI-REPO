# Requirements Document

## Introduction

`POST /api/v1/bookings/` currently has no idempotency mechanism. On mobile networks with flaky connections, a booking request can fail mid-flight — the server receives and processes the request, but the client never receives the response. The user retries and creates a duplicate booking, potentially double-charging and double-booking the same availability slot.

This feature adds an optional `Idempotency-Key` header to the booking creation endpoint. When provided, the system stores the key alongside the request fingerprint and response, and replays the cached response on any retry within a 24-hour window. A background cleanup task expires stale keys hourly.

## Glossary

- **Booking_API**: The FastAPI route handler at `POST /api/v1/bookings/`.
- **Idempotency_Service**: The service layer responsible for storing, looking up, and expiring idempotency records.
- **Idempotency_Key**: A client-supplied string (UUID or arbitrary, max 128 characters) passed in the `Idempotency-Key` HTTP request header.
- **Idempotency_Record**: A row in the `idempotency_keys` table that stores the key, user identity, request fingerprint, and cached response.
- **Request_Hash**: A SHA-256 digest of the canonical JSON-serialised request body, used to detect body mismatches on retry.
- **Cleanup_Task**: A background APScheduler job that deletes expired `Idempotency_Record` rows.
- **TTL**: Time-to-live — 24 hours from the moment an `Idempotency_Record` is first created.
- **User**: An authenticated caller identified by `user_id` (UUID), resolved via `Depends(get_current_user)`.

---

## Requirements

### Requirement 1: Accept Optional Idempotency-Key Header

**User Story:** As a mobile client, I want to attach an `Idempotency-Key` header to a booking request, so that I can safely retry the request on a dropped connection without creating a duplicate booking.

#### Acceptance Criteria

1. THE `Booking_API` SHALL accept an optional `Idempotency-Key` HTTP request header on `POST /api/v1/bookings/`.
2. WHEN the `Idempotency-Key` header is absent, THE `Booking_API` SHALL process the booking request normally without any idempotency checks.
3. WHEN the `Idempotency-Key` header value exceeds 128 characters, THE `Booking_API` SHALL return HTTP 422 with error code `VALIDATION_IDEMPOTENCY_KEY_TOO_LONG`.
4. WHEN the `Idempotency-Key` header value is an empty string, THE `Booking_API` SHALL return HTTP 422 with error code `VALIDATION_IDEMPOTENCY_KEY_EMPTY`.

---

### Requirement 2: Store Idempotency Record on First Request

**User Story:** As the system, I want to persist the idempotency key, user identity, request fingerprint, and response on the first successful or failed booking attempt, so that subsequent retries can be served from cache.

#### Acceptance Criteria

1. WHEN a booking request is received with a valid `Idempotency-Key` and no matching `Idempotency_Record` exists for that key and `user_id`, THE `Idempotency_Service` SHALL create an `Idempotency_Record` containing: `key`, `user_id`, `request_hash` (SHA-256 of the request body), `response_status` (HTTP status code), `response_body` (JSONB), `created_at`, and `expires_at` (= `created_at` + 24 hours).
2. THE `Idempotency_Service` SHALL persist the `Idempotency_Record` atomically within the same database transaction as the booking creation.
3. THE `idempotency_keys` table SHALL enforce a unique constraint on `(key, user_id)` to prevent concurrent duplicate inserts.

---

### Requirement 3: Replay Cached Response on Retry

**User Story:** As a mobile client, I want a retry with the same `Idempotency-Key` to return the original response, so that I receive a consistent result without triggering a second booking.

#### Acceptance Criteria

1. WHEN a booking request is received with a valid `Idempotency-Key` and a matching, non-expired `Idempotency_Record` exists for that key and `user_id`, THE `Booking_API` SHALL return the cached `response_status` and `response_body` without executing the booking creation logic.
2. WHEN the cached response is replayed, THE `Booking_API` SHALL include the response header `Idempotency-Replayed: true`.
3. WHEN the cached response is replayed, THE `Idempotency_Service` SHALL NOT create a new booking, charge the user, or modify availability.

---

### Requirement 4: Reject Mismatched Request Body

**User Story:** As the system, I want to detect when a client reuses an idempotency key with a different request body, so that I can reject the request and prevent unintended behaviour.

#### Acceptance Criteria

1. WHEN a booking request is received with a valid `Idempotency-Key` and a matching `Idempotency_Record` exists for that key and `user_id`, but the `Request_Hash` of the incoming body does not match the stored `request_hash`, THE `Booking_API` SHALL return HTTP 422 with error code `IDEMPOTENCY_KEY_MISMATCH`.
2. WHEN an `IDEMPOTENCY_KEY_MISMATCH` error is returned, THE `Booking_API` SHALL NOT modify any existing `Idempotency_Record` or create a new booking.

---

### Requirement 5: Scope Idempotency Keys Per User

**User Story:** As the system, I want idempotency keys to be scoped to the authenticated user, so that two different users can use the same key string without conflict.

#### Acceptance Criteria

1. THE `Idempotency_Service` SHALL scope all `Idempotency_Record` lookups and uniqueness checks to the combination of `(key, user_id)`.
2. WHEN two different users submit requests with the same `Idempotency-Key` value, THE `Idempotency_Service` SHALL treat each as an independent `Idempotency_Record` and process both requests normally.

---

### Requirement 6: Expire Idempotency Records After 24 Hours

**User Story:** As the system, I want idempotency records to expire after 24 hours, so that clients can reuse a key for a genuinely new booking after the TTL has elapsed.

#### Acceptance Criteria

1. WHEN a booking request is received with a valid `Idempotency-Key` and a matching `Idempotency_Record` exists for that key and `user_id` but `expires_at` is in the past, THE `Booking_API` SHALL treat the request as a new first-time request and process it normally.
2. WHEN a new `Idempotency_Record` is created to replace an expired one, THE `Idempotency_Service` SHALL delete the expired record and insert a fresh record with a new `expires_at` of `now + 24 hours`.

---

### Requirement 7: Background Cleanup of Expired Records

**User Story:** As the system operator, I want expired idempotency records to be removed automatically, so that the `idempotency_keys` table does not grow unboundedly.

#### Acceptance Criteria

1. THE `Cleanup_Task` SHALL execute on a recurring schedule of every 60 minutes.
2. WHEN the `Cleanup_Task` executes, THE `Cleanup_Task` SHALL delete all `Idempotency_Record` rows where `expires_at` is less than or equal to the current UTC timestamp.
3. WHEN the `Cleanup_Task` completes, THE `Cleanup_Task` SHALL emit a structured log entry recording the number of rows deleted and the execution timestamp.
4. IF the `Cleanup_Task` encounters a database error, THEN THE `Cleanup_Task` SHALL log the error with severity `ERROR` and reschedule normally without crashing the application.

---

### Requirement 8: Database Schema — idempotency_keys Table

**User Story:** As a developer, I want a well-defined `idempotency_keys` table with appropriate indexes and constraints, so that key lookups are fast and data integrity is enforced.

#### Acceptance Criteria

1. THE `idempotency_keys` table SHALL contain the following columns: `id` (UUID, primary key), `key` (VARCHAR(128), not null), `user_id` (UUID, not null, foreign key → `users.id` ON DELETE CASCADE), `request_hash` (CHAR(64), not null — hex-encoded SHA-256), `response_status` (INTEGER, not null), `response_body` (JSONB, not null), `created_at` (TIMESTAMPTZ, not null, default `now()`), `expires_at` (TIMESTAMPTZ, not null).
2. THE `idempotency_keys` table SHALL have a unique constraint on `(key, user_id)`.
3. THE `idempotency_keys` table SHALL have a B-tree index on `expires_at` to support efficient cleanup queries.
4. THE `Idempotency_Service` SHALL use `DIRECT_URL` for Alembic migrations and `DATABASE_URL` (pooler) for runtime queries, consistent with the project database conventions.

---

### Requirement 9: Alembic Migration

**User Story:** As a developer, I want a reversible Alembic migration for the `idempotency_keys` table, so that the schema change can be applied and rolled back safely.

#### Acceptance Criteria

1. THE migration SHALL create the `idempotency_keys` table with all columns, constraints, and indexes defined in Requirement 8.
2. THE migration `downgrade()` function SHALL drop the `idempotency_keys` table completely.
3. THE migration SHALL be placed in `packages/backend/alembic/versions/` and follow the project naming convention.

---

### Requirement 10: Idempotency Round-Trip Property

**User Story:** As a developer, I want a property-based test that verifies sending the same booking request twice with the same idempotency key always produces the same response and exactly one booking, so that the core idempotency guarantee is machine-verified across a wide range of inputs.

#### Acceptance Criteria

1. FOR ALL valid `BookingCreate` payloads and arbitrary `Idempotency-Key` strings (up to 128 characters), sending the same request twice with the same key SHALL return identical `response_status` and `response_body` on both calls (round-trip property).
2. FOR ALL valid `BookingCreate` payloads and arbitrary `Idempotency-Key` strings, after two identical requests the total number of bookings created for that user SHALL equal 1 (invariant property).
3. WHEN the property-based test generates inputs, THE test SHALL use `hypothesis` strategies to cover varied booking payloads, key formats (UUID strings, alphanumeric strings, strings with special characters), and key lengths from 1 to 128 characters.
