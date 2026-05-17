# Implementation Plan

## Overview

Fix the availability lock double-booking race condition in `BookingService._acquire_lock` by replacing the plain `SELECT` with `SELECT ... FOR UPDATE NOWAIT`, adding `_get_availability_row_for_update`, and handling both `LockNotAvailableError` and `IntegrityError` with clean HTTP 409 responses.

## Task Dependency Graph

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1"] },
    { "wave": 2, "tasks": ["2"] },
    { "wave": 3, "tasks": ["3"] },
    { "wave": 4, "tasks": ["4"] },
    { "wave": 5, "tasks": ["5"] }
  ]
}
```

Tasks 1 and 4 can be written before the fix is applied (task 1 must fail on unfixed code; task 4 must pass on unfixed code). Task 3 validates the fix. Task 5 runs the full suite.

## Tasks

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Concurrent Lock Acquisition Double-Booking Race
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists.
  - **DO NOT attempt to fix the test or the code when it fails.**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation.
  - **GOAL**: Surface counterexamples that demonstrate the double-booking race on unfixed `_acquire_lock`.
  - **Scoped PBT Approach**: Scope the property to the three concrete failing cases (double-UPDATE, double-INSERT, expired-lock race) to ensure reproducibility in the SQLite test environment.
  - Create `packages/backend/tests/test_availability_lock_bug_condition.py`
  - **Test 1 — Double-UPDATE race** (existing `available` row):
    - Pre-insert a `VendorAvailability` row with `status=available` directly into the test DB session.
    - Fire two concurrent `_acquire_lock` calls via `asyncio.gather` on the same `(vendor_id, service_id, date)`.
    - On unfixed code: both calls return without error — double-booking confirmed.
    - Expected behavior (post-fix): exactly one succeeds, the other raises `HTTPException` 409 `CONFLICT_DATE_BEING_PROCESSED`.
    - Assert: `exactly_one_of(result1, result2)` raises 409 `CONFLICT_DATE_BEING_PROCESSED`.
  - **Test 2 — Double-INSERT race** (no pre-existing row):
    - No row exists for the slot.
    - Fire two concurrent `_acquire_lock` calls via `asyncio.gather`.
    - On unfixed code: the second call raises an unhandled `IntegrityError` (500-level), not a clean 409.
    - Expected behavior (post-fix): the second call raises `HTTPException` 409 `CONFLICT_DATE_BEING_PROCESSED`.
    - Assert: the exception raised is `HTTPException` with status 409 and code `CONFLICT_DATE_BEING_PROCESSED`.
  - **Test 3 — Expired-lock race** (row with expired `locked` status):
    - Pre-insert a row with `status=locked` and `locked_until` set to a past timestamp.
    - Fire two concurrent `_acquire_lock` calls via `asyncio.gather`.
    - On unfixed code: both treat the expired lock as available and both succeed.
    - Expected behavior (post-fix): exactly one succeeds, the other raises 409 `CONFLICT_DATE_BEING_PROCESSED`.
    - Assert: `exactly_one_of(result1, result2)` raises 409 `CONFLICT_DATE_BEING_PROCESSED`.
  - **SQLite concurrency note**: SQLite in-memory does not support true concurrent transactions. Mock `_get_availability_row_for_update` on the second call to raise `LockNotAvailableError` (or simulate the race by calling `_acquire_lock` sequentially with a shared mutable state) to validate the error-mapping logic without requiring PostgreSQL.
  - Run test on UNFIXED code.
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct — it proves the bug exists).
  - Document counterexamples found (e.g., "both `_acquire_lock` calls returned successfully — double-booking confirmed").
  - Mark task complete when tests are written, run, and failures are documented.
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Implement the fix
  - Apply the fix to `packages/backend/src/services/booking_service.py` based on understanding from task 1.
  - _Bug_Condition: isBugCondition(R1, R2) where R1.vendor_id = R2.vendor_id AND R1.service_id = R2.service_id AND R1.event_date = R2.event_date AND both execute _acquire_lock concurrently within the SELECT→UPDATE/INSERT window_
  - _Expected_Behavior: exactly one _acquire_lock call succeeds; all others immediately raise HTTPException 409 CONFLICT_DATE_BEING_PROCESSED_
  - _Preservation: all single-request (non-concurrent) paths through _acquire_lock and the entire check_availability read path must produce identical outcomes before and after the fix_
  - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 2.1 Add guarded asyncpg import and IntegrityError import
    - Add at the top of `booking_service.py`, after existing imports:
      ```python
      from sqlalchemy.exc import IntegrityError
      try:
          import asyncpg.exceptions as asyncpg_exc
      except ImportError:
          asyncpg_exc = None  # SQLite test environment — FOR UPDATE not supported
      ```
    - The `try/except ImportError` guard ensures the module loads cleanly in the SQLite test environment where asyncpg is not installed.
    - _Requirements: 2.1, 2.3_

  - [x] 2.2 Add `_get_availability_row_for_update` helper method
    - Add a new private async method to `BookingService` that issues `SELECT ... FOR UPDATE NOWAIT`:
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
    - This method is used exclusively inside `_acquire_lock` — never by the read-only `check_availability` path.
    - `_get_availability_row` (plain SELECT, no lock) remains unchanged for `check_availability`.
    - _Requirements: 2.2, 3.6_

  - [x] 2.3 Rewrite `_acquire_lock` to use `_get_availability_row_for_update`
    - Replace the call to `_get_availability_row` with `_get_availability_row_for_update`.
    - Wrap the `session.execute` call in a `try/except` that catches `LockNotAvailableError` (asyncpg row-lock contention) and maps it to HTTP 409 `CONFLICT_DATE_BEING_PROCESSED`:
      ```python
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
      ```
    - Keep all existing status-check branches (BOOKED → 409, BLOCKED → 409, active LOCKED → 409, expired LOCKED → treat as available) exactly as they are.
    - _Bug_Condition: isBugCondition(R1, R2) — concurrent SELECT without FOR UPDATE_
    - _Requirements: 2.1, 2.2_

  - [x] 2.4 Handle concurrent INSERT via IntegrityError on `session.flush()`
    - In the `else` branch (no existing row), wrap `await session.flush()` in a `try/except IntegrityError`:
      ```python
      else:
          row = VendorAvailability(
              vendor_id=vendor_id,
              service_id=service_id,
              date=check_date,
              status=AvailabilityStatus.LOCKED,
              locked_by=user_id,
              locked_until=now + timedelta(seconds=LOCK_TTL_SECONDS),
              locked_reason="booking_in_progress",
          )
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
      ```
    - This eliminates the unhandled 500 on concurrent INSERT that violates `uq_vendor_service_date`.
    - _Bug_Condition: concurrent INSERT race on uq_vendor_service_date unique constraint_
    - _Requirements: 2.3_

- [x] 3. Write fix-checking tests (concurrent lock tests + IntegrityError handling)
  - Create `packages/backend/tests/test_availability_lock_fix_checking.py`
  - These tests verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.
  - **SQLite constraint**: Mock `_get_availability_row_for_update` to raise `LockNotAvailableError` on the second call; mock `session.flush` to raise `IntegrityError` for the INSERT race test. This validates the error-mapping logic without requiring PostgreSQL.

  - [x] 3.1 Verify `_get_availability_row_for_update` issues a FOR UPDATE NOWAIT query
    - Mock `session.execute` and assert the SQLAlchemy statement has `.with_for_update(nowait=True)` set.
    - Assert `_get_availability_row` (plain SELECT) does NOT have `for_update` set — read-only path is unaffected.
    - _Requirements: 2.2, 3.6_

  - [x] 3.2 Verify `_acquire_lock` catches `LockNotAvailableError` and raises HTTP 409
    - Mock `_get_availability_row_for_update` to raise an exception whose `__cause__` is `asyncpg.exceptions.LockNotAvailableError`.
    - Assert `_acquire_lock` raises `HTTPException` with `status_code=409` and `detail["code"] == "CONFLICT_DATE_BEING_PROCESSED"`.
    - _Requirements: 2.1_

  - [x] 3.3 Verify `_acquire_lock` catches `IntegrityError` on `session.flush()` and raises HTTP 409
    - Pre-insert no row (so `_acquire_lock` reaches the INSERT branch).
    - Mock `session.flush` to raise `sqlalchemy.exc.IntegrityError`.
    - Assert `_acquire_lock` raises `HTTPException` with `status_code=409` and `detail["code"] == "CONFLICT_DATE_BEING_PROCESSED"`.
    - _Requirements: 2.3_

  - [x] 3.4 Verify concurrent lock acquisition — exactly one succeeds (mocked FOR UPDATE)
    - **Property 1: Expected Behavior** - Concurrent Lock Acquisition Is Mutually Exclusive
    - **IMPORTANT**: Re-run the SAME scenario from task 1 — do NOT write a new test.
    - Mock `_get_availability_row_for_update`: first call returns the available row normally; second call raises `LockNotAvailableError` (simulating PostgreSQL NOWAIT contention).
    - Fire two concurrent `_acquire_lock` calls via `asyncio.gather`.
    - Assert: exactly one call succeeds (returns a `VendorAvailability` row with `status=locked`); the other raises `HTTPException` 409 `CONFLICT_DATE_BEING_PROCESSED`.
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed).
    - _Requirements: 2.1, 2.2_

  - [x] 3.5 Verify concurrent INSERT race — second request gets 409 not 500
    - Mock `session.flush` to raise `IntegrityError` on the second call.
    - Assert the second `_acquire_lock` call raises `HTTPException` 409 `CONFLICT_DATE_BEING_PROCESSED` (not an unhandled `IntegrityError` 500).
    - **EXPECTED OUTCOME**: Test PASSES (confirms clean 409 instead of 500).
    - _Requirements: 2.3_

- [x] 4. Write preservation property-based tests (BEFORE verifying fix — observe on unfixed code first)
  - **Property 2: Preservation** - Non-Concurrent Single-Request Behavior Is Unchanged
  - **IMPORTANT**: Follow observation-first methodology.
  - Create `packages/backend/tests/test_availability_lock_preservation.py`
  - **Observation step** (run on unfixed code to record baseline):
    - Observe: `_acquire_lock` on an `available` slot → returns row with `status=locked` ✓
    - Observe: `_acquire_lock` on a `booked` slot → raises 409 `CONFLICT_DATE_UNAVAILABLE` ✓
    - Observe: `_acquire_lock` on a `blocked` slot → raises 409 `CONFLICT_DATE_UNAVAILABLE` ✓
    - Observe: `_acquire_lock` on an active `locked` slot (`locked_until > now`) → raises 409 `CONFLICT_DATE_BEING_PROCESSED` ✓
    - Observe: `_acquire_lock` on an expired `locked` slot (`locked_until <= now`) → returns row with `status=locked` ✓
    - Observe: `check_availability` for any slot → returns correct status dict, no write lock acquired ✓
  - Write property-based tests capturing these observed behaviors using `hypothesis`.
  - Verify tests PASS on UNFIXED code (confirms baseline behavior to preserve).
  - **EXPECTED OUTCOME**: Tests PASS on unfixed code (confirms baseline); must also PASS after fix (confirms no regressions).
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 4.1 Property: available slot → lock acquired, status=locked
    - **Property 2a: Preservation** - Available Slot Lock Acquisition
    - Use `hypothesis` to generate random `(vendor_id, service_id, date)` UUIDs and date values.
    - For each generated input: mock `_get_availability_row_for_update` to return an `available` row; assert `_acquire_lock` returns a row with `status=locked`.
    - Validates: for all non-concurrent single requests on available slots, the happy path is unaffected.
    - _Requirements: 3.1_

  - [x] 4.2 Property: booked slot → 409 CONFLICT_DATE_UNAVAILABLE
    - **Property 2b: Preservation** - Booked Slot Rejection
    - Use `hypothesis` to generate random `(vendor_id, service_id, date)` values.
    - For each: mock `_get_availability_row_for_update` to return a `booked` row; assert `_acquire_lock` raises `HTTPException` 409 `CONFLICT_DATE_UNAVAILABLE`.
    - _Requirements: 3.2_

  - [x] 4.3 Property: blocked slot → 409 CONFLICT_DATE_UNAVAILABLE
    - **Property 2c: Preservation** - Blocked Slot Rejection
    - Use `hypothesis` to generate random `(vendor_id, service_id, date)` values.
    - For each: mock `_get_availability_row_for_update` to return a `blocked` row; assert `_acquire_lock` raises `HTTPException` 409 `CONFLICT_DATE_UNAVAILABLE`.
    - _Requirements: 3.3_

  - [x] 4.4 Property: active locked slot → 409 CONFLICT_DATE_BEING_PROCESSED
    - **Property 2d: Preservation** - Active Lock Rejection
    - Use `hypothesis` to generate random `(vendor_id, service_id, date)` values and future `locked_until` timestamps.
    - For each: mock `_get_availability_row_for_update` to return a `locked` row with `locked_until > now`; assert `_acquire_lock` raises `HTTPException` 409 `CONFLICT_DATE_BEING_PROCESSED`.
    - _Requirements: 3.4_

  - [x] 4.5 Property: expired locked slot → treated as available, lock acquired
    - **Property 2e: Preservation** - Expired Lock Re-acquisition
    - Use `hypothesis` to generate random `(vendor_id, service_id, date)` values and past `locked_until` timestamps.
    - For each: mock `_get_availability_row_for_update` to return a `locked` row with `locked_until <= now`; assert `_acquire_lock` returns a row with `status=locked` (treated as available).
    - _Requirements: 3.5_

  - [x] 4.6 Property: `check_availability` read path is unaffected (no FOR UPDATE)
    - **Property 2f: Preservation** - Read-Only Path Unchanged
    - Assert `_get_availability_row` (used by `check_availability`) does NOT use `.with_for_update()` — the read-only path must remain lock-free.
    - Use `hypothesis` to generate random slot states (`available`, `booked`, `blocked`, `locked` with active/expired TTL) and verify `check_availability` returns the correct `{"available": bool}` dict for each.
    - _Requirements: 3.6_

- [x] 5. Checkpoint — Run full test suite and verify no regressions
  - Run `uv run pytest` from `packages/backend`.
  - Ensure all tests pass, ask the user if questions arise.
  - Verify:
    - Task 1 exploration tests now PASS (bug is fixed — Property 1: Expected Behavior confirmed).
    - Task 3 fix-checking tests PASS (concurrent lock and IntegrityError handling confirmed).
    - Task 4 preservation tests PASS (no regressions in single-request paths — Property 2: Preservation confirmed).
    - All pre-existing tests in `test_booking_service.py`, `test_vendor_availability_service.py`, and the full suite continue to PASS.
  - If any test fails, diagnose root cause before patching.

## Notes

- All tests run against SQLite in-memory (`sqlite+aiosqlite:///:memory:`). SQLite does not support `SELECT ... FOR UPDATE`, so concurrency tests must mock `_get_availability_row_for_update` to simulate PostgreSQL lock contention.
- The `asyncpg` import in `booking_service.py` must be guarded with `try/except ImportError` so the module loads cleanly in the SQLite test environment.
- Run tests with `uv run pytest` from `packages/backend`.
- For true end-to-end concurrency validation against PostgreSQL, a separate integration test file (skipped in SQLite CI) would be needed — that is out of scope for this task list.
- Property-based tests use `hypothesis` with `max_examples=3` and `suppress_health_check=[HealthCheck.function_scoped_fixture]` to match the project's existing PBT pattern (see `test_otp_preservation.py`).
