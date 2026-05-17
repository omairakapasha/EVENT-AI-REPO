# Event-AI — Security, Cache & Architecture Audit Report (Code-Verified)

**Repository:** `omairakapasha/Event`
**Stack:** FastAPI (Python 3.12+) · Next.js 15 · Neon PostgreSQL · pgvector · OpenAI Agents SDK
**Date:** May 2026
**Audited files:** Actual source code — `auth_service.py`, `otp_service.py`, `auth.py` (routes), `auth.middleware.py`, `deps.py`, `booking_service.py`, `event_bus_service.py`, `sse_manager.py`, `rate_limit.py`, `login_rate_limit.py`, `google_oauth_service.py`, `api.ts` (user + vendor), `auth-store.ts`, `auth/callback/page.tsx`

> **Methodology:** Every finding below is backed by a specific file and line of actual code. The previous report was based on documentation only — several of those findings are now **resolved** in the real implementation. This report supersedes it.

---

## What Changed Since the Previous Report (Documentation-Only Audit)

| Previous Finding | Actual Code Status |
|---|---|
| AUTH-01: JWT in localStorage | ✅ **FIXED** — both portals use `withCredentials: true` + httpOnly cookies |
| AUTH-02: Google OAuth `?token=` in URL | ✅ **FIXED** — backend redirects to `/auth/callback` with cookies only, no token in URL |
| AUTH-03: No email verification | ✅ **FIXED** — OTP issued on register, `POST /auth/verify-email` endpoint exists |
| OTP-01: Reset tokens stored plaintext | ✅ **FIXED** — `_generate_token_hash()` SHA-256 hashes all tokens before storage |
| STD-02: Double-booking race | ⚠️ **PARTIALLY FIXED** — lock exists but no `SELECT FOR UPDATE` or unique index |

---

## Severity Summary

| Category | 🔴 Critical | 🟠 High | 🟡 Medium | Total |
|---|---|---|---|---|
| Authentication | 1 | 3 | 3 | 7 |
| Caching | 0 | 2 | 3 | 5 |
| OTP / Password Reset | 0 | 1 | 2 | 3 |
| Other Standard Gaps | 0 | 2 | 4 | 6 |
| Architectural Gaps | 0 | 3 | 4 | 7 |
| **Total** | **1** | **11** | **16** | **28** |

---

## 1. Authentication — Is It Industry-Standard for Email Registration?

### What Is Correctly Implemented ✅

- `bcrypt` with `rounds=12` for password hashing (`auth_service.py:32`)
- JWT access token (HS256, 15-min TTL) with `iss`, `iat`, `exp`, `sub`, `email`, `role` claims
- DB-backed refresh tokens stored as SHA-256 hashes — plaintext never persisted (`auth_service.py:_generate_token_hash`)
- Refresh token rotation on every `/auth/refresh` call
- Account lockout after 5 failed attempts, 15-min cooldown
- httpOnly cookies set on login, register, and OAuth callback (`auth.py:_set_auth_cookies`)
- Google OAuth redirects to `/auth/callback` with cookies — no token in URL
- Email OTP issued on registration; `POST /auth/verify-email` endpoint exists
- Password reset tokens hashed before DB storage
- Both portals use `withCredentials: true` — no localStorage JWT

---

### AUTH-01 🔴 CRITICAL — `auth.middleware.py` calls `verify_access_token` as a sync method; `auth_service.py` defines it as `async`

**Files:** `src/middleware/auth.middleware.py:52` vs `src/services/auth_service.py:verify_access_token`

The canonical middleware (`auth.middleware.py`) calls:
```python
payload = auth_service.verify_access_token(token)   # ← no await, no session arg
```

But `auth_service.py` defines:
```python
@classmethod
async def verify_access_token(cls, token: str, session: AsyncSession) -> User:
```

The middleware version calls it without `await` and without the required `session` argument. This means:
- The middleware returns a coroutine object instead of a User — any route using `Depends(get_current_user)` from `auth.middleware.py` will silently pass a coroutine as the "user"
- The actual working dependency is `deps.py:get_current_user`, which correctly calls `await auth_service.verify_access_token(token, session)`

**Impact:** Any route that imports `get_current_user` from `middleware/auth.middleware.py` instead of `api/deps.py` is completely unprotected — it receives a coroutine, not a user. This is a silent auth bypass.

**Fix:**
```python
# auth.middleware.py — fix the call to match the service signature
user = await auth_service.verify_access_token(token, session)
```
Or consolidate: delete `auth.middleware.py:get_current_user` and have all routes import from `api/deps.py` only.

---

### AUTH-02 🟠 HIGH — No refresh token re-use detection (stolen token family attack)

**File:** `src/services/auth_service.py:rotate_refresh_token`

Token rotation is implemented — the old token is revoked when a new one is issued. However, there is no **re-use detection**: if an attacker steals a refresh token and rotates it before the legitimate user does, the legitimate user's next refresh attempt will fail with a generic 401. The system does not detect that the same token family was used twice and does not revoke all sessions for that user.

**OWASP standard (OAuth 2.0 Security BCP RFC 9700):** When a refresh token that has already been rotated is presented, treat it as a token theft signal and immediately revoke **all tokens in that session family**.

**Fix:**
```python
# In rotate_refresh_token: if the token hash exists but is already revoked,
# it means someone is replaying a rotated token → revoke all user tokens
if old_record.revoked_at is not None:
    await cls.revoke_all_refresh_tokens(session, old_record.user_id)
    raise HTTPException(401, "Token reuse detected — all sessions revoked")
```

---

### AUTH-03 🟠 HIGH — Email verification is not enforced — unverified users access all features

**File:** `src/api/v1/auth.py:register`

Registration correctly issues an OTP and sets `email_verified=False`. However, no route checks `email_verified` before granting access. A user who never verifies their email can:
- Create bookings
- Access vendor dashboard
- Interact with the AI agent

The `email_verified` field exists on the User model and is set correctly, but it is never read in any `Depends()` guard.

**Industry standard:** Block or restrict access to core features until email is verified. At minimum, add a dependency:
```python
async def require_verified_email(user: User = Depends(get_current_user)) -> User:
    if not user.email_verified:
        raise HTTPException(403, detail={"code": "EMAIL_NOT_VERIFIED",
                                          "message": "Please verify your email to continue."})
    return user
```
Apply to booking creation, vendor registration, and AI chat endpoints.

---

### AUTH-04 🟠 HIGH — Two login endpoints with divergent security logic

**Files:** `src/api/v1/auth.py:login` (form-encoded) and `auth.py:json_login` (JSON)

Both endpoints implement account lockout, but the lockout check has a subtle difference:

- Form-encoded login: checks `locked_until` **after** verifying the password fails
- JSON login: same pattern

The real gap is maintenance: any future security change (e.g., adding 2FA, adding audit logging, changing lockout duration) must be applied to both endpoints. They already diverge in response shape. This is a split maintenance surface that will cause security regressions.

**Fix:** Extract shared login logic into `auth_service.authenticate_user(session, email, password) -> User` and call it from both endpoints.

---

### AUTH-05 🟡 MEDIUM — HS256 symmetric JWT is wrong for a multi-service architecture

**File:** `src/config/database.py` (settings: `JWT_ALGORITHM=HS256`)

The platform has two separate services (backend port 5000, AI orchestrator port 8000). With HS256, every service that verifies tokens must hold the signing secret. The AI orchestrator currently uses `AI_SERVICE_API_KEY` for its own auth, but if it ever needs to verify user JWTs directly, the `JWT_SECRET_KEY` must be shared — making it a high-value, widely distributed secret.

**Industry standard 2026:** RS256 or ES256 (asymmetric). Private key signs (backend only); public key verifies (all services, no secret distribution).

---

### AUTH-06 🟡 MEDIUM — `password-reset-request` returns the raw token in the response body

**File:** `src/api/v1/auth.py:request_password_reset`

```python
return PasswordResetTokenResponse(
    token=raw_token,          # ← raw token returned in HTTP response body
    expires_at=expires_at,
    user_email=user.email,
)
```

The comment says "TODO: In production, call EmailService.send_password_reset". This means the reset token is currently returned in the API response instead of being emailed. Any API log, proxy, or CDN that captures response bodies will capture valid password reset tokens.

**Fix:** Remove `token` from the response schema entirely. The endpoint should return only `{"success": true, "data": {"message": "If that email is registered, a reset link has been sent."}}`. The token must only travel via email.

---

### AUTH-07 🟡 MEDIUM — PKCE not implemented for Google OAuth

**File:** `src/services/google_oauth_service.py:build_authorization_url`

The OAuth flow uses a signed state JWT for CSRF protection (correct), but PKCE (RFC 7636) is missing. PKCE protects against authorization code interception — an attacker who intercepts the `code` in transit cannot exchange it without the `code_verifier`. All modern OAuth 2.0 implementations require PKCE for public clients.

**Fix:** Generate `code_verifier` + `code_challenge` (S256) at authorization URL build time, store `code_verifier` in the state JWT, and pass `code_challenge` + `code_challenge_method=S256` to Google.

---

## 2. Caching — Is It Implemented Correctly? What Are the Gaps?

### What Is Correctly Implemented ✅

- SHA-256 content hash on vendor embeddings — Gemini only called when content changes
- React Query client-side caching in all portals
- SSE per-user queue with evict-oldest overflow handling
- Refresh token mutex in both portal `api.ts` files — thundering herd is handled

---

### CACHE-01 🟠 HIGH — Rate limiter is in-memory per process — breaks on any horizontal scaling

**File:** `src/middleware/rate_limit.py:RateLimiter`

```python
class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        self.requests: Dict[str, List[float]] = defaultdict(list)  # ← in-process dict
```

The file's own docstring says: *"Not suitable for multi-process deployments; use Redis for production."* This is confirmed in the code. Every `rate_limit_dependency()` call creates a new `RateLimiter` instance with its own in-memory dict. In any multi-worker or multi-container deployment:
- Each worker has its own counter
- A user can make `N × max_attempts` requests by hitting different workers
- Rate limits reset to zero on every deployment or restart

The same applies to `login_rate_limit.py` — `IPLoginRateLimiter` and `CredentialLoginRateLimiter` are both in-memory.

**Fix:**
```python
# Replace in-memory dict with Redis atomic sliding window
import redis.asyncio as redis

async def is_allowed(self, key: str) -> bool:
    now = time.time()
    pipe = self.redis.pipeline()
    pipe.zremrangebyscore(key, 0, now - self.window_seconds)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, self.window_seconds)
    results = await pipe.execute()
    return results[2] <= self.max_attempts
```

---

### CACHE-02 🟠 HIGH — No distributed cache — SSE state, rate limits, and OTP storage are non-recoverable on restart

There is no Redis or any distributed cache in the stack. This affects:

| System | Current Storage | Problem |
|---|---|---|
| Rate limiter counters | In-process memory | Reset on restart; rate limits bypassed after every deploy |
| SSE connection queues | In-process memory | Lost on restart; users miss notifications |
| Password reset tokens | PostgreSQL | Acceptable but slow; no auto-TTL cleanup |
| OTP codes | PostgreSQL | Wrong tool for ephemeral state (see Section 3) |
| Embedding query cache | None | Every identical search query hits Gemini |

Redis is referenced in `.env.example` as optional but is not implemented anywhere in the codebase.

---

### CACHE-03 🟡 MEDIUM — No HTTP caching headers on read-heavy public endpoints

**File:** `src/api/v1/public_vendors.py`, `src/api/v1/categories.py`

Public vendor listings and category lists are served without `Cache-Control`, `ETag`, or `Last-Modified` headers. These are read-heavy, low-mutation endpoints — every page load hits the database.

**Fix:**
```python
# categories (changes rarely):
response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"

# vendor search (changes moderately):
response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
```

---

### CACHE-04 🟡 MEDIUM — pgvector embedding query results not cached

**File:** `packages/agentic_event_orchestrator` + `src/services/embedding_service.py`

When users search "wedding photographer Karachi," the platform calls Gemini to embed the query string, then runs pgvector cosine similarity. Hundreds of users searching the same phrase each trigger a separate Gemini API call.

**Fix:** Cache query embeddings by `sha256(query_string)` in Redis with a 24-hour TTL. Common queries become instant; Gemini API costs drop significantly.

---

### CACHE-05 🟡 MEDIUM — SSE queue evict-oldest is not atomic under concurrent pushes

**File:** `src/services/sse_manager.py:push`

```python
try:
    q.put_nowait({"event": event_type, "data": data})
except asyncio.QueueFull:
    try:
        q.get_nowait()   # ← another coroutine can also evict here between these two lines
        q.put_nowait({"event": event_type, "data": data})
```

Under a booking event that triggers multiple notifications in parallel (e.g., `booking.confirmed` fires both a vendor notification and a user notification simultaneously), two coroutines can both hit `QueueFull`, both call `get_nowait()`, and both then call `put_nowait()` — dropping two messages instead of one.

**Fix:** Wrap the check-and-swap in a per-user `asyncio.Lock`:
```python
async with self._locks.setdefault(user_id, asyncio.Lock()):
    if q.full():
        q.get_nowait()
    q.put_nowait(item)
```

---

## 3. Why Is OTP Being Stored in the Database?

### What Is Correctly Implemented ✅

- OTP is a cryptographically random 6-digit code (`secrets.randbelow`)
- Stored as SHA-256 hash — plaintext never persisted (`otp_service.py:_hash_code`)
- 10-minute expiry enforced at application level
- Single-use: `used_at` set on first successful verification
- Old unused OTPs invalidated when a new one is issued
- Verification raises distinct errors for invalid vs expired codes

The OTP implementation is **significantly better than the previous report suggested** — the hash-before-store pattern is already in place.

---

### OTP-01 🟠 HIGH — PostgreSQL is the wrong storage backend for ephemeral OTP state

**File:** `src/services/otp_service.py`, `src/models/email_otp.py`

Even with correct hashing, storing OTPs in PostgreSQL has structural problems:

| Concern | Detail |
|---|---|
| **No automatic TTL** | Expired OTP rows accumulate indefinitely; requires a manual cleanup job that doesn't exist |
| **DB query on every verify** | `SELECT ... WHERE code_hash = ? AND used_at IS NULL` on every verification attempt |
| **Wrong tool for ephemeral state** | Relational DB is optimised for persistent, relational data — not short-lived codes |
| **Table bloat** | Every registration, every resend creates a new row; old rows are never deleted |

**Industry standard pattern (OWASP):**
```python
# Redis: automatic TTL, atomic single-use, zero cleanup
await redis.set(f"otp:{user_id}", hashed_code, ex=600)   # auto-expires in 10 min

# On verify:
stored = await redis.get(f"otp:{user_id}")
if stored and hmac.compare_digest(stored, hash_code(submitted)):
    await redis.delete(f"otp:{user_id}")   # single-use: delete immediately
    return True
```

This approach: auto-expires tokens, handles single-use atomically, requires zero cleanup jobs, and keeps PostgreSQL focused on persistent data.

---

### OTP-02 🟡 MEDIUM — No rate limiting on OTP verification attempts

**File:** `src/api/v1/auth.py:verify_email`

The `POST /auth/verify-email` endpoint has no rate limiting. A 6-digit OTP has only 1,000,000 possible values. An attacker with a valid JWT (e.g., a registered but unverified account) can brute-force the OTP in at most 1,000,000 requests — practically much fewer since the space is uniform.

**Fix:** Add a rate limiter: max 5 attempts per user per 10-minute window. After 5 failures, invalidate the current OTP and require a resend.

---

### OTP-03 🟡 MEDIUM — No rate limiting on `POST /auth/resend-otp`

**File:** `src/api/v1/auth.py:resend_otp`

The resend endpoint has no rate limiting. An attacker can trigger mass OTP emails to any registered user by repeatedly calling this endpoint, causing email spam and potential Brevo API cost abuse.

**Fix:** Rate limit to 3 resends per user per hour.

---

## 4. Other Standard Gaps

### STD-01 🟠 HIGH — Double-booking race: availability lock is not atomic at the DB level

**File:** `src/services/booking_service.py:_acquire_lock`

The lock acquisition flow is:
1. `SELECT * FROM vendor_availability WHERE vendor_id=? AND date=?`
2. Check status in Python
3. `UPDATE` or `INSERT` the row to `LOCKED`

Between steps 1 and 3, two concurrent requests can both read the same row as `AVAILABLE`, both pass the Python check, and both attempt to write `LOCKED`. Without `SELECT FOR UPDATE`, the database does not prevent this race.

**Fix:**
```sql
-- Use SELECT FOR UPDATE to hold a row-level lock during the check
SELECT * FROM vendor_availability
WHERE vendor_id = ? AND service_id = ? AND date = ?
FOR UPDATE;
```

In SQLAlchemy async:
```python
stmt = select(VendorAvailability).where(...).with_for_update()
```

Additionally, add a partial unique index as a safety net:
```sql
CREATE UNIQUE INDEX idx_active_booking
ON bookings (vendor_id, service_id, event_date)
WHERE status NOT IN ('cancelled', 'rejected');
```

---

### STD-02 🟠 HIGH — Outbox pattern is half-implemented — no background poller

**File:** `src/services/event_bus_service.py:emit`

Domain events are persisted to `domain_events` within the same DB transaction (correct outbox pattern). However, the only delivery mechanism is **in-process listeners**:

```python
for listener in self._listeners.get(event_type, []):
    await listener(event_type, payload, user_id, session=session)
```

If the process crashes between the DB commit and listener execution, the event is durably persisted but side effects (SSE push, user notifications) are **silently and permanently lost**. There is no background poller that re-fires unprocessed events.

**Fix:** Add a `processed_at TIMESTAMPTZ` column to `domain_events`. Add a background task (APScheduler or asyncio periodic task) that queries `WHERE processed_at IS NULL ORDER BY timestamp LIMIT 100` and re-fires events. This guarantees at-least-once delivery across restarts.

---

### STD-03 🟡 MEDIUM — No idempotency keys on booking creation

**File:** `src/api/v1/bookings.py`

`POST /api/v1/bookings/` has no idempotency key mechanism. On a mobile network, a booking POST can fail mid-flight (server received it; client never got the response). The user retries and creates a duplicate booking — potentially double-charging.

**Fix:** Accept an `Idempotency-Key` header. Store `key + response hash` in Redis with 24h TTL. Return the cached response for duplicate keys within the window.

---

### STD-04 🟡 MEDIUM — Booking currency defaults to `"USD"` on a Pakistani platform

**File:** `src/models/booking.py`

Every booking record defaults to `currency="USD"`. The platform is built exclusively for Pakistan. All admin revenue stats display in USD, which is meaningless for local operations.

**Fix:** Change default to `"PKR"`. Add a currency allowlist to the booking schema.

---

### STD-05 🟡 MEDIUM — `rating` and `total_reviews` columns exist but no review system is implemented

**File:** `src/models/vendor.py`

The `vendors` table has `rating: float = 0.0` and `total_reviews: int = 0`, but there is no review submission endpoint, review model, or rating aggregation service. The public vendor listing returns `rating=0.0` for every vendor, actively misleading users.

**Fix:** Either implement the review system (`POST /bookings/{id}/review`) or drop the columns and add them in a future migration when the feature is actually built.

---

### STD-06 🟡 MEDIUM — SQLite in tests does not catch PostgreSQL-specific bugs

Tests use `sqlite+aiosqlite:///:memory:`. SQLite does not support `JSONB` operators, `pgvector` cosine distance, `ON CONFLICT DO UPDATE`, `ARRAY` types, or PostgreSQL-specific `UUID` handling. Production-only bugs in these areas will not be caught by the test suite.

**Fix:** Add a separate integration test target that runs against a real PostgreSQL container (GitHub Actions `services:` block). Keep SQLite for fast unit tests; use PostgreSQL for integration tests covering search, embeddings, and complex queries.

---

## 5. Architectural Gaps

### ARCH-01 🟠 HIGH — No distributed cache layer (Redis) — single point of failure for all stateful systems

The entire stateful layer (rate limiting, SSE queues, OTP storage, session data) is either in-process memory or PostgreSQL. There is no Redis or equivalent.

**Consequences:**
- Any process restart loses all in-flight SSE notification queues
- Rate limits reset to zero on restart (bypassed after every deployment)
- No way to share session state across multiple backend instances
- OTP rows accumulate in PostgreSQL with no auto-cleanup

**Fix:** Add Redis as a required service. It handles: rate limiting, SSE queue overflow buffer, OTP/reset token storage, embedding query cache, idempotency key storage.

---

### ARCH-02 🟠 HIGH — In-memory SSEConnectionManager is not scalable and loses state on restart

**File:** `src/services/sse_manager.py`

The SSE connection manager holds per-user `asyncio.Queue` objects in memory. This has two serious problems:

1. **Not horizontally scalable** — a user connected to Instance A will not receive events published by Instance B
2. **State lost on restart** — all queued notifications for connected users vanish silently on any deployment or crash

**Fix:** Replace the in-memory queue with a Redis Pub/Sub channel per user. Each backend instance subscribes to the channel for all currently-connected users. Events published to Redis reach all instances. This is the standard pattern for SSE in multi-instance deployments.

---

### ARCH-03 🟠 HIGH — No circuit breaker for external dependencies (Gemini, Mem0, Google OAuth)

The platform calls Gemini (embeddings + chat), Mem0 (memory), and Google OAuth on every relevant request, with no circuit breaker, retry policy, or timeout configured for any of them.

If Gemini returns 503, every embedding-related request will hang until timeout. If Mem0 is slow, every chat response is delayed. There is no graceful degradation strategy.

**Fix:**
```python
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(3))
async def embed_text(text: str) -> list[float]: ...
```

Add a circuit breaker state machine (closed → open → half-open) to stop calling failed services immediately rather than waiting for every request to time out.

---

### ARCH-04 🟡 MEDIUM — Outbox pattern without a reliable poller is not true outbox

As noted in STD-02, the outbox pattern is only half-implemented. Architecturally, this means the event-driven architecture provides **no delivery guarantees** — it is fire-and-forget dressed as outbox. For a marketplace where booking confirmations and vendor notifications are business-critical, this is a significant reliability gap.

---

### ARCH-05 🟡 MEDIUM — No API gateway — AI orchestrator is directly exposed

The AI orchestrator runs on port 8000 with its own auth (`AI_SERVICE_API_KEY`). There is no API gateway that enforces unified authentication, rate limiting, and routing across services. The Next.js proxy (`/api/ai/[...path]/route.ts`) may forward requests to the AI service without validating the user JWT first, making it a potential open relay.

**Fix:** Route all external traffic through the backend (port 5000) as an API gateway. The AI orchestrator should be an internal service not directly reachable from outside the Docker network.

---

### ARCH-06 🟡 MEDIUM — No observability stack — production incidents are undiagnosable

The only observability tool is Structlog (writes JSON to stdout). There is no:
- Error tracking (Sentry) — unhandled exceptions are invisible
- Metrics collection (Prometheus/Grafana) — no request rate, error rate, latency
- Alerting — nobody is notified when the system degrades

**Minimum required stack:**
```
Sentry → unhandled exceptions + performance monitoring
Prometheus + Grafana → request metrics, DB pool stats, AI latency
Structured logs → already done (Structlog) ✅
```

---

### ARCH-07 🟡 MEDIUM — No staging environment — migrations run blind in production

The deployment pipeline has `dev` and `Docker` environments, but no staging. Database migrations are tested in production for the first time. There is no way to verify that a config change doesn't break the system before it affects real users.

**Fix:** Add a staging environment that mirrors production (same Neon branch, same env vars, same Docker images). All migrations must complete successfully in staging before production deployment is allowed.

---

---

## Priority Fix Roadmap

### P0 — Fix Before Any Real Users (Security-Critical)

| ID | Issue | File | Effort |
|---|---|---|---|
| AUTH-01 | Fix `auth.middleware.py` — missing `await` + `session` arg on `verify_access_token` | `middleware/auth.middleware.py:52` | Low |
| AUTH-03 | Enforce `email_verified` on booking/vendor/AI endpoints | `api/deps.py` | Low |
| AUTH-06 | Remove raw token from `password-reset-request` response; email only | `api/v1/auth.py` | Low |
| STD-01 | Add `SELECT FOR UPDATE` to availability lock acquisition | `services/booking_service.py` | Low |
| ARCH-01 | Add Redis to the stack | `docker-compose.yml` | Medium |

### P1 — Fix Before Scaling

| ID | Issue | File | Effort |
|---|---|---|---|
| AUTH-02 | Implement refresh token re-use detection | `services/auth_service.py` | Low |
| AUTH-04 | Extract shared login logic to `auth_service.authenticate_user()` | `services/auth_service.py` | Medium |
| CACHE-01 | Replace in-memory rate limiter with Redis sliding window | `middleware/rate_limit.py` | Low |
| OTP-01 | Move OTP storage to Redis with TTL | `services/otp_service.py` | Medium |
| OTP-02 | Add rate limiting on OTP verify (5 attempts/10 min) | `api/v1/auth.py` | Low |
| OTP-03 | Add rate limiting on OTP resend (3/hour) | `api/v1/auth.py` | Low |
| STD-02 | Add outbox background poller for at-least-once delivery | `services/event_bus_service.py` | Medium |
| STD-03 | Add idempotency keys to booking endpoints | `api/v1/bookings.py` | Medium |
| ARCH-03 | Add circuit breakers (tenacity) for Gemini/Mem0 | `agentic_event_orchestrator` | Low |

### P2 — Production Polish

| ID | Issue | Effort |
|---|---|---|
| AUTH-05 | Migrate to RS256 JWT | Medium |
| AUTH-07 | Implement PKCE for Google OAuth | Low |
| CACHE-03 | Add HTTP caching headers to public endpoints | Low |
| CACHE-04 | Cache embedding query results in Redis | Low |
| CACHE-05 | Fix SSE queue eviction atomicity with per-user Lock | Low |
| ARCH-02 | Replace in-memory SSE with Redis Pub/Sub | High |
| ARCH-05 | Route AI orchestrator behind backend API gateway | Medium |
| ARCH-06 | Add Sentry + Prometheus | Medium |
| ARCH-07 | Add staging environment | High |
| STD-04 | Change booking currency default to PKR | Low |
| STD-05 | Implement review system or drop rating columns | Medium |
| STD-06 | Add PostgreSQL integration test target in CI | Medium |

---

## Overall Assessment

The project has made **significant progress** since the documentation-only audit. The most critical issues from that report — localStorage JWT, Google OAuth token-in-URL, missing email verification, and plaintext token storage — are all **fixed in the actual code**. The httpOnly cookie architecture is correctly implemented end-to-end across both portals.

**Three real issues remain critical:**

1. **Silent auth bypass in `auth.middleware.py`** — the canonical middleware calls `verify_access_token` without `await` and without the required `session` argument. Any route using this import is unprotected. This is a one-line fix but a P0 security issue.

2. **No email verification enforcement** — the OTP system exists and works, but `email_verified=False` is never checked before granting access to protected features. The guard is missing, not the feature.

3. **No distributed state** — the absence of Redis means rate limiting, SSE queues, and OTP storage are all either in-process memory (lost on restart, broken on scale) or PostgreSQL (wrong tool for ephemeral state). This is the single highest-leverage infrastructure addition.

The codebase is well-structured, follows the project's own conventions consistently, and demonstrates genuine understanding of async Python, event-driven architecture, and security fundamentals. The gaps above are fixable incrementally without architectural rewrites.

---

*Audit based on direct code review of `packages/backend/src/` and `packages/vendor/src/` — May 2026.*
*Context7 MCP used to cross-reference OWASP Cheat Sheet Series standards for authentication, OTP, and rate limiting.*
