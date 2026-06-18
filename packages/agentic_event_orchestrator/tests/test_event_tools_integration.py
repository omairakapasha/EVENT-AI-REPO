"""Integration tests for event_tools.py — DB-direct tools via SQLite fixtures.

Uses conftest.py fixtures: db_session, make_ctx.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text as sa_text

from tools.event_tools import (
    create_event,
    get_event_details,
    get_user_events,
    query_event_types,
    update_event_status,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _call(tool, ctx, **kwargs) -> dict:
    raw = await tool.on_invoke_tool(ctx, json.dumps(kwargs))
    return json.loads(raw)


async def _seed_user(db, subscription_status: str = "free") -> uuid.UUID:
    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    await db.execute(sa_text(
        "INSERT INTO users (id, email, password_hash, role, is_active, email_verified, "
        "failed_login_attempts, subscription_status, created_at, updated_at) "
        "VALUES (:id, :email, 'x', 'user', 1, 0, 0, :sub, :now, :now)"
    ), {"id": str(user_id), "email": f"ev-{user_id}@t.com", "sub": subscription_status, "now": now})
    return user_id


async def _seed_event_type(db, name: str = "Wedding") -> str:
    et_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    # INSERT OR IGNORE — safe across tests sharing the same in-memory DB
    await db.execute(sa_text(
        "INSERT OR IGNORE INTO event_types (id, name, description, display_order, is_active, "
        "created_at, updated_at) "
        "VALUES (:id, :name, 'A special day', 1, 1, :now, :now)"
    ), {"id": et_id, "name": name, "now": now})
    return et_id


# ── query_event_types ─────────────────────────────────────────────────────────


class TestQueryEventTypes:
    @pytest.mark.asyncio
    async def test_returns_active_event_types(self, db_session, make_ctx):
        await _seed_event_type(db_session, "Wedding")
        await _seed_event_type(db_session, "Birthday Party")
        ctx = make_ctx(uuid.uuid4())

        result = await _call(query_event_types, ctx)

        assert "event_types" in result
        names = [et["name"] for et in result["event_types"]]
        assert "Wedding" in names

    @pytest.mark.asyncio
    async def test_each_type_has_id_and_name(self, db_session, make_ctx):
        await _seed_event_type(db_session, "Corporate")
        ctx = make_ctx(uuid.uuid4())

        result = await _call(query_event_types, ctx)

        for et in result["event_types"]:
            assert "id" in et
            assert "name" in et
            uuid.UUID(et["id"])  # valid UUID


# ── create_event ──────────────────────────────────────────────────────────────


class TestCreateEvent:
    @pytest.mark.asyncio
    async def test_creates_event_in_draft_status(self, db_session, make_ctx):
        user_id = await _seed_user(db_session)
        await _seed_event_type(db_session, "Mehndi")
        ctx = make_ctx(user_id)

        result = await _call(
            create_event, ctx, country="United States",
            event_type="Mehndi", event_name="Ali's Mehndi Night",
            event_date="2030-06-20", location="Lahore",
            attendee_count=200, budget_pkr=500000,
        )

        assert result["success"] is True
        assert "event_id" in result
        assert result["event"]["status"] == "draft"
        assert result["event"]["name"] == "Ali's Mehndi Night"

    @pytest.mark.asyncio
    async def test_resolves_alias_nikah_to_wedding(self, db_session, make_ctx):
        user_id = await _seed_user(db_session)
        await _seed_event_type(db_session, "Wedding")
        ctx = make_ctx(user_id)

        result = await _call(
            create_event, ctx, country="United States",
            event_type="nikah", event_name="Nikah Ceremony",
            event_date="2030-07-01",
        )

        assert result["success"] is True
        assert result["event"]["event_type"] == "Wedding"

    @pytest.mark.asyncio
    async def test_unknown_event_type_returns_error(self, db_session, make_ctx):
        user_id = await _seed_user(db_session)
        ctx = make_ctx(user_id)

        result = await _call(
            create_event, ctx, country="United States",
            event_type="absolutely_unknown_xyz", event_name="Test",
            event_date="2030-08-01",
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_date_returns_error(self, db_session, make_ctx):
        user_id = await _seed_user(db_session)
        await _seed_event_type(db_session, "Baraat")
        ctx = make_ctx(user_id)

        result = await _call(
            create_event, ctx, country="United States",
            event_type="Baraat", event_name="Baraat Ceremony",
            event_date="not-a-date",
        )

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_event_persisted_in_db(self, db_session, make_ctx):
        user_id = await _seed_user(db_session)
        await _seed_event_type(db_session, "Walima")
        ctx = make_ctx(user_id)

        result = await _call(
            create_event, ctx, country="United States",
            event_type="Walima", event_name="Reception Dinner",
            event_date="2030-09-15", location="Karachi",
            attendee_count=300, budget_pkr=1000000,
        )
        event_id = result["event_id"]

        row = await db_session.execute(
            sa_text("SELECT id, name, status, city FROM events WHERE id = :id"),
            {"id": event_id},
        )
        ev = row.fetchone()
        assert ev is not None
        assert ev.name == "Reception Dinner"
        assert ev.status == "draft"
        assert ev.city == "Karachi"

    @pytest.mark.asyncio
    async def test_datetime_iso_format_accepted(self, db_session, make_ctx):
        user_id = await _seed_user(db_session)
        await _seed_event_type(db_session, "Birthday Party")
        ctx = make_ctx(user_id)

        result = await _call(
            create_event, ctx, country="United States",
            event_type="Birthday Party", event_name="Surprise Party",
            event_date="2030-10-01T18:00:00",
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_free_plan_blocked_at_limit(self, db_session, make_ctx):
        user_id = await _seed_user(db_session, subscription_status="free")
        await _seed_event_type(db_session, "Conference")
        ctx = make_ctx(user_id)

        # Create 3 events to hit the limit
        for i in range(3):
            r = await _call(
                create_event, ctx, country="United States",
                event_type="Conference", event_name=f"Conf {i}",
                event_date="2030-11-01",
            )
            assert r["success"] is True, f"Event {i} should succeed"

        # 4th must be blocked
        result = await _call(
            create_event, ctx, country="United States",
            event_type="Conference", event_name="One Too Many",
            event_date="2030-11-01",
        )
        assert result["success"] is False
        assert "Free plan" in result["error"] or "3" in result["error"]

    @pytest.mark.asyncio
    async def test_pro_plan_not_blocked_beyond_limit(self, db_session, make_ctx):
        user_id = await _seed_user(db_session, subscription_status="pro")
        await _seed_event_type(db_session, "Party")
        ctx = make_ctx(user_id)

        for i in range(4):
            result = await _call(
                create_event, ctx, country="United States",
                event_type="Party", event_name=f"Party {i}",
                event_date="2030-12-01",
            )
            assert result["success"] is True, f"Pro user blocked at event {i}"


# ── get_user_events ───────────────────────────────────────────────────────────


class TestGetUserEvents:
    @pytest.mark.asyncio
    async def test_empty_for_new_user(self, db_session, make_ctx):
        user_id = await _seed_user(db_session)
        ctx = make_ctx(user_id)

        result = await _call(get_user_events, ctx)

        assert result["events"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_returns_created_event(self, db_session, make_ctx):
        user_id = await _seed_user(db_session)
        await _seed_event_type(db_session, "Engagement")
        ctx = make_ctx(user_id)

        cr = await _call(
            create_event, ctx, country="United States",
            event_type="Engagement", event_name="Our Engagement",
            event_date="2030-11-01",
        )

        result = await _call(get_user_events, ctx)

        ids = [e["id"] for e in result["events"]]
        assert cr["event_id"] in ids

    @pytest.mark.asyncio
    async def test_scoped_to_current_user(self, db_session, make_ctx):
        user_a_id = await _seed_user(db_session)
        user_b_id = await _seed_user(db_session)
        await _seed_event_type(db_session, "Graduation")
        ctx_a = make_ctx(user_a_id)
        ctx_b = make_ctx(user_b_id)

        cr = await _call(
            create_event, ctx_a, country="United States",
            event_type="Graduation", event_name="My Graduation",
            event_date="2030-12-01",
        )

        result_b = await _call(get_user_events, ctx_b)

        ids = [e["id"] for e in result_b["events"]]
        assert cr["event_id"] not in ids

    @pytest.mark.asyncio
    async def test_response_shape_has_required_fields(self, db_session, make_ctx):
        user_id = await _seed_user(db_session)
        await _seed_event_type(db_session, "Corporate")
        ctx = make_ctx(user_id)

        await _call(
            create_event, ctx, country="United States",
            event_type="Corporate", event_name="Annual Conference",
            event_date="2031-01-15", location="Islamabad",
            attendee_count=500, budget_pkr=2000000,
        )

        result = await _call(get_user_events, ctx)

        for ev in result["events"]:
            for field in ("id", "name", "status", "user_id"):
                assert field in ev, f"Missing field: {field}"


# ── get_event_details ─────────────────────────────────────────────────────────


class TestGetEventDetails:
    @pytest.mark.asyncio
    async def test_owner_gets_full_details(self, db_session, make_ctx):
        user_id = await _seed_user(db_session)
        await _seed_event_type(db_session, "Seminar")
        ctx = make_ctx(user_id)

        cr = await _call(
            create_event, ctx, country="United States",
            event_type="Seminar", event_name="Tech Seminar",
            event_date="2031-02-01", location="Rawalpindi",
            attendee_count=100, budget_pkr=300000,
        )

        detail = await _call(get_event_details, ctx, event_id=cr["event_id"])

        assert detail["id"] == cr["event_id"]
        assert detail["name"] == "Tech Seminar"
        assert detail["city"] == "Rawalpindi"
        assert detail["status"] == "draft"

    @pytest.mark.asyncio
    async def test_other_user_cannot_see_event(self, db_session, make_ctx):
        user_id = await _seed_user(db_session)
        other_id = await _seed_user(db_session)
        await _seed_event_type(db_session, "Workshop")
        ctx_owner = make_ctx(user_id)
        ctx_other = make_ctx(other_id)

        cr = await _call(
            create_event, ctx_owner, country="United States",
            event_type="Workshop", event_name="Private Workshop",
            event_date="2031-03-01",
        )

        result = await _call(get_event_details, ctx_other, event_id=cr["event_id"])

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_nonexistent_event_returns_error(self, db_session, make_ctx):
        ctx = make_ctx(uuid.uuid4())

        result = await _call(get_event_details, ctx, event_id=str(uuid.uuid4()))

        assert result["success"] is False


# ── update_event_status ───────────────────────────────────────────────────────


class TestUpdateEventStatus:
    @pytest.mark.asyncio
    async def test_updates_status_to_planned(self, db_session, make_ctx):
        user_id = await _seed_user(db_session)
        await _seed_event_type(db_session, "Nikah")
        ctx = make_ctx(user_id)

        cr = await _call(
            create_event, ctx, country="United States",
            event_type="Nikah", event_name="Nikah Ceremony",
            event_date="2031-04-01",
        )
        event_id = cr["event_id"]

        result = await _call(update_event_status, ctx, event_id=event_id, status="planned")

        assert result["success"] is True

        row = await db_session.execute(
            sa_text("SELECT status FROM events WHERE id = :id"), {"id": event_id}
        )
        assert row.fetchone().status == "planned"

    @pytest.mark.asyncio
    async def test_invalid_status_rejected(self, db_session, make_ctx):
        user_id = await _seed_user(db_session)
        await _seed_event_type(db_session, "Aqeeqa")
        ctx = make_ctx(user_id)

        cr = await _call(
            create_event, ctx, country="United States",
            event_type="Aqeeqa", event_name="Aqeeqa",
            event_date="2031-05-01",
        )

        result = await _call(update_event_status, ctx, event_id=cr["event_id"], status="flying")

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_other_user_cannot_update(self, db_session, make_ctx):
        user_id = await _seed_user(db_session)
        other_id = await _seed_user(db_session)
        await _seed_event_type(db_session, "Gathering")
        ctx_owner = make_ctx(user_id)
        ctx_other = make_ctx(other_id)

        cr = await _call(
            create_event, ctx_owner, country="United States",
            event_type="Gathering", event_name="Private Gathering",
            event_date="2031-06-01",
        )

        result = await _call(update_event_status, ctx_other, event_id=cr["event_id"], status="active")

        assert result["success"] is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", ["draft", "planned", "active", "completed", "canceled"])
    async def test_all_valid_statuses_accepted(self, status, db_session, make_ctx):
        user_id = await _seed_user(db_session)
        et_name = f"StatusTest-{status}"
        await _seed_event_type(db_session, et_name)
        ctx = make_ctx(user_id)

        cr = await _call(
            create_event, ctx, country="United States",
            event_type=et_name, event_name=f"Event-{status}",
            event_date="2031-07-01",
        )

        result = await _call(update_event_status, ctx, event_id=cr["event_id"], status=status)

        assert result["success"] is True
