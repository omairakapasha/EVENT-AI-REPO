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
    get_active_quotes,
    get_booking_details,
    get_my_bookings,
    submit_counter_offer,
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

_quotes = Table(
    "quotes", _meta,
    Column("id", String(36), primary_key=True),
    Column("booking_id", String(36), ForeignKey("bookings.id"), nullable=True),
    Column("vendor_id", String(36), ForeignKey("vendors.id"), nullable=False),
    Column("subtotal", Float, nullable=False),
    Column("deposit_required", Float, default=0.0),
    Column("currency", String(3), default="PKR"),
    Column("status", String(50), default="sent"),
    Column("valid_until", DateTime, nullable=True),
    Column("round_number", Integer, default=1),
    Column("notes", String(1000), nullable=True),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
)

_counter_offers = Table(
    "counter_offers", _meta,
    Column("id", String(36), primary_key=True),
    Column("quote_id", String(36), ForeignKey("quotes.id"), nullable=False),
    Column("proposed_by_user_id", String(36), ForeignKey("users.id"), nullable=False),
    Column("proposed_total", Float, nullable=False),
    Column("proposed_changes", String(1000), nullable=True),
    Column("message", String(500), nullable=True),
    Column("status", String(50), default="pending"),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
)

_notifications = Table(
    "notifications", _meta,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id"), nullable=False),
    Column("type", String(100), nullable=False),
    Column("title", String(255), nullable=False),
    Column("body", String(2000), nullable=False),
    Column("data", String(4000), nullable=True),
    Column("is_read", Boolean, default=False),
    Column("read_at", DateTime, nullable=True),
    Column("created_at", DateTime),
)

_vendor_availability = Table(
    "vendor_availability", _meta,
    Column("id", String(36), primary_key=True),
    Column("vendor_id", String(36), ForeignKey("vendors.id"), nullable=False),
    Column("service_id", String(36), ForeignKey("services.id"), nullable=True),
    Column("date", String(50), nullable=False),
    Column("status", String(20), default="available"),
    Column("locked_by", String(36), nullable=True),
    Column("locked_until", DateTime, nullable=True),
    Column("locked_reason", String(255), nullable=True),
    Column("booking_id", String(36), ForeignKey("bookings.id"), nullable=True),
    Column("notes", String(500), nullable=True),
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

    @pytest.mark.asyncio
    async def test_holds_availability_slot_pending_confirmation(self, db, make_ctx):
        """Creating a booking via chat holds the slot — locked, not yet booked —
        mirroring booking_service._hold_pending."""
        from sqlalchemy import text as sa_text
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2033-01-01", event_name="Aqiqah", guest_count=40,
        )
        assert cr["success"] is True

        result = await db.execute(
            sa_text(
                "SELECT status, locked_until, booking_id FROM vendor_availability "
                "WHERE vendor_id = :vendor_id AND service_id = :service_id AND date = :event_date"
            ),
            {"vendor_id": vendor_id, "service_id": service_id, "event_date": "2033-01-01"},
        )
        row = result.fetchone()
        assert row is not None
        assert row.status == "locked"
        assert row.locked_until is None
        assert row.booking_id == cr["booking_id"]

    @pytest.mark.asyncio
    async def test_writes_vendor_notification(self, db, make_ctx):
        """Creating a booking via chat notifies the vendor — mirrors notification_service's
        'booking.created' vendor notice, written directly since the orchestrator runs
        cross-process from the backend's in-process event bus."""
        from sqlalchemy import text as sa_text
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)

        await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2033-02-01", event_name="Birthday", guest_count=60,
        )

        result = await db.execute(
            sa_text("SELECT COUNT(*) FROM notifications WHERE type = 'booking_created'")
        )
        assert result.scalar() >= 1

    @pytest.mark.asyncio
    async def test_rejects_when_slot_pending_confirmation_for_other_booking(self, db, make_ctx):
        """If the availability slot is already held pending confirmation for another
        request, a new request for the same vendor/service/date is rejected — mirrors
        booking_service._acquire_lock's CONFLICT_DATE_UNAVAILABLE check."""
        from sqlalchemy import text as sa_text
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)
        now = datetime.now(timezone.utc)

        await db.execute(_vendor_availability.insert().values(
            id=str(uuid.uuid4()), vendor_id=vendor_id, service_id=service_id,
            date="2033-03-01", status="locked", locked_until=None,
            locked_reason="pending_vendor_confirmation", booking_id=None,
            created_at=now, updated_at=now,
        ))
        await db.commit()

        result = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2033-03-01", event_name="Conference", guest_count=20,
        )

        assert result["success"] is False
        assert "pending vendor confirmation" in result["error"].lower()


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

    @pytest.mark.asyncio
    async def test_cancel_releases_held_slot(self, db, make_ctx):
        """Cancelling a pending booking releases its held availability slot back to
        available — mirrors booking_service._release_slot."""
        from sqlalchemy import text as sa_text
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2031-03-01", event_name="Engagement", guest_count=80,
        )
        booking_id = cr["booking_id"]

        result = await _call(cancel_booking, ctx, booking_id=booking_id, reason="Changed plans")
        assert result["success"] is True

        avail = await db.execute(
            sa_text(
                "SELECT status, booking_id FROM vendor_availability "
                "WHERE vendor_id = :vendor_id AND service_id = :service_id AND date = :event_date"
            ),
            {"vendor_id": vendor_id, "service_id": service_id, "event_date": "2031-03-01"},
        )
        row = avail.fetchone()
        assert row is not None
        assert row.status == "available"
        assert row.booking_id is None

    @pytest.mark.asyncio
    async def test_cancel_refunds_paid_booking(self, db, make_ctx):
        """Cancelling a booking whose payment was already taken (e.g. Pro auto-pay on
        confirm) flips payment_status to refunded — mirrors booking_service.update_status's
        reject/cancel branch."""
        from sqlalchemy import text as sa_text
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2031-04-01", event_name="Reception", guest_count=120,
        )
        booking_id = cr["booking_id"]

        await db.execute(
            sa_text("UPDATE bookings SET payment_status = 'paid' WHERE id = :id"),
            {"id": booking_id},
        )
        await db.commit()

        result = await _call(cancel_booking, ctx, booking_id=booking_id)
        assert result["success"] is True

        row = (await db.execute(
            sa_text("SELECT payment_status FROM bookings WHERE id = :id"),
            {"id": booking_id},
        )).fetchone()
        assert row.payment_status == "refunded"


# ── Helpers: seed quote & counter_offer ──────────────────────────────────────


async def _seed_quote(db: AsyncSession, booking_id: str, vendor_id: str, status: str = "sent") -> str:
    quote_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.execute(_quotes.insert().values(
        id=quote_id, booking_id=booking_id, vendor_id=vendor_id,
        subtotal=100000.0, deposit_required=20000.0, currency="PKR",
        status=status, round_number=1, created_at=now, updated_at=now,
    ))
    await db.commit()
    return quote_id


async def _seed_counter(db: AsyncSession, quote_id: str, user_id: str, count: int = 1) -> None:
    now = datetime.now(timezone.utc)
    for _ in range(count):
        await db.execute(_counter_offers.insert().values(
            id=str(uuid.uuid4()), quote_id=quote_id,
            proposed_by_user_id=user_id, proposed_total=80000.0,
            proposed_changes="{}", message="", status="pending",
            created_at=now, updated_at=now,
        ))
    await db.commit()


# ── Tests: get_active_quotes ──────────────────────────────────────────────────


class TestGetActiveQuotes:
    @pytest.mark.asyncio
    async def test_returns_sent_quotes_for_user(self, db, make_ctx):
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2032-01-01", event_name="Wedding", guest_count=300,
        )
        quote_id = await _seed_quote(db, cr["booking_id"], vendor_id, status="sent")

        result = await _call(get_active_quotes, ctx)

        assert result["total"] >= 1
        ids = [q["id"] for q in result["quotes"]]
        assert quote_id in ids

    @pytest.mark.asyncio
    async def test_empty_for_user_with_no_quotes(self, db, make_ctx):
        user_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        await db.execute(_users.insert().values(
            id=str(user_id), email=f"noquotes-{user_id}@test.com",
            password_hash="x", created_at=now, updated_at=now,
        ))
        ctx = make_ctx(user_id)

        result = await _call(get_active_quotes, ctx)

        assert result["quotes"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_excludes_accepted_quotes(self, db, make_ctx):
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2032-02-01", event_name="Mehndi", guest_count=150,
        )
        quote_id = await _seed_quote(db, cr["booking_id"], vendor_id, status="accepted")

        result = await _call(get_active_quotes, ctx)

        ids = [q["id"] for q in result["quotes"]]
        assert quote_id not in ids


# ── Tests: submit_counter_offer ───────────────────────────────────────────────


class TestSubmitCounterOffer:
    @pytest.mark.asyncio
    async def test_counter_on_sent_quote_succeeds(self, db, make_ctx):
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2032-03-01", event_name="Baraat", guest_count=200,
        )
        quote_id = await _seed_quote(db, cr["booking_id"], vendor_id, status="sent")

        result = await _call(
            submit_counter_offer, ctx,
            quote_id=quote_id, proposed_total_pkr=80000.0, message="Can you do 80k?",
        )

        assert result["success"] is True
        assert result["quote_status"] == "countered"
        assert result["counter_offer_id"] is not None

    @pytest.mark.asyncio
    async def test_counter_on_non_sent_quote_fails(self, db, make_ctx):
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2032-04-01", event_name="Walima", guest_count=100,
        )
        quote_id = await _seed_quote(db, cr["booking_id"], vendor_id, status="countered")

        result = await _call(
            submit_counter_offer, ctx,
            quote_id=quote_id, proposed_total_pkr=70000.0,
        )

        assert result["success"] is False
        assert "sent" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_counter_by_wrong_user_fails(self, db, make_ctx):
        user_id, vendor_id, service_id = await _seed(db)
        other_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        await db.execute(_users.insert().values(
            id=str(other_id), email=f"intruder-{other_id}@test.com",
            password_hash="x", created_at=now, updated_at=now,
        ))
        ctx_owner = make_ctx(user_id)
        ctx_intruder = make_ctx(other_id)

        cr = await _call(
            create_booking_request, ctx_owner,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2032-05-01", event_name="Nikah", guest_count=250,
        )
        quote_id = await _seed_quote(db, cr["booking_id"], vendor_id, status="sent")

        result = await _call(
            submit_counter_offer, ctx_intruder,
            quote_id=quote_id, proposed_total_pkr=60000.0,
        )

        assert result["success"] is False
        assert "authoris" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_counter_max_rounds_exceeded(self, db, make_ctx):
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2032-06-01", event_name="Corporate", guest_count=50,
        )
        quote_id = await _seed_quote(db, cr["booking_id"], vendor_id, status="sent")
        await _seed_counter(db, quote_id, str(user_id), count=5)

        result = await _call(
            submit_counter_offer, ctx,
            quote_id=quote_id, proposed_total_pkr=90000.0,
        )

        assert result["success"] is False
        assert "maximum" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_counter_writes_vendor_notification(self, db, make_ctx):
        from sqlalchemy import text as sa_text
        user_id, vendor_id, service_id = await _seed(db)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_booking_request, ctx,
            vendor_id=vendor_id, service_id=service_id,
            event_date="2032-07-01", event_name="Birthday", guest_count=80,
        )
        quote_id = await _seed_quote(db, cr["booking_id"], vendor_id, status="sent")

        await _call(
            submit_counter_offer, ctx,
            quote_id=quote_id, proposed_total_pkr=75000.0, message="Budget is tight",
        )

        result = await db.execute(
            sa_text(
                "SELECT COUNT(*) FROM notifications "
                "WHERE type = 'booking_counter_offered'"
            )
        )
        count = result.scalar()
        assert count >= 1
