# Event-AI — Vendor Issues Audit Report

**Repository:** AlyOmer/Event-AI  
**Scope:** `packages/frontend`, `packages/backend`, `packages/user`, `packages/admin`  
**Date:** May 2026  
**Sources:** `CLAUDE.md` · `PROJECT_STATUS.md` · `README.md` · `vendor_portal_task_review.md`

---

## Summary

| Severity | Count |
|----------|-------|
| 🔴 CRITICAL | 2 |
| 🟠 HIGH | 7 |
| 🟡 MEDIUM | 8 |
| 🔵 LOW | 2 |
| **Total** | **19** |

---

## 1. Login & Authentication

### [AUTH-01] 🔴 CRITICAL — JWT stored in `localStorage`, violates own constitution

**File:** `packages/frontend/src/lib/api.ts` (axios interceptor)

`CLAUDE.md §17` explicitly warns:
> "The current `api.ts` stores the JWT in `localStorage` (`userToken` key). This predates the architecture decision to use httpOnly cookies."

The constitution lists `localStorage JWT` as a **BANNED** practice. Yet the vendor portal's axios request interceptor reads `userToken` from `localStorage` today.

**Impact:**
- Tokens are accessible to any JavaScript on the page — full XSS attack surface
- Tokens persist indefinitely across tab/browser closes
- Directly contradicts the stated security architecture

**Fix:** Replace the localStorage interceptor with cookie-based auth. Update axios to use `withCredentials: true`. Coordinate with backend to issue tokens via `Set-Cookie` (httpOnly, Secure, SameSite=Lax) on login.

---

### [AUTH-02] 🔴 CRITICAL — Google OAuth passes JWT as `?token=` URL query parameter

**File:** `packages/frontend/src/app/auth/google/callback/page.tsx`

`PROJECT_STATUS.md` confirms: *"Google OAuth callback page — reads `?token=` from redirect."*

Passing access tokens in URL query strings is a known OWASP vulnerability (CWE-598). The token is exposed in:
- Browser history
- Server access logs
- `Referer` headers sent to any third-party scripts on the page
- Clipboard if the user copies the URL

The backend correctly uses a CSRF state JWT for OAuth initiation, but defeats that by putting the resulting access token in the URL.

**Fix:** After the Google OAuth callback, issue the token via `Set-Cookie` (httpOnly) and redirect to the dashboard with no token in the URL.

---

### [AUTH-03] 🟠 HIGH — Token refresh thundering herd causes valid users to be logged out

**File:** `packages/frontend/src/store/authStore.ts`

The auth store has a *"token refresh interceptor: catches 401, retries original request, redirects to `/login` on failure."*

If multiple concurrent API calls (e.g., dashboard loads stats + bookings + services simultaneously) all receive 401 at the same time:
1. All three interceptors fire a refresh simultaneously
2. The first refresh rotates the refresh token — backend revokes the old one
3. Requests 2 and 3 attempt to refresh with the already-invalidated token
4. Both fail → all three redirect to `/login`
5. User is forcefully logged out despite having a valid session

**Fix:** Implement a refresh mutex — a single pending Promise that all concurrent refresh callers wait on. Only the first caller executes the actual refresh; the others await its result before retrying.

---

### [AUTH-04] 🟡 MEDIUM — Two login endpoints for the same action (anti-pattern)

**File:** `packages/backend/src/api/auth/routes.py` + `src/api/users/routes.py`

Two separate endpoints serve login:
- `POST /api/v1/auth/login` — OAuth2 form-encoded (for Swagger)
- `POST /api/v1/users/login` — JSON body (for frontend portals)

This creates a split maintenance surface where a bug fix or security patch must be applied to both endpoints. Token TTLs, account lockout logic, and audit logging may also diverge between them over time.

**Fix:** One login endpoint with Content-Type negotiation, or a single JSON endpoint with a Swagger schema override. The Swagger UI form encoding requirement does not justify a second production endpoint.

---

### [AUTH-05] 🟠 HIGH — Route guard checks authentication but not vendor role or account status

**File:** `packages/frontend/src/middleware.ts` or route guard HOC

`PROJECT_STATUS.md`: *"Route guards — unauthenticated → `/login`, authenticated vendor → `/dashboard`"*

The guard only checks `isAuthenticated`. It does not verify:
- That the logged-in user has `role === 'vendor'` — a regular user account can access the vendor portal
- That the vendor's status is `ACTIVE` — a `PENDING` or `SUSPENDED` vendor sees the full dashboard
- That a vendor profile actually exists for the user (registered but never completed onboarding)

A `SUSPENDED` vendor can view all booking data and trigger mutations until the backend returns 403, causing confusing error states in the UI.

**Fix:** Guard must check `role === 'vendor'` AND `vendor.status === 'ACTIVE'`. `PENDING` vendors → "awaiting approval" screen. `SUSPENDED` vendors → suspension notice with contact info.

---

## 2. Race Conditions

### [RACE-01] 🟠 HIGH — Double-booking window: availability check and lock are not atomic

**File:** `packages/backend/src/services/booking_service.py`

The booking flow is described as *"Acquire-lock → create-booking → confirm-lock pattern (30s TTL)."*

The race window:
1. User A calls `GET /bookings/availability` — sees slot as free
2. User B calls `GET /bookings/availability` — also sees slot as free (A hasn't locked yet)
3. Both simultaneously call `POST /bookings/` — both `acquire-lock` calls race at the DB

If lock acquisition is a SELECT + INSERT (check-then-act) without `SELECT FOR UPDATE` or a DB-level unique constraint on `(vendor_id, service_id, event_date)`, two bookings can be created for the same slot. The 30s TTL only protects after a lock is acquired; it does not protect acquisition itself.

**Fix:** Use `SELECT FOR UPDATE SKIP LOCKED` on the availability slot row during lock acquisition. Add a partial unique index: `UNIQUE (vendor_id, service_id, event_date) WHERE status NOT IN ('cancelled', 'rejected')`.

---

### [RACE-02] 🟡 MEDIUM — Vendor approval fires duplicate embedding tasks on double-click

**File:** `packages/backend/src/services/vendor_service.py` + `embedding_service.py`

`PATCH /api/v1/admin/vendors/{id}/status` → approve → emits `vendor.approved` → `EmbeddingService.handle_vendor_approved()` fires.

If an admin double-clicks "Approve" or two admin sessions approve simultaneously:
- Two `vendor.approved` events are emitted
- Two background embedding tasks are dispatched to Gemini
- The SHA-256 staleness check has a TOCTOU race — if both tasks read the hash before either writes, both proceed to call Gemini

The status transition itself (PENDING → ACTIVE) is also unprotected — two concurrent PATCH requests can both read `status=PENDING` and both transition to `ACTIVE`.

**Fix:** Use `SELECT FOR UPDATE` on the vendor row during the status transition. Make the embedding upsert use `INSERT ... ON CONFLICT DO UPDATE` (atomic upsert) rather than check-then-insert.

---

### [RACE-03] 🟡 MEDIUM — SSE queue evict-oldest is not atomic under concurrent pushes

**File:** `packages/backend/src/services/sse_manager.py`

The SSE manager uses a per-user async queue (max 50 items) with an evict-oldest strategy. In Python asyncio, the check-and-swap is not atomic at the application level:

```python
if queue.full():
    queue.get_nowait()   # evict oldest
queue.put_nowait(item)   # insert new
```

Between `full()` and `get_nowait()`, another coroutine can also see `full()=True` and also evict — causing two evictions for one insertion. Under a booking event that triggers multiple notifications in parallel, the queue can silently lose more messages than expected.

**Fix:** Wrap the check-and-swap in an `asyncio.Lock` per user queue, or use a custom bounded deque with atomic replace semantics.

---

### [RACE-04] 🟡 MEDIUM — 60s cleanup task can expire a lock while a user is completing their booking

**File:** `packages/backend/src/services/booking_service.py` (background cleanup task)

The background task deletes or expires booking locks older than 30s every 60 seconds. This creates a window where:
1. User acquires lock at T=0
2. Background task runs at T=35s — lock is >30s old → marked expired and slot released
3. Second user acquires the same slot at T=36s
4. Original user submits booking at T=40s — their lock appears valid client-side but is already expired
5. Two confirmed bookings exist for the same slot

**Fix:** Lock expiry should be enforced via DB-level timestamp comparison (`expires_at < NOW()`). When creating the booking, re-validate within the same DB transaction that the lock still belongs to the requesting user and has not expired. Never rely on background job timing for transactional integrity.

---

## 3. Inconsistencies

### [INC-01] 🟠 HIGH — Backend port is `3001` in `CLAUDE.md` but `5000` everywhere else

**File:** `CLAUDE.md §7`, `README.md`, `PROJECT_STATUS.md` — port map sections

| Document | Backend Port |
|----------|-------------|
| `CLAUDE.md §7` Port Map | `3001` |
| `CLAUDE.md §7` env vars (`BACKEND_API_URL`) | `http://localhost:3001/api/v1` |
| `README.md` Port Map | `5000` |
| `PROJECT_STATUS.md` Port Map | `5000` |
| `PROJECT_STATUS.md` env vars | `http://localhost:5000/api/v1` |

Critically, in Docker the vendor portal maps to port `3001` — meaning `CLAUDE.md`'s backend port (`3001`) would **collide** with the Docker vendor portal. A new developer following `CLAUDE.md` would configure entirely the wrong backend URL and face silent connection failures.

**Fix:** Standardize on port `5000` for the backend across all documentation. Update `CLAUDE.md §7` and all curl command examples.

---

### [INC-02] 🟡 MEDIUM — Vendor portal package is `packages/frontend/` in the file tree but `packages/vendor/` in docs

**File:** Directory vs. documentation references

The actual repo directory is `packages/frontend/`. `CLAUDE.md §3` uses `packages/frontend/` in the directory tree, but then the Core Product Areas table calls it `packages/vendor/`. `PROJECT_STATUS.md` consistently uses `packages/vendor/`.

This makes it unclear which package to edit for vendor-specific work and risks a new developer modifying the wrong package.

**Fix:** Either rename the directory to `packages/vendor/` (update `turbo.json` + `pnpm-workspace.yaml`) or update all documentation to consistently say `packages/frontend/` with a clear note that it is the vendor portal.

---

### [INC-03] 🟡 MEDIUM — CORS env var is `CORS_ORIGIN` in `CLAUDE.md` but `CORS_ORIGINS` in README and PROJECT_STATUS

**File:** `CLAUDE.md §7` vs `README.md` vs `PROJECT_STATUS.md`

`CLAUDE.md §7` lists the variable as `CORS_ORIGIN` (singular). Both `README.md` and `PROJECT_STATUS.md` list it as `CORS_ORIGINS` (plural). If a developer follows `CLAUDE.md` and sets `CORS_ORIGIN`, the backend `Settings` class (which reads `CORS_ORIGINS`) will silently ignore it — resulting in CORS failures on all cross-origin requests.

**Fix:** Check the actual field name in `packages/backend/src/core/config.py` and update all documentation to match exactly.

---

### [INC-04] 🟡 MEDIUM — Booking `currency` defaults to `"USD"` on a Pakistan-focused platform

**File:** `packages/backend/src/models/booking.py`

The `bookings` table defines `currency | str | default "USD"`. The platform is explicitly built for Pakistan — weddings, mehndi, baraat, walima. Every booking record defaults to an incorrect currency unless explicitly overridden. Financial reporting in admin stats will display revenue in USD, which is meaningless for local operations.

**Fix:** Change the default to `"PKR"`. Add a currency allowlist to the booking creation schema. Update the admin stats revenue calculation to handle currency correctly.

---

### [INC-05] 🟡 MEDIUM — `rating` and `total_reviews` columns exist but no rating system is implemented

**File:** `packages/backend/src/models/vendor.py`

The `vendors` table has `rating: float = 0.0` and `total_reviews: int = 0`, but there is no review submission endpoint, no review model or table, and no rating aggregation service in any completed module.

These columns sit unused. The public vendor listing returns `rating=0.0` for all vendors, which is actively misleading to users browsing the marketplace.

**Fix:** Either implement the full review system (review model, `POST /bookings/{id}/review`, rating aggregation trigger), or remove the columns now and add them in a future migration when the feature is actually built.

---

### [INC-06] 🟠 HIGH — User portal session also uses `localStorage` — second violation of the same constitution rule

**File:** `packages/user/src/lib/api.ts` or equivalent auth store

`PROJECT_STATUS.md` under User Portal: *"Session persistence via `localStorage`."*

This is the same `localStorage JWT` violation as AUTH-01, present in a second portal. Two portals independently violating the same constitution rule suggests the httpOnly cookie architecture was decided after both portals were partially built, and the migration was never completed in either.

**Fix:** Both the user portal and vendor portal need coordinated migration of JWT storage from `localStorage` to httpOnly cookies. This requires backend changes to `Set-Cookie` on login/logout and frontend changes to remove all localStorage token reads/writes.

---

## 4. Frontend Route Issues

### [ROUTE-01] 🟡 MEDIUM — No `not-found.tsx` or `error.tsx` pages in any portal

**File:** `packages/frontend/src/app/not-found.tsx` (missing)

The vendor portal implementation lists all functional pages but no `not-found.tsx` or `error.tsx` are mentioned anywhere. In Next.js 15 App Router:
- Without `not-found.tsx`, any undefined route renders the default Next.js 404 page — breaks design system and exposes framework version
- Without `error.tsx`, any unhandled Server Component runtime error shows the default Next.js error screen — may expose stack traces in misconfigured environments

**Fix:** Add `app/not-found.tsx`, `app/error.tsx`, and `app/global-error.tsx` to all three portals (vendor, user, admin).

---

### [ROUTE-02] 🟠 HIGH — Post-OAuth redirect URL is hardcoded, breaks if vendor portal port changes

**File:** `packages/backend/src/api/auth/routes.py` (OAuth callback redirect)

After Google OAuth callback, the backend redirects to the vendor portal with `?token=` in the URL. This redirect URL is hardcoded in the backend. If the vendor portal changes ports (e.g., Docker vs. dev), or if a second portal (user portal) also adds Google OAuth, the hardcoded redirect breaks.

Additionally, the `GOOGLE_REDIRECT_URI` must match exactly character-for-character what is registered in Google Cloud Console. There is only one registered redirect URI, meaning both portals cannot independently use Google OAuth without adding a second registered URI and adding routing logic.

**Fix:** Pass a `redirect_to` parameter encoded in the OAuth state JWT so the backend knows which portal to redirect to after login. Make the post-OAuth destination configurable rather than hardcoded.

---

### [ROUTE-03] 🟠 HIGH — Admin portal has no documented authentication or role route guard

**File:** `packages/admin/src/middleware.ts` (missing or incomplete)

The admin portal pages (dashboard, vendors, users, settings) are all described in `PROJECT_STATUS.md`, but unlike the vendor portal, there is no mention of route guards, auth middleware, or role verification (`role === 'admin'` check).

If the admin portal only has client-side route protection (which can be bypassed by navigating directly to the URL), an authenticated non-admin user could access admin pages. The backend correctly enforces role on `/admin/*` endpoints, but the UI would still render and display failed API error states rather than a proper access-denied screen.

**Fix:** Add `middleware.ts` to the admin portal that reads the auth cookie, verifies `role === 'admin'`, and redirects unauthenticated users to `/login` and authenticated non-admin users to a 403 page.

---

### [ROUTE-04] 🟠 HIGH — Next.js AI service proxy may forward requests without validating user session

**File:** `packages/user/src/app/api/ai/[...path]/route.ts`

The user portal has a Next.js API proxy at `/api/ai/[...path]/route.ts` that forwards requests to the AI orchestrator at port 8000. If the proxy attaches the `AI_SERVICE_API_KEY` unconditionally (without first validating the user's JWT):
- Any unauthenticated request with knowledge of the proxy URL can reach the AI service
- The proxy becomes an open relay, exposing the service-to-service API key's privileges
- The AI orchestrator's per-user rate limiting (30 req/min) falls back to IP-based limiting, which is easily circumvented

**Fix:** The proxy `route.ts` must validate the user's JWT first before forwarding. Attach `AI_SERVICE_API_KEY` + a verified `user_id` header server-side only. Never expose `AI_SERVICE_API_KEY` to the browser.

---

## 5. Industry Standards Not Followed

### [STD-01] 🟠 HIGH — No idempotency keys on booking creation — network retries create duplicate bookings

**File:** `packages/backend/src/api/bookings/routes.py`

`POST /api/v1/bookings/` has no idempotency key mechanism. In a marketplace with mobile users on flaky connections, a booking POST can fail mid-flight (connection dropped after the server received it but before the client got a response). The user retries and creates a duplicate booking, potentially double-charging.

**Fix:** Accept an `Idempotency-Key` header on all booking/payment write endpoints. Store the key + response in a short-lived cache (Redis or a DB table with TTL). If the same key is seen within 24h, return the cached response instead of processing again. This is standard practice at Stripe, Airbnb, and all financial platforms.

---

### [STD-02] 🟡 MEDIUM — Offset-based pagination gives inconsistent results under concurrent writes

**File:** `packages/backend/src/api/bookings/routes.py`, `notifications/routes.py`, etc.

All paginated endpoints use offset/limit pagination. Under concurrent writes:
- A new record inserted between page 1 and page 2 requests causes record 20 to appear on both pages
- A deleted record causes record 21 to be skipped entirely
- For a live marketplace with real-time bookings and notifications, users see duplicate or missing items

**Fix:** Use cursor-based (keyset) pagination with `(created_at, id)` as the cursor. This gives stable, consistent pages regardless of concurrent inserts or deletes.

---

### [STD-03] 🔵 LOW — Soft delete via `DELETE /vendors/profile/me` and admin suspend are two paths to the same state

**File:** `packages/backend/src/api/vendors/routes.py`

Two flows both set `status=SUSPENDED`:
1. `DELETE /api/v1/vendors/profile/me` — vendor self-deactivates
2. `PATCH /api/v1/admin/vendors/{id}/status` — admin suspends

These likely emit different domain events, trigger different notifications, and have different audit trail entries. `DELETE` semantically implies removal, not suspension — this violates the principle of least surprise.

**Fix:** Rename or replace the self-delete endpoint with `PATCH /vendors/profile/me/deactivate`. Ensure both paths emit consistent domain events and have identical side effects.

---

### [STD-04] 🔵 LOW — No API deprecation or versioning strategy beyond `/api/v1/`

**File:** `packages/backend/src/main.py` (router registration)

The codebase uses `/api/v1/` but there is no documented strategy for introducing breaking changes, when `/api/v2/` will be introduced, or how sunset periods will be communicated. All four consumers (vendor portal, user portal, admin portal, AI orchestrator) share one backend — an uncoordinated breaking change breaks all of them simultaneously.

**Fix:** Document a versioning policy. Add `Deprecation` and `Sunset` HTTP response headers (RFC 8594) when deprecating endpoints. Provide at least one version of overlap before removing any endpoint.

---

### [STD-05] 🟡 MEDIUM — Outbox pattern writes events but has no background poller — side effects silently drop on restart

**File:** `packages/backend/src/services/event_bus_service.py`

The outbox pattern is described as: events are persisted to `domain_events` within the same DB transaction, then in-process listeners fire (SSE push, notification creation). If the process crashes or restarts between the DB commit and the listener execution, the event is durably persisted in `domain_events` but the side effects (SSE push, user notification) never fire and are silently lost.

True outbox delivery requires a background worker that polls `domain_events` for unprocessed entries and re-fires them, ensuring at-least-once delivery.

**Fix:** Add a `processed_at` column to `domain_events`. Add a background poller or Postgres `LISTEN/NOTIFY` trigger that picks up events where `processed_at IS NULL` and fires them. This guarantees delivery across process restarts.

---

## Quick Reference by File

| File | Issues |
|------|--------|
| `packages/frontend/src/lib/api.ts` | AUTH-01, AUTH-03 |
| `packages/frontend/src/app/auth/google/callback/page.tsx` | AUTH-02 |
| `packages/frontend/src/middleware.ts` | AUTH-05 |
| `packages/frontend/src/app/` | ROUTE-01 |
| `packages/user/src/app/api/ai/[...path]/route.ts` | ROUTE-04 |
| `packages/user/src/lib/api.ts` | INC-06 |
| `packages/admin/src/middleware.ts` | ROUTE-03 |
| `packages/backend/src/api/auth/routes.py` | AUTH-04, ROUTE-02 |
| `packages/backend/src/api/bookings/routes.py` | RACE-01, RACE-04, STD-01, STD-02 |
| `packages/backend/src/api/vendors/routes.py` | STD-03 |
| `packages/backend/src/services/booking_service.py` | RACE-01, RACE-04 |
| `packages/backend/src/services/vendor_service.py` | RACE-02 |
| `packages/backend/src/services/embedding_service.py` | RACE-02 |
| `packages/backend/src/services/sse_manager.py` | RACE-03 |
| `packages/backend/src/services/event_bus_service.py` | STD-05 |
| `packages/backend/src/models/booking.py` | INC-04 |
| `packages/backend/src/models/vendor.py` | INC-05 |
| `packages/backend/src/main.py` | STD-04 |
| `CLAUDE.md`, `README.md`, `PROJECT_STATUS.md` | INC-01, INC-02, INC-03 |
