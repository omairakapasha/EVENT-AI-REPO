# Implementation Plan

## Overview

This task list implements the fix for the password reset token exposure vulnerability in `POST /api/v1/auth/password-reset-request`. The fix follows the exploratory bugfix workflow: first surface counterexamples confirming the bug, then capture preservation baselines, then apply the targeted code changes, and finally validate everything passes.

## Task Dependency Graph

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1"] },
    { "wave": 2, "tasks": ["2"] },
    { "wave": 3, "tasks": ["3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7", "3.8", "3.9"] },
    { "wave": 4, "tasks": ["3.10", "3.11"] },
    { "wave": 5, "tasks": ["4"] }
  ]
}
```

## Tasks

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Token Exposed in Response and Logs
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the raw token appears in the HTTP response body and in plaintext log records
  - **Scoped PBT Approach**: Scope the property to the concrete failing cases — registered email and unregistered email — to ensure reproducibility
  - Create a test file at `packages/backend/tests/test_password_reset_token_exposure.py`
  - Use the existing `client` fixture from `conftest.py` (AsyncClient with DB + rate-limit overrides)
  - Register a test user via `POST /api/v1/auth/register` to obtain a registered email
  - **Case 1 — Registered email, token in response**: POST `{"email": "<registered>"}` to `/api/v1/auth/password-reset-request`; assert `"token" in response.json()` — this confirms the bug is present
  - **Case 2 — Registered email, token in logs**: Capture structlog output during the request (use `structlog.testing.capture_logs()`); assert a log record exists with key `"token"` containing a non-empty string value
  - **Case 3 — Unregistered email, dummy token in response**: POST `{"email": "notregistered@example.com"}` to `/api/v1/auth/password-reset-request`; assert `response.json()["token"] == "dummy_token_for_security"`
  - **Case 4 — Email service not called**: Mock `email_service.send_email` with `unittest.mock.AsyncMock`; POST with a registered email; assert the mock was NOT called — confirming the TODO was never implemented
  - Run tests on UNFIXED code: `uv run pytest packages/backend/tests/test_password_reset_token_exposure.py -v`
  - **EXPECTED OUTCOME**: All four assertions PASS on unfixed code (they confirm the bug exists); the test file itself is the counterexample documentation
  - Document counterexamples found (e.g., `response.json()["token"]` is a non-empty URL-safe string for registered emails; `"dummy_token_for_security"` for unregistered emails; `email_service.send_email` never called)
  - Mark task complete when test is written, run, and failure mode is documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Anti-Enumeration and Downstream Flows Unchanged
  - **IMPORTANT**: Follow observation-first methodology — run UNFIXED code with non-buggy inputs and record actual outputs before writing assertions
  - **Observe on UNFIXED code**:
    - `POST /api/v1/auth/password-reset-request` with an unregistered email → HTTP 200 (anti-enumeration holds even on unfixed code)
    - `POST /api/v1/auth/password-reset-confirm` with a valid token → HTTP 200, password updated
    - `POST /api/v1/auth/password-reset-confirm` with an invalid token → HTTP 400 with `AUTH_RESET_TOKEN_INVALID`
    - Rate limiter: 6th request within the hour → HTTP 429
    - Other auth endpoints (`/register`, `/login`, `/refresh`, `/logout`) → unchanged responses
  - **Write property-based tests** capturing observed behavior patterns from Preservation Requirements in design:
    - **Property 2a — Anti-enumeration**: Generate a mix of registered and unregistered email addresses using `hypothesis` (`st.emails()` or a custom strategy); for each, POST to `/api/v1/auth/password-reset-request`; assert `response.status_code == 200` and `response.json()["success"] is True` — callers cannot distinguish registered from unregistered by response shape
    - **Property 2b — Confirm flow preserved**: Create a user, call the unfixed endpoint to get a raw token from the response, POST that token to `/api/v1/auth/password-reset-confirm` with a new password; assert HTTP 200 and the password is updated
    - **Property 2c — Invalid token still rejected**: POST a random string to `/api/v1/auth/password-reset-confirm`; assert HTTP 400 with `AUTH_RESET_TOKEN_INVALID`
    - **Property 2d — Rate limiter preserved**: Call `/api/v1/auth/password-reset-request` 6 times in sequence for the same email; assert the 6th call returns HTTP 429
  - Run tests on UNFIXED code: `uv run pytest packages/backend/tests/test_password_reset_preservation.py -v`
  - **EXPECTED OUTCOME**: All preservation tests PASS on unfixed code (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Fix for password reset token exposure in `request_password_reset`

  - [x] 3.1 Import `email_service` into `auth.py`
    - Add `from src.services.email_service import email_service` to the imports in `packages/backend/src/api/v1/auth.py`
    - `get_settings` is already imported — no additional import needed for settings
    - _Bug_Condition: isBugCondition(request) — any POST to /api/v1/auth/password-reset-request causes token to appear in response body or log record_
    - _Expected_Behavior: email_service.send_email() is called with the token embedded in a reset link; no token field in response; no plaintext token in logs_
    - _Preservation: import change is additive — no existing behavior affected_
    - _Requirements: 2.2_

  - [x] 3.2 Change `response_model` from `PasswordResetTokenResponse` to `SuccessResponse`
    - On the `@router.post("/password-reset-request", ...)` decorator, replace `response_model=PasswordResetTokenResponse` with `response_model=SuccessResponse`
    - `SuccessResponse` is already imported in `auth.py`
    - _Bug_Condition: PasswordResetTokenResponse exposes a `token` field in the HTTP response body_
    - _Expected_Behavior: SuccessResponse returns only `{"success": true, "message": "..."}` with no token field_
    - _Preservation: HTTP status code remains 200; rate limiter dependency unchanged_
    - _Requirements: 2.1, 2.4_

  - [x] 3.3 Fix the unregistered-email path to return `SuccessResponse`
    - Replace the `return PasswordResetTokenResponse(token="dummy_token_for_security", ...)` block with:
      ```python
      return SuccessResponse(message="If that email is registered, a password reset link has been sent.")
      ```
    - _Bug_Condition: unregistered-email path returns `token="dummy_token_for_security"` in response body, leaking anti-enumeration implementation detail_
    - _Expected_Behavior: both registered and unregistered paths return identical SuccessResponse shape_
    - _Preservation: HTTP 200 is still returned for unregistered emails — anti-enumeration guarantee preserved (Requirement 3.3)_
    - _Requirements: 2.4, 3.3_

  - [x] 3.4 Remove the plaintext token log and replace with sanitised log
    - Replace:
      ```python
      log.info(
          "auth.password_reset.token_dev",
          user_id=str(user.id),
          email=user.email,
          token=raw_token,
          expires_at=expires_at.isoformat(),
      )
      ```
      with:
      ```python
      log.info("auth.password_reset.requested", user_id=str(user.id), email=user.email)
      ```
    - _Bug_Condition: log record contains key `token` with raw token value, visible to any log aggregator_
    - _Expected_Behavior: log record contains only `user_id` and `email` — no token value at any log level_
    - _Preservation: structured logging via structlog is preserved; log event name changes from `token_dev` to `requested`_
    - _Requirements: 2.3_

  - [x] 3.5 Wire email dispatch — call `email_service.send_email()` with the reset link
    - Remove the `# TODO: In production, call EmailService.send_password_reset(user.email, raw_token)` comment
    - After `raw_token, expires_at = await auth_service.create_password_reset_token(session, user)`, add:
      ```python
      settings = get_settings()
      reset_link = f"{settings.frontend_url}/reset-password?token={raw_token}"
      html_body = f"""
      <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px;">
          <h2 style="color: #2563eb;">Reset your Event-AI password</h2>
          <p>We received a request to reset the password for your account.</p>
          <p style="margin: 24px 0;">
              <a href="{reset_link}" style="background: #2563eb; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600;">
                  Reset Password
              </a>
          </p>
          <p style="color: #6b7280; font-size: 14px;">This link expires in 1 hour. If you did not request a password reset, you can safely ignore this email.</p>
          <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
          <p style="color: #9ca3af; font-size: 12px;">Event-AI — Pakistan's Event Planning Marketplace</p>
      </div>
      """
      text_body = f"Reset your Event-AI password by visiting: {reset_link}\n\nThis link expires in 1 hour."
      await email_service.send_email(
          to=user.email,
          subject="Reset your Event-AI password",
          body_html=html_body,
          body_text=text_body,
      )
      ```
    - _Bug_Condition: email_service.send_email() was never called — token was only reachable via HTTP response_
    - _Expected_Behavior: email_service.send_email() is called with to=user.email, subject="Reset your Event-AI password", and body_text containing `/reset-password?token=`_
    - _Preservation: EmailService.send_email() is fire-and-forget; in dev mode (SMTP not configured) it logs the email content instead of sending — acceptable for development (Requirement 2.5)_
    - _Requirements: 2.2, 2.5_

  - [x] 3.6 Change the registered-email return value to `SuccessResponse`
    - Replace:
      ```python
      return PasswordResetTokenResponse(
          token=raw_token,
          expires_at=expires_at,
          user_email=user.email,
      )
      ```
      with:
      ```python
      return SuccessResponse(message="If that email is registered, a password reset link has been sent.")
      ```
    - _Bug_Condition: raw_token returned directly in HTTP response body under `token` field_
    - _Expected_Behavior: SuccessResponse with no token field; token is now exclusively in the email_
    - _Preservation: HTTP 200 preserved; response shape now identical for registered and unregistered emails_
    - _Requirements: 2.1, 2.4_

  - [x] 3.7 Remove `PasswordResetTokenResponse` from the imports in `auth.py`
    - Remove `PasswordResetTokenResponse` from the `from src.schemas.auth import (...)` block in `packages/backend/src/api/v1/auth.py`
    - Verify no other route in `auth.py` references `PasswordResetTokenResponse` before removing
    - _Bug_Condition: unused import left in place would cause confusion and potential future misuse_
    - _Expected_Behavior: import block is clean; PasswordResetTokenResponse is no longer part of the auth router's public surface_
    - _Preservation: no runtime behavior change — import removal only_
    - _Requirements: 2.1_

  - [x] 3.8 Deprecate `PasswordResetTokenResponse` in `packages/backend/src/schemas/auth.py`
    - Add a deprecation notice to the docstring of `PasswordResetTokenResponse`:
      ```python
      """
      DEPRECATED: No longer used by any endpoint as of the password-reset-token-exposure fix.
      The token is now delivered exclusively via email. Do not use in new code.
      Retained temporarily to avoid breaking any existing tests that reference this schema.
      """
      ```
    - Remove `PasswordResetTokenResponse` from `__all__` in `schemas/auth.py` (if present) to signal it is no longer part of the public API
    - Do NOT delete the class yet — update existing tests first (task 3.9)
    - _Requirements: 2.1_

  - [x] 3.9 Update existing test assertions for the password reset endpoint
    - Search `packages/backend/tests/` for any test that asserts `response.json()["token"]` on the `/api/v1/auth/password-reset-request` endpoint
    - Update those assertions to:
      - Assert `response.json()["success"] is True`
      - Assert `"token" not in response.json()`
      - Mock `email_service.send_email` with `unittest.mock.AsyncMock` and assert it is called with `to=<user_email>` and `subject="Reset your Event-AI password"` for the registered-email path
      - Assert `email_service.send_email` is NOT called for the unregistered-email path
    - _Requirements: 2.1, 2.2, 2.4_

  - [x] 3.10 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Token Exposed in Response and Logs
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - The test from task 1 encodes the expected behavior (token NOT in response, email service IS called, no plaintext token in logs)
    - Wait — the exploration test from task 1 was written to CONFIRM the bug (assert token IS present). After the fix, those assertions will FAIL, which means the bug is gone.
    - Re-interpret: the exploration test assertions that PASSED on unfixed code (confirming the bug) should now FAIL — this is the signal that the fix works. Write a complementary "fix verification" test that asserts the CORRECT post-fix behavior:
      - `"token" not in response.json()`
      - `response.json()["success"] is True`
      - `email_service.send_email` was called once with correct `to` and `subject`
      - No structlog record contains key `"token"` with the raw token value
    - Run: `uv run pytest packages/backend/tests/test_password_reset_token_exposure.py -v`
    - **EXPECTED OUTCOME**: Fix verification assertions PASS; original bug-confirming assertions FAIL (confirming bug is resolved)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 3.11 Verify preservation tests still pass
    - **Property 2: Preservation** - Anti-Enumeration and Downstream Flows Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run: `uv run pytest packages/backend/tests/test_password_reset_preservation.py -v`
    - **EXPECTED OUTCOME**: All preservation tests PASS (confirms no regressions)
    - Confirm: anti-enumeration (HTTP 200 for both registered and unregistered), confirm flow, invalid token rejection, rate limiting, and other auth endpoints all behave identically

- [x] 4. Checkpoint — Ensure all tests pass
  - Run the full backend test suite: `uv run pytest packages/backend/tests/ -v`
  - Confirm all tests pass; ask the user if any failures arise that require clarification
  - Verify the fix is complete by checking all requirements:
    - ✅ 2.1 — No `token` field in response for registered email
    - ✅ 2.2 — `email_service.send_email()` called with reset link for registered email
    - ✅ 2.3 — No plaintext token in any log record
    - ✅ 2.4 — No `token` field in response for unregistered email (anti-enumeration preserved)
    - ✅ 2.5 — Dev mode (SMTP not configured) relies on EmailService's existing dev-mode logging
    - ✅ 3.1 — `password-reset-confirm` with valid token still works
    - ✅ 3.2 — `password-reset-confirm` with invalid token still returns HTTP 400
    - ✅ 3.3 — Unregistered email still returns HTTP 200
    - ✅ 3.4 — Rate limiter still returns HTTP 429 after threshold
    - ✅ 3.5 — All other auth endpoints unaffected

## Notes

- All Python commands must be run with `uv run` — never activate the venv manually
- Tests use `sqlite+aiosqlite:///:memory:` — no Neon or Docker needed
- Mock `email_service.send_email` with `unittest.mock.AsyncMock` in all tests that call the password reset endpoint to avoid real SMTP calls
- The `PasswordResetTokenResponse` schema is NOT deleted in this fix — it is deprecated and retained until all test references are updated
- The `password-reset-confirm` endpoint and `AuthService` methods are NOT modified
- Run tests from `packages/backend`: `uv run pytest tests/ -v`
