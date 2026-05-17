"""
Password Reset Token Exposure — Fix Verification Tests
=======================================================

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

These tests verify the CORRECT post-fix behaviour of
POST /api/v1/auth/password-reset-request.

The original bug-condition assertions (token IS present in response/logs,
email service NOT called) have been updated to assert the fixed behaviour:
  - "token" NOT in response body
  - response.json()["success"] is True
  - email_service.send_email IS called with correct to/subject
  - No structlog record contains key "token" with the raw token value

Counterexamples from the original exploration (task 1) that confirmed the bug:
  - response.json()["token"] was a non-empty URL-safe string for registered emails
  - response.json()["token"] == "dummy_token_for_security" for unregistered emails
  - email_service.send_email was never called (TODO was never implemented)
  - structlog emitted a record with key "token" containing the raw token value
"""
import pytest
import structlog.testing
from unittest.mock import AsyncMock, patch, call
from httpx import AsyncClient


REGISTER_URL = "/api/v1/auth/register"
RESET_REQUEST_URL = "/api/v1/auth/password-reset-request"
RESET_CONFIRM_URL = "/api/v1/auth/password-reset-confirm"


def _reg_payload(email: str) -> dict:
    return {
        "email": email,
        "password": "StrongPass123!",
        "first_name": "Fix",
        "last_name": "Verifier",
    }


class TestPasswordResetTokenExposureFixed:
    """
    Property 1: Expected Behavior — Token NOT in Response or Logs

    All four cases verify the fix is in place.
    These assertions PASS on fixed code and FAIL on unfixed code.
    """

    @pytest.mark.asyncio
    async def test_case1_registered_email_token_not_in_response(self, client: AsyncClient):
        """
        Case 1 — Registered email: token NOT in response body.

        FIX VERIFICATION: The raw reset token must NOT appear in the HTTP
        response body. The response must be a SuccessResponse with
        success=True and no "token" field.

        EXPECTED ON FIXED CODE: PASS
        EXPECTED ON UNFIXED CODE: FAIL ("token" would be in response)

        Validates: Requirements 2.1, 2.4
        """
        reg_resp = await client.post(REGISTER_URL, json=_reg_payload("fixtest1@example.com"))
        assert reg_resp.status_code in (200, 201), f"Registration failed: {reg_resp.json()}"

        with patch(
            "src.services.email_service.email_service.send_email",
            new_callable=AsyncMock,
        ):
            resp = await client.post(RESET_REQUEST_URL, json={"email": "fixtest1@example.com"})

        assert resp.status_code == 200
        body = resp.json()

        # FIX VERIFICATION: token must NOT be in the response
        assert "token" not in body, (
            f"SECURITY BUG: 'token' key found in response body. "
            f"The fix was not applied correctly. Got: {body}"
        )
        # FIX VERIFICATION: response must be a SuccessResponse
        assert body.get("success") is True, (
            f"Expected success=True in response, got: {body}"
        )

    @pytest.mark.asyncio
    async def test_case2_registered_email_token_not_in_logs(self, client: AsyncClient):
        """
        Case 2 — Registered email: token NOT in structlog records.

        FIX VERIFICATION: No structlog record emitted during the request
        should contain a "token" key with the raw token value.

        EXPECTED ON FIXED CODE: PASS
        EXPECTED ON UNFIXED CODE: FAIL (log record with token= would exist)

        Validates: Requirement 2.3
        """
        reg_resp = await client.post(REGISTER_URL, json=_reg_payload("fixtest2@example.com"))
        assert reg_resp.status_code in (200, 201), f"Registration failed: {reg_resp.json()}"

        with patch(
            "src.services.email_service.email_service.send_email",
            new_callable=AsyncMock,
        ):
            with structlog.testing.capture_logs() as captured_logs:
                resp = await client.post(RESET_REQUEST_URL, json={"email": "fixtest2@example.com"})
                assert resp.status_code == 200

        # FIX VERIFICATION: no log record should contain a raw token value
        token_log_records = [
            record for record in captured_logs
            if "token" in record and isinstance(record["token"], str) and len(record["token"]) > 0
        ]
        assert len(token_log_records) == 0, (
            f"SECURITY BUG: Log record(s) with raw 'token' key found. "
            f"The fix was not applied correctly. Records: {token_log_records}"
        )

    @pytest.mark.asyncio
    async def test_case3_unregistered_email_token_not_in_response(self, client: AsyncClient):
        """
        Case 3 — Unregistered email: token NOT in response body.

        FIX VERIFICATION: For unregistered emails, the response must be a
        SuccessResponse with no "token" field — the dummy_token_for_security
        anti-enumeration leak must be gone.

        EXPECTED ON FIXED CODE: PASS
        EXPECTED ON UNFIXED CODE: FAIL (dummy_token_for_security would be present)

        Validates: Requirements 2.4, 3.3
        """
        resp = await client.post(
            RESET_REQUEST_URL,
            json={"email": "notregistered_fixtest@example.com"},
        )
        assert resp.status_code == 200
        body = resp.json()

        # FIX VERIFICATION: token must NOT be in the response for unregistered emails
        assert "token" not in body, (
            f"SECURITY BUG: 'token' key found in response for unregistered email. "
            f"Got: {body}"
        )
        assert body.get("success") is True, (
            f"Expected success=True in response, got: {body}"
        )

    @pytest.mark.asyncio
    async def test_case4_email_service_called_for_registered_email(self, client: AsyncClient):
        """
        Case 4 — Email service IS called for registered email.

        FIX VERIFICATION: email_service.send_email() must be called exactly
        once with the correct to= and subject= arguments. The body_text must
        contain the reset link with /reset-password?token=.

        EXPECTED ON FIXED CODE: PASS
        EXPECTED ON UNFIXED CODE: FAIL (email_service.send_email would not be called)

        Validates: Requirement 2.2
        """
        reg_resp = await client.post(REGISTER_URL, json=_reg_payload("fixtest4@example.com"))
        assert reg_resp.status_code in (200, 201), f"Registration failed: {reg_resp.json()}"

        with patch(
            "src.services.email_service.email_service.send_email",
            new_callable=AsyncMock,
        ) as mock_send_email:
            resp = await client.post(
                RESET_REQUEST_URL,
                json={"email": "fixtest4@example.com"},
            )
            assert resp.status_code == 200

            # FIX VERIFICATION: email_service.send_email WAS called
            mock_send_email.assert_called_once()
            call_kwargs = mock_send_email.call_args

            # Verify correct recipient
            assert call_kwargs.kwargs.get("to") == "fixtest4@example.com" or (
                len(call_kwargs.args) > 0 and call_kwargs.args[0] == "fixtest4@example.com"
            ), f"email_service.send_email called with wrong 'to': {call_kwargs}"

            # Verify correct subject
            subject = call_kwargs.kwargs.get("subject") or (
                call_kwargs.args[1] if len(call_kwargs.args) > 1 else None
            )
            assert subject == "Reset your Event-AI password", (
                f"email_service.send_email called with wrong subject: {subject!r}"
            )

            # Verify reset link is in body_text
            body_text = call_kwargs.kwargs.get("body_text", "")
            assert "/reset-password?token=" in body_text, (
                f"Reset link not found in body_text. Got: {body_text!r}"
            )

    @pytest.mark.asyncio
    async def test_email_service_not_called_for_unregistered_email(self, client: AsyncClient):
        """
        Unregistered email: email_service.send_email must NOT be called.

        Anti-enumeration: we return the same SuccessResponse but do not
        attempt to send an email to an address that is not in the system.

        Validates: Requirements 2.4, 3.3
        """
        with patch(
            "src.services.email_service.email_service.send_email",
            new_callable=AsyncMock,
        ) as mock_send_email:
            resp = await client.post(
                RESET_REQUEST_URL,
                json={"email": "unregistered_nomail@example.com"},
            )
            assert resp.status_code == 200
            mock_send_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_response_shape_identical_for_registered_and_unregistered(
        self, client: AsyncClient
    ):
        """
        Anti-enumeration: response shape is identical for registered and
        unregistered emails — callers cannot distinguish them.

        Validates: Requirements 2.4, 3.3
        """
        # Register a user
        reg_resp = await client.post(REGISTER_URL, json=_reg_payload("fixtest_shape@example.com"))
        assert reg_resp.status_code in (200, 201)

        with patch(
            "src.services.email_service.email_service.send_email",
            new_callable=AsyncMock,
        ):
            registered_resp = await client.post(
                RESET_REQUEST_URL, json={"email": "fixtest_shape@example.com"}
            )
        unregistered_resp = await client.post(
            RESET_REQUEST_URL, json={"email": "unregistered_shape@example.com"}
        )

        assert registered_resp.status_code == 200
        assert unregistered_resp.status_code == 200

        reg_body = registered_resp.json()
        unreg_body = unregistered_resp.json()

        # Both must have success=True and no token field
        assert reg_body.get("success") is True
        assert unreg_body.get("success") is True
        assert "token" not in reg_body
        assert "token" not in unreg_body

        # Message must be identical (no enumeration via message text)
        assert reg_body.get("message") == unreg_body.get("message"), (
            f"Response messages differ — enumeration possible. "
            f"Registered: {reg_body.get('message')!r}, "
            f"Unregistered: {unreg_body.get('message')!r}"
        )
