"""
Tests for Notification System (Module 010 gaps).

Run with: uv run pytest tests/test_notifications.py -v
"""
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import text as sa_text

from src.models.notification import Notification, NotificationType
from src.services.notification_service import NotificationService, _EVENT_MAP

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────

async def register_and_login(client, db_session, email=None):
    email = email or f"notif_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "TestPass123!",
        "first_name": "Notif", "last_name": "User",
    })
    assert r.status_code == 201
    await db_session.execute(sa_text("UPDATE users SET email_verified = 1 WHERE email = :email"), {"email": email})
    await db_session.commit()
    return r.json()["access_token"], email


def make_mock_session():
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    # Mock execute to return a result object with scalar_one_or_none
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    session.execute = AsyncMock(return_value=mock_result)
    return session


# ── Service: handle() for booking events ─────────────────────────────────────

@pytest.mark.parametrize("event_type", [
    "booking.created", "booking.confirmed", "booking.cancelled",
    "booking.completed", "booking.rejected", "booking.status_changed",
])
async def test_handle_booking_events_creates_notification(event_type):
    svc = NotificationService()
    user_id = uuid.uuid4()
    session = make_mock_session()

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock):
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            await svc.handle(
                event_type=event_type,
                payload={"booking_id": str(uuid.uuid4()), "new_status": "confirmed"},
                user_id=user_id,
                session=session,
            )

    session.add.assert_called()


# ── Service: handle() for event domain events ─────────────────────────────────

@pytest.mark.parametrize("event_type,payload_extra", [
    ("event.created",        {"name": "My Wedding"}),
    ("event.status_changed", {"name": "My Wedding", "new_status": "active"}),
    ("event.cancelled",      {"name": "My Wedding"}),
])
async def test_handle_event_domain_events(event_type, payload_extra):
    svc = NotificationService()
    user_id = uuid.uuid4()
    session = make_mock_session()

    payload = {"user_id": str(user_id), "event_id": str(uuid.uuid4()), **payload_extra}

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock):
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            await svc.handle(event_type=event_type, payload=payload, session=session)

    session.add.assert_called_once()


# ── Service: handle() for vendor domain events ────────────────────────────────

@pytest.mark.parametrize("event_type", ["vendor.approved", "vendor.rejected"])
async def test_handle_vendor_domain_events(event_type):
    """vendor.approved / vendor.rejected → notify via _VENDOR_ID_EVENTS path (ORM lookup on vendor_id)."""
    svc = NotificationService()
    vendor_user_id = uuid.uuid4()
    session = make_mock_session()

    mock_vendor = MagicMock()
    mock_vendor.user_id = vendor_user_id
    session.get = AsyncMock(return_value=mock_vendor)

    # Real approval_service payload: vendor_id + business_name, NO user_id
    payload = {"vendor_id": str(uuid.uuid4()), "business_name": "Test Vendor"}

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock):
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=False):
                with patch("src.services.notification_service.NotificationService._send_email", new_callable=AsyncMock):
                    await svc.handle(event_type=event_type, payload=payload, session=session)

    session.add.assert_called_once()
    assert session.add.call_args[0][0].user_id == vendor_user_id


async def test_handle_unknown_event_type_is_noop():
    svc = NotificationService()
    session = make_mock_session()
    await svc.handle(event_type="unknown.event", payload={}, session=session)
    session.add.assert_not_called()


async def test_handle_missing_user_id_logs_warning():
    svc = NotificationService()
    session = make_mock_session()
    # event.created without user_id in payload
    await svc.handle(event_type="event.created", payload={"event_id": str(uuid.uuid4())}, session=session)
    session.add.assert_not_called()


async def test_handle_preference_disabled_skips_notification():
    svc = NotificationService()
    user_id = uuid.uuid4()
    session = make_mock_session()

    payload = {"user_id": str(user_id), "event_id": str(uuid.uuid4()), "name": "Test"}

    with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=False):
        await svc.handle(event_type="event.created", payload=payload, session=session)

    session.add.assert_not_called()


# ── Route: list notifications ─────────────────────────────────────────────────

async def test_list_notifications_returns_envelope(client, db_session):
    token, _ = await register_and_login(client, db_session)
    r = await client.get("/api/v1/notifications/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "data" in body
    assert "meta" in body
    assert "total" in body["meta"]


async def test_list_notifications_unread_only(client, db_session):
    token, _ = await register_and_login(client, db_session)
    r = await client.get(
        "/api/v1/notifications/?unread_only=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["success"] is True


async def test_unread_count_returns_envelope(client, db_session):
    token, _ = await register_and_login(client, db_session)
    r = await client.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["data"]["count"] == 0


async def test_mark_all_read(client, db_session):
    token, _ = await register_and_login(client, db_session)
    r = await client.patch("/api/v1/notifications/read-all", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["success"] is True


# ── Route: mark single read ───────────────────────────────────────────────────

async def test_mark_read_returns_envelope(client, db_session):
    token, _ = await register_and_login(client, db_session)

    # Get user_id from /me
    me_r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = uuid.UUID(me_r.json()["id"])

    # Insert a notification directly
    notif = Notification(
        user_id=user_id,
        type=NotificationType.system,
        title="Test",
        body="Test body",
        data={},
    )
    db_session.add(notif)
    await db_session.commit()
    await db_session.refresh(notif)

    r = await client.patch(
        f"/api/v1/notifications/{notif.id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "data" in body
    assert body["data"]["is_read"] is True


# ── Route: delete single notification ────────────────────────────────────────

async def test_delete_notification_success(client, db_session):
    token, _ = await register_and_login(client, db_session)
    me_r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = uuid.UUID(me_r.json()["id"])

    notif = Notification(user_id=user_id, type=NotificationType.system, title="Del", body="body", data={})
    db_session.add(notif)
    await db_session.commit()
    await db_session.refresh(notif)

    r = await client.delete(f"/api/v1/notifications/{notif.id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["success"] is True


async def test_delete_notification_not_found(client, db_session):
    token, _ = await register_and_login(client, db_session)
    r = await client.delete(
        f"/api/v1/notifications/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND_NOTIFICATION"


async def test_delete_notification_forbidden(client, db_session):
    token1, _ = await register_and_login(client, db_session)
    token2, _ = await register_and_login(client, db_session)

    me_r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})
    user_id = uuid.UUID(me_r.json()["id"])

    notif = Notification(user_id=user_id, type=NotificationType.system, title="Private", body="body", data={})
    db_session.add(notif)
    await db_session.commit()
    await db_session.refresh(notif)

    r = await client.delete(f"/api/v1/notifications/{notif.id}", headers={"Authorization": f"Bearer {token2}"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "AUTH_FORBIDDEN"


# ── Route: delete read notifications ─────────────────────────────────────────

async def test_delete_read_notifications(client, db_session):
    token, _ = await register_and_login(client, db_session)
    me_r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = uuid.UUID(me_r.json()["id"])

    # Insert 2 read + 1 unread
    for i in range(2):
        n = Notification(user_id=user_id, type=NotificationType.system, title=f"Read {i}", body="b", data={}, is_read=True)
        db_session.add(n)
    n_unread = Notification(user_id=user_id, type=NotificationType.system, title="Unread", body="b", data={}, is_read=False)
    db_session.add(n_unread)
    await db_session.commit()

    r = await client.delete("/api/v1/notifications/read", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["data"]["deleted"] == 2


async def test_delete_read_notifications_zero(client, db_session):
    token, _ = await register_and_login(client, db_session)
    r = await client.delete("/api/v1/notifications/read", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["data"]["deleted"] == 0


# ── Route: preferences ────────────────────────────────────────────────────────

async def test_get_preferences_empty(client, db_session):
    token, _ = await register_and_login(client, db_session)
    r = await client.get("/api/v1/notifications/preferences", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["data"] == []


async def test_put_preference(client, db_session):
    token, _ = await register_and_login(client, db_session)
    r = await client.put(
        "/api/v1/notifications/preferences/booking_created",
        json={"enabled": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["enabled"] is False
    assert r.json()["data"]["notification_type"] == "booking_created"


async def test_put_preference_invalid_type_422(client, db_session):
    token, _ = await register_and_login(client, db_session)
    r = await client.put(
        "/api/v1/notifications/preferences/invalid_type_xyz",
        json={"enabled": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


async def test_unauthenticated_401(client):
    r = await client.get("/api/v1/notifications/")
    assert r.status_code == 401


# ── Deduplication tests (7.2) ─────────────────────────────────────────────────

async def test_deduplication_skips_duplicate_within_window():
    """Test that duplicate notifications are skipped within 5-minute window."""
    svc = NotificationService()
    user_id = uuid.uuid4()
    booking_id = str(uuid.uuid4())
    session = make_mock_session()

    # Mock existing notification with same booking_id
    existing_notif = Notification(
        user_id=user_id,
        type=NotificationType.booking_confirmed,
        title="Test",
        body="Body",
        data={"booking_id": booking_id},
    )

    with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
        with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=True):
            await svc.handle(
                event_type="booking.confirmed",
                payload={"booking_id": booking_id},
                user_id=user_id,
                session=session,
            )

    session.add.assert_not_called()


async def test_deduplication_allows_after_window():
    """Test that notifications are allowed after dedup window expires."""
    svc = NotificationService()
    user_id = uuid.uuid4()
    booking_id = str(uuid.uuid4())
    session = make_mock_session()

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock):
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=False):
                with patch("src.services.notification_service.NotificationService._send_email", new_callable=AsyncMock):
                    await svc.handle(
                        event_type="booking.confirmed",
                        payload={"booking_id": booking_id},
                        user_id=user_id,
                        session=session,
                    )

    session.add.assert_called()


# ── Email integration tests (7.1) ────────────────────────────────────────────

async def test_email_sent_on_booking_event():
    """Test that email is queued when booking event fires."""
    svc = NotificationService()
    user_id = uuid.uuid4()
    booking_id = str(uuid.uuid4())
    session = make_mock_session()

    # Mock booking with user
    mock_booking = MagicMock()
    mock_booking.user_id = user_id
    mock_booking.vendor_id = None
    mock_booking.event_name = "Test Event"
    mock_booking.event_date = "2026-05-15"
    session.get = AsyncMock(return_value=mock_booking)

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock):
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=False):
                with patch("src.services.notification_service.NotificationService._send_email", new_callable=AsyncMock) as mock_email:
                    await svc.handle(
                        event_type="booking.confirmed",
                        payload={"booking_id": booking_id},
                        user_id=user_id,
                        session=session,
                    )

    mock_email.assert_called_once()


# ── booking.counter_offered — vendor notification ─────────────────────────────

async def test_handle_counter_offered_notifies_vendor():
    """booking.counter_offered sends notification to VENDOR, not customer."""
    svc = NotificationService()
    vendor_user_id = uuid.uuid4()
    customer_user_id = uuid.uuid4()
    booking_id = str(uuid.uuid4())
    session = make_mock_session()

    mock_vendor = MagicMock()
    mock_vendor.user_id = vendor_user_id

    mock_booking = MagicMock()
    mock_booking.user_id = customer_user_id
    mock_booking.vendor_id = uuid.uuid4()
    mock_booking.event_name = "Wedding"
    mock_booking.event_date = "2026-12-01"

    # session.get: first call returns booking, second returns vendor
    session.get = AsyncMock(side_effect=[mock_booking, mock_vendor])

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock) as mock_sse:
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=False):
                with patch("src.services.notification_service.NotificationService._send_email", new_callable=AsyncMock):
                    await svc.handle(
                        event_type="booking.counter_offered",
                        payload={
                            "booking_id": booking_id,
                            "quote_id": str(uuid.uuid4()),
                            "proposed_total": 80000.0,
                        },
                        user_id=customer_user_id,
                        session=session,
                    )

    # Notification row added for vendor
    session.add.assert_called_once()
    added_notif = session.add.call_args[0][0]
    assert added_notif.user_id == vendor_user_id
    assert added_notif.type == NotificationType.booking_counter_offered

    # SSE pushed to vendor, not customer
    mock_sse.assert_called_once()
    sse_recipient = mock_sse.call_args[0][0]
    assert sse_recipient == vendor_user_id


async def test_handle_counter_offered_skips_when_vendor_preference_disabled():
    svc = NotificationService()
    vendor_user_id = uuid.uuid4()
    session = make_mock_session()

    mock_vendor = MagicMock()
    mock_vendor.user_id = vendor_user_id

    mock_booking = MagicMock()
    mock_booking.user_id = uuid.uuid4()
    mock_booking.vendor_id = uuid.uuid4()
    session.get = AsyncMock(side_effect=[mock_booking, mock_vendor])

    with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=False):
        await svc.handle(
            event_type="booking.counter_offered",
            payload={"booking_id": str(uuid.uuid4()), "proposed_total": 50000.0},
            user_id=uuid.uuid4(),
            session=session,
        )

    session.add.assert_not_called()


async def test_handle_counter_offered_not_in_event_map_guard():
    """booking.counter_offered must be in _EVENT_MAP — if accidentally removed, handle() is a no-op."""
    from src.services.notification_service import _EVENT_MAP
    assert "booking.counter_offered" in _EVENT_MAP


# ── Negotiation loop gap tests ────────────────────────────────────────────────

async def test_handle_booking_quoted_notifies_customer():
    """booking.quoted → customer (booking.user_id) receives notification."""
    svc = NotificationService()
    customer_user_id = uuid.uuid4()
    session = make_mock_session()

    mock_booking = MagicMock()
    mock_booking.user_id = customer_user_id
    mock_booking.vendor_id = uuid.uuid4()
    mock_booking.event_name = "Birthday"
    mock_booking.event_date = "2026-12-15"

    session.get = AsyncMock(return_value=mock_booking)

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock) as mock_sse:
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=False):
                with patch("src.services.notification_service.NotificationService._send_email", new_callable=AsyncMock):
                    await svc.handle(
                        event_type="booking.quoted",
                        payload={"booking_id": str(uuid.uuid4()), "quote_id": str(uuid.uuid4())},
                        user_id=uuid.uuid4(),
                        session=session,
                    )

    session.add.assert_called_once()
    added_notif = session.add.call_args[0][0]
    assert added_notif.user_id == customer_user_id
    assert added_notif.type == NotificationType.booking_quoted

    mock_sse.assert_called_once()
    assert mock_sse.call_args[0][0] == customer_user_id


async def test_handle_booking_accepted_customer_actor_notifies_vendor():
    """booking.accepted with actor=customer → vendor receives notification, not customer."""
    svc = NotificationService()
    customer_user_id = uuid.uuid4()
    vendor_user_id = uuid.uuid4()
    session = make_mock_session()

    mock_booking = MagicMock()
    mock_booking.user_id = customer_user_id
    mock_booking.vendor_id = uuid.uuid4()
    mock_booking.event_name = "Wedding"
    mock_booking.event_date = "2026-12-20"

    mock_vendor = MagicMock()
    mock_vendor.user_id = vendor_user_id

    session.get = AsyncMock(side_effect=[mock_booking, mock_vendor])

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock) as mock_sse:
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=False):
                with patch("src.services.notification_service.NotificationService._send_email", new_callable=AsyncMock):
                    await svc.handle(
                        event_type="booking.accepted",
                        payload={"booking_id": str(uuid.uuid4()), "quote_id": str(uuid.uuid4()), "actor": "customer"},
                        user_id=customer_user_id,
                        session=session,
                    )

    session.add.assert_called_once()
    added_notif = session.add.call_args[0][0]
    assert added_notif.user_id == vendor_user_id
    assert added_notif.type == NotificationType.booking_accepted

    mock_sse.assert_called_once()
    assert mock_sse.call_args[0][0] == vendor_user_id


async def test_handle_booking_accepted_vendor_actor_notifies_customer():
    """booking.accepted with actor=vendor → customer receives notification."""
    svc = NotificationService()
    customer_user_id = uuid.uuid4()
    session = make_mock_session()

    mock_booking = MagicMock()
    mock_booking.user_id = customer_user_id
    mock_booking.vendor_id = uuid.uuid4()
    mock_booking.event_name = "Concert"
    mock_booking.event_date = "2026-11-01"

    session.get = AsyncMock(return_value=mock_booking)

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock) as mock_sse:
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=False):
                with patch("src.services.notification_service.NotificationService._send_email", new_callable=AsyncMock):
                    await svc.handle(
                        event_type="booking.accepted",
                        payload={"booking_id": str(uuid.uuid4()), "quote_id": str(uuid.uuid4()), "actor": "vendor"},
                        user_id=uuid.uuid4(),
                        session=session,
                    )

    session.add.assert_called_once()
    added_notif = session.add.call_args[0][0]
    assert added_notif.user_id == customer_user_id
    assert added_notif.type == NotificationType.booking_accepted

    mock_sse.assert_called_once()
    assert mock_sse.call_args[0][0] == customer_user_id


async def test_handle_booking_counter_rejected_notifies_customer():
    """booking.counter_rejected → customer receives notification."""
    svc = NotificationService()
    customer_user_id = uuid.uuid4()
    session = make_mock_session()

    mock_booking = MagicMock()
    mock_booking.user_id = customer_user_id
    mock_booking.vendor_id = uuid.uuid4()
    mock_booking.event_name = "Corporate Event"
    mock_booking.event_date = "2026-10-10"

    session.get = AsyncMock(return_value=mock_booking)

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock) as mock_sse:
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=False):
                with patch("src.services.notification_service.NotificationService._send_email", new_callable=AsyncMock):
                    await svc.handle(
                        event_type="booking.counter_rejected",
                        payload={"booking_id": str(uuid.uuid4()), "quote_id": str(uuid.uuid4()), "counter_id": str(uuid.uuid4())},
                        user_id=uuid.uuid4(),
                        session=session,
                    )

    session.add.assert_called_once()
    added_notif = session.add.call_args[0][0]
    assert added_notif.user_id == customer_user_id
    assert added_notif.type == NotificationType.booking_counter_rejected

    mock_sse.assert_called_once()
    assert mock_sse.call_args[0][0] == customer_user_id


def test_negotiation_events_in_event_map():
    """All three negotiation events must be in _EVENT_MAP."""
    assert "booking.quoted" in _EVENT_MAP
    assert "booking.accepted" in _EVENT_MAP
    assert "booking.counter_rejected" in _EVENT_MAP


# ── Vendor / subscription / inquiry gap tests ─────────────────────────────────

async def test_handle_vendor_approved_notifies_vendor_user():
    """vendor.approved → vendor's user_id receives notification (ORM lookup via vendor_id)."""
    from src.services.notification_service import NotificationService, _VENDOR_ID_EVENTS
    svc = NotificationService()
    vendor_user_id = uuid.uuid4()
    vendor_id = uuid.uuid4()
    session = make_mock_session()

    mock_vendor = MagicMock()
    mock_vendor.user_id = vendor_user_id
    session.get = AsyncMock(return_value=mock_vendor)

    assert "vendor.approved" in _VENDOR_ID_EVENTS

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock) as mock_sse:
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=False):
                with patch("src.services.notification_service.NotificationService._send_email", new_callable=AsyncMock):
                    await svc.handle(
                        event_type="vendor.approved",
                        payload={"vendor_id": str(vendor_id), "business_name": "Test Co"},
                        session=session,
                    )

    session.add.assert_called_once()
    added_notif = session.add.call_args[0][0]
    assert added_notif.user_id == vendor_user_id
    assert added_notif.type == NotificationType.vendor_approved
    mock_sse.assert_called_once()
    assert mock_sse.call_args[0][0] == vendor_user_id


async def test_handle_vendor_rejected_notifies_vendor_user():
    """vendor.rejected → vendor's user_id receives notification."""
    from src.services.notification_service import NotificationService
    svc = NotificationService()
    vendor_user_id = uuid.uuid4()
    session = make_mock_session()

    mock_vendor = MagicMock()
    mock_vendor.user_id = vendor_user_id
    session.get = AsyncMock(return_value=mock_vendor)

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock) as mock_sse:
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=False):
                with patch("src.services.notification_service.NotificationService._send_email", new_callable=AsyncMock):
                    await svc.handle(
                        event_type="vendor.rejected",
                        payload={"vendor_id": str(uuid.uuid4()), "reason": "Incomplete docs"},
                        session=session,
                    )

    session.add.assert_called_once()
    added_notif = session.add.call_args[0][0]
    assert added_notif.user_id == vendor_user_id
    assert added_notif.type == NotificationType.vendor_rejected
    assert mock_sse.call_args[0][0] == vendor_user_id


async def test_handle_vendor_suspended_notifies_vendor_user():
    """vendor.suspended → vendor's user_id receives notification."""
    from src.services.notification_service import NotificationService, _VENDOR_ID_EVENTS
    svc = NotificationService()
    vendor_user_id = uuid.uuid4()
    session = make_mock_session()

    mock_vendor = MagicMock()
    mock_vendor.user_id = vendor_user_id
    session.get = AsyncMock(return_value=mock_vendor)

    assert "vendor.suspended" in _VENDOR_ID_EVENTS

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock) as mock_sse:
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=False):
                with patch("src.services.notification_service.NotificationService._send_email", new_callable=AsyncMock):
                    await svc.handle(
                        event_type="vendor.suspended",
                        payload={"vendor_id": str(uuid.uuid4()), "reason": "Policy violation"},
                        session=session,
                    )

    session.add.assert_called_once()
    added_notif = session.add.call_args[0][0]
    assert added_notif.user_id == vendor_user_id
    assert added_notif.type == NotificationType.vendor_suspended
    assert mock_sse.call_args[0][0] == vendor_user_id


async def test_handle_subscription_granted_notifies_user():
    """subscription.granted → user receives notification (user_id from payload)."""
    from src.services.notification_service import NotificationService, _PAYLOAD_USER_ID_EVENTS
    svc = NotificationService()
    user_id = uuid.uuid4()
    session = make_mock_session()

    assert "subscription.granted" in _PAYLOAD_USER_ID_EVENTS

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock) as mock_sse:
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=False):
                with patch("src.services.notification_service.NotificationService._send_email", new_callable=AsyncMock):
                    await svc.handle(
                        event_type="subscription.granted",
                        payload={"user_id": str(user_id), "days": 30},
                        session=session,
                    )

    session.add.assert_called_once()
    added_notif = session.add.call_args[0][0]
    assert added_notif.user_id == user_id
    assert added_notif.type == NotificationType.subscription_granted
    assert mock_sse.call_args[0][0] == user_id


async def test_handle_subscription_revoked_notifies_user():
    """subscription.revoked → user receives notification."""
    from src.services.notification_service import NotificationService, _PAYLOAD_USER_ID_EVENTS
    svc = NotificationService()
    user_id = uuid.uuid4()
    session = make_mock_session()

    assert "subscription.revoked" in _PAYLOAD_USER_ID_EVENTS

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock) as mock_sse:
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=False):
                with patch("src.services.notification_service.NotificationService._send_email", new_callable=AsyncMock):
                    await svc.handle(
                        event_type="subscription.revoked",
                        payload={"user_id": str(user_id), "revoked_by": str(uuid.uuid4())},
                        session=session,
                    )

    session.add.assert_called_once()
    added_notif = session.add.call_args[0][0]
    assert added_notif.user_id == user_id
    assert added_notif.type == NotificationType.subscription_revoked
    assert mock_sse.call_args[0][0] == user_id


async def test_handle_inquiry_created_notifies_vendor_user():
    """inquiry.created → vendor's user_id receives notification."""
    from src.services.notification_service import NotificationService, _VENDOR_ID_EVENTS
    svc = NotificationService()
    vendor_user_id = uuid.uuid4()
    session = make_mock_session()

    mock_vendor = MagicMock()
    mock_vendor.user_id = vendor_user_id
    session.get = AsyncMock(return_value=mock_vendor)

    assert "inquiry.created" in _VENDOR_ID_EVENTS

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock) as mock_sse:
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=False):
                with patch("src.services.notification_service.NotificationService._send_email", new_callable=AsyncMock):
                    await svc.handle(
                        event_type="inquiry.created",
                        payload={
                            "inquiry_id": str(uuid.uuid4()),
                            "vendor_id": str(uuid.uuid4()),
                            "customer_email": "customer@example.com",
                        },
                        session=session,
                    )

    session.add.assert_called_once()
    added_notif = session.add.call_args[0][0]
    assert added_notif.user_id == vendor_user_id
    assert added_notif.type == NotificationType.inquiry_created
    assert mock_sse.call_args[0][0] == vendor_user_id


async def test_handle_vendor_suspended_missing_vendor_id_is_noop():
    """vendor.suspended with no vendor_id in payload → no notification, no crash."""
    from src.services.notification_service import NotificationService
    svc = NotificationService()
    session = make_mock_session()

    await svc.handle(
        event_type="vendor.suspended",
        payload={"reason": "violation"},  # missing vendor_id
        session=session,
    )

    session.add.assert_not_called()


async def test_vendor_approved_no_longer_in_payload_user_id_events():
    """vendor.approved must use _VENDOR_ID_EVENTS path, not _PAYLOAD_USER_ID_EVENTS."""
    from src.services.notification_service import _PAYLOAD_USER_ID_EVENTS, _VENDOR_ID_EVENTS
    assert "vendor.approved" not in _PAYLOAD_USER_ID_EVENTS
    assert "vendor.approved" in _VENDOR_ID_EVENTS
    assert "vendor.rejected" not in _PAYLOAD_USER_ID_EVENTS
    assert "vendor.rejected" in _VENDOR_ID_EVENTS


def test_all_gap_events_in_event_map():
    """All 6 previously missing events must be in _EVENT_MAP."""
    assert "vendor.suspended" in _EVENT_MAP
    assert "subscription.granted" in _EVENT_MAP
    assert "subscription.revoked" in _EVENT_MAP
    assert "inquiry.created" in _EVENT_MAP
