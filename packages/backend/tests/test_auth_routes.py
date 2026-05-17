"""
HTTP integration tests for auth routes via AsyncClient + ASGITransport.

All tests use the in-memory SQLite test DB (no real Neon DB calls).
Login endpoint uses form-encoded data (OAuth2PasswordRequestForm).
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"
RESET_REQUEST_URL = "/api/v1/auth/password-reset-request"
RESET_CONFIRM_URL = "/api/v1/auth/password-reset-confirm"


def reg_payload(**kwargs):
    base = {
        "email": "user@example.com",
        "password": "StrongPass123!",
        "first_name": "Test",
        "last_name": "User",
    }
    base.update(kwargs)
    return base


def login_form(email="user@example.com", password="StrongPass123!"):
    """Form-encoded login payload for OAuth2PasswordRequestForm."""
    return {"username": email, "password": password}


# ── Registration ──────────────────────────────────────────────────────────────

class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post(REGISTER_URL, json=reg_payload())
        # Register returns 200 (JSONResponse overrides the 201 status_code on the decorator)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        await client.post(REGISTER_URL, json=reg_payload(email="dup@example.com"))
        resp = await client.post(REGISTER_URL, json=reg_payload(email="dup@example.com"))
        assert resp.status_code == 409
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "CONFLICT_EMAIL_EXISTS"

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        resp = await client.post(REGISTER_URL, json=reg_payload(password="short"))
        assert resp.status_code == 422
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        resp = await client.post(REGISTER_URL, json=reg_payload(email="not-an-email"))
        assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success_form_encoded(self, client: AsyncClient):
        await client.post(REGISTER_URL, json=reg_payload(email="login@example.com"))
        resp = await client.post(
            LOGIN_URL,
            data=login_form("login@example.com"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_login_json_body_rejected(self, client: AsyncClient):
        """Login must use form-encoded data, not JSON."""
        resp = await client.post(
            LOGIN_URL,
            json={"username": "login@example.com", "password": "StrongPass123!"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post(REGISTER_URL, json=reg_payload(email="wrongpw@example.com"))
        resp = await client.post(
            LOGIN_URL,
            data=login_form("wrongpw@example.com", "WrongPassword!"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 401
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
        assert resp.headers.get("www-authenticate") == "Bearer"

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        resp = await client.post(
            LOGIN_URL,
            data=login_form("nobody@example.com"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 401


# ── /me ───────────────────────────────────────────────────────────────────────

class TestMe:
    @pytest.mark.asyncio
    async def test_me_with_valid_token(self, client: AsyncClient):
        reg = await client.post(REGISTER_URL, json=reg_payload(email="me@example.com"))
        token = reg.json()["access_token"]
        resp = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "me@example.com"

    @pytest.mark.asyncio
    async def test_me_without_token(self, client: AsyncClient):
        resp = await client.get(ME_URL)
        assert resp.status_code == 401
        body = resp.json()
        assert body["success"] is False

    @pytest.mark.asyncio
    async def test_me_with_invalid_token(self, client: AsyncClient):
        resp = await client.get(ME_URL, headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401


# ── Token refresh ─────────────────────────────────────────────────────────────

class TestRefresh:
    @pytest.mark.asyncio
    async def test_refresh_success(self, client: AsyncClient):
        reg = await client.post(REGISTER_URL, json=reg_payload(email="refresh@example.com"))
        old_refresh = reg.json()["refresh_token"]

        # /refresh reads from the httpOnly cookie. The test client uses base_url="http://test"
        # but cookies are set with domain="localhost", so we must set the cookie manually.
        client.cookies.set("refresh_token", old_refresh)
        resp = await client.post(REFRESH_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_old_token_rejected(self, client: AsyncClient):
        reg = await client.post(REGISTER_URL, json=reg_payload(email="refresh2@example.com"))
        old_refresh = reg.json()["refresh_token"]

        await client.post(REFRESH_URL, json={"refresh_token": old_refresh})

        # Old token should now be invalid
        resp = await client.post(REFRESH_URL, json={"refresh_token": old_refresh})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client: AsyncClient):
        resp = await client.post(REFRESH_URL, json={"refresh_token": "bad_token"})
        assert resp.status_code == 401
        body = resp.json()
        assert body["success"] is False


# ── Logout ────────────────────────────────────────────────────────────────────

class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient):
        reg = await client.post(REGISTER_URL, json=reg_payload(email="logout@example.com"))
        # Logout reads the refresh_token from the httpOnly cookie set at login.
        # The client fixture shares cookies automatically.
        resp = await client.post(LOGOUT_URL)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_logout_invalidates_token(self, client: AsyncClient):
        reg = await client.post(REGISTER_URL, json=reg_payload(email="logout2@example.com"))
        # After logout the refresh cookie is cleared; a subsequent refresh must fail.
        await client.post(LOGOUT_URL)
        resp = await client.post(REFRESH_URL)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_invalid_token(self, client: AsyncClient):
        # No cookie present — logout should still return 200 (idempotent)
        resp = await client.post(LOGOUT_URL)
        assert resp.status_code == 200


# ── Password reset ────────────────────────────────────────────────────────────

class TestPasswordReset:
    @pytest.mark.asyncio
    async def test_reset_request_registered_email(self, client: AsyncClient):
        await client.post(REGISTER_URL, json=reg_payload(email="reset@example.com"))
        with patch(
            "src.services.email_service.email_service.send_email",
            new_callable=AsyncMock,
        ):
            resp = await client.post(RESET_REQUEST_URL, json={"email": "reset@example.com"})
        assert resp.status_code == 200
        data = resp.json()
        # Token must NOT be in the response — it is delivered via email
        assert "token" not in data
        assert data.get("success") is True

    @pytest.mark.asyncio
    async def test_reset_request_unregistered_email(self, client: AsyncClient):
        """Should return 200 even for unknown emails (no enumeration)."""
        resp = await client.post(RESET_REQUEST_URL, json={"email": "nobody@example.com"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_reset_confirm_success(self, client: AsyncClient):
        await client.post(REGISTER_URL, json=reg_payload(email="resetconfirm@example.com"))
        with patch(
            "src.services.email_service.email_service.send_email",
            new_callable=AsyncMock,
        ) as mock_send:
            req = await client.post(RESET_REQUEST_URL, json={"email": "resetconfirm@example.com"})
        assert req.status_code == 200

        # Extract token from the mocked email body_text
        import re
        body_text = mock_send.call_args.kwargs.get("body_text", "")
        match = re.search(r"/reset-password\?token=([^\s\n]+)", body_text)
        assert match, f"Could not extract token from email body_text: {body_text!r}"
        token = match.group(1)

        resp = await client.post(
            RESET_CONFIRM_URL,
            json={"token": token, "new_password": "NewStrongPass456!"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_reset_confirm_invalid_token(self, client: AsyncClient):
        resp = await client.post(
            RESET_CONFIRM_URL,
            json={"token": "bad_token", "new_password": "NewStrongPass456!"},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["success"] is False

    @pytest.mark.asyncio
    async def test_reset_confirm_weak_password(self, client: AsyncClient):
        await client.post(REGISTER_URL, json=reg_payload(email="resetweak@example.com"))
        with patch(
            "src.services.email_service.email_service.send_email",
            new_callable=AsyncMock,
        ) as mock_send:
            req = await client.post(RESET_REQUEST_URL, json={"email": "resetweak@example.com"})
        assert req.status_code == 200

        # Extract token from the mocked email body_text
        import re
        body_text = mock_send.call_args.kwargs.get("body_text", "")
        match = re.search(r"/reset-password\?token=([^\s\n]+)", body_text)
        assert match, f"Could not extract token from email body_text: {body_text!r}"
        token = match.group(1)

        resp = await client.post(
            RESET_CONFIRM_URL,
            json={"token": token, "new_password": "weak"},
        )
        assert resp.status_code == 422
