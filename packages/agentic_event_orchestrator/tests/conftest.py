"""
Shared test fixtures for agentic_event_orchestrator tests.

Uses sqlite+aiosqlite:///:memory: — no Neon, no Docker required.
Defines minimal SQLAlchemy table metadata that mirrors the backend models
for event_types, events, bookings, services, vendors, and users.
"""
from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Callable

import pytest
import pytest_asyncio
from agents.tool_context import ToolContext
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Minimal AgentContext stub
# (Task 3.1 will create the real services/agent_context.py — this stub is
#  used only in tests until that file exists.)
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class AgentContext:
    """Minimal context threaded through RunContext[AgentContext] into tools."""
    db: AsyncSession
    user_id: uuid.UUID


# ---------------------------------------------------------------------------
# Minimal table metadata (mirrors backend models, SQLite-compatible)
# ---------------------------------------------------------------------------

metadata = MetaData()

users_table = Table(
    "users",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("email", String(255), unique=True, nullable=False),
    Column("password_hash", String(255), nullable=False, default="hash"),
    Column("first_name", String(100)),
    Column("last_name", String(100)),
    Column("role", String(50), default="user"),
    Column("is_active", Boolean, default=True),
    Column("email_verified", Boolean, default=False),
    Column("failed_login_attempts", Integer, default=0),
    Column("subscription_status", String(20), default="free"),
    Column("subscription_expires_at", DateTime),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("updated_at", DateTime, default=datetime.utcnow),
)

event_types_table = Table(
    "event_types",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("name", String(100), unique=True, nullable=False),
    Column("description", String(500)),
    Column("icon", String(255)),
    Column("display_order", Integer, default=0),
    Column("is_active", Boolean, default=True),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("updated_at", DateTime, default=datetime.utcnow),
)

events_table = Table(
    "events",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id"), nullable=False),
    Column("event_type_id", String(36), ForeignKey("event_types.id"), nullable=False),
    Column("name", String(200), nullable=False),
    Column("description", String(5000)),
    Column("start_date", DateTime, nullable=False),
    Column("end_date", DateTime),
    Column("timezone", String(50), default="Asia/Karachi"),
    Column("venue_name", String(255)),
    Column("address", String(500)),
    Column("city", String(100)),
    Column("country", String(100), default="Pakistan"),
    Column("guest_count", Integer),
    Column("budget", Float),
    Column("special_requirements", String(2000)),
    Column("status", String(50), default="draft"),
    Column("cancellation_reason", String(500)),
    Column("canceled_at", DateTime),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("updated_at", DateTime, default=datetime.utcnow),
)

vendors_table = Table(
    "vendors",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id"), unique=True, nullable=False),
    Column("business_name", String(255), nullable=False),
    Column("description", String(2000)),
    Column("contact_email", String(255), unique=True, nullable=False),
    Column("contact_phone", String(50)),
    Column("city", String(100)),
    Column("region", String(100)),
    Column("status", String(50), default="PENDING"),
    Column("rating", Float, default=0.0),
    Column("total_reviews", Integer, default=0),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("updated_at", DateTime, default=datetime.utcnow),
)

services_table = Table(
    "services",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("vendor_id", String(36), ForeignKey("vendors.id"), nullable=False),
    Column("name", String(255), nullable=False),
    Column("description", String(2000)),
    Column("capacity", Integer),
    Column("price_min", Float),
    Column("price_max", Float),
    Column("requirements", String(1000)),
    Column("is_active", Boolean, default=True),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("updated_at", DateTime, default=datetime.utcnow),
)

bookings_table = Table(
    "bookings",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("vendor_id", String(36), ForeignKey("vendors.id"), nullable=False),
    Column("service_id", String(36), ForeignKey("services.id"), nullable=False),
    Column("user_id", String(36), ForeignKey("users.id")),
    Column("event_id", String(36)),
    Column("event_name", String(255)),
    Column("event_date", String(50), nullable=False),  # stored as ISO string in SQLite
    Column("guest_count", Integer),
    Column("status", String(50), default="pending"),
    Column("quantity", Integer, default=1),
    Column("special_requirements", String(2000)),
    Column("notes", String(1000)),
    Column("unit_price", Float, nullable=False),
    Column("total_price", Float, nullable=False),
    Column("currency", String(3), default="USD"),
    Column("payment_status", String(50), default="pending"),
    Column("cancellation_reason", String(300)),
    Column("cancelled_at", DateTime),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("updated_at", DateTime, default=datetime.utcnow),
)

vendor_availability_table = Table(
    "vendor_availability",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("vendor_id", String(36), ForeignKey("vendors.id"), nullable=False),
    Column("service_id", String(36), ForeignKey("services.id")),
    Column("date", String(50), nullable=False),
    Column("status", String(50), default="available"),
    Column("locked_until", DateTime),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("updated_at", DateTime, default=datetime.utcnow),
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def engine():
    """Session-scoped in-memory SQLite engine."""
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)


@pytest_asyncio.fixture(scope="session")
async def create_tables(engine):
    """Create all tables once per session."""
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(engine, create_tables) -> AsyncGenerator[AsyncSession, None]:
    """Function-scoped session. Tools manage their own commits; tests use unique UUIDs for isolation."""
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
def make_ctx(db_session: AsyncSession) -> Callable[[uuid.UUID], ToolContext]:
    """
    Factory fixture: returns a function that builds a ToolContext carrying
    the test DB session and the given user_id.

    Usage in tests:
        ctx = make_ctx(some_user_id)
        result = await some_tool.on_invoke_tool(ctx, json.dumps(args))
    """
    def _factory(user_id: uuid.UUID) -> ToolContext:
        return ToolContext(
            context=AgentContext(db=db_session, user_id=user_id),
            tool_name="test_tool",
            tool_call_id="test-call-id",
            tool_arguments="{}",
            run_config=None,
        )

    return _factory
