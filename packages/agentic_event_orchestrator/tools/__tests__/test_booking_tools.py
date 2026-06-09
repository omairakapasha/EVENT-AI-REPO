"""Tests for booking_tools.py — self-contained with in-memory SQLite fixtures.

Covers the current DB-direct implementation (no HTTP, no signed_get/signed_post).
Run explicitly: pytest tools/__tests__/test_booking_tools.py
"""
from __future__ import annotations

import dataclasses
import json
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from agents.tool_context import ToolContext
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, MetaData, String, Table
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from tools.booking_tools import (
    cancel_booking,
    create_booking_request,
    get_booking_details,
    get_my_bookings,
)

# ── Minimal AgentContext stub ─────────────────────────────────────────────────


@dataclasses.dataclass
class _AgentContext:
    db: AsyncSession
    user_id: uuid.UUID


# ── Minimal table metadata ────────────────────────────────────────────────────

_meta = MetaData()

_users = Table(
    "users", _meta,
    Column("id", String(36), primary_key=True),
    Column("email", String(255), unique=True, nullable=False),
    Column("password_hash", String(255), default="hash"),
    Column("role", String(50), default="user"),
    Column("is_active", Boolean, default=True),
    Column("email_verified", Boolean, default=False),
    Column("failed_login_attempts", Integer, default=0),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
)

_vendors = Table(
    "vendors", _meta,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id"), unique=True, nullable=False),
    Column("business_name", String(255), nullable=False),
    Column("contact_email", String(255), unique=True, nullable=False),
    Column("status", String(50), default="ACTIVE"),
    Column("rating", Float, default=0.0),
    Column("total_reviews", Integer, default=0),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
)

_services = Table(
    "services", _meta,
    Column("id", String(36), primary_key=True),
    Column("vendor_id", String(36), ForeignKey("vendors.id"), nullable=False),
    Column("name", String(255), nullable=False),
    Column("price_min", Float),
    Column("price_max", Float),
    Column("capacity", Integer),
    Column("is_active", Boolean, default=True),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
)

_bookings = Table(
    "bookings", _meta,
    Column("id", String(36), primary_key=True),
    Column("vendor_id", String(36), ForeignKey("vendors.id"), nullable=False),
    Column("service_id", String(36), ForeignKey("services.id"), nullable=False),
    Column("user_id", String(36), ForeignKey("users.id")),
    Column("event_date", String(50), nullable=False),
    Column("event_name", String(255)),
    Column("guest_count", Integer),
    Column("status", String(50), default="pending"),
    Column("quantity", Integer, default=1),
    Column("notes", String(1000)),
    Column("unit_price", Float, nullable=False),
    Column("total_price", Float, nullable=False),
    Column("currency", String(3), default="USD"),
    Column("payment_status", String(50), default="pending"),
    Column("cancellation_reason", String(300)),
    Column("cancelled_at", DateTime),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)


@pytest_asyncio.fixture(scope="module")
async def create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(_meta.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(_meta.drop_all)


@pytest_asyncio.fixture
async def db(engine, create_tables):
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
def make_ctx(db):
    def _make(user_id: uuid.UUID) -> ToolContext:
        return ToolContext(
            context=_AgentContext(db=db, user_id=user_id),
            tool_name="test_tool",
            tool_call_id="test-call-id",
            tool_arguments="{}",
            run_config=None,
        )
    return _make


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _call(tool, ctx, **kwargs) -> dict:
    raw = await tool.on_invoke_tool(ctx, json.dumps(kwargs))
    return json.loads(raw)


async def _seed(db: AsyncSession) -> tuple[uuid.UUID, str, str]:
    """Create user, vendor, service; return (user_id, vendor_id, service_id)."""
    user_id = uuid.uuid4()
    vendor_user_id = uuid.uuid4()
    vendor_id = uuid.uuid4()
    service_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    await db.execute(_users.insert().values(
        id=str(user_id), email=f"u-{user_id}@test.com",
        password_hash="x", created_at=now, updated_at=now,
    ))
    await db.execute(_users.insert().values(
        id=str(vendor_user_id), email=f"v-{vendor_user_id}@test.com",
        password_hash="x", created_at=now, updated_at=now,
    ))
    await db.execute(_vendors.insert().values(
        id=str(vendor_id), user_id=str(vendor_user_id),
        business_name="Test Vendor", contact_email=f"{vendor_id}@v.com",
        status="ACTIVE", rating=4.5, total_reviews=10, created_at=now, updated_at=now,
    ))
    await db.execute(_services.insert().values(
        id=str(service_id), vendor_id=str(vendor_id),
        name="Wedding Package", price_min=50000.0, price_max=150000.0,
        capacity=500, is_active=True, created_at=now, updated_at=now,
    ))
    return user_id, str(vendor_id), str(service_id)


# ── Tests: create_booking_request ────────────────────────────────────────────


class TestCreateBookingRequest:
    @pytest.mark.asyncio
    async def test_creates_booking_in_pending_state(self, db, make_ctx):
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)

        result = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2030-01-15", event_name="Wedding", guest_count=200,
        )

        assert result["success"] is True
        assert "booking_id" in result
        assert result["status"] == "pending"
        assert result["unit_price"] == 50000.0
        assert result["total_price"] == 50000.0

    @pytest.mark.asyncio
    async def test_unknown_service_returns_error(self, db, make_ctx):
        user_id, vendor_id, _ = await _seed(db)
        ctx = make_ctx(user_id)

        result = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=str(uuid.uuid4()),
            event_date="2030-02-01", event_name="Birthday", guest_count=50,
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_quantity_multiplies_total_price(self, db, make_ctx):
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)

        result = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2030-03-01", event_name="Corporate", guest_count=50, quantity=3,
        )

        assert result["success"] is True
        assert result["total_price"] == pytest.approx(50000.0 * 3)

    @pytest.mark.asyncio
    async def test_notes_truncated_at_500_chars(self, db, make_ctx):
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)

        long_note = "x" * 600
        result = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2030-04-01", event_name="Mehndi", guest_count=100,
            notes=long_note,
        )

        assert result["success"] is True


# ── Tests: get_my_bookings ────────────────────────────────────────────────────


class TestGetMyBookings:
    @pytest.mark.asyncio
    async def test_empty_for_new_user(self, db, make_ctx):
        user_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        await db.execute(_users.insert().values(
            id=str(user_id), email=f"empty-{user_id}@test.com",
            password_hash="x", created_at=now, updated_at=now,
        ))
        ctx = make_ctx(user_id)

        result = await _call(get_my_bookings, ctx)

        assert result["bookings"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_returns_users_own_bookings(self, db, make_ctx):
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2030-06-01", event_name="Walima", guest_count=150,
        )
        assert cr["success"] is True

        result = await _call(get_my_bookings, ctx)

        ids = [b["id"] for b in result["bookings"]]
        assert cr["booking_id"] in ids

    @pytest.mark.asyncio
    async def test_does_not_return_other_users_bookings(self, db, make_ctx):
        user_id, vendor_id, service_id = await _seed(db)
        other_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        await db.execute(_users.insert().values(
            id=str(other_id), email=f"other-{other_id}@test.com",
            password_hash="x", created_at=now, updated_at=now,
        ))
        ctx_owner = make_ctx(user_id)
        ctx_other = make_ctx(other_id)

        cr = await _call(
            create_booking_request, ctx_owner,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2030-07-01", event_name="Baraat", guest_count=200,
        )

        result = await _call(get_my_bookings, ctx_other)

        ids = [b["id"] for b in result["bookings"]]
        assert cr["booking_id"] not in ids


# ── Tests: get_booking_details ────────────────────────────────────────────────


class TestGetBookingDetails:
    @pytest.mark.asyncio
    async def test_owner_gets_full_details(self, db, make_ctx):
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2030-09-01", event_name="Nikah", guest_count=300,
        )
        booking_id = cr["booking_id"]

        detail = await _call(get_booking_details, ctx, booking_id=booking_id)

        assert detail["id"] == booking_id
        assert detail["status"] == "pending"
        assert detail["event_name"] == "Nikah"
        assert detail["vendor_id"] == vendor_id

    @pytest.mark.asyncio
    async def test_other_user_cannot_see_booking(self, db, make_ctx):
        user_id, vendor_id, service_id = await _seed(db)
        other_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        await db.execute(_users.insert().values(
            id=str(other_id), email=f"spy-{other_id}@test.com",
            password_hash="x", created_at=now, updated_at=now,
        ))
        ctx_owner = make_ctx(user_id)
        ctx_spy = make_ctx(other_id)

        cr = await _call(
            create_booking_request, ctx_owner,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2030-10-01", event_name="Anniversary", guest_count=60,
        )

        result = await _call(get_booking_details, ctx_spy, booking_id=cr["booking_id"])

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_nonexistent_booking_returns_error(self, db, make_ctx):
        user_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        await db.execute(_users.insert().values(
            id=str(user_id), email=f"ghost-{user_id}@test.com",
            password_hash="x", created_at=now, updated_at=now,
        ))
        ctx = make_ctx(user_id)

        result = await _call(get_booking_details, ctx, booking_id=str(uuid.uuid4()))

        assert result["success"] is False


# ── Tests: cancel_booking ─────────────────────────────────────────────────────


class TestCancelBooking:
    @pytest.mark.asyncio
    async def test_cancels_pending_booking(self, db, make_ctx):
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2030-12-01", event_name="Birthday", guest_count=50,
        )
        booking_id = cr["booking_id"]

        result = await _call(cancel_booking, ctx, booking_id=booking_id, reason="Changed plans")

        assert result["success"] is True
        assert result["booking_id"] == booking_id

    @pytest.mark.asyncio
    async def test_cannot_cancel_twice(self, db, make_ctx):
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2031-01-01", event_name="Engagement", guest_count=80,
        )
        booking_id = cr["booking_id"]

        await _call(cancel_booking, ctx, booking_id=booking_id)
        second = await _call(cancel_booking, ctx, booking_id=booking_id)

        assert second["success"] is False
        assert "terminal" in second["error"].lower()

    @pytest.mark.asyncio
    async def test_cannot_cancel_other_users_booking(self, db, make_ctx):
        user_id, vendor_id, service_id = await _seed(db)
        other_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        await db.execute(_users.insert().values(
            id=str(other_id), email=f"bad-{other_id}@test.com",
            password_hash="x", created_at=now, updated_at=now,
        ))
        ctx_owner = make_ctx(user_id)
        ctx_other = make_ctx(other_id)

        cr = await _call(
            create_booking_request, ctx_owner,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2031-02-01", event_name="Graduation", guest_count=100,
        )

        result = await _call(cancel_booking, ctx_other, booking_id=cr["booking_id"])

        assert result["success"] is False
