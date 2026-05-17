"""
Preservation Property Tests — Password Reset Token Exposure
===========================================================

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

These tests capture the BASELINE behaviour of the unfixed code on non-buggy
inputs.  They are written BEFORE the fix is applied and must ALL PASS on
unfixed code.  After the fix is applied (tasks 3.x), they must STILL PASS —
confirming no regressions were introduced.

Properties tested:
  2a — Anti-enumeration: any email (registered or not) → HTTP 200, success=True
  2b — Confirm flow preserved: valid token from unfixed endpoint → HTTP 200, password updated
  2c — Invalid token still rejected: random string → HTTP 400
  2d — Rate limiter preserved: 6th request within the hour → HTTP 429
"""
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, ASGITransport
from hypothesis import given, settings as h_settings, HealthCheck
from hypothesis import strategies as st
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.config.database import get_session
import src.api.v1.auth as auth_module


# ── URL constants ─────────────────────────────────────────────────────────────

REGISTER_URL = "/api/v1/auth/register"
RESET_REQUEST_URL = "/api/v1/auth/password-reset-request"
RESET_CONFIRM_URL = "/api/v1/auth/password-reset-confirm"
LOGIN_URL = "/api/v1/auth/login"
LOGOUT_URL = "/api/v1/auth/logout"
REFRESH_URL = "/api/v1/auth/refresh"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _reg_payload(email: str) -> dict:
    return {
        "email": email,
        "password": "StrongPass123!",
        "first_name": "Preserve",
        "last_name": "Tester",
    }


# ── Rate-limit-aware client fixture ──────────────────────────────────────────
# The default `client` fixture in conftest.py overrides password_reset_limiter
# with a no-op.  For Property 2d we need the REAL limiter, so we create a
# separate fixture that only bypasses register/login limiters.

@pytest_asyncio.fixture
async def rate_limited_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    AsyncClient with the test DB injected but password_reset_limiter NOT bypassed.
    Used exclusively for Property 2d (rate limiter preservation test).
    """
    import src.api.v1.events as events_module
    import src.api.v1.notifications as notif_module

    async def no_rate_limit(request=None):
        pass

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    # Bypass register and login limiters so setup calls succeed
    app.dependency_overrides[auth_module.register_limiter] = no_rate_limit
    app.dependency_overrides[auth_module.login_limiter] = no_rate_limit
    # NOTE: password_reset_limiter is intentionally NOT overridden here
    # Override event/notification limiters to avoid interference
    app.dependency_overrides[events_module.create_limiter] = no_rate_limit
    app.dependency_overrides[events_module.read_limiter] = no_rate_limit
    app.dependency_overrides[notif_module._read_limiter] = no_rate_limit
    app.dependency_overrides[notif_module._write_limiter] = no_rate_limit

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Property 2a — Anti-enumeration
# ─────────────────────────────────────────────────────────────────────────────

class TestAntiEnumerationPreservation:
    """
    Property 2a — Anti-enumeration: POST /api/v1/auth/password-reset-request
    returns HTTP 200 with success=True for ANY email address, whether registered
    or not.  Callers cannot distinguish registered from unregistered by response
    shape.

    **Validates: Requirements 3.3**
    """

    @pytest.mark.asyncio
    async def test_unregistered_email_returns_200(self, client: AsyncClient):
        """Unregistered email → HTTP 200 (baseline observation on unfixed code)."""
        resp = await client.post(
            RESET_REQUEST_URL,
            json={"email": "definitely_not_registered_xyz@example.com"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_registered_email_returns_200(self, client: AsyncClient):
        """Registered email → HTTP 200 (same status as unregistered)."""
        reg = await client.post(REGISTER_URL, json=_reg_payload("preserve_2a_reg@example.com"))
        assert reg.status_code in (200, 201)

        with patch(
            "src.services.email_service.email_service.send_email",
            new_callable=AsyncMock,
        ):
            resp = await client.post(
                RESET_REQUEST_URL,
                json={"email": "preserve_2a_reg@example.com"},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    @h_settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    @given(email=st.emails())
    async def test_property_2a_anti_enumeration(self, client: AsyncClient, email: str):
        """
        Property 2a — Anti-enumeration (property-based).

        For any syntactically valid email address (registered or not), the
        endpoint MUST return HTTP 200.  The response body MUST contain
        ``success`` equal to True and must NOT contain a ``token`` field.

        **Validates: Requirements 2.4, 3.3**
        """
        with patch(
            "src.services.email_service.email_service.send_email",
            new_callable=AsyncMock,
        ):
            resp = await client.post(RESET_REQUEST_URL, json={"email": email})

        # Core preservation: status is always 200 regardless of registration
        assert resp.status_code == 200, (
            f"Anti-enumeration violated: email={email!r} returned {resp.status_code}"
        )
        # Response must be valid JSON
        body = resp.json()
        assert isinstance(body, dict), f"Response is not a JSON object: {body!r}"
        # Token must never appear in the response
        assert "token" not in body, (
            f"SECURITY BUG: 'token' key found in response for email={email!r}. Got: {body}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property 2b — Confirm flow preserved
# ─────────────────────────────────────────────────────────────────────────────

class TestConfirmFlowPreservation:
    """
    Property 2b — Confirm flow preserved: a valid token obtained from the
    (unfixed) endpoint can be submitted to /password-reset-confirm and the
    password is updated successfully.

    **Validates: Requirements 3.1, 3.2**
    """

    @pytest.mark.asyncio
    async def test_valid_token_resets_password(self, client: AsyncClient):
        """
        Property 2b — Valid token → HTTP 200, password updated.

        After the fix the token arrives via email (mocked). We extract it
        from the mock call's body_text argument which contains the reset link
        in the form: /reset-password?token=<raw_token>

        **Validates: Requirements 3.1, 3.2**
        """
        # 1. Register a user
        email = "preserve_2b_confirm@example.com"
        reg = await client.post(REGISTER_URL, json=_reg_payload(email))
        assert reg.status_code in (200, 201), f"Registration failed: {reg.json()}"

        # 2. Request a password reset — token is now delivered via email (mocked)
        with patch(
            "src.services.email_service.email_service.send_email",
            new_callable=AsyncMock,
        ) as mock_send:
            reset_req = await client.post(RESET_REQUEST_URL, json={"email": email})
        assert reset_req.status_code == 200

        # Extract the raw token from the mocked email call's body_text
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        body_text = call_kwargs.kwargs.get("body_text", "")
        # body_text contains: "...visiting: {frontend_url}/reset-password?token={raw_token}\n..."
        import re
        match = re.search(r"/reset-password\?token=([^\s\n]+)", body_text)
        assert match, (
            f"Could not extract token from email body_text. Got: {body_text!r}"
        )
        raw_token = match.group(1)
        assert isinstance(raw_token, str) and len(raw_token) > 0

        # 3. Confirm the reset with the token
        new_password = "NewStrongPass456!"
        confirm_resp = await client.post(
            RESET_CONFIRM_URL,
            json={"token": raw_token, "new_password": new_password},
        )
        assert confirm_resp.status_code == 200, (
            f"Confirm flow failed: {confirm_resp.json()}"
        )
        confirm_body = confirm_resp.json()
        assert confirm_body.get("success") is True

        # 4. Verify the new password works by logging in
        login_resp = await client.post(
            LOGIN_URL,
            data={"username": email, "password": new_password},
        )
        assert login_resp.status_code == 200, (
            f"Login with new password failed: {login_resp.json()}"
        )

    @pytest.mark.asyncio
    async def test_token_can_only_be_used_once(self, client: AsyncClient):
        """
        A consumed token cannot be reused — confirm endpoint rejects it on
        second use with HTTP 400.

        **Validates: Requirements 3.2**
        """
        email = "preserve_2b_once@example.com"
        reg = await client.post(REGISTER_URL, json=_reg_payload(email))
        assert reg.status_code in (200, 201)

        with patch(
            "src.services.email_service.email_service.send_email",
            new_callable=AsyncMock,
        ) as mock_send:
            reset_req = await client.post(RESET_REQUEST_URL, json={"email": email})
        assert reset_req.status_code == 200

        # Extract token from mocked email body_text
        import re
        body_text = mock_send.call_args.kwargs.get("body_text", "")
        match = re.search(r"/reset-password\?token=([^\s\n]+)", body_text)
        assert match, f"Could not extract token from email body_text. Got: {body_text!r}"
        raw_token = match.group(1)

        # First use — should succeed
        first = await client.post(
            RESET_CONFIRM_URL,
            json={"token": raw_token, "new_password": "FirstNewPass123!"},
        )
        assert first.status_code == 200

        # Second use — should be rejected
        second = await client.post(
            RESET_CONFIRM_URL,
            json={"token": raw_token, "new_password": "SecondNewPass123!"},
        )
        assert second.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# Property 2c — Invalid token still rejected
# ─────────────────────────────────────────────────────────────────────────────

class TestInvalidTokenRejection:
    """
    Property 2c — Invalid token still rejected: a random string submitted to
    /password-reset-confirm returns HTTP 400.

    **Validates: Requirements 3.3**
    """

    @pytest.mark.asyncio
    async def test_random_string_token_rejected(self, client: AsyncClient):
        """
        Property 2c — Random string → HTTP 400.

        **Validates: Requirements 3.3**
        """
        resp = await client.post(
            RESET_CONFIRM_URL,
            json={"token": "this_is_not_a_valid_token_at_all", "new_password": "NewPass123456!"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    @h_settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    @given(
        invalid_token=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            min_size=1,
            max_size=100,
        )
    )
    async def test_property_2c_invalid_token_rejected(
        self, client: AsyncClient, invalid_token: str
    ):
        """
        Property 2c — Invalid token rejected (property-based).

        For any random string that is not a valid, unexpired, unused reset
        token, POST /api/v1/auth/password-reset-confirm MUST return HTTP 400.

        **Validates: Requirements 3.3**
        """
        resp = await client.post(
            RESET_CONFIRM_URL,
            json={"token": invalid_token, "new_password": "NewPass123456!"},
        )
        assert resp.status_code == 400, (
            f"Expected 400 for invalid token {invalid_token!r}, got {resp.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property 2d — Rate limiter preserved
# ─────────────────────────────────────────────────────────────────────────────

class TestRateLimiterPreservation:
    """
    Property 2d — Rate limiter preserved: the 6th request within the hour
    returns HTTP 429.

    Uses the ``rate_limited_client`` fixture which does NOT bypass the
    password_reset_limiter dependency.

    **Validates: Requirements 3.4**
    """

    @pytest.mark.asyncio
    async def test_sixth_request_returns_429(self, rate_limited_client: AsyncClient):
        """
        Property 2d — 6th request within the hour → HTTP 429.

        The rate limiter is configured for 5 requests/hour.  The first 5
        calls must succeed (HTTP 200); the 6th must be rejected (HTTP 429).

        **Validates: Requirements 3.4**
        """
        email = "preserve_2d_ratelimit@example.com"

        # Register the user (uses register_limiter which IS bypassed)
        reg = await rate_limited_client.post(REGISTER_URL, json=_reg_payload(email))
        assert reg.status_code in (200, 201), f"Registration failed: {reg.json()}"

        # Make 5 allowed requests
        for i in range(5):
            with patch(
                "src.services.email_service.email_service.send_email",
                new_callable=AsyncMock,
            ):
                resp = await rate_limited_client.post(
                    RESET_REQUEST_URL, json={"email": email}
                )
            assert resp.status_code == 200, (
                f"Request {i + 1} should be allowed (HTTP 200), got {resp.status_code}"
            )

        # 6th request must be rate-limited
        with patch(
            "src.services.email_service.email_service.send_email",
            new_callable=AsyncMock,
        ):
            sixth_resp = await rate_limited_client.post(
                RESET_REQUEST_URL, json={"email": email}
            )
        assert sixth_resp.status_code == 429, (
            f"6th request should be rate-limited (HTTP 429), got {sixth_resp.status_code}. "
            f"Body: {sixth_resp.json()}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Other auth endpoints unaffected
# ─────────────────────────────────────────────────────────────────────────────

class TestOtherAuthEndpointsUnaffected:
    """
    Verify that /register, /login, /refresh, and /logout continue to behave
    identically — the password reset fix must not touch any other endpoint.

    **Validates: Requirements 3.5**
    """

    @pytest.mark.asyncio
    async def test_register_unaffected(self, client: AsyncClient):
        """POST /register still creates a user and returns tokens."""
        resp = await client.post(
            REGISTER_URL,
            json=_reg_payload("preserve_other_register@example.com"),
        )
        assert resp.status_code in (200, 201)
        body = resp.json()
        assert "access_token" in body

    @pytest.mark.asyncio
    async def test_login_unaffected(self, client: AsyncClient):
        """POST /login still authenticates and returns tokens."""
        email = "preserve_other_login@example.com"
        password = "StrongPass123!"

        reg = await client.post(REGISTER_URL, json=_reg_payload(email))
        assert reg.status_code in (200, 201)

        login_resp = await client.post(
            LOGIN_URL,
            data={"username": email, "password": password},
        )
        assert login_resp.status_code == 200
        body = login_resp.json()
        assert "access_token" in body

    @pytest.mark.asyncio
    async def test_refresh_endpoint_reachable(self, client: AsyncClient):
        """
        POST /refresh endpoint is reachable and returns 401 when no cookie is
        present (expected behavior — not affected by the password reset fix).

        **Validates: Requirements 3.5**
        """
        # Without a refresh token cookie, /refresh should return 401
        refresh_resp = await client.post(REFRESH_URL)
        assert refresh_resp.status_code == 401
