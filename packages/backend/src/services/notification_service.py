"""
Notification Service (010) — subscribes to booking domain events,
writes Notification rows atomically in the same DB session, and pushes
to SSE via ConnectionManager.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from src.models.notification import Notification, NotificationType, NotificationRead
from src.models.booking import Booking
from src.models.vendor import Vendor
from src.models.user import User
import structlog

logger = structlog.get_logger()

# Deduplication window (5 minutes)
_DEDUP_WINDOW_MINUTES = 5

# domain event type → (NotificationType, title, body_template)
_EVENT_MAP: Dict[str, Tuple[NotificationType, str, str]] = {
    "booking.created":        (NotificationType.booking_created,        "Booking Request Received", "Your booking for {event_name} on {event_date} is pending confirmation."),
    "booking.confirmed":      (NotificationType.booking_confirmed,      "Booking Confirmed ✓",      "Your booking on {event_date} has been confirmed."),
    "booking.cancelled":      (NotificationType.booking_cancelled,      "Booking Cancelled",         "Your booking on {event_date} has been cancelled."),
    "booking.completed":      (NotificationType.booking_completed,      "Booking Completed",         "Your event on {event_date} is complete. Leave a review!"),
    "booking.rejected":       (NotificationType.booking_rejected,       "Booking Rejected",          "Your booking request was declined."),
    "booking.status_changed":   (NotificationType.booking_status_changed,   "Booking Updated",           "Your booking status changed to {new_status}."),
    "booking.counter_offered":  (NotificationType.booking_counter_offered,  "Customer Counter-Offer",    "Customer proposed a new price on your quote."),
    "booking.quoted":           (NotificationType.booking_quoted,           "New Quote Received",         "A vendor has sent you a quote for your event on {event_date}."),
    "booking.accepted":         (NotificationType.booking_accepted,         "Quote Accepted",             "Your quote has been accepted."),
    "booking.counter_rejected": (NotificationType.booking_counter_rejected, "Counter-Offer Declined",     "Your counter-offer was declined. The original quote is still available."),
    # Event domain events
    "event.created":          (NotificationType.event_created,          "Event Created",             "Your event '{event_name}' has been created."),
    "event.status_changed":   (NotificationType.event_status_changed,   "Event Status Updated",      "Your event '{event_name}' status changed to {new_status}."),
    "event.cancelled":        (NotificationType.event_cancelled,        "Event Cancelled",           "Your event '{event_name}' has been cancelled."),
    # Vendor domain events
    "vendor.approved":        (NotificationType.vendor_approved,        "Vendor Account Approved",   "Your vendor account has been approved. You can now accept bookings."),
    "vendor.rejected":        (NotificationType.vendor_rejected,        "Vendor Account Rejected",   "Your vendor account application was not approved."),
    "vendor.suspended":       (NotificationType.vendor_suspended,       "Account Suspended",         "Your vendor account has been suspended."),
    # Subscription events
    "subscription.granted":   (NotificationType.subscription_granted,   "Pro Subscription Activated", "Your Pro subscription is now active."),
    "subscription.revoked":   (NotificationType.subscription_revoked,   "Pro Subscription Ended",     "Your Pro subscription has been revoked."),
    # Inquiry events
    "inquiry.created":        (NotificationType.inquiry_created,        "New Customer Inquiry",       "You have a new customer inquiry."),
}

# Event types that resolve user_id directly from payload (not via ORM lookup)
_PAYLOAD_USER_ID_EVENTS = {
    "event.created", "event.status_changed", "event.cancelled",
    "subscription.granted", "subscription.revoked",
}

# Event types that resolve vendor.user_id via ORM lookup on vendor_id in payload
_VENDOR_ID_EVENTS = {
    "vendor.approved", "vendor.rejected", "vendor.suspended", "inquiry.created",
}


class NotificationService:

    async def handle(
        self,
        event_type: str,
        payload: Dict[str, Any],
        user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None,
    ) -> None:
        """Event bus listener — called within the booking/event/vendor transaction."""
        if session is None or event_type not in _EVENT_MAP:
            return

        notif_type, title, body_template = _EVENT_MAP[event_type]

        # Check per-user preference before creating any notification
        # (preference check is done after resolving recipient_id below for booking events)

        # For event.* and vendor.* events, resolve user_id directly from payload
        if event_type in _PAYLOAD_USER_ID_EVENTS:
            raw_uid = payload.get("user_id") or payload.get("vendor_user_id")
            if not raw_uid:
                logger.warning(
                    "notification.handle.missing_user_id",
                    event_type=event_type,
                    payload_keys=list(payload.keys()),
                )
                return
            try:
                recipient_id = uuid.UUID(str(raw_uid))
            except (ValueError, AttributeError):
                logger.warning("notification.handle.invalid_user_id", event_type=event_type, raw=raw_uid)
                return

            body = body_template.format(
                event_name=payload.get("name") or payload.get("event_name") or "your event",
                new_status=payload.get("new_status", ""),
            )

            if not await self._is_enabled_for_user(session, recipient_id, notif_type):
                return

            # Deduplication check for event/vendor events
            event_id = payload.get("event_id") or payload.get("vendor_id")
            if await self._is_duplicate(session, recipient_id, event_type, event_id):
                return

            notif = Notification(
                user_id=recipient_id,
                type=notif_type,
                title=title,
                body=body,
                data=payload,
            )
            session.add(notif)
            await session.flush()
            await self._push_sse(recipient_id, notif)
            await self._send_email(session, recipient_id, title, body, event_type)
            return

        # Vendor/inquiry events — resolve vendor.user_id via ORM lookup on vendor_id
        if event_type in _VENDOR_ID_EVENTS:
            vendor_id_str = payload.get("vendor_id")
            if not vendor_id_str:
                logger.warning("notification.handle.missing_vendor_id", event_type=event_type)
                return
            try:
                vendor_id = uuid.UUID(str(vendor_id_str))
            except (ValueError, AttributeError):
                logger.warning("notification.handle.invalid_vendor_id", event_type=event_type, raw=vendor_id_str)
                return
            vendor_obj: Optional[Vendor] = await session.get(Vendor, vendor_id)
            if not vendor_obj or not vendor_obj.user_id:
                return
            recipient_id = vendor_obj.user_id

            if not await self._is_enabled_for_user(session, recipient_id, notif_type):
                return

            dedup_id = payload.get("inquiry_id") or vendor_id_str
            if await self._is_duplicate(session, recipient_id, event_type, dedup_id):
                return

            notif = Notification(
                user_id=recipient_id,
                type=notif_type,
                title=title,
                body=body_template,  # no format vars for vendor/inquiry events
                data=payload,
            )
            session.add(notif)
            await session.flush()
            await self._push_sse(recipient_id, notif)
            await self._send_email(session, recipient_id, title, body_template, event_type)
            return

        # Booking events — resolve via ORM lookup
        booking: Optional[Booking] = None
        booking_id_str = payload.get("booking_id")
        if booking_id_str:
            try:
                booking = await session.get(Booking, uuid.UUID(booking_id_str))
            except Exception:
                pass

        body = body_template.format(
            event_name=getattr(booking, "event_name", None) or "your event",
            event_date=str(getattr(booking, "event_date", "")),
            new_status=payload.get("new_status", ""),
        )

        recipient_id = (booking.user_id if booking and booking.user_id else user_id)
        if recipient_id is None:
            logger.warning("notification.handle.missing_user_id", event_type=event_type)
            return

        if not await self._is_enabled_for_user(session, recipient_id, notif_type):
            return

        # Deduplication check
        event_id = payload.get("booking_id") or payload.get("event_id")
        if await self._is_duplicate(session, recipient_id, event_type, event_id):
            return

        # booking.counter_offered — notify VENDOR only (customer submitted it, no self-notification).
        # Must come before the standard session.add below so we don't double-notify.
        if event_type == "booking.counter_offered":
            if booking and booking.vendor_id:
                vendor: Optional[Vendor] = await session.get(Vendor, booking.vendor_id)
                if vendor and vendor.user_id:
                    if not await self._is_enabled_for_user(session, vendor.user_id, notif_type):
                        return
                    dedup_id = payload.get("booking_id") or payload.get("quote_id")
                    if await self._is_duplicate(session, vendor.user_id, event_type, dedup_id):
                        return
                    proposed = payload.get("proposed_total", 0)
                    vendor_body = (
                        f"Customer proposed PKR {proposed:,.0f} on your quote "
                        f"for {getattr(booking, 'event_name', None) or 'their event'}."
                    )
                    vendor_notif = Notification(
                        user_id=vendor.user_id,
                        type=notif_type,
                        title=title,
                        body=vendor_body,
                        data=payload,
                    )
                    session.add(vendor_notif)
                    await session.flush()
                    await self._push_sse(vendor.user_id, vendor_notif)
                    await self._send_email(
                        session, vendor.user_id, title, vendor_body, event_type, booking
                    )
            return  # skip standard customer notification for counter_offered

        # booking.accepted — route based on actor: customer accepts → notify vendor; vendor accepts → notify customer
        if event_type == "booking.accepted" and payload.get("actor") == "customer":
            if booking and booking.vendor_id:
                vendor: Optional[Vendor] = await session.get(Vendor, booking.vendor_id)
                if vendor and vendor.user_id:
                    if not await self._is_enabled_for_user(session, vendor.user_id, notif_type):
                        return
                    dedup_id = payload.get("booking_id") or payload.get("quote_id")
                    if await self._is_duplicate(session, vendor.user_id, event_type, dedup_id):
                        return
                    accepted_body = (
                        f"Customer accepted your quote for "
                        f"{getattr(booking, 'event_name', None) or 'their event'} "
                        f"on {getattr(booking, 'event_date', '')}."
                    )
                    vendor_notif = Notification(
                        user_id=vendor.user_id,
                        type=notif_type,
                        title=title,
                        body=accepted_body,
                        data=payload,
                    )
                    session.add(vendor_notif)
                    await session.flush()
                    await self._push_sse(vendor.user_id, vendor_notif)
                    await self._send_email(session, vendor.user_id, title, accepted_body, event_type, booking)
            return  # skip standard customer notification when customer is the actor

        notif = Notification(
            user_id=recipient_id,
            type=notif_type,
            title=title,
            body=body,
            data=payload,
        )
        session.add(notif)
        await session.flush()
        await self._push_sse(recipient_id, notif)
        await self._send_email(session, recipient_id, title, body, event_type, booking)

        # Vendor notification for booking.created (7.3 - already implemented)
        if event_type == "booking.created" and booking and booking.vendor_id:
            vendor: Optional[Vendor] = await session.get(Vendor, booking.vendor_id)
            if vendor and vendor.user_id:
                # Check vendor preference
                if not await self._is_enabled_for_user(session, vendor.user_id, NotificationType.booking_created):
                    return

                # Deduplication for vendor
                if await self._is_duplicate(session, vendor.user_id, event_type, event_id):
                    return

                vendor_body = f"You have a new booking request for {getattr(booking, 'event_name', None) or 'your event'} on {getattr(booking, 'event_date', '')}."
                vendor_notif = Notification(
                    user_id=vendor.user_id,
                    type=NotificationType.booking_created,
                    title="New Booking Request",
                    body=vendor_body,
                    data=payload,
                )
                session.add(vendor_notif)
                await session.flush()
                await self._push_sse(vendor.user_id, vendor_notif)
                await self._send_email(
                    session, vendor.user_id, "New Booking Request", vendor_body,
                    "new_booking_request", booking
                )

    async def _is_enabled_for_user(
        self, session: AsyncSession, user_id: uuid.UUID, notif_type: NotificationType
    ) -> bool:
        """Check preference — defaults to True (opt-in) if no row exists."""
        try:
            from src.services.preference_service import preference_service
            return await preference_service.is_enabled(session, user_id, notif_type)
        except Exception:
            return True  # fail open

    async def _push_sse(self, recipient_id: uuid.UUID, notif: Notification) -> None:
        """Push notification to open SSE connections."""
        try:
            from src.main import app
            cm = getattr(app.state, "connection_manager", None)
            if cm is not None:
                await cm.push(
                    recipient_id,
                    "notification",
                    NotificationRead.model_validate(notif).model_dump(mode="json"),
                )
        except Exception as e:
            logger.warning("sse.push_failed", error=str(e))

    async def _send_email(
        self,
        session: AsyncSession,
        recipient_id: uuid.UUID,
        title: str,
        body: str,
        event_type: str,
        booking: Optional[Booking] = None,
    ) -> None:
        """Send email notification to user (fire-and-forget)."""
        try:
            # Fetch user email
            user = await session.get(User, recipient_id)
            if not user or not user.email:
                logger.warning("email.no_recipient", recipient_id=str(recipient_id))
                return

            from src.services.email_service import email_service

            vendor_name = ""
            event_date = ""
            event_name = ""

            if booking:
                vendor_name = getattr(booking, "vendor_name", "") or ""
                event_date = str(getattr(booking, "event_date", ""))
                event_name = getattr(booking, "event_name", "") or "your event"
                # Fetch vendor name if not on booking
                if not vendor_name and booking.vendor_id:
                    vendor = await session.get(Vendor, booking.vendor_id)
                    if vendor:
                        vendor_name = vendor.business_name

            subject, html_body = email_service.render_booking_email(
                event_type=event_type,
                vendor_name=vendor_name or "Event-AI Vendor",
                event_date=event_date,
                event_name=event_name,
            )

            await email_service.send_email(
                to=user.email,
                subject=subject,
                body_html=html_body,
                body_text=body,
            )
            logger.info("email.queued", recipient_id=str(recipient_id), title=subject)
        except Exception as e:
            logger.warning("email.send_error", recipient_id=str(recipient_id), error=str(e))

    async def _is_duplicate(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        event_type: str,
        event_id: Optional[str] = None,
    ) -> bool:
        """Check for duplicate notification within 5-minute window."""
        if not event_id:
            return False

        window_start = datetime.now(timezone.utc) - timedelta(minutes=_DEDUP_WINDOW_MINUTES)

        # Check by data->booking_id or data->event_id
        result = await session.execute(
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.type == NotificationType[event_type.replace(".", "_")],
                Notification.created_at >= window_start,
            )
            .limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing and existing.data:
            # Check if same event_id in data
            existing_event_id = existing.data.get("booking_id") or existing.data.get("event_id")
            if existing_event_id == event_id:
                logger.info(
                    "notification.deduplicated",
                    user_id=str(user_id),
                    event_type=event_type,
                    event_id=event_id,
                )
                return True

        return False

    # ── REST helpers ──────────────────────────────────────────────────────────

    async def list_notifications(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        unread_only: bool = False,
    ) -> Tuple[List[Notification], int]:
        offset = (page - 1) * limit
        base = select(Notification).where(Notification.user_id == user_id)
        count_q = select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
        if unread_only:
            base = base.where(Notification.is_read == False)       # noqa: E712
            count_q = count_q.where(Notification.is_read == False) # noqa: E712
        total = (await session.execute(count_q)).scalar() or 0
        rows = (
            await session.execute(
                base.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
            )
        ).scalars().all()
        return list(rows), total

    async def unread_count(self, session: AsyncSession, user_id: uuid.UUID) -> int:
        result = await session.execute(
            select(func.count()).select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False) # noqa: E712
        )
        return result.scalar() or 0

    async def mark_read(
        self, session: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Notification:
        notif = await session.get(Notification, notification_id)
        if not notif:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "NOT_FOUND", "message": "Notification not found."})
        if notif.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "AUTH_FORBIDDEN", "message": "Not your notification."})
        if not notif.is_read:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(notif)
        return notif

    async def mark_all_read(self, session: AsyncSession, user_id: uuid.UUID) -> int:
        result = await session.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False) # noqa: E712
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        await session.commit()
        return result.rowcount


notification_service = NotificationService()
