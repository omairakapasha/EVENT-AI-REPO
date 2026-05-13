# Bugfix Requirements Document

## Introduction

`rotate_refresh_token` in `packages/backend/src/services/auth_service.py` does not distinguish between a refresh token that **never existed** and one that **was already rotated** (i.e., exists in the DB with `revoked_at IS NOT NULL`). Both cases return the same generic 401, and neither triggers any further action.

This is a security gap: per OAuth 2.0 Security BCP (RFC 9700) and industry practice (Auth0, Okta), presenting an already-rotated token is a **token theft signal**. An attacker who steals and rotates a token before the legitimate user does will receive a valid new token pair and can continue using it indefinitely — the legitimate user's subsequent 401 is the only observable symptom, and the attacker's session is never terminated.

The fix must detect re-use of a rotated token, immediately revoke all active refresh tokens for that user (entire session family), and return a distinct error code so clients and security monitoring can react appropriately.

---

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a refresh token is presented that exists in the DB but has `revoked_at IS NOT NULL` (already rotated), THEN the system returns HTTP 401 "Invalid or expired refresh token" — identical to the response for a token that never existed

1.2 WHEN a previously-rotated refresh token is presented, THEN the system does NOT revoke any other active refresh tokens for that user

1.3 WHEN a previously-rotated refresh token is presented, THEN the system does NOT log a security warning distinguishing this event from a routine invalid-token rejection

1.4 WHEN an attacker rotates a stolen token and the legitimate user later presents their (now-revoked) original token, THEN the attacker's newly-issued token remains valid and the attacker's session continues indefinitely

### Expected Behavior (Correct)

2.1 WHEN a refresh token is presented that exists in the DB but has `revoked_at IS NOT NULL`, THEN the system SHALL revoke ALL active (non-revoked, non-expired) refresh tokens for that user before returning a response

2.2 WHEN a refresh token is presented that exists in the DB but has `revoked_at IS NOT NULL`, THEN the system SHALL return HTTP 401 with error code `AUTH_TOKEN_REUSE_DETECTED` and a human-readable message

2.3 WHEN a refresh token is presented that exists in the DB but has `revoked_at IS NOT NULL`, THEN the system SHALL emit a structured security warning log containing `user_id` and the token's `id` (or hash prefix)

2.4 WHEN family revocation is triggered, THEN the system SHALL revoke all tokens for the user atomically within the same database transaction before returning the 401 response

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a refresh token is presented that does not exist in the DB at all (truly invalid or fabricated), THEN the system SHALL CONTINUE TO return HTTP 401 without triggering family revocation

3.2 WHEN a valid refresh token is presented (exists in DB, `revoked_at IS NULL`, not expired), THEN the system SHALL CONTINUE TO revoke the old token, issue a new token pair, and return HTTP 200 with the new tokens

3.3 WHEN a refresh token is presented that exists in the DB but has `expires_at` in the past and `revoked_at IS NULL` (naturally expired, never rotated), THEN the system SHALL CONTINUE TO return HTTP 401 without triggering family revocation

3.4 WHEN `revoke_all_refresh_tokens` is called for any reason (e.g., password reset), THEN the system SHALL CONTINUE TO revoke all active tokens for that user as before

3.5 WHEN a valid token rotation completes successfully, THEN the system SHALL CONTINUE TO log `auth.refresh.rotated` with `user_id` and `old_token_id`

---

## Bug Condition

**Bug Condition Function:**

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type RefreshTokenRequest { raw_token: str }
  OUTPUT: boolean

  token_hash ← SHA256(X.raw_token)
  record ← DB.query(RefreshToken WHERE token_hash = token_hash)

  RETURN record IS NOT NULL
     AND record.revoked_at IS NOT NULL
END FUNCTION
```

**Property: Fix Checking**

```pascal
// Property: Fix Checking — Re-use of a rotated token triggers family revocation
FOR ALL X WHERE isBugCondition(X) DO
  result ← rotate_refresh_token'(X)
  ASSERT result.status = 401
  ASSERT result.error.code = "AUTH_TOKEN_REUSE_DETECTED"
  ASSERT COUNT(active_tokens_for_user(record.user_id)) = 0
END FOR
```

**Property: Preservation Checking**

```pascal
// Property: Preservation — Non-buggy inputs behave identically before and after the fix
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT rotate_refresh_token(X) = rotate_refresh_token'(X)
END FOR
```

Where `F` = `rotate_refresh_token` (before fix) and `F'` = `rotate_refresh_token'` (after fix).
