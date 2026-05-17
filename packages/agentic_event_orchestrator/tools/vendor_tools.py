"""Vendor tools — async httpx, @function_tool, JSON string returns."""
import asyncio
import json
import logging
import os
from datetime import datetime, date
import httpx
from pydantic import BaseModel
from typing import Optional

from _agents_sdk import function_tool
from service_auth import make_service_headers

logger = logging.getLogger(__name__)


# ── Internal helpers (no @function_tool — called directly by compare_vendors) ─

async def _fetch_vendor_details(vendor_id: str, backend_url: str) -> dict:
    """Raw GET to /api/v1/public_vendors/{vendor_id}.

    Returns the parsed ``data`` dict on a 200 response, or ``{}`` on any
    failure (non-200, network error, malformed JSON, etc.).  Never raises.
    """
    path = f"/api/v1/public_vendors/{vendor_id}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{backend_url}{path}",
                headers=make_service_headers("GET", path),
            )
            if resp.status_code == 200:
                return resp.json().get("data", {})
            return {}
    except Exception:
        return {}


async def _fetch_vendor_availability(
    vendor_id: str, event_date: str, backend_url: str
) -> bool:
    """Raw GET to /api/v1/vendors/{vendor_id}/availability.

    Passes ``start_date`` and ``end_date`` both set to *event_date*.
    Returns ``True`` if the ``slots`` list in the response is non-empty,
    ``False`` on any failure (non-200, network error, empty slots, etc.).
    Never raises.
    """
    path = f"/api/v1/vendors/{vendor_id}/availability"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{backend_url}{path}",
                params={"start_date": event_date, "end_date": event_date},
                headers=make_service_headers("GET", path),
            )
            if resp.status_code == 200:
                body = resp.json()
                # Backend may return {"data": {"slots": [...]}} or {"data": [...]}
                data = body.get("data", {})
                if isinstance(data, dict):
                    slots = data.get("slots", [])
                elif isinstance(data, list):
                    slots = data
                else:
                    slots = []
                return len(slots) > 0
            return False
    except Exception:
        return False


class VendorSearchInput(BaseModel):
    event_type: str
    location: str
    budget_pkr: Optional[float] = None
    category: Optional[str] = None
    limit: int = 10


@function_tool
async def search_vendors(
    event_type: str,
    location: str,
    budget_pkr: Optional[float] = None,
    category: Optional[str] = None,
    limit: int = 10,
    mode: str = "hybrid",
) -> str:
    """Search the vendor marketplace for vendors matching the given criteria.
    Use mode='semantic' for descriptive queries (e.g. 'elegant outdoor venue'),
    mode='keyword' for category labels or vendor names, mode='hybrid' (default) otherwise.
    Returns a JSON string with a vendors list and total count."""
    try:
        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:5000/api/v1")
        params = {
            "mode": mode,
            "q": f"{event_type} {location}",
            "city": location,
            "limit": min(limit, 20),
        }
        if budget_pkr:
            params["max_price"] = budget_pkr
        if category:
            params["category"] = category

        path = "/api/v1/public_vendors/search"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{backend_url}/public_vendors/search",
                params=params,
                headers=make_service_headers("GET", path),
            )
            if resp.status_code == 200:
                data = resp.json()
                vendors = data.get("data", data.get("vendors", []))
                return json.dumps({"vendors": vendors[:limit], "total": len(vendors)})
            if resp.status_code in (401, 403):
                return json.dumps({"vendors": [], "error": "Service authentication failed. Check SERVICE_SECRET configuration."})
            if resp.status_code == 503:
                try:
                    body = resp.json()
                    err = body.get("error", {})
                    if isinstance(err, dict) and err.get("code") == "AI_EMBEDDING_UNAVAILABLE":
                        return json.dumps({"vendors": [], "error": "Semantic search is temporarily unavailable. Please try keyword or hybrid search."})
                except Exception:
                    pass
            return json.dumps({"vendors": [], "error": f"Vendor service temporarily unavailable (HTTP {resp.status_code})"})
    except Exception as e:
        logger.error("search_vendors error: %s", e)
        return json.dumps({"error": str(e), "vendors": []})


@function_tool
async def get_vendor_details(vendor_id: str) -> str:
    """Get detailed information about a specific vendor including services, pricing, and contact info.
    Returns a JSON string with full vendor profile."""
    try:
        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:5000/api/v1")
        path = f"/api/v1/public_vendors/{vendor_id}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{backend_url}/public_vendors/{vendor_id}",
                headers=make_service_headers("GET", path),
            )
            if resp.status_code == 200:
                return json.dumps(resp.json().get("data", {}))
            if resp.status_code in (401, 403):
                return json.dumps({"error": "Service authentication failed. Check SERVICE_SECRET configuration."})
            return json.dumps({"error": f"Vendor service temporarily unavailable (HTTP {resp.status_code})"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@function_tool
async def check_vendor_availability(
    vendor_id: str,
    event_date: str,
    service_id: Optional[str] = None,
) -> str:
    """Check whether a vendor is available on a specific date. event_date must be ISO-8601 format YYYY-MM-DD. Returns a JSON string with vendor_id, available (bool), and slots list. Each slot has: id, vendor_id, service_id, start_date, end_date, is_available."""
    try:
        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:5000/api/v1")
        path = f"/api/v1/vendors/{vendor_id}/availability"
        params: dict = {"start_date": event_date, "end_date": event_date}
        if service_id is not None:
            params["service_id"] = service_id

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{backend_url}/vendors/{vendor_id}/availability",
                params=params,
                headers={**make_service_headers("GET", path)},
            )
            if resp.status_code == 200:
                body = resp.json()
                data = body.get("data", {})
                if isinstance(data, dict):
                    slots = data.get("slots", [])
                elif isinstance(data, list):
                    slots = data
                else:
                    slots = []
                available = len(slots) > 0
                return json.dumps({"vendor_id": vendor_id, "available": available, "slots": slots})
            if resp.status_code in (401, 403):
                return json.dumps({
                    "vendor_id": vendor_id,
                    "available": False,
                    "slots": [],
                    "error": "Service authentication failed. Check SERVICE_SECRET configuration.",
                })
            return json.dumps({
                "vendor_id": vendor_id,
                "available": False,
                "slots": [],
                "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
            })
    except httpx.ConnectError:
        return json.dumps({
            "vendor_id": vendor_id,
            "available": False,
            "slots": [],
            "error": "Could not connect to vendor service",
        })
    except httpx.TimeoutException:
        return json.dumps({
            "vendor_id": vendor_id,
            "available": False,
            "slots": [],
            "error": "Vendor service request timed out",
        })
    except Exception:
        return json.dumps({
            "vendor_id": vendor_id,
            "available": False,
            "slots": [],
            "error": "An unexpected error occurred",
        })


@function_tool
async def get_vendor_services(vendor_id: str) -> str:
    """Get the active services offered by a vendor, including pricing and capacity.
    Returns a JSON string with a services list (only active services).
    Each service has: id, name, price_min, price_max, capacity."""
    if vendor_id == "":
        return json.dumps({"vendor_id": "", "services": [], "error": "vendor_id must not be empty"})
    try:
        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:5000/api/v1")
        details = await _fetch_vendor_details(vendor_id, backend_url)
        if not details:
            return json.dumps({"vendor_id": vendor_id, "services": [], "error": "Could not retrieve vendor services"})
        raw_services = details.get("services", [])
        active_services = [
            {
                "id": s.get("id"),
                "name": s.get("name"),
                "price_min": s.get("price_min"),
                "price_max": s.get("price_max"),
                "capacity": s.get("capacity"),
            }
            for s in raw_services
            if s.get("is_active") is True
        ]
        return json.dumps({"vendor_id": vendor_id, "services": active_services})
    except Exception:
        return json.dumps({"vendor_id": vendor_id, "services": [], "error": "Could not retrieve vendor services"})


@function_tool
async def compare_vendors(
    vendor_ids: list[str],
    event_date: str,
    criteria: Optional[list[str]] = None,
) -> str:
    """Compare multiple vendors side-by-side on rating, price, and availability.
    Requires at least 2 and at most 10 vendor IDs. event_date must be ISO-8601 YYYY-MM-DD.
    Returns a JSON string with a comparison list ordered by rating descending,
    ties broken by business_name ascending. Failed vendor fetches appear with null fields."""
    try:
        # Input validation — no HTTP calls yet
        if len(vendor_ids) < 2:
            return json.dumps({"error": "At least two vendor IDs are required for comparison"})
        if len(vendor_ids) > 10:
            return json.dumps({"error": "vendor_ids must contain between 2 and 10 entries"})
        if any(v == "" for v in vendor_ids):
            return json.dumps({"error": "vendor_ids must not contain empty strings"})
        try:
            event_dt = date.fromisoformat(event_date)
            if event_dt <= datetime.utcnow().date():
                return json.dumps({"error": "event_date must be a future date"})
        except ValueError:
            return json.dumps({"error": "event_date must be a valid ISO-8601 date (YYYY-MM-DD)"})

        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:5000/api/v1")

        # Concurrent fetch of details + availability for all vendors
        detail_tasks = [_fetch_vendor_details(vid, backend_url) for vid in vendor_ids]
        avail_tasks = [_fetch_vendor_availability(vid, event_date, backend_url) for vid in vendor_ids]
        all_results = await asyncio.gather(*detail_tasks, *avail_tasks, return_exceptions=True)

        n = len(vendor_ids)
        details_results = all_results[:n]
        avail_results = all_results[n:]

        comparison = []
        for i, vendor_id in enumerate(vendor_ids):
            det = details_results[i]
            avail = avail_results[i]
            if isinstance(det, Exception) or not det:
                comparison.append({
                    "vendor_id": vendor_id,
                    "business_name": None,
                    "rating": None,
                    "price_min": None,
                    "price_max": None,
                    "available": None,
                    "city": None,
                })
            else:
                # Extract price from services if not top-level
                services = det.get("services", [])
                price_min = det.get("price_min")
                price_max = det.get("price_max")
                if price_min is None and services:
                    prices = [s.get("price_min") for s in services if s.get("price_min") is not None]
                    price_min = min(prices) if prices else None
                if price_max is None and services:
                    prices = [s.get("price_max") for s in services if s.get("price_max") is not None]
                    price_max = max(prices) if prices else None

                comparison.append({
                    "vendor_id": vendor_id,
                    "business_name": det.get("business_name"),
                    "rating": det.get("rating"),
                    "price_min": price_min,
                    "price_max": price_max,
                    "available": avail if not isinstance(avail, Exception) else None,
                    "city": det.get("city"),
                })

        # Sort: rating DESC (None last), then business_name ASC (None last)
        def sort_key(entry):
            rating = entry["rating"]
            name = entry["business_name"] or ""
            return (rating is None, -(rating or 0), name)

        comparison.sort(key=sort_key)
        return json.dumps({"comparison": comparison})
    except Exception:
        return json.dumps({"error": "An unexpected error occurred during vendor comparison"})


@function_tool
async def get_vendor_recommendations(
    event_type: str,
    location: str,
    budget_pkr: float,
) -> str:
    """Get curated vendor recommendations for an event based on type, location, and budget.
    Returns a JSON string with recommended vendors per category."""
    try:
        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:5000/api/v1")
        params = {
            "mode": "hybrid",
            "q": f"{event_type} vendors {location}",
            "city": location,
            "limit": 10,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{backend_url}/public_vendors/search", params=params)
            if resp.status_code == 200:
                data = resp.json()
                vendors = data.get("data", [])
                return json.dumps({"recommendations": vendors, "event_type": event_type, "location": location})
            return json.dumps({"recommendations": [], "error": f"Backend returned {resp.status_code}"})
    except Exception as e:
        return json.dumps({"error": str(e), "recommendations": []})
