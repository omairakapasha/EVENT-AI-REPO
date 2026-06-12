"""
HTTP integration tests for Event Management routes.

Uses AsyncClient + ASGITransport with SQLite in-memory DB.
Run with: uv run pytest tests/test_event_routes.py -v
"""
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import text as sa_text

pytestmark = pytest.mark.asyncio

FUTURE = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
FUTURE2 = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
PAST = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()


# ── Auth helpers ──────────────────────────────────────────────────────────────

async def register_and_login(client: AsyncClient, db_session, email: str = None) -> str:
    email = email or f"evtest_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "TestPass123!",
        "first_name": "Event", "last_name": "Tester",
    })
    assert r.status_code == 201
    await db_session.execute(sa_text("UPDATE users SET email_verified = 1 WHERE email = :email"), {"email": email})
    await db_session.commit()
    return r.json()["access_token"]


async def create_event_type(client: AsyncClient, admin_token: str, name: str = None) -> str:
    name = name or f"EventType_{uuid.uuid4().hex[:6]}"
    r = await client.post(
        "/api/v1/events/types",
        json={"name": name, "display_order": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 201
    return r.json()["data"]["id"]


async def register_admin(client: AsyncClient, db_session) -> str:
    email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "AdminPass123!",
        "first_name": "Admin", "last_name": "User", "role": "admin",
    })
    assert r.status_code == 201
    await db_session.execute(sa_text("UPDATE users SET email_verified = 1 WHERE email = :email"), {"email": email})
    await db_session.commit()
    return r.json()["access_token"]


# ── Event Types ───────────────────────────────────────────────────────────────

async def test_list_event_types_returns_envelope(client: AsyncClient):
    r = await client.get("/api/v1/events/types")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "data" in body
    assert "meta" in body


async def test_create_event_type_admin_201(client: AsyncClient, db_session):
    token = await register_admin(client, db_session)
    r = await client.post(
        "/api/v1/events/types",
        json={"name": f"Wedding_{uuid.uuid4().hex[:4]}", "display_order": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    assert r.json()["success"] is True
    assert "id" in r.json()["data"]


async def test_create_event_type_duplicate_409(client: AsyncClient, db_session):
    token = await register_admin(client, db_session)
    name = f"UniqueType_{uuid.uuid4().hex[:6]}"
    await client.post(
        "/api/v1/events/types",
        json={"name": name, "display_order": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.post(
        "/api/v1/events/types",
        json={"name": name, "display_order": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CONFLICT_EVENT_TYPE_EXISTS"


# ── Create Event ──────────────────────────────────────────────────────────────

async def test_create_event_201(client: AsyncClient, db_session):
    token = await register_and_login(client, db_session)
    admin_token = await register_admin(client, db_session)
    et_id = await create_event_type(client, admin_token)

    r = await client.post(
        "/api/v1/events/",
        json={"event_type_id": et_id, "name": "My Wedding", "start_date": FUTURE},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["success"] is True
    assert body["data"]["name"] == "My Wedding"
    assert body["data"]["status"] == "planned"


async def test_create_event_invalid_event_type_422(client: AsyncClient, db_session):
    token = await register_and_login(client, db_session)
    r = await client.post(
        "/api/v1/events/",
        json={"event_type_id": str(uuid.uuid4()), "name": "Bad Event", "start_date": FUTURE},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_INVALID_EVENT_TYPE"


async def test_create_event_past_start_date_422(client: AsyncClient, db_session):
    token = await register_and_login(client, db_session)
    admin_token = await register_admin(client, db_session)
    et_id = await create_event_type(client, admin_token)

    r = await client.post(
        "/api/v1/events/",
        json={"event_type_id": et_id, "name": "Past Event", "start_date": PAST},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


async def test_create_event_end_before_start_422(client: AsyncClient, db_session):
    token = await register_and_login(client, db_session)
    admin_token = await register_admin(client, db_session)
    et_id = await create_event_type(client, admin_token)

    r = await client.post(
        "/api/v1/events/",
        json={
            "event_type_id": et_id, "name": "Bad Dates",
            "start_date": FUTURE2, "end_date": FUTURE,  # end before start
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


# ── List Events ───────────────────────────────────────────────────────────────

async def test_list_events_pagination_meta(client: AsyncClient, db_session):
    token = await register_and_login(client, db_session)
    admin_token = await register_admin(client, db_session)
    et_id = await create_event_type(client, admin_token)

    # Create 2 events
    for i in range(2):
        await client.post(
            "/api/v1/events/",
            json={"event_type_id": et_id, "name": f"Event {i}", "start_date": FUTURE},
            headers={"Authorization": f"Bearer {token}"},
        )

    r = await client.get("/api/v1/events/?page=1&limit=10", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "total" in body["meta"]
    assert "pages" in body["meta"]
    assert len(body["data"]) >= 2


async def test_list_events_status_filter(client: AsyncClient, db_session):
    token = await register_and_login(client, db_session)
    admin_token = await register_admin(client, db_session)
    et_id = await create_event_type(client, admin_token)

    await client.post(
        "/api/v1/events/",
        json={"event_type_id": et_id, "name": "Planned Event", "start_date": FUTURE},
        headers={"Authorization": f"Bearer {token}"},
    )

    r = await client.get(
        "/api/v1/events/?status=planned",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    for event in r.json()["data"]:
        assert event["status"] == "planned"


# ── Get Event ─────────────────────────────────────────────────────────────────

async def test_get_event_200(client: AsyncClient, db_session):
    token = await register_and_login(client, db_session)
    admin_token = await register_admin(client, db_session)
    et_id = await create_event_type(client, admin_token)

    create_r = await client.post(
        "/api/v1/events/",
        json={"event_type_id": et_id, "name": "Get Me", "start_date": FUTURE},
        headers={"Authorization": f"Bearer {token}"},
    )
    event_id = create_r.json()["data"]["id"]

    r = await client.get(f"/api/v1/events/{event_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["data"]["id"] == event_id


async def test_get_event_404_not_found(client: AsyncClient, db_session):
    token = await register_and_login(client, db_session)
    r = await client.get(f"/api/v1/events/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND_EVENT"


async def test_get_event_404_wrong_user(client: AsyncClient, db_session):
    token1 = await register_and_login(client, db_session)
    token2 = await register_and_login(client, db_session)
    admin_token = await register_admin(client, db_session)
    et_id = await create_event_type(client, admin_token)

    create_r = await client.post(
        "/api/v1/events/",
        json={"event_type_id": et_id, "name": "Private Event", "start_date": FUTURE},
        headers={"Authorization": f"Bearer {token1}"},
    )
    event_id = create_r.json()["data"]["id"]

    r = await client.get(f"/api/v1/events/{event_id}", headers={"Authorization": f"Bearer {token2}"})
    assert r.status_code == 404


# ── Update Event ──────────────────────────────────────────────────────────────

async def test_update_event_200(client: AsyncClient, db_session):
    token = await register_and_login(client, db_session)
    admin_token = await register_admin(client, db_session)
    et_id = await create_event_type(client, admin_token)

    create_r = await client.post(
        "/api/v1/events/",
        json={"event_type_id": et_id, "name": "Old Name", "start_date": FUTURE},
        headers={"Authorization": f"Bearer {token}"},
    )
    event_id = create_r.json()["data"]["id"]

    r = await client.put(
        f"/api/v1/events/{event_id}",
        json={"name": "New Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["name"] == "New Name"


async def test_update_event_terminal_status_409(client: AsyncClient, db_session):
    token = await register_and_login(client, db_session)
    admin_token = await register_admin(client, db_session)
    et_id = await create_event_type(client, admin_token)

    create_r = await client.post(
        "/api/v1/events/",
        json={"event_type_id": et_id, "name": "To Cancel", "start_date": FUTURE},
        headers={"Authorization": f"Bearer {token}"},
    )
    event_id = create_r.json()["data"]["id"]

    # Cancel it
    await client.delete(f"/api/v1/events/{event_id}", headers={"Authorization": f"Bearer {token}"})

    # Try to update
    r = await client.put(
        f"/api/v1/events/{event_id}",
        json={"name": "Updated"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "VALIDATION_INVALID_STATUS_TRANSITION"


# ── Cancel Event ──────────────────────────────────────────────────────────────

async def test_cancel_event_200(client: AsyncClient, db_session):
    token = await register_and_login(client, db_session)
    admin_token = await register_admin(client, db_session)
    et_id = await create_event_type(client, admin_token)

    create_r = await client.post(
        "/api/v1/events/",
        json={"event_type_id": et_id, "name": "Cancel Me", "start_date": FUTURE},
        headers={"Authorization": f"Bearer {token}"},
    )
    event_id = create_r.json()["data"]["id"]

    r = await client.delete(
        f"/api/v1/events/{event_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "canceled"


async def test_cancel_already_canceled_409(client: AsyncClient, db_session):
    token = await register_and_login(client, db_session)
    admin_token = await register_admin(client, db_session)
    et_id = await create_event_type(client, admin_token)

    create_r = await client.post(
        "/api/v1/events/",
        json={"event_type_id": et_id, "name": "Cancel Twice", "start_date": FUTURE},
        headers={"Authorization": f"Bearer {token}"},
    )
    event_id = create_r.json()["data"]["id"]

    await client.delete(f"/api/v1/events/{event_id}", headers={"Authorization": f"Bearer {token}"})
    r = await client.delete(f"/api/v1/events/{event_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 409


# ── Duplicate Event ───────────────────────────────────────────────────────────

async def test_duplicate_event_201(client: AsyncClient, db_session):
    token = await register_and_login(client, db_session)
    admin_token = await register_admin(client, db_session)
    et_id = await create_event_type(client, admin_token)

    create_r = await client.post(
        "/api/v1/events/",
        json={"event_type_id": et_id, "name": "Original", "start_date": FUTURE},
        headers={"Authorization": f"Bearer {token}"},
    )
    event_id = create_r.json()["data"]["id"]

    r = await client.post(
        f"/api/v1/events/{event_id}/duplicate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["success"] is True
    assert body["data"]["name"] == "Copy of Original"
    assert body["data"]["status"] == "draft"
    assert body["data"]["id"] != event_id


async def test_duplicate_event_404_not_found(client: AsyncClient, db_session):
    token = await register_and_login(client, db_session)
    r = await client.post(
        f"/api/v1/events/{uuid.uuid4()}/duplicate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


# ── Event Bookings ────────────────────────────────────────────────────────────

async def test_list_event_bookings_empty(client: AsyncClient, db_session):
    token = await register_and_login(client, db_session)
    admin_token = await register_admin(client, db_session)
    et_id = await create_event_type(client, admin_token)

    create_r = await client.post(
        "/api/v1/events/",
        json={"event_type_id": et_id, "name": "No Bookings", "start_date": FUTURE},
        headers={"Authorization": f"Bearer {token}"},
    )
    event_id = create_r.json()["data"]["id"]

    r = await client.get(
        f"/api/v1/events/{event_id}/bookings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"] == []
    assert body["meta"]["total"] == 0


# ── Admin: all events ─────────────────────────────────────────────────────────

async def test_admin_list_all_events_200(client: AsyncClient, db_session):
    admin_token = await register_admin(client, db_session)
    r = await client.get(
        "/api/v1/events/admin/all",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "total" in body["meta"]


async def test_admin_list_all_events_403_non_admin(client: AsyncClient, db_session):
    token = await register_and_login(client, db_session)
    r = await client.get(
        "/api/v1/events/admin/all",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


async def test_unauthenticated_401(client: AsyncClient):
    r = await client.get("/api/v1/events/")
    assert r.status_code == 401
