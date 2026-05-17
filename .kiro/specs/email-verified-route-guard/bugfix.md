# Bugfix Requirements Document

## Introduction

AUTH-03: The `email_verified` boolean field is set to `False` on user registration and is correctly updated when a user verifies their email. However, the route guard (`get_current_user` in `src/middleware/auth.middleware.py`) never checks this field. As a result, any user who registers but has not verified their email can immediately access all protected features — bookings, events, vendor management, profile updates, and every other resource behind `Depends(get_current_user)` — as if they were fully verified. This undermines the purpose of email verification entirely.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user with `email_verified = False` presents a valid JWT to any protected route THEN the system grants full access to that route without checking email verification status

1.2 WHEN `get_current_user` resolves a user from a valid JWT THEN the system only checks `is_active` and returns the user, ignoring the `email_verified` field entirely

1.3 WHEN an unverified user calls any `/api/v1/*` endpoint protected by `Depends(get_current_user)` THEN the system returns a successful response as if the user were verified

### Expected Behavior (Correct)

2.1 WHEN a user with `email_verified = False` presents a valid JWT to any protected route THEN the system SHALL reject the request with HTTP 403 and error code `AUTH_EMAIL_NOT_VERIFIED`

2.2 WHEN `get_current_user` resolves a user from a valid JWT THEN the system SHALL check `email_verified` after confirming `is_active`, and raise an `HTTPException(403)` if `email_verified` is `False`

2.3 WHEN an unverified user calls any `/api/v1/*` endpoint protected by `Depends(get_current_user)` THEN the system SHALL return `{ "success": false, "error": { "code": "AUTH_EMAIL_NOT_VERIFIED", "message": "Email address has not been verified." } }`

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user with `email_verified = True` presents a valid JWT THEN the system SHALL CONTINUE TO grant access to protected routes as before

3.2 WHEN a user presents an invalid or expired JWT THEN the system SHALL CONTINUE TO reject the request with HTTP 401 and error code `AUTH_UNAUTHORIZED`

3.3 WHEN a user with `is_active = False` presents a valid JWT THEN the system SHALL CONTINUE TO reject the request with HTTP 401 as before

3.4 WHEN a request is made to a public endpoint (e.g., `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/public_vendors`) that does not use `Depends(get_current_user)` THEN the system SHALL CONTINUE TO serve those endpoints without requiring email verification

3.5 WHEN `get_current_user_optional` is used on an endpoint and the user is authenticated but unverified THEN the system SHALL CONTINUE TO return the user object without raising an error (optional auth endpoints are not subject to the verification gate)
