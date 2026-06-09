"""Integration tests for booking_tools.py — DB-direct tools via SQLite fixtures.

Uses conftest.py fixtures: db_session, make_ctx, and the shared table metadata.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text as sa_text

from tools.booking_tools import (
    cancel_booking,
    create_booking_request,
    get_booking_details,
    get_my_bookings,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _call(tool, ctx, **kwargs) -> dict:
    raw = await tool.on_invoke_tool(ctx, json.dumps(kwargs))
    return json.loads(raw)


async def _seed(db) -> tuple[uuid.UUID, str, str]:
    """Insert user + vendor + service. Returns (user_id, vendor_id, service_id)."""
    user_id = uuid.uuid4()
    vendor_user_id = uuid.uuid4()
    vendor_id = uuid.uuid4()
    service_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    for uid, email in [(user_id, f"u-{user_id}@test.com"), (vendor_user_id, f"vu-{vendor_user_id}@test.com")]:
        await db.execute(sa_text(
            "INSERT INTO users (id, email, password_hash, role, is_active, email_verified, "
            "failed_login_attempts, created_at, updated_at) "
            "VALUES (:id, :email, 'x', 'user', 1, 0, 0, :now, :now)"
        ), {"id": str(uid), "email": email, "now": now})

    await db.execute(sa_text(
        "INSERT INTO vendors (id, user_id, business_name, contact_email, status, rating, "
        "total_reviews, created_at, updated_at) "
        "VALUES (:id, :uid, 'Acme Events', :email, 'ACTIVE', 4.7, 20, :now, :now)"
    ), {"id": str(vendor_id), "uid": str(vendor_user_id),
        "email": f"{vendor_id}@acme.com", "now": now})

    await db.execute(sa_text(
        "INSERT INTO services (id, vendor_id, name, price_min, price_max, capacity, "
        "is_active, created_at, updated_at) "
        "VALUES (:id, :vid, 'Full Wedding Package', 75000.0, 200000.0, 600, 1, :now, :now)"
    ), {"id": str(service_id), "vid": str(vendor_id), "now": now})

    return user_id, str(vendor_id), str(service_id)


# ── create_booking_request ────────────────────────────────────────────────────


class TestCreateBookingRequest:
    @pytest.mark.asyncio
    async def test_success_returns_booking_id_and_pending_status(self, db_session, make_ctx):
        user_id, vendor_id, service_id = await _seed(db_session)
        ctx = make_ctx(user_id)

        result = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2030-06-15", event_name="Grand Wedding", guest_count=400,
        )

        assert result["success"] is True
        assert uuid.UUID(result["booking_id"])  # valid UUID
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_price_computed_from_service_price_min(self, db_session, make_ctx):
        user_id, vendor_id, service_id = await _seed(db_session)
        ctx = make_ctx(user_id)

        result = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2030-07-01", event_name="Reception", guest_count=200,
        )

        assert result["unit_price"] == 75000.0
        assert result["total_price"] == 75000.0

    @pytest.mark.asyncio
    async def test_quantity_scales_total_price(self, db_session, make_ctx):
        user_id, vendor_id, service_id = await _seed(db_session)
        ctx = make_ctx(user_id)

        result = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2030-08-01", event_name="Multi-Day", guest_count=100, quantity=2,
        )

        assert result["total_price"] == pytest.approx(75000.0 * 2)

    @pytest.mark.asyncio
    async def test_inactive_service_returns_error(self, db_session, make_ctx):
        user_id, vendor_id, _ = await _seed(db_session)
        ctx = make_ctx(user_id)

        # Insert inactive service
        inactive_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        await db_session.execute(sa_text(
            "INSERT INTO services (id, vendor_id, name, price_min, price_max, capacity, "
            "is_active, created_at, updated_at) "
            "VALUES (:id, :vid, 'Inactive', 1000.0, 5000.0, 50, 0, :now, :now)"
        ), {"id": inactive_id, "vid": vendor_id, "now": now})

        result = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=inactive_id,
            event_date="2030-09-01", event_name="Party", guest_count=30,
        )

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_missing_service_returns_error(self, db_session, make_ctx):
        user_id, vendor_id, _ = await _seed(db_session)
        ctx = make_ctx(user_id)

        result = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=str(uuid.uuid4()),
            event_date="2030-10-01", event_name="Birthday", guest_count=20,
        )

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_booking_persisted_in_db(self, db_session, make_ctx):
        user_id, vendor_id, service_id = await _seed(db_session)
        ctx = make_ctx(user_id)

        result = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2030-11-01", event_name="Nikah", guest_count=300,
        )
        booking_id = result["booking_id"]

        row = await db_session.execute(
            sa_text("SELECT id, status, user_id FROM bookings WHERE id = :id"),
            {"id": booking_id},
        )
        booking = row.fetchone()

        assert booking is not None
        assert booking.status == "pending"
        assert booking.user_id == str(user_id)


# ── get_my_bookings ───────────────────────────────────────────────────────────


class TestGetMyBookings:
    @pytest.mark.asyncio
    async def test_new_user_gets_empty_list(self, db_session, make_ctx):
        user_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        await db_session.execute(sa_text(
            "INSERT INTO users (id, email, password_hash, role, is_active, email_verified, "
            "failed_login_attempts, created_at, updated_at) "
            "VALUES (:id, :email, 'x', 'user', 1, 0, 0, :now, :now)"
        ), {"id": str(user_id), "email": f"fresh-{user_id}@t.com", "now": now})
        ctx = make_ctx(user_id)

        result = await _call(get_my_bookings, ctx)

        assert result["bookings"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_returns_created_booking(self, db_session, make_ctx):
        user_id, vendor_id, service_id = await _seed(db_session)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2030-12-01", event_name="Baraat", guest_count=250,
        )

        result = await _call(get_my_bookings, ctx)

        booking_ids = [b["id"] for b in result["bookings"]]
        assert cr["booking_id"] in booking_ids

    @pytest.mark.asyncio
    async def test_scoped_to_current_user(self, db_session, make_ctx):
        """Bookings from other users must not appear."""
        user_a_id, vendor_id, service_id = await _seed(db_session)
        user_b_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        await db_session.execute(sa_text(
            "INSERT INTO users (id, email, password_hash, role, is_active, email_verified, "
            "failed_login_attempts, created_at, updated_at) "
            "VALUES (:id, :email, 'x', 'user', 1, 0, 0, :now, :now)"
        ), {"id": str(user_b_id), "email": f"b-{user_b_id}@t.com", "now": now})

        ctx_a = make_ctx(user_a_id)
        ctx_b = make_ctx(user_b_id)

        cr = await _call(
            create_booking_request, ctx_a,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2031-01-01", event_name="Walima", guest_count=120,
        )

        result_b = await _call(get_my_bookings, ctx_b)

        booking_ids = [b["id"] for b in result_b["bookings"]]
        assert cr["booking_id"] not in booking_ids

    @pytest.mark.asyncio
    async def test_response_shape_has_required_fields(self, db_session, make_ctx):
        user_id, vendor_id, service_id = await _seed(db_session)
        ctx = make_ctx(user_id)

        await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2031-02-01", event_name="Engagement", guest_count=80,
        )

        result = await _call(get_my_bookings, ctx)

        assert "bookings" in result
        assert "total" in result
        for b in result["bookings"]:
            for field in ("id", "vendor_id", "service_id", "event_date", "status",
                          "unit_price", "total_price", "payment_status"):
                assert field in b, f"Missing field: {field}"


# ── get_booking_details ───────────────────────────────────────────────────────


class TestGetBookingDetails:
    @pytest.mark.asyncio
    async def test_owner_retrieves_full_details(self, db_session, make_ctx):
        user_id, vendor_id, service_id = await _seed(db_session)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2031-03-01", event_name="Annual Dinner", guest_count=150,
        )
        booking_id = cr["booking_id"]

        detail = await _call(get_booking_details, ctx, booking_id=booking_id)

        assert detail["id"] == booking_id
        assert detail["status"] == "pending"
        assert detail["event_name"] == "Annual Dinner"
        assert detail["vendor_id"] == vendor_id
        assert detail["currency"] == "PKR"

    @pytest.mark.asyncio
    async def test_other_user_cannot_read(self, db_session, make_ctx):
        user_id, vendor_id, service_id = await _seed(db_session)
        other_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        await db_session.execute(sa_text(
            "INSERT INTO users (id, email, password_hash, role, is_active, email_verified, "
            "failed_login_attempts, created_at, updated_at) "
            "VALUES (:id, :email, 'x', 'user', 1, 0, 0, :now, :now)"
        ), {"id": str(other_id), "email": f"other-{other_id}@t.com", "now": now})

        ctx_owner = make_ctx(user_id)
        ctx_other = make_ctx(other_id)

        cr = await _call(
            create_booking_request, ctx_owner,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2031-04-01", event_name="Conference", guest_count=200,
        )

        result = await _call(get_booking_details, ctx_other, booking_id=cr["booking_id"])

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_nonexistent_booking_returns_error(self, db_session, make_ctx):
        ctx = make_ctx(uuid.uuid4())

        result = await _call(get_booking_details, ctx, booking_id=str(uuid.uuid4()))

        assert result["success"] is False


# ── cancel_booking ────────────────────────────────────────────────────────────


class TestCancelBooking:
    @pytest.mark.asyncio
    async def test_cancels_pending_booking(self, db_session, make_ctx):
        user_id, vendor_id, service_id = await _seed(db_session)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2031-05-01", event_name="Mehndi Night", guest_count=100,
        )
        booking_id = cr["booking_id"]

        result = await _call(cancel_booking, ctx, booking_id=booking_id, reason="Venue changed")

        assert result["success"] is True
        assert result["booking_id"] == booking_id

    @pytest.mark.asyncio
    async def test_status_updated_in_db_after_cancel(self, db_session, make_ctx):
        user_id, vendor_id, service_id = await _seed(db_session)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2031-06-01", event_name="Graduation Party", guest_count=60,
        )
        booking_id = cr["booking_id"]

        await _call(cancel_booking, ctx, booking_id=booking_id, reason="Budget cut")

        row = await db_session.execute(
            sa_text("SELECT status, cancellation_reason FROM bookings WHERE id = :id"),
            {"id": booking_id},
        )
        booking = row.fetchone()
        assert booking.status == "cancelled"
        assert booking.cancellation_reason == "Budget cut"

    @pytest.mark.asyncio
    async def test_terminal_booking_cannot_be_cancelled(self, db_session, make_ctx):
        user_id, vendor_id, service_id = await _seed(db_session)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2031-07-01", event_name="Corporate Dinner", guest_count=80,
        )
        booking_id = cr["booking_id"]

        await _call(cancel_booking, ctx, booking_id=booking_id)
        second = await _call(cancel_booking, ctx, booking_id=booking_id)

        assert second["success"] is False
        assert "terminal" in second["error"].lower()

    @pytest.mark.asyncio
    async def test_other_user_cannot_cancel(self, db_session, make_ctx):
        user_id, vendor_id, service_id = await _seed(db_session)
        attacker_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        await db_session.execute(sa_text(
            "INSERT INTO users (id, email, password_hash, role, is_active, email_verified, "
            "failed_login_attempts, created_at, updated_at) "
            "VALUES (:id, :email, 'x', 'user', 1, 0, 0, :now, :now)"
        ), {"id": str(attacker_id), "email": f"atk-{attacker_id}@t.com", "now": now})

        ctx_owner = make_ctx(user_id)
        ctx_attacker = make_ctx(attacker_id)

        cr = await _call(
            create_booking_request, ctx_owner,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2031-08-01", event_name="Anniversary", guest_count=40,
        )

        result = await _call(cancel_booking, ctx_attacker, booking_id=cr["booking_id"])

        assert result["success"] is False

        # Verify booking still pending in DB
        row = await db_session.execute(
            sa_text("SELECT status FROM bookings WHERE id = :id"),
            {"id": cr["booking_id"]},
        )
        assert row.fetchone().status == "pending"
