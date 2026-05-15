"""Vendor tools — async httpx, @function_tool, JSON string returns."""
import json
import logging
import os
import httpx
from pydantic import BaseModel
from typing import Optional

from _agents_sdk import function_tool

logger = logging.getLogger(__name__)


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
) -> str:
    """Search the vendor marketplace for vendors matching the given criteria.
    Returns a JSON string with a list of matching vendors including name, category, city, price range, and rating."""
    try:
        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:5000/api/v1")
        params = {
            "mode": "hybrid",
            "q": f"{event_type} {location}",
            "city": location,
            "limit": min(limit, 20),
        }
        if budget_pkr:
            params["max_price"] = budget_pkr
        if category:
            params["category"] = category

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{backend_url}/public_vendors/search", params=params)
            if resp.status_code == 200:
                data = resp.json()
                vendors = data.get("data", data.get("vendors", []))
                return json.dumps({"vendors": vendors[:limit], "total": len(vendors)})
            return json.dumps({"vendors": [], "error": f"Backend returned {resp.status_code}"})
    except Exception as e:
        logger.error("search_vendors error: %s", e)
        return json.dumps({"error": str(e), "vendors": []})


@function_tool
async def get_vendor_details(vendor_id: str) -> str:
    """Get detailed information about a specific vendor including services, pricing, and contact info.
    Returns a JSON string with full vendor profile."""
    try:
        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:5000/api/v1")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{backend_url}/public_vendors/{vendor_id}")
            if resp.status_code == 200:
                return json.dumps(resp.json().get("data", {}))
            return json.dumps({"error": f"Vendor {vendor_id} not found"})
    except Exception as e:
        return json.dumps({"error": str(e)})


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
