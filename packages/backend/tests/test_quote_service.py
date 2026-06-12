"""
Unit tests for QuoteService — negotiation loop.

Uses AsyncMock for the session so no real DB is needed.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.models.booking import Booking, BookingStatus
from src.models.quote import (
    CounterOffer,
    CounterOfferStatus,
    Quote,
    QuoteCreate,
    QuoteStatus,
    CounterOfferCreate,
)
from src.models.vendor import Vendor
from src.services.quote_service import QuoteService, MAX_NEGOTIATION_ROUNDS


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_vendor(user_id=None):
    v = MagicMock(spec=Vendor)
    v.id = uuid.uuid4()
    v.user_id = user_id or uuid.uuid4()
    return v


def _make_booking(vendor_id=None, user_id=None, booking_status=BookingStatus.pending):
    b = MagicMock(spec=Booking)
    b.id = uuid.uuid4()
    b.vendor_id = vendor_id or uuid.uuid4()
    b.user_id = user_id or uuid.uuid4()
    b.status = booking_status
    b.total_price = 10000.0
    b.event_date = None
    b.service_id = uuid.uuid4()
    b.updated_at = None
    return b


def _make_quote(vendor_id=None, booking_id=None, quote_status=QuoteStatus.sent):
    q = MagicMock(spec=Quote)
    q.id = uuid.uuid4()
    q.vendor_id = vendor_id or uuid.uuid4()
    q.booking_id = booking_id or uuid.uuid4()
    q.status = quote_status
    q.subtotal = 50000.0
    q.updated_at = None
    return q


def _mock_session_with_vendor(vendor):
    session = AsyncMock()
    scalar_mock = AsyncMock()
    scalar_mock.scalar_one_or_none = MagicMock(return_value=vendor)
    session.execute = AsyncMock(return_value=scalar_mock)
    return session


# ── create_quote ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_quote_requires_booking_or_inquiry():
    service = QuoteService()
    vendor = _make_vendor()
    session = AsyncMock()

    # Patch _require_vendor to return vendor
    with patch.object(service, "_require_vendor", AsyncMock(return_value=vendor)):
        quote_in = QuoteCreate(subtotal=5000.0)  # no booking_id, no inquiry_id
        with pytest.raises(HTTPException) as exc:
            await service.create_quote(session, quote_in, vendor.user_id)
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_create_quote_rejects_wrong_vendor():
    service = QuoteService()
    vendor = _make_vendor()
    booking = _make_booking(vendor_id=uuid.uuid4())  # different vendor
    session = AsyncMock()

    with patch.object(service, "_require_vendor", AsyncMock(return_value=vendor)):
        with patch.object(service, "_get_booking", AsyncMock(return_value=booking)):
            quote_in = QuoteCreate(booking_id=booking.id, subtotal=5000.0)
            with pytest.raises(HTTPException) as exc:
                await service.create_quote(session, quote_in, vendor.user_id)
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "AUTH_FORBIDDEN"


@pytest.mark.asyncio
async def test_create_quote_rejects_confirmed_booking():
    service = QuoteService()
    vendor = _make_vendor()
    booking = _make_booking(vendor_id=vendor.id, booking_status=BookingStatus.confirmed)
    session = AsyncMock()

    with patch.object(service, "_require_vendor", AsyncMock(return_value=vendor)):
        with patch.object(service, "_get_booking", AsyncMock(return_value=booking)):
            quote_in = QuoteCreate(booking_id=booking.id, subtotal=5000.0)
            with pytest.raises(HTTPException) as exc:
                await service.create_quote(session, quote_in, vendor.user_id)
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "CONFLICT_INVALID_STATE"


# ── accept_quote ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_accept_quote_wrong_status_raises_409():
    service = QuoteService()
    quote = _make_quote(quote_status=QuoteStatus.withdrawn)
    session = AsyncMock()

    with patch.object(service, "_get_quote", AsyncMock(return_value=quote)):
        with pytest.raises(HTTPException) as exc:
            await service.accept_quote(session, quote.id, uuid.uuid4())
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "CONFLICT_INVALID_STATE"


@pytest.mark.asyncio
async def test_accept_quote_wrong_user_raises_403():
    service = QuoteService()
    booking = _make_booking()
    quote = _make_quote(booking_id=booking.id, quote_status=QuoteStatus.sent)
    session = AsyncMock()
    other_user = uuid.uuid4()  # not the booking owner

    with patch.object(service, "_get_quote", AsyncMock(return_value=quote)):
        with patch.object(service, "_get_booking", AsyncMock(return_value=booking)):
            with pytest.raises(HTTPException) as exc:
                await service.accept_quote(session, quote.id, other_user)
    assert exc.value.status_code == 403


# ── withdraw_quote ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_withdraw_accepted_quote_raises_409():
    service = QuoteService()
    vendor = _make_vendor()
    quote = _make_quote(vendor_id=vendor.id, quote_status=QuoteStatus.accepted)
    session = AsyncMock()

    with patch.object(service, "_require_vendor", AsyncMock(return_value=vendor)):
        with patch.object(service, "_get_quote", AsyncMock(return_value=quote)):
            with pytest.raises(HTTPException) as exc:
                await service.withdraw_quote(session, quote.id, vendor.user_id)
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "CONFLICT_INVALID_STATE"


@pytest.mark.asyncio
async def test_withdraw_wrong_vendor_raises_403():
    service = QuoteService()
    vendor = _make_vendor()
    quote = _make_quote(vendor_id=uuid.uuid4(), quote_status=QuoteStatus.sent)  # other vendor
    session = AsyncMock()

    with patch.object(service, "_require_vendor", AsyncMock(return_value=vendor)):
        with patch.object(service, "_get_quote", AsyncMock(return_value=quote)):
            with pytest.raises(HTTPException) as exc:
                await service.withdraw_quote(session, quote.id, vendor.user_id)
    assert exc.value.status_code == 403


# ── submit_counter ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_counter_not_sent_raises_409():
    service = QuoteService()
    quote = _make_quote(quote_status=QuoteStatus.countered)
    session = AsyncMock()

    with patch.object(service, "_get_quote", AsyncMock(return_value=quote)):
        with pytest.raises(HTTPException) as exc:
            await service.submit_counter(
                session, quote.id, CounterOfferCreate(proposed_total=40000.0), uuid.uuid4()
            )
    assert exc.value.status_code == 409
    assert "sent" in exc.value.detail["message"]


@pytest.mark.asyncio
async def test_submit_counter_enforces_max_rounds():
    service = QuoteService()
    booking = _make_booking()
    quote = _make_quote(booking_id=booking.id, quote_status=QuoteStatus.sent)
    session = AsyncMock()

    # simulate round count at max
    count_result = MagicMock()
    count_result.scalar = MagicMock(return_value=MAX_NEGOTIATION_ROUNDS)
    session.execute = AsyncMock(return_value=count_result)

    with patch.object(service, "_get_quote", AsyncMock(return_value=quote)):
        with patch.object(service, "_get_booking", AsyncMock(return_value=booking)):
            with pytest.raises(HTTPException) as exc:
                await service.submit_counter(
                    session, quote.id, CounterOfferCreate(proposed_total=40000.0), booking.user_id
                )
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "CONFLICT_MAX_ROUNDS"


@pytest.mark.asyncio
async def test_submit_counter_wrong_user_raises_403():
    service = QuoteService()
    booking = _make_booking()
    quote = _make_quote(booking_id=booking.id, quote_status=QuoteStatus.sent)
    session = AsyncMock()

    count_result = MagicMock()
    count_result.scalar = MagicMock(return_value=0)
    session.execute = AsyncMock(return_value=count_result)

    other_user = uuid.uuid4()
    with patch.object(service, "_get_quote", AsyncMock(return_value=quote)):
        with patch.object(service, "_get_booking", AsyncMock(return_value=booking)):
            with pytest.raises(HTTPException) as exc:
                await service.submit_counter(
                    session, quote.id, CounterOfferCreate(proposed_total=40000.0), other_user
                )
    assert exc.value.status_code == 403


# ── respond_to_counter ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_respond_invalid_action_raises_422():
    service = QuoteService()
    vendor = _make_vendor()
    counter = MagicMock(spec=CounterOffer)
    counter.id = uuid.uuid4()
    counter.status = CounterOfferStatus.pending
    counter.quote_id = uuid.uuid4()
    counter.proposed_total = 40000.0
    counter.updated_at = None
    quote = _make_quote(vendor_id=vendor.id, quote_status=QuoteStatus.countered)
    session = AsyncMock()
    session.get = AsyncMock(return_value=counter)

    with patch.object(service, "_require_vendor", AsyncMock(return_value=vendor)):
        with patch.object(service, "_get_quote", AsyncMock(return_value=quote)):
            with pytest.raises(HTTPException) as exc:
                await service.respond_to_counter(session, counter.id, "maybe", None, vendor.user_id)
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_respond_already_settled_raises_409():
    service = QuoteService()
    vendor = _make_vendor()
    counter = MagicMock(spec=CounterOffer)
    counter.id = uuid.uuid4()
    counter.status = CounterOfferStatus.accepted  # already settled
    session = AsyncMock()
    session.get = AsyncMock(return_value=counter)

    with patch.object(service, "_require_vendor", AsyncMock(return_value=vendor)):
        with pytest.raises(HTTPException) as exc:
            await service.respond_to_counter(session, counter.id, "accept", None, vendor.user_id)
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "CONFLICT_INVALID_STATE"


# ── booking state machine ─────────────────────────────────────────────────────

def test_valid_transitions_include_negotiation_states():
    from src.services.booking_service import VALID_TRANSITIONS
    assert BookingStatus.quoted in VALID_TRANSITIONS[BookingStatus.pending]
    assert BookingStatus.accepted in VALID_TRANSITIONS[BookingStatus.quoted]
    assert BookingStatus.negotiating in VALID_TRANSITIONS[BookingStatus.quoted]
    assert BookingStatus.confirmed in VALID_TRANSITIONS[BookingStatus.awaiting_deposit]
    assert BookingStatus.confirmed in VALID_TRANSITIONS[BookingStatus.accepted]


def test_new_booking_statuses_exist():
    assert BookingStatus.quoted.value == "quoted"
    assert BookingStatus.negotiating.value == "negotiating"
    assert BookingStatus.accepted.value == "accepted"
    assert BookingStatus.awaiting_deposit.value == "awaiting_deposit"
