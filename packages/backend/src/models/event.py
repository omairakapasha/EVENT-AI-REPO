"""
Event and EventType models for event management.
"""
import uuid
import enum
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import ENUM


class EventStatus(str, enum.Enum):
    DRAFT = "draft"
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELED = "canceled"


class EventType(SQLModel, table=True):
    __tablename__ = "event_types"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(unique=True, index=True, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    icon: Optional[str] = Field(default=None, max_length=255)
    display_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )


class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    event_type_id: uuid.UUID = Field(foreign_key="event_types.id", index=True)

    name: str = Field(max_length=200, index=True)
    description: Optional[str] = Field(default=None, max_length=5000)

    # Date/time (stored UTC)
    start_date: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    end_date: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    timezone: str = Field(default="Asia/Karachi", max_length=50)

    # Location
    venue_name: Optional[str] = Field(default=None, max_length=255)
    address: Optional[str] = Field(default=None, max_length=500)
    city: Optional[str] = Field(default=None, max_length=100)
    country: str = Field(max_length=100)

    # Planning details
    guest_count: Optional[int] = Field(default=None, ge=1)
    budget: Optional[float] = Field(default=None, ge=0)
    special_requirements: Optional[str] = Field(default=None, max_length=2000)

    # Status
    status: str = Field(
        default=EventStatus.DRAFT,
        sa_column=Column(
            ENUM(
                "draft", "planned", "active", "completed", "canceled",
                name="event_status_enum",
                create_type=False,
            )
        ),
    )

    # Cancellation
    cancellation_reason: Optional[str] = Field(default=None, max_length=500)
    canceled_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
