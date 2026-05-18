"""
Vendor tool regression tests — Task 2 (Preservation).

These tests verify that the vendor HTTP tools continue to return correct
response shapes after the fix.  They mock httpx.AsyncClient so no real
backend is needed.

All tests MUST PASS on both unfixed and fixed code.
"""
from __future__ import annotations

import json
import uuid

import httpx
import pytest
import respx

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
# Helper: invoke a FunctionTool via on_invoke_tool
# ---------------------------------------------------------------------------

async def _call(tool, args: dict) -> dict:
    """Call a FunctionTool with the given args dict and return parsed JSON."""
    result_str = await tool.on_invoke_tool(None, json.dumps(args))
    return json.loads(result_str)


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
    """get_vendor_details returns correct shape and no HMAC headers."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_vendor_data(self):
        respx.get(f"http://localhost:5000/api/v1/public_vendors/{VENDOR_ID}").mock(
            return_value=httpx.Response(200, json=VENDOR_DETAIL_PAYLOAD)
        )
        result = await _call(get_vendor_details, {"vendor_id": VENDOR_ID})
        assert result.get("id") == VENDOR_ID
        assert result.get("business_name") == "Elite Photography"

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_hmac_headers_sent(self):
        captured_request = None

        def capture(request):
            nonlocal captured_request
            captured_request = request
            return httpx.Response(200, json=VENDOR_DETAIL_PAYLOAD)

        respx.get(f"http://localhost:5000/api/v1/public_vendors/{VENDOR_ID}").mock(
            side_effect=capture
        )
        await _call(get_vendor_details, {"vendor_id": VENDOR_ID})

        assert captured_request is not None
        headers = dict(captured_request.headers)
        hmac_headers = [k for k in headers if k.lower().startswith("x-service")]
        assert not hmac_headers, (
            f"HMAC headers found on public endpoint: {hmac_headers}."
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_not_found_returns_error(self):
        respx.get(f"http://localhost:5000/api/v1/public_vendors/{VENDOR_ID}").mock(
            return_value=httpx.Response(404)
        )
        result = await _call(get_vendor_details, {"vendor_id": VENDOR_ID})
        assert "error" in result


class TestGetVendorServices:
    """get_vendor_services returns only active services with correct shape."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_active_services_only(self):
        payload = {
            "success": True,
            "data": {
                "id": VENDOR_ID,
                "business_name": "Elite Photography",
                "services": [
                    {"id": SERVICE_ID, "name": "Wedding Package", "price_min": 50000.0,
                     "price_max": 150000.0, "capacity": 500, "is_active": True},
                    {"id": str(uuid.uuid4()), "name": "Inactive Package", "price_min": 10000.0,
                     "price_max": 20000.0, "capacity": 100, "is_active": False},
                ],
            },
        }
        respx.get(f"http://localhost:5000/api/v1/public_vendors/{VENDOR_ID}").mock(
            return_value=httpx.Response(200, json=payload)
        )
        result = await _call(get_vendor_services, {"vendor_id": VENDOR_ID})
        assert result["vendor_id"] == VENDOR_ID
        assert "services" in result
        assert len(result["services"]) == 1
        assert result["services"][0]["name"] == "Wedding Package"

    @pytest.mark.asyncio
    async def test_empty_vendor_id_returns_error(self):
        result = await _call(get_vendor_services, {"vendor_id": ""})
        assert result["vendor_id"] == ""
        assert result["services"] == []
        assert "error" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_service_shape_has_required_fields(self):
        respx.get(f"http://localhost:5000/api/v1/public_vendors/{VENDOR_ID}").mock(
            return_value=httpx.Response(200, json=VENDOR_DETAIL_PAYLOAD)
        )
        result = await _call(get_vendor_services, {"vendor_id": VENDOR_ID})
        for svc in result["services"]:
            assert "id" in svc
            assert "name" in svc
            assert "price_min" in svc
            assert "price_max" in svc
            assert "capacity" in svc


class TestCompareVendors:
    """compare_vendors returns sorted comparison list with correct shape."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_comparison_list(self):
        vid_a = str(uuid.uuid4())
        vid_b = str(uuid.uuid4())

        def detail_handler(request):
            vid = request.url.path.split("/")[-1]
            return httpx.Response(200, json={
                "success": True,
                "data": {
                    "id": vid,
                    "business_name": f"Vendor {vid[:4]}",
                    "city": "Lahore",
                    "rating": 4.5 if vid == vid_a else 4.0,
                    "services": [],
                },
            })

        respx.get(url__regex=r".*/public_vendors/.*").mock(side_effect=detail_handler)
        # Availability endpoint — mock to return empty slots (unavailable)
        respx.get(url__regex=r".*/vendors/.*/availability").mock(
            return_value=httpx.Response(200, json={"data": {"slots": []}})
        )

        result = await _call(compare_vendors, {
            "vendor_ids": [vid_a, vid_b],
            "event_date": "2027-06-01",
        })
        assert "comparison" in result
        assert len(result["comparison"]) == 2
        # Higher rated vendor should be first
        assert result["comparison"][0]["rating"] >= result["comparison"][1]["rating"]

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

    @pytest.mark.asyncio
    @respx.mock
    async def test_failed_fetch_appears_with_null_fields(self):
        vid_a = str(uuid.uuid4())
        vid_b = str(uuid.uuid4())

        # vid_a returns data, vid_b returns 404
        respx.get(f"http://localhost:5000/api/v1/public_vendors/{vid_a}").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {"id": vid_a, "business_name": "Vendor A", "rating": 4.5, "city": "Lahore", "services": []},
            })
        )
        respx.get(f"http://localhost:5000/api/v1/public_vendors/{vid_b}").mock(
            return_value=httpx.Response(404)
        )
        respx.get(url__regex=r".*/vendors/.*/availability").mock(
            return_value=httpx.Response(200, json={"data": {"slots": []}})
        )

        result = await _call(compare_vendors, {
            "vendor_ids": [vid_a, vid_b],
            "event_date": "2027-06-01",
        })
        assert "comparison" in result
        failed = next((c for c in result["comparison"] if c["vendor_id"] == vid_b), None)
        assert failed is not None
        assert failed["business_name"] is None
        assert failed["rating"] is None
