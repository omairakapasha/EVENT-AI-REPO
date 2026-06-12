"""
Booking tools — direct SQLAlchemy DB access via RunContext[AgentContext].

All four tools receive ctx: RunContext[AgentContext] as their first parameter.
They use ctx.context.db for all reads/writes and ctx.context.user_id for
ownership scoping.  No httpx calls.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from agents import function_tool
from agents.run_context import RunContextWrapper

from services.agent_context import AgentContext

logger = logging.getLogger(__name__)

# Terminal booking states — cannot be transitioned out of
_TERMINAL_STATES = {"completed", "cancelled", "rejected", "no_show"}


def _err(msg: str) -> str:
    return json.dumps({"success": False, "error": msg})


@function_tool
async def create_booking_request(
    ctx: RunContextWrapper[AgentContext],
    vendor_id: str,
    service_id: str,
    event_date: str,
    event_name: str,
    guest_count: int,
    notes: str = "",
    quantity: int = 1,
) -> str:
    """Create a booking inquiry request for a vendor service.
    IMPORTANT: Only call this AFTER showing the user a summary and receiving explicit confirmation.
    Returns a JSON string with booking_id and status."""
    try:
        from sqlalchemy import text as sa_text
        db = ctx.context.db
        user_id = ctx.context.user_id

        # Look up service price_min for unit_price
        svc_result = await db.execute(
            sa_text(
                "SELECT id, price_min, price_max, name FROM services "
                "WHERE id = :service_id AND is_active = true LIMIT 1"
            ),
            {"service_id": service_id},
        )
        svc_row = svc_result.fetchone()
        if not svc_row:
            return _err(f"Service {service_id} not found or is not active.")

        # Guard against double-booking: reject if an active booking already exists
        # for the same vendor+service on the same date
        conflict_result = await db.execute(
            sa_text(
                "SELECT id FROM bookings "
                "WHERE vendor_id = :vendor_id AND service_id = :service_id "
                "AND event_date = :event_date "
                "AND status NOT IN ('cancelled', 'rejected') "
                "LIMIT 1"
            ),
            {"vendor_id": vendor_id, "service_id": service_id, "event_date": event_date},
        )
        if conflict_result.fetchone():
            return _err(
                f"This vendor service is already booked for {event_date}. "
                "Please choose a different date."
            )

        # Check the availability slot — mirrors booking_service._acquire_lock so the
        # chat flow honours the same booked/locked states as the REST flow
        now = datetime.now(timezone.utc)
        avail_result = await db.execute(
            sa_text(
                "SELECT id, status, locked_until FROM vendor_availability "
                "WHERE vendor_id = :vendor_id AND service_id = :service_id AND date = :event_date LIMIT 1"
            ),
            {"vendor_id": vendor_id, "service_id": service_id, "event_date": event_date},
        )
        avail_row = avail_result.fetchone()
        if avail_row:
            if avail_row.status == "booked":
                return _err(
                    f"This vendor service is already booked for {event_date}. "
                    "Please choose a different date."
                )
            if avail_row.status == "blocked":
                return _err(
                    f"The vendor is not available on {event_date}. "
                    "Please choose a different date."
                )
            if avail_row.status == "locked":
                locked_until = avail_row.locked_until
                if locked_until is None:
                    return _err(
                        f"This date is pending vendor confirmation for another request. "
                        "Please choose a different date."
                    )
                if isinstance(locked_until, str):
                    locked_until = datetime.fromisoformat(locked_until)
                if locked_until.tzinfo is None:
                    locked_until = locked_until.replace(tzinfo=timezone.utc)
                if locked_until > now:
                    return _err(
                        "This date is temporarily held by another request. Please try again shortly."
                    )

        unit_price = float(svc_row.price_min or 0.0)
        qty = max(1, min(quantity, 10000))
        total_price = unit_price * qty

        booking_id = str(uuid.uuid4())

        await db.execute(
            sa_text(
                "INSERT INTO bookings "
                "(id, vendor_id, service_id, user_id, event_date, event_name, "
                " guest_count, status, quantity, notes, unit_price, total_price, "
                " currency, payment_status, created_at, updated_at) "
                "VALUES (:id, :vendor_id, :service_id, :user_id, :event_date, :event_name, "
                "        :guest_count, :status, :quantity, :notes, :unit_price, :total_price, "
                "        :currency, :payment_status, :created_at, :updated_at)"
            ),
            {
                "id": booking_id,
                "vendor_id": vendor_id,
                "service_id": service_id,
                "user_id": str(user_id),
                "event_date": event_date,
                "event_name": event_name,
                "guest_count": max(1, min(guest_count, 10000)),
                "status": "pending",
                "quantity": qty,
                "notes": notes[:500] if notes else "",
                "unit_price": unit_price,
                "total_price": total_price,
                "currency": "PKR",
                "payment_status": "pending",
                "created_at": now,
                "updated_at": now,
            },
        )

        # Hold the slot for this pending request — locked pending vendor confirmation,
        # not yet booked. Becomes 'booked' only when the vendor confirms (booking_service
        # ._confirm_lock) and is released back to 'available' on reject/cancel.
        if avail_row:
            await db.execute(
                sa_text(
                    "UPDATE vendor_availability SET status = 'locked', locked_by = NULL, "
                    "locked_until = NULL, locked_reason = 'pending_vendor_confirmation', "
                    "booking_id = :booking_id, updated_at = :now WHERE id = :id"
                ),
                {"booking_id": booking_id, "now": now, "id": avail_row.id},
            )
        else:
            await db.execute(
                sa_text(
                    "INSERT INTO vendor_availability "
                    "(id, vendor_id, service_id, date, status, locked_by, locked_until, "
                    " locked_reason, booking_id, created_at, updated_at) "
                    "VALUES (:id, :vendor_id, :service_id, :event_date, 'locked', NULL, NULL, "
                    "        'pending_vendor_confirmation', :booking_id, :now, :now)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "vendor_id": vendor_id,
                    "service_id": service_id,
                    "event_date": event_date,
                    "booking_id": booking_id,
                    "now": now,
                },
            )

        # Notify the vendor — mirrors notification_service's "booking.created" vendor notice.
        # The orchestrator runs cross-process from the backend, so the in-process event bus
        # cannot be invoked; write the notification row directly instead.
        try:
            vendor_result = await db.execute(
                sa_text("SELECT user_id FROM vendors WHERE id = :vendor_id LIMIT 1"),
                {"vendor_id": vendor_id},
            )
            vendor_row = vendor_result.fetchone()
            if vendor_row:
                await db.execute(
                    sa_text(
                        "INSERT INTO notifications "
                        "(id, user_id, type, title, body, data, is_read, created_at) "
                        "VALUES (:id, :user_id, :type, :title, :body, :data, :is_read, :created_at)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "user_id": str(vendor_row.user_id),
                        "type": "booking_created",
                        "title": "New Booking Request",
                        "body": f"You have a new booking request for {event_name} on {event_date}.",
                        "data": json.dumps({
                            "booking_id": booking_id,
                            "vendor_id": vendor_id,
                            "service_id": service_id,
                            "event_date": event_date,
                            "user_id": str(user_id),
                        }),
                        "is_read": False,
                        "created_at": now,
                    },
                )
        except Exception as notif_err:
            logger.warning("create_booking_request.notification_write_failed: %s", notif_err)

        await db.flush()
        await db.commit()

        return json.dumps({
            "success": True,
            "booking_id": booking_id,
            "status": "pending",
            "message": "Booking request created successfully. The vendor will respond within 24 hours.",
            "unit_price": unit_price,
            "total_price": total_price,
        })
    except Exception as e:
        logger.error("create_booking_request error: %s", e)
        return _err(str(e))


@function_tool
async def get_my_bookings(ctx: RunContextWrapper[AgentContext]) -> str:
    """Get all bookings for the current user.
    Returns a JSON string with list of bookings including status and vendor details."""
    try:
        from sqlalchemy import text as sa_text
        db = ctx.context.db
        user_id = ctx.context.user_id

        result = await db.execute(
            sa_text(
                "SELECT id, vendor_id, service_id, event_date, event_name, "
                "       guest_count, status, unit_price, total_price, payment_status "
                "FROM bookings WHERE user_id = :user_id ORDER BY created_at DESC"
            ),
            {"user_id": str(user_id)},
        )
        rows = result.fetchall()
        bookings = [
            {
                "id": str(row.id),
                "vendor_id": str(row.vendor_id),
                "service_id": str(row.service_id),
                "event_date": str(row.event_date),
                "event_name": row.event_name,
                "guest_count": row.guest_count,
                "status": row.status,
                "unit_price": row.unit_price,
                "total_price": row.total_price,
                "payment_status": row.payment_status,
            }
            for row in rows
        ]
        return json.dumps({"bookings": bookings, "total": len(bookings)})
    except Exception as e:
        logger.error("get_my_bookings error: %s", e)
        return json.dumps({"bookings": [], "error": str(e)})


@function_tool
async def get_booking_details(
    ctx: RunContextWrapper[AgentContext],
    booking_id: str,
) -> str:
    """Get full details of a specific booking including vendor info and status.
    Returns a JSON string with complete booking details."""
    try:
        from sqlalchemy import text as sa_text
        db = ctx.context.db
        user_id = ctx.context.user_id

        result = await db.execute(
            sa_text(
                "SELECT id, vendor_id, service_id, user_id, event_date, event_name, "
                "       guest_count, status, quantity, notes, unit_price, total_price, "
                "       currency, payment_status "
                "FROM bookings WHERE id = :booking_id AND user_id = :user_id LIMIT 1"
            ),
            {"booking_id": booking_id, "user_id": str(user_id)},
        )
        row = result.fetchone()
        if not row:
            return _err(f"Booking {booking_id} not found or does not belong to you.")

        return json.dumps({
            "id": str(row.id),
            "vendor_id": str(row.vendor_id),
            "service_id": str(row.service_id),
            "user_id": str(row.user_id),
            "event_date": str(row.event_date),
            "event_name": row.event_name,
            "guest_count": row.guest_count,
            "status": row.status,
            "quantity": row.quantity,
            "notes": row.notes,
            "unit_price": row.unit_price,
            "total_price": row.total_price,
            "currency": row.currency,
            "payment_status": row.payment_status,
        })
    except Exception as e:
        logger.error("get_booking_details error: %s", e)
        return _err(str(e))


@function_tool
async def get_active_quotes(ctx: RunContextWrapper[AgentContext]) -> str:
    """Get all open quotes for the current user's bookings.
    Returns a JSON string listing quotes that are in 'sent' or 'countered' status."""
    try:
        from sqlalchemy import text as sa_text
        db = ctx.context.db
        user_id = ctx.context.user_id

        result = await db.execute(
            sa_text(
                "SELECT q.id, q.booking_id, q.vendor_id, q.subtotal, q.deposit_required, "
                "       q.currency, q.status, q.valid_until, q.round_number, q.notes "
                "FROM quotes q "
                "JOIN bookings b ON b.id = q.booking_id "
                "WHERE b.user_id = :user_id "
                "AND q.status IN ('sent', 'countered') "
                "ORDER BY q.created_at DESC"
            ),
            {"user_id": str(user_id)},
        )
        rows = result.fetchall()
        quotes = [
            {
                "id": str(row.id),
                "booking_id": str(row.booking_id),
                "vendor_id": str(row.vendor_id),
                "subtotal": row.subtotal,
                "deposit_required": row.deposit_required,
                "currency": row.currency,
                "status": row.status,
                "valid_until": str(row.valid_until) if row.valid_until else None,
                "round_number": row.round_number,
                "notes": row.notes,
            }
            for row in rows
        ]
        return json.dumps({"quotes": quotes, "total": len(quotes)})
    except Exception as e:
        logger.error("get_active_quotes error: %s", e)
        return json.dumps({"quotes": [], "error": str(e)})


@function_tool
async def submit_counter_offer(
    ctx: RunContextWrapper[AgentContext],
    quote_id: str,
    proposed_total_pkr: float,
    message: str = "",
) -> str:
    """Submit a counter-offer on an open quote.
    IMPORTANT: Only call this AFTER showing the user the proposed amount and receiving confirmation.
    Returns a JSON string with the counter-offer ID and new quote status."""
    try:
        from sqlalchemy import text as sa_text
        db = ctx.context.db
        user_id = ctx.context.user_id

        # Verify quote exists and is in 'sent' status
        quote_result = await db.execute(
            sa_text(
                "SELECT q.id, q.status, q.booking_id, b.user_id AS booking_user_id "
                "FROM quotes q "
                "LEFT JOIN bookings b ON b.id = q.booking_id "
                "WHERE q.id = :quote_id AND q.status = 'sent' LIMIT 1"
            ),
            {"quote_id": quote_id},
        )
        quote_row = quote_result.fetchone()
        if not quote_row:
            return _err("Quote not found or is not in 'sent' status.")

        if quote_row.booking_user_id and str(quote_row.booking_user_id) != str(user_id):
            return _err("You are not authorised to counter this quote.")

        # Check round limit
        round_result = await db.execute(
            sa_text("SELECT COUNT(*) FROM counter_offers WHERE quote_id = :quote_id"),
            {"quote_id": quote_id},
        )
        round_count = round_result.scalar() or 0
        if round_count >= 5:
            return _err("Maximum negotiation rounds (5) reached.")

        # Supersede existing pending counters
        now = datetime.now(timezone.utc)
        await db.execute(
            sa_text(
                "UPDATE counter_offers SET status = 'superseded', updated_at = :now "
                "WHERE quote_id = :quote_id AND status = 'pending'"
            ),
            {"quote_id": quote_id, "now": now},
        )

        counter_id = str(uuid.uuid4())
        await db.execute(
            sa_text(
                "INSERT INTO counter_offers "
                "(id, quote_id, proposed_by_user_id, proposed_total, proposed_changes, message, status, created_at, updated_at) "
                "VALUES (:id, :quote_id, :user_id, :proposed_total, :changes, :message, 'pending', :now, :now)"
            ),
            {
                "id": counter_id,
                "quote_id": quote_id,
                "user_id": str(user_id),
                "proposed_total": proposed_total_pkr,
                "changes": json.dumps({}),
                "message": message[:500] if message else "",
                "now": now,
            },
        )

        # Update quote to 'countered' and booking to 'negotiating'
        await db.execute(
            sa_text("UPDATE quotes SET status = 'countered', updated_at = :now WHERE id = :quote_id"),
            {"quote_id": quote_id, "now": now},
        )
        if quote_row.booking_id:
            await db.execute(
                sa_text(
                    "UPDATE bookings SET status = 'negotiating', updated_at = :now "
                    "WHERE id = :booking_id AND status NOT IN ('cancelled', 'rejected', 'completed', 'no_show')"
                ),
                {"booking_id": str(quote_row.booking_id), "now": now},
            )

        await db.flush()
        await db.commit()

        # Write vendor notification directly — agent runs in orchestrator process,
        # so backend's in-process event bus cannot be called cross-process.
        # Notification appears for the vendor on next poll / window focus.
        try:
            vendor_result = await db.execute(
                sa_text(
                    "SELECT v.user_id FROM bookings b "
                    "JOIN vendors v ON v.id = b.vendor_id "
                    "WHERE b.id = :booking_id LIMIT 1"
                ),
                {"booking_id": str(quote_row.booking_id)},
            )
            vendor_row = vendor_result.fetchone()
            if vendor_row:
                notif_id = str(uuid.uuid4())
                notif_body = (
                    f"Customer proposed PKR {proposed_total_pkr:,.0f} on your quote."
                )
                await db.execute(
                    sa_text(
                        "INSERT INTO notifications "
                        "(id, user_id, type, title, body, data, is_read, created_at) "
                        "VALUES (:id, :user_id, :type, :title, :body, :data, :is_read, :created_at)"
                    ),
                    {
                        "id": notif_id,
                        "user_id": str(vendor_row.user_id),
                        "type": "booking_counter_offered",
                        "title": "Customer Counter-Offer",
                        "body": notif_body,
                        "data": json.dumps({
                            "booking_id": str(quote_row.booking_id),
                            "quote_id": quote_id,
                            "proposed_total": proposed_total_pkr,
                        }),
                        "is_read": False,
                        "created_at": now,
                    },
                )
                await db.commit()
        except Exception as notif_err:
            logger.warning("submit_counter_offer.notification_write_failed: %s", notif_err)

        return json.dumps({
            "success": True,
            "counter_offer_id": counter_id,
            "quote_status": "countered",
            "proposed_total_pkr": proposed_total_pkr,
            "message": "Counter-offer submitted. The vendor will respond shortly.",
        })
    except Exception as e:
        logger.error("submit_counter_offer error: %s", e)
        return _err(str(e))


@function_tool
async def cancel_booking(
    ctx: RunContextWrapper[AgentContext],
    booking_id: str,
    reason: str = "Cancelled by user",
) -> str:
    """Cancel an existing booking. Only call after explicit user confirmation.
    Returns a JSON string with cancellation status."""
    try:
        from sqlalchemy import text as sa_text
        db = ctx.context.db
        user_id = ctx.context.user_id

        # Fetch current status and verify ownership
        result = await db.execute(
            sa_text(
                "SELECT id, status, vendor_id, service_id, event_date, payment_status FROM bookings "
                "WHERE id = :booking_id AND user_id = :user_id LIMIT 1"
            ),
            {"booking_id": booking_id, "user_id": str(user_id)},
        )
        row = result.fetchone()
        if not row:
            return _err(f"Booking {booking_id} not found or does not belong to you.")

        current_status = row.status
        if current_status in _TERMINAL_STATES:
            return _err(
                f"Booking is already in terminal state '{current_status}'. "
                "It cannot be cancelled."
            )

        now = datetime.now(timezone.utc)

        # Reverse any payment already taken (e.g. Pro auto-pay on confirm) on a dead booking —
        # mirrors booking_service.update_status's reject/cancel branch
        new_payment_status = row.payment_status
        if row.payment_status in ("paid", "partial"):
            new_payment_status = "refunded"

        await db.execute(
            sa_text(
                "UPDATE bookings SET status = 'cancelled', "
                "cancellation_reason = :reason, cancelled_at = :now, updated_at = :now, "
                "payment_status = :payment_status "
                "WHERE id = :booking_id AND user_id = :user_id"
            ),
            {
                "reason": reason[:300],
                "now": now,
                "payment_status": new_payment_status,
                "booking_id": booking_id,
                "user_id": str(user_id),
            },
        )

        # Release the held/booked availability slot back to available — mirrors
        # booking_service._release_slot
        await db.execute(
            sa_text(
                "UPDATE vendor_availability SET status = 'available', locked_by = NULL, "
                "locked_until = NULL, locked_reason = NULL, booking_id = NULL, updated_at = :now "
                "WHERE vendor_id = :vendor_id AND service_id = :service_id AND date = :event_date"
            ),
            {
                "now": now,
                "vendor_id": str(row.vendor_id),
                "service_id": str(row.service_id),
                "event_date": row.event_date,
            },
        )

        await db.flush()
        await db.commit()

        return json.dumps({
            "success": True,
            "booking_id": booking_id,
            "message": "Booking cancelled successfully.",
        })
    except Exception as e:
        logger.error("cancel_booking error: %s", e)
        return _err(str(e))
