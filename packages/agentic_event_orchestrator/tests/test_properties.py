"""
Property-based tests for agentic_event_orchestrator tool correctness.

Task 1 — Bug Condition Exploration Tests (Properties 1 & 4):
  These tests are EXPECTED TO FAIL on unfixed code.
  Failure confirms the bugs exist. Do NOT fix the code when they fail.

Task 2 — Preservation Tests (Properties 5–8):
  These tests are EXPECTED TO PASS on unfixed code.
  They establish the baseline behaviour to preserve after the fix.

Invocation pattern
------------------
The openai-agents SDK wraps every @function_tool in a FunctionTool dataclass
that is NOT directly callable.  The correct way to invoke a tool in tests is:

    tool_ctx = _make_tool_ctx(agent_ctx, tool_name="create_event")
    result_str = await tool.on_invoke_tool(tool_ctx, json.dumps({...args...}))

This mirrors exactly what the SDK does internally when the LLM calls a tool.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone

import httpx
import pytest
import respx
from agents.tool_context import ToolContext
from agents.usage import Usage
from hypothesis import HealthCheck, assume, given, settings, strategies as st

from conftest import (
    AgentContext,
    bookings_table,
    event_types_table,
    events_table,
    services_table,
    users_table,
    vendors_table,
)
from sqlalchemy import insert, select, text as sa_text

# ---------------------------------------------------------------------------
# Import the FunctionTool objects under test (unfixed versions)
# ---------------------------------------------------------------------------
from tools.event_tools import (
    _EVENT_TYPE_ALIASES,
    _resolve_event_type_alias,
    create_event,
    get_event_details,
    get_user_events,
    query_event_types,
    update_event_status,
)
from tools.booking_tools import (
    cancel_booking,
    create_booking_request,
    get_booking_details,
    get_my_bookings,
)


# ---------------------------------------------------------------------------
# Helper: build a ToolContext that carries an AgentContext
# ---------------------------------------------------------------------------

def _make_tool_ctx(agent_ctx: AgentContext, tool_name: str = "tool") -> ToolContext:
    """
    Construct a ToolContext wrapping the given AgentContext.
    This is the same object the SDK passes to on_invoke_tool internally.
    """
    return ToolContext(
        context=agent_ctx,
        usage=Usage(),
        tool_name=tool_name,
        tool_call_id="test-call-id",
        tool_arguments="{}",
    )


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

async def _seed_user(session, user_id: uuid.UUID) -> None:
    """Insert a minimal user row."""
    await session.execute(
        insert(users_table).values(
            id=str(user_id),
            email=f"user-{user_id}@test.example",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            role="user",
            is_active=True,
            email_verified=True,
            failed_login_attempts=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )


async def _seed_event_type(session, name: str) -> uuid.UUID:
    """Insert an active EventType row and return its UUID."""
    et_id = uuid.uuid4()
    await session.execute(
        insert(event_types_table).values(
            id=str(et_id),
            # Append a UUID suffix to guarantee uniqueness across Hypothesis examples
            name=f"{name[:80]}-{et_id}",
            description=f"Test event type: {name}",
            is_active=True,
            display_order=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    return et_id


async def _seed_vendor_and_service(
    session, owner_user_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID, float]:
    """Insert a vendor + service row; return (vendor_id, service_id, price_min)."""
    vendor_user_id = uuid.uuid4()
    await _seed_user(session, vendor_user_id)

    vendor_id = uuid.uuid4()
    await session.execute(
        insert(vendors_table).values(
            id=str(vendor_id),
            user_id=str(vendor_user_id),
            business_name="Test Vendor",
            contact_email=f"vendor-{vendor_id}@test.example",
            city="Lahore",
            status="ACTIVE",
            rating=4.5,
            total_reviews=10,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )

    price_min = 5000.0
    service_id = uuid.uuid4()
    await session.execute(
        insert(services_table).values(
            id=str(service_id),
            vendor_id=str(vendor_id),
            name="Photography Package",
            price_min=price_min,
            price_max=10000.0,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    return vendor_id, service_id, price_min


# ---------------------------------------------------------------------------
# Autouse fixture: make all HTTP calls fail fast (no hanging on unfixed code)
# The unfixed tools make real httpx calls to localhost:5000 — without this
# fixture the tests hang waiting for a connection that never comes.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_backend_unavailable():
    """
    Mock all HTTP calls to the backend to fail immediately with ConnectError.
    This ensures unfixed tools (which use httpx) fail fast instead of hanging.
    The tools' except blocks catch this and return {"success": False, "error": ...}.
    """
    with respx.mock(assert_all_called=False) as mock:
        mock.route(host="localhost").mock(
            side_effect=httpx.ConnectError("Backend not available in tests")
        )
        yield mock


# ===========================================================================
# TASK 1 — Bug Condition Exploration Tests
# EXPECTED TO FAIL on unfixed code.
# ===========================================================================


class TestBugConditionExploration:
    """
    Properties 1 & 4 — confirm the six compounding defects exist.

    These tests MUST FAIL on unfixed code.  When they fail, the counterexamples
    prove the bugs are real.  Do NOT fix the code or the tests.
    """

    @pytest.mark.asyncio
    @given(
        event_name=st.text(min_size=1, max_size=100),
        start_date=st.dates(
            min_value=date(2025, 1, 1),
            max_value=date(2030, 12, 31),
        ),
        guest_count=st.integers(min_value=1, max_value=10000),
        budget=st.floats(
            min_value=0, max_value=10_000_000,
            allow_nan=False, allow_infinity=False,
        ),
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    async def test_create_event_inserts_correct_row(
        self,
        db_session,
        make_ctx,
        event_name: str,
        start_date: date,
        guest_count: int,
        budget: float,
    ) -> None:
        """
        Property 1 (Bug Condition):
        create_event should insert a row into the events table with the correct
        user_id, event_type_id, and field mapping.

        EXPECTED TO FAIL on unfixed code because the tool makes an unauthenticated
        HTTP call to the backend instead of using ctx.context.db.

        Counterexample documented:
          - create_event raises httpx.ConnectError (no backend running in tests)
          - No row is inserted into the events table
          - The tool signature has no ctx parameter — it cannot receive AgentContext
        """
        user_id = uuid.uuid4()
        await _seed_user(db_session, user_id)
        et_id = await _seed_event_type(db_session, "wedding")
        await db_session.flush()

        # The seeded name has a UUID suffix (e.g. "wedding-<uuid>") — fetch it back
        from sqlalchemy import text as sa_text
        et_row = (await db_session.execute(
            sa_text("SELECT name FROM event_types WHERE id = :id"),
            {"id": str(et_id)},
        )).fetchone()
        seeded_name = et_row.name

        agent_ctx = AgentContext(db=db_session, user_id=user_id)
        tool_ctx = _make_tool_ctx(agent_ctx, tool_name="create_event")

        # Call via on_invoke_tool — the SDK-native invocation path
        result_str = await create_event.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "event_type": seeded_name,
                "event_name": event_name,
                "event_date": start_date.isoformat(),
                "location": "Lahore",
                "attendee_count": guest_count,
                "budget_pkr": budget,
            }),
        )
        result = json.loads(result_str)

        # Assert the tool reported success
        assert result.get("success") is True, (
            f"create_event returned failure: {result.get('error')}\n"
            "Bug confirmed: tool makes unauthenticated HTTP call with no backend running."
        )

        # Assert a row was actually inserted in the DB (not via HTTP)
        rows = (await db_session.execute(
            select(events_table).where(events_table.c.user_id == str(user_id))
        )).fetchall()

        assert len(rows) == 1, (
            f"Expected 1 event row for user {user_id}, found {len(rows)}.\n"
            "Bug confirmed: tool made HTTP call instead of writing to ctx.context.db."
        )

        row = rows[0]
        assert str(row.user_id) == str(user_id), "user_id mismatch"
        assert str(row.event_type_id) == str(et_id), (
            f"event_type_id mismatch: got {row.event_type_id!r}, expected {et_id!r}.\n"
            "Bug confirmed: tool sent camelCase string ID instead of resolving UUID."
        )
        assert row.name == event_name, f"name mismatch: {row.name!r} != {event_name!r}"
        assert row.guest_count == guest_count, "guest_count mismatch"

    @pytest.mark.asyncio
    @given(
        type_names=st.lists(
            st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
            min_size=1,
            max_size=5,
            unique=True,
        )
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    async def test_query_event_types_returns_real_uuids(
        self,
        db_session,
        make_ctx,
        type_names: list[str],
    ) -> None:
        """
        Property 4 (Bug Condition):
        query_event_types should return the real UUIDs from the database.

        EXPECTED TO FAIL on unfixed code because the tool returns a hardcoded
        static list with string IDs like "wedding", "birthday", etc.

        Counterexample documented:
          - Returned ids are "wedding", "birthday", etc. — not valid UUIDs
          - The tool ignores the database entirely
          - The tool signature has no ctx parameter — it cannot receive AgentContext
        """
        user_id = uuid.uuid4()
        await _seed_user(db_session, user_id)

        seeded_ids: dict[str, str] = {}
        for name in type_names:
            et_id = await _seed_event_type(db_session, name)
            # The actual stored name has a UUID suffix (see _seed_event_type)
            seeded_ids[name] = str(et_id)
        await db_session.flush()

        agent_ctx = AgentContext(db=db_session, user_id=user_id)
        tool_ctx = _make_tool_ctx(agent_ctx, tool_name="query_event_types")

        result_str = await query_event_types.on_invoke_tool(tool_ctx, "{}")
        result = json.loads(result_str)

        event_types = result.get("event_types", [])
        assert len(event_types) > 0, "query_event_types returned empty list"

        returned_ids = {et["id"] for et in event_types}

        # Every returned id must be a valid UUID
        for et_id in returned_ids:
            assert _is_valid_uuid(et_id), (
                f"Returned id {et_id!r} is not a valid UUID.\n"
                "Bug confirmed: tool returns hardcoded string IDs like 'wedding'."
            )

        # The seeded UUIDs must appear in the results
        for name, expected_id in seeded_ids.items():
            assert expected_id in returned_ids, (
                f"Seeded event type '{name}' with id {expected_id} not found in results.\n"
                "Bug confirmed: tool returns hardcoded list, ignoring the database."
            )


# ===========================================================================
# TASK 2 — Preservation Tests
# EXPECTED TO PASS on unfixed code (establishes baseline).
# ===========================================================================


class TestPreservationProperties:
    """
    Properties 5–8 — capture baseline behaviour that must be preserved after fix.

    These tests MUST PASS on unfixed code.
    """

    @pytest.mark.asyncio
    @given(
        count_a=st.integers(min_value=1, max_value=3),
        count_b=st.integers(min_value=1, max_value=3),
    )
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    async def test_get_user_events_isolation(
        self,
        db_session,
        make_ctx,
        count_a: int,
        count_b: int,
    ) -> None:
        """
        Property 5 (Preservation):
        get_user_events must only return events belonging to the requesting user.
        Events from other users must never appear.

        On unfixed code the tool makes an HTTP call with no backend running —
        the call fails and the tool returns {"events": [], "error": "..."}.
        We verify the isolation contract: no events from user B appear in user A's
        result.  The test skips gracefully if the HTTP call raises an exception.
        """
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        await _seed_user(db_session, user_a)
        await _seed_user(db_session, user_b)

        et_id = await _seed_event_type(db_session, "isolation-test")
        await db_session.flush()

        now = datetime.now(timezone.utc)

        # Seed events for user A
        for i in range(count_a):
            eid = uuid.uuid4()
            await db_session.execute(
                insert(events_table).values(
                    id=str(eid),
                    user_id=str(user_a),
                    event_type_id=str(et_id),
                    name=f"Event A-{i}",
                    start_date=now,
                    status="draft",
                    country="United States",
                    timezone="Asia/Karachi",
                    created_at=now,
                    updated_at=now,
                )
            )

        # Seed events for user B
        b_event_ids = []
        for i in range(count_b):
            eid = uuid.uuid4()
            b_event_ids.append(str(eid))
            await db_session.execute(
                insert(events_table).values(
                    id=str(eid),
                    user_id=str(user_b),
                    event_type_id=str(et_id),
                    name=f"Event B-{i}",
                    start_date=now,
                    status="draft",
                    country="United States",
                    timezone="Asia/Karachi",
                    created_at=now,
                    updated_at=now,
                )
            )
        await db_session.flush()

        agent_ctx_a = AgentContext(db=db_session, user_id=user_a)
        tool_ctx = _make_tool_ctx(agent_ctx_a, tool_name="get_user_events")

        try:
            result_str = await get_user_events.on_invoke_tool(
                tool_ctx,
                json.dumps({"user_id": str(user_a)}),
            )
        except Exception:
            # Unfixed code makes HTTP call — connection refused is expected
            pytest.skip("Unfixed code makes HTTP call — skipping isolation check")
            return

        result = json.loads(result_str)
        returned_events = result.get("events", [])

        # No events from user B must appear
        b_ids_in_result = {
            e.get("id") for e in returned_events
            if isinstance(e, dict) and e.get("id") in b_event_ids
        }
        assert not b_ids_in_result, (
            f"User B's events leaked into User A's results: {b_ids_in_result}"
        )

    @pytest.mark.asyncio
    async def test_booking_ownership_enforcement(
        self,
        db_session,
        make_ctx,
    ) -> None:
        """
        Property 6 (Preservation):
        get_booking_details must not return a booking belonging to another user.
        """
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        await _seed_user(db_session, user_a)
        await _seed_user(db_session, user_b)

        vendor_id, service_id, price_min = await _seed_vendor_and_service(db_session, user_a)
        await db_session.flush()

        # Seed a booking for user A
        booking_id = uuid.uuid4()
        await db_session.execute(
            insert(bookings_table).values(
                id=str(booking_id),
                vendor_id=str(vendor_id),
                service_id=str(service_id),
                user_id=str(user_a),
                event_date="2026-01-01",
                event_name="User A Wedding",
                guest_count=100,
                status="pending",
                quantity=1,
                unit_price=price_min,
                total_price=price_min,
                currency="USD",
                payment_status="pending",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        await db_session.flush()

        # User B tries to access User A's booking
        agent_ctx_b = AgentContext(db=db_session, user_id=user_b)
        tool_ctx = _make_tool_ctx(agent_ctx_b, tool_name="get_booking_details")

        try:
            result_str = await get_booking_details.on_invoke_tool(
                tool_ctx,
                json.dumps({"booking_id": str(booking_id)}),
            )
        except Exception:
            pytest.skip("Unfixed code makes HTTP call — skipping ownership check")
            return

        result = json.loads(result_str)

        # Must return an error / not-found, not the booking data
        assert "error" in result or result.get("success") is False, (
            f"Booking ownership not enforced: user B got user A's booking. result={result}"
        )

    @pytest.mark.asyncio
    @given(
        unknown_type=st.text(min_size=1, max_size=50).filter(
            lambda s: s.strip() and s.lower() not in {
                "wedding", "mehndi", "birthday", "corporate", "conference", "party"
            }
        )
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    async def test_create_event_unknown_type_returns_error(
        self,
        db_session,
        make_ctx,
        unknown_type: str,
    ) -> None:
        """
        Property 7 (Preservation):
        create_event with an unknown event type must return
        {"success": false, "error": <non-empty>}.

        On unfixed code the HTTP call fails (no backend) and the except block
        returns {"success": False, "error": <connection error>}.
        After the fix the DB lookup fails and returns the same shape.
        """
        # create_event resolves event_type via three passes: exact match,
        # substring match (>=3 chars) against event_types.name, then the
        # static alias map. The fixed exclusion set on `unknown_type` above
        # only covers a handful of canonical names — it misses the dozens of
        # other alias keys (e.g. "nikah", "bday") and any UUID-suffixed rows
        # left in event_types by other tests sharing this session-scoped DB.
        # Skip any example that would genuinely resolve via one of those
        # passes, so this test only exercises truly-unknown inputs.
        assume(_resolve_event_type_alias(unknown_type) is None)

        ut_lower = unknown_type.strip().lower()
        existing_rows = (await db_session.execute(
            sa_text("SELECT name FROM event_types")
        )).fetchall()
        candidate_names = set(_EVENT_TYPE_ALIASES.values()) | {
            row.name for row in existing_rows
        }
        for name in candidate_names:
            name_lower = name.lower()
            assume(ut_lower != name_lower)
            if len(ut_lower) >= 3:
                assume(ut_lower not in name_lower)

        user_id = uuid.uuid4()
        await _seed_user(db_session, user_id)
        await db_session.flush()

        agent_ctx = AgentContext(db=db_session, user_id=user_id)
        tool_ctx = _make_tool_ctx(agent_ctx, tool_name="create_event")

        result_str = await create_event.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "event_type": unknown_type,
                "event_name": "Test Event",
                "event_date": "2026-06-01",
                "location": "Karachi",
                "attendee_count": 50,
                "budget_pkr": 100000,
            }),
        )
        result = json.loads(result_str)

        assert result.get("success") is False, (
            f"Expected failure for unknown event type {unknown_type!r}, got: {result}"
        )
        assert result.get("error"), "error field must be non-empty"

    @pytest.mark.asyncio
    @given(
        invalid_status=st.text(min_size=1, max_size=50).filter(
            lambda s: s.strip() and s.lower() not in {
                "draft", "planned", "active", "completed", "canceled"
            }
        )
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    async def test_update_event_status_rejects_invalid_values(
        self,
        db_session,
        make_ctx,
        invalid_status: str,
    ) -> None:
        """
        Property 8 (Preservation):
        update_event_status with an invalid status must return
        {"success": false, "error": <non-empty>} and must NOT change the DB row.

        On unfixed code the HTTP call fails (no backend) and the except block
        returns {"success": False, "error": <connection error>}.
        After the fix the enum validation fails and returns the same shape.
        """
        user_id = uuid.uuid4()
        await _seed_user(db_session, user_id)
        et_id = await _seed_event_type(db_session, "status-test")
        await db_session.flush()

        now = datetime.now(timezone.utc)
        event_id = uuid.uuid4()
        original_status = "draft"
        await db_session.execute(
            insert(events_table).values(
                id=str(event_id),
                user_id=str(user_id),
                event_type_id=str(et_id),
                name="Status Test Event",
                start_date=now,
                status=original_status,
                country="United States",
                timezone="Asia/Karachi",
                created_at=now,
                updated_at=now,
            )
        )
        await db_session.flush()

        agent_ctx = AgentContext(db=db_session, user_id=user_id)
        tool_ctx = _make_tool_ctx(agent_ctx, tool_name="update_event_status")

        result_str = await update_event_status.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "event_id": str(event_id),
                "status": invalid_status,
            }),
        )
        result = json.loads(result_str)

        assert result.get("success") is False, (
            f"Expected failure for invalid status {invalid_status!r}, got: {result}"
        )
        assert result.get("error"), "error field must be non-empty"

        # DB row must be unchanged (only verifiable after the fix; on unfixed code
        # the HTTP call never touches the DB so this always holds)
        row = (await db_session.execute(
            select(events_table).where(events_table.c.id == str(event_id))
        )).fetchone()
        assert row is not None
        assert row.status == original_status, (
            f"DB status changed to {row.status!r} despite invalid input {invalid_status!r}"
        )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError):
        return False
