"""
Preservation Property Tests — Availability Lock Race Condition Bugfix
=====================================================================

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

These tests capture the BASELINE behaviour of `_acquire_lock` and
`check_availability` on non-concurrent single-request inputs. They were
written BEFORE the fix was applied and confirmed passing on unfixed code.
After the fix (tasks 2.x), they must STILL PASS — confirming no regressions
were introduced.

Observation-first methodology:
  - _acquire_lock(available slot)              → row with status=LOCKED
  - _acquire_lock(booked slot)                 → HTTPException 409 CONFLICT_DATE_UNAVAILABLE
  - _acquire_lock(blocked slot)                → HTTPException 409 CONFLICT_DATE_UNAVAILABLE
  - _acquire_lock(locked slot, future TTL)     → HTTPException 409 CONFLICT_DATE_BEING_PROCESSED
  - _acquire_lock(locked slot, expired TTL)    → row with status=LOCKED (treated as available)
  - check_availability(any slot)               → correct {"available": bool} dict, no FOR UPDATE

Properties tested:
  2a — Available slot:      _acquire_lock returns row with status=LOCKED
  2b — Booked slot:         _acquire_lock raises 409 CONFLICT_DATE_UNAVAILABLE
  2c — Blocked slot:        _acquire_lock raises 409 CONFLICT_DATE_UNAVAILABLE
  2d — Active locked slot:  _acquire_lock raises 409 CONFLICT_DATE_BEING_PROCESSED
  2e — Expired locked slot: _acquire_lock returns row with status=LOCKED
  2f — check_availability:  returns correct dict, never calls _get_availability_row_for_update
"""
import uuid
from datetime import datetime, timedelta, timezone, date as date_type
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from hypothesis import HealthCheck, given
from hypothesis import settings as h_settings
from hypothesis import strategies as st

from src.models.availability import VendorAvailability, AvailabilityStatus
from src.services.booking_service import booking_service


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_row(
    status: str,
    vendor_id: uuid.UUID | None = None,
    service_id: uuid.UUID | None = None,
    locked_until: datetime | None = None,
) -> MagicMock:
    """Build a MagicMock that looks like a VendorAvailability row."""
    row = MagicMock(spec=VendorAvailability)
    row.status = status
    row.vendor_id = vendor_id or uuid.uuid4()
    row.service_id = service_id or uuid.uuid4()
    row.locked_until = locked_until
    return row


def _make_session() -> AsyncMock:
    """Build a minimal async session mock with flush/add/rollback."""
    session = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    session.rollback = AsyncMock()
    return session


# ─────────────────────────────────────────────────────────────────────────────
# Property 2a — Available slot → lock acquired, status=LOCKED
# ─────────────────────────────────────────────────────────────────────────────

class TestProperty2aAvailableSlot:
    """
    Property 2a — Available slot: for any (vendor_id, service_id, user_id),
    when the slot is AVAILABLE, _acquire_lock must return a row with
    status == AvailabilityStatus.LOCKED.

    **Validates: Requirements 3.1**
    """

    @pytest.mark.asyncio
    @h_settings(
        max_examples=3,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    @given(
        vendor_id=st.uuids(),
        service_id=st.uuids(),
        user_id=st.uuids(),
    )
    async def test_property_2a_available_slot_lock_acquired(
        self,
        vendor_id: uuid.UUID,
        service_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """
        Property 2a — Available slot preservation (property-based).

        For any (vendor_id, service_id, user_id), when _get_availability_row_for_update
        returns a row with status=AVAILABLE, _acquire_lock must return a row with
        status == AvailabilityStatus.LOCKED.

        **Validates: Requirements 3.1**
        """
        available_row = _make_row(AvailabilityStatus.AVAILABLE, vendor_id, service_id)
        session = _make_session()
        check_date = date_type(2028, 10, 1)

        with patch.object(
            booking_service,
            "_get_availability_row_for_update",
            new=AsyncMock(return_value=available_row),
        ):
            result = await booking_service._acquire_lock(
                session, vendor_id, service_id, check_date, user_id
            )

        assert result.status == AvailabilityStatus.LOCKED, (
            f"PRESERVATION VIOLATED: _acquire_lock returned status={result.status!r} "
            f"instead of LOCKED for an available slot "
            f"(vendor_id={vendor_id}, service_id={service_id})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property 2b — Booked slot → 409 CONFLICT_DATE_UNAVAILABLE
# ─────────────────────────────────────────────────────────────────────────────

class TestProperty2bBookedSlot:
    """
    Property 2b — Booked slot: for any (vendor_id, service_id, user_id),
    when the slot is BOOKED, _acquire_lock must raise HTTPException 409
    CONFLICT_DATE_UNAVAILABLE.

    **Validates: Requirements 3.2**
    """

    @pytest.mark.asyncio
    @h_settings(
        max_examples=3,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    @given(
        vendor_id=st.uuids(),
        service_id=st.uuids(),
        user_id=st.uuids(),
    )
    async def test_property_2b_booked_slot_raises_conflict_date_unavailable(
        self,
        vendor_id: uuid.UUID,
        service_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """
        Property 2b — Booked slot preservation (property-based).

        For any (vendor_id, service_id, user_id), when _get_availability_row_for_update
        returns a row with status=BOOKED, _acquire_lock must raise HTTPException 409
        with code CONFLICT_DATE_UNAVAILABLE.

        **Validates: Requirements 3.2**
        """
        booked_row = _make_row(AvailabilityStatus.BOOKED, vendor_id, service_id)
        session = _make_session()
        check_date = date_type(2028, 10, 2)

        with patch.object(
            booking_service,
            "_get_availability_row_for_update",
            new=AsyncMock(return_value=booked_row),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await booking_service._acquire_lock(
                    session, vendor_id, service_id, check_date, user_id
                )

        assert exc_info.value.status_code == 409, (
            f"PRESERVATION VIOLATED: expected status_code=409, "
            f"got {exc_info.value.status_code!r} for booked slot"
        )
        assert exc_info.value.detail["code"] == "CONFLICT_DATE_UNAVAILABLE", (
            f"PRESERVATION VIOLATED: expected code=CONFLICT_DATE_UNAVAILABLE, "
            f"got {exc_info.value.detail!r} for booked slot"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property 2c — Blocked slot → 409 CONFLICT_DATE_UNAVAILABLE
# ─────────────────────────────────────────────────────────────────────────────

class TestProperty2cBlockedSlot:
    """
    Property 2c — Blocked slot: for any (vendor_id, service_id, user_id),
    when the slot is BLOCKED, _acquire_lock must raise HTTPException 409
    CONFLICT_DATE_UNAVAILABLE.

    **Validates: Requirements 3.3**
    """

    @pytest.mark.asyncio
    @h_settings(
        max_examples=3,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    @given(
        vendor_id=st.uuids(),
        service_id=st.uuids(),
        user_id=st.uuids(),
    )
    async def test_property_2c_blocked_slot_raises_conflict_date_unavailable(
        self,
        vendor_id: uuid.UUID,
        service_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """
        Property 2c — Blocked slot preservation (property-based).

        For any (vendor_id, service_id, user_id), when _get_availability_row_for_update
        returns a row with status=BLOCKED, _acquire_lock must raise HTTPException 409
        with code CONFLICT_DATE_UNAVAILABLE.

        **Validates: Requirements 3.3**
        """
        blocked_row = _make_row(AvailabilityStatus.BLOCKED, vendor_id, service_id)
        session = _make_session()
        check_date = date_type(2028, 10, 3)

        with patch.object(
            booking_service,
            "_get_availability_row_for_update",
            new=AsyncMock(return_value=blocked_row),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await booking_service._acquire_lock(
                    session, vendor_id, service_id, check_date, user_id
                )

        assert exc_info.value.status_code == 409, (
            f"PRESERVATION VIOLATED: expected status_code=409, "
            f"got {exc_info.value.status_code!r} for blocked slot"
        )
        assert exc_info.value.detail["code"] == "CONFLICT_DATE_UNAVAILABLE", (
            f"PRESERVATION VIOLATED: expected code=CONFLICT_DATE_UNAVAILABLE, "
            f"got {exc_info.value.detail!r} for blocked slot"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property 2d — Active locked slot → 409 CONFLICT_DATE_BEING_PROCESSED
# ─────────────────────────────────────────────────────────────────────────────

class TestProperty2dActiveLocked:
    """
    Property 2d — Active locked slot: for any (vendor_id, service_id, user_id)
    and any future locked_until timestamp, when the slot is LOCKED with
    locked_until > now, _acquire_lock must raise HTTPException 409
    CONFLICT_DATE_BEING_PROCESSED.

    **Validates: Requirements 3.4**
    """

    @pytest.mark.asyncio
    @h_settings(
        max_examples=3,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    @given(
        vendor_id=st.uuids(),
        service_id=st.uuids(),
        user_id=st.uuids(),
        # Generate future locked_until timestamps (1 second to 1 hour from now)
        future_offset_seconds=st.integers(min_value=1, max_value=3600),
    )
    async def test_property_2d_active_locked_slot_raises_conflict_being_processed(
        self,
        vendor_id: uuid.UUID,
        service_id: uuid.UUID,
        user_id: uuid.UUID,
        future_offset_seconds: int,
    ):
        """
        Property 2d — Active locked slot preservation (property-based).

        For any (vendor_id, service_id, user_id) and any future locked_until,
        when _get_availability_row_for_update returns a row with status=LOCKED
        and locked_until > now, _acquire_lock must raise HTTPException 409
        with code CONFLICT_DATE_BEING_PROCESSED.

        **Validates: Requirements 3.4**
        """
        future_locked_until = datetime.now(timezone.utc) + timedelta(
            seconds=future_offset_seconds
        )
        locked_row = _make_row(
            AvailabilityStatus.LOCKED,
            vendor_id,
            service_id,
            locked_until=future_locked_until,
        )
        session = _make_session()
        check_date = date_type(2028, 10, 4)

        with patch.object(
            booking_service,
            "_get_availability_row_for_update",
            new=AsyncMock(return_value=locked_row),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await booking_service._acquire_lock(
                    session, vendor_id, service_id, check_date, user_id
                )

        assert exc_info.value.status_code == 409, (
            f"PRESERVATION VIOLATED: expected status_code=409, "
            f"got {exc_info.value.status_code!r} for active locked slot "
            f"(locked_until={future_locked_until!r})"
        )
        assert exc_info.value.detail["code"] == "CONFLICT_DATE_BEING_PROCESSED", (
            f"PRESERVATION VIOLATED: expected code=CONFLICT_DATE_BEING_PROCESSED, "
            f"got {exc_info.value.detail!r} for active locked slot"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property 2e — Expired locked slot → treated as available, lock acquired
# ─────────────────────────────────────────────────────────────────────────────

class TestProperty2eExpiredLocked:
    """
    Property 2e — Expired locked slot: for any (vendor_id, service_id, user_id)
    and any past locked_until timestamp, when the slot is LOCKED with
    locked_until <= now, _acquire_lock must treat it as available and return
    a row with status == AvailabilityStatus.LOCKED.

    **Validates: Requirements 3.5**
    """

    @pytest.mark.asyncio
    @h_settings(
        max_examples=3,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    @given(
        vendor_id=st.uuids(),
        service_id=st.uuids(),
        user_id=st.uuids(),
        # Generate past locked_until timestamps (1 second to 1 hour ago)
        past_offset_seconds=st.integers(min_value=1, max_value=3600),
    )
    async def test_property_2e_expired_locked_slot_treated_as_available(
        self,
        vendor_id: uuid.UUID,
        service_id: uuid.UUID,
        user_id: uuid.UUID,
        past_offset_seconds: int,
    ):
        """
        Property 2e — Expired locked slot preservation (property-based).

        For any (vendor_id, service_id, user_id) and any past locked_until,
        when _get_availability_row_for_update returns a row with status=LOCKED
        and locked_until <= now, _acquire_lock must treat it as available and
        return a row with status == AvailabilityStatus.LOCKED (re-locked).

        **Validates: Requirements 3.5**
        """
        past_locked_until = datetime.now(timezone.utc) - timedelta(
            seconds=past_offset_seconds
        )
        expired_locked_row = _make_row(
            AvailabilityStatus.LOCKED,
            vendor_id,
            service_id,
            locked_until=past_locked_until,
        )
        session = _make_session()
        check_date = date_type(2028, 10, 5)

        with patch.object(
            booking_service,
            "_get_availability_row_for_update",
            new=AsyncMock(return_value=expired_locked_row),
        ):
            result = await booking_service._acquire_lock(
                session, vendor_id, service_id, check_date, user_id
            )

        assert result.status == AvailabilityStatus.LOCKED, (
            f"PRESERVATION VIOLATED: _acquire_lock returned status={result.status!r} "
            f"instead of LOCKED for an expired locked slot "
            f"(locked_until={past_locked_until!r})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property 2f — check_availability read path is unaffected (no FOR UPDATE)
# ─────────────────────────────────────────────────────────────────────────────

class TestProperty2fCheckAvailabilityReadPath:
    """
    Property 2f — check_availability read path: for any slot status,
    check_availability must return the correct {"available": bool} dict
    and must NEVER call _get_availability_row_for_update (the locking helper).

    **Validates: Requirements 3.6**
    """

    @pytest.mark.asyncio
    @h_settings(
        max_examples=3,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    @given(
        vendor_id=st.uuids(),
        service_id=st.uuids(),
        slot_status=st.sampled_from([
            AvailabilityStatus.AVAILABLE,
            AvailabilityStatus.BOOKED,
            AvailabilityStatus.BLOCKED,
            AvailabilityStatus.LOCKED,
        ]),
    )
    async def test_property_2f_check_availability_correct_result_no_for_update(
        self,
        vendor_id: uuid.UUID,
        service_id: uuid.UUID,
        slot_status: str,
    ):
        """
        Property 2f — check_availability read path preservation (property-based).

        For any slot status, check_availability must:
          1. Return {"available": True}  for AVAILABLE and expired LOCKED slots.
          2. Return {"available": False} for BOOKED, BLOCKED, and active LOCKED slots.
          3. NEVER call _get_availability_row_for_update (read-only path must stay lock-free).

        We use an active locked_until (future) for LOCKED status to test the
        "active lock → unavailable" branch. The expired-lock branch is covered
        by property 2e above.

        **Validates: Requirements 3.6**
        """
        check_date = date_type(2028, 10, 6)

        # For LOCKED status, use an active (future) locked_until so the slot
        # is reported as unavailable — this tests the active-lock branch.
        if slot_status == AvailabilityStatus.LOCKED:
            locked_until = datetime.now(timezone.utc) + timedelta(seconds=60)
        else:
            locked_until = None

        row = _make_row(slot_status, vendor_id, service_id, locked_until=locked_until)

        session = _make_session()

        # Spy on _get_availability_row_for_update to assert it is NEVER called
        for_update_mock = AsyncMock(return_value=None)

        with patch.object(
            booking_service,
            "_get_availability_row",
            new=AsyncMock(return_value=row),
        ), patch.object(
            booking_service,
            "_get_availability_row_for_update",
            new=for_update_mock,
        ):
            result = await booking_service.check_availability(
                session, vendor_id, service_id, check_date
            )

        # Assert _get_availability_row_for_update was NEVER called
        for_update_mock.assert_not_called(), (
            "PRESERVATION VIOLATED: check_availability called _get_availability_row_for_update "
            "— the read-only path must never acquire a write lock"
        )

        # Assert correct availability result per status
        if slot_status == AvailabilityStatus.AVAILABLE:
            assert result.get("available") is True, (
                f"PRESERVATION VIOLATED: check_availability returned {result!r} "
                f"instead of available=True for AVAILABLE slot"
            )
        elif slot_status in (AvailabilityStatus.BOOKED, AvailabilityStatus.BLOCKED):
            assert result.get("available") is False, (
                f"PRESERVATION VIOLATED: check_availability returned {result!r} "
                f"instead of available=False for {slot_status!r} slot"
            )
        elif slot_status == AvailabilityStatus.LOCKED:
            # Active lock (locked_until in future) → unavailable
            assert result.get("available") is False, (
                f"PRESERVATION VIOLATED: check_availability returned {result!r} "
                f"instead of available=False for active LOCKED slot"
            )
