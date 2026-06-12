import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, JSON
from sqlmodel import Field, SQLModel


class NotificationType(str, Enum):
    booking_created = "booking_created"
    booking_confirmed = "booking_confirmed"
    booking_cancelled = "booking_cancelled"
    booking_completed = "booking_completed"
    booking_rejected = "booking_rejected"
    booking_status_changed = "booking_status_changed"
    booking_counter_offered = "booking_counter_offered"
    booking_quoted = "booking_quoted"
    booking_accepted = "booking_accepted"
    booking_counter_rejected = "booking_counter_rejected"
    system = "system"
    # Event domain events
    event_created = "event_created"
    event_status_changed = "event_status_changed"
    event_cancelled = "event_cancelled"
    # Vendor domain events
    vendor_approved = "vendor_approved"
    vendor_rejected = "vendor_rejected"
    vendor_suspended = "vendor_suspended"
    subscription_granted = "subscription_granted"
    subscription_revoked = "subscription_revoked"
    inquiry_created = "inquiry_created"


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(index=True)
    type: NotificationType
    title: str = Field(max_length=255)
    body: str
    # JSON works on both SQLite (tests) and Postgres (prod); Alembic migration uses JSONB explicitly
    data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    is_read: bool = Field(default=False)
    read_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class NotificationRead(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    title: str
    body: str
    data: Dict[str, Any]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}
