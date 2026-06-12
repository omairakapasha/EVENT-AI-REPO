"""
Review model — customer feedback for a vendor after a completed booking.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Review(SQLModel, table=True):
    __tablename__ = "reviews"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    booking_id: uuid.UUID = Field(foreign_key="bookings.id", unique=True, index=True)
    vendor_id: uuid.UUID = Field(foreign_key="vendors.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)

    rating: int
    comment: Optional[str] = None

    created_at: datetime = Field(default_factory=_utcnow)


class ReviewCreate(SQLModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)


class ReviewRead(SQLModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    vendor_id: uuid.UUID
    user_id: uuid.UUID
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    user_name: Optional[str] = None

    model_config = {"from_attributes": True}
