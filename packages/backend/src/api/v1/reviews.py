"""
Reviews API — customer feedback for vendors after a completed booking.

Routes:
  GET  /vendors/{vendor_id}/reviews   — list reviews for a vendor (public)
  POST /vendors/{vendor_id}/reviews   — submit a review for a vendor (auth required)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.config.database import get_session
from src.models.review import ReviewCreate
from src.models.user import User
from src.services.review_service import review_service

router = APIRouter(tags=["Reviews"])


@router.get("/vendors/{vendor_id}/reviews")
async def list_vendor_reviews(
    vendor_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Public list of reviews for a vendor, newest first."""
    reviews = await review_service.list_vendor_reviews(session, vendor_id)
    return {
        "success": True,
        "data": [r.model_dump(mode="json") for r in reviews],
        "meta": {"total": len(reviews)},
    }


@router.post("/vendors/{vendor_id}/reviews", status_code=status.HTTP_201_CREATED)
async def submit_vendor_review(
    vendor_id: uuid.UUID,
    review_in: ReviewCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Submit a review for a vendor. Requires a completed booking with this vendor
    that hasn't been reviewed yet."""
    review = await review_service.create_review(session, vendor_id, review_in, current_user.id)
    return {"success": True, "data": review.model_dump(mode="json"), "meta": {}}
