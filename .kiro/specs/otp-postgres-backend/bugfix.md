# Bugfix Requirements Document

## Introduction

OTP codes for email verification are stored in the `email_otps` PostgreSQL table. PostgreSQL has no native TTL mechanism, so expired and used OTP rows accumulate indefinitely. There is no background cleanup job, which means the table grows without bound (table bloat), and every `verify_otp` query must scan an ever-growing set of stale rows. The fix is to migrate OTP storage to Redis, which provides native key expiry (TTL), automatic eviction of expired codes, and eliminates the need for a cleanup job entirely. The OTP hashing logic (SHA-256) is correct and must be preserved unchanged.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a new OTP is issued for a user THEN the system writes a row to the `email_otps` PostgreSQL table with no database-level TTL, so the row persists indefinitely even after it expires.

1.2 WHEN an OTP expires (10 minutes after issuance) THEN the system does not automatically remove the row; the expired row remains in the table until a manual cleanup is performed.

1.3 WHEN a user requests multiple OTPs over time THEN the system accumulates one row per issuance in `email_otps`, causing unbounded table growth (table bloat) because no cleanup job exists.

1.4 WHEN `verify_otp` is called THEN the system queries the `email_otps` table, which may contain a large number of stale (expired or used) rows, degrading query performance over time.

1.5 WHEN the application is deployed THEN the system has no automated mechanism to purge expired or used OTP rows from PostgreSQL.

### Expected Behavior (Correct)

2.1 WHEN a new OTP is issued for a user THEN the system SHALL store the OTP hash in Redis with a TTL equal to the OTP expiry window (10 minutes), so the entry is automatically evicted when it expires.

2.2 WHEN an OTP expires THEN the system SHALL have the Redis key automatically deleted by Redis TTL expiry, with no manual cleanup required.

2.3 WHEN a user requests multiple OTPs over time THEN the system SHALL overwrite the previous Redis key for that user, so at most one active OTP entry exists per user at any time, with no accumulation of stale rows.

2.4 WHEN `verify_otp` is called THEN the system SHALL look up the OTP hash in Redis by a deterministic key (e.g. `otp:<user_id>`), returning a result in O(1) time regardless of historical OTP volume.

2.5 WHEN an OTP is successfully verified THEN the system SHALL immediately delete the Redis key so the code cannot be reused (single-use guarantee preserved).

2.6 WHEN Redis is used as the OTP store THEN the system SHALL continue to hash the OTP code with SHA-256 before storing it, preserving the existing security property that plaintext codes are never persisted.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a valid, unexpired OTP code is submitted THEN the system SHALL CONTINUE TO verify it successfully and mark the user's email as verified.

3.2 WHEN an already-used OTP code is submitted THEN the system SHALL CONTINUE TO reject it with `OTP_INVALID`.

3.3 WHEN an expired OTP code is submitted THEN the system SHALL CONTINUE TO reject it with `OTP_EXPIRED`.

3.4 WHEN an incorrect OTP code is submitted THEN the system SHALL CONTINUE TO reject it with `OTP_INVALID`.

3.5 WHEN a new OTP is issued for a user who already has an active OTP THEN the system SHALL CONTINUE TO invalidate the previous code so only the most recently issued code is valid.

3.6 WHEN `issue_otp` is called THEN the system SHALL CONTINUE TO send the verification email via Brevo SMTP with the plaintext code.

3.7 WHEN the `/api/v1/auth/verify-email` and `/api/v1/auth/resend-otp` endpoints are called THEN the system SHALL CONTINUE TO return responses conforming to the `{ "success": true, "data": {}, "meta": {} }` envelope.

3.8 WHEN the application runs tests THEN the system SHALL CONTINUE TO use an in-memory or fakeredis backend so no real Redis instance is required in the test environment.

---

## Bug Condition Pseudocode

**Bug Condition Function** — identifies the storage path that triggers the defect:

```pascal
FUNCTION isBugCondition(operation)
  INPUT: operation of type OTPOperation { issue | verify | expire }
  OUTPUT: boolean

  // The bug is triggered whenever OTP state is read from or written to PostgreSQL
  RETURN operation.backend = POSTGRES
END FUNCTION
```

**Property: Fix Checking**

```pascal
// For all OTP operations routed through the new backend
FOR ALL op WHERE isBugCondition(op) DO
  result ← executeOTPOperation'(op)   // F' = Redis-backed implementation
  ASSERT result.backend = REDIS
  ASSERT result.ttl_enforced = TRUE
  ASSERT result.stale_rows_in_postgres = 0
END FOR
```

**Property: Preservation Checking**

```pascal
// For all OTP verification outcomes, behaviour must be identical before and after the fix
FOR ALL input WHERE NOT isBugCondition(input) DO
  // input = { valid_code, expired_code, wrong_code, reused_code }
  ASSERT F(input).outcome = F'(input).outcome
END FOR
```

**Key:**
- **F** — current implementation (`OTPService` backed by `email_otps` PostgreSQL table)
- **F'** — fixed implementation (`OTPService` backed by Redis with TTL)
