# Email Verified Route Guard Bugfix Design

## Overview

AUTH-03 describes a missing guard in `get_current_user` (`src/middleware/auth.middleware.py`).
After `verify_access_token` resolves a user from a valid JWT, the middleware confirms only
`is_active` and returns the user immediately — it never inspects `email_verified`. Any user
who registers but skips email verification therefore has unrestricted access to every route
protected by `Depends(get_current_user)`.

The fix is a single, targeted addition: after the existing `is_active` check inside
`verify_access_token` (or immediately after the call returns in `get_current_user`), raise
`HTTPException(403)` when `user.email_verified is False`. The change touches one function in
one file and requires no schema migration. `get_current_user_optional` is explicitly excluded
from the gate — it must continue to return the user object regardless of verification status.

---

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug — a valid JWT resolves to a user
  whose `email_verified` field is `False`, yet the middleware returns that user without error.
- **Property (P)**: The desired post-fix behavior for inputs satisfying C — `get_current_user`
  SHALL raise `HTTPException(status_code=403, detail={"code": "AUTH_EMAIL_NOT_VERIFIED", ...})`.
- **Preservation**: All behaviors that must remain byte-for-byte identical after the fix —
  verified-user access, 401 paths (invalid token, inactive user), public endpoints, and
  `get_current_user_optional` semantics.
- **`get_current_user`**: The FastAPI dependency in
  `packages/backend/src/middleware/auth.middleware.py` that extracts, verifies, and returns
  the authenticated user for every protected route.
- **`get_current_user_optional`**: The sibling dependency that returns `None` (not an error)
  when no valid token is present; it delegates to `get_current_user` internally and catches
  `HTTPException`. After the fix it must also suppress the new 403.
- **`verify_access_token`**: The method on `AuthService` that decodes the JWT, fetches the
  `User` row, and checks `is_active`. The `email_verified` check will be added here or in
  `get_current_user` — see Fix Implementation for the chosen location.
- **`email_verified`**: `bool` column on the `users` table, defaulting to `False` on
  registration and set to `True` by the email-verification flow.

---

## Bug Details

### Bug Condition

The bug manifests when a user whose `email_verified` column is `False` presents a structurally
valid, non-expired JWT to any route protected by `Depends(get_current_user)`. The middleware
calls `auth_service.verify_access_token(token, session)`, which checks only `is_active` before
returning the `User` object. Because `email_verified` is never inspected, the dependency
resolves successfully and the route handler executes as if the user were fully verified.

**Formal Specification:**

```
FUNCTION isBugCondition(user, token)
  INPUT:  user  — User object resolved from a valid, non-expired JWT
          token — the raw JWT string presented in the request
  OUTPUT: boolean

  RETURN token IS structurally valid
         AND token IS not expired
         AND user.is_active IS True
         AND user.email_verified IS False
END FUNCTION
```

### Examples

- **Unverified user hits booking endpoint**: User registers, skips email verification, sends
  `POST /api/v1/bookings` with their JWT → currently receives `201 Created`. Expected: `403`.
- **Unverified vendor hits service management**: Vendor registers, skips verification, sends
  `POST /api/v1/vendors/services` → currently receives `201 Created`. Expected: `403`.
- **Unverified user hits profile update**: `PATCH /api/v1/users/me` with unverified JWT →
  currently receives `200 OK`. Expected: `403`.
- **Edge case — unverified user on optional-auth endpoint**: `GET /api/v1/public_vendors`
  uses `get_current_user_optional`; the user object should be returned (not `None`, not `403`)
  because optional-auth endpoints are not subject to the verification gate.

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

- A user with `email_verified = True` and `is_active = True` presenting a valid JWT SHALL
  continue to receive `200 OK` (or the appropriate success status) on all protected routes.
- A request with a missing, malformed, or expired JWT SHALL continue to receive `401` with
  error code `AUTH_UNAUTHORIZED`.
- A user with `is_active = False` presenting a valid JWT SHALL continue to receive `401`
  (the existing `is_active` check in `verify_access_token` is not modified).
- Public endpoints that do not use `Depends(get_current_user)` (e.g.,
  `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/public_vendors`) SHALL continue
  to serve requests without any email-verification requirement.
- `get_current_user_optional` SHALL continue to return the `User` object for an authenticated
  but unverified user — it must not propagate the new `403`.

**Scope:**

All inputs that do NOT satisfy `isBugCondition` (i.e., the user is verified, the token is
invalid, the user is inactive, or the endpoint uses optional auth) must be completely
unaffected by this fix.

---

## Hypothesized Root Cause

Based on reading `auth_service.verify_access_token` and `get_current_user`:

1. **Missing guard in `verify_access_token`**: After `user = await session.get(User, parsed_id)`,
   the method checks `not user or not user.is_active` and raises `401` if true. There is no
   subsequent `if not user.email_verified` branch. This is the primary root cause.

2. **`get_current_user` trusts the service return value unconditionally**: The middleware
   calls `user = await auth_service.verify_access_token(token, session)` and immediately
   attaches the result to `request.state.user` and returns it. It performs no additional
   field-level validation of its own.

3. **`get_current_user_optional` inherits the gap**: Because it delegates to
   `get_current_user`, it would also silently pass unverified users — but per requirement 3.5
   this is intentional behaviour that must be preserved after the fix.

4. **No test coverage for the unverified path**: The existing test suite does not assert that
   an unverified user is blocked, so the gap went undetected.

The fix location is `get_current_user` in `auth.middleware.py` (not inside
`verify_access_token`) so that `get_current_user_optional` — which catches `HTTPException`
from `get_current_user` — naturally suppresses the new `403` without any additional changes.

---

## Correctness Properties

Property 1: Bug Condition — Unverified User Is Rejected with 403

_For any_ valid, non-expired JWT that resolves to a user where `email_verified is False` and
`is_active is True`, the fixed `get_current_user` dependency SHALL raise
`HTTPException(status_code=403)` with detail
`{"code": "AUTH_EMAIL_NOT_VERIFIED", "message": "Email address has not been verified."}`,
causing every protected route to return an HTTP 403 response with the standard error envelope.

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation — Verified User Access Is Unchanged

_For any_ valid, non-expired JWT that resolves to a user where `email_verified is True` and
`is_active is True`, the fixed `get_current_user` dependency SHALL return the `User` object
without raising any exception, preserving all existing access behaviour for verified users.

**Validates: Requirements 3.1**

---

## Fix Implementation

### Changes Required

**File:** `packages/backend/src/middleware/auth.middleware.py`

**Function:** `get_current_user`

**Specific Changes:**

1. **Add email-verification guard after `verify_access_token` returns**: Immediately after
   `user = await auth_service.verify_access_token(token, session)`, insert:

   ```python
   if not user.email_verified:
       raise HTTPException(
           status_code=403,
           detail={
               "code": "AUTH_EMAIL_NOT_VERIFIED",
               "message": "Email address has not been verified.",
           },
       )
   ```

2. **Placement rationale**: The guard lives in `get_current_user`, not in
   `verify_access_token`, so that `get_current_user_optional` (which calls `get_current_user`
   and catches `HTTPException`) automatically suppresses the new `403` — satisfying
   requirement 3.5 with zero additional code.

3. **No changes to `get_current_user_optional`**: Its existing `except HTTPException: return None`
   block already handles any `HTTPException` raised by `get_current_user`, including the new
   `403`. No modification needed.

4. **No schema migration required**: `email_verified` already exists on the `users` table
   with `default=False`. No new columns, no Alembic revision.

5. **No changes to `verify_access_token`**: The service method remains responsible only for
   JWT validity and `is_active`. The new semantic gate (email verification) belongs in the
   middleware layer.

**Resulting `get_current_user` logic (pseudocode):**

```
FUNCTION get_current_user(request, credentials, session)
  token ← resolve from Bearer header or httpOnly cookie
  IF token is None THEN raise HTTPException(401, AUTH_UNAUTHORIZED)

  TRY
    user ← auth_service.verify_access_token(token, session)  # checks is_active

    IF NOT user.email_verified THEN                           # ← NEW GUARD
      raise HTTPException(403, AUTH_EMAIL_NOT_VERIFIED)

    request.state.user ← user
    RETURN user
  CATCH HTTPException
    re-raise
  CATCH Exception
    raise HTTPException(401, AUTH_UNAUTHORIZED)
END FUNCTION
```

---

## Testing Strategy

### Validation Approach

Testing follows a two-phase approach:

1. **Exploratory phase** — run tests against the *unfixed* code to confirm the bug manifests
   as described and to validate the root cause hypothesis.
2. **Fix + preservation phase** — after applying the fix, run fix-checking tests (Property 1)
   and preservation tests (Property 2) to confirm correct behaviour and no regressions.

### Exploratory Bug Condition Checking

**Goal:** Surface counterexamples that demonstrate the bug on unfixed code. Confirm that an
unverified user with a valid JWT currently receives `200` (not `403`) on protected routes.

**Test Plan:** Register a user, skip email verification, obtain a JWT via login, call a
protected endpoint, and assert the current (broken) response is `200`. Run on unfixed code.

**Test Cases:**

1. **Unverified user hits protected route** — register user, do NOT verify email, login to
   get JWT, `GET /api/v1/users/me` → currently returns `200` (will fail on fixed code).
2. **Unverified user hits booking endpoint** — same setup, `POST /api/v1/bookings` →
   currently returns `201` or `422` (not `403`).
3. **Unverified user hits event endpoint** — `POST /api/v1/events` → currently returns `201`
   or `422` (not `403`).
4. **Edge case — `get_current_user_optional` with unverified user** — call an optional-auth
   endpoint; currently returns user object (this behaviour must be preserved after fix too).

**Expected Counterexamples:**

- Protected routes return `2xx` for unverified users instead of `403`.
- Root cause confirmed: `get_current_user` returns the user without checking `email_verified`.

### Fix Checking

**Goal:** Verify that for all inputs where the bug condition holds, the fixed function
produces the expected `403` response.

**Pseudocode:**

```
FOR ALL (user, token) WHERE isBugCondition(user, token) DO
  response ← call_protected_endpoint(token)
  ASSERT response.status_code == 403
  ASSERT response.json()["success"] is False
  ASSERT response.json()["error"]["code"] == "AUTH_EMAIL_NOT_VERIFIED"
  ASSERT response.json()["error"]["message"] == "Email address has not been verified."
END FOR
```

### Preservation Checking

**Goal:** Verify that for all inputs where the bug condition does NOT hold, the fixed function
produces the same result as the original function.

**Pseudocode:**

```
FOR ALL (user, token) WHERE NOT isBugCondition(user, token) DO
  ASSERT fixed_get_current_user(user, token) == original_get_current_user(user, token)
END FOR
```

**Testing Approach:** Property-based testing is recommended for the verified-user preservation
path because it generates many combinations of user state (different roles, names, UUIDs) and
confirms that none of them are accidentally blocked by the new guard.

**Test Cases:**

1. **Verified user preservation** — generate users with `email_verified=True`, assert `200`
   on protected routes after fix (property-based: many random verified users).
2. **Invalid token preservation** — send malformed/expired JWT, assert `401 AUTH_UNAUTHORIZED`
   is unchanged.
3. **Inactive user preservation** — user with `is_active=False`, assert `401` is unchanged.
4. **Public endpoint preservation** — `POST /api/v1/auth/register` without token, assert
   `201` is unchanged.
5. **`get_current_user_optional` preservation** — unverified user on optional-auth endpoint,
   assert user object is returned (not `None`, not `403`).

### Unit Tests

- Test `get_current_user` directly: mock `auth_service.verify_access_token` to return a user
  with `email_verified=False`; assert `HTTPException(403)` is raised with correct detail.
- Test `get_current_user` with `email_verified=True`; assert user is returned without error.
- Test `get_current_user_optional` with an unverified user; assert `None` is NOT returned
  (the user object is returned because the `403` is caught and suppressed).

### Property-Based Tests

- **Property 1 (Fix)**: Generate arbitrary users with `email_verified=False` and
  `is_active=True`; for each, assert that calling a protected endpoint returns `403` with
  `AUTH_EMAIL_NOT_VERIFIED`. Use `hypothesis` with `@given(st.builds(User, ...))`.
- **Property 2 (Preservation)**: Generate arbitrary users with `email_verified=True` and
  `is_active=True`; for each, assert that calling a protected endpoint returns `200` (or the
  route's normal success code), never `403`.

### Integration Tests

- Full registration → skip verification → login → call protected route → assert `403`.
- Full registration → verify email → login → call protected route → assert `200`.
- Full registration → skip verification → call `get_current_user_optional` endpoint →
  assert user object is present in response context (no `403` propagated).
- Confirm `POST /api/v1/auth/login` (public) still works for unverified users (they can log
  in; they just cannot access protected resources).
