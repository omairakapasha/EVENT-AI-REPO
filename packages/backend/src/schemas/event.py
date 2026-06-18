"""
Pydantic schemas for Event and EventType.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator

from src.models.event import EventStatus


# ── EventType ─────────────────────────────────────────────────────────────────

class EventTypeBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=255)
    display_order: int = 0
    is_active: bool = True


class EventTypeCreate(EventTypeBase):
    pass


class EventTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=255)
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class EventTypeRead(EventTypeBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Event ─────────────────────────────────────────────────────────────────────

class EventCreate(BaseModel):
    event_type_id: uuid.UUID
    name: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    start_date: datetime
    end_date: Optional[datetime] = None
    timezone: str = Field("UTC", max_length=50)
    venue_name: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    country: str = Field(..., max_length=100)
    guest_count: Optional[int] = Field(None, ge=1)
    budget: Optional[float] = Field(None, ge=0)
    special_requirements: Optional[str] = Field(None, max_length=2000)

    @field_validator("start_date")
    @classmethod
    def start_date_must_be_future(cls, v: datetime) -> datetime:
        now = datetime.now(timezone.utc)
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= now:
            raise ValueError("start_date must be in the future")
        return v

    @model_validator(mode="after")
    def end_date_after_start(self) -> "EventCreate":
        if self.end_date is not None and self.start_date is not None:
            start = self.start_date
            end = self.end_date
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            if end <= start:
                raise ValueError("end_date must be after start_date")
        return self


class EventUpdate(BaseModel):
    event_type_id: Optional[uuid.UUID] = None
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    timezone: Optional[str] = Field(None, max_length=50)
    venue_name: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    guest_count: Optional[int] = Field(None, ge=1)
    budget: Optional[float] = Field(None, ge=0)
    special_requirements: Optional[str] = Field(None, max_length=2000)

    @field_validator("start_date")
    @classmethod
    def start_date_must_be_future(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return v
        now = datetime.now(timezone.utc)
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= now:
            raise ValueError("start_date must be in the future")
        return v

    @model_validator(mode="after")
    def end_date_after_start(self) -> "EventUpdate":
        if self.end_date is not None and self.start_date is not None:
            start = self.start_date
            end = self.end_date
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            if end <= start:
                raise ValueError("end_date must be after start_date")
        return self


class EventStatusUpdate(BaseModel):
    status: EventStatus
    reason: Optional[str] = Field(None, max_length=500)


class EventCancel(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class EventRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    event_type_id: uuid.UUID
    name: str
    description: Optional[str]
    start_date: datetime
    end_date: Optional[datetime]
    timezone: str
    venue_name: Optional[str]
    address: Optional[str]
    city: Optional[str]
    country: str
    guest_count: Optional[int]
    budget: Optional[float]
    special_requirements: Optional[str]
    status: str
    cancellation_reason: Optional[str]
    canceled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    success: bool = True
    data: List[EventRead]
    meta: dict
