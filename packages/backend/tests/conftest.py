"""
Shared pytest fixtures for the backend test suite.

- Uses SQLite in-memory (aiosqlite) so no real DB is needed.
- Creates auth, event, and booking-related tables.
- Overrides the `get_session` FastAPI dependency with the test session.
- Provides an `AsyncClient` via ASGITransport for HTTP integration tests.
"""
import pytest
import pytest_asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from httpx import AsyncClient, ASGITransport
import fakeredis.aioredis as fakeredis_aio

from src.main import app
from src.config.database import get_session
from src.middleware.rate_limit import rate_limit_dependency
from src.middleware.login_rate_limit import create_login_rate_limit_dependency

# Import models so SQLite registers them with SQLModel metadata
from src.models.user import User, RefreshToken, PasswordResetToken  # noqa: F401
from src.models.event import Event, EventType  # noqa: F401
from src.models.domain_event import DomainEvent  # noqa: F401
from src.models.booking import Booking  # noqa: F401
from src.models.notification import Notification  # noqa: F401
from src.models.notification_preference import NotificationPreference  # noqa: F401
from src.models.quote import Quote, CounterOffer  # noqa: F401

# ── Test database ─────────────────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Tables needed for all tests
AUTH_TABLES = [
    "users", "refresh_tokens", "password_reset_tokens",
    "event_types", "events", "domain_events", "bookings",
    "notifications", "notification_preferences",
    "quotes", "counter_offers",
]


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        # Patch JSONB → JSON for SQLite compatibility
        from sqlalchemy.dialects.postgresql import JSONB
        from sqlalchemy import JSON
        from src.models.domain_event import DomainEvent
        DomainEvent.__table__.c["data"].type = JSON()

        await conn.run_sync(
            lambda sync_conn: SQLModel.metadata.create_all(
                sync_conn,
                tables=[SQLModel.metadata.tables[t] for t in AUTH_TABLES if t in SQLModel.metadata.tables],
            )
        )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional test session that rolls back after each test."""
    async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


# ── Redis fixture ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def fake_redis():
    """In-memory Redis emulator — no real Redis instance required."""
    r = fakeredis_aio.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()


# ── FastAPI dependency override ───────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(request, db_session: AsyncSession, fake_redis) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with the test DB session injected, Redis mocked, and rate limiting bypassed.

    By default the email_verified guard on get_current_user is bypassed so tests
    that register a user and immediately call a protected endpoint don't hit a
    403 AUTH_EMAIL_NOT_VERIFIED. Tests that explicitly exercise the guard
    (test_email_verified_route_guard_*.py) keep the real dependency.
    """
    import src.api.v1.auth as auth_module
    import src.api.v1.events as events_module
    import src.api.v1.notifications as notif_module
    from src.api import deps as deps_module
    from src.services.auth_service import auth_service
    from fastapi import HTTPException, Request, status as http_status
    from fastapi import Depends
    from fastapi.security import HTTPAuthorizationCredentials
    from typing import Optional

    async def no_rate_limit(request=None):
        pass

    async def override_get_session():
        yield db_session

    # Bypass email_verified check unless the test file is specifically validating it.
    test_file = request.node.path.name if hasattr(request.node, "path") else ""
    bypass_email_guard = "email_verified_route_guard" not in test_file

    async def get_current_user_no_email_check(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(deps_module.bearer_scheme),
        session: AsyncSession = Depends(get_session),
    ):
        token: Optional[str] = None
        if credentials:
            token = credentials.credentials
        else:
            token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail={"code": "AUTH_UNAUTHORIZED", "message": "Not authenticated"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await auth_service.verify_access_token(token, session)

    # Inject fake_redis into app.state so route handlers use it
    app.state.redis = fake_redis

    app.dependency_overrides[get_session] = override_get_session
    # Override auth rate limiters
    app.dependency_overrides[auth_module.register_limiter] = no_rate_limit
    app.dependency_overrides[auth_module.login_limiter] = no_rate_limit
    app.dependency_overrides[auth_module.password_reset_limiter] = no_rate_limit
    # Override event route rate limiters
    app.dependency_overrides[events_module.create_limiter] = no_rate_limit
    app.dependency_overrides[events_module.read_limiter] = no_rate_limit
    # Override notification rate limiters
    app.dependency_overrides[notif_module._read_limiter] = no_rate_limit
    app.dependency_overrides[notif_module._write_limiter] = no_rate_limit
    # Bypass email_verified guard for the majority of tests
    if bypass_email_guard:
        app.dependency_overrides[deps_module.get_current_user] = get_current_user_no_email_check

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
