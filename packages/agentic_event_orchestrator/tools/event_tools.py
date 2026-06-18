"""
Event tools — direct SQLAlchemy DB access via RunContext[AgentContext].

All five tools receive ctx: RunContext[AgentContext] as their first parameter.
They use ctx.context.db for all reads/writes and ctx.context.user_id for
ownership scoping.  No httpx calls.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from agents import function_tool
from agents.run_context import RunContextWrapper
from sqlalchemy import select, update

from services.agent_context import AgentContext

logger = logging.getLogger(__name__)

# Valid EventStatus values (mirrors backend EventStatus enum)
_VALID_STATUSES = {"draft", "planned", "active", "completed", "canceled"}

# ---------------------------------------------------------------------------
# Alias map — maps every realistic LLM variation to the canonical DB name.
# Used as a third-pass fallback when exact and partial matches both fail.
# Keys are lowercase; values are the exact name stored in event_types.name.
# ---------------------------------------------------------------------------
_EVENT_TYPE_ALIASES: dict[str, str] = {
    # Wedding & ceremonies
    "wedding": "Wedding",
    "nikah": "Wedding",
    "nikkah": "Wedding",
    "shaadi": "Wedding",
    "shadi": "Wedding",
    "marriage": "Wedding",
    "wedding ceremony": "Wedding",
    "wedding reception": "Wedding",
    "wedding event": "Wedding",
    # Mehndi
    "mehndi": "Mehndi",
    "mehendi": "Mehndi",
    "henna": "Mehndi",
    "henna night": "Mehndi",
    "mehndi night": "Mehndi",
    "mehndi ceremony": "Mehndi",
    "mehndi function": "Mehndi",
    # Baraat
    "baraat": "Baraat",
    "barat": "Baraat",
    "baraat ceremony": "Baraat",
    "barat ceremony": "Baraat",
    "groom procession": "Baraat",
    # Walima
    "walima": "Walima",
    "waleema": "Walima",
    "walima reception": "Walima",
    "walima dinner": "Walima",
    "reception": "Walima",
    # Birthday
    "birthday": "Birthday Party",
    "birthday party": "Birthday Party",
    "birthday celebration": "Birthday Party",
    "birthday event": "Birthday Party",
    "bday": "Birthday Party",
    "bday party": "Birthday Party",
    "kids birthday": "Birthday Party",
    "surprise party": "Birthday Party",
    "anniversary": "Birthday Party",
    "anniversary party": "Birthday Party",
    # Corporate
    "corporate": "Corporate",
    "corporate event": "Corporate",
    "corporate function": "Corporate",
    "office event": "Corporate",
    "office party": "Corporate",
    "team building": "Corporate",
    "team event": "Corporate",
    "business event": "Corporate",
    "company event": "Corporate",
    "product launch": "Corporate",
    "award ceremony": "Corporate",
    "gala dinner": "Corporate",
    "networking event": "Corporate",
    "annual dinner": "Corporate",
    "annual function": "Corporate",
    # Conference
    "conference": "Conference",
    "seminar": "Conference",
    "workshop": "Conference",
    "summit": "Conference",
    "symposium": "Conference",
    "expo": "Conference",
    "exhibition": "Conference",
    "trade show": "Conference",
    "webinar": "Conference",
    "panel discussion": "Conference",
    # Party
    "party": "Party",
    "social gathering": "Party",
    "get together": "Party",
    "get-together": "Party",
    "gathering": "Party",
    "celebration": "Party",
    "farewell": "Party",
    "farewell party": "Party",
    "graduation party": "Party",
    "graduation": "Party",
    "house party": "Party",
    "dinner party": "Party",
    "lunch party": "Party",
    "engagement party": "Party",
    "engagement": "Party",
    "baby shower": "Party",
    "bridal shower": "Party",
    "eid party": "Party",
    "eid celebration": "Party",
    "new year party": "Party",
    "new year": "Party",
    "halloween party": "Party",
    "christmas party": "Party",
}


def _resolve_event_type_alias(event_type: str) -> str | None:
    """Return the canonical DB name for a given event type string, or None."""
    return _EVENT_TYPE_ALIASES.get(event_type.strip().lower())


def _err(msg: str) -> str:
    return json.dumps({"success": False, "error": msg})


@function_tool
async def query_event_types(ctx: RunContextWrapper[AgentContext]) -> str:
    """Get the list of supported event types on the platform.
    Returns a JSON string with available event types and their real UUIDs."""
    try:
        from sqlalchemy import text as sa_text
        db = ctx.context.db
        result = await db.execute(
            sa_text("SELECT id, name, description FROM event_types WHERE is_active = 1 OR is_active = true ORDER BY display_order ASC")
        )
        rows = result.fetchall()
        event_types = [
            {"id": str(row.id), "name": row.name, "description": row.description or ""}
            for row in rows
        ]
        return json.dumps({"event_types": event_types})
    except Exception as e:
        logger.error("query_event_types error: %s", e)
        return json.dumps({"event_types": [], "error": str(e)})


@function_tool
async def create_event(
    ctx: RunContextWrapper[AgentContext],
    event_type: str,
    event_name: str,
    event_date: str,
    city: str = "",
    country: str = "",
    location: str = "",
    attendee_count: int = 0,
    budget_pkr: float = 0,
    preferences: str = "",
) -> str:
    """Create a new event for planning.
    event_type accepts any common name or alias, e.g.:
      'Wedding', 'Nikah', 'Shaadi', 'Mehndi', 'Henna', 'Baraat', 'Barat',
      'Walima', 'Reception', 'Birthday', 'Birthday Party', 'Anniversary',
      'Corporate', 'Team Building', 'Annual Dinner', 'Conference', 'Seminar',
      'Workshop', 'Party', 'Gathering', 'Engagement', 'Graduation', etc.

    Location: ALWAYS capture `country` (required) and `city` for the event. If the
    user has not given a country, ask before creating. `location` is accepted as a
    legacy free-text fallback (used as the city when `city` is empty).
    Returns a JSON string with the created event ID and details."""
    try:
        from sqlalchemy import text as sa_text
        db = ctx.context.db
        user_id = ctx.context.user_id

        # Resolve event_type name → UUID (three-pass lookup)
        # Pass 1: exact case-insensitive match
        et_result = await db.execute(
            sa_text(
                "SELECT id, name FROM event_types "
                "WHERE LOWER(name) = LOWER(:name) AND (is_active = 1 OR is_active = true) "
                "LIMIT 1"
            ),
            {"name": event_type.strip()},
        )
        et_row = et_result.fetchone()

        # Pass 2: partial/contains match (e.g. "birthday" → "Birthday Party")
        # Skip for very short strings to avoid false positives (e.g. "0" matching any type with a digit)
        if not et_row and len(event_type.strip()) >= 3:
            et_result = await db.execute(
                sa_text(
                    "SELECT id, name FROM event_types "
                    "WHERE LOWER(name) LIKE LOWER(:pattern) AND (is_active = 1 OR is_active = true) "
                    "ORDER BY display_order ASC LIMIT 1"
                ),
                {"pattern": f"%{event_type.strip()}%"},
            )
            et_row = et_result.fetchone()

        # Pass 3: alias map (e.g. "nikah" → "Wedding", "team building" → "Corporate")
        if not et_row:
            canonical = _resolve_event_type_alias(event_type)
            if canonical:
                et_result = await db.execute(
                    sa_text(
                        "SELECT id, name FROM event_types "
                        "WHERE LOWER(name) = LOWER(:name) AND (is_active = 1 OR is_active = true) "
                        "LIMIT 1"
                    ),
                    {"name": canonical},
                )
                et_row = et_result.fetchone()

        if not et_row:
            # List available types so the agent can recover
            all_types = await db.execute(
                sa_text("SELECT name FROM event_types WHERE is_active = 1 OR is_active = true ORDER BY display_order ASC")
            )
            available = [r.name for r in all_types.fetchall()]
            return _err(
                f"Unknown event type '{event_type}'. "
                f"Available types: {', '.join(available) if available else 'none — run seed script first'}. "
                "Use query_event_types to see available types."
            )
        event_type_id = str(et_row.id)

        # Parse event_date → timezone-aware datetime
        try:
            if "T" in event_date:
                start_date = datetime.fromisoformat(event_date)
            else:
                start_date = datetime.strptime(event_date, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
        except ValueError:
            return _err(f"Invalid event_date '{event_date}'. Use ISO format: YYYY-MM-DD.")

        # Enforce free-plan event limit (mirrors EventService._enforce_free_plan_event_limit)
        sub_result = await db.execute(
            sa_text("SELECT subscription_status FROM users WHERE id = :uid LIMIT 1"),
            {"uid": str(user_id)},
        )
        sub_row = sub_result.fetchone()
        if sub_row and sub_row.subscription_status == "free":
            count_result = await db.execute(
                sa_text(
                    "SELECT COUNT(*) FROM events "
                    "WHERE user_id = :uid AND status != 'canceled'"
                ),
                {"uid": str(user_id)},
            )
            event_count = count_result.scalar() or 0
            if event_count >= 3:
                return _err(
                    "Free plan allows only 3 active events. "
                    "Upgrade to Pro for unlimited events."
                )

        # Resolve location: prefer explicit city; fall back to legacy free-text location.
        resolved_city = (city or location).strip() or None
        resolved_country = country.strip()
        if not resolved_country:
            return _err(
                "Missing country for the event. Ask the user which country the event "
                "is in (and the city, if known), then call create_event again."
            )

        event_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        await db.execute(
            sa_text(
                "INSERT INTO events "
                "(id, user_id, event_type_id, name, start_date, city, guest_count, "
                " budget, status, country, timezone, created_at, updated_at) "
                "VALUES (:id, :user_id, :event_type_id, :name, :start_date, :city, "
                "        :guest_count, :budget, :status, :country, :timezone, :created_at, :updated_at)"
            ),
            {
                "id": event_id,
                "user_id": str(user_id),
                "event_type_id": event_type_id,
                "name": event_name,
                "start_date": start_date,
                "city": resolved_city,
                "guest_count": max(0, attendee_count) or None,
                "budget": max(0.0, budget_pkr) or None,
                "status": "draft",
                "country": resolved_country,
                "timezone": "UTC",
                "created_at": now,
                "updated_at": now,
            },
        )
        await db.flush()
        await db.commit()

        return json.dumps({
            "success": True,
            "event_id": event_id,
            "event": {
                "id": event_id,
                "name": event_name,
                "event_type": et_row.name,
                "start_date": start_date.isoformat(),
                "city": resolved_city,
                "country": resolved_country,
                "guest_count": max(0, attendee_count) or None,
                "budget": max(0.0, budget_pkr) or None,
                "status": "draft",
            },
        })
    except Exception as e:
        logger.error("create_event error: %s", e)
        return _err(str(e))


@function_tool
async def get_user_events(ctx: RunContextWrapper[AgentContext]) -> str:
    """Get all events for the current user.
    Returns a JSON string with list of events."""
    try:
        from sqlalchemy import text as sa_text
        db = ctx.context.db
        user_id = ctx.context.user_id

        result = await db.execute(
            sa_text(
                "SELECT id, name, status, start_date, city, guest_count, budget "
                "FROM events WHERE user_id = :user_id ORDER BY created_at DESC"
            ),
            {"user_id": str(user_id)},
        )
        rows = result.fetchall()
        events = [
            {
                "id": str(row.id),
                "name": row.name,
                "status": row.status,
                "start_date": str(row.start_date) if row.start_date else None,
                "city": row.city,
                "guest_count": row.guest_count,
                "budget": row.budget,
                "user_id": str(user_id),
            }
            for row in rows
        ]
        return json.dumps({"events": events, "total": len(events)})
    except Exception as e:
        logger.error("get_user_events error: %s", e)
        return json.dumps({"events": [], "error": str(e)})


@function_tool
async def get_event_details(
    ctx: RunContextWrapper[AgentContext],
    event_id: str,
) -> str:
    """Get full details of a specific event.
    Returns a JSON string with complete event details."""
    try:
        from sqlalchemy import text as sa_text
        db = ctx.context.db
        user_id = ctx.context.user_id

        result = await db.execute(
            sa_text(
                "SELECT id, user_id, event_type_id, name, status, start_date, "
                "       city, guest_count, budget, description "
                "FROM events WHERE id = :event_id AND user_id = :user_id LIMIT 1"
            ),
            {"event_id": event_id, "user_id": str(user_id)},
        )
        row = result.fetchone()
        if not row:
            return _err(f"Event {event_id} not found or does not belong to you.")

        return json.dumps({
            "id": str(row.id),
            "user_id": str(row.user_id),
            "event_type_id": str(row.event_type_id),
            "name": row.name,
            "status": row.status,
            "start_date": str(row.start_date) if row.start_date else None,
            "city": row.city,
            "guest_count": row.guest_count,
            "budget": row.budget,
            "description": row.description,
        })
    except Exception as e:
        logger.error("get_event_details error: %s", e)
        return _err(str(e))


@function_tool
async def update_event_status(
    ctx: RunContextWrapper[AgentContext],
    event_id: str,
    status: str,
) -> str:
    """Update the status of an event.
    status must be one of: draft, planned, active, completed, canceled.
    Returns a JSON string with update result."""
    try:
        from sqlalchemy import text as sa_text
        db = ctx.context.db
        user_id = ctx.context.user_id

        # Validate status
        normalized = status.strip().lower()
        if normalized not in _VALID_STATUSES:
            return _err(
                f"Invalid status '{status}'. "
                f"Must be one of: {', '.join(sorted(_VALID_STATUSES))}."
            )

        # Verify ownership
        check = await db.execute(
            sa_text("SELECT id FROM events WHERE id = :event_id AND user_id = :user_id LIMIT 1"),
            {"event_id": event_id, "user_id": str(user_id)},
        )
        if not check.fetchone():
            return _err(f"Event {event_id} not found or does not belong to you.")

        now = datetime.now(timezone.utc)
        await db.execute(
            sa_text(
                "UPDATE events SET status = :status, updated_at = :updated_at "
                "WHERE id = :event_id AND user_id = :user_id"
            ),
            {"status": normalized, "updated_at": now, "event_id": event_id, "user_id": str(user_id)},
        )
        await db.flush()
        await db.commit()

        return json.dumps({"success": True, "event_id": event_id, "status": normalized})
    except Exception as e:
        logger.error("update_event_status error: %s", e)
        return _err(str(e))
