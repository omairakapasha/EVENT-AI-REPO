"""
Quotes and counter-offers API — negotiation loop between customers and vendors.

Routes:
  POST   /bookings/{id}/quotes          — vendor sends a quote
  GET    /bookings/{id}/quotes          — list quotes for a booking
  PATCH  /quotes/{id}/accept            — customer accepts a quote
  PATCH  /quotes/{id}/withdraw          — vendor withdraws a quote
  POST   /quotes/{id}/counter           — customer submits a counter-offer
  PATCH  /counter-offers/{id}/respond   — vendor accepts or rejects a counter-offer
  GET    /quotes/{id}/counter-offers    — list counter-offers for a quote
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.config.database import get_session
from src.models.quote import (
    CounterOfferCreate,
    CounterOfferRead,
    CounterOfferRespond,
    QuoteCreate,
    QuoteRead,
)
from src.models.user import User
from src.services.quote_service import quote_service

router = APIRouter(tags=["Quotes"])


# ── Quote routes ──────────────────────────────────────────────────────────────

@router.post(
    "/inquiries/{inquiry_id}/quotes",
    response_model=QuoteRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_quote_from_inquiry(
    inquiry_id: uuid.UUID,
    quote_in: QuoteCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Vendor creates and sends a quote directly from a customer inquiry."""
    quote_in.inquiry_id = inquiry_id
    quote_in.booking_id = None
    return await quote_service.create_quote(session, quote_in, current_user.id)


@router.post(
    "/bookings/{booking_id}/quotes",
    response_model=QuoteRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_quote(
    booking_id: uuid.UUID,
    quote_in: QuoteCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Vendor creates and sends a quote for a pending booking."""
    quote_in.booking_id = booking_id
    return await quote_service.create_quote(session, quote_in, current_user.id)


@router.get("/bookings/{booking_id}/quotes")
async def list_quotes(
    booking_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List all quotes for a booking (accessible by customer or vendor)."""
    quotes = await quote_service.list_quotes_for_booking(session, booking_id, current_user.id)
    return {
        "success": True,
        "data": [QuoteRead.model_validate(q) for q in quotes],
        "meta": {"total": len(quotes)},
    }


@router.patch("/quotes/{quote_id}/accept", response_model=QuoteRead)
async def accept_quote(
    quote_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Customer accepts a quote; booking moves to 'accepted'."""
    return await quote_service.accept_quote(session, quote_id, current_user.id)


@router.patch("/quotes/{quote_id}/withdraw", response_model=QuoteRead)
async def withdraw_quote(
    quote_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Vendor withdraws an unsettled quote."""
    return await quote_service.withdraw_quote(session, quote_id, current_user.id)


# ── Counter-offer routes ──────────────────────────────────────────────────────

@router.post(
    "/quotes/{quote_id}/counter",
    response_model=CounterOfferRead,
    status_code=status.HTTP_201_CREATED,
)
async def submit_counter(
    quote_id: uuid.UUID,
    counter_in: CounterOfferCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Customer submits a counter-offer on a sent quote."""
    return await quote_service.submit_counter(session, quote_id, counter_in, current_user.id)


@router.patch("/counter-offers/{counter_id}/respond", response_model=CounterOfferRead)
async def respond_to_counter(
    counter_id: uuid.UUID,
    body: CounterOfferRespond,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Vendor accepts or rejects a customer's counter-offer."""
    return await quote_service.respond_to_counter(
        session, counter_id, body.action, body.message, current_user.id
    )


@router.get("/quotes/{quote_id}/counter-offers")
async def list_counters(
    quote_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List all counter-offers for a quote."""
    counters = await quote_service.list_counters_for_quote(session, quote_id, current_user.id)
    return {
        "success": True,
        "data": [CounterOfferRead.model_validate(c) for c in counters],
        "meta": {"total": len(counters)},
    }
