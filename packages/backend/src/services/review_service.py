"""
ReviewService — customer feedback for vendors after a completed booking.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

import structlog
from fastapi import HTTPException, status as http_status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.booking import Booking, BookingStatus
from src.models.review import Review, ReviewCreate, ReviewRead
from src.models.user import User
from src.models.vendor import Vendor
from src.services.event_bus_service import event_bus

logger = structlog.get_logger()


def _err(code: str, message: str) -> dict:
    return {"code": code, "message": message}


class ReviewService:

    async def _get_vendor(self, session: AsyncSession, vendor_id: uuid.UUID) -> Vendor:
        vendor = await session.get(Vendor, vendor_id)
        if not vendor:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=_err("NOT_FOUND_VENDOR", "Vendor not found."),
            )
        return vendor

    async def _find_reviewable_booking(
        self, session: AsyncSession, vendor_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Booking]:
        """A booking is reviewable if it's completed, belongs to this user/vendor,
        and doesn't already have a review."""
        stmt = (
            select(Booking)
            .outerjoin(Review, Review.booking_id == Booking.id)
            .where(
                Booking.vendor_id == vendor_id,
                Booking.user_id == user_id,
                Booking.status == BookingStatus.completed,
                Review.id.is_(None),
            )
            .order_by(Booking.event_date.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def _recalculate_vendor_rating(self, session: AsyncSession, vendor: Vendor) -> None:
        result = await session.execute(
            select(func.avg(Review.rating), func.count(Review.id)).where(Review.vendor_id == vendor.id)
        )
        avg_rating, count = result.one()
        vendor.rating = round(float(avg_rating), 1) if avg_rating is not None else 0.0
        vendor.total_reviews = int(count or 0)

    async def _push_sse(self, vendor: Vendor, review: Review) -> None:
        """Notify the vendor's open SSE connections that a new review came in."""
        try:
            from src.main import app
            cm = getattr(app.state, "connection_manager", None)
            if cm is not None:
                await cm.push(
                    vendor.user_id,
                    "review.created",
                    {
                        "vendor_id": str(vendor.id),
                        "rating": review.rating,
                        "comment": review.comment,
                        "vendor_rating": vendor.rating,
                        "total_reviews": vendor.total_reviews,
                    },
                )
        except Exception as e:
            logger.warning("review.sse_push_failed", error=str(e))

    async def create_review(
        self,
        session: AsyncSession,
        vendor_id: uuid.UUID,
        review_in: ReviewCreate,
        user_id: uuid.UUID,
    ) -> ReviewRead:
        vendor = await self._get_vendor(session, vendor_id)

        booking = await self._find_reviewable_booking(session, vendor_id, user_id)
        if booking is None:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=_err(
                    "CONFLICT_REVIEW_NOT_ALLOWED",
                    "You can review a vendor only after a completed booking, and each booking can only be reviewed once.",
                ),
            )

        review = Review(
            booking_id=booking.id,
            vendor_id=vendor_id,
            user_id=user_id,
            rating=review_in.rating,
            comment=review_in.comment,
        )
        session.add(review)
        await session.flush()

        await self._recalculate_vendor_rating(session, vendor)

        await event_bus.emit(
            session,
            "review.created",
            payload={
                "review_id": str(review.id),
                "vendor_id": str(vendor_id),
                "booking_id": str(booking.id),
                "rating": review.rating,
            },
            user_id=user_id,
        )

        await session.commit()
        await session.refresh(review)
        await session.refresh(vendor)

        await self._push_sse(vendor, review)

        logger.info("review.created", review_id=str(review.id), vendor_id=str(vendor_id))

        user = await session.get(User, user_id)
        return ReviewRead(
            **review.model_dump(),
            user_name=(user.first_name if user else None) or "User",
        )

    async def list_vendor_reviews(self, session: AsyncSession, vendor_id: uuid.UUID) -> List[ReviewRead]:
        await self._get_vendor(session, vendor_id)

        result = await session.execute(
            select(Review, User.first_name)
            .join(User, User.id == Review.user_id)
            .where(Review.vendor_id == vendor_id)
            .order_by(Review.created_at.desc())
        )
        return [
            ReviewRead(**review.model_dump(), user_name=first_name or "User")
            for review, first_name in result.all()
        ]


review_service = ReviewService()
