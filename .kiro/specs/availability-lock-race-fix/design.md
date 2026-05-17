# Availability Lock Race Condition Bugfix Design

## Overview

`BookingService._acquire_lock` currently performs a plain `SELECT` (via `_get_availability_row`)
followed by a conditional `UPDATE`/`INSERT`. Because no row-level database lock is held between
the read and the write, two concurrent `POST /api/v1/bookings` requests for the same
`vendor_id + service_id + event_date` can both observe the slot as available, both pass the
status check, and both write `status=locked` — resulting in a double-booking.

**Fix strategy:** Replace the plain `SELECT` inside `_acquire_lock` with
`SELECT ... FOR UPDATE NOWAIT` via SQLAlchemy's `.with_for_update(nowait=True)`. This acquires
a PostgreSQL exclusive row-level lock atomically. A concurrent request that cannot immediately
acquire the lock receives `asyncpg.exceptions.LockNotAvailableError`, which is caught and mapped
to HTTP 409 `CONFLICT_DATE_BEING_PROCESSED`. For slots with no existing row, the first `INSERT`
wins via the `uq_vendor_service_date` unique constraint; a concurrent insert raises
`IntegrityError`, which is also caught and mapped to 409.

The read-only path (`_get_availability_row`, used by `check_availability`) is **not changed** —
it remains a plain `SELECT` with no write lock.

---

## Glossary

- **Bug_Condition (C)**: Two or more concurrent `_acquire_lock` calls for the same
  `(vendor_id, service_id, event_date)` tuple that both read the slot as available before either
  has committed a lock.
- **Property (P)**: For any input where C holds, exactly one call succeeds and all others
  immediately receive HTTP 409 `CONFLICT_DATE_BEING_PROCESSED`.
- **Preservation**: All single-request (non-concurrent) paths through `_acquire_lock` and the
  entire `check_availability` read path must produce identical outcomes before and after the fix.
- **`_acquire_lock`**: The method in `BookingService`
  (`packages/backend/src/services/booking_service.py`) responsible for atomically reserving a
  `vendor_availability` slot before a booking is created.
- **`_get_availability_row`**: Plain `SELECT` helper used by the read-only
  `check_availability` path — must remain lock-free.
- **`_get_availability_row_for_update`**: New internal helper that issues
  `SELECT ... FOR UPDATE NOWAIT` — used exclusively inside `_acquire_lock`.
- **`uq_vendor_service_date`**: The PostgreSQL unique constraint on
  `(vendor_id, service_id, date)` in `vendor_availability` that prevents duplicate rows.
- **`LockNotAvailableError`**: `asyncpg.exceptions.LockNotAvailableError` — raised by asyncpg
  when `NOWAIT` cannot acquire the row lock immediately.
- **`IntegrityError`**: `sqlalchemy.exc.IntegrityError` — raised when a concurrent `INSERT`
  violates `uq_vendor_service_date`.

---

## Bug Details

### Bug Condition

The bug manifests when two or more concurrent `POST /api/v1/bookings` requests arrive for the
same `vendor_id`, `service_id`, and `event_date`. The `_acquire_lock` method reads the
availability row (or finds it absent) without holding any database lock, so both requests
observe the slot as available and both proceed to write `status=locked` — or both attempt to
`INSERT` a new row — before either transaction commits.

**Formal Specification:**

```
FUNCTION isBugCondition(R1, R2)
  INPUT:  R1, R2 of type BookingRequest
  OUTPUT: boolean

  RETURN R1.vendor_id  = R2.vendor_id
     AND R1.service_id = R2.service_id
     AND R1.event_date = R2.event_date
     AND R1 and R2 execute _acquire_lock concurrently
         such that both complete the SELECT before either commits the UPDATE/INSERT
END FUNCTION
```

### Examples

- **Double-UPDATE race**: Two requests both read `status=available`, both pass the status check,
  both execute `UPDATE vendor_availability SET status='locked' ...` — the second silently
  overwrites the first, and both proceed to create a `Booking` record for the same slot.
- **Double-INSERT race**: No row exists yet; both requests reach the `INSERT` branch; the second
  `INSERT` raises an unhandled `IntegrityError` (500) instead of a clean 409.
- **Expired-lock race**: A row exists with an expired `locked` status; both requests treat it as
  available and both attempt to update it to `locked` simultaneously.
- **Single request (non-buggy)**: One request for an available slot — lock acquired, booking
  created, 201 returned. This path must be unaffected by the fix.

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

- A single (non-concurrent) request for an available slot SHALL continue to acquire the lock,
  create the booking, and return HTTP 201.
- A request for a `BOOKED` slot SHALL continue to return HTTP 409 `CONFLICT_DATE_UNAVAILABLE`.
- A request for a `BLOCKED` slot SHALL continue to return HTTP 409 `CONFLICT_DATE_UNAVAILABLE`.
- A request for a slot with an active (non-expired) `LOCKED` status SHALL continue to return
  HTTP 409 `CONFLICT_DATE_BEING_PROCESSED`.
- A request for a slot with an **expired** `LOCKED` status SHALL continue to be treated as
  available and proceed with locking and booking.
- `check_availability` SHALL continue to return the correct availability status without
  acquiring any write lock (read-only path is unaffected).
- `VendorAvailabilityService.upsert_availability` and `bulk_upsert_availability` SHALL continue
  to perform upserts correctly (these paths are not touched by the fix).

**Scope:**

All inputs that do NOT involve two or more concurrent requests racing on the same slot should be
completely unaffected by this fix. This includes:

- Any single booking request (no concurrency)
- `check_availability` calls (read-only, no lock)
- Vendor availability management via `VendorAvailabilityService`
- Status transitions (`confirm`, `cancel`, `reject`) on existing bookings

---

## Hypothesized Root Cause

Based on the bug description and code analysis, the root causes are:

1. **No row-level lock on read**: `_acquire_lock` calls `_get_availability_row`, which issues a
   plain `SELECT` with no `FOR UPDATE`. PostgreSQL does not prevent concurrent transactions from
   reading the same row simultaneously, so the check-then-act pattern is not atomic.

2. **TOCTOU (Time-of-Check to Time-of-Use) gap**: The window between the `SELECT` and the
   subsequent `UPDATE`/`INSERT` is unprotected. Under concurrent load, both transactions pass
   the availability check before either commits, making the guard condition ineffective.

3. **Unhandled `IntegrityError` on concurrent INSERT**: When no row exists, both transactions
   reach the `else` branch and call `session.add(row)` + `session.flush()`. The second flush
   raises `sqlalchemy.exc.IntegrityError` on `uq_vendor_service_date`, which propagates as an
   unhandled 500 instead of a clean 409.

4. **No contention signal from the database**: The current code relies entirely on application-
   level status checks. There is no mechanism to detect that another transaction is mid-flight
   on the same row, so the database cannot signal contention back to the application.

---

## Correctness Properties

Property 1: Bug Condition — Concurrent Lock Acquisition Is Mutually Exclusive

_For any_ pair of concurrent `_acquire_lock` calls `(R1, R2)` where `isBugCondition(R1, R2)`
returns true (same `vendor_id`, `service_id`, `event_date`, concurrent execution), the fixed
`_acquire_lock` SHALL allow exactly one call to succeed (acquire the lock and proceed) and the
other SHALL immediately raise `HTTPException` with status 409 and error code
`CONFLICT_DATE_BEING_PROCESSED`, ensuring no double-booking can occur.

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation — Non-Concurrent Single-Request Behavior Is Unchanged

_For any_ single (non-concurrent) `_acquire_lock` call where `isBugCondition` does NOT hold,
the fixed `_acquire_lock` SHALL produce the same outcome as the original `_acquire_lock`:
available slots are locked and the call succeeds; `BOOKED`/`BLOCKED` slots raise 409
`CONFLICT_DATE_UNAVAILABLE`; active `LOCKED` slots raise 409 `CONFLICT_DATE_BEING_PROCESSED`;
expired `LOCKED` slots are treated as available — preserving all existing single-request
behavior exactly.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

---

## Fix Implementation

### Changes Required

**File**: `packages/backend/src/services/booking_service.py`

**Specific Changes**:

1. **Add imports**: Import `asyncpg.exceptions` and `sqlalchemy.exc.IntegrityError` at the top
   of the file.
   ```python
   from sqlalchemy.exc import IntegrityError
   try:
       import asyncpg.exceptions as asyncpg_exc
   except ImportError:
       asyncpg_exc = None  # SQLite test environment
   ```

2. **Add `_get_availability_row_for_update` helper**: New private method that issues
   `SELECT ... FOR UPDATE NOWAIT` using SQLAlchemy's `.with_for_update(nowait=True)`. This is
   used exclusively inside `_acquire_lock` and never by the read-only `check_availability` path.
   ```python
   async def _get_availability_row_for_update(
       self,
       session: AsyncSession,
       vendor_id: uuid.UUID,
       service_id: uuid.UUID,
       check_date: date_type,
   ) -> Optional[VendorAvailability]:
       stmt = (
           select(VendorAvailability)
           .where(
               VendorAvailability.vendor_id == vendor_id,
               VendorAvailability.service_id == service_id,
               VendorAvailability.date == check_date,
           )
           .with_for_update(nowait=True)
       )
       result = await session.execute(stmt)
       return result.scalar_one_or_none()
   ```

3. **Rewrite `_acquire_lock` to use the new helper**: Replace the call to
   `_get_availability_row` with `_get_availability_row_for_update`. Wrap the entire method body
   in a `try/except` that catches `LockNotAvailableError` (asyncpg contention) and
   `IntegrityError` (concurrent INSERT collision), both mapped to 409
   `CONFLICT_DATE_BEING_PROCESSED`.

4. **INSERT-first for missing rows**: When no row exists, `INSERT` directly (no prior `SELECT`)
   and catch `IntegrityError` from the unique constraint. This eliminates the double-SELECT
   pattern and ensures the constraint is the sole arbiter for new rows.

5. **Catch `LockNotAvailableError`**: Wrap the `session.execute(stmt)` call (or the entire
   method) to catch `asyncpg.exceptions.LockNotAvailableError` and raise HTTP 409
   `CONFLICT_DATE_BEING_PROCESSED`. Guard the import with a try/except so the code still loads
   in the SQLite test environment.

**File**: `packages/backend/src/services/booking_service.py` — `_acquire_lock` method outline:

```python
async def _acquire_lock(self, session, vendor_id, service_id, check_date, user_id):
    now = datetime.now(timezone.utc)
    try:
        row = await self._get_availability_row_for_update(
            session, vendor_id, service_id, check_date
        )
    except Exception as exc:
        if asyncpg_exc and isinstance(exc.__cause__, asyncpg_exc.LockNotAvailableError):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_err("CONFLICT_DATE_BEING_PROCESSED",
                            "This date is temporarily held by another request."),
            )
        raise

    if row is not None:
        # existing status checks (BOOKED → 409, BLOCKED → 409, active LOCKED → 409)
        # expired LOCKED or AVAILABLE → update row in place
        ...
    else:
        # No row — INSERT directly; catch IntegrityError from concurrent INSERT
        row = VendorAvailability(...)
        session.add(row)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_err("CONFLICT_DATE_BEING_PROCESSED",
                            "This date is temporarily held by another request."),
            )
    return row
```

---

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that
demonstrate the bug on unfixed code (exploratory), then verify the fix works correctly and
preserves existing behavior (fix + preservation checking).

**Important constraint**: SQLite (used in the test suite via `sqlite+aiosqlite:///:memory:`)
does **not** support `SELECT ... FOR UPDATE`. Tests that exercise the new locking path must
either mock `_acquire_lock` / `_get_availability_row_for_update`, or run as separate
integration tests against a real PostgreSQL instance. The existing unit/integration test suite
uses SQLite and must not be broken.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the double-booking race on the **unfixed**
code. Confirm or refute the root cause analysis.

**Test Plan**: Simulate two concurrent calls to `_acquire_lock` on the same slot using
`asyncio.gather`. On unfixed code, both calls should succeed (no exception), demonstrating the
double-booking. On fixed code, exactly one should succeed and the other should raise 409.

**Test Cases**:

1. **Concurrent lock on existing available row** (will demonstrate bug on unfixed code):
   Pre-insert a `VendorAvailability` row with `status=available`. Fire two concurrent
   `_acquire_lock` calls. On unfixed code, both return without error — double-booking confirmed.

2. **Concurrent INSERT on missing row** (will raise unhandled IntegrityError on unfixed code):
   No row exists. Fire two concurrent `_acquire_lock` calls. On unfixed code, the second raises
   an unhandled `IntegrityError` (500). On fixed code, the second raises 409.

3. **Concurrent lock on expired-locked row** (will demonstrate bug on unfixed code):
   Pre-insert a row with `status=locked` and `locked_until` in the past. Fire two concurrent
   calls. On unfixed code, both treat it as available and both succeed.

**Expected Counterexamples**:

- Both `_acquire_lock` calls return successfully on unfixed code (no exception raised), proving
  the check-then-act pattern is not atomic.
- Possible causes: no `FOR UPDATE` on the `SELECT`, no `IntegrityError` handling on `INSERT`.

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces
the expected behavior (exactly one succeeds, the other gets 409).

**Pseudocode:**

```
FOR ALL (R1, R2) WHERE isBugCondition(R1, R2) DO
  (result1, result2) ← concurrent(_acquire_lock_fixed(R1), _acquire_lock_fixed(R2))
  ASSERT exactly_one_of(result1, result2) raises HTTP 409 CONFLICT_DATE_BEING_PROCESSED
  AND    the_other returns a VendorAvailability row with status=locked
END FOR
```

**Test approach for SQLite environment**: Mock `_get_availability_row_for_update` to raise
`LockNotAvailableError` on the second call, then assert the method raises HTTP 409. This
validates the error-mapping logic without requiring PostgreSQL.

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (single, non-
concurrent requests), the fixed function produces the same result as the original.

**Pseudocode:**

```
FOR ALL R WHERE NOT isBugCondition(R) DO
  ASSERT _acquire_lock_original(R) = _acquire_lock_fixed(R)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:

- It generates many test cases automatically across the input domain (different slot states,
  different user IDs, different dates).
- It catches edge cases that manual unit tests might miss (e.g., expired locks with various TTLs).
- It provides strong guarantees that behavior is unchanged for all non-concurrent inputs.

**Test Plan**: Observe behavior on unfixed code for each slot state, then write property-based
tests that verify the same outcomes after the fix.

**Test Cases**:

1. **Available slot preservation**: For any `(vendor_id, service_id, date)` where the slot is
   `available`, `_acquire_lock` must succeed and return a row with `status=locked`.
2. **BOOKED slot preservation**: For any slot with `status=booked`, `_acquire_lock` must raise
   HTTP 409 `CONFLICT_DATE_UNAVAILABLE`.
3. **BLOCKED slot preservation**: For any slot with `status=blocked`, `_acquire_lock` must raise
   HTTP 409 `CONFLICT_DATE_UNAVAILABLE`.
4. **Active LOCKED slot preservation**: For any slot with `status=locked` and
   `locked_until > now`, `_acquire_lock` must raise HTTP 409 `CONFLICT_DATE_BEING_PROCESSED`.
5. **Expired LOCKED slot preservation**: For any slot with `status=locked` and
   `locked_until <= now`, `_acquire_lock` must succeed (treat as available).

### Unit Tests

- Test `_get_availability_row_for_update` issues a query with `.with_for_update(nowait=True)`
  (mock `session.execute` and assert the statement has `for_update` set).
- Test `_acquire_lock` catches `LockNotAvailableError` and raises HTTP 409
  `CONFLICT_DATE_BEING_PROCESSED` (mock the helper to raise the error).
- Test `_acquire_lock` catches `IntegrityError` on `session.flush()` and raises HTTP 409
  `CONFLICT_DATE_BEING_PROCESSED` (mock `session.flush` to raise `IntegrityError`).
- Test all existing status-check branches (BOOKED, BLOCKED, active LOCKED, expired LOCKED)
  still raise the correct HTTP exceptions after the refactor.
- Test that `_get_availability_row` (used by `check_availability`) does NOT use
  `.with_for_update()` — the read-only path must remain lock-free.

### Property-Based Tests

- Generate random `AvailabilityStatus` values and verify that `_acquire_lock` raises the correct
  exception for each non-available status (preservation of status-check logic).
- Generate random `locked_until` timestamps (past and future) and verify the expired-lock
  branch behaves correctly across many time values.
- Generate random `(vendor_id, service_id, date)` tuples and verify that a single call to
  `_acquire_lock` on an available slot always succeeds and sets `status=locked` (no regression
  in the happy path).

### Integration Tests

- **PostgreSQL only** (separate test file, skipped in SQLite CI): Test two concurrent
  `POST /api/v1/bookings` requests for the same slot; assert exactly one returns 201 and the
  other returns 409 `CONFLICT_DATE_BEING_PROCESSED`.
- **PostgreSQL only**: Test concurrent INSERT race (no pre-existing row); assert the second
  request returns 409 `CONFLICT_DATE_BEING_PROCESSED` (not 500).
- Test the full booking creation flow (single request) end-to-end via `POST /api/v1/bookings`
  to confirm the happy path is unaffected (runs in SQLite with mocked `_acquire_lock`).
- Test `GET /api/v1/vendors/{id}/availability` (check_availability) to confirm it still returns
  correct status without acquiring any write lock.
