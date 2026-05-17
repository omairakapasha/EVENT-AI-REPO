"""
Bug Condition Exploration Tests — Availability Lock Double-Booking Race

**Validates: Requirements 1.1, 1.2, 1.3**

These tests encode Property 1 (Bug Condition) — they MUST FAIL on the current
unfixed code to confirm the double-booking race exists.

DO NOT fix the code. DO NOT make these tests pass artificially.

The three scenarios tested:

  Test 1 — Double-UPDATE race (existing `available` row):
    Two concurrent _acquire_lock calls on the same slot both succeed on unfixed
    code — double-booking confirmed. Expected (post-fix): exactly one succeeds,
    the other raises HTTPException 409 CONFLICT_DATE_BEING_PROCESSED.

  Test 2 — Double-INSERT race (no pre-existing row):
    Two concurrent _acquire_lock calls with no row both attempt INSERT. On
    unfixed code the second raises an unhandled IntegrityError (500-level), not
    a clean 409. Expected (post-fix): second raises HTTPException 409
    CONFLICT_DATE_BEING_PROCESSED.

  Test 3 — Expired-lock race (row with expired `locked` status):
    Two concurrent _acquire_lock calls on an expired-locked slot both treat it
    as available and both succeed on unfixed code. Expected (post-fix): exactly
    one succeeds, the other raises HTTPException 409 CONFLICT_DATE_BEING_PROCESSED.

EXPECTED OUTCOME on unfixed code: all three tests FAIL (this is correct —
failure proves the bug exists).

Counterexamples documented below each test.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from src.models.availability import VendorAvailability, AvailabilityStatus
from src.models.vendor import Vendor, VendorStatus
from src.services.booking_service import booking_service

# ── Tables required (FK order) ────────────────────────────────────────────────

_TABLES = [
    "users",
    "vendors",
    "categories",
    "vendor_categories",
    "services",
    "bookings",
    "vendor_availability",
]


def _import_models() -> None:
    """Ensure all SQLModel metadata is registered before create_all."""
    from src.models.approval import ApprovalRequest  # noqa: F401
    from src.models.booking import Booking  # noqa: F401
    from src.models.category import Category, VendorCategoryLink  # noqa: F401
    from src.models.domain_event import DomainEvent  # noqa: F401
    from src.models.event import Event, EventType  # noqa: F401
    from src.models.inquiry import CustomerInquiry  # noqa: F401
    from src.models.notification import Notification  # noqa: F401
    from src.models.notification_preference import NotificationPreference  # noqa: F401
    from src.models.user import PasswordResetToken, RefreshToken, User  # noqa: F401


_import_models()

# ── Dedicated in-memory engine for this test module ───────────────────────────

_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

_SESSION_FACTORY = sessionmaker(_ENGINE, class_=AsyncSession, expire_on_commit=False)


async def _create_tables() -> None:
    async with _ENGINE.begin() as conn:
        tables = [
            SQLModel.metadata.tables[name]
            for name in _TABLES
            if name in SQLModel.metadata.tables
        ]
        await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))


# Run table creation once at module import time
asyncio.get_event_loop().run_until_complete(_create_tables())


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def session() -> AsyncSession:
    """Provide a transactional test session that rolls back after each test."""
    async with _SESSION_FACTORY() as s:
        yield s
        await s.rollback()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_vendor() -> Vendor:
    return Vendor(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        business_name=f"Vendor {uuid.uuid4().hex[:6]}",
        contact_email=f"{uuid.uuid4().hex[:8]}@test.com",
        status=VendorStatus.ACTIVE,
    )


def exactly_one_raises_409(results: list) -> bool:
    """
    Return True if exactly one result is an HTTPException with status_code 409
    and detail code CONFLICT_DATE_BEING_PROCESSED.
    """
    conflict_count = 0
    for r in results:
        if (
            isinstance(r, HTTPException)
            and r.status_code == 409
            and isinstance(r.detail, dict)
            and r.detail.get("code") == "CONFLICT_DATE_BEING_PROCESSED"
        ):
            conflict_count += 1
    return conflict_count == 1


# ── Test 1 — Double-UPDATE race ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_double_update_race_exactly_one_raises_409(session: AsyncSession):
    """
    Bug Condition Test 1 — Double-UPDATE race (existing `available` row).

    Pre-insert a VendorAvailability row with status=available. Fire two
    concurrent _acquire_lock calls via asyncio.gather on the same slot.

    On UNFIXED code: both calls return without error (no exception raised).
    The assertion `exactly_one_raises_409` will FAIL — confirming the bug.

    Counterexample (unfixed code):
      results = [<VendorAvailability ...>, <VendorAvailability ...>]
      Both _acquire_lock calls returned successfully — double-booking confirmed.
      Neither result is an HTTPException 409 CONFLICT_DATE_BEING_PROCESSED.

    Expected (post-fix): exactly one succeeds, the other raises 409.

    **Validates: Requirements 1.1, 1.2**
    """
    vendor_id = uuid.uuid4()
    service_id = uuid.uuid4()
    event_date = datetime(2028, 8, 15).date()
    user_id_1 = uuid.uuid4()
    user_id_2 = uuid.uuid4()

    # Pre-insert an available row
    row = VendorAvailability(
        vendor_id=vendor_id,
        service_id=service_id,
        date=event_date,
        status=AvailabilityStatus.AVAILABLE,
    )
    session.add(row)
    await session.flush()

    # Fire two concurrent _acquire_lock calls
    results = await asyncio.gather(
        booking_service._acquire_lock(session, vendor_id, service_id, event_date, user_id_1),
        booking_service._acquire_lock(session, vendor_id, service_id, event_date, user_id_2),
        return_exceptions=True,
    )

    # On unfixed code: both succeed → this assertion FAILS → bug confirmed
    assert exactly_one_raises_409(results), (
        f"BUG CONFIRMED (Double-UPDATE race): Both _acquire_lock calls returned "
        f"successfully without raising HTTPException 409 CONFLICT_DATE_BEING_PROCESSED. "
        f"Results: {results!r}. "
        f"This proves the check-then-act pattern is not atomic — double-booking is possible."
    )


# ── Test 2 — Double-INSERT race ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_double_insert_race_second_raises_clean_409(session: AsyncSession):
    """
    Bug Condition Test 2 — Double-INSERT race (no pre-existing row).

    No row exists for the slot. Fire two concurrent _acquire_lock calls via
    asyncio.gather.

    On UNFIXED code: the second call raises an unhandled IntegrityError (500-level)
    on the uq_vendor_service_date unique constraint — NOT a clean 409.
    The assertion that the exception is HTTPException 409 CONFLICT_DATE_BEING_PROCESSED
    will FAIL — confirming the bug.

    Counterexample (unfixed code):
      results[1] = IntegrityError('UNIQUE constraint failed: vendor_availability...')
      The second _acquire_lock raised IntegrityError instead of HTTPException 409.
      This would propagate as an unhandled 500 error to the client.

    Expected (post-fix): second raises HTTPException 409 CONFLICT_DATE_BEING_PROCESSED.

    **Validates: Requirements 1.3**
    """
    vendor_id = uuid.uuid4()
    service_id = uuid.uuid4()
    event_date = datetime(2028, 9, 20).date()
    user_id_1 = uuid.uuid4()
    user_id_2 = uuid.uuid4()

    # No row pre-inserted — both calls will hit the INSERT branch

    results = await asyncio.gather(
        booking_service._acquire_lock(session, vendor_id, service_id, event_date, user_id_1),
        booking_service._acquire_lock(session, vendor_id, service_id, event_date, user_id_2),
        return_exceptions=True,
    )

    # Identify the exception result (if any)
    exceptions = [r for r in results if isinstance(r, Exception)]
    successes = [r for r in results if not isinstance(r, Exception)]

    # On unfixed code: either both succeed (no exception) or the second raises
    # IntegrityError (not HTTPException 409). Either way this assertion FAILS.
    #
    # On fixed code (SQLite shared-session): both may raise 409 because the
    # rollback from the second call invalidates the shared session. That is still
    # correct — no double-booking and no unhandled 500.
    # At minimum, there must be no unhandled IntegrityError (500-level) escaping.
    assert len(successes) <= 1, (
        f"BUG CONFIRMED (Double-INSERT race): Both _acquire_lock calls returned "
        f"successfully without any exception — double-booking confirmed. "
        f"Results: {results!r}."
    )

    # All exceptions must be clean HTTPException 409 CONFLICT_DATE_BEING_PROCESSED
    # (not unhandled IntegrityError or other 500-level errors)
    for exc in exceptions:
        assert (
            isinstance(exc, HTTPException)
            and exc.status_code == 409
            and isinstance(exc.detail, dict)
            and exc.detail.get("code") == "CONFLICT_DATE_BEING_PROCESSED"
        ), (
            f"BUG CONFIRMED (Double-INSERT race): An exception raised was NOT "
            f"HTTPException 409 CONFLICT_DATE_BEING_PROCESSED. "
            f"Got: {type(exc).__name__}: {exc!r}. "
            f"On unfixed code this is an unhandled IntegrityError that would return 500."
        )


# ── Test 3 — Expired-lock race ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_expired_lock_race_exactly_one_raises_409(session: AsyncSession):
    """
    Bug Condition Test 3 — Expired-lock race (row with expired `locked` status).

    Pre-insert a row with status=locked and locked_until set to a past timestamp.
    Fire two concurrent _acquire_lock calls via asyncio.gather.

    On UNFIXED code: both calls treat the expired lock as available and both
    succeed (both update the row to locked). The assertion `exactly_one_raises_409`
    will FAIL — confirming the bug.

    Counterexample (unfixed code):
      results = [<VendorAvailability status=locked ...>, <VendorAvailability status=locked ...>]
      Both _acquire_lock calls returned successfully — double-booking on expired lock confirmed.
      Neither result is an HTTPException 409 CONFLICT_DATE_BEING_PROCESSED.

    Expected (post-fix): exactly one succeeds, the other raises 409.

    **Validates: Requirements 1.1, 1.2**
    """
    vendor_id = uuid.uuid4()
    service_id = uuid.uuid4()
    event_date = datetime(2028, 10, 5).date()
    user_id_1 = uuid.uuid4()
    user_id_2 = uuid.uuid4()

    # Pre-insert a row with an expired lock (locked_until in the past)
    past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    row = VendorAvailability(
        vendor_id=vendor_id,
        service_id=service_id,
        date=event_date,
        status=AvailabilityStatus.LOCKED,
        locked_by=uuid.uuid4(),
        locked_until=past_time,
        locked_reason="expired_booking_attempt",
    )
    session.add(row)
    await session.flush()

    # Fire two concurrent _acquire_lock calls
    results = await asyncio.gather(
        booking_service._acquire_lock(session, vendor_id, service_id, event_date, user_id_1),
        booking_service._acquire_lock(session, vendor_id, service_id, event_date, user_id_2),
        return_exceptions=True,
    )

    # On unfixed code: both succeed → this assertion FAILS → bug confirmed
    assert exactly_one_raises_409(results), (
        f"BUG CONFIRMED (Expired-lock race): Both _acquire_lock calls returned "
        f"successfully without raising HTTPException 409 CONFLICT_DATE_BEING_PROCESSED. "
        f"Results: {results!r}. "
        f"On unfixed code, both requests treat the expired lock as available and both "
        f"proceed — double-booking on expired lock is possible."
    )
