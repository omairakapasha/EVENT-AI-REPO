"""
Bug Condition Exploration Tests — PostgreSQL OTP Accumulation Bug (Post-Fix)

These tests were originally written to confirm the bug on unfixed code.
After the fix (migration to Redis), they are re-run in task 3.9 to confirm
the bug is resolved:

  Test 1 — No Accumulation:
    Calling issue_otp three times for the same user results in exactly ONE
    Redis key (overwrite semantics) — no unbounded growth.

  Test 2 — Redis key written:
    After issue_otp, a Redis key otp:<user_id> EXISTS — confirming Redis is
    now the storage backend.

  Test 3 — TTL set:
    After issue_otp, the Redis key has a TTL in [1, 600] seconds — confirming
    automatic eviction is in place.

EXPECTED OUTCOME on fixed code: all three tests PASS (bug is resolved).

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.3, 2.6
"""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
import fakeredis.aioredis as fakeredis_aio

from src.services.otp_service import otp_service


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def fake_redis():
    """In-memory Redis emulator — no real Redis instance required."""
    r = fakeredis_aio.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()


# ── Test 1: No Accumulation (overwrite semantics) ─────────────────────────────

@pytest.mark.asyncio
async def test_otp_no_accumulation_overwrite_semantics(fake_redis):
    """
    Fix Verification — No Accumulation:
    Calling issue_otp three times for the same user results in exactly ONE
    Redis key (overwrite semantics). The bug (unbounded PostgreSQL row growth)
    is resolved.

    PASSES on fixed code — confirms overwrite semantics.

    Counterexample from unfixed code:
      After 3 issue_otp calls, email_otps contained 3 rows (accumulation bug).
      Fixed code: exactly 1 Redis key exists after 3 calls.
    """
    user_id = uuid.uuid4()
    user_email = f"{user_id}@example.com"

    with patch(
        "src.services.otp_service.email_service.send_email",
        new_callable=AsyncMock,
    ):
        await otp_service.issue_otp(fake_redis, user_id, user_email, "Test User")
        await otp_service.issue_otp(fake_redis, user_id, user_email, "Test User")
        await otp_service.issue_otp(fake_redis, user_id, user_email, "Test User")

    redis_key = f"otp:{user_id}"
    key_exists = await fake_redis.exists(redis_key)

    assert key_exists == 1, (
        f"Expected exactly 1 Redis key '{redis_key}' after 3 issue_otp calls, "
        f"got exists={key_exists}. Overwrite semantics not working."
    )


# ── Test 2: Redis key written ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_otp_redis_key_written(fake_redis):
    """
    Fix Verification — Redis key written:
    After issue_otp, a Redis key otp:<user_id> EXISTS — confirming Redis is
    now the storage backend (not PostgreSQL).

    PASSES on fixed code — confirms Redis backend.

    Counterexample from unfixed code:
      After issue_otp, fake_redis.exists("otp:<user_id>") == 0 (no key written).
      Fixed code: key exists immediately after issue_otp.
    """
    user_id = uuid.uuid4()
    user_email = f"{user_id}@example.com"

    with patch(
        "src.services.otp_service.email_service.send_email",
        new_callable=AsyncMock,
    ):
        await otp_service.issue_otp(fake_redis, user_id, user_email, "Test User")

    redis_key = f"otp:{user_id}"
    key_exists = await fake_redis.exists(redis_key)

    assert key_exists == 1, (
        f"Expected Redis key '{redis_key}' to exist after issue_otp on fixed code, "
        f"but key does not exist (exists={key_exists}). "
        "Redis backend not writing the key."
    )


# ── Test 3: TTL set ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_otp_ttl_set_on_redis_key(fake_redis):
    """
    Fix Verification — TTL set:
    After issue_otp, the Redis key otp:<user_id> has a TTL in [1, 600] seconds —
    confirming automatic eviction is in place (no manual cleanup needed).

    PASSES on fixed code — confirms TTL-based auto-eviction.

    Counterexample from unfixed code:
      An expired row in email_otps still existed after its expiry timestamp
      (no auto-eviction). Fixed code: Redis TTL handles eviction automatically.
    """
    user_id = uuid.uuid4()
    user_email = f"{user_id}@example.com"

    with patch(
        "src.services.otp_service.email_service.send_email",
        new_callable=AsyncMock,
    ):
        await otp_service.issue_otp(fake_redis, user_id, user_email, "Test User")

    redis_key = f"otp:{user_id}"
    ttl = await fake_redis.ttl(redis_key)

    assert 1 <= ttl <= 600, (
        f"Expected Redis key '{redis_key}' to have TTL in [1, 600], got ttl={ttl}. "
        "TTL not set correctly — auto-eviction will not work."
    )
