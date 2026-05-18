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
                "WHERE id = :service_id AND is_active = 1 OR "
                "      id = :service_id AND is_active = true LIMIT 1"
            ),
            {"service_id": service_id},
        )
        svc_row = svc_result.fetchone()
        if not svc_row:
            return _err(f"Service {service_id} not found or is not active.")

        unit_price = float(svc_row.price_min or 0.0)
        qty = max(1, min(quantity, 10000))
        total_price = unit_price * qty

        booking_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

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
                "currency": "USD",
                "payment_status": "pending",
                "created_at": now,
                "updated_at": now,
            },
        )
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
                "SELECT id, status FROM bookings "
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
        await db.execute(
            sa_text(
                "UPDATE bookings SET status = 'cancelled', "
                "cancellation_reason = :reason, cancelled_at = :now, updated_at = :now "
                "WHERE id = :booking_id AND user_id = :user_id"
            ),
            {
                "reason": reason[:300],
                "now": now,
                "booking_id": booking_id,
                "user_id": str(user_id),
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
