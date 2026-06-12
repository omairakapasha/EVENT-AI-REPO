"""
AgentContext — the sole context type threaded through RunContext[AgentContext]
into all tool functions.

Usage:
    from services.agent_context import AgentContext

    agent_ctx = AgentContext(db=session, user_id=uuid.UUID(user_id_str))
    result = await Runner.run(triage_agent, message, context=agent_ctx)
"""
from __future__ import annotations

import dataclasses
import uuid

from sqlalchemy.ext.asyncio import AsyncSession


@dataclasses.dataclass
class AgentContext:
    """
    Carries the authenticated database session and the requesting user's UUID
    into every @function_tool call via RunContext[AgentContext].

    Fields
    ------
    db : AsyncSession
        The active SQLAlchemy async session for the current request.
        Tools use this for all DB reads and writes — never httpx.
    user_id : uuid.UUID
        The UUID of the authenticated user making the request.
        Tools use this to scope queries and enforce ownership.
    vendor_suggestions : list
        Vendor dicts collected by vendor tools during this run.
        The chat router reads this after the stream completes and emits
        a structured SSE event so the UI can render booking cards.
    """

    db: AsyncSession
    user_id: uuid.UUID
    vendor_suggestions: list = dataclasses.field(default_factory=list)
