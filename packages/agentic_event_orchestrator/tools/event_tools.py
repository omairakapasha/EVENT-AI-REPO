"""Event tools — async httpx, @function_tool, JSON string returns."""
import json
import logging
import os
import httpx
from typing import Optional

from _agents_sdk import function_tool

logger = logging.getLogger(__name__)


@function_tool
async def get_user_events(user_id: str) -> str:
    """Get all events for the current user.
    Returns a JSON string with list of events."""
    try:
        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:5000/api/v1")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{backend_url}/events", params={"userId": user_id})
            if resp.status_code == 200:
                data = resp.json()
                events = data.get("data", {}).get("items", data.get("events", []))
                return json.dumps({"events": events, "total": len(events)})
            return json.dumps({"events": [], "error": f"HTTP {resp.status_code}"})
    except Exception as e:
        return json.dumps({"error": str(e), "events": []})


@function_tool
async def create_event(
    event_type: str,
    event_name: str,
    event_date: str,
    location: str = "",
    attendee_count: int = 0,
    budget_pkr: float = 0,
    preferences: str = "",
) -> str:
    """Create a new event for planning.
    event_type must be one of: wedding, birthday, corporate, mehndi, conference, party.
    Returns a JSON string with the created event ID and details."""
    try:
        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:5000/api/v1")
        prefs = [p.strip() for p in preferences.split(",") if p.strip()] if preferences else []
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{backend_url}/events",
                json={
                    "eventType": event_type,
                    "eventName": event_name,
                    "eventDate": event_date,
                    "location": location,
                    "attendees": max(0, attendee_count),
                    "budget": max(0, budget_pkr),
                    "preferences": prefs,
                },
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                event = data.get("data", data.get("event", {}))
                return json.dumps({"success": True, "event_id": str(event.get("id", "")), "event": event})
            error = resp.json().get("message", f"HTTP {resp.status_code}")
            return json.dumps({"success": False, "error": error})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@function_tool
async def get_event_details(event_id: str) -> str:
    """Get full details of a specific event including linked vendors and status.
    Returns a JSON string with complete event details."""
    try:
        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:5000/api/v1")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{backend_url}/events/{event_id}")
            if resp.status_code == 200:
                return json.dumps(resp.json().get("data", resp.json().get("event", {})))
            return json.dumps({"error": f"Event {event_id} not found"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@function_tool
async def update_event_status(event_id: str, status: str) -> str:
    """Update the status of an event.
    status must be one of: draft, planning, quoted, approved, confirmed, completed, cancelled.
    Returns a JSON string with update result."""
    try:
        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:5000/api/v1")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.patch(
                f"{backend_url}/events/{event_id}/status",
                json={"status": status},
            )
            if resp.status_code == 200:
                return json.dumps({"success": True, "event_id": event_id, "status": status})
            error = resp.json().get("message", f"HTTP {resp.status_code}")
            return json.dumps({"success": False, "error": error})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@function_tool
async def query_event_types() -> str:
    """Get the list of supported event types on the platform.
    Returns a JSON string with available event types."""
    return json.dumps({
        "event_types": [
            {"id": "wedding", "name": "Wedding", "description": "Nikah, baraat, walima ceremonies"},
            {"id": "mehndi", "name": "Mehndi", "description": "Mehndi/henna ceremony"},
            {"id": "birthday", "name": "Birthday Party", "description": "Birthday celebrations"},
            {"id": "corporate", "name": "Corporate Event", "description": "Business meetings, conferences, team events"},
            {"id": "conference", "name": "Conference", "description": "Large-scale conferences and seminars"},
            {"id": "party", "name": "Party", "description": "General parties and social gatherings"},
        ]
    })
