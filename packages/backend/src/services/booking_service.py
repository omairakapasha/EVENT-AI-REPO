"""
Booking Service — business logic, status transitions, availability locking,
pricing lookup, and domain event emission.
"""
import uuid
from datetime import datetime, timedelta, timezone, date as date_type
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from fastapi import HTTPException, status

from src.models.booking import Booking, BookingStatus, BookingCreate, BookingMessage, BookingMessageCreate
from src.models.vendor import Vendor
from src.models.service import Service
from src.models.availability import VendorAvailability, AvailabilityStatus
from src.services.event_bus_service import event_bus
import structlog
from sqlalchemy.exc import IntegrityError, InvalidRequestError
try:
    import asyncpg.exceptions as asyncpg_exc
except ImportError:
    asyncpg_exc = None  # SQLite test environment — FOR UPDATE not supported

logger = structlog.get_logger()

# Valid state machine transitions
VALID_TRANSITIONS = {
    BookingStatus.pending: {BookingStatus.confirmed, BookingStatus.rejected, BookingStatus.cancelled},
    BookingStatus.confirmed: {BookingStatus.in_progress, BookingStatus.cancelled},
    BookingStatus.in_progress: {BookingStatus.completed, BookingStatus.no_show},
}

TERMINAL_STATUSES = {BookingStatus.completed, BookingStatus.cancelled, BookingStatus.rejected, BookingStatus.no_show}

LOCK_TTL_SECONDS = 30


def _err(code: str, message: str) -> dict:
    return {"code": code, "message": message}


class BookingService:

    # ── Availability ──────────────────────────────────────────────────────────

    async def check_availability(
        self,
        session: AsyncSession,
        vendor_id: uuid.UUID,
        service_id: uuid.UUID,
        check_date: date_type,
    ) -> dict:
        """Return availability status for a vendor+service+date."""
        row = await self._get_availability_row(session, vendor_id, service_id, check_date)
        if row is None:
            return {"available": True}

        if row.status == AvailabilityStatus.BOOKED:
            return {"available": False, "reason": "Date already booked"}
        if row.status == AvailabilityStatus.BLOCKED:
            return {"available": False, "reason": "Vendor not available on this date"}
        if row.status == AvailabilityStatus.LOCKED:
            if row.locked_until and row.locked_until > datetime.now(timezone.utc):
                return {"available": False, "reason": "Date is temporarily held"}
            # Expired lock — treat as available
        return {"available": True}

    async def _get_availability_row(
        self,
        session: AsyncSession,
        vendor_id: uuid.UUID,
        service_id: uuid.UUID,
        check_date: date_type,
    ) -> Optional[VendorAvailability]:
        stmt = select(VendorAvailability).where(
            VendorAvailability.vendor_id == vendor_id,
            VendorAvailability.service_id == service_id,
            VendorAvailability.date == check_date,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_availability_row_for_update(
        self,
        session: AsyncSession,
        vendor_id: uuid.UUID,
        service_id: uuid.UUID,
        check_date: date_type,
    ) -> Optional[VendorAvailability]:
        stmt = (
            select(VendorAvailability)
            .where(
                VendorAvailability.vendor_id == vendor_id,
                VendorAvailability.service_id == service_id,
                VendorAvailability.date == check_date,
            )
            .with_for_update(nowait=True)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _acquire_lock(
        self,
        session: AsyncSession,
        vendor_id: uuid.UUID,
        service_id: uuid.UUID,
        check_date: date_type,
        user_id: uuid.UUID,
    ) -> VendorAvailability:
        """Acquire availability lock. Raises 409 if already booked/locked."""
        now = datetime.now(timezone.utc)
        try:
            row = await self._get_availability_row_for_update(
                session, vendor_id, service_id, check_date
            )
        except Exception as exc:
            if asyncpg_exc and isinstance(exc.__cause__, asyncpg_exc.LockNotAvailableError):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=_err("CONFLICT_DATE_BEING_PROCESSED",
                                "This date is temporarily held by another request."),
                )
            raise

        if row is not None:
            if row.status == AvailabilityStatus.BOOKED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=_err("CONFLICT_DATE_UNAVAILABLE", "This date is already booked."),
                )
            if row.status == AvailabilityStatus.BLOCKED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=_err("CONFLICT_DATE_UNAVAILABLE", "Vendor is not available on this date."),
                )
            if row.status == AvailabilityStatus.LOCKED and row.locked_until and row.locked_until > now:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=_err("CONFLICT_DATE_BEING_PROCESSED", "This date is temporarily held by another request."),
                )
            # Expired lock or available — update existing row
            row.status = AvailabilityStatus.LOCKED
            row.locked_by = user_id
            row.locked_until = now + timedelta(seconds=LOCK_TTL_SECONDS)
            row.locked_reason = "booking_in_progress"
            row.updated_at = now
        else:
            row = VendorAvailability(
                vendor_id=vendor_id,
                service_id=service_id,
                date=check_date,
                status=AvailabilityStatus.LOCKED,
                locked_by=user_id,
                locked_until=now + timedelta(seconds=LOCK_TTL_SECONDS),
                locked_reason="booking_in_progress",
            )
            session.add(row)
            try:
                await session.flush()
            except (IntegrityError, InvalidRequestError):
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=_err("CONFLICT_DATE_BEING_PROCESSED",
                                "This date is temporarily held by another request."),
                )
            return row

        await session.flush()
        return row

    async def _confirm_lock(
        self,
        session: AsyncSession,
        availability_row: VendorAvailability,
        booking_id: uuid.UUID,
    ) -> None:
        """Confirm lock → booked after successful booking creation."""
        availability_row.status = AvailabilityStatus.BOOKED
        availability_row.locked_by = None
        availability_row.locked_until = None
        availability_row.locked_reason = None
        availability_row.booking_id = booking_id
        availability_row.updated_at = datetime.now(timezone.utc)

    async def _release_slot(
        self,
        session: AsyncSession,
        vendor_id: uuid.UUID,
        service_id: Optional[uuid.UUID],
        check_date: date_type,
    ) -> None:
        """Release a booked/locked slot back to available."""
        stmt = (
            update(VendorAvailability)
            .where(
                VendorAvailability.vendor_id == vendor_id,
                VendorAvailability.date == check_date,
            )
            .values(
                status=AvailabilityStatus.AVAILABLE,
                locked_by=None,
                locked_until=None,
                locked_reason=None,
                booking_id=None,
                updated_at=datetime.now(timezone.utc),
            )
        )
        if service_id:
            stmt = stmt.where(VendorAvailability.service_id == service_id)
        await session.execute(stmt)

    # ── Booking CRUD ──────────────────────────────────────────────────────────

    async def create_booking(
        self,
        session: AsyncSession,
        booking_in: BookingCreate,
        user_id: uuid.UUID,
    ) -> Booking:
        """Create booking: validate → lock → price → insert → confirm lock → emit event."""
        # Validate future date
        if booking_in.event_date <= date_type.today():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_err("VALIDATION_PAST_DATE", "event_date must be in the future."),
            )

        # Validate vendor
        vendor = await session.get(Vendor, booking_in.vendor_id)
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_err("NOT_FOUND_VENDOR", "Vendor not found."),
            )

        # Validate service + pricing
        service = await session.get(Service, booking_in.service_id)
        if not service or not service.is_active or service.vendor_id != booking_in.vendor_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_err("VALIDATION_SERVICE_NOT_FOUND", "Service not found or inactive."),
            )

        # Acquire availability lock
        avail_row = await self._acquire_lock(
            session, booking_in.vendor_id, booking_in.service_id, booking_in.event_date, user_id
        )

        # Determine pricing
        unit_price = booking_in.unit_price if booking_in.unit_price else (service.price_min or 0.0)
        quantity = booking_in.quantity or 1
        total_price = unit_price * quantity

        # Create booking
        booking_data = booking_in.model_dump(exclude={"unit_price", "total_price"})
        db_booking = Booking(
            **booking_data,
            user_id=user_id,
            status=BookingStatus.pending,
            unit_price=unit_price,
            total_price=total_price,
        )
        session.add(db_booking)
        await session.flush()

        # Confirm lock
        await self._confirm_lock(session, avail_row, db_booking.id)

        # Emit domain event
        await event_bus.emit(
            session,
            "booking.created",
            payload={"booking_id": str(db_booking.id), "vendor_id": str(booking_in.vendor_id), "user_id": str(user_id)},
            user_id=user_id,
        )

        await session.commit()
        await session.refresh(db_booking)
        logger.info("booking.created", booking_id=str(db_booking.id), user_id=str(user_id))
        return db_booking

    async def get_by_id(self, session: AsyncSession, booking_id: uuid.UUID) -> Optional[Booking]:
        return await session.get(Booking, booking_id)

    async def list_bookings(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        status_filter: Optional[BookingStatus] = None,
    ) -> Tuple[List[Booking], int]:
        offset = (page - 1) * limit
        base = select(Booking).where(Booking.user_id == user_id)
        count_base = select(func.count()).select_from(Booking).where(Booking.user_id == user_id)

        if status_filter:
            base = base.where(Booking.status == status_filter)
            count_base = count_base.where(Booking.status == status_filter)

        total_result = await session.execute(count_base)
        total = total_result.scalar() or 0

        result = await session.execute(base.order_by(Booking.created_at.desc()).offset(offset).limit(limit))
        bookings = list(result.scalars().all())
        return bookings, total

    # ── Status transitions ────────────────────────────────────────────────────

    async def update_status(
        self,
        session: AsyncSession,
        booking_id: uuid.UUID,
        new_status: BookingStatus,
        user_id: uuid.UUID,
        reason: Optional[str] = None,
    ) -> Booking:
        booking = await session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_err("NOT_FOUND_BOOKING", "Booking not found."),
            )

        current = booking.status
        if current in TERMINAL_STATUSES:
            if current == BookingStatus.cancelled:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=_err("CONFLICT_ALREADY_CANCELLED", "Booking is already cancelled."),
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_err("VALIDATION_INVALID_TRANSITION", f"Cannot transition from terminal status '{current}'."),
            )

        if current == new_status and new_status == BookingStatus.confirmed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_err("CONFLICT_ALREADY_CONFIRMED", "Booking is already confirmed."),
            )

        allowed = VALID_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_err("VALIDATION_INVALID_TRANSITION", f"Cannot transition from '{current}' to '{new_status}'."),
            )

        old_status = booking.status
        booking.status = new_status
        booking.updated_at = datetime.now(timezone.utc)

        if new_status == BookingStatus.confirmed:
            booking.confirmed_at = datetime.now(timezone.utc)
            booking.confirmed_by = user_id
            event_type = "booking.confirmed"
            payload = {"booking_id": str(booking_id), "confirmed_by": str(user_id)}
        elif new_status == BookingStatus.rejected:
            booking.cancelled_at = datetime.now(timezone.utc)
            booking.cancelled_by = user_id
            booking.cancellation_reason = reason
            # Release availability slot
            await self._release_slot(session, booking.vendor_id, booking.service_id, booking.event_date)
            event_type = "booking.cancelled"
            payload = {"booking_id": str(booking_id), "reason": reason or "rejected"}
        elif new_status == BookingStatus.completed:
            event_type = "booking.completed"
            payload = {"booking_id": str(booking_id)}
        else:
            event_type = "booking.status_changed"
            payload = {"booking_id": str(booking_id), "old_status": old_status, "new_status": new_status}

        await event_bus.emit(session, event_type, payload=payload, user_id=user_id)
        await session.commit()
        await session.refresh(booking)
        logger.info("booking.status_updated", booking_id=str(booking_id), old=old_status, new=new_status)
        return booking

    async def cancel_booking(
        self,
        session: AsyncSession,
        booking_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: Optional[str] = None,
    ) -> Booking:
        booking = await session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_err("NOT_FOUND_BOOKING", "Booking not found."),
            )

        if booking.status == BookingStatus.cancelled:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_err("CONFLICT_ALREADY_CANCELLED", "Booking is already cancelled."),
            )
        if booking.status == BookingStatus.completed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_err("CONFLICT_COMPLETED_BOOKINGS_CANNOT_CANCEL", "Cannot cancel a completed booking."),
            )
        if booking.status not in {BookingStatus.pending, BookingStatus.confirmed}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_err("CONFLICT_ALREADY_CANCELLED", f"Cannot cancel booking with status '{booking.status}'."),
            )

        booking.status = BookingStatus.cancelled
        booking.cancelled_at = datetime.now(timezone.utc)
        booking.cancelled_by = user_id
        booking.cancellation_reason = reason
        booking.updated_at = datetime.now(timezone.utc)

        # Release availability slot
        await self._release_slot(session, booking.vendor_id, booking.service_id, booking.event_date)

        await event_bus.emit(
            session,
            "booking.cancelled",
            payload={"booking_id": str(booking_id), "cancelled_by": str(user_id), "reason": reason},
            user_id=user_id,
        )

        await session.commit()
        await session.refresh(booking)
        logger.info("booking.cancelled", booking_id=str(booking_id), user_id=str(user_id))
        return booking

    # ── Messages ──────────────────────────────────────────────────────────────

    async def _check_booking_access(
        self, session: AsyncSession, booking: Booking, user_id: uuid.UUID
    ) -> None:
        """Raise 403 if user is neither the booking owner nor the vendor owner."""
        if booking.user_id == user_id:
            return
        # Check if user owns the vendor
        from src.models.vendor import Vendor
        vendor = await session.get(Vendor, booking.vendor_id)
        if vendor and vendor.user_id == user_id:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_err("AUTH_FORBIDDEN", "You do not have permission to access this booking."),
        )

    async def add_message(
        self,
        session: AsyncSession,
        booking_id: uuid.UUID,
        message_in: BookingMessageCreate,
        user_id: uuid.UUID,
    ) -> BookingMessage:
        booking = await session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_err("NOT_FOUND_BOOKING", "Booking not found."),
            )
        await self._check_booking_access(session, booking, user_id)

        msg = BookingMessage(
            **message_in.model_dump(),
            booking_id=booking_id,
            sender_id=user_id,
        )
        session.add(msg)
        await session.commit()
        await session.refresh(msg)
        return msg

    async def list_messages(
        self,
        session: AsyncSession,
        booking_id: uuid.UUID,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[BookingMessage], int]:
        booking = await session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_err("NOT_FOUND_BOOKING", "Booking not found."),
            )
        await self._check_booking_access(session, booking, user_id)

        offset = (page - 1) * limit
        count_result = await session.execute(
            select(func.count()).select_from(BookingMessage).where(BookingMessage.booking_id == booking_id)
        )
        total = count_result.scalar() or 0

        result = await session.execute(
            select(BookingMessage)
            .where(BookingMessage.booking_id == booking_id)
            .order_by(BookingMessage.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total


booking_service = BookingService()
