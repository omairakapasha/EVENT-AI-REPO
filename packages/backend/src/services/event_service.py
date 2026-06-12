"""
Event Service — business logic for event lifecycle, status transitions,
domain event emission, and admin operations.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.event import Event, EventType, EventStatus
from src.models.booking import Booking, BookingStatus
from src.models.user import SubscriptionStatus, User
from src.schemas.event import EventCreate, EventUpdate
from src.services.event_bus_service import event_bus
import structlog

logger = structlog.get_logger()

# ── State machine ─────────────────────────────────────────────────────────────

VALID_TRANSITIONS: dict[EventStatus, set[EventStatus]] = {
    EventStatus.DRAFT:   {EventStatus.PLANNED, EventStatus.CANCELED},
    EventStatus.PLANNED: {EventStatus.ACTIVE,  EventStatus.CANCELED},
    EventStatus.ACTIVE:  {EventStatus.COMPLETED, EventStatus.CANCELED},
}

TERMINAL_STATUSES: set[EventStatus] = {EventStatus.COMPLETED, EventStatus.CANCELED}


def _err(code: str, message: str) -> dict:
    return {"code": code, "message": message}


class EventService:

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get_event_or_404(
        self, session: AsyncSession, event_id: uuid.UUID, user_id: uuid.UUID
    ) -> Event:
        event = await session.get(Event, event_id)
        if not event or event.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_err("NOT_FOUND_EVENT", "Event not found."),
            )
        return event

    async def _enforce_free_plan_event_limit(
        self, session: AsyncSession, user_id: uuid.UUID
    ) -> None:
        user = await session.get(User, user_id)
        if user is None or user.subscription_status != SubscriptionStatus.free:
            return
        count = (
            await session.execute(
                select(func.count())
                .select_from(Event)
                .where(Event.user_id == user_id, Event.status != EventStatus.CANCELED)
            )
        ).scalar() or 0
        if count >= 3:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_err(
                    "SUBSCRIPTION_LIMIT_EXCEEDED",
                    "Free plan allows only 3 active events. Upgrade to Pro for unlimited events.",
                ),
            )

    async def _get_active_event_type(
        self, session: AsyncSession, event_type_id: uuid.UUID
    ) -> EventType:
        et = await session.get(EventType, event_type_id)
        if not et or not et.is_active:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_err("VALIDATION_INVALID_EVENT_TYPE", "Event type not found or inactive."),
            )
        return et

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def create_event(
        self,
        session: AsyncSession,
        event_in: EventCreate,
        user_id: uuid.UUID,
    ) -> Event:
        """Validate event_type, create Event with status=PLANNED, emit event.created."""
        await self._enforce_free_plan_event_limit(session, user_id)
        await self._get_active_event_type(session, event_in.event_type_id)

        event = Event(
            **event_in.model_dump(),
            user_id=user_id,
            status=EventStatus.PLANNED,
        )
        session.add(event)
        await session.flush()

        await event_bus.emit(
            session,
            "event.created",
            payload={
                "event_id": str(event.id),
                "user_id": str(user_id),
                "event_type_id": str(event.event_type_id),
                "name": event.name,
                "start_date": event.start_date.isoformat(),
                "status": event.status,
            },
            user_id=user_id,
        )

        await session.commit()
        await session.refresh(event)
        logger.info("event.created", event_id=str(event.id), user_id=str(user_id))
        return event

    async def get_event(
        self,
        session: AsyncSession,
        event_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Event:
        return await self._get_event_or_404(session, event_id, user_id)

    async def list_events(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        status_filter: Optional[EventStatus] = None,
    ) -> Tuple[List[Event], int]:
        offset = (page - 1) * limit
        base = select(Event).where(Event.user_id == user_id)
        count_base = select(func.count()).select_from(Event).where(Event.user_id == user_id)

        if status_filter:
            base = base.where(Event.status == status_filter)
            count_base = count_base.where(Event.status == status_filter)

        total = (await session.execute(count_base)).scalar() or 0
        events = list((await session.execute(
            base.order_by(Event.created_at.desc()).offset(offset).limit(limit)
        )).scalars().all())
        return events, total

    async def update_event(
        self,
        session: AsyncSession,
        event_id: uuid.UUID,
        event_in: EventUpdate,
        user_id: uuid.UUID,
    ) -> Event:
        event = await self._get_event_or_404(session, event_id, user_id)

        if event.status in TERMINAL_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_err(
                    "VALIDATION_INVALID_STATUS_TRANSITION",
                    f"Cannot update event with terminal status '{event.status}'.",
                ),
            )

        update_data = event_in.model_dump(exclude_unset=True)

        # Validate end_date against existing start_date when only end_date provided
        if "end_date" in update_data and "start_date" not in update_data:
            end = update_data["end_date"]
            if end is not None:
                start = event.start_date
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                if end <= start:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=_err("VALIDATION_END_DATE_BEFORE_START", "end_date must be after start_date"),
                    )

        for field, value in update_data.items():
            setattr(event, field, value)
        event.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(event)
        logger.info("event.updated", event_id=str(event_id), user_id=str(user_id))
        return event

    # ── Status transitions ────────────────────────────────────────────────────

    async def transition_status(
        self,
        session: AsyncSession,
        event: Event,
        new_status: EventStatus,
        user_id: uuid.UUID,
        reason: Optional[str] = None,
    ) -> Event:
        current = EventStatus(event.status)

        if current in TERMINAL_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_err(
                    "VALIDATION_INVALID_STATUS_TRANSITION",
                    f"Cannot transition from terminal status '{current}'.",
                ),
            )

        allowed = VALID_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_err(
                    "VALIDATION_INVALID_STATUS_TRANSITION",
                    f"Cannot transition from '{current}' to '{new_status}'.",
                ),
            )

        old_status = event.status
        event.status = new_status
        event.updated_at = datetime.now(timezone.utc)

        if new_status == EventStatus.CANCELED:
            event.canceled_at = datetime.now(timezone.utc)
            event.cancellation_reason = reason

        await event_bus.emit(
            session,
            "event.status_changed",
            payload={
                "event_id": str(event.id),
                "user_id": str(user_id),
                "old_status": old_status,
                "new_status": new_status,
            },
            user_id=user_id,
        )

        await session.commit()
        await session.refresh(event)
        logger.info("event.status_changed", event_id=str(event.id), old=old_status, new=new_status)
        return event

    async def cancel_event(
        self,
        session: AsyncSession,
        event_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: Optional[str] = None,
    ) -> Event:
        event = await self._get_event_or_404(session, event_id, user_id)
        event = await self.transition_status(session, event, EventStatus.CANCELED, user_id, reason)

        # Emit dedicated cancelled event
        await event_bus.emit(
            session,
            "event.cancelled",
            payload={
                "event_id": str(event.id),
                "user_id": str(user_id),
                "reason": reason,
                "canceled_at": event.canceled_at.isoformat() if event.canceled_at else None,
            },
            user_id=user_id,
        )
        await session.commit()
        logger.info("event.cancelled", event_id=str(event_id), user_id=str(user_id))
        return event

    # ── Duplicate ─────────────────────────────────────────────────────────────

    async def duplicate_event(
        self,
        session: AsyncSession,
        event_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Event:
        source = await self._get_event_or_404(session, event_id, user_id)
        await self._enforce_free_plan_event_limit(session, user_id)

        new_event = Event(
            user_id=user_id,
            event_type_id=source.event_type_id,
            name=f"Copy of {source.name}",
            description=source.description,
            start_date=source.start_date,
            end_date=source.end_date,
            timezone=source.timezone,
            venue_name=source.venue_name,
            address=source.address,
            city=source.city,
            country=source.country,
            guest_count=source.guest_count,
            budget=source.budget,
            special_requirements=source.special_requirements,
            status=EventStatus.DRAFT,
        )
        session.add(new_event)
        await session.flush()

        await event_bus.emit(
            session,
            "event.created",
            payload={
                "event_id": str(new_event.id),
                "user_id": str(user_id),
                "event_type_id": str(new_event.event_type_id),
                "name": new_event.name,
                "start_date": new_event.start_date.isoformat(),
                "status": new_event.status,
            },
            user_id=user_id,
        )

        await session.commit()
        await session.refresh(new_event)
        logger.info("event.duplicated", source_id=str(event_id), new_id=str(new_event.id))
        return new_event

    # ── Bookings for event ────────────────────────────────────────────────────

    async def list_event_bookings(
        self,
        session: AsyncSession,
        event_id: uuid.UUID,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        status_filter: Optional[BookingStatus] = None,
    ) -> Tuple[List[Booking], int]:
        # Verify ownership
        await self._get_event_or_404(session, event_id, user_id)

        offset = (page - 1) * limit
        base = select(Booking).where(Booking.event_id == event_id)
        count_base = select(func.count()).select_from(Booking).where(Booking.event_id == event_id)

        if status_filter:
            base = base.where(Booking.status == status_filter)
            count_base = count_base.where(Booking.status == status_filter)

        total = (await session.execute(count_base)).scalar() or 0
        bookings = list((await session.execute(
            base.order_by(Booking.created_at.desc()).offset(offset).limit(limit)
        )).scalars().all())
        return bookings, total

    # ── Admin ─────────────────────────────────────────────────────────────────

    async def list_all_events_admin(
        self,
        session: AsyncSession,
        page: int = 1,
        limit: int = 20,
        status: Optional[EventStatus] = None,
        user_id: Optional[uuid.UUID] = None,
        city: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[List[Event], int]:
        offset = (page - 1) * limit
        base = select(Event)
        count_base = select(func.count()).select_from(Event)

        filters = []
        if status:
            filters.append(Event.status == status)
        if user_id:
            filters.append(Event.user_id == user_id)
        if city:
            filters.append(Event.city.ilike(f"%{city}%"))
        if date_from:
            filters.append(Event.start_date >= date_from)
        if date_to:
            filters.append(Event.start_date <= date_to)

        for f in filters:
            base = base.where(f)
            count_base = count_base.where(f)

        total = (await session.execute(count_base)).scalar() or 0
        events = list((await session.execute(
            base.order_by(Event.created_at.desc()).offset(offset).limit(limit)
        )).scalars().all())
        return events, total


event_service = EventService()
