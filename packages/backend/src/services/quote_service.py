"""
QuoteService — business logic for the vendor negotiation loop.

Covers quote creation/withdrawal by vendors, acceptance by customers,
counter-offers from customers, vendor responses, and the inquiry→quote bridge.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

import structlog
from fastapi import HTTPException, status as http_status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.booking import Booking, BookingStatus
from src.models.inquiry import CustomerInquiry, InquiryStatus
from src.models.quote import (
    CounterOffer,
    CounterOfferCreate,
    CounterOfferStatus,
    Quote,
    QuoteCreate,
    QuoteStatus,
    _utcnow,
)
from src.models.vendor import Vendor
from src.services.event_bus_service import event_bus

logger = structlog.get_logger()

MAX_NEGOTIATION_ROUNDS = 5


def _err(code: str, message: str) -> dict:
    return {"code": code, "message": message}


class QuoteService:

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _require_vendor(
        self, session: AsyncSession, user_id: uuid.UUID
    ) -> Vendor:
        result = await session.execute(select(Vendor).where(Vendor.user_id == user_id))
        vendor = result.scalar_one_or_none()
        if not vendor:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail=_err("AUTH_FORBIDDEN", "Only vendors can perform this action."),
            )
        return vendor

    async def _get_quote(
        self, session: AsyncSession, quote_id: uuid.UUID
    ) -> Quote:
        quote = await session.get(Quote, quote_id)
        if not quote:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=_err("NOT_FOUND_QUOTE", "Quote not found."),
            )
        return quote

    async def _get_booking(
        self, session: AsyncSession, booking_id: uuid.UUID
    ) -> Booking:
        booking = await session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=_err("NOT_FOUND_BOOKING", "Booking not found."),
            )
        return booking

    # ── Quote lifecycle ───────────────────────────────────────────────────────

    async def create_quote(
        self,
        session: AsyncSession,
        quote_in: QuoteCreate,
        vendor_user_id: uuid.UUID,
    ) -> Quote:
        """Vendor creates and immediately sends a quote for a booking or inquiry."""
        vendor = await self._require_vendor(session, vendor_user_id)

        if quote_in.booking_id is None and quote_in.inquiry_id is None:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_err("VALIDATION_ERROR", "Either booking_id or inquiry_id is required."),
            )

        if quote_in.booking_id:
            booking = await self._get_booking(session, quote_in.booking_id)
            if booking.vendor_id != vendor.id:
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail=_err("AUTH_FORBIDDEN", "This booking does not belong to your vendor account."),
                )
            _quoteable = {BookingStatus.pending, BookingStatus.negotiating}
            if booking.status not in _quoteable:
                raise HTTPException(
                    status_code=http_status.HTTP_409_CONFLICT,
                    detail=_err("CONFLICT_INVALID_STATE",
                                f"Cannot quote a booking in '{booking.status}' state."),
                )

        quote = Quote(
            booking_id=quote_in.booking_id,
            inquiry_id=quote_in.inquiry_id,
            vendor_id=vendor.id,
            line_items=quote_in.line_items,
            subtotal=quote_in.subtotal,
            deposit_required=quote_in.deposit_required,
            currency=quote_in.currency,
            valid_until=quote_in.valid_until,
            notes=quote_in.notes,
            status=QuoteStatus.sent,
            created_by=vendor_user_id,
        )
        session.add(quote)
        await session.flush()

        if quote_in.booking_id:
            booking = await self._get_booking(session, quote_in.booking_id)
            booking.status = BookingStatus.quoted
            booking.updated_at = _utcnow()
            await event_bus.emit(
                session,
                "booking.quoted",
                payload={"booking_id": str(quote_in.booking_id), "quote_id": str(quote.id)},
                user_id=vendor_user_id,
            )

        # Wire inquiry → quote bridge (G1.5)
        if quote_in.inquiry_id:
            inquiry = await session.get(CustomerInquiry, quote_in.inquiry_id)
            if inquiry and inquiry.status == InquiryStatus.NEW:
                inquiry.status = InquiryStatus.QUOTED
                inquiry.vendor_response = f"Quote sent: PKR {quote_in.subtotal:,.0f}"
                inquiry.vendor_responded_at = _utcnow()
                inquiry.quote_id = quote.id
                inquiry.quoted_amount = quote_in.subtotal

        await session.commit()
        await session.refresh(quote)
        logger.info("quote.created", quote_id=str(quote.id), vendor_id=str(vendor.id))
        return quote

    async def list_quotes_for_booking(
        self,
        session: AsyncSession,
        booking_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
    ) -> List[Quote]:
        """Return all quotes for a booking. Accessible by booking owner or vendor."""
        booking = await self._get_booking(session, booking_id)

        vendor = (
            await session.execute(select(Vendor).where(Vendor.user_id == requesting_user_id))
        ).scalar_one_or_none()
        is_customer = booking.user_id == requesting_user_id
        is_vendor = vendor is not None and booking.vendor_id == vendor.id
        if not (is_customer or is_vendor):
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail=_err("AUTH_FORBIDDEN", "Not authorized to view quotes for this booking."),
            )

        result = await session.execute(
            select(Quote)
            .where(Quote.booking_id == booking_id)
            .order_by(Quote.round_number.asc(), Quote.created_at.asc())
        )
        return list(result.scalars().all())

    async def accept_quote(
        self,
        session: AsyncSession,
        quote_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Quote:
        """Customer accepts a quote; moves booking to 'accepted'."""
        quote = await self._get_quote(session, quote_id)

        if quote.status not in {QuoteStatus.sent, QuoteStatus.countered}:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=_err("CONFLICT_INVALID_STATE",
                            f"Cannot accept a quote with status '{quote.status}'."),
            )

        if quote.booking_id:
            booking = await self._get_booking(session, quote.booking_id)
            if booking.user_id != user_id:
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail=_err("AUTH_FORBIDDEN", "Only the booking customer can accept a quote."),
                )
            booking.status = BookingStatus.accepted
            booking.updated_at = _utcnow()
            await event_bus.emit(
                session,
                "booking.accepted",
                payload={"booking_id": str(quote.booking_id), "quote_id": str(quote_id), "actor": "customer"},
                user_id=user_id,
            )

        quote.status = QuoteStatus.accepted
        quote.updated_at = _utcnow()
        await session.commit()
        await session.refresh(quote)
        logger.info("quote.accepted", quote_id=str(quote_id), user_id=str(user_id))
        return quote

    async def withdraw_quote(
        self,
        session: AsyncSession,
        quote_id: uuid.UUID,
        vendor_user_id: uuid.UUID,
    ) -> Quote:
        """Vendor withdraws an unsettled quote."""
        vendor = await self._require_vendor(session, vendor_user_id)
        quote = await self._get_quote(session, quote_id)

        if quote.vendor_id != vendor.id:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail=_err("AUTH_FORBIDDEN", "This quote does not belong to your vendor account."),
            )
        if quote.status in {QuoteStatus.accepted, QuoteStatus.withdrawn}:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=_err("CONFLICT_INVALID_STATE",
                            f"Cannot withdraw a quote with status '{quote.status}'."),
            )

        quote.status = QuoteStatus.withdrawn
        quote.updated_at = _utcnow()
        await session.commit()
        await session.refresh(quote)
        logger.info("quote.withdrawn", quote_id=str(quote_id), vendor_id=str(vendor.id))
        return quote

    # ── Counter-offers ────────────────────────────────────────────────────────

    async def submit_counter(
        self,
        session: AsyncSession,
        quote_id: uuid.UUID,
        counter_in: CounterOfferCreate,
        user_id: uuid.UUID,
    ) -> CounterOffer:
        """Customer counters a sent quote. Enforces round limit."""
        quote = await self._get_quote(session, quote_id)

        if quote.status != QuoteStatus.sent:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=_err("CONFLICT_INVALID_STATE",
                            f"Can only counter a quote with status 'sent', not '{quote.status}'."),
            )

        round_count_result = await session.execute(
            select(func.count()).select_from(CounterOffer).where(CounterOffer.quote_id == quote_id)
        )
        round_count = round_count_result.scalar() or 0
        if round_count >= MAX_NEGOTIATION_ROUNDS:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=_err("CONFLICT_MAX_ROUNDS",
                            f"Maximum negotiation rounds ({MAX_NEGOTIATION_ROUNDS}) reached."),
            )

        if quote.booking_id:
            booking = await self._get_booking(session, quote.booking_id)
            if booking.user_id != user_id:
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail=_err("AUTH_FORBIDDEN", "Only the booking customer can counter a quote."),
                )
            if booking.status != BookingStatus.negotiating:
                booking.status = BookingStatus.negotiating
                booking.updated_at = _utcnow()

        # Supersede any previous pending counters on this quote
        existing = await session.execute(
            select(CounterOffer).where(
                CounterOffer.quote_id == quote_id,
                CounterOffer.status == CounterOfferStatus.pending,
            )
        )
        for old in existing.scalars().all():
            old.status = CounterOfferStatus.superseded
            old.updated_at = _utcnow()

        counter = CounterOffer(
            quote_id=quote_id,
            proposed_by_user_id=user_id,
            proposed_total=counter_in.proposed_total,
            proposed_changes=counter_in.proposed_changes,
            message=counter_in.message,
        )
        session.add(counter)

        quote.status = QuoteStatus.countered
        quote.updated_at = _utcnow()

        if quote.booking_id:
            await event_bus.emit(
                session,
                "booking.counter_offered",
                payload={
                    "booking_id": str(quote.booking_id),
                    "quote_id": str(quote_id),
                    "proposed_total": counter_in.proposed_total,
                },
                user_id=user_id,
            )

        await session.commit()
        await session.refresh(counter)
        logger.info("counter_offer.submitted", quote_id=str(quote_id), user_id=str(user_id))
        return counter

    async def respond_to_counter(
        self,
        session: AsyncSession,
        counter_id: uuid.UUID,
        action: str,
        message: Optional[str],
        vendor_user_id: uuid.UUID,
    ) -> CounterOffer:
        """Vendor accepts or rejects a counter-offer."""
        vendor = await self._require_vendor(session, vendor_user_id)

        counter = await session.get(CounterOffer, counter_id)
        if not counter:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=_err("NOT_FOUND_COUNTER_OFFER", "Counter-offer not found."),
            )
        if counter.status != CounterOfferStatus.pending:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=_err("CONFLICT_INVALID_STATE",
                            f"Counter-offer is already '{counter.status}'."),
            )
        if action not in {"accept", "reject"}:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_err("VALIDATION_ERROR", "action must be 'accept' or 'reject'."),
            )

        quote = await self._get_quote(session, counter.quote_id)
        if quote.vendor_id != vendor.id:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail=_err("AUTH_FORBIDDEN", "This counter-offer is not for your quote."),
            )

        if action == "accept":
            counter.status = CounterOfferStatus.accepted
            quote.status = QuoteStatus.accepted
            quote.subtotal = counter.proposed_total

            if quote.booking_id:
                booking = await self._get_booking(session, quote.booking_id)
                booking.status = BookingStatus.accepted
                booking.total_price = counter.proposed_total
                booking.updated_at = _utcnow()
                await event_bus.emit(
                    session,
                    "booking.accepted",
                    payload={"booking_id": str(quote.booking_id), "quote_id": str(quote.id), "actor": "vendor"},
                    user_id=vendor_user_id,
                )
        else:
            counter.status = CounterOfferStatus.rejected
            # Restore quote to 'sent' so customer can accept original or try again
            quote.status = QuoteStatus.sent

            if quote.booking_id:
                await event_bus.emit(
                    session,
                    "booking.counter_rejected",
                    payload={"booking_id": str(quote.booking_id), "quote_id": str(quote.id), "counter_id": str(counter_id)},
                    user_id=vendor_user_id,
                )

        counter.updated_at = _utcnow()
        quote.updated_at = _utcnow()

        await session.commit()
        await session.refresh(counter)
        logger.info("counter_offer.responded",
                    counter_id=str(counter_id), action=action, vendor_id=str(vendor.id))
        return counter

    async def list_counters_for_quote(
        self,
        session: AsyncSession,
        quote_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
    ) -> List[CounterOffer]:
        """List all counter-offers for a quote (customer or vendor)."""
        quote = await self._get_quote(session, quote_id)

        vendor = (
            await session.execute(select(Vendor).where(Vendor.user_id == requesting_user_id))
        ).scalar_one_or_none()
        is_vendor = vendor is not None and quote.vendor_id == vendor.id
        is_customer = False
        if quote.booking_id:
            booking = await self._get_booking(session, quote.booking_id)
            is_customer = booking.user_id == requesting_user_id
        if not (is_vendor or is_customer):
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail=_err("AUTH_FORBIDDEN", "Not authorized to view these counter-offers."),
            )

        result = await session.execute(
            select(CounterOffer)
            .where(CounterOffer.quote_id == quote_id)
            .order_by(CounterOffer.created_at.asc())
        )
        return list(result.scalars().all())


quote_service = QuoteService()
