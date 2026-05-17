"""
Unit tests for the Redis-backed OTPService.

All tests use the `fake_redis` fixture — no real Redis instance required.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.2, 3.3, 3.4
"""
import hashlib
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.services.otp_service import OTPService, _hash_code


# ── _hash_code ────────────────────────────────────────────────────────────────


class TestHashCode:
    def test_deterministic(self):
        """Same input always produces the same output."""
        code = "123456"
        assert _hash_code(code) == _hash_code(code)

    def test_produces_64_char_hex_string(self):
        """SHA-256 hex digest is always 64 characters of hex."""
        result = _hash_code("000000")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_matches_sha256(self):
        """Output matches a direct hashlib.sha256 call."""
        code = "987654"
        expected = hashlib.sha256(code.encode()).hexdigest()
        assert _hash_code(code) == expected

    def test_different_inputs_produce_different_hashes(self):
        """Different codes produce different hashes (collision resistance)."""
        assert _hash_code("000000") != _hash_code("000001")


# ── issue_otp ─────────────────────────────────────────────────────────────────


class TestIssueOtp:
    @pytest.mark.asyncio
    async def test_sets_redis_key_with_correct_hash(self, fake_redis):
        """issue_otp stores SHA-256(code) under otp:<user_id>."""
        service = OTPService()
        user_id = uuid.uuid4()

        with patch(
            "src.services.otp_service.email_service.send_email",
            new_callable=AsyncMock,
        ):
            code = await service.issue_otp(
                fake_redis, user_id, "user@example.com", "Alice"
            )

        stored = await fake_redis.get(f"otp:{user_id}")
        assert stored == _hash_code(code)

    @pytest.mark.asyncio
    async def test_ttl_is_within_valid_range(self, fake_redis):
        """TTL of the Redis key is in [1, 600] seconds after issue."""
        service = OTPService()
        user_id = uuid.uuid4()

        with patch(
            "src.services.otp_service.email_service.send_email",
            new_callable=AsyncMock,
        ):
            await service.issue_otp(
                fake_redis, user_id, "user@example.com", "Alice"
            )

        ttl = await fake_redis.ttl(f"otp:{user_id}")
        assert 1 <= ttl <= 600

    @pytest.mark.asyncio
    async def test_overwrite_semantics_single_key(self, fake_redis):
        """Calling issue_otp twice for the same user leaves exactly one Redis key."""
        service = OTPService()
        user_id = uuid.uuid4()

        with patch(
            "src.services.otp_service.email_service.send_email",
            new_callable=AsyncMock,
        ):
            await service.issue_otp(fake_redis, user_id, "user@example.com", "Alice")
            await service.issue_otp(fake_redis, user_id, "user@example.com", "Alice")

        # Scan all keys matching the pattern — should be exactly one
        keys = await fake_redis.keys(f"otp:{user_id}")
        assert len(keys) == 1

    @pytest.mark.asyncio
    async def test_second_issue_overwrites_first_hash(self, fake_redis):
        """After two issue_otp calls, only the second code's hash is stored."""
        service = OTPService()
        user_id = uuid.uuid4()

        with patch(
            "src.services.otp_service.email_service.send_email",
            new_callable=AsyncMock,
        ):
            code_a = await service.issue_otp(
                fake_redis, user_id, "user@example.com", "Alice"
            )
            code_b = await service.issue_otp(
                fake_redis, user_id, "user@example.com", "Alice"
            )

        stored = await fake_redis.get(f"otp:{user_id}")
        assert stored == _hash_code(code_b)
        assert stored != _hash_code(code_a)

    @pytest.mark.asyncio
    async def test_calls_send_email_exactly_once(self, fake_redis):
        """issue_otp calls email_service.send_email exactly once per call."""
        service = OTPService()
        user_id = uuid.uuid4()

        with patch(
            "src.services.otp_service.email_service.send_email",
            new_callable=AsyncMock,
        ) as mock_send:
            await service.issue_otp(
                fake_redis, user_id, "user@example.com", "Alice"
            )

        mock_send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_email_called_with_correct_recipient(self, fake_redis):
        """issue_otp passes the correct email address to send_email."""
        service = OTPService()
        user_id = uuid.uuid4()
        email = "recipient@example.com"

        with patch(
            "src.services.otp_service.email_service.send_email",
            new_callable=AsyncMock,
        ) as mock_send:
            await service.issue_otp(fake_redis, user_id, email, "Bob")

        call_kwargs = mock_send.call_args
        # send_email is called with keyword arg `to`
        assert call_kwargs.kwargs.get("to") == email or call_kwargs.args[0] == email


# ── verify_otp ────────────────────────────────────────────────────────────────


class TestVerifyOtp:
    @pytest.mark.asyncio
    async def test_correct_code_returns_true(self, fake_redis):
        """verify_otp returns True when the correct code is submitted."""
        service = OTPService()
        user_id = uuid.uuid4()

        with patch(
            "src.services.otp_service.email_service.send_email",
            new_callable=AsyncMock,
        ):
            code = await service.issue_otp(
                fake_redis, user_id, "user@example.com", "Alice"
            )

        result = await service.verify_otp(fake_redis, user_id, code)
        assert result is True

    @pytest.mark.asyncio
    async def test_correct_code_deletes_redis_key(self, fake_redis):
        """verify_otp deletes the Redis key on successful verification (single-use)."""
        service = OTPService()
        user_id = uuid.uuid4()

        with patch(
            "src.services.otp_service.email_service.send_email",
            new_callable=AsyncMock,
        ):
            code = await service.issue_otp(
                fake_redis, user_id, "user@example.com", "Alice"
            )

        await service.verify_otp(fake_redis, user_id, code)

        exists = await fake_redis.exists(f"otp:{user_id}")
        assert exists == 0

    @pytest.mark.asyncio
    async def test_wrong_code_raises_otp_invalid(self, fake_redis):
        """verify_otp raises HTTPException with OTP_INVALID for a wrong code."""
        service = OTPService()
        user_id = uuid.uuid4()

        with patch(
            "src.services.otp_service.email_service.send_email",
            new_callable=AsyncMock,
        ):
            code = await service.issue_otp(
                fake_redis, user_id, "user@example.com", "Alice"
            )

        wrong_code = "000000" if code != "000000" else "111111"

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_otp(fake_redis, user_id, wrong_code)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "OTP_INVALID"

    @pytest.mark.asyncio
    async def test_absent_key_raises_otp_expired(self, fake_redis):
        """verify_otp raises HTTPException with OTP_EXPIRED when no key exists."""
        service = OTPService()
        user_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_otp(fake_redis, user_id, "123456")

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "OTP_EXPIRED"

    @pytest.mark.asyncio
    async def test_second_verify_raises_otp_invalid_or_expired(self, fake_redis):
        """
        Calling verify_otp twice with the same code raises OTP_INVALID or OTP_EXPIRED
        on the second call (key was deleted after first successful verification).
        """
        service = OTPService()
        user_id = uuid.uuid4()

        with patch(
            "src.services.otp_service.email_service.send_email",
            new_callable=AsyncMock,
        ):
            code = await service.issue_otp(
                fake_redis, user_id, "user@example.com", "Alice"
            )

        # First call succeeds
        result = await service.verify_otp(fake_redis, user_id, code)
        assert result is True

        # Second call must fail — key was deleted
        with pytest.raises(HTTPException) as exc_info:
            await service.verify_otp(fake_redis, user_id, code)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] in ("OTP_INVALID", "OTP_EXPIRED")

    @pytest.mark.asyncio
    async def test_verify_strips_whitespace_from_code(self, fake_redis):
        """verify_otp strips leading/trailing whitespace before hashing."""
        service = OTPService()
        user_id = uuid.uuid4()

        with patch(
            "src.services.otp_service.email_service.send_email",
            new_callable=AsyncMock,
        ):
            code = await service.issue_otp(
                fake_redis, user_id, "user@example.com", "Alice"
            )

        # Submit code with surrounding whitespace — should still verify
        result = await service.verify_otp(fake_redis, user_id, f"  {code}  ")
        assert result is True
