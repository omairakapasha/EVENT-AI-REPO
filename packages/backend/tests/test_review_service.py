"""
Unit tests for ReviewService — vendor reviews after a completed booking.

Uses AsyncMock for the session so no real DB is needed.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.models.booking import Booking, BookingStatus
from src.models.review import Review, ReviewCreate
from src.models.user import User
from src.models.vendor import Vendor
from src.services.review_service import ReviewService


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_vendor(vendor_id=None, user_id=None, rating=4.0, total_reviews=2):
    v = MagicMock(spec=Vendor)
    v.id = vendor_id or uuid.uuid4()
    v.user_id = user_id or uuid.uuid4()
    v.rating = rating
    v.total_reviews = total_reviews
    return v


def _make_booking(booking_id=None, vendor_id=None, user_id=None, booking_status=BookingStatus.completed):
    b = MagicMock(spec=Booking)
    b.id = booking_id or uuid.uuid4()
    b.vendor_id = vendor_id or uuid.uuid4()
    b.user_id = user_id or uuid.uuid4()
    b.status = booking_status
    b.event_date = None
    return b


def _make_user(user_id=None, first_name="Ayesha"):
    u = MagicMock(spec=User)
    u.id = user_id or uuid.uuid4()
    u.first_name = first_name
    return u


# ── create_review ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_review_vendor_not_found_raises_404():
    service = ReviewService()
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await service.create_review(session, uuid.uuid4(), ReviewCreate(rating=5), uuid.uuid4())

    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "NOT_FOUND_VENDOR"
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_create_review_no_completed_booking_raises_409():
    service = ReviewService()
    vendor_id = uuid.uuid4()
    user_id = uuid.uuid4()
    vendor = _make_vendor(vendor_id=vendor_id)

    session = AsyncMock()
    session.get = AsyncMock(return_value=vendor)

    no_booking_result = MagicMock()
    no_booking_result.scalars.return_value.first.return_value = None
    session.execute = AsyncMock(return_value=no_booking_result)

    with pytest.raises(HTTPException) as exc:
        await service.create_review(session, vendor_id, ReviewCreate(rating=5, comment="Great!"), user_id)

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "CONFLICT_REVIEW_NOT_ALLOWED"
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_create_review_success_recalculates_vendor_rating():
    service = ReviewService()
    vendor_id = uuid.uuid4()
    user_id = uuid.uuid4()
    vendor = _make_vendor(vendor_id=vendor_id, rating=4.0, total_reviews=2)
    booking = _make_booking(vendor_id=vendor_id, user_id=user_id)
    user = _make_user(user_id=user_id, first_name="Ayesha")

    session = AsyncMock()
    session.get = AsyncMock(side_effect=[vendor, user])

    booking_result = MagicMock()
    booking_result.scalars.return_value.first.return_value = booking

    agg_result = MagicMock()
    agg_result.one.return_value = (4.5, 3)

    session.execute = AsyncMock(side_effect=[booking_result, agg_result])

    with patch("src.services.review_service.event_bus.emit", new=AsyncMock()) as mock_emit:
        result = await service.create_review(
            session, vendor_id, ReviewCreate(rating=5, comment="Great!"), user_id
        )

    # Vendor aggregate rating recalculated from the avg/count query
    assert vendor.rating == 4.5
    assert vendor.total_reviews == 3

    # Domain event emitted
    mock_emit.assert_awaited_once()
    assert mock_emit.call_args.args[1] == "review.created"

    # Returned review reflects input + reviewer's first name
    assert result.rating == 5
    assert result.comment == "Great!"
    assert result.vendor_id == vendor_id
    assert result.booking_id == booking.id
    assert result.user_name == "Ayesha"

    session.add.assert_called_once()
    added_review = session.add.call_args.args[0]
    assert isinstance(added_review, Review)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_review_falls_back_to_default_user_name():
    service = ReviewService()
    vendor_id = uuid.uuid4()
    user_id = uuid.uuid4()
    vendor = _make_vendor(vendor_id=vendor_id, rating=0.0, total_reviews=0)
    booking = _make_booking(vendor_id=vendor_id, user_id=user_id)
    user = _make_user(user_id=user_id, first_name=None)

    session = AsyncMock()
    session.get = AsyncMock(side_effect=[vendor, user])

    booking_result = MagicMock()
    booking_result.scalars.return_value.first.return_value = booking

    agg_result = MagicMock()
    agg_result.one.return_value = (5.0, 1)

    session.execute = AsyncMock(side_effect=[booking_result, agg_result])

    with patch("src.services.review_service.event_bus.emit", new=AsyncMock()):
        result = await service.create_review(
            session, vendor_id, ReviewCreate(rating=5), user_id
        )

    assert result.user_name == "User"


# ── list_vendor_reviews ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_vendor_reviews_vendor_not_found_raises_404():
    service = ReviewService()
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await service.list_vendor_reviews(session, uuid.uuid4())

    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "NOT_FOUND_VENDOR"


@pytest.mark.asyncio
async def test_list_vendor_reviews_returns_newest_first_with_user_names():
    service = ReviewService()
    vendor_id = uuid.uuid4()
    vendor = _make_vendor(vendor_id=vendor_id)

    review1 = Review(booking_id=uuid.uuid4(), vendor_id=vendor_id, user_id=uuid.uuid4(), rating=5, comment="Loved it")
    review2 = Review(booking_id=uuid.uuid4(), vendor_id=vendor_id, user_id=uuid.uuid4(), rating=3, comment="It was okay")

    session = AsyncMock()
    session.get = AsyncMock(return_value=vendor)

    list_result = MagicMock()
    list_result.all.return_value = [(review1, "Ayesha"), (review2, None)]
    session.execute = AsyncMock(return_value=list_result)

    reviews = await service.list_vendor_reviews(session, vendor_id)

    assert len(reviews) == 2
    assert reviews[0].rating == 5
    assert reviews[0].user_name == "Ayesha"
    assert reviews[1].rating == 3
    assert reviews[1].user_name == "User"
