# Implementation Plan

## Overview

Migrate OTP storage from the `email_otps` PostgreSQL table to Redis with native TTL. The workflow follows the exploratory bugfix methodology: write tests to confirm the bug exists on unfixed code, write preservation tests to capture baseline behavior, then implement the fix and verify both test suites pass.

## Task Dependency Graph

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1"] },
    { "wave": 2, "tasks": ["2"] },
    { "wave": 3, "tasks": ["3.1"] },
    { "wave": 4, "tasks": ["3.2"] },
    { "wave": 5, "tasks": ["3.3"] },
    { "wave": 6, "tasks": ["3.4"] },
    { "wave": 7, "tasks": ["3.5"] },
    { "wave": 8, "tasks": ["3.6"] },
    { "wave": 9, "tasks": ["3.7"] },
    { "wave": 10, "tasks": ["3.8"] },
    { "wave": 11, "tasks": ["3.9", "3.10"] },
    { "wave": 12, "tasks": ["4"] }
  ]
}
```

## Tasks

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - PostgreSQL OTP Accumulation Bug
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate that OTP state is stored in PostgreSQL (not Redis) and accumulates without TTL
  - **Scoped PBT Approach**: Scope the property to the concrete failing cases — `issue_otp` writes to `email_otps` table and `verify_otp` reads from it; assert that after `issue_otp` no Redis key `otp:<user_id>` exists (will pass on unfixed code, confirming PostgreSQL backend)
  - Create `tests/test_otp_bug_condition.py` using `fakeredis.aioredis.FakeRedis` and the existing `db_session` fixture
  - Test 1 — Accumulation: call `issue_otp` three times for the same user; assert `email_otps` table contains three rows (confirms unbounded growth)
  - Test 2 — No Redis key: after `issue_otp`, assert `await fake_redis.exists(f"otp:{user_id}") == 0` (confirms PostgreSQL is the backend, not Redis)
  - Test 3 — No TTL eviction: insert an expired row directly into `email_otps`; assert the row still exists after the expiry timestamp has passed (confirms no auto-eviction)
  - Run tests on UNFIXED code: `uv run pytest tests/test_otp_bug_condition.py -v`
  - **EXPECTED OUTCOME**: Tests 1 and 3 PASS (confirming accumulation bug); Test 2 PASSES (confirming no Redis key written) — all three confirm the bug exists
  - Document counterexamples found (e.g., "After 3 issue_otp calls, email_otps has 3 rows; no Redis key otp:<user_id> was written")
  - Mark task complete when tests are written, run, and findings are documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - OTP Verification Outcomes Unchanged
  - **IMPORTANT**: Follow observation-first methodology — observe behavior on UNFIXED code for non-buggy inputs first
  - Observe: `verify_otp(session, user_id, correct_code)` returns `True` on unfixed code
  - Observe: `verify_otp(session, user_id, wrong_code)` raises `HTTPException` with code `OTP_INVALID` on unfixed code
  - Observe: `verify_otp(session, user_id, correct_code)` called twice raises `OTP_INVALID` on second call (single-use)
  - Observe: `verify_otp(session, user_id, expired_code)` raises `HTTPException` with code `OTP_EXPIRED` on unfixed code
  - Observe: after re-issuing OTP (code B), verifying with old code A raises `OTP_INVALID`
  - Create `tests/test_otp_preservation.py` using `hypothesis` for property-based generation
  - **Property 2a — Valid code**: for any `user_id` (UUID) and any 6-digit code string, after `issue_otp` + immediate `verify_otp` with correct code, result is `True` (use `@given(st.uuids(), st.from_regex(r'\d{6}'))`)
  - **Property 2b — Wrong code**: for any `(user_id, code, wrong_code)` where `wrong_code != code`, after `issue_otp(code)`, `verify_otp(wrong_code)` raises `OTP_INVALID`
  - **Property 2c — Single-use**: for any valid `(user_id, code)`, after one successful `verify_otp`, a second `verify_otp` with the same code raises `OTP_INVALID`
  - **Property 2d — Re-issue invalidation**: for any `user_id`, after `issue_otp` (code A) then `issue_otp` (code B), `verify_otp(code_A)` raises `OTP_INVALID` and `verify_otp(code_B)` returns `True`
  - Run tests on UNFIXED code: `uv run pytest tests/test_otp_preservation.py -v`
  - **EXPECTED OUTCOME**: All preservation tests PASS on unfixed code (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 3. Fix: migrate OTP storage from PostgreSQL to Redis

  - [x] 3.1 Add project dependencies
    - Add `redis[hiredis]>=5.0.0` to runtime dependencies in `pyproject.toml`
    - Add `fakeredis>=2.20.0` to dev dependencies in `pyproject.toml`
    - Run `uv sync` from `packages/backend` to install
    - _Requirements: 2.1, 2.4_

  - [x] 3.2 Wire Redis client into application lifespan (`src/config/database.py`)
    - Add `redis_url: str = "redis://localhost:6379/0"` to `Settings` class
    - Import `redis.asyncio as aioredis` at top of file
    - In `lifespan` startup block: `app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)`
    - In `lifespan` teardown block: `await app.state.redis.aclose()`
    - _Bug_Condition: isBugCondition(op) where op.backend = POSTGRES — this wires the Redis backend that replaces it_
    - _Expected_Behavior: app.state.redis is a live redis.asyncio.Redis client available to all route handlers_
    - _Requirements: 2.1, 2.4_

  - [x] 3.3 Rewrite `src/services/otp_service.py` to use Redis
    - Remove `from sqlalchemy.ext.asyncio import AsyncSession`, `from src.models.email_otp import EmailOTP`, and all SQLAlchemy `select`/`update`/`add`/`commit` imports
    - Add `import redis.asyncio as aioredis` type annotation import
    - Rewrite `issue_otp(self, redis: aioredis.Redis, user_id, user_email, user_name) -> str`:
      - Generate code and hash identically (`secrets.randbelow`, `hashlib.sha256`) — unchanged
      - Execute `await redis.set(f"otp:{user_id}", code_hash, ex=600)` — atomically overwrites any existing key and sets TTL=600
      - Send email via `email_service.send_email` — unchanged
      - Remove all `update(EmailOTP)`, `session.add()`, `session.commit()` calls
    - Rewrite `verify_otp(self, redis: aioredis.Redis, user_id, code) -> bool`:
      - Compute `code_hash = _hash_code(code.strip())`
      - Execute `stored = await redis.get(f"otp:{user_id}")`
      - If `stored is None`: raise `HTTPException` with code `OTP_EXPIRED` (absent key = expired or never issued; dominant UX case is expiry)
      - If `stored != code_hash`: raise `HTTPException` with code `OTP_INVALID`
      - On match: `await redis.delete(f"otp:{user_id}")` — single-use guarantee
      - Return `True`
    - _Bug_Condition: isBugCondition(op) where op.backend = POSTGRES — all PostgreSQL OTP reads/writes are removed_
    - _Expected_Behavior: issue_otp sets otp:<user_id> in Redis with TTL=600; verify_otp does O(1) GET+DEL; no email_otps rows written_
    - _Preservation: SHA-256 hashing unchanged; OTP_INVALID/OTP_EXPIRED error codes preserved; email delivery via Brevo SMTP unchanged_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 3.4 Update call sites in `src/api/v1/auth.py`
    - Remove `from src.models.email_otp import EmailOTP` import
    - In `register` handler: replace `await otp_service.issue_otp(session, ...)` with `await otp_service.issue_otp(request.app.state.redis, ...)`
    - In `verify_email` handler: replace `await otp_service.verify_otp(session, ...)` with `await otp_service.verify_otp(request.app.state.redis, ...)`; keep `session` for the `email_verified = True` commit
    - In `resend_otp` handler: replace `await otp_service.issue_otp(session, ...)` with `await otp_service.issue_otp(request.app.state.redis, ...)`
    - _Requirements: 2.1, 3.7_

  - [x] 3.5 Delete `src/models/email_otp.py`
    - Delete the file `src/models/email_otp.py`
    - Remove any remaining `from src.models.email_otp import EmailOTP` imports from `tests/conftest.py` and any other files
    - _Requirements: 2.1, 2.3_

  - [x] 3.6 Create Alembic migration to drop `email_otps` table
    - Run `uv run alembic revision -m "drop_email_otps_use_redis"` from `packages/backend`
    - In `upgrade()`: `op.drop_index("ix_email_otps_user_id", table_name="email_otps"); op.drop_table("email_otps")`
    - In `downgrade()`: recreate the `email_otps` table with all original columns (`id`, `user_id`, `code_hash`, `expires_at`, `used_at`, `created_at`) and recreate `ix_email_otps_user_id` index (reversible)
    - Apply migration: `uv run alembic upgrade head`
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.7 Add fakeredis fixture to `tests/conftest.py`
    - Add import: `import fakeredis.aioredis as fakeredis_aio`
    - Add `fake_redis` fixture:
      ```python
      @pytest_asyncio.fixture
      async def fake_redis():
          r = fakeredis_aio.FakeRedis(decode_responses=True)
          yield r
          await r.aclose()
      ```
    - Update the `client` fixture to override `app.state.redis` with `fake_redis` before each test: `app.state.redis = fake_redis_instance`
    - _Preservation: tests continue to run without a real Redis instance_
    - _Requirements: 3.8_

  - [x] 3.8 Write unit tests for the rewritten `OTPService`
    - Create or update `tests/test_otp_service.py`
    - Test `_hash_code` is deterministic and produces a 64-character hex string
    - Test `issue_otp` sets Redis key `otp:<user_id>` with correct hash value and TTL in `[1, 600]`
    - Test `issue_otp` called twice for same user results in exactly one Redis key (overwrite semantics)
    - Test `issue_otp` calls `email_service.send_email` exactly once with correct arguments
    - Test `verify_otp` with correct code returns `True` and deletes the Redis key
    - Test `verify_otp` with wrong code raises `HTTPException` with code `OTP_INVALID`
    - Test `verify_otp` with absent key raises `HTTPException` with code `OTP_EXPIRED`
    - Test `verify_otp` called twice with same code raises `OTP_INVALID` on second call
    - All tests use `fake_redis` fixture — no real Redis
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.2, 3.3, 3.4_

  - [x] 3.9 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Redis Storage with TTL
    - **IMPORTANT**: Re-run the SAME tests from task 1 — do NOT write new tests
    - The tests from task 1 encode the expected behavior (no PostgreSQL writes, Redis key present, TTL set)
    - Run: `uv run pytest tests/test_otp_bug_condition.py -v`
    - **EXPECTED OUTCOME**: Tests PASS (confirms bug is fixed — Redis key exists, no email_otps rows written)
    - _Requirements: 2.1, 2.3, 2.6_

  - [x] 3.10 Verify preservation tests still pass
    - **Property 2: Preservation** - OTP Verification Outcomes Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run: `uv run pytest tests/test_otp_preservation.py -v`
    - **EXPECTED OUTCOME**: All preservation tests PASS (confirms no regressions — valid/invalid/expired/reused code outcomes unchanged)
    - Confirm all property-based tests pass with the Redis-backed implementation
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [~] 4. Checkpoint — Ensure all tests pass
  - Run the full test suite: `uv run pytest -v` from `packages/backend`
  - Confirm `tests/test_otp_bug_condition.py` passes (bug fixed)
  - Confirm `tests/test_otp_preservation.py` passes (no regressions)
  - Confirm `tests/test_otp_service.py` passes (unit tests)
  - Confirm integration tests pass: register → verify-email flow, resend-otp flow, wrong/expired code paths
  - Confirm response envelope `{ "success": true, "data": {}, "meta": {} }` is unchanged on all OTP endpoints
  - Run Ruff: `uv run ruff check src/ tests/` and `uv run ruff format src/ tests/`
  - Ensure all tests pass; ask the user if questions arise

## Notes

- Run all Python commands with `uv run` from `packages/backend` — never use `pip` or activate the venv manually
- Tests use `sqlite+aiosqlite:///:memory:` for the DB layer and `fakeredis` for Redis — no real Redis or Neon instance required
- The `OTP_EXPIRED` error code is preserved: when the Redis key is absent (TTL elapsed or never issued), `verify_otp` raises `OTP_EXPIRED` to match the dominant user-facing case
- SHA-256 hashing logic in `_hash_code` is correct and must not be changed
- The `session` parameter is retained in `verify_email` route handler for the `email_verified = True` commit — only the OTP lookup is moved to Redis
- Every schema change requires a reversible Alembic migration (`downgrade()` must recreate the table)
- Ruff is the formatter and linter — run `uv run ruff check` and `uv run ruff format` before marking complete
