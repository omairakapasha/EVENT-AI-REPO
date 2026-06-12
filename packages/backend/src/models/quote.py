"""
Quote and CounterOffer models for the vendor negotiation loop.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class QuoteStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    accepted = "accepted"
    countered = "countered"
    expired = "expired"
    withdrawn = "withdrawn"


class CounterOfferStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    superseded = "superseded"


class Quote(SQLModel, table=True):
    __tablename__ = "quotes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    booking_id: Optional[uuid.UUID] = Field(default=None, foreign_key="bookings.id", index=True)
    inquiry_id: Optional[uuid.UUID] = Field(default=None, foreign_key="customer_inquiries.id", index=True)
    vendor_id: uuid.UUID = Field(foreign_key="vendors.id", index=True)

    line_items: List[Dict[str, Any]] = Field(
        default_factory=list, sa_column=Column("line_items", JSON)
    )
    subtotal: float = Field(default=0.0)
    deposit_required: float = Field(default=0.0)
    currency: str = Field(default="PKR", max_length=3)
    valid_until: Optional[datetime] = None

    status: QuoteStatus = Field(default=QuoteStatus.draft)
    notes: Optional[str] = None

    round_number: int = Field(default=1)

    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class QuoteCreate(SQLModel):
    booking_id: Optional[uuid.UUID] = None
    inquiry_id: Optional[uuid.UUID] = None
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    subtotal: float
    deposit_required: float = 0.0
    currency: str = "PKR"
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None


class QuoteRead(SQLModel):
    id: uuid.UUID
    booking_id: Optional[uuid.UUID] = None
    inquiry_id: Optional[uuid.UUID] = None
    vendor_id: uuid.UUID
    line_items: List[Dict[str, Any]]
    subtotal: float
    deposit_required: float
    currency: str
    valid_until: Optional[datetime] = None
    status: QuoteStatus
    notes: Optional[str] = None
    round_number: int
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CounterOffer(SQLModel, table=True):
    __tablename__ = "counter_offers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    quote_id: uuid.UUID = Field(foreign_key="quotes.id", index=True)
    proposed_by_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)

    proposed_total: float
    proposed_changes: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column("proposed_changes", JSON)
    )
    message: Optional[str] = None

    status: CounterOfferStatus = Field(default=CounterOfferStatus.pending)

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class CounterOfferCreate(SQLModel):
    proposed_total: float
    proposed_changes: Dict[str, Any] = Field(default_factory=dict)
    message: Optional[str] = None


class CounterOfferRead(SQLModel):
    id: uuid.UUID
    quote_id: uuid.UUID
    proposed_by_user_id: uuid.UUID
    proposed_total: float
    proposed_changes: Dict[str, Any]
    message: Optional[str] = None
    status: CounterOfferStatus
    created_at: datetime
    updated_at: datetime


class CounterOfferRespond(SQLModel):
    action: str  # "accept" | "reject"
    message: Optional[str] = None
