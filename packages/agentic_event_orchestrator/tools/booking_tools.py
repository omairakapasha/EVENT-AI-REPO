"""Booking tools — async httpx, @function_tool, JSON string returns."""
import json
import logging
import os
import httpx
from typing import Optional

from _agents_sdk import function_tool

logger = logging.getLogger(__name__)


@function_tool
async def create_booking_request(
    vendor_id: str,
    service_id: str,
    event_date: str,
    event_name: str,
    guest_count: int,
    notes: str = "",
) -> str:
    """Create a booking inquiry request for a vendor service.
    IMPORTANT: Only call this AFTER showing the user a summary and receiving explicit confirmation.
    Returns a JSON string with booking_id and status."""
    try:
        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:5000/api/v1")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{backend_url}/bookings",
                json={
                    "vendorId": vendor_id,
                    "serviceId": service_id,
                    "eventDate": event_date,
                    "eventName": event_name,
                    "guestCount": max(1, min(guest_count, 10000)),
                    "notes": notes[:500],
                },
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                booking = data.get("data", data.get("booking", {}))
                return json.dumps({
                    "success": True,
                    "booking_id": str(booking.get("id", "")),
                    "status": booking.get("status", "pending"),
                    "message": "Booking request created successfully. The vendor will respond within 24 hours.",
                })
            error = resp.json().get("message", f"HTTP {resp.status_code}")
            return json.dumps({"success": False, "error": error})
    except Exception as e:
        logger.error("create_booking_request error: %s", e)
        return json.dumps({"success": False, "error": str(e)})


@function_tool
async def get_my_bookings(user_id: str) -> str:
    """Get all bookings for the current user.
    Returns a JSON string with list of bookings including status and vendor details."""
    try:
        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:5000/api/v1")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{backend_url}/bookings", params={"userId": user_id})
            if resp.status_code == 200:
                data = resp.json()
                bookings = data.get("data", {}).get("items", data.get("bookings", []))
                return json.dumps({"bookings": bookings, "total": len(bookings)})
            return json.dumps({"bookings": [], "error": f"HTTP {resp.status_code}"})
    except Exception as e:
        return json.dumps({"error": str(e), "bookings": []})


@function_tool
async def get_booking_details(booking_id: str) -> str:
    """Get full details of a specific booking including vendor info and status.
    Returns a JSON string with complete booking details."""
    try:
        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:5000/api/v1")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{backend_url}/bookings/{booking_id}")
            if resp.status_code == 200:
                return json.dumps(resp.json().get("data", {}))
            return json.dumps({"error": f"Booking {booking_id} not found"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@function_tool
async def cancel_booking(booking_id: str, reason: str = "Cancelled by user") -> str:
    """Cancel an existing booking. Only call after explicit user confirmation.
    Returns a JSON string with cancellation status."""
    try:
        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:5000/api/v1")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.patch(
                f"{backend_url}/bookings/{booking_id}/cancel",
                json={"reason": reason[:300]},
            )
            if resp.status_code == 200:
                return json.dumps({"success": True, "booking_id": booking_id, "message": "Booking cancelled."})
            error = resp.json().get("message", f"HTTP {resp.status_code}")
            return json.dumps({"success": False, "error": error})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
