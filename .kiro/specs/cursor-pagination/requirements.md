# Requirements Document

## Introduction

`GET /api/v1/bookings/` and `GET /api/v1/notifications/` currently use offset/limit pagination. On a live marketplace with constant concurrent writes, offset pagination produces phantom duplicates and skipped items: a booking inserted between two page requests causes item 20 to appear on both pages, and a cancelled booking causes item 21 to be skipped entirely. For notifications — a high-write table driven by every booking state transition — users see duplicate or missing items on every page turn.

This feature replaces the primary pagination mechanism on both endpoints with keyset (cursor-based) pagination using a composite `(created_at DESC, id DESC)` cursor. The cursor is opaque to clients (base64-encoded JSON internally). The legacy `page` and `offset` parameters remain functional but are deprecated and trigger a `Deprecation-Warning` response header.

## Glossary

- **Bookings_API**: The FastAPI route handler at `GET /api/v1/bookings/`.
- **Notifications_API**: The FastAPI route handler at `GET /api/v1/notifications/`.
- **Pagination_Service**: The shared service layer responsible for encoding, decoding, and applying cursor-based pagination to SQLAlchemy queries.
- **Cursor**: An opaque string passed as the `cursor` query parameter. Internally it is a base64url-encoded JSON object containing `created_at` (ISO-8601 UTC timestamp) and `id` (UUID string) that together identify the last item seen by the client.
- **Cursor_Position**: The decoded pair `(created_at, id)` extracted from a `Cursor`, used to construct a keyset `WHERE` clause.
- **Page**: A single response payload containing a list of items and a `meta` object with `next_cursor` and `has_more`.
- **next_cursor**: The `Cursor` value the client must pass to retrieve the next `Page`. `null` when no further items exist.
- **has_more**: A boolean in the `meta` object. `true` when at least one item exists beyond the current `Page`.
- **limit**: The maximum number of items returned per `Page`. Default 20, maximum 100.
- **Deprecation_Warning**: The `Deprecation-Warning` HTTP response header returned when a caller uses the legacy `page` or `offset` parameters.
- **User**: An authenticated caller identified by `user_id` (UUID), resolved via `Depends(get_current_user)`.

---

## Requirements

### Requirement 1: Cursor Query Parameter

**User Story:** As a client application, I want to pass an optional `cursor` query parameter to the bookings and notifications endpoints, so that I can retrieve pages of results that are stable under concurrent writes.

#### Acceptance Criteria

1. THE `Bookings_API` SHALL accept an optional `cursor` query parameter of type string.
2. THE `Notifications_API` SHALL accept an optional `cursor` query parameter of type string.
3. WHEN the `cursor` parameter is absent, THE `Bookings_API` SHALL return the first page of the authenticated user's bookings ordered by `(created_at DESC, id DESC)`.
4. WHEN the `cursor` parameter is absent, THE `Notifications_API` SHALL return the first page of the authenticated user's notifications ordered by `(created_at DESC, id DESC)`.
5. WHEN the `cursor` parameter is present and valid, THE `Bookings_API` SHALL return only items whose `(created_at, id)` pair is strictly less than the `Cursor_Position` in `(created_at DESC, id DESC)` order.
6. WHEN the `cursor` parameter is present and valid, THE `Notifications_API` SHALL return only items whose `(created_at, id)` pair is strictly less than the `Cursor_Position` in `(created_at DESC, id DESC)` order.

---

### Requirement 2: Cursor Encoding and Opacity

**User Story:** As the system, I want the cursor to be opaque to clients, so that the internal pagination strategy can change without breaking client contracts.

#### Acceptance Criteria

1. THE `Pagination_Service` SHALL encode each `Cursor` as a base64url string (no padding) whose decoded content is a JSON object with exactly two fields: `"created_at"` (ISO-8601 UTC string) and `"id"` (UUID string).
2. THE `Pagination_Service` SHALL decode a `Cursor` by base64url-decoding the string and parsing the resulting JSON.
3. WHEN a `cursor` value cannot be base64url-decoded, THE `Bookings_API` SHALL return HTTP 422 with error code `VALIDATION_INVALID_CURSOR`.
4. WHEN a `cursor` value cannot be base64url-decoded, THE `Notifications_API` SHALL return HTTP 422 with error code `VALIDATION_INVALID_CURSOR`.
5. WHEN a decoded cursor JSON is missing the `"created_at"` or `"id"` field, or either field fails to parse, THE `Bookings_API` SHALL return HTTP 422 with error code `VALIDATION_INVALID_CURSOR`.
6. WHEN a decoded cursor JSON is missing the `"created_at"` or `"id"` field, or either field fails to parse, THE `Notifications_API` SHALL return HTTP 422 with error code `VALIDATION_INVALID_CURSOR`.
7. THE `Pagination_Service` SHALL generate the `next_cursor` for a `Page` by encoding the `(created_at, id)` of the last item in that `Page`.

---

### Requirement 3: Response Meta Object

**User Story:** As a client application, I want the response `meta` object to include `next_cursor` and `has_more`, so that I can determine whether more items exist and how to fetch them.

#### Acceptance Criteria

1. THE `Bookings_API` SHALL include a `meta` object in every cursor-paginated response containing: `next_cursor` (string or null), `has_more` (boolean), and `limit` (integer).
2. THE `Notifications_API` SHALL include a `meta` object in every cursor-paginated response containing: `next_cursor` (string or null), `has_more` (boolean), and `limit` (integer).
3. WHEN the current `Page` contains fewer items than `limit`, THE `Pagination_Service` SHALL set `has_more` to `false` and `next_cursor` to `null`.
4. WHEN the current `Page` contains exactly `limit` items, THE `Pagination_Service` SHALL set `has_more` to `true` and `next_cursor` to the encoded cursor of the last item in the `Page`.
5. WHEN the result set is empty, THE `Pagination_Service` SHALL set `has_more` to `false` and `next_cursor` to `null`.

---

### Requirement 4: Limit Parameter

**User Story:** As a client application, I want to control the number of items returned per page, so that I can tune the response size for my use case.

#### Acceptance Criteria

1. THE `Bookings_API` SHALL accept an optional `limit` query parameter with a default value of 20 and a maximum value of 100.
2. THE `Notifications_API` SHALL accept an optional `limit` query parameter with a default value of 20 and a maximum value of 100.
3. WHEN `limit` is less than 1, THE `Bookings_API` SHALL return HTTP 422 with error code `VALIDATION_ERROR`.
4. WHEN `limit` is less than 1, THE `Notifications_API` SHALL return HTTP 422 with error code `VALIDATION_ERROR`.
5. WHEN `limit` exceeds 100, THE `Bookings_API` SHALL return HTTP 422 with error code `VALIDATION_ERROR`.
6. WHEN `limit` exceeds 100, THE `Notifications_API` SHALL return HTTP 422 with error code `VALIDATION_ERROR`.

---

### Requirement 5: Backward Compatibility — Deprecated Offset Parameters

**User Story:** As an existing client, I want the legacy `page` and `offset` parameters to continue working, so that I am not broken by this change before I migrate to cursor pagination.

#### Acceptance Criteria

1. WHEN a request to `Bookings_API` includes the `page` query parameter, THE `Bookings_API` SHALL process the request using offset pagination and include a `Deprecation-Warning` response header with the value `"page and offset parameters are deprecated; migrate to cursor-based pagination"`.
2. WHEN a request to `Notifications_API` includes the `page` query parameter, THE `Notifications_API` SHALL process the request using offset pagination and include a `Deprecation-Warning` response header with the value `"page and offset parameters are deprecated; migrate to cursor-based pagination"`.
3. WHEN a request to `Bookings_API` includes both `cursor` and `page` parameters simultaneously, THE `Bookings_API` SHALL use cursor pagination and ignore the `page` parameter, and SHALL include the `Deprecation-Warning` header.
4. WHEN a request to `Notifications_API` includes both `cursor` and `page` parameters simultaneously, THE `Notifications_API` SHALL use cursor pagination and ignore the `page` parameter, and SHALL include the `Deprecation-Warning` header.
5. WHEN neither `cursor` nor `page` is present, THE `Bookings_API` SHALL use cursor pagination without emitting a `Deprecation-Warning` header.
6. WHEN neither `cursor` nor `page` is present, THE `Notifications_API` SHALL use cursor pagination without emitting a `Deprecation-Warning` header.

---

### Requirement 6: Keyset Query Construction

**User Story:** As the system, I want the keyset `WHERE` clause to use the composite `(created_at, id)` tuple comparison, so that pagination is correct even when multiple rows share the same `created_at` timestamp.

#### Acceptance Criteria

1. WHEN a valid `Cursor_Position` `(ts, uid)` is provided, THE `Pagination_Service` SHALL apply the filter `(created_at < ts) OR (created_at = ts AND id < uid)` to the base query, using the database's native timestamp and UUID comparison semantics.
2. THE `Pagination_Service` SHALL apply `ORDER BY created_at DESC, id DESC` to all cursor-paginated queries on both `bookings` and `notifications` tables.
3. THE `Pagination_Service` SHALL apply the `limit` value as the SQL `LIMIT` clause on all cursor-paginated queries.
4. WHEN a `status` filter is present on `Bookings_API`, THE `Pagination_Service` SHALL apply the status filter in addition to the keyset filter, preserving the `ORDER BY created_at DESC, id DESC` ordering.
5. WHEN an `unread_only` filter is present on `Notifications_API`, THE `Pagination_Service` SHALL apply the unread filter in addition to the keyset filter, preserving the `ORDER BY created_at DESC, id DESC` ordering.

---

### Requirement 7: Database Index

**User Story:** As a developer, I want composite indexes on `(user_id, created_at DESC, id DESC)` for both tables, so that cursor-paginated queries execute efficiently without full table scans.

#### Acceptance Criteria

1. THE `bookings` table SHALL have a composite B-tree index on `(user_id, created_at DESC, id DESC)`.
2. THE `notifications` table SHALL have a composite B-tree index on `(user_id, created_at DESC, id DESC)`.
3. THE index on `bookings` SHALL be created via a reversible Alembic migration placed in `packages/backend/alembic/versions/`.
4. THE index on `notifications` SHALL be created via the same reversible Alembic migration.
5. THE migration `downgrade()` function SHALL drop both indexes.

---

### Requirement 8: Alembic Migration

**User Story:** As a developer, I want a single reversible Alembic migration that adds the cursor pagination indexes, so that the schema change can be applied and rolled back safely.

#### Acceptance Criteria

1. THE migration SHALL create the composite index on `bookings (user_id, created_at DESC, id DESC)` as defined in Requirement 7.
2. THE migration SHALL create the composite index on `notifications (user_id, created_at DESC, id DESC)` as defined in Requirement 7.
3. THE migration `downgrade()` function SHALL drop both indexes without affecting any other schema objects.
4. THE migration SHALL be placed in `packages/backend/alembic/versions/` and follow the project naming convention (autogenerated prefix + descriptive slug).

---

### Requirement 9: No-Duplicate, No-Skip Stability Property

**User Story:** As a developer, I want a property-based test that verifies cursor-paginated results never contain duplicates and never skip items that existed before the first page request, so that the core stability guarantee is machine-verified across arbitrary concurrent insert sequences.

#### Acceptance Criteria

1. FOR ALL sequences of bookings inserted before the first page request, collecting all pages via cursor pagination SHALL return each pre-existing booking exactly once (no duplicates, no skips — invariant property).
2. FOR ALL sequences of bookings inserted concurrently between page requests (after the first cursor is issued), those new bookings SHALL NOT appear in any subsequent page of the same pagination session (stability property).
3. WHEN the property-based test generates inputs, THE test SHALL use `hypothesis` strategies to vary: the number of pre-existing bookings (1–50), the number of concurrent inserts between pages (0–10), and the `limit` value (1–20).
4. THE property-based test SHALL run entirely in-memory using `sqlite+aiosqlite:///:memory:` and SHALL NOT make any real network calls.

---

### Requirement 10: Cursor Continuity Property

**User Story:** As a developer, I want a property-based test that verifies the cursor from page N correctly addresses page N+1, so that sequential page traversal is complete and non-overlapping for any dataset size and limit.

#### Acceptance Criteria

1. FOR ALL datasets of N items and any `limit` value L where 1 ≤ L ≤ N, collecting all pages by following `next_cursor` until `has_more` is `false` SHALL yield exactly N items in `(created_at DESC, id DESC)` order (completeness property).
2. FOR ALL datasets and limit values, no item SHALL appear in more than one page when pages are collected by following `next_cursor` sequentially (non-overlap property).
3. WHEN `has_more` is `false`, the `next_cursor` SHALL be `null` (consistency invariant).
4. WHEN `has_more` is `true`, the `next_cursor` SHALL be a non-empty string that decodes to a valid `Cursor_Position` (round-trip property).

---

### Requirement 11: Invalid Cursor Rejection

**User Story:** As the system, I want tampered or malformed cursor values to be rejected with a 422 error, so that clients receive a clear error rather than undefined query behaviour.

#### Acceptance Criteria

1. WHEN a `cursor` value is a valid base64url string but decodes to JSON that does not contain both `"created_at"` and `"id"` fields, THE `Bookings_API` SHALL return HTTP 422 with error code `VALIDATION_INVALID_CURSOR`.
2. WHEN a `cursor` value is a valid base64url string but decodes to JSON that does not contain both `"created_at"` and `"id"` fields, THE `Notifications_API` SHALL return HTTP 422 with error code `VALIDATION_INVALID_CURSOR`.
3. WHEN a `cursor` value contains characters outside the base64url alphabet, THE `Bookings_API` SHALL return HTTP 422 with error code `VALIDATION_INVALID_CURSOR`.
4. WHEN a `cursor` value contains characters outside the base64url alphabet, THE `Notifications_API` SHALL return HTTP 422 with error code `VALIDATION_INVALID_CURSOR`.
5. WHEN a `cursor` value is a valid base64url string that decodes to valid JSON but the `"created_at"` field is not a parseable ISO-8601 UTC timestamp, THE `Bookings_API` SHALL return HTTP 422 with error code `VALIDATION_INVALID_CURSOR`.
6. WHEN a `cursor` value is a valid base64url string that decodes to valid JSON but the `"id"` field is not a parseable UUID, THE `Notifications_API` SHALL return HTTP 422 with error code `VALIDATION_INVALID_CURSOR`.
