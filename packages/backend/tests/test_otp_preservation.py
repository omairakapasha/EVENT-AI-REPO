"""
Preservation Property Tests — OTP Postgres Backend Bugfix
=========================================================

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

These tests capture the BASELINE behaviour of the OTP service on non-buggy
inputs (valid/wrong/expired/reused OTP codes). They were written BEFORE the
fix was applied and confirmed passing on unfixed code. After the fix (tasks 3.x),
they must STILL PASS — confirming no regressions were introduced.

Observation-first methodology:
  - verify_otp(redis, user_id, correct_code) → True
  - verify_otp(redis, user_id, wrong_code)   → HTTPException OTP_INVALID
  - verify_otp(redis, user_id, correct_code) called twice → OTP_INVALID on 2nd
  - verify_otp(redis, user_id, expired_code) → HTTPException OTP_EXPIRED
  - after re-issuing (code B), verify_otp(code_A) → OTP_INVALID

Properties tested:
  2a — Valid code:      issue_otp + verify_otp(correct_code) → True
  2b — Wrong code:      issue_otp(code) + verify_otp(wrong_code) → OTP_INVALID
  2c — Single-use:      verify_otp twice with same code → OTP_INVALID on 2nd call
  2d — Re-issue invalidation: issue_otp(A) then issue_otp(B) →
        verify_otp(A) raises OTP_INVALID, verify_otp(B) returns True
"""
import hashlib
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
import fakeredis.aioredis as fakeredis_aio
from fastapi import HTTPException
from hypothesis import HealthCheck, given
from hypothesis import settings as h_settings
from hypothesis import strategies as st

from src.services.otp_service import otp_service, OTP_EXPIRY_SECONDS


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def fake_redis():
    """In-memory Redis emulator — no real Redis instance required."""
    r = fakeredis_aio.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()


# ── Helpers ───────────────────────────────────────────────────────────────────

_PATCH_TARGET = "src.services.otp_service.email_service.send_email"


async def _issue(redis, user_id: uuid.UUID) -> str:
    """
    Issue an OTP for the given user_id. Email sending is always mocked.
    Returns the plaintext code returned by issue_otp.
    """
    with patch(_PATCH_TARGET, new_callable=AsyncMock):
        code = await otp_service.issue_otp(
            redis,
            user_id,
            f"{user_id}@example.com",
            "Test User",
        )
    return code


# ─────────────────────────────────────────────────────────────────────────────
# Baseline observations (deterministic, run first)
# ─────────────────────────────────────────────────────────────────────────────

class TestBaselineObservations:
    """
    Deterministic baseline observations on fixed code.
    These confirm the expected behaviour is preserved after the Redis migration.
    """

    @pytest.mark.asyncio
    async def test_observe_valid_code_returns_true(self, fake_redis):
        """
        Observe: verify_otp(redis, user_id, correct_code) returns True.
        """
        user_id = uuid.uuid4()
        code = await _issue(fake_redis, user_id)
        result = await otp_service.verify_otp(fake_redis, user_id, code)
        assert result is True

    @pytest.mark.asyncio
    async def test_observe_wrong_code_raises_otp_invalid(self, fake_redis):
        """
        Observe: verify_otp(redis, user_id, wrong_code) raises HTTPException OTP_INVALID.
        """
        user_id = uuid.uuid4()
        code = await _issue(fake_redis, user_id)
        wrong_code = "000000" if code != "000000" else "111111"

        with pytest.raises(HTTPException) as exc_info:
            await otp_service.verify_otp(fake_redis, user_id, wrong_code)
        assert exc_info.value.detail["code"] == "OTP_INVALID"

    @pytest.mark.asyncio
    async def test_observe_single_use_second_call_raises_otp_invalid(self, fake_redis):
        """
        Observe: verify_otp called twice with the same correct code raises OTP_INVALID on 2nd call.
        """
        user_id = uuid.uuid4()
        code = await _issue(fake_redis, user_id)

        # First call succeeds
        result = await otp_service.verify_otp(fake_redis, user_id, code)
        assert result is True

        # Second call raises OTP_INVALID (key deleted after first verify)
        with pytest.raises(HTTPException) as exc_info:
            await otp_service.verify_otp(fake_redis, user_id, code)
        assert exc_info.value.detail["code"] in ("OTP_INVALID", "OTP_EXPIRED")

    @pytest.mark.asyncio
    async def test_observe_expired_code_raises_otp_expired(self, fake_redis):
        """
        Observe: verify_otp with an expired code raises HTTPException OTP_EXPIRED.
        We simulate expiry by deleting the Redis key (TTL elapsed = key gone).
        """
        user_id = uuid.uuid4()
        code = await _issue(fake_redis, user_id)

        # Simulate TTL expiry by deleting the key
        await fake_redis.delete(f"otp:{user_id}")

        with pytest.raises(HTTPException) as exc_info:
            await otp_service.verify_otp(fake_redis, user_id, code)
        assert exc_info.value.detail["code"] == "OTP_EXPIRED"

    @pytest.mark.asyncio
    async def test_observe_reissue_invalidates_old_code(self, fake_redis):
        """
        Observe: after re-issuing OTP (code B), verifying with old code A raises OTP_INVALID.
        """
        user_id = uuid.uuid4()
        code_a = await _issue(fake_redis, user_id)
        code_b = await _issue(fake_redis, user_id)

        # Old code A is now invalid (key overwritten with code B's hash)
        with pytest.raises(HTTPException) as exc_info:
            await otp_service.verify_otp(fake_redis, user_id, code_a)
        assert exc_info.value.detail["code"] == "OTP_INVALID"

        # New code B is valid
        result = await otp_service.verify_otp(fake_redis, user_id, code_b)
        assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# Property 2a — Valid code
# ─────────────────────────────────────────────────────────────────────────────

class TestProperty2aValidCode:
    """
    Property 2a — Valid code: for any user_id (UUID) and any 6-digit code string,
    after issue_otp + immediate verify_otp with the correct code, result is True.

    **Validates: Requirements 3.1**
    """

    @pytest.mark.asyncio
    @h_settings(
        max_examples=3,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    @given(
        user_id=st.uuids(),
        code=st.from_regex(r"\d{6}", fullmatch=True),
    )
    async def test_property_2a_valid_code_returns_true(
        self,
        fake_redis,
        user_id: uuid.UUID,
        code: str,
    ):
        """
        Property 2a — Valid code preservation (property-based).

        For any user_id (UUID) and any 6-digit code, after storing the hash in
        Redis + immediate verify_otp with the correct code, the result MUST be True.

        **Validates: Requirements 3.1**
        """
        # Store the known code hash directly in Redis
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        await fake_redis.set(f"otp:{user_id}", code_hash, ex=OTP_EXPIRY_SECONDS)

        result = await otp_service.verify_otp(fake_redis, user_id, code)
        assert result is True, (
            f"PRESERVATION VIOLATED: verify_otp returned {result!r} instead of True "
            f"for user_id={user_id}, code={code!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property 2b — Wrong code
# ─────────────────────────────────────────────────────────────────────────────

class TestProperty2bWrongCode:
    """
    Property 2b — Wrong code: for any (user_id, code, wrong_code) where
    wrong_code != code, after storing code, verify_otp(wrong_code) raises OTP_INVALID.

    **Validates: Requirements 3.4**
    """

    @pytest.mark.asyncio
    @h_settings(
        max_examples=3,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    @given(
        user_id=st.uuids(),
        code=st.from_regex(r"\d{6}", fullmatch=True),
        wrong_code=st.from_regex(r"\d{6}", fullmatch=True),
    )
    async def test_property_2b_wrong_code_raises_otp_invalid(
        self,
        fake_redis,
        user_id: uuid.UUID,
        code: str,
        wrong_code: str,
    ):
        """
        Property 2b — Wrong code preservation (property-based).

        **Validates: Requirements 3.4**
        """
        if wrong_code == code:
            return

        code_hash = hashlib.sha256(code.encode()).hexdigest()
        await fake_redis.set(f"otp:{user_id}", code_hash, ex=OTP_EXPIRY_SECONDS)

        with pytest.raises(HTTPException) as exc_info:
            await otp_service.verify_otp(fake_redis, user_id, wrong_code)

        assert exc_info.value.detail["code"] == "OTP_INVALID", (
            f"PRESERVATION VIOLATED: expected OTP_INVALID for wrong_code={wrong_code!r} "
            f"(issued code={code!r}), got {exc_info.value.detail!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property 2c — Single-use
# ─────────────────────────────────────────────────────────────────────────────

class TestProperty2cSingleUse:
    """
    Property 2c — Single-use: for any valid (user_id, code), after one successful
    verify_otp, a second verify_otp with the same code raises OTP_INVALID or OTP_EXPIRED.

    **Validates: Requirements 3.2**
    """

    @pytest.mark.asyncio
    @h_settings(
        max_examples=3,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    @given(
        user_id=st.uuids(),
        code=st.from_regex(r"\d{6}", fullmatch=True),
    )
    async def test_property_2c_single_use_second_call_raises_error(
        self,
        fake_redis,
        user_id: uuid.UUID,
        code: str,
    ):
        """
        Property 2c — Single-use preservation (property-based).

        **Validates: Requirements 3.2**
        """
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        await fake_redis.set(f"otp:{user_id}", code_hash, ex=OTP_EXPIRY_SECONDS)

        # First call must succeed
        result = await otp_service.verify_otp(fake_redis, user_id, code)
        assert result is True

        # Second call must raise (key deleted after first verify)
        with pytest.raises(HTTPException) as exc_info:
            await otp_service.verify_otp(fake_redis, user_id, code)

        assert exc_info.value.detail["code"] in ("OTP_INVALID", "OTP_EXPIRED"), (
            f"PRESERVATION VIOLATED: second verify_otp should raise OTP_INVALID or OTP_EXPIRED "
            f"for code={code!r}, got {exc_info.value.detail!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property 2d — Re-issue invalidation
# ─────────────────────────────────────────────────────────────────────────────

class TestProperty2dReissueInvalidation:
    """
    Property 2d — Re-issue invalidation: for any user_id, after issue_otp (code A)
    then issue_otp (code B), verify_otp(code_A) raises OTP_INVALID and
    verify_otp(code_B) returns True.

    **Validates: Requirements 3.5**
    """

    @pytest.mark.asyncio
    @h_settings(
        max_examples=3,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    @given(user_id=st.uuids())
    async def test_property_2d_reissue_invalidates_old_code(
        self,
        fake_redis,
        user_id: uuid.UUID,
    ):
        """
        Property 2d — Re-issue invalidation preservation (property-based).

        **Validates: Requirements 3.5**
        """
        code_a = await _issue(fake_redis, user_id)
        code_b = await _issue(fake_redis, user_id)

        if code_a == code_b:
            return

        # Verifying with old code A must raise OTP_INVALID
        with pytest.raises(HTTPException) as exc_info_a:
            await otp_service.verify_otp(fake_redis, user_id, code_a)

        assert exc_info_a.value.detail["code"] == "OTP_INVALID", (
            f"PRESERVATION VIOLATED: verify_otp(code_A={code_a!r}) should raise "
            f"OTP_INVALID after re-issue, got {exc_info_a.value.detail!r}"
        )

        # Verifying with new code B must return True
        result = await otp_service.verify_otp(fake_redis, user_id, code_b)
        assert result is True, (
            f"PRESERVATION VIOLATED: verify_otp(code_B={code_b!r}) should return True "
            f"after re-issue, got {result!r}"
        )
