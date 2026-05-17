# Password Reset Token Exposure — Bugfix Design

## Overview

`POST /api/v1/auth/password-reset-request` currently returns the raw, usable one-time password reset token directly in the HTTP response body (`PasswordResetTokenResponse.token`) and logs it in plaintext via structlog. Because the email delivery path was never wired (a `# TODO` comment acknowledges this), the token is only reachable through the HTTP response — making it visible to any HTTP proxy, CDN access log, log aggregator, or network observer.

The fix is minimal and targeted:
1. Change the endpoint's `response_model` from `PasswordResetTokenResponse` to `SuccessResponse` and return a generic message for both registered and unregistered emails.
2. Call `email_service.send_email()` with the token embedded in a reset link (`{settings.frontend_url}/reset-password?token={raw_token}`) — following the same pattern already used by `otp_service`.
3. Replace the `log.info(... token=raw_token ...)` call with a sanitised log that records only `user_id` and `email`.
4. Remove `PasswordResetTokenResponse` from the endpoint's imports (it is no longer used by any route).

No database schema changes, no changes to `AuthService`, and no changes to the `password-reset-confirm` endpoint or any other auth flow.

---

## Glossary

- **Bug_Condition (C)**: The condition that triggers the security defect — a `POST /api/v1/auth/password-reset-request` request for a registered email causes the raw, usable reset token to appear in the HTTP response body or in a plaintext log record.
- **Property (P)**: The desired post-fix behaviour — the HTTP response body contains no `token` field, `email_service.send_email()` is called with the token embedded in a reset link, and no log record contains the raw token value.
- **Preservation**: All existing behaviours that must remain unchanged — anti-enumeration (HTTP 200 for both registered and unregistered emails), rate limiting, the `password-reset-confirm` flow, and all other auth endpoints.
- **`request_password_reset`**: The FastAPI route handler in `packages/backend/src/api/v1/auth.py` that is the sole subject of this fix.
- **`PasswordResetTokenResponse`**: The Pydantic schema in `packages/backend/src/schemas/auth.py` that currently exposes `token`, `expires_at`, and `user_email`. It will no longer be used by any endpoint after this fix.
- **`SuccessResponse`**: The existing Pydantic schema (`success: bool`, `message: str`) that will replace `PasswordResetTokenResponse` as the response model.
- **`email_service`**: The singleton `EmailService` instance in `packages/backend/src/services/email_service.py`. In dev mode (SMTP not configured) it logs the email content instead of sending — this is acceptable for development.
- **`raw_token`**: The URL-safe base64 string returned by `auth_service.create_password_reset_token()`. It must never appear in an HTTP response body or a plaintext log record after this fix.
- **`reset_link`**: The URL `{settings.frontend_url}/reset-password?token={raw_token}` embedded in the email body. The `/reset-password` page already exists in the user portal.

---

## Bug Details

### Bug Condition

The bug manifests when `POST /api/v1/auth/password-reset-request` is called with a registered user's email. The `request_password_reset` handler creates a valid one-time token via `auth_service.create_password_reset_token()`, then immediately returns it in the HTTP response body and logs it in plaintext — instead of routing it exclusively through email.

A secondary manifestation exists for unregistered emails: the handler returns the hardcoded string `"dummy_token_for_security"` in the `token` field, which leaks the anti-enumeration implementation detail.

**Formal Specification:**

```
FUNCTION isBugCondition(request)
  INPUT: request — an HTTP POST to /api/v1/auth/password-reset-request
  OUTPUT: boolean

  IF request.body.email matches a registered user THEN
    RETURN response.body contains "token" field
           OR any log record contains key "token" with a non-empty string value
  ELSE
    RETURN response.body contains "token" field
           -- (the "dummy_token_for_security" case)
  END IF
END FUNCTION
```

### Examples

- **Registered email, happy path**: `POST /api/v1/auth/password-reset-request` with `{"email": "ali@example.com"}` (registered) → current response: `{"token": "abc123...", "expires_at": "...", "user_email": "ali@example.com"}`. An attacker reading the response can immediately call `POST /api/v1/auth/password-reset-confirm` with that token and take over the account.
- **Registered email, log exposure**: The same request causes `log.info("auth.password_reset.token_dev", user_id="...", email="...", token="abc123...", ...)` to be emitted. Any log aggregator (Datadog, CloudWatch, Loki) that indexes this record exposes the token to anyone with log read access.
- **Unregistered email**: `POST /api/v1/auth/password-reset-request` with `{"email": "unknown@example.com"}` → current response: `{"token": "dummy_token_for_security", "expires_at": "...", "user_email": "unknown@example.com"}`. The `token` field is present, leaking the anti-enumeration strategy.
- **Edge case — SMTP not configured (dev mode)**: After the fix, `email_service.send_email()` is called; because SMTP is not configured, `EmailService` logs the email content (including the reset link) at INFO level. This is acceptable for development — the token is in a log record, but only in dev mode and only as part of a structured email preview, not as a bare `token=` field.

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- `POST /api/v1/auth/password-reset-request` with an unregistered email MUST continue to return HTTP 200 (no user enumeration).
- `POST /api/v1/auth/password-reset-confirm` with a valid token MUST continue to validate the token, update the password, and return HTTP 200.
- `POST /api/v1/auth/password-reset-confirm` with an invalid or expired token MUST continue to return HTTP 400.
- The password reset rate limiter (5 requests/hour) MUST continue to return HTTP 429 when the threshold is exceeded.
- All other auth endpoints (`/register`, `/login`, `/refresh`, `/logout`, `/verify-email`, `/resend-otp`, `/google`) MUST continue to behave identically.
- `auth_service.create_password_reset_token()`, `auth_service.verify_and_consume_password_reset_token()`, and `auth_service.reset_password()` are NOT modified.

**Scope:**
All inputs that do NOT involve `POST /api/v1/auth/password-reset-request` are completely unaffected by this fix. Within that endpoint, the only changes are: response schema, email dispatch call, and log sanitisation.

---

## Hypothesized Root Cause

The bug is not a logic error — it is an incomplete implementation. The root cause is:

1. **Email delivery was never wired**: A `# TODO: In production, call EmailService.send_password_reset(user.email, raw_token)` comment in `request_password_reset` confirms the email dispatch was deferred and never completed. The token was returned in the response as a temporary development convenience that was never removed.

2. **Response schema was not updated**: `PasswordResetTokenResponse` (with its `token` field) was designed for the temporary dev-mode response. It was never replaced with `SuccessResponse` once the email path was meant to be wired.

3. **Plaintext log was added for debugging**: `log.info("auth.password_reset.token_dev", ..., token=raw_token, ...)` was added to make the token visible during development (before email was wired). The `_dev` suffix in the log event name signals this was intended as temporary, but it was never removed.

4. **Dummy token for unregistered emails**: The `"dummy_token_for_security"` string was added to maintain a consistent response shape for the unregistered-email path. Once the response schema changes to `SuccessResponse`, this dummy value is no longer needed.

There is no ambiguity about the fix: all four issues are resolved by a single, targeted change to `request_password_reset` in `packages/backend/src/api/v1/auth.py`.

---

## Correctness Properties

Property 1: Bug Condition — No Token in Response or Logs

_For any_ HTTP POST to `/api/v1/auth/password-reset-request` with a valid email address (registered or unregistered), the fixed `request_password_reset` handler SHALL return an HTTP 200 response whose JSON body does NOT contain a `"token"` key, and SHALL NOT emit any structlog record containing a `"token"` key with the raw reset token value.

**Validates: Requirements 2.1, 2.3, 2.4**

Property 2: Preservation — Identical Response Shape for All Emails

_For any_ HTTP POST to `/api/v1/auth/password-reset-request` with any syntactically valid email address (whether registered or not), the fixed handler SHALL return a response with `status_code == 200`, `response.json()["success"] is True`, and `"token" not in response.json()` — preserving the anti-enumeration guarantee that callers cannot distinguish registered from unregistered emails by inspecting the response.

**Validates: Requirements 2.4, 3.3**

---

## Fix Implementation

### Changes Required

**File**: `packages/backend/src/api/v1/auth.py`

**Function**: `request_password_reset`

**Specific Changes**:

1. **Import `email_service` and `get_settings`**: Add `from src.services.email_service import email_service` to the imports. `get_settings` is already imported.

2. **Change `response_model`**: Replace `response_model=PasswordResetTokenResponse` with `response_model=SuccessResponse` on the `@router.post` decorator.

3. **Unregistered-email path**: Replace the `PasswordResetTokenResponse(token="dummy_token_for_security", ...)` return with:
   ```python
   return SuccessResponse(message="If that email is registered, a password reset link has been sent.")
   ```

4. **Remove plaintext token log**: Replace:
   ```python
   log.info("auth.password_reset.token_dev", user_id=str(user.id), email=user.email, token=raw_token, expires_at=expires_at.isoformat())
   ```
   with:
   ```python
   log.info("auth.password_reset.requested", user_id=str(user.id), email=user.email)
   ```

5. **Wire email dispatch**: After `create_password_reset_token`, add:
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

6. **Change return value**: Replace:
   ```python
   return PasswordResetTokenResponse(token=raw_token, expires_at=expires_at, user_email=user.email)
   ```
   with:
   ```python
   return SuccessResponse(message="If that email is registered, a password reset link has been sent.")
   ```

7. **Remove unused import**: Remove `PasswordResetTokenResponse` from the `from src.schemas.auth import (...)` block.

**File**: `packages/backend/src/schemas/auth.py`

8. **Deprecate `PasswordResetTokenResponse`**: Add a deprecation notice to the docstring of `PasswordResetTokenResponse`. Do not delete the class yet — it may be referenced in existing tests that need to be updated first. Remove it from `__all__` to signal it is no longer part of the public API.

**File**: `packages/backend/tests/` (existing test files for the password reset endpoint)

9. **Update test assertions**: Any test that asserts `response.json()["token"]` must be updated to assert `response.json()["success"] is True` and `"token" not in response.json()`. Tests must also mock `email_service.send_email` and assert it is called with the correct `to` and `subject` arguments for the registered-email path.

---

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on the unfixed code to confirm the root cause analysis; then verify the fix works correctly and preserves all existing behaviour.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that the token appears in the response body and in log records for registered-email requests.

**Test Plan**: Write tests that POST to `/api/v1/auth/password-reset-request` with a registered email and assert that `"token"` appears in the response JSON. Run these tests on the UNFIXED code to observe the failure mode and confirm the root cause.

**Test Cases**:
1. **Registered email — token in response** (will pass on unfixed code, must fail after fix): POST with a registered email, assert `"token" in response.json()` — this confirms the bug is present.
2. **Registered email — token in logs** (will pass on unfixed code, must fail after fix): Capture structlog output during the request, assert a log record with `token=<non-empty string>` exists.
3. **Unregistered email — dummy token in response** (will pass on unfixed code, must fail after fix): POST with an unregistered email, assert `response.json()["token"] == "dummy_token_for_security"`.
4. **Email service not called** (will pass on unfixed code, must fail after fix): Mock `email_service.send_email`, POST with a registered email, assert the mock was NOT called — confirming the TODO was never implemented.

**Expected Counterexamples**:
- `response.json()["token"]` is a non-empty string for registered emails.
- `response.json()["token"]` is `"dummy_token_for_security"` for unregistered emails.
- `email_service.send_email` is never called.

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behaviour.

**Pseudocode:**
```
FOR ALL request WHERE isBugCondition(request) DO
  response := request_password_reset_fixed(request)
  ASSERT response.status_code == 200
  ASSERT "token" NOT IN response.json()
  ASSERT response.json()["success"] IS True
  ASSERT email_service.send_email WAS CALLED with to=user.email, subject="Reset your Event-AI password"
  ASSERT NO log record contains key "token" with raw token value
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL request WHERE NOT isBugCondition(request) DO
  ASSERT request_password_reset_original(request) ≈ request_password_reset_fixed(request)
  -- same HTTP status code, same response schema shape, same anti-enumeration guarantee
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many email inputs automatically (registered, unregistered, edge-case formats).
- It verifies the anti-enumeration guarantee holds across all inputs — not just the two manually tested cases.
- It provides strong assurance that the response schema is identical regardless of whether the email is registered.

**Test Plan**: Observe that the unregistered-email path returns HTTP 200 on unfixed code, then write a property-based test that generates arbitrary email strings and asserts the response is always HTTP 200 with `"token" not in response.json()` after the fix.

**Test Cases**:
1. **Anti-enumeration preservation**: Generate random email addresses (registered and unregistered); assert all return HTTP 200 with `success=True` and no `token` field.
2. **Rate limiter preservation**: Exceed the 5-requests/hour threshold; assert HTTP 429 is still returned.
3. **Confirm endpoint preservation**: Submit a valid token to `/password-reset-confirm`; assert HTTP 200 and password is updated.
4. **Confirm endpoint — invalid token preservation**: Submit an invalid token to `/password-reset-confirm`; assert HTTP 400.
5. **Other endpoints unaffected**: Call `/register`, `/login`, `/logout` and assert their responses are unchanged.

### Unit Tests

- Test `request_password_reset` with a registered email: assert `SuccessResponse` is returned, `email_service.send_email` is called once with correct `to`/`subject`, and no `token` key appears in the response.
- Test `request_password_reset` with an unregistered email: assert `SuccessResponse` is returned, `email_service.send_email` is NOT called, and no `token` key appears in the response.
- Test that the reset link URL is correctly formed as `{frontend_url}/reset-password?token={raw_token}`.
- Test that the sanitised log record contains `user_id` and `email` but NOT `token`.

### Property-Based Tests

- Generate a large set of email addresses (mix of registered and unregistered); for each, assert the response is HTTP 200 with `"token" not in response.json()` — verifying Property 2 (anti-enumeration preservation) holds universally.
- Generate random registered users and assert that after calling the fixed endpoint, `email_service.send_email` is always called exactly once with a `body_text` containing the string `/reset-password?token=`.
- Generate random valid tokens and submit them to `/password-reset-confirm`; assert the confirm flow is unaffected by the request endpoint change.

### Integration Tests

- Full password reset flow: call the fixed `request_password_reset`, capture the reset link from the mocked `email_service.send_email` call, extract the token from the link, call `password-reset-confirm` with that token, assert the password is updated and all sessions are revoked.
- Dev-mode flow: with SMTP not configured, call the fixed endpoint and assert `email_service` logs the email content (including the reset link) at INFO level — confirming dev-mode usability is preserved.
- Rate limiting integration: call the endpoint 6 times in sequence; assert the 6th call returns HTTP 429.
