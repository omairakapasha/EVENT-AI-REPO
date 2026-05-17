"""
Bug Condition Exploration Test — AUTH-03: Email Verified Route Guard

Property 1: Bug Condition — Unverified User Accesses Protected Route

CRITICAL: This test MUST FAIL on unfixed code — failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

This test encodes the expected behavior (403 + AUTH_EMAIL_NOT_VERIFIED).
It will validate the fix when it passes after implementation.

GOAL: Surface counterexamples that demonstrate that an unverified user currently
receives 2xx on protected routes instead of the expected 403.

Bug Condition (isBugCondition):
  - user.is_active is True
  - user.email_verified is False
  - token is valid and non-expired

Validates: Requirements 1.1, 1.2, 1.3
"""
import pytest
from httpx import AsyncClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"
BOOKINGS_URL = "/api/v1/bookings/"
EVENTS_URL = "/api/v1/events/"


async def _register_and_login_unverified(client: AsyncClient, email: str) -> str:
    """Register, skip verification, login — produces the bug condition."""
    reg = await client.post(REGISTER_URL, json={
        "email": email, "password": "StrongPass123!",
        "first_name": "Unverified", "last_name": "User",
    })
    assert reg.status_code == 200, f"Registration failed: {reg.status_code} {reg.text}"

    login = await client.post(
        LOGIN_URL,
        data={"username": email, "password": "StrongPass123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, f"Login failed: {login.status_code} {login.text}"
    return login.json()["access_token"]


def _assert_403(response, endpoint: str) -> None:
    """Assert the response is a 403 AUTH_EMAIL_NOT_VERIFIED."""
    assert response.status_code == 403, (
        f"COUNTEREXAMPLE: {endpoint} with unverified JWT returned "
        f"{response.status_code} instead of 403. Body: {response.text}"
    )
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "AUTH_EMAIL_NOT_VERIFIED"
    assert body["error"]["message"] == "Email address has not been verified."


class TestBugConditionUnverifiedUserAccessesProtectedRoute:
    """
    Property 1: Bug Condition — Unverified User Accesses Protected Route

    All three endpoint checks share a single register+login cycle to minimise
    test runtime. These tests FAIL on unfixed code — that failure is the
    SUCCESS case confirming the bug exists.

    Validates: Requirements 1.1, 1.2, 1.3
    """

    @pytest.mark.asyncio
    async def test_unverified_user_blocked_on_protected_routes(self, client: AsyncClient):
        """
        Single token, three protected endpoints — all must return 403.

        Counterexamples on unfixed code:
          GET  /api/v1/auth/me   → 200 OK   (expected 403)
          POST /api/v1/bookings/ → 422       (expected 403)
          POST /api/v1/events/   → 422       (expected 403)

        isBugCondition: is_active=True, email_verified=False, token valid+non-expired
        """
        token = await _register_and_login_unverified(client, "unverified_bug@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        _assert_403(await client.get(ME_URL, headers=headers), "GET /api/v1/auth/me")
        _assert_403(await client.post(BOOKINGS_URL, json={}, headers=headers), "POST /api/v1/bookings/")
        _assert_403(await client.post(EVENTS_URL, json={}, headers=headers), "POST /api/v1/events/")
