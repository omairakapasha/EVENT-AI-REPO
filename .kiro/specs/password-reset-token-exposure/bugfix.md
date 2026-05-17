# Bugfix Requirements Document

## Introduction

`POST /api/v1/auth/password-reset-request` returns the raw, plaintext reset token directly in the HTTP response body. The endpoint was scaffolded with a TODO comment acknowledging that email delivery was not yet wired. As a result, any log aggregator, reverse proxy, CDN, or network observer that captures the response body obtains a fully valid, single-use token that can be used to take over the target account — with no authentication required. This is a critical account-takeover vulnerability (AUTH-06).

The fix must remove the token from the response entirely and deliver it exclusively via email, while preserving all non-buggy behaviour (rate limiting, dummy response for unknown emails, token generation, token consumption, and the confirm flow).

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a registered user's email is submitted to `POST /api/v1/auth/password-reset-request` THEN the system returns the raw plaintext reset token in the JSON response body under the `token` field.

1.2 WHEN a registered user's email is submitted to `POST /api/v1/auth/password-reset-request` THEN the system logs the raw plaintext reset token at INFO level via structlog (field `token=raw_token`), making it visible in any log aggregator.

1.3 WHEN the response body is captured by a reverse proxy, CDN, load balancer, or network observer THEN the captured token is immediately usable to call `POST /api/v1/auth/password-reset-confirm` and take over the account.

### Expected Behavior (Correct)

2.1 WHEN a registered user's email is submitted to `POST /api/v1/auth/password-reset-request` THEN the system SHALL send the reset token exclusively via email to the registered address and SHALL NOT include the token (or any derivative of it) in the HTTP response body.

2.2 WHEN a registered user's email is submitted to `POST /api/v1/auth/password-reset-request` THEN the system SHALL return a generic success envelope `{ "success": true, "message": "If that email is registered you will receive a reset link shortly." }` that contains no token, no expiry, and no user email.

2.3 WHEN the system logs the password-reset-request event for a registered user THEN the system SHALL log only non-sensitive fields (e.g. `user_id`, `token_id`, `expires_at`) and SHALL NOT log the raw token value.

2.4 WHEN the email service is unavailable or not yet configured THEN the system SHALL fail safely: the token SHALL still not be returned in the response body, and the error SHALL be surfaced as an internal server error or logged at ERROR level without exposing the token.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN an unregistered email is submitted to `POST /api/v1/auth/password-reset-request` THEN the system SHALL CONTINUE TO return the same generic success response (timing-safe, no enumeration of registered addresses).

3.2 WHEN a valid, unexpired, unused reset token is submitted to `POST /api/v1/auth/password-reset-confirm` THEN the system SHALL CONTINUE TO accept it, update the user's password, mark the token as used, and revoke all existing refresh tokens.

3.3 WHEN an invalid, expired, or already-used reset token is submitted to `POST /api/v1/auth/password-reset-confirm` THEN the system SHALL CONTINUE TO return HTTP 400 with error code `VALIDATION_ERROR`.

3.4 WHEN `POST /api/v1/auth/password-reset-request` is called more than the configured rate-limit threshold THEN the system SHALL CONTINUE TO return HTTP 429 with error code `AUTH_RATE_LIMITED`.

3.5 WHEN `AuthService.create_password_reset_token` is called THEN the system SHALL CONTINUE TO store only the SHA-256 hash of the token in the database, never the raw token.
