import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, time
from fastapi import HTTPException

from src.models.booking import Booking, BookingStatus, BookingCreate
from src.models.availability import VendorAvailability, AvailabilityStatus
from src.services.booking_service import BookingService, VALID_TRANSITIONS


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_booking_in(vendor_id=None, service_id=None):
    return BookingCreate(
        vendor_id=vendor_id or uuid.uuid4(),
        service_id=service_id or uuid.uuid4(),
        event_date=date(2027, 6, 1),
        unit_price=500.0,
        total_price=500.0,
    )


def _mock_vendor(vendor_id=None, user_id=None):
    v = MagicMock()
    v.id = vendor_id or uuid.uuid4()
    v.user_id = user_id or uuid.uuid4()
    return v


def _mock_service(vendor_id, service_id=None, is_active=True, price_min=500.0):
    s = MagicMock()
    s.id = service_id or uuid.uuid4()
    s.vendor_id = vendor_id
    s.is_active = is_active
    s.price_min = price_min
    return s


# ── create_booking ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_booking_past_date_raises_422():
    service = BookingService()
    session = AsyncMock()
    booking_in = BookingCreate(
        vendor_id=uuid.uuid4(), service_id=uuid.uuid4(),
        event_date=date(2020, 1, 1), unit_price=100.0, total_price=100.0,
    )
    with pytest.raises(HTTPException) as exc:
        await service.create_booking(session, booking_in, uuid.uuid4())
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "VALIDATION_PAST_DATE"


@pytest.mark.asyncio
async def test_create_booking_vendor_not_found_raises_404():
    service = BookingService()
    session = AsyncMock()
    session.get.return_value = None  # vendor not found
    booking_in = _make_booking_in()
    with pytest.raises(HTTPException) as exc:
        await service.create_booking(session, booking_in, uuid.uuid4())
    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "NOT_FOUND_VENDOR"


@pytest.mark.asyncio
async def test_create_booking_inactive_service_raises_422():
    service = BookingService()
    session = AsyncMock()
    vendor_id = uuid.uuid4()
    service_id = uuid.uuid4()
    booking_in = _make_booking_in(vendor_id=vendor_id, service_id=service_id)
    # session.get: first call = vendor, second call = service (inactive)
    session.get.side_effect = [_mock_vendor(vendor_id), _mock_service(vendor_id, service_id, is_active=False)]
    with pytest.raises(HTTPException) as exc:
        await service.create_booking(session, booking_in, uuid.uuid4())
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "VALIDATION_SERVICE_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_booking_date_already_booked_raises_409():
    service = BookingService()
    session = AsyncMock()
    vendor_id = uuid.uuid4()
    service_id = uuid.uuid4()
    booking_in = _make_booking_in(vendor_id=vendor_id, service_id=service_id)
    session.get.side_effect = [_mock_vendor(vendor_id), _mock_service(vendor_id, service_id)]
    # availability row = BOOKED
    booked_row = VendorAvailability(
        vendor_id=vendor_id, service_id=service_id,
        date=booking_in.event_date, status=AvailabilityStatus.BOOKED,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = booked_row
    session.execute.return_value = mock_result
    with pytest.raises(HTTPException) as exc:
        await service.create_booking(session, booking_in, uuid.uuid4())
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "CONFLICT_DATE_UNAVAILABLE"


# ── update_status state machine ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_status_invalid_transition_raises_409():
    service = BookingService()
    session = AsyncMock()
    booking = Booking(
        id=uuid.uuid4(), vendor_id=uuid.uuid4(), service_id=uuid.uuid4(),
        user_id=uuid.uuid4(), event_date=date(2027, 6, 1),
        status=BookingStatus.pending, unit_price=100.0, total_price=100.0,
    )
    session.get.return_value = booking
    with pytest.raises(HTTPException) as exc:
        await service.update_status(session, booking.id, BookingStatus.completed, uuid.uuid4())
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "VALIDATION_INVALID_TRANSITION"


@pytest.mark.asyncio
async def test_update_status_terminal_raises_409():
    service = BookingService()
    session = AsyncMock()
    booking = Booking(
        id=uuid.uuid4(), vendor_id=uuid.uuid4(), service_id=uuid.uuid4(),
        user_id=uuid.uuid4(), event_date=date(2027, 6, 1),
        status=BookingStatus.completed, unit_price=100.0, total_price=100.0,
    )
    session.get.return_value = booking
    with pytest.raises(HTTPException) as exc:
        await service.update_status(session, booking.id, BookingStatus.confirmed, uuid.uuid4())
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_cancel_already_cancelled_raises_409():
    service = BookingService()
    session = AsyncMock()
    booking = Booking(
        id=uuid.uuid4(), vendor_id=uuid.uuid4(), service_id=uuid.uuid4(),
        user_id=uuid.uuid4(), event_date=date(2027, 6, 1),
        status=BookingStatus.cancelled, unit_price=100.0, total_price=100.0,
    )
    session.get.return_value = booking
    with pytest.raises(HTTPException) as exc:
        await service.cancel_booking(session, booking.id, uuid.uuid4())
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "CONFLICT_ALREADY_CANCELLED"


# ── state machine coverage ────────────────────────────────────────────────────

def test_valid_transitions_defined():
    assert BookingStatus.confirmed in VALID_TRANSITIONS[BookingStatus.pending]
    assert BookingStatus.rejected in VALID_TRANSITIONS[BookingStatus.pending]
    assert BookingStatus.cancelled in VALID_TRANSITIONS[BookingStatus.pending]
    assert BookingStatus.in_progress in VALID_TRANSITIONS[BookingStatus.confirmed]


# ── slot held (not booked) until vendor confirms ────────────────────────────────

@pytest.mark.asyncio
async def test_pending_hold_is_not_available():
    """A slot held for a pending (unconfirmed) booking reports as unavailable."""
    service = BookingService()
    row = VendorAvailability(
        vendor_id=uuid.uuid4(), service_id=uuid.uuid4(),
        date=date(2027, 6, 1), status=AvailabilityStatus.LOCKED,
        locked_until=None, locked_reason="pending_vendor_confirmation",
    )
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = row
    session.execute.return_value = mock_result
    result = await service.check_availability(session, row.vendor_id, row.service_id, row.date)
    assert result == {"available": False, "reason": "Date is pending vendor confirmation"}


@pytest.mark.asyncio
async def test_acquire_lock_rejects_when_pending_confirmation_hold_exists():
    """A second booking attempt for a date already held pending confirmation is rejected."""
    service = BookingService()
    vendor_id, service_id = uuid.uuid4(), uuid.uuid4()
    row = VendorAvailability(
        vendor_id=vendor_id, service_id=service_id,
        date=date(2027, 6, 1), status=AvailabilityStatus.LOCKED,
        locked_until=None, locked_reason="pending_vendor_confirmation",
    )
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = row
    session.execute.return_value = mock_result
    with pytest.raises(HTTPException) as exc:
        await service._acquire_lock(session, vendor_id, service_id, date(2027, 6, 1), uuid.uuid4())
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "CONFLICT_DATE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_confirm_marks_slot_booked():
    """Vendor confirming a pending booking flips its held slot to booked."""
    service = BookingService()
    vendor_id, service_id, booking_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    booking = Booking(
        id=booking_id, vendor_id=vendor_id, service_id=service_id,
        user_id=uuid.uuid4(), event_date=date(2027, 6, 1),
        status=BookingStatus.pending, unit_price=100.0, total_price=100.0,
    )
    avail_row = VendorAvailability(
        vendor_id=vendor_id, service_id=service_id, date=date(2027, 6, 1),
        status=AvailabilityStatus.LOCKED, locked_until=None,
        locked_reason="pending_vendor_confirmation", booking_id=booking_id,
    )
    session = AsyncMock()
    mock_user = MagicMock()  # not pro: subscription_status != SubscriptionStatus.pro
    session.get.side_effect = [booking, mock_user]
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = avail_row
    session.execute.return_value = mock_result

    with patch("src.services.booking_service.event_bus.emit", new=AsyncMock()):
        await service.update_status(session, booking_id, BookingStatus.confirmed, uuid.uuid4())

    assert avail_row.status == AvailabilityStatus.BOOKED
    assert avail_row.booking_id == booking_id


@pytest.mark.asyncio
async def test_create_booking_payment_pending_even_for_pro():
    """payment_status is always pending at creation — even for Pro users — until the vendor accepts."""
    from src.models.booking import PaymentStatus
    service = BookingService()
    vendor_id, service_id = uuid.uuid4(), uuid.uuid4()
    booking_in = _make_booking_in(vendor_id=vendor_id, service_id=service_id)
    session = AsyncMock()
    session.get.side_effect = [_mock_vendor(vendor_id), _mock_service(vendor_id, service_id)]
    no_avail_result = MagicMock()
    no_avail_result.scalar_one_or_none.return_value = None
    session.execute.return_value = no_avail_result

    with patch("src.services.booking_service.event_bus.emit", new=AsyncMock()):
        booking = await service.create_booking(session, booking_in, uuid.uuid4())

    assert booking.payment_status == PaymentStatus.pending


@pytest.mark.asyncio
async def test_confirm_triggers_payment_for_pro_user():
    """Vendor confirming a Pro user's booking auto-marks payment as paid (deposit skipped)."""
    from src.models.booking import PaymentStatus
    from src.models.user import SubscriptionStatus
    service = BookingService()
    vendor_id, service_id, booking_id, booker_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    booking = Booking(
        id=booking_id, vendor_id=vendor_id, service_id=service_id,
        user_id=booker_id, event_date=date(2027, 6, 1),
        status=BookingStatus.pending, unit_price=100.0, total_price=100.0,
        payment_status=PaymentStatus.pending,
    )
    pro_user = MagicMock()
    pro_user.subscription_status = SubscriptionStatus.pro
    pro_user.subscription_expires_at = None

    session = AsyncMock()
    session.get.side_effect = [booking, pro_user]
    no_avail_result = MagicMock()
    no_avail_result.scalar_one_or_none.return_value = None
    session.execute.return_value = no_avail_result

    with patch("src.services.booking_service.event_bus.emit", new=AsyncMock()):
        await service.update_status(session, booking_id, BookingStatus.confirmed, uuid.uuid4())

    assert booking.payment_status == PaymentStatus.paid


@pytest.mark.asyncio
async def test_reject_refunds_already_paid_booking():
    """Rejecting a confirmed Pro booking that was auto-marked paid flips payment_status to refunded."""
    from src.models.booking import PaymentStatus
    service = BookingService()
    vendor_id, service_id, booking_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    booking = Booking(
        id=booking_id, vendor_id=vendor_id, service_id=service_id,
        user_id=uuid.uuid4(), event_date=date(2027, 6, 1),
        status=BookingStatus.confirmed, unit_price=100.0, total_price=100.0,
        payment_status=PaymentStatus.paid,
    )
    session = AsyncMock()
    session.get.return_value = booking

    with patch("src.services.booking_service.event_bus.emit", new=AsyncMock()), \
         patch.object(service, "_release_slot", new=AsyncMock()):
        await service.update_status(session, booking_id, BookingStatus.cancelled, uuid.uuid4())

    assert booking.payment_status == PaymentStatus.refunded


@pytest.mark.asyncio
async def test_reject_releases_held_slot():
    """Rejecting a pending booking releases its held slot back to available."""
    service = BookingService()
    vendor_id, service_id, booking_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    booking = Booking(
        id=booking_id, vendor_id=vendor_id, service_id=service_id,
        user_id=uuid.uuid4(), event_date=date(2027, 6, 1),
        status=BookingStatus.pending, unit_price=100.0, total_price=100.0,
    )
    session = AsyncMock()
    session.get.return_value = booking

    with patch("src.services.booking_service.event_bus.emit", new=AsyncMock()), \
         patch.object(service, "_release_slot", new=AsyncMock()) as release_mock:
        await service.update_status(session, booking_id, BookingStatus.rejected, uuid.uuid4())

    release_mock.assert_awaited_once_with(session, vendor_id, service_id, date(2027, 6, 1))
    assert booking.status == BookingStatus.rejected
    assert BookingStatus.completed in VALID_TRANSITIONS[BookingStatus.in_progress]
