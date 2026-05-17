# OTP Postgres Backend Bugfix Design

## Overview

The `email_otps` PostgreSQL table accumulates rows indefinitely because PostgreSQL has no native TTL mechanism and no cleanup job exists. Every `verify_otp` call queries an ever-growing set of stale rows, degrading performance over time.

The fix migrates OTP storage from PostgreSQL to Redis. Redis provides native key expiry (TTL), automatic eviction of expired codes, O(1) key-based lookups, and a trivial single-use guarantee via key deletion on successful verification. The OTP hashing logic (SHA-256) is correct and is preserved unchanged. All API contracts, error codes, and email delivery behaviour remain identical.

The change is confined to `src/services/otp_service.py` (rewrite), `src/models/email_otp.py` (delete), `src/config/database.py` (add Redis client to lifespan), and a new Alembic migration that drops the `email_otps` table. Route handlers in `src/api/v1/auth.py` are untouched.

---

## Glossary

- **Bug_Condition (C)**: Any OTP operation (`issue` or `verify`) that reads from or writes to the `email_otps` PostgreSQL table.
- **Property (P)**: The desired behaviour of the fixed implementation — OTP state is stored in Redis with a TTL, looked up by `otp:<user_id>`, and deleted on successful verification.
- **Preservation**: All observable API outcomes (success responses, error codes `OTP_INVALID` / `OTP_EXPIRED`, email delivery) that must remain identical before and after the fix.
- **OTPService**: The singleton class in `src/services/otp_service.py` that owns `issue_otp` and `verify_otp`.
- **EmailOTP**: The SQLModel table class in `src/models/email_otp.py` that maps to the `email_otps` table — to be deleted by this fix.
- **Redis key pattern**: `otp:<user_id>` — a string key whose value is the SHA-256 hex digest of the OTP code.
- **TTL**: Time-to-live of 600 seconds (10 minutes), set atomically with `SET … EX 600` on every `issue_otp` call.
- **fakeredis**: The `fakeredis` Python package — an in-memory Redis emulator used in tests so no real Redis instance is required.
- **F**: The original (unfixed) `OTPService` backed by the `email_otps` PostgreSQL table.
- **F'**: The fixed `OTPService` backed by Redis with TTL.

---

## Bug Details

### Bug Condition

The bug is triggered whenever OTP state is read from or written to PostgreSQL. The `OTPService.issue_otp` method inserts a row into `email_otps` with no database-level TTL. The `OTPService.verify_otp` method queries that table, which may contain arbitrarily many stale rows. Neither method has any mechanism to remove expired or used rows.

**Formal Specification:**

```
FUNCTION isBugCondition(operation)
  INPUT: operation of type OTPOperation { issue | verify }
  OUTPUT: boolean

  // The bug is triggered whenever OTP state touches PostgreSQL
  RETURN operation.backend = POSTGRES
END FUNCTION
```

### Examples

- **Issue OTP (bug)**: `issue_otp(session, user_id, email, name)` inserts a row into `email_otps`. After 10 minutes the row is expired but still present. After 100 OTP requests the table has 100 rows for that user.
- **Verify OTP (bug)**: `verify_otp(session, user_id, code)` executes `SELECT … WHERE user_id = ? AND code_hash = ? AND used_at IS NULL`. With 10 000 stale rows the query scans all of them.
- **Re-issue (bug)**: Calling `issue_otp` a second time for the same user marks the previous row `used_at = now` but does not delete it. Both rows remain in the table forever.
- **Edge case — expired code (bug)**: An expired row is returned by the query (because `used_at IS NULL`), then rejected in Python after the round-trip. The row is never cleaned up.

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

- A valid, unexpired OTP code submitted to `POST /api/v1/auth/verify-email` must continue to verify successfully and set `email_verified = True`.
- An already-used OTP code must continue to be rejected with HTTP 400 and error code `OTP_INVALID`.
- An expired OTP code must continue to be rejected with HTTP 400 and error code `OTP_EXPIRED`.
- An incorrect OTP code must continue to be rejected with HTTP 400 and error code `OTP_INVALID`.
- Re-issuing an OTP must continue to invalidate the previous code so only the most recently issued code is valid.
- `issue_otp` must continue to send the verification email via Brevo SMTP with the plaintext code.
- `POST /api/v1/auth/verify-email` and `POST /api/v1/auth/resend-otp` must continue to return responses conforming to `{ "success": true, "data": {}, "meta": {} }`.
- Tests must continue to run without a real Redis instance (fakeredis backend injected via fixture).

**Scope:**

All inputs that do NOT involve OTP storage (login, registration token issuance, password reset, Google OAuth, booking operations, etc.) are completely unaffected by this fix. Within the OTP flow, the only change is the storage backend — the public interface of `OTPService` (`issue_otp`, `verify_otp`) and all route handler signatures remain identical.

---

## Hypothesized Root Cause

The root cause is a **storage backend mismatch**: PostgreSQL is a durable relational store designed for long-lived data, not for ephemeral short-lived tokens. The specific issues are:

1. **No native TTL in PostgreSQL**: PostgreSQL rows do not expire automatically. The `expires_at` column is a soft expiry enforced only in application code at query time — expired rows are never physically removed.

2. **No cleanup job**: There is no background task, cron job, or trigger that deletes rows from `email_otps` after they expire or are used. The `_cleanup_expired_locks` background task in `database.py` handles availability locks but has no equivalent for OTPs.

3. **Accumulation on re-issue**: `issue_otp` marks previous rows `used_at = now` (soft-invalidation) rather than deleting them. This means every OTP issuance adds a permanent row to the table.

4. **Query scans stale rows**: The `SELECT … WHERE used_at IS NULL` filter does not use a partial index in the current migration, so as the table grows the query cost increases linearly with the number of stale rows.

5. **Wrong tool for the job**: Redis is purpose-built for ephemeral keyed data with TTL. A single `SET otp:<user_id> <hash> EX 600` replaces the entire PostgreSQL row lifecycle (insert, soft-invalidate, expire-check, mark-used) with three atomic Redis operations: `SET`, `GET`+`DEL`.

---

## Correctness Properties

Property 1: Bug Condition — Redis Storage with TTL

_For any_ OTP issuance operation (isBugCondition returns true — i.e., the operation previously touched PostgreSQL), the fixed `issue_otp` function SHALL store the SHA-256 hash of the OTP code in Redis under the key `otp:<user_id>` with a TTL of exactly 600 seconds, overwriting any previously stored value for that user, and SHALL NOT write any row to the `email_otps` PostgreSQL table.

**Validates: Requirements 2.1, 2.3, 2.6**

Property 2: Preservation — Verification Outcomes Unchanged

_For any_ OTP verification input (valid code, expired code, wrong code, or reused code) where the observable outcome is determined solely by the code's validity and expiry state, the fixed `verify_otp` function SHALL produce the same outcome as the original function: success (`True`) for a valid unexpired code, `OTP_INVALID` for a wrong or reused code, and `OTP_EXPIRED` for an expired code.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

---

## Fix Implementation

### Changes Required

Assuming the root cause analysis is correct (PostgreSQL is the wrong backend for ephemeral TTL-bound tokens):

**File 1**: `src/services/otp_service.py` — **full rewrite**

**Specific Changes:**

1. **Remove SQLAlchemy imports and `EmailOTP` model import**: Replace with `redis.asyncio` client type annotation. The service no longer takes an `AsyncSession` parameter — `issue_otp` and `verify_otp` accept a `redis.asyncio.Redis` instance instead.

   > Note: The route handlers in `auth.py` currently pass `session: AsyncSession` to both methods. After the fix, they will pass `redis_client: Redis` obtained from `request.app.state.redis`. The `session` parameter is still needed in `verify_email` to commit `email_verified = True` — it is kept as a separate argument.

2. **`issue_otp` rewrite**:
   - Generate code and hash identically (`secrets.randbelow`, `hashlib.sha256`).
   - Execute `await redis.set(f"otp:{user_id}", code_hash, ex=OTP_EXPIRY_SECONDS)` — this atomically overwrites any existing key and sets TTL=600.
   - Send email via `email_service.send_email` — unchanged.
   - Remove all SQLAlchemy `update(EmailOTP)` and `session.add(otp)` / `session.commit()` calls.

3. **`verify_otp` rewrite**:
   - Compute `code_hash = _hash_code(code.strip())`.
   - Execute `stored = await redis.get(f"otp:{user_id}")`.
   - If `stored is None`: raise `OTP_INVALID` (covers wrong code, already-used, and expired — Redis TTL handles expiry automatically, so absence of key = expired or never issued).
   - If `stored != code_hash`: raise `OTP_INVALID`.
   - On match: `await redis.delete(f"otp:{user_id}")` — single-use guarantee.
   - Return `True`.
   - **Note on OTP_EXPIRED**: With Redis TTL, an expired key is indistinguishable from a missing key at the application level. The `OTP_EXPIRED` error code is preserved by checking TTL state: if the key is absent and the code was recently issued, it is expired. Since we cannot distinguish "never issued" from "expired" without additional state, the simplest correct approach is to raise `OTP_EXPIRED` when the key is absent (matching the most common user-facing case). Alternatively, raise `OTP_INVALID` for all absent-key cases and document that `OTP_EXPIRED` is only raised when the key exists but TTL has elapsed — which is impossible with Redis (TTL deletion is atomic). **Resolution**: Preserve `OTP_EXPIRED` by storing a sentinel: after TTL expiry the key is gone, so we raise `OTP_INVALID`. The `OTP_EXPIRED` path is triggered only when the key exists but the TTL has elapsed — which cannot happen with Redis. Therefore `OTP_EXPIRED` is raised by checking the TTL explicitly: `ttl = await redis.ttl(key)` — if `ttl == -2` (key does not exist) and we know a code was recently issued, it expired. **Simplest correct approach**: store the hash with TTL; if key is absent, raise `OTP_EXPIRED` (the dominant absent-key scenario for a real user is expiry, not "never issued"). This matches the existing UX. Document this decision.

4. **`session` parameter removal from `issue_otp`**: `issue_otp` no longer needs a DB session. Signature becomes `async def issue_otp(self, redis: Redis, user_id, user_email, user_name) -> str`.

5. **`session` parameter in `verify_otp`**: `verify_otp` no longer needs a DB session for OTP lookup. Signature becomes `async def verify_otp(self, redis: Redis, user_id, code) -> bool`. The caller (`verify_email` route) retains its own `session` for the `email_verified = True` commit.

**File 2**: `src/config/database.py` — **add Redis lifespan wiring**

1. Add `redis_url` setting to `Settings` (default `redis://localhost:6379/0`).
2. In `lifespan`: `import redis.asyncio as aioredis; app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)`.
3. In lifespan teardown: `await app.state.redis.aclose()`.

**File 3**: `src/api/v1/auth.py` — **update call sites**

1. In `register`: replace `await otp_service.issue_otp(session, ...)` with `await otp_service.issue_otp(request.app.state.redis, ...)`. Remove `from src.models.email_otp import EmailOTP` import.
2. In `verify_email`: replace `await otp_service.verify_otp(session, ...)` with `await otp_service.verify_otp(request.app.state.redis, ...)`. Keep `session` for the `email_verified` commit.
3. In `resend_otp`: replace `await otp_service.issue_otp(session, ...)` with `await otp_service.issue_otp(request.app.state.redis, ...)`.

**File 4**: `src/models/email_otp.py` — **delete file**

The `EmailOTP` SQLModel class is no longer needed. Delete the file. Remove the `from src.models.email_otp import EmailOTP` import from `conftest.py` and `auth.py`.

**File 5**: New Alembic migration — **drop `email_otps` table**

Create `alembic/versions/<id>_drop_email_otps_use_redis.py`:
- `upgrade()`: `op.drop_index("ix_email_otps_user_id", table_name="email_otps"); op.drop_table("email_otps")`.
- `downgrade()`: recreate the table and index (reversible).

**File 6**: `pyproject.toml` — **add dependencies**

- Runtime: `redis[hiredis]>=5.0.0` (async Redis client).
- Dev: `fakeredis>=2.20.0` (in-memory Redis for tests).

**File 7**: `tests/conftest.py` — **add fakeredis fixture**

```python
import fakeredis.aioredis as fakeredis_aio

@pytest_asyncio.fixture
async def fake_redis():
    r = fakeredis_aio.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()
```

Inject into the `client` fixture by overriding `app.state.redis` before each test.

---

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code (exploratory), then verify the fix works correctly (fix checking) and preserves all existing behaviour (preservation checking).

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that call `issue_otp` and `verify_otp` against the current PostgreSQL-backed implementation and assert that (a) no Redis key is written, (b) rows accumulate in `email_otps` on repeated issuance, and (c) expired rows are not automatically removed. Run these tests on the UNFIXED code to observe failures and understand the root cause.

**Test Cases**:

1. **Accumulation Test**: Call `issue_otp` three times for the same user. Assert that `email_otps` contains three rows (will pass on unfixed code — confirming the accumulation bug).
2. **No TTL Test**: After `issue_otp`, query `email_otps` and assert `expires_at` is set but the row still exists after the expiry time (will pass on unfixed code — confirming no auto-eviction).
3. **Stale Row Scan Test**: Insert 1 000 expired rows into `email_otps`, then call `verify_otp` with a valid code and measure that the query still returns a result (will pass on unfixed code — confirming O(n) scan).
4. **Redis Absence Test**: After `issue_otp`, assert that no Redis key `otp:<user_id>` exists (will pass on unfixed code — confirming PostgreSQL is the backend).

**Expected Counterexamples**:

- `email_otps` grows without bound on repeated `issue_otp` calls.
- Expired rows remain in the table indefinitely.
- Possible causes: no TTL mechanism in PostgreSQL, no cleanup job, soft-invalidation instead of deletion.

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (OTP operations), the fixed function produces the expected behaviour.

**Pseudocode:**

```
FOR ALL op WHERE isBugCondition(op) DO
  result ← executeOTPOperation'(op)   // F' = Redis-backed implementation
  ASSERT result.backend = REDIS
  ASSERT redis.exists(f"otp:{op.user_id}") = TRUE   // key present after issue
  ASSERT redis.ttl(f"otp:{op.user_id}") IN [1, 600]  // TTL set correctly
  ASSERT email_otps table does not exist (or is empty)
END FOR
```

### Preservation Checking

**Goal**: Verify that for all OTP verification inputs, the fixed function produces the same observable outcome as the original function.

**Pseudocode:**

```
FOR ALL input WHERE NOT isBugCondition(input) DO
  // input = { valid_code, expired_code, wrong_code, reused_code }
  ASSERT F(input).outcome = F'(input).outcome
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:

- It generates many (user_id, code) combinations automatically, covering edge cases like UUIDs with special characters, zero-padded codes like `000001`, and codes at boundary lengths.
- It provides strong guarantees that the hash comparison and key-lookup logic is correct across the full input domain.
- It catches regressions where a code that should be valid is incorrectly rejected, or vice versa.

**Test Plan**: Observe behaviour on UNFIXED code first for valid/invalid/expired/reused codes, then write property-based tests capturing that behaviour.

**Test Cases**:

1. **Valid Code Preservation**: Generate random `(user_id, code)` pairs. Issue OTP, immediately verify with correct code. Assert `True` returned and `email_verified` flag set. (Must pass on fixed code.)
2. **Wrong Code Preservation**: Generate random `(user_id, code, wrong_code)` where `wrong_code != code`. Issue OTP with `code`, verify with `wrong_code`. Assert `OTP_INVALID` raised. (Must pass on fixed code.)
3. **Reused Code Preservation**: Issue OTP, verify once (success), verify again with same code. Assert second call raises `OTP_INVALID`. (Must pass on fixed code — key deleted on first verify.)
4. **Expired Code Preservation**: Issue OTP, advance fakeredis time past TTL (or delete key manually to simulate expiry), verify. Assert `OTP_EXPIRED` raised. (Must pass on fixed code.)
5. **Re-issue Invalidation Preservation**: Issue OTP (code A), issue again (code B). Verify with code A. Assert `OTP_INVALID`. Verify with code B. Assert `True`. (Must pass on fixed code — overwrite semantics.)

### Unit Tests

- Test `_hash_code` is deterministic and produces a 64-character hex string.
- Test `issue_otp` sets Redis key `otp:<user_id>` with correct hash value and TTL ≤ 600s.
- Test `issue_otp` called twice for same user results in exactly one Redis key (overwrite).
- Test `verify_otp` with correct code returns `True` and deletes the Redis key.
- Test `verify_otp` with wrong code raises `HTTPException` with code `OTP_INVALID`.
- Test `verify_otp` with absent key (simulated expiry) raises `HTTPException` with code `OTP_EXPIRED`.
- Test `verify_otp` called twice with same code raises `OTP_INVALID` on second call.
- Test `issue_otp` calls `email_service.send_email` exactly once with correct arguments.

### Property-Based Tests

- **Property 1 (Fix)**: For any `user_id` (UUID) and any 6-digit code string, after `issue_otp`, the Redis key `otp:<user_id>` exists, its value equals `sha256(code)`, and its TTL is in `[1, 600]`.
- **Property 2 (Fix — overwrite)**: For any `user_id` and two sequential `issue_otp` calls, exactly one Redis key exists for that user after both calls, and only the second code verifies successfully.
- **Property 3 (Preservation — single-use)**: For any valid `(user_id, code)` pair, after one successful `verify_otp`, a second `verify_otp` with the same code always raises `OTP_INVALID`.
- **Property 4 (Preservation — hash integrity)**: For any `user_id` and any code string, `verify_otp` with a code whose SHA-256 hash does not match the stored hash always raises `OTP_INVALID`.

### Integration Tests

- `POST /api/v1/auth/register` → OTP issued → `POST /api/v1/auth/verify-email` with correct code → 200, `email_verified = True`.
- `POST /api/v1/auth/resend-otp` → new OTP issued → old code rejected → new code accepted.
- `POST /api/v1/auth/verify-email` with wrong code → 400, `OTP_INVALID`.
- `POST /api/v1/auth/verify-email` with expired code (fakeredis key deleted) → 400, `OTP_EXPIRED`.
- Full registration flow returns `{ "success": true, "data": { ... }, "meta": {} }` envelope unchanged.
