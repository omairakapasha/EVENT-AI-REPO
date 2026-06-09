"""
Vendor tool regression tests — Task 2 (Preservation).

search_vendors / get_vendor_recommendations: HTTP tools — tested with respx mocks.
get_vendor_details / get_vendor_services / compare_vendors / check_vendor_availability:
  DB-direct tools — tested with in-memory SQLite via conftest fixtures.

All tests MUST PASS without a real backend or Postgres.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx
from agents.tool_context import ToolContext
from sqlalchemy import text as sa_text

from tools.vendor_tools import (
    check_vendor_availability,
    compare_vendors,
    get_vendor_details,
    get_vendor_services,
    search_vendors,
)

# ---------------------------------------------------------------------------
# Sample fixture data
# ---------------------------------------------------------------------------

VENDOR_ID = str(uuid.uuid4())
SERVICE_ID = str(uuid.uuid4())

VENDOR_DETAIL_PAYLOAD = {
    "success": True,
    "data": {
        "id": VENDOR_ID,
        "business_name": "Elite Photography",
        "city": "Lahore",
        "rating": 4.8,
        "total_reviews": 42,
        "services": [
            {
                "id": SERVICE_ID,
                "name": "Wedding Package",
                "price_min": 50000.0,
                "price_max": 150000.0,
                "capacity": 500,
                "is_active": True,
            }
        ],
    },
}

SEARCH_PAYLOAD = {
    "success": True,
    "data": [
        {
            "id": VENDOR_ID,
            "business_name": "Elite Photography",
            "city": "Lahore",
            "rating": 4.8,
        }
    ],
}

AVAILABILITY_PAYLOAD = {
    "success": True,
    "data": {
        "slots": [
            {
                "id": str(uuid.uuid4()),
                "vendor_id": VENDOR_ID,
                "start_date": "2027-06-01",
                "end_date": "2027-06-01",
                "is_available": True,
            }
        ]
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_NO_CTX = ToolContext(
    context=None,
    tool_name="test_tool",
    tool_call_id="test-call-id",
    tool_arguments="{}",
    run_config=None,
)


async def _call(tool, args: dict) -> dict:
    """Invoke an HTTP-only or validation-only FunctionTool (no AgentContext needed)."""
    result_str = await tool.on_invoke_tool(_NO_CTX, json.dumps(args))
    return json.loads(result_str)


async def _call_db(tool, ctx, args: dict) -> dict:
    """Invoke a DB-direct FunctionTool that requires a RunContextWrapper."""
    result_str = await tool.on_invoke_tool(ctx, json.dumps(args))
    return json.loads(result_str)


# ---------------------------------------------------------------------------
# DB seed helper
# ---------------------------------------------------------------------------


async def _seed_vendor(db, *, status: str = "ACTIVE") -> tuple[str, str]:
    """Insert a vendor + one active service. Returns (vendor_id, service_id)."""
    vendor_user_id = str(uuid.uuid4())
    vendor_id = str(uuid.uuid4())
    service_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    await db.execute(sa_text(
        "INSERT INTO users (id, email, password_hash, created_at, updated_at) "
        "VALUES (:id, :email, 'x', :now, :now)"
    ), {"id": vendor_user_id, "email": f"vu-{vendor_user_id}@test.com", "now": now})

    await db.execute(sa_text(
        "INSERT INTO vendors (id, user_id, business_name, contact_email, status, rating, "
        "total_reviews, created_at, updated_at) "
        "VALUES (:id, :uid, :name, :email, :status, 4.5, 10, :now, :now)"
    ), {
        "id": vendor_id, "uid": vendor_user_id,
        "name": f"Vendor {vendor_id[:4]}", "email": f"{vendor_id}@v.com",
        "status": status, "now": now,
    })

    await db.execute(sa_text(
        "INSERT INTO services (id, vendor_id, name, price_min, price_max, capacity, "
        "is_active, created_at, updated_at) "
        "VALUES (:id, :vid, 'Wedding Package', 50000.0, 150000.0, 500, 1, :now, :now)"
    ), {"id": service_id, "vid": vendor_id, "now": now})

    return vendor_id, service_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSearchVendors:
    """search_vendors returns correct shape and no HMAC headers on public endpoint."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_vendors_list(self):
        respx.get("http://localhost:5000/api/v1/public_vendors/search").mock(
            return_value=httpx.Response(200, json=SEARCH_PAYLOAD)
        )
        result = await _call(search_vendors, {
            "event_type": "wedding",
            "location": "Lahore",
            "limit": 5,
        })
        assert "vendors" in result
        assert isinstance(result["vendors"], list)
        assert "total" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_hmac_headers_sent(self):
        """Verify no X-Service-* HMAC headers are sent to the public endpoint."""
        captured_request = None

        def capture(request):
            nonlocal captured_request
            captured_request = request
            return httpx.Response(200, json=SEARCH_PAYLOAD)

        respx.get("http://localhost:5000/api/v1/public_vendors/search").mock(
            side_effect=capture
        )
        await _call(search_vendors, {"event_type": "wedding", "location": "Lahore"})

        assert captured_request is not None
        headers = dict(captured_request.headers)
        hmac_headers = [k for k in headers if k.lower().startswith("x-service")]
        assert not hmac_headers, (
            f"HMAC headers found on public endpoint: {hmac_headers}. "
            "Defect 5: dead HMAC headers must be stripped from public endpoints."
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_backend_error_returns_empty_vendors(self):
        respx.get("http://localhost:5000/api/v1/public_vendors/search").mock(
            return_value=httpx.Response(503)
        )
        result = await _call(search_vendors, {"event_type": "wedding", "location": "Lahore"})
        assert "vendors" in result
        assert result["vendors"] == []
        assert "error" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_connection_error_returns_empty_vendors(self):
        respx.get("http://localhost:5000/api/v1/public_vendors/search").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        result = await _call(search_vendors, {"event_type": "wedding", "location": "Lahore"})
        assert "vendors" in result
        assert result["vendors"] == []


class TestGetVendorDetails:
    """get_vendor_details uses DB — tested with in-memory SQLite fixtures."""

    @pytest.mark.asyncio
    async def test_returns_vendor_data(self, db_session, make_ctx):
        vendor_id, _ = await _seed_vendor(db_session)
        ctx = make_ctx(uuid.uuid4())

        result = await _call_db(get_vendor_details, ctx, {"vendor_id": vendor_id})

        assert result.get("id") == vendor_id
        assert result.get("business_name") is not None

    @pytest.mark.asyncio
    async def test_not_found_returns_error(self, db_session, make_ctx):
        ctx = make_ctx(uuid.uuid4())

        result = await _call_db(get_vendor_details, ctx, {"vendor_id": str(uuid.uuid4())})

        assert "error" in result

    @pytest.mark.asyncio
    async def test_inactive_vendor_returns_error(self, db_session, make_ctx):
        vendor_id, _ = await _seed_vendor(db_session, status="PENDING")
        ctx = make_ctx(uuid.uuid4())

        result = await _call_db(get_vendor_details, ctx, {"vendor_id": vendor_id})

        assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_error(self, db_session, make_ctx):
        ctx = make_ctx(uuid.uuid4())

        result = await _call_db(get_vendor_details, ctx, {"vendor_id": "not-a-uuid"})

        assert "error" in result


class TestGetVendorServices:
    """get_vendor_services uses DB — returns only active services."""

    @pytest.mark.asyncio
    async def test_returns_active_services(self, db_session, make_ctx):
        vendor_id, service_id = await _seed_vendor(db_session)
        ctx = make_ctx(uuid.uuid4())

        result = await _call_db(get_vendor_services, ctx, {"vendor_id": vendor_id})

        assert result["vendor_id"] == vendor_id
        assert len(result["services"]) >= 1
        assert result["services"][0]["name"] == "Wedding Package"

    @pytest.mark.asyncio
    async def test_empty_vendor_id_returns_error(self, db_session, make_ctx):
        ctx = make_ctx(uuid.uuid4())
        # empty vendor_id is validated before DB access
        result = await _call_db(get_vendor_services, ctx, {"vendor_id": ""})

        assert result["vendor_id"] == ""
        assert result["services"] == []
        assert "error" in result

    @pytest.mark.asyncio
    async def test_service_shape_has_required_fields(self, db_session, make_ctx):
        vendor_id, _ = await _seed_vendor(db_session)
        ctx = make_ctx(uuid.uuid4())

        result = await _call_db(get_vendor_services, ctx, {"vendor_id": vendor_id})

        for svc in result["services"]:
            assert "id" in svc
            assert "name" in svc
            assert "price_min" in svc
            assert "price_max" in svc
            assert "capacity" in svc


class TestCompareVendors:
    """compare_vendors uses DB — validation tests work without ctx, data tests need fixtures."""

    # Validation tests — these return before touching ctx.context.db
    @pytest.mark.asyncio
    async def test_requires_at_least_two_vendors(self):
        result = await _call(compare_vendors, {
            "vendor_ids": [VENDOR_ID],
            "event_date": "2027-06-01",
        })
        assert "error" in result

    @pytest.mark.asyncio
    async def test_rejects_past_date(self):
        result = await _call(compare_vendors, {
            "vendor_ids": [VENDOR_ID, str(uuid.uuid4())],
            "event_date": "2020-01-01",
        })
        assert "error" in result

    @pytest.mark.asyncio
    async def test_rejects_empty_vendor_id(self):
        result = await _call(compare_vendors, {
            "vendor_ids": [VENDOR_ID, ""],
            "event_date": "2027-06-01",
        })
        assert "error" in result

    # Data tests — require DB fixtures
    @pytest.mark.asyncio
    async def test_returns_comparison_list(self, db_session, make_ctx):
        vid_a, _ = await _seed_vendor(db_session)
        vid_b, _ = await _seed_vendor(db_session)
        ctx = make_ctx(uuid.uuid4())

        result = await _call_db(compare_vendors, ctx, {
            "vendor_ids": [vid_a, vid_b],
            "event_date": "2030-06-01",
        })

        assert "comparison" in result
        assert len(result["comparison"]) == 2
        ratings = [c["rating"] for c in result["comparison"] if c["rating"] is not None]
        if len(ratings) == 2:
            assert ratings[0] >= ratings[1]

    @pytest.mark.asyncio
    async def test_unknown_vendor_appears_with_null_fields(self, db_session, make_ctx):
        vid_a, _ = await _seed_vendor(db_session)
        vid_missing = str(uuid.uuid4())
        ctx = make_ctx(uuid.uuid4())

        result = await _call_db(compare_vendors, ctx, {
            "vendor_ids": [vid_a, vid_missing],
            "event_date": "2030-07-01",
        })

        assert "comparison" in result
        missing = next((c for c in result["comparison"] if c["vendor_id"] == vid_missing), None)
        assert missing is not None
        assert missing["business_name"] is None
        assert missing["rating"] is None
