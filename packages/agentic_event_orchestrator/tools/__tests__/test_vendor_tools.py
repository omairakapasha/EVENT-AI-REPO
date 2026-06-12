"""Unit tests for vendor tools — uses on_invoke_tool pattern (same as test_booking_tools)."""
from __future__ import annotations

import dataclasses
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
import respx
from agents.tool_context import ToolContext
from sqlalchemy import Column, DateTime, Float, Integer, MetaData, String, Table, Boolean
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from tools.vendor_tools import (
    _merge_vendor_suggestions,
    get_vendor_details,
    search_vendors,
    get_vendor_recommendations,
)


# ── Minimal AgentContext stub ─────────────────────────────────────────────────

@dataclasses.dataclass
class _AgentContext:
    db: AsyncSession
    user_id: uuid.UUID
    vendor_suggestions: list = dataclasses.field(default_factory=list)


# ── SQLite DB fixtures (mirrors booking_tools test pattern) ──────────────────

_meta = MetaData()

_vendors = Table(
    "vendors", _meta,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(36), nullable=False),
    Column("business_name", String(255), nullable=False),
    Column("contact_email", String(255), unique=True, nullable=False),
    Column("description", String(500)),
    Column("city", String(100)),
    Column("region", String(100)),
    Column("status", String(50), default="ACTIVE"),
    Column("rating", Float, default=0.0),
    Column("total_reviews", Integer, default=0),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
)

_services = Table(
    "services", _meta,
    Column("id", String(36), primary_key=True),
    Column("vendor_id", String(36), nullable=False),
    Column("name", String(255), nullable=False),
    Column("description", String(500)),
    Column("price_min", Float),
    Column("price_max", Float),
    Column("capacity", Integer),
    Column("is_active", Boolean, default=True),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
)

_vendor_availability = Table(
    "vendor_availability", _meta,
    Column("id", String(36), primary_key=True),
    Column("vendor_id", String(36), nullable=False),
    Column("service_id", String(36), nullable=True),
    Column("date", String(20), nullable=False),
    Column("status", String(50), default="available"),
    Column("locked_until", DateTime, nullable=True),
)


@pytest_asyncio.fixture(scope="module")
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(_meta.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(_meta.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
def make_ctx(db):
    def _make() -> ToolContext:
        ctx = _AgentContext(db=db, user_id=uuid.uuid4())
        return ToolContext(
            context=ctx,
            tool_name="test_tool",
            tool_call_id="test-call-id",
            tool_arguments="{}",
            run_config=None,
        )
    return _make


async def _call(tool, ctx, **kwargs) -> dict:
    raw = await tool.on_invoke_tool(ctx, json.dumps(kwargs))
    return json.loads(raw)


async def _seed_vendor(db: AsyncSession, status: str = "ACTIVE") -> tuple[str, str]:
    """Insert vendor + service; return (vendor_id, service_id)."""
    vid = str(uuid.uuid4())
    sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.execute(_vendors.insert().values(
        id=vid, user_id=str(uuid.uuid4()),
        business_name="Elite Events Co", contact_email=f"{vid}@v.com",
        description="Premium event services", city="Lahore", region="Punjab",
        status=status, rating=4.8, total_reviews=50,
        created_at=now, updated_at=now,
    ))
    await db.execute(_services.insert().values(
        id=sid, vendor_id=vid,
        name="Wedding Package", description="Full wedding planning",
        price_min=50000.0, price_max=150000.0,
        capacity=500, is_active=True, created_at=now, updated_at=now,
    ))
    await db.commit()
    return vid, sid


# ── _merge_vendor_suggestions ─────────────────────────────────────────────────

class TestMergeVendorSuggestions:
    def _ctx(self) -> _AgentContext:
        return _AgentContext(db=None, user_id=uuid.uuid4())  # type: ignore

    def test_adds_vendors(self):
        ctx = self._ctx()
        v = {"id": "abc", "business_name": "Test"}
        _merge_vendor_suggestions(ctx, [v])
        assert len(ctx.vendor_suggestions) == 1
        assert ctx.vendor_suggestions[0]["id"] == "abc"

    def test_deduplicates_by_id(self):
        ctx = self._ctx()
        v = {"id": "abc", "business_name": "Test"}
        _merge_vendor_suggestions(ctx, [v])
        _merge_vendor_suggestions(ctx, [v])
        assert len(ctx.vendor_suggestions) == 1

    def test_skips_vendors_without_id(self):
        ctx = self._ctx()
        _merge_vendor_suggestions(ctx, [{"business_name": "No ID"}])
        assert len(ctx.vendor_suggestions) == 0

    def test_merges_multiple(self):
        ctx = self._ctx()
        _merge_vendor_suggestions(ctx, [{"id": "a"}, {"id": "b"}])
        _merge_vendor_suggestions(ctx, [{"id": "b"}, {"id": "c"}])
        assert len(ctx.vendor_suggestions) == 3


# ── search_vendors ────────────────────────────────────────────────────────────

class TestSearchVendors:

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_vendors_and_stores_in_context(self, make_ctx):
        ctx = make_ctx()
        respx.get("http://localhost:5000/api/v1/public_vendors/search").mock(
            return_value=httpx.Response(200, json={
                "data": [
                    {"id": "v1", "business_name": "Caterer A", "city": "Lahore"},
                    {"id": "v2", "business_name": "Caterer B", "city": "Karachi"},
                ]
            })
        )
        result = await _call(search_vendors, ctx, event_type="wedding", location="Lahore")
        assert result["vendors"][0]["business_name"] == "Caterer A"
        assert len(ctx.context.vendor_suggestions) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_empty_results(self, make_ctx):
        ctx = make_ctx()
        respx.get("http://localhost:5000/api/v1/public_vendors/search").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        result = await _call(search_vendors, ctx, event_type="birthday", location="Remote")
        assert result["vendors"] == []
        assert ctx.context.vendor_suggestions == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_backend_error_returns_empty(self, make_ctx):
        ctx = make_ctx()
        respx.get("http://localhost:5000/api/v1/public_vendors/search").mock(
            return_value=httpx.Response(500, json={"error": "Server error"})
        )
        result = await _call(search_vendors, ctx, event_type="wedding", location="Lahore")
        assert result["vendors"] == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_timeout_returns_error(self, make_ctx):
        ctx = make_ctx()
        respx.get("http://localhost:5000/api/v1/public_vendors/search").mock(
            side_effect=httpx.TimeoutException("timed out")
        )
        result = await _call(search_vendors, ctx, event_type="wedding", location="Lahore")
        assert "error" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_does_not_exceed_limit(self, make_ctx):
        ctx = make_ctx()
        vendors = [{"id": str(i), "business_name": f"V{i}"} for i in range(15)]
        respx.get("http://localhost:5000/api/v1/public_vendors/search").mock(
            return_value=httpx.Response(200, json={"data": vendors})
        )
        result = await _call(search_vendors, ctx, event_type="wedding", location="Lahore", limit=5)
        assert len(result["vendors"]) <= 5


# ── get_vendor_details ────────────────────────────────────────────────────────

class TestGetVendorDetails:

    @pytest.mark.asyncio
    async def test_returns_vendor_from_db(self, make_ctx, db):
        vid, sid = await _seed_vendor(db)
        ctx = make_ctx()
        result = await _call(get_vendor_details, ctx, vendor_id=vid)
        assert result["id"] == vid
        assert result["business_name"] == "Elite Events Co"
        assert any(s["id"] == sid for s in result["services"])

    @pytest.mark.asyncio
    async def test_stores_in_context(self, make_ctx, db):
        vid, _ = await _seed_vendor(db)
        ctx = make_ctx()
        await _call(get_vendor_details, ctx, vendor_id=vid)
        assert any(v["id"] == vid for v in ctx.context.vendor_suggestions)

    @pytest.mark.asyncio
    async def test_not_found_returns_error(self, make_ctx):
        ctx = make_ctx()
        result = await _call(get_vendor_details, ctx, vendor_id=str(uuid.uuid4()))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_inactive_vendor_not_found(self, make_ctx, db):
        vid, _ = await _seed_vendor(db, status="SUSPENDED")
        ctx = make_ctx()
        result = await _call(get_vendor_details, ctx, vendor_id=vid)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_error(self, make_ctx):
        ctx = make_ctx()
        result = await _call(get_vendor_details, ctx, vendor_id="not-a-uuid")
        assert "error" in result
