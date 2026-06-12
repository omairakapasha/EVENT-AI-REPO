"""
Unit tests for EventService.

Uses AsyncMock for session and patches event_bus.emit — zero real DB calls.
Run with: uv run pytest tests/test_event_service.py -v
"""
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from src.models.event import Event, EventType, EventStatus
from src.models.user import SubscriptionStatus, User
from src.schemas.event import EventCreate, EventUpdate
from src.services.event_service import EventService, VALID_TRANSITIONS, TERMINAL_STATUSES

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_event(
    status: EventStatus = EventStatus.DRAFT,
    user_id: uuid.UUID = None,
) -> Event:
    uid = user_id or uuid.uuid4()
    return Event(
        id=uuid.uuid4(),
        user_id=uid,
        event_type_id=uuid.uuid4(),
        name="Test Event",
        start_date=datetime.now(timezone.utc) + timedelta(days=30),
        status=status,
        timezone="Asia/Karachi",
        country="Pakistan",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def make_user(status: SubscriptionStatus = SubscriptionStatus.pro) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.subscription_status = status
    u.subscription_expires_at = None
    return u


def make_session(event: Event = None, user: User = None) -> AsyncMock:
    session = AsyncMock()

    async def _get(model, pk):
        if model is User:
            return user
        return event

    session.get = AsyncMock(side_effect=_get)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    # Default execute mock — returns scalar() == 0 (used by count queries)
    _exec_result = MagicMock()
    _exec_result.scalar = MagicMock(return_value=0)
    session.execute = AsyncMock(return_value=_exec_result)
    return session


# ── State machine tests ───────────────────────────────────────────────────────

@pytest.mark.parametrize("from_status,to_status", [
    (EventStatus.DRAFT,    EventStatus.PLANNED),
    (EventStatus.DRAFT,    EventStatus.CANCELED),
    (EventStatus.PLANNED,  EventStatus.ACTIVE),
    (EventStatus.PLANNED,  EventStatus.CANCELED),
    (EventStatus.ACTIVE,   EventStatus.COMPLETED),
    (EventStatus.ACTIVE,   EventStatus.CANCELED),
])
async def test_valid_transitions(from_status, to_status):
    svc = EventService()
    user_id = uuid.uuid4()
    event = make_event(status=from_status, user_id=user_id)
    session = make_session(event)

    with patch("src.services.event_service.event_bus.emit", new_callable=AsyncMock):
        result = await svc.transition_status(session, event, to_status, user_id)

    assert result.status == to_status


@pytest.mark.parametrize("from_status,to_status", [
    (EventStatus.DRAFT,    EventStatus.ACTIVE),
    (EventStatus.DRAFT,    EventStatus.COMPLETED),
    (EventStatus.PLANNED,  EventStatus.COMPLETED),
    (EventStatus.ACTIVE,   EventStatus.DRAFT),
    (EventStatus.ACTIVE,   EventStatus.PLANNED),
])
async def test_invalid_transitions_raise_409(from_status, to_status):
    svc = EventService()
    user_id = uuid.uuid4()
    event = make_event(status=from_status, user_id=user_id)
    session = make_session(event)

    with pytest.raises(HTTPException) as exc_info:
        await svc.transition_status(session, event, to_status, user_id)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "VALIDATION_INVALID_STATUS_TRANSITION"


@pytest.mark.parametrize("terminal_status", [EventStatus.COMPLETED, EventStatus.CANCELED])
async def test_terminal_status_blocks_transition(terminal_status):
    svc = EventService()
    user_id = uuid.uuid4()
    event = make_event(status=terminal_status, user_id=user_id)
    session = make_session(event)

    with pytest.raises(HTTPException) as exc_info:
        await svc.transition_status(session, event, EventStatus.PLANNED, user_id)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "VALIDATION_INVALID_STATUS_TRANSITION"


async def test_terminal_status_blocks_update():
    svc = EventService()
    user_id = uuid.uuid4()
    event = make_event(status=EventStatus.COMPLETED, user_id=user_id)
    session = make_session(event)

    with pytest.raises(HTTPException) as exc_info:
        await svc.update_event(session, event.id, EventUpdate(name="New Name"), user_id)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "VALIDATION_INVALID_STATUS_TRANSITION"


# ── Domain event emission tests ───────────────────────────────────────────────

async def test_create_event_emits_event_created():
    svc = EventService()
    user_id = uuid.uuid4()
    et_id = uuid.uuid4()

    event_type = EventType(
        id=et_id, name="Wedding", display_order=1, is_active=True,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )
    pro_user = make_user(SubscriptionStatus.pro)
    session = AsyncMock()

    async def _get(model, pk):
        if model is User:
            return pro_user
        return event_type

    session.get = AsyncMock(side_effect=_get)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    _exec_result = MagicMock()
    _exec_result.scalar = MagicMock(return_value=0)
    session.execute = AsyncMock(return_value=_exec_result)

    event_in = EventCreate(
        event_type_id=et_id,
        name="My Wedding",
        start_date=datetime.now(timezone.utc) + timedelta(days=60),
    )

    with patch("src.services.event_service.event_bus.emit", new_callable=AsyncMock) as mock_emit:
        await svc.create_event(session, event_in, user_id)

    mock_emit.assert_called_once()
    call_args = mock_emit.call_args
    assert call_args[0][1] == "event.created"
    payload = call_args[1]["payload"] if "payload" in call_args[1] else call_args[0][2]
    for key in ("event_id", "user_id", "event_type_id", "name", "start_date", "status"):
        assert key in payload


async def test_transition_status_emits_status_changed():
    svc = EventService()
    user_id = uuid.uuid4()
    event = make_event(status=EventStatus.DRAFT, user_id=user_id)
    session = make_session(event)

    with patch("src.services.event_service.event_bus.emit", new_callable=AsyncMock) as mock_emit:
        await svc.transition_status(session, event, EventStatus.PLANNED, user_id)

    mock_emit.assert_called_once()
    call_args = mock_emit.call_args
    assert call_args[0][1] == "event.status_changed"
    payload = call_args[1]["payload"] if "payload" in call_args[1] else call_args[0][2]
    for key in ("event_id", "user_id", "old_status", "new_status"):
        assert key in payload


async def test_cancel_event_emits_event_cancelled():
    svc = EventService()
    user_id = uuid.uuid4()
    event = make_event(status=EventStatus.PLANNED, user_id=user_id)
    session = make_session(event)

    with patch("src.services.event_service.event_bus.emit", new_callable=AsyncMock) as mock_emit:
        await svc.cancel_event(session, event.id, user_id, reason="Changed plans")

    # Should have emitted event.status_changed + event.cancelled
    assert mock_emit.call_count == 2
    event_types_emitted = [c[0][1] for c in mock_emit.call_args_list]
    assert "event.cancelled" in event_types_emitted

    cancelled_call = next(c for c in mock_emit.call_args_list if c[0][1] == "event.cancelled")
    payload = cancelled_call[1]["payload"] if "payload" in cancelled_call[1] else cancelled_call[0][2]
    for key in ("event_id", "user_id", "reason", "canceled_at"):
        assert key in payload


# ── Duplicate tests ───────────────────────────────────────────────────────────

async def test_duplicate_event_correct_fields():
    svc = EventService()
    user_id = uuid.uuid4()
    source = make_event(status=EventStatus.ACTIVE, user_id=user_id)
    source.name = "Annual Gala"
    session = make_session(source)

    with patch("src.services.event_service.event_bus.emit", new_callable=AsyncMock):
        new_event = await svc.duplicate_event(session, source.id, user_id)

    assert new_event.name == "Copy of Annual Gala"
    assert new_event.status == EventStatus.DRAFT
    assert new_event.cancellation_reason is None
    assert new_event.canceled_at is None
    assert new_event.user_id == user_id


# ── get_event wrong user ──────────────────────────────────────────────────────

async def test_get_event_wrong_user_raises_404():
    svc = EventService()
    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()
    event = make_event(user_id=owner_id)
    session = make_session(event)

    with pytest.raises(HTTPException) as exc_info:
        await svc.get_event(session, event.id, other_id)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["code"] == "NOT_FOUND_EVENT"


async def test_get_event_not_found_raises_404():
    svc = EventService()
    session = make_session(None)  # session.get returns None

    with pytest.raises(HTTPException) as exc_info:
        await svc.get_event(session, uuid.uuid4(), uuid.uuid4())

    assert exc_info.value.status_code == 404


# ── Free plan event limit ─────────────────────────────────────────────────────

async def test_free_plan_create_event_allowed_when_no_existing_events():
    svc = EventService()
    user_id = uuid.uuid4()
    et_id = uuid.uuid4()
    free_user = make_user(SubscriptionStatus.free)
    event_type = EventType(
        id=et_id, name="Wedding", display_order=1, is_active=True,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )

    session = AsyncMock()

    async def _get(model, pk):
        if model is User:
            return free_user
        return event_type

    session.get = AsyncMock(side_effect=_get)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    _exec_result = MagicMock()
    _exec_result.scalar = MagicMock(return_value=0)  # no existing events
    session.execute = AsyncMock(return_value=_exec_result)

    event_in = EventCreate(
        event_type_id=et_id,
        name="My First Event",
        start_date=datetime.now(timezone.utc) + timedelta(days=30),
    )

    with patch("src.services.event_service.event_bus.emit", new_callable=AsyncMock):
        result = await svc.create_event(session, event_in, user_id)

    assert result is not None


async def test_free_plan_create_event_blocked_when_event_exists():
    svc = EventService()
    user_id = uuid.uuid4()
    et_id = uuid.uuid4()
    free_user = make_user(SubscriptionStatus.free)

    session = AsyncMock()

    async def _get(model, pk):
        if model is User:
            return free_user
        return None

    session.get = AsyncMock(side_effect=_get)
    _exec_result = MagicMock()
    _exec_result.scalar = MagicMock(return_value=3)  # at limit
    session.execute = AsyncMock(return_value=_exec_result)

    event_in = EventCreate(
        event_type_id=et_id,
        name="Second Event",
        start_date=datetime.now(timezone.utc) + timedelta(days=30),
    )

    with pytest.raises(HTTPException) as exc_info:
        await svc.create_event(session, event_in, user_id)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "SUBSCRIPTION_LIMIT_EXCEEDED"


async def test_pro_plan_create_event_allowed_regardless_of_count():
    svc = EventService()
    user_id = uuid.uuid4()
    et_id = uuid.uuid4()
    pro_user = make_user(SubscriptionStatus.pro)
    event_type = EventType(
        id=et_id, name="Wedding", display_order=1, is_active=True,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )

    session = AsyncMock()

    async def _get(model, pk):
        if model is User:
            return pro_user
        return event_type

    session.get = AsyncMock(side_effect=_get)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    _exec_result = MagicMock()
    _exec_result.scalar = MagicMock(return_value=99)  # many existing events
    session.execute = AsyncMock(return_value=_exec_result)

    event_in = EventCreate(
        event_type_id=et_id,
        name="Another Pro Event",
        start_date=datetime.now(timezone.utc) + timedelta(days=30),
    )

    with patch("src.services.event_service.event_bus.emit", new_callable=AsyncMock):
        result = await svc.create_event(session, event_in, user_id)

    assert result is not None


async def test_free_plan_duplicate_event_blocked():
    svc = EventService()
    user_id = uuid.uuid4()
    source = make_event(status=EventStatus.ACTIVE, user_id=user_id)
    free_user = make_user(SubscriptionStatus.free)

    session = AsyncMock()

    async def _get(model, pk):
        if model is User:
            return free_user
        return source

    session.get = AsyncMock(side_effect=_get)
    _exec_result = MagicMock()
    _exec_result.scalar = MagicMock(return_value=3)
    session.execute = AsyncMock(return_value=_exec_result)

    with pytest.raises(HTTPException) as exc_info:
        await svc.duplicate_event(session, source.id, user_id)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "SUBSCRIPTION_LIMIT_EXCEEDED"
