"""
Preservation Property Tests — AUTH-03: Email Verified Route Guard
=================================================================

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

These tests capture the BASELINE behaviour of the unfixed code on non-buggy
inputs.  They are written BEFORE the fix is applied and must ALL PASS on
unfixed code.  After the fix is applied (task 3.3), they must STILL PASS —
confirming no regressions were introduced.

Properties tested:
  2a — Verified user gets 200: email_verified=True user → HTTP 200 on protected routes
  2b — Invalid/expired JWT gets 401: malformed token → HTTP 401 AUTH_UNAUTHORIZED
  2c — Inactive user gets 401: is_active=False user → HTTP 401
  2d — Public endpoints unaffected: /register and /login work without email verification
  2e — get_current_user_optional with unverified user returns user object (not None, not 403)

Observation-first methodology: each case was run on unfixed code first to record
the actual response, then the assertion was written to match that baseline.
"""
import pytest
import pytest_asyncio
from typing import AsyncGenerator

from httpx import AsyncClient
from hypothesis import given, settings as h_settings, HealthCheck
from hypothesis import strategies as st
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User


# ── URL constants ─────────────────────────────────────────────────────────────

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _reg_payload(email: str, first_name: str = "Preserve", last_name: str = "Tester") -> dict:
    return {
        "email": email,
        "password": "StrongPass123!",
        "first_name": first_name,
        "last_name": last_name,
    }


def _login_form(email: str) -> dict:
    """Form-encoded login payload for OAuth2PasswordRequestForm."""
    return {"username": email, "password": "StrongPass123!"}


async def _register_verify_and_login(
    client: AsyncClient,
    db_session: AsyncSession,
    email: str,
    first_name: str = "Preserve",
    last_name: str = "Tester",
) -> str:
    """
    Register a user, set email_verified=True directly on the DB row, then login.
    Returns the access_token.
    """
    # Step 1: Register
    reg_resp = await client.post(REGISTER_URL, json=_reg_payload(email, first_name, last_name))
    assert reg_resp.status_code == 201, (
        f"Registration failed: {reg_resp.status_code} {reg_resp.text}"
    )

    # Step 2: Set email_verified=True directly on the DB row
    await db_session.execute(
        update(User).where(User.email == email).values(email_verified=True)
    )
    await db_session.commit()

    # Step 3: Login with form-encoded data
    login_resp = await client.post(
        LOGIN_URL,
        data=_login_form(email),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200, (
        f"Login failed: {login_resp.status_code} {login_resp.text}"
    )
    token = login_resp.json()["access_token"]
    assert token, "Expected a non-empty access_token from login"
    return token


async def _register_and_login_unverified(client: AsyncClient, email: str) -> str:
    """
    Register a user, skip email verification, then login.
    Returns the access_token.
    """
    reg_resp = await client.post(REGISTER_URL, json=_reg_payload(email))
    assert reg_resp.status_code == 201, (
        f"Registration failed: {reg_resp.status_code} {reg_resp.text}"
    )
    login_resp = await client.post(
        LOGIN_URL,
        data=_login_form(email),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200, (
        f"Login failed: {login_resp.status_code} {login_resp.text}"
    )
    return login_resp.json()["access_token"]


# ─────────────────────────────────────────────────────────────────────────────
# Property 2a — Verified user gets 200
# ─────────────────────────────────────────────────────────────────────────────

class TestVerifiedUserPreservation:
    """
    Property 2a — Verified user gets 200: a user with email_verified=True and
    is_active=True presenting a valid JWT SHALL continue to receive 200 OK on
    protected routes.

    Baseline observation (unfixed code): verified user → 200 OK on GET /api/v1/auth/me.
    This behavior must be preserved after the fix.

    **Validates: Requirements 3.1**
    """

    @pytest.mark.asyncio
    async def test_verified_user_gets_200_on_me(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        Property 2a — Deterministic case: verified user → HTTP 200 on GET /api/v1/auth/me.

        Baseline observation: register → set email_verified=True → login → GET /me → 200 OK.

        **Validates: Requirements 3.1**
        """
        token = await _register_verify_and_login(
            client, db_session, "preserve_2a_verified@example.com"
        )
        resp = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, (
            f"Verified user should get 200 on /me, got {resp.status_code}. "
            f"Body: {resp.text}"
        )
        body = resp.json()
        assert body["email"] == "preserve_2a_verified@example.com"
        assert body["email_verified"] is True

    @pytest.mark.asyncio
    @h_settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    @given(
        first_name=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll"), min_codepoint=65, max_codepoint=122),
            min_size=1,
            max_size=20,
        ),
        last_name=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll"), min_codepoint=65, max_codepoint=122),
            min_size=1,
            max_size=20,
        ),
        uid=st.integers(min_value=1000, max_value=9999),
    )
    async def test_property_2a_verified_user_always_gets_200(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        first_name: str,
        last_name: str,
        uid: int,
    ):
        """
        Property 2a — Verified user preservation (property-based).

        For any user with email_verified=True and is_active=True presenting a
        valid JWT, GET /api/v1/auth/me MUST return HTTP 200.

        Generates arbitrary verified users (different names, unique emails) and
        asserts 200 on the protected route.

        **Validates: Requirements 3.1**
        """
        email = f"pbt_2a_{uid}_{first_name[:3].lower()}@example.com"

        # Register the user
        reg_resp = await client.post(
            REGISTER_URL,
            json=_reg_payload(email, first_name, last_name),
        )
        # Skip if email already registered (hypothesis may generate duplicate uid)
        if reg_resp.status_code == 409:
            return
        assert reg_resp.status_code == 201, (
            f"Registration failed: {reg_resp.status_code} {reg_resp.text}"
        )

        # Set email_verified=True directly on the DB row
        await db_session.execute(
            update(User).where(User.email == email).values(email_verified=True)
        )
        await db_session.commit()

        # Login
        login_resp = await client.post(
            LOGIN_URL,
            data=_login_form(email),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_resp.status_code == 200, (
            f"Login failed: {login_resp.status_code} {login_resp.text}"
        )
        token = login_resp.json()["access_token"]

        # Assert 200 on protected route
        resp = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, (
            f"PRESERVATION VIOLATED: verified user (email={email!r}, "
            f"first_name={first_name!r}, last_name={last_name!r}) "
            f"got {resp.status_code} instead of 200. Body: {resp.text}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property 2b — Invalid/expired JWT gets 401
# ─────────────────────────────────────────────────────────────────────────────

class TestInvalidJWTPreservation:
    """
    Property 2b — Invalid/expired JWT gets 401: a request with a missing,
    malformed, or expired JWT SHALL continue to receive 401 with error code
    AUTH_UNAUTHORIZED.

    Baseline observation (unfixed code): malformed token → 401 AUTH_UNAUTHORIZED.
    This behavior must be preserved after the fix.

    **Validates: Requirements 3.2**
    """

    @pytest.mark.asyncio
    async def test_malformed_token_gets_401(self, client: AsyncClient):
        """
        Property 2b — Deterministic case: malformed token → HTTP 401 AUTH_UNAUTHORIZED.

        Baseline observation: send "not.a.valid.jwt" → 401 with AUTH_UNAUTHORIZED.

        **Validates: Requirements 3.2**
        """
        resp = await client.get(
            ME_URL,
            headers={"Authorization": "Bearer not.a.valid.jwt"},
        )
        assert resp.status_code == 401, (
            f"Malformed token should get 401, got {resp.status_code}. Body: {resp.text}"
        )
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] in ("AUTH_UNAUTHORIZED", "AUTH_CREDENTIALS_INVALID")

    @pytest.mark.asyncio
    async def test_no_token_gets_401(self, client: AsyncClient):
        """
        Property 2b — No token → HTTP 401.

        Baseline observation: no Authorization header → 401.

        **Validates: Requirements 3.2**
        """
        resp = await client.get(ME_URL)
        assert resp.status_code == 401, (
            f"No token should get 401, got {resp.status_code}. Body: {resp.text}"
        )
        body = resp.json()
        assert body["success"] is False

    @pytest.mark.asyncio
    @h_settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    @given(
        invalid_token=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=32, max_codepoint=126),
            min_size=1,
            max_size=200,
        ).filter(lambda t: "." in t or len(t) < 10)
    )
    async def test_property_2b_invalid_token_always_gets_401(
        self, client: AsyncClient, invalid_token: str
    ):
        """
        Property 2b — Invalid JWT preservation (property-based).

        For any string that is not a valid, non-expired JWT, GET /api/v1/auth/me
        MUST return HTTP 401.

        **Validates: Requirements 3.2**
        """
        resp = await client.get(
            ME_URL,
            headers={"Authorization": f"Bearer {invalid_token}"},
        )
        assert resp.status_code == 401, (
            f"PRESERVATION VIOLATED: invalid token {invalid_token!r} "
            f"got {resp.status_code} instead of 401. Body: {resp.text}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property 2c — Inactive user gets 401
# ─────────────────────────────────────────────────────────────────────────────

class TestInactiveUserPreservation:
    """
    Property 2c — Inactive user gets 401: a user with is_active=False presenting
    a valid JWT SHALL continue to receive 401.

    Baseline observation (unfixed code): inactive user → 401 on GET /api/v1/auth/me.
    This behavior must be preserved after the fix.

    **Validates: Requirements 3.3**
    """

    @pytest.mark.asyncio
    async def test_inactive_user_gets_401(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        Property 2c — Inactive user → HTTP 401.

        Baseline observation:
          register → set is_active=False → login → GET /me → 401.

        Note: login succeeds because the login endpoint checks is_active differently
        (or the token is issued before the is_active check in verify_access_token).
        The 401 is returned when the token is used on a protected route.

        **Validates: Requirements 3.3**
        """
        email = "preserve_2c_inactive@example.com"

        # Step 1: Register
        reg_resp = await client.post(REGISTER_URL, json=_reg_payload(email))
        assert reg_resp.status_code == 201, (
            f"Registration failed: {reg_resp.status_code} {reg_resp.text}"
        )

        # Step 2: Login to get a valid token BEFORE deactivating
        login_resp = await client.post(
            LOGIN_URL,
            data=_login_form(email),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_resp.status_code == 200, (
            f"Login failed: {login_resp.status_code} {login_resp.text}"
        )
        token = login_resp.json()["access_token"]

        # Step 3: Set is_active=False directly on the DB row
        await db_session.execute(
            update(User).where(User.email == email).values(is_active=False)
        )
        await db_session.commit()

        # Step 4: Use the token on a protected route — should get 401
        resp = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401, (
            f"Inactive user should get 401 on /me, got {resp.status_code}. "
            f"Body: {resp.text}"
        )
        body = resp.json()
        assert body["success"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Property 2d — Public endpoints unaffected
# ─────────────────────────────────────────────────────────────────────────────

class TestPublicEndpointsPreservation:
    """
    Property 2d — Public endpoints unaffected: POST /api/v1/auth/register and
    POST /api/v1/auth/login do not require email verification and continue to
    work without any token.

    Baseline observation (unfixed code):
      - POST /register → 200 (no token required)
      - POST /login → 200 (no email verification required)

    This behavior must be preserved after the fix.

    **Validates: Requirements 3.4**
    """

    @pytest.mark.asyncio
    async def test_register_works_without_email_verification(self, client: AsyncClient):
        """
        Property 2d — POST /register works without email verification.

        Baseline observation: POST /register → 200 with access_token.
        Unverified users can still register and receive tokens.

        **Validates: Requirements 3.4**
        """
        resp = await client.post(
            REGISTER_URL,
            json=_reg_payload("preserve_2d_register@example.com"),
        )
        assert resp.status_code == 201, (
            f"Register should return 201, got {resp.status_code}. Body: {resp.text}"
        )
        body = resp.json()
        assert "access_token" in body, (
            f"Register response should contain access_token. Got: {body}"
        )

    @pytest.mark.asyncio
    async def test_login_works_for_unverified_user(self, client: AsyncClient):
        """
        Property 2d — POST /login works for unverified users.

        Baseline observation: unverified user can login and receive tokens.
        The login endpoint does not check email_verified.

        **Validates: Requirements 3.4**
        """
        email = "preserve_2d_login@example.com"

        # Register (email_verified defaults to False)
        reg_resp = await client.post(REGISTER_URL, json=_reg_payload(email))
        assert reg_resp.status_code == 201

        # Login without verifying email — should succeed
        login_resp = await client.post(
            LOGIN_URL,
            data=_login_form(email),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_resp.status_code == 200, (
            f"Login should return 200 for unverified user, got {login_resp.status_code}. "
            f"Body: {login_resp.text}"
        )
        body = login_resp.json()
        assert "access_token" in body, (
            f"Login response should contain access_token. Got: {body}"
        )

    @pytest.mark.asyncio
    async def test_register_and_login_require_no_token(self, client: AsyncClient):
        """
        Property 2d — /register and /login are public endpoints (no auth required).

        Baseline observation: both endpoints work without any Authorization header.

        **Validates: Requirements 3.4**
        """
        email = "preserve_2d_notoken@example.com"

        # Register without any token
        reg_resp = await client.post(
            REGISTER_URL,
            json=_reg_payload(email),
            # No Authorization header
        )
        assert reg_resp.status_code == 201, (
            f"Register should work without token, got {reg_resp.status_code}"
        )

        # Login without any token
        login_resp = await client.post(
            LOGIN_URL,
            data=_login_form(email),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            # No Authorization header
        )
        assert login_resp.status_code == 200, (
            f"Login should work without token, got {login_resp.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property 2e — get_current_user_optional with unverified user returns user object
# ─────────────────────────────────────────────────────────────────────────────

class TestOptionalAuthPreservation:
    """
    Property 2e — get_current_user_optional with unverified user returns user object:
    when an authenticated but unverified user calls an optional-auth endpoint,
    the user object is present (not None, not 403).

    Baseline observation (unfixed code): get_current_user_optional with unverified
    user → returns the User object (not None, not an exception).

    This behavior must be preserved after the fix. The fix adds a 403 guard in
    get_current_user; get_current_user_optional catches HTTPException and returns
    None. But per requirement 3.5, it must return the user object for unverified
    users — meaning the 403 must NOT be raised in get_current_user_optional's path.

    NOTE: Since no route currently uses get_current_user_optional, we test the
    function directly by calling it with a mock request object.

    **Validates: Requirements 3.5**
    """

    @pytest.mark.asyncio
    async def test_optional_auth_unverified_user_returns_user_object(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        Property 2e — get_current_user_optional with unverified user returns user object.

        Baseline observation:
          register → skip verification → login → call get_current_user_optional
          with the token → returns User object (not None, not 403).

        We test this by calling get_current_user_optional directly with a mock
        request carrying the unverified user's token.

        The function is in auth.middleware.py (dot in filename) so we load it
        via importlib.util.spec_from_file_location.

        **Validates: Requirements 3.5**
        """
        import importlib.util
        import sys
        import os
        from unittest.mock import MagicMock
        from fastapi.security import HTTPAuthorizationCredentials

        email = "preserve_2e_optional@example.com"

        # Step 1: Register (email_verified defaults to False)
        reg_resp = await client.post(REGISTER_URL, json=_reg_payload(email))
        assert reg_resp.status_code == 201

        # Step 2: Login to get a valid token (skip email verification)
        login_resp = await client.post(
            LOGIN_URL,
            data=_login_form(email),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        # Step 3: Load auth.middleware module (dot in filename requires importlib)
        src_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if src_root not in sys.path:
            sys.path.insert(0, src_root)
        middleware_path = os.path.join(src_root, "src", "middleware", "auth.middleware.py")
        middleware_path = os.path.abspath(middleware_path)
        spec = importlib.util.spec_from_file_location("auth_middleware_module", middleware_path)
        auth_middleware_module = importlib.util.module_from_spec(spec)
        # Register in sys.modules so internal imports resolve correctly
        sys.modules["auth_middleware_module"] = auth_middleware_module
        spec.loader.exec_module(auth_middleware_module)

        get_current_user_optional = auth_middleware_module.get_current_user_optional

        # Step 4: Build a mock request with the token
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = None  # no cookie

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Step 5: Call get_current_user_optional directly
        result = await get_current_user_optional(
            request=mock_request,
            credentials=credentials,
            session=db_session,
        )

        # Step 6: Assert the user object is returned (not None, not an exception)
        assert result is not None, (
            "PRESERVATION VIOLATED: get_current_user_optional returned None for "
            "an unverified user with a valid token. Expected the User object."
        )
        assert hasattr(result, "email"), (
            f"Expected a User object, got: {result!r}"
        )
        assert result.email == email, (
            f"Expected user email {email!r}, got {result.email!r}"
        )
        assert result.email_verified is False, (
            "User should still be unverified in this test"
        )

    @pytest.mark.asyncio
    async def test_optional_auth_no_token_returns_none(self, client: AsyncClient):
        """
        Property 2e — get_current_user_optional with no token returns None.

        Baseline observation: no token → None (not an exception).
        This is the expected behavior for optional auth endpoints.

        **Validates: Requirements 3.5**
        """
        import importlib.util
        import sys
        import os
        from unittest.mock import MagicMock

        # Load auth.middleware module (dot in filename requires importlib)
        src_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if src_root not in sys.path:
            sys.path.insert(0, src_root)
        middleware_path = os.path.join(src_root, "src", "middleware", "auth.middleware.py")
        middleware_path = os.path.abspath(middleware_path)
        spec = importlib.util.spec_from_file_location("auth_middleware_module2", middleware_path)
        auth_middleware_module = importlib.util.module_from_spec(spec)
        sys.modules["auth_middleware_module2"] = auth_middleware_module
        spec.loader.exec_module(auth_middleware_module)

        get_current_user_optional = auth_middleware_module.get_current_user_optional

        # No credentials, no cookie
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = None

        result = await get_current_user_optional(
            request=mock_request,
            credentials=None,
            session=None,  # session not needed when no token
        )

        assert result is None, (
            f"get_current_user_optional with no token should return None, got: {result!r}"
        )
