"""
Fix-Checking Tests — Availability Lock Race Condition

**Validates: Requirements 2.2, 3.6**

Task 3.1: Verify `_get_availability_row_for_update` issues a FOR UPDATE NOWAIT query.

These tests inspect the SQLAlchemy statement object directly (no DB execution needed)
to confirm:

  1. `_get_availability_row_for_update` builds a statement with
     `.with_for_update(nowait=True)` — the locking helper is correctly constructed.

  2. `_get_availability_row` (plain SELECT) does NOT have `for_update` set —
     the read-only path used by `check_availability` is unaffected.
"""
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.booking_service import booking_service


# ── Task 3.1 — Statement-level FOR UPDATE NOWAIT inspection ──────────────────


@pytest.mark.asyncio
async def test_for_update_helper_uses_nowait():
    """
    `_get_availability_row_for_update` must build a SELECT … FOR UPDATE NOWAIT
    statement.

    We mock `session.execute` to capture the statement passed to it, then
    inspect the SQLAlchemy `_for_update_arg` attribute directly — no DB needed.

    **Validates: Requirements 2.2, 3.6**
    """
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    vendor_id = uuid.uuid4()
    service_id = uuid.uuid4()
    check_date = date(2028, 8, 15)

    await booking_service._get_availability_row_for_update(
        mock_session, vendor_id, service_id, check_date
    )

    # Confirm session.execute was called exactly once
    mock_session.execute.assert_called_once()

    # Extract the statement passed as the first positional argument
    call_args = mock_session.execute.call_args
    stmt = call_args[0][0]  # first positional arg

    # SQLAlchemy 2.x: Select._for_update_arg is a ForUpdateArg instance when
    # .with_for_update() is used, or None for a plain SELECT.
    assert stmt._for_update_arg is not None, (
        "_get_availability_row_for_update must use .with_for_update() — "
        "_for_update_arg is None (plain SELECT detected)"
    )
    assert stmt._for_update_arg.nowait is True, (
        "_get_availability_row_for_update must use .with_for_update(nowait=True) — "
        f"nowait={stmt._for_update_arg.nowait!r} (expected True)"
    )


@pytest.mark.asyncio
async def test_plain_select_helper_has_no_for_update():
    """
    `_get_availability_row` (used by the read-only `check_availability` path)
    must NOT use FOR UPDATE — it must remain a plain SELECT.

    We mock `session.execute` to capture the statement, then assert that
    `_for_update_arg` is None.

    **Validates: Requirements 2.2, 3.6**
    """
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    vendor_id = uuid.uuid4()
    service_id = uuid.uuid4()
    check_date = date(2028, 8, 15)

    await booking_service._get_availability_row(
        mock_session, vendor_id, service_id, check_date
    )

    # Confirm session.execute was called exactly once
    mock_session.execute.assert_called_once()

    # Extract the statement
    call_args = mock_session.execute.call_args
    stmt = call_args[0][0]

    # Plain SELECT must have no FOR UPDATE clause
    assert stmt._for_update_arg is None, (
        "_get_availability_row must be a plain SELECT with no FOR UPDATE — "
        f"_for_update_arg={stmt._for_update_arg!r} (expected None). "
        "The read-only check_availability path must not acquire write locks."
    )


# ── Shared fake exception classes (used by tasks 3.2 and 3.4) ────────────────


class FakeLockNotAvailableError(Exception):
    """Stands in for asyncpg.exceptions.LockNotAvailableError in the test env."""


class FakeDBError(Exception):
    """Wraps FakeLockNotAvailableError as __cause__, mimicking asyncpg wrapping."""

    def __init__(self):
        super().__init__()
        self.__cause__ = FakeLockNotAvailableError()


# ── Task 3.2 — _acquire_lock catches LockNotAvailableError → HTTP 409 ────────


@pytest.mark.asyncio
async def test_acquire_lock_raises_409_on_lock_not_available():
    """
    When `_get_availability_row_for_update` raises an exception whose __cause__
    is `asyncpg.exceptions.LockNotAvailableError`, `_acquire_lock` must catch it
    and raise HTTPException 409 CONFLICT_DATE_BEING_PROCESSED.

    We patch `booking_service_module.asyncpg_exc` so the isinstance check works
    with our fake exception class, and mock `_get_availability_row_for_update`
    to raise FakeDBError (which carries FakeLockNotAvailableError as __cause__).

    **Validates: Requirements 2.1**
    """
    from fastapi import HTTPException
    import src.services.booking_service as booking_service_module

    mock_asyncpg_exc = MagicMock()
    mock_asyncpg_exc.LockNotAvailableError = FakeLockNotAvailableError

    mock_session = AsyncMock()
    vendor_id = uuid.uuid4()
    service_id = uuid.uuid4()
    user_id = uuid.uuid4()
    check_date = date(2028, 9, 10)

    with patch.object(
        booking_service,
        "_get_availability_row_for_update",
        new=AsyncMock(side_effect=FakeDBError()),
    ), patch.object(booking_service_module, "asyncpg_exc", mock_asyncpg_exc):
        with pytest.raises(HTTPException) as exc_info:
            await booking_service._acquire_lock(
                mock_session, vendor_id, service_id, check_date, user_id
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "CONFLICT_DATE_BEING_PROCESSED"


# ── Task 3.3 — _acquire_lock catches IntegrityError on flush → HTTP 409 ──────


@pytest.mark.asyncio
async def test_acquire_lock_raises_409_on_integrity_error_during_insert():
    """
    When no availability row exists (INSERT branch) and `session.flush()` raises
    `sqlalchemy.exc.IntegrityError` (concurrent INSERT race on uq_vendor_service_date),
    `_acquire_lock` must catch it and raise HTTPException 409
    CONFLICT_DATE_BEING_PROCESSED instead of letting the IntegrityError propagate.

    We mock `_get_availability_row_for_update` to return None (no existing row)
    and mock `session.flush` to raise IntegrityError.

    **Validates: Requirements 2.3**
    """
    from fastapi import HTTPException
    from sqlalchemy.exc import IntegrityError

    mock_session = AsyncMock()
    # flush raises IntegrityError — simulates concurrent INSERT collision
    mock_session.flush.side_effect = IntegrityError(None, None, Exception())
    mock_session.rollback = AsyncMock()

    vendor_id = uuid.uuid4()
    service_id = uuid.uuid4()
    user_id = uuid.uuid4()
    check_date = date(2028, 9, 11)

    with patch.object(
        booking_service,
        "_get_availability_row_for_update",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await booking_service._acquire_lock(
                mock_session, vendor_id, service_id, check_date, user_id
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "CONFLICT_DATE_BEING_PROCESSED"


# ── Task 3.4 — Concurrent lock acquisition: exactly one succeeds ─────────────


@pytest.mark.asyncio
async def test_concurrent_lock_acquisition_exactly_one_succeeds():
    """
    Property 1: Expected Behavior — Concurrent Lock Acquisition Is Mutually Exclusive.

    Simulates two concurrent _acquire_lock calls on the same slot:
      - First call: _get_availability_row_for_update returns an available row → succeeds.
      - Second call: _get_availability_row_for_update raises FakeDBError
        (LockNotAvailableError cause) → raises HTTPException 409.

    Asserts exactly one call succeeds (returns VendorAvailability with status=locked)
    and the other raises HTTPException 409 CONFLICT_DATE_BEING_PROCESSED.

    **Validates: Requirements 2.1, 2.2**
    """
    import asyncio
    from fastapi import HTTPException
    from src.models.availability import VendorAvailability, AvailabilityStatus
    import src.services.booking_service as booking_service_module

    mock_asyncpg_exc = MagicMock()
    mock_asyncpg_exc.LockNotAvailableError = FakeLockNotAvailableError

    vendor_id = uuid.uuid4()
    service_id = uuid.uuid4()
    user_id = uuid.uuid4()
    check_date = date(2028, 9, 12)

    # Build an available row that the first call will receive
    available_row = MagicMock(spec=VendorAvailability)
    available_row.status = AvailabilityStatus.AVAILABLE
    available_row.locked_until = None

    # call_count tracks how many times the mock has been invoked
    call_count = {"n": 0}

    async def mock_get_row_for_update(session, vid, sid, cdate):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return available_row
        raise FakeDBError()

    # Each concurrent call needs its own session mock so flush/add don't collide
    mock_session_1 = AsyncMock()
    mock_session_1.flush = AsyncMock()
    mock_session_1.add = MagicMock()

    mock_session_2 = AsyncMock()
    mock_session_2.flush = AsyncMock()
    mock_session_2.add = MagicMock()

    with patch.object(
        booking_service,
        "_get_availability_row_for_update",
        new=mock_get_row_for_update,
    ), patch.object(booking_service_module, "asyncpg_exc", mock_asyncpg_exc):
        results = await asyncio.gather(
            booking_service._acquire_lock(
                mock_session_1, vendor_id, service_id, check_date, user_id
            ),
            booking_service._acquire_lock(
                mock_session_2, vendor_id, service_id, check_date, user_id
            ),
            return_exceptions=True,
        )

    failures = [
        r
        for r in results
        if isinstance(r, HTTPException) and r.status_code == 409
        and r.detail.get("code") == "CONFLICT_DATE_BEING_PROCESSED"
    ]
    # Successes are anything that is NOT an exception
    successes = [r for r in results if not isinstance(r, Exception)]

    assert len(successes) == 1, (
        f"Expected exactly 1 success, got {len(successes)}. Results: {results}"
    )
    assert len(failures) == 1, (
        f"Expected exactly 1 HTTP 409 failure, got {len(failures)}. Results: {results}"
    )
    # The successful result must be the locked row (mock with status updated to LOCKED)
    assert successes[0].status == AvailabilityStatus.LOCKED


# ── Task 3.5 — Concurrent INSERT race: second request gets 409 not 500 ───────


@pytest.mark.asyncio
async def test_concurrent_insert_race_second_request_gets_409_not_500():
    """
    When two concurrent _acquire_lock calls both find no existing row (INSERT branch):
      - First call: session.flush() succeeds → lock acquired.
      - Second call: session.flush() raises IntegrityError (unique constraint) →
        must raise HTTPException 409 CONFLICT_DATE_BEING_PROCESSED, NOT propagate
        the raw IntegrityError (which would surface as a 500).

    **Validates: Requirements 2.3**
    """
    import asyncio
    from fastapi import HTTPException
    from sqlalchemy.exc import IntegrityError

    vendor_id = uuid.uuid4()
    service_id = uuid.uuid4()
    user_id = uuid.uuid4()
    check_date = date(2028, 9, 13)

    flush_call_count = {"n": 0}

    async def mock_flush_side_effect():
        flush_call_count["n"] += 1
        if flush_call_count["n"] >= 2:
            raise IntegrityError(None, None, Exception())

    mock_session_1 = AsyncMock()
    mock_session_1.flush = AsyncMock(side_effect=mock_flush_side_effect)
    mock_session_1.add = MagicMock()
    mock_session_1.rollback = AsyncMock()

    mock_session_2 = AsyncMock()
    mock_session_2.flush = AsyncMock(side_effect=mock_flush_side_effect)
    mock_session_2.add = MagicMock()
    mock_session_2.rollback = AsyncMock()

    with patch.object(
        booking_service,
        "_get_availability_row_for_update",
        new=AsyncMock(return_value=None),
    ):
        results = await asyncio.gather(
            booking_service._acquire_lock(
                mock_session_1, vendor_id, service_id, check_date, user_id
            ),
            booking_service._acquire_lock(
                mock_session_2, vendor_id, service_id, check_date, user_id
            ),
            return_exceptions=True,
        )

    http_409s = [
        r
        for r in results
        if isinstance(r, HTTPException)
        and r.status_code == 409
        and r.detail.get("code") == "CONFLICT_DATE_BEING_PROCESSED"
    ]
    unhandled_integrity_errors = [
        r for r in results if isinstance(r, IntegrityError)
    ]

    assert len(unhandled_integrity_errors) == 0, (
        "IntegrityError must NOT propagate as an unhandled exception (would cause 500). "
        f"Got: {unhandled_integrity_errors}"
    )
    assert len(http_409s) == 1, (
        f"Expected exactly 1 HTTP 409 CONFLICT_DATE_BEING_PROCESSED, got {len(http_409s)}. "
        f"Results: {results}"
    )
