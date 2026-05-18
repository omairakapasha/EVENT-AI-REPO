"""Vendor tools — direct SQLAlchemy DB access via RunContext[AgentContext] for details/availability, httpx for vector search."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import unicodedata
import uuid
from datetime import datetime, date, timezone
from typing import Optional
import httpx

from sqlalchemy import text as sa_text
from agents import function_tool
from agents.run_context import RunContextWrapper
from services.agent_context import AgentContext

logger = logging.getLogger(__name__)


def _err(msg: str) -> str:
    return json.dumps({"success": False, "error": msg})


# ── Indirect Injection Sanitizer (OWASP ASI06) ───────────────────────────────
# Vendor descriptions and service names come from the DB and could contain
# embedded injection instructions. Sanitize all text fields before they
# reach the agent context.

_VENDOR_INJECTION_RE = re.compile(
    r"ignore\s+(all\s+)?(previous|prior|above|your|the|my)?\s*instructions?"
    r"|disregard\s+(all\s+)?(previous|prior|above|the|my)?\s*instructions?"
    r"|forget\s+(everything|all|your|the|my)?\s*instructions?"
    r"|you\s+are\s+now\s+(a\s+)?(different|new|another|unrestricted|evil|free)"
    r"|<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\]|<<SYS>>"
    r"|###\s*(system|instruction|human|assistant)\s*:"
    r"|override\s+(safety|guardrails?|restrictions?|filters?|instructions?)"
    r"|bypass\s+(safety|guardrails?|restrictions?|filters?|instructions?)"
    r"|reveal\s+(your|the)\s+(system\s+prompt|instructions?|api.?key|password)"
    r"|cancel\s+(every|all)\s+bookings?"
    r"|delete\s+(every|all)\s+(booking|vendor|event|user|account)"
    r"|book\s+(every|all)\s+vendor",
    re.IGNORECASE,
)

_SPECIAL_TOKEN_RE = re.compile(r"(<\|[^|]{1,20}\|>|\[INST\]|\[/INST\]|<<SYS>>)", re.IGNORECASE)


def _sanitize_vendor_text(text: str, field: str = "vendor", max_length: int = 300) -> str:
    """Sanitize a vendor text field before embedding in agent context.

    Defends against OWASP ASI06 (indirect prompt injection via DB content).
    Truncates, strips special LLM tokens, and removes injection patterns.
    """
    if not text:
        return ""
    # Truncate first — prevents context stuffing
    if len(text) > max_length:
        text = text[:max_length] + "..."
    # Strip special LLM prompt tokens
    text = _SPECIAL_TOKEN_RE.sub("[removed]", text)
    # Remove injection instruction patterns
    if _VENDOR_INJECTION_RE.search(text):
        logger.warning("Indirect injection pattern removed from vendor %s: %.80s", field, text)
        text = _VENDOR_INJECTION_RE.sub("[content removed]", text)
    return text.strip()


_VENDOR_TEXT_FIELDS = ["business_name", "description", "city", "region", "name"]
_SERVICE_TEXT_FIELDS = ["name", "description"]


def _sanitize_vendor_dict(vendor: dict) -> dict:
    """Sanitize all text fields of a vendor dict (including nested services)."""
    sanitized = dict(vendor)
    for field in _VENDOR_TEXT_FIELDS:
        if field in sanitized and isinstance(sanitized[field], str):
            sanitized[field] = _sanitize_vendor_text(sanitized[field], field=field)
    if "services" in sanitized and isinstance(sanitized["services"], list):
        sanitized["services"] = [
            {
                **svc,
                **{
                    f: _sanitize_vendor_text(svc[f], field=f)
                    for f in _SERVICE_TEXT_FIELDS
                    if f in svc and isinstance(svc[f], str)
                },
            }
            for svc in sanitized["services"]
        ]
    return sanitized


# ── Direct DB Helpers ─────────────────────────────────────────────────────────

async def _db_fetch_vendor_details(db, vendor_id: str) -> dict:
    """Fetch vendor details and active services directly from the database."""
    try:
        vid = uuid.UUID(vendor_id)
    except ValueError:
        return {}

    # Vendor basic
    v_res = await db.execute(
        sa_text("""
            SELECT id, business_name, description, city, region, rating, total_reviews, status
            FROM vendors WHERE id = :vid AND status = 'ACTIVE'
        """),
        {"vid": str(vid)}
    )
    v_row = v_res.fetchone()
    if not v_row:
        return {}

    vendor_dict = dict(v_row._mapping)
    vendor_dict["id"] = str(vendor_dict["id"])
    vendor_dict["services"] = []

    # Vendor services
    s_res = await db.execute(
        sa_text("""
            SELECT id, name, description, capacity, price_min, price_max, is_active
            FROM services WHERE vendor_id = :vid AND is_active = true
        """),
        {"vid": str(vid)}
    )
    for s_row in s_res.fetchall():
        s_dict = dict(s_row._mapping)
        s_dict["id"] = str(s_dict["id"])
        vendor_dict["services"].append(s_dict)

    # Compute top-level price_min/max
    prices_min = [float(s["price_min"]) for s in vendor_dict["services"] if s["price_min"] is not None]
    prices_max = [float(s["price_max"]) for s in vendor_dict["services"] if s["price_max"] is not None]
    vendor_dict["price_min"] = min(prices_min) if prices_min else None
    vendor_dict["price_max"] = max(prices_max) if prices_max else None

    return _sanitize_vendor_dict(vendor_dict)


async def _db_fetch_vendor_availability(db, vendor_id: str, event_date: str, service_id: Optional[str] = None) -> bool:
    """Check availability. Returns True if available, False if booked/blocked/locked."""
    try:
        vid = uuid.UUID(vendor_id)
        edate = date.fromisoformat(event_date)
    except ValueError:
        return False

    sql = """
        SELECT status, locked_until 
        FROM vendor_availability 
        WHERE vendor_id = :vid AND date = :edate
    """
    params = {"vid": str(vid), "edate": edate}
    
    if service_id:
        try:
            params["sid"] = str(uuid.UUID(service_id))
            sql += " AND service_id = :sid"
        except ValueError:
            pass
            
    res = await db.execute(sa_text(sql), params)
    row = res.fetchone()
    
    # If no row exists, the slot is open (available by default in our backend)
    if not row:
        return True
        
    status = row._mapping["status"]
    if status == "available":
        return True
    if status == "locked":
        locked_until = row._mapping["locked_until"]
        if locked_until and locked_until > datetime.now(timezone.utc):
            return False # Still locked
        return True # Lock expired
        
    return False # Booked or Blocked


# ── HTTP Search Tools ─────────────────────────────────────────────────────────

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

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{backend_url}/public_vendors/search",
                params=params,
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


# ── Database Vendor Tools ─────────────────────────────────────────────────────

@function_tool
async def get_vendor_details(ctx: RunContextWrapper[AgentContext], vendor_id: str) -> str:
    """Get detailed information about a specific vendor including services, pricing, and contact info.
    Returns a JSON string with full vendor profile."""
    try:
        db = ctx.context.db
        vendor_data = await _db_fetch_vendor_details(db, vendor_id)
        if not vendor_data:
            return _err("Vendor not found or not active")
        return json.dumps(vendor_data)
    except Exception as e:
        return _err(f"Database error: {str(e)}")


@function_tool
async def check_vendor_availability(
    ctx: RunContextWrapper[AgentContext],
    vendor_id: str,
    event_date: str,
    service_id: Optional[str] = None,
) -> str:
    """Check whether a vendor is available on a specific date. event_date must be ISO-8601 format YYYY-MM-DD. Returns a JSON string with vendor_id and available (bool)."""
    try:
        db = ctx.context.db
        try:
            date.fromisoformat(event_date)
        except ValueError:
            return json.dumps({
                "vendor_id": vendor_id,
                "available": False,
                "error": "Invalid event_date. Use ISO format YYYY-MM-DD."
            })
            
        available = await _db_fetch_vendor_availability(db, vendor_id, event_date, service_id)
        return json.dumps({"vendor_id": vendor_id, "available": available})
        
    except Exception as e:
        return json.dumps({
            "vendor_id": vendor_id,
            "available": False,
            "error": f"An unexpected error occurred: {str(e)}",
        })


@function_tool
async def get_vendor_services(ctx: RunContextWrapper[AgentContext], vendor_id: str) -> str:
    """Get the active services offered by a vendor, including pricing and capacity.
    Returns a JSON string with a services list (only active services).
    Each service has: id, name, price_min, price_max, capacity."""
    if vendor_id == "":
        return json.dumps({"vendor_id": "", "services": [], "error": "vendor_id must not be empty"})
    try:
        db = ctx.context.db
        details = await _db_fetch_vendor_details(db, vendor_id)
        if not details:
            return json.dumps({"vendor_id": vendor_id, "services": [], "error": "Could not retrieve vendor services"})
            
        return json.dumps({"vendor_id": vendor_id, "services": details.get("services", [])})
    except Exception:
        return json.dumps({"vendor_id": vendor_id, "services": [], "error": "Could not retrieve vendor services"})


@function_tool
async def compare_vendors(
    ctx: RunContextWrapper[AgentContext],
    vendor_ids: list[str],
    event_date: str,
    criteria: Optional[list[str]] = None,
) -> str:
    """Compare multiple vendors side-by-side on rating, price, and availability.
    Requires at least 2 and at most 10 vendor IDs. event_date must be ISO-8601 YYYY-MM-DD.
    Returns a JSON string with a comparison list ordered by rating descending,
    ties broken by business_name ascending. Failed vendor fetches appear with null fields."""
    try:
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

        db = ctx.context.db

        # Concurrent fetch of details + availability for all vendors
        detail_tasks = [_db_fetch_vendor_details(db, vid) for vid in vendor_ids]
        avail_tasks = [_db_fetch_vendor_availability(db, vid, event_date) for vid in vendor_ids]
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
                comparison.append({
                    "vendor_id": vendor_id,
                    "business_name": det.get("business_name"),
                    "rating": det.get("rating"),
                    "price_min": det.get("price_min"),
                    "price_max": det.get("price_max"),
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
