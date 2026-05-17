# Event-AI Constitution — Industry Standards Audit

**File:** `.specify/memory/constitution.md` (as reflected in `CLAUDE.md` + `AGENTS.md`)  
**Date:** May 2026  
**Verdict:** Solid foundation for a student/indie project — meaningful gaps before production-grade

---

## Scoring Overview

| Area | Score | Status |
|------|-------|--------|
| Authentication & Sessions | 6 / 10 | ⚠️ Needs work |
| Database & Data Access | 5 / 10 | ⚠️ Needs work |
| API Design | 5 / 10 | ⚠️ Needs work |
| Frontend Standards | 4 / 10 | ❌ Missing key requirements |
| Testing Strategy | 6 / 10 | ⚠️ Needs work |
| Security Posture | 5 / 10 | ⚠️ Needs work |
| Observability | 2 / 10 | ❌ Largely absent |
| CI/CD & Deployment | 3 / 10 | ❌ Largely absent |
| AI / Agent Layer | 7 / 10 | ✅ Genuinely strong |
| Architecture Patterns | 6 / 10 | ⚠️ Needs work |

---

## What the Constitution Gets Right ✅

These rules are current, correct, and would pass a 2026 production review:

- **httpOnly cookies for JWT** — matches OWASP Session Management Cheat Sheet
- **Async-first Python** (`asyncpg`, `AsyncSession`) — correct for I/O-heavy FastAPI services
- **Full type hints + Ruff** — current Python best practice
- **Structlog JSON logging** — structured logs are the industry baseline
- **Pydantic for all validation** — correct; never trust raw input
- **Alembic with reversible `downgrade()`** — non-negotiable for safe deployments
- **`selectinload` to prevent N+1** — correct; lazy loading in async SQLAlchemy is a footgun
- **Turborepo + pnpm workspaces** — modern monorepo standard
- **Conventional Commits** — enables automated changelogs and semantic versioning
- **React Query for data fetching** — correct; replaces manual `useEffect` fetch patterns
- **TypeScript strict mode, no `any`** — correct
- **pgvector with HNSW index** — correct for 2025/2026 semantic search
- **TDD mandatory** — correctly baked into the constitution
- **Zero real API calls in tests** — correctly enforced
- **`TriageAgent` as sole agent entry point** — correct agent architecture pattern
- **MCP tools read-only** — correct safety constraint
- **No wildcard CORS in production** — baseline security requirement
- **Rate limiting on all public endpoints** — correct

---

## Section-by-Section Analysis

---

### 1. Authentication & Sessions — 6/10

#### ✅ What is correct
- httpOnly cookies with `SameSite=Lax`
- Account lockout after 5 failed attempts
- Refresh token revocation on logout
- CSRF state JWT for Google OAuth

#### ❌ Missing: Refresh token re-use detection

The constitution mandates refresh token rotation but says nothing about **re-use detection**. Industry standard (used by Auth0, Okta, and described in OAuth 2.0 Security BCP RFC 9700) requires:

> If a refresh token is presented that was already rotated, treat it as a token theft signal — immediately revoke all tokens in that session family.

Without this, a stolen refresh token is usable indefinitely as long as the attacker rotates it before the legitimate user does.

**Add to constitution:**
```
If a refresh token is used that has already been rotated, revoke all 
refresh tokens for that user_id and force re-authentication.
```

#### ❌ HS256 — symmetric signing is outdated for multi-service architectures

The constitution mandates `JWT_ALGORITHM=HS256`. This is symmetric — every service that needs to *verify* tokens must also know the signing secret, making the secret high-value and widely distributed.

**Industry standard 2025/2026:** RS256 or ES256 (asymmetric). The AI orchestrator service needs to verify backend tokens. With HS256, it must share `JWT_SECRET_KEY`. With RS256, it only needs the public key.

**Add to constitution:**
```
Use RS256 (RSA) or ES256 (ECDSA) for JWT signing in multi-service deployments.
The private key signs (backend only). The public key verifies (all services).
HS256 is acceptable in single-service deployments only.
```

#### ⚠️ PKCE not mentioned for Google OAuth

The Google OAuth flow should use PKCE (Proof Key for Code Exchange, RFC 7636). The constitution uses a CSRF state JWT, which is correct but does not replace PKCE. PKCE protects against authorization code interception attacks.

#### ❌ No absolute session expiry or idle timeout policy

The constitution defines `ACCESS_TOKEN_EXPIRE_MINUTES=15` and `REFRESH_TOKEN_EXPIRE_DAYS=7`. But there is no **absolute maximum session lifetime** (e.g., force re-authentication after 30 days regardless of activity) and no **idle timeout** (e.g., revoke refresh token if not used in 48h). Both are standard in banking and marketplace applications.

---

### 2. Database & Data Access — 5/10

#### ✅ What is correct
- Alembic with reversible `downgrade()`
- `DIRECT_URL` for migrations, pooler URL for runtime
- `selectinload` for relational queries
- pgvector extension management

#### ❌ No `SELECT FOR UPDATE` / pessimistic locking rule

The constitution has no guidance on concurrent write safety. It describes the outbox pattern and async sessions but says nothing about when to use:

- `SELECT FOR UPDATE` for booking slot acquisition
- `SELECT FOR UPDATE SKIP LOCKED` for job queues
- Optimistic locking with version columns for conflict detection

This is why the double-booking race condition exists — the constitution never tells developers to think about it.

**Add to constitution:**
```
Any operation that reads state and then writes based on that state 
(check-then-act) MUST use SELECT FOR UPDATE within the same transaction,
or use a database-level unique constraint, or use optimistic locking 
(version column + UPDATE WHERE version = expected). 
Never use application-level locks for database consistency.
```

#### ❌ No indexing strategy beyond pgvector

The constitution mandates an HNSW index for `vendor_embeddings` but provides no guidance on indexing strategy for the rest of the schema. There are no rules for:

- Indexing foreign keys (standard practice — unindexed FKs cause full table scans on JOINs)
- Composite indexes for common filter/sort patterns
- Partial indexes for status-filtered queries (e.g., `WHERE status = 'ACTIVE'`)
- Index bloat monitoring

#### ❌ No cursor-based pagination requirement

The constitution says nothing about pagination strategy. All endpoints use offset/limit, which produces inconsistent results under concurrent writes. Industry standard for high-write tables (bookings, notifications) is **keyset pagination** (cursor-based).

**Add to constitution:**
```
Use cursor-based (keyset) pagination for all list endpoints on tables 
that receive concurrent writes. Use (created_at DESC, id DESC) as the 
default cursor. Offset pagination is only acceptable for admin-only 
endpoints with low write volume.
```

#### ⚠️ No data retention or GDPR rules

The `domain_events` table is explicitly documented as "append-only, never delete." For a Pakistani platform handling personal data (names, phone numbers, event locations), there should be retention limits and a right-to-erasure procedure. The AI service has `DELETE /api/v1/ai/memory/{user_id}` (GDPR right-to-forget) but there is no equivalent for booking history, domain events, or notification data.

---

### 3. API Design — 5/10

#### ✅ What is correct
- `/api/v1/` prefix on all routes
- Consistent response envelope `{"success", "data", "error", "meta"}`
- Namespaced error codes
- Domain-specific error codes (`NOT_FOUND_VENDOR`, etc.)

#### ❌ No idempotency key requirement

The constitution never mentions idempotency keys. For any endpoint that creates a resource and involves money (bookings, payments), network retries without idempotency produce duplicate records. This is a standard requirement at every fintech and marketplace company.

**Add to constitution:**
```
All POST endpoints that create financial records (bookings, payments, 
invoices) MUST accept an Idempotency-Key request header. Store the 
key + response hash. Return the cached response for duplicate keys 
within a 24-hour window.
```

#### ❌ No HTTP caching headers policy

The constitution says nothing about `Cache-Control`, `ETag`, or `Last-Modified` headers. Public vendor listings (`GET /public_vendors/`) and category listings (`GET /categories/`) are read-heavy, cacheable data. Without caching headers, every page load hits the database unnecessarily.

#### ❌ No API deprecation / sunset header requirement

The constitution has no rules for how to retire endpoints. Industry standard (RFC 8594): add `Deprecation` and `Sunset` headers to endpoints being phased out, with at least one version of overlap before removal.

#### ⚠️ PUT vs PATCH semantics not specified

The constitution uses both `PUT` (vendor profile update, notification preferences) and `PATCH` (booking status, vendor status). No guidance is given on the semantic difference. Industry standard: `PUT` = full replacement; `PATCH` = partial update. Using `PUT` for partial updates is incorrect.

---

### 4. Frontend Standards — 4/10

#### ✅ What is correct
- Next.js 15 App Router
- TypeScript strict, no `any`
- React Query for server state
- `await cookies()` in Next.js 15

#### ❌ No accessibility requirement (WCAG)

The constitution has zero mention of accessibility. WCAG 2.1 AA is the minimum legal requirement in most jurisdictions and a standard requirement in any professional frontend codebase. Missing: keyboard navigation, ARIA labels, colour contrast, focus management, screen reader compatibility.

For a platform targeting Pakistan, where mobile usage is dominant and accessibility support varies, this is a real gap.

**Add to constitution:**
```
All user-facing pages MUST meet WCAG 2.1 Level AA. This includes:
keyboard-navigable interactive elements, ARIA labels on icon-only buttons,
minimum 4.5:1 colour contrast ratio, and visible focus indicators.
Run axe-core or Lighthouse accessibility audit in CI.
```

#### ❌ No Core Web Vitals / performance budget

No mention of LCP, FID/INP, or CLS targets. No bundle size limits. No performance monitoring requirement. In 2025/2026 these are table stakes, especially given that `pnpm typecheck` is in CI but no performance check is.

#### ❌ No internationalisation (i18n) requirement

This is a Pakistan-focused marketplace. Urdu is the national language. The constitution mandates `country: default "Pakistan"` in the events model, but has no requirement for Urdu language support, RTL layout consideration, or localisation of dates and currencies.

#### ❌ No Content Security Policy (CSP) requirement

The constitution bans `localStorage JWT` (to prevent XSS token theft), but never mentions CSP headers, which are the primary defence against XSS. Without a CSP, the localStorage ban is less effective — an attacker can still exfiltrate cookie values via other XSS vectors if `HttpOnly` is misconfigured.

#### ⚠️ No error boundary standard

No `error.tsx`, `not-found.tsx`, or `global-error.tsx` requirement in the constitution. This is why the vendor portal has none (see ROUTE-01 in the vendor audit).

---

### 5. Testing Strategy — 6/10

#### ✅ What is correct
- TDD mandatory
- Zero real LLM/MCP calls in tests
- `respx` for HTTP mocking
- Property-based tests with Hypothesis and fast-check
- SQLite in-memory (fast, no external dependencies)

#### ❌ No coverage thresholds

"241 tests passing" says nothing about coverage. A project can have 241 tests covering 30% of the codebase. Industry standard: define minimum line/branch coverage thresholds (e.g., 80% line coverage, 70% branch coverage) enforced in CI.

**Add to constitution:**
```
pytest-cov must run in CI with minimum thresholds:
  line coverage: 80%
  branch coverage: 70%
Failing below threshold blocks merge.
```

#### ❌ No E2E testing requirement

The constitution mentions unit tests and integration tests but has no E2E test requirement. For a marketplace with multi-step flows (vendor registration → admin approval → customer booking → vendor confirmation), E2E tests catch failures that unit tests cannot.

**Add to constitution:**
```
Critical user journeys MUST have E2E test coverage using Playwright:
- Vendor registration and approval flow
- Customer booking flow (search → select → book → confirm)
- Google OAuth login flow
E2E tests run in CI on every PR targeting develop.
```

#### ⚠️ SQLite vs PostgreSQL test gap

SQLite in tests does not catch PostgreSQL-specific bugs: `JSONB` operators, `pgvector` cosine distance, `ON CONFLICT DO UPDATE`, `ARRAY` types, `RETURNING` clause edge cases, and `UUID` handling differences. The constitution acknowledges this with the JSONB patch in `conftest.py` but offers no broader guidance.

#### ❌ No contract testing

The vendor portal, user portal, admin portal, and AI orchestrator are all consumers of the backend API. The constitution has no requirement for contract tests (e.g., Pact) to verify that the backend's responses match what the frontends expect. A backend refactor can silently break all three portals.

---

### 6. Security Posture — 5/10

#### ✅ What is correct
- No hardcoded secrets
- Rate limiting on all public endpoints
- No wildcard CORS in production
- Never store raw payment data
- CSRF protection mentioned

#### ❌ No security headers policy

The constitution does not require any HTTP security headers. Industry standard (OWASP Secure Headers Project) requires at minimum:

| Header | Purpose |
|--------|---------|
| `Strict-Transport-Security` | Enforce HTTPS |
| `Content-Security-Policy` | XSS mitigation |
| `X-Content-Type-Options: nosniff` | MIME sniffing attacks |
| `X-Frame-Options: DENY` | Clickjacking |
| `Referrer-Policy: strict-origin` | Referrer leakage |
| `Permissions-Policy` | Browser API access |

None of these are mentioned.

#### ❌ No dependency vulnerability scanning

No mention of `pip-audit`, `safety`, Snyk, Dependabot, or any automated dependency scanning. A production system without automated CVE scanning will unknowingly run vulnerable libraries.

**Add to constitution:**
```
Dependency scanning is mandatory:
  Python: pip-audit or safety in CI on every PR
  Node: npm audit / pnpm audit in CI on every PR
  GitHub Dependabot: enabled for both ecosystems
Critical or high CVEs block merge.
```

#### ❌ No CSRF implementation detail

The constitution says "CSRF protection required" but does not specify the mechanism. `SameSite=Lax` cookies partially mitigate CSRF (cross-site navigations are blocked) but not for same-site subdomains or older browsers. A complete policy requires specifying:
- `SameSite=Strict` for all auth cookies
- Or a synchronizer token / double-submit cookie for state-changing requests

#### ❌ No audit logging requirement for sensitive operations

Vendor approvals, user role changes, admin actions, and booking status overrides should produce tamper-evident audit logs. The domain events table captures some of this, but the constitution does not mandate that audit trails are produced, immutable, or queryable.

#### ⚠️ No penetration testing or SAST requirement

No mention of static analysis security tools (Bandit for Python, ESLint security plugin for JS), DAST, or regular penetration testing. For a financial marketplace, at least annual pen testing is expected.

---

### 7. Observability — 2/10

This is the constitution's biggest gap relative to 2025/2026 industry standards.

#### ✅ What is correct
- Structlog JSON logging throughout
- DB health endpoint (`/health/db`)

#### ❌ No distributed tracing requirement

The platform has three separate services (backend, AI orchestrator, user/vendor/admin portals). A user request may touch the frontend, then the backend, then the AI orchestrator. Without distributed tracing (OpenTelemetry), debugging cross-service failures is essentially impossible.

**Add to constitution:**
```
All services MUST emit OpenTelemetry traces.
Use a correlation_id (trace ID) propagated across all service boundaries 
via the traceparent HTTP header (W3C Trace Context).
The correlation_id must appear in all structured log entries.
```

#### ❌ No metrics collection requirement

No Prometheus, no Datadog, no metrics at all. Minimum required metrics for a marketplace:

- Request rate, error rate, latency (p50/p95/p99) per endpoint
- Active DB connections, query latency
- Booking conversion rate (availability check → created → confirmed)
- AI agent latency and error rate per agent
- SSE connected users count

#### ❌ No error tracking

No Sentry, no Rollbar, no equivalent. Unhandled exceptions in production are invisible. `Structlog` writes to stdout/logs, but without an error tracking service, nobody receives alerts when a new exception class appears.

**Add to constitution:**
```
Sentry (or equivalent) MUST be integrated in backend and all frontends.
SENTRY_DSN is a required env var in production.
All unhandled exceptions are captured with full context.
```

#### ❌ No SLO/SLA definition

No latency targets, availability targets, or error budget policies are defined. Industry standard for a marketplace: define at least one SLO (e.g., "p95 booking creation latency < 500ms") so you know when the system is degraded.

#### ⚠️ Single health endpoint

`/health/db` is a good start, but production systems need:
- `/health/live` — liveness probe (is the process running?)
- `/health/ready` — readiness probe (is the service ready to accept traffic — DB connected, external deps reachable?)

The distinction matters for Kubernetes/container orchestration restarts.

---

### 8. CI/CD & Deployment — 3/10

#### ✅ What is correct
- GitHub Actions CI/CD
- lint + typecheck + pytest must pass before merge
- Conventional Commits (enables semantic versioning)

#### ❌ No staging environment requirement

The constitution defines `dev` and `Docker` environments but no staging/pre-production environment. Production deployments without staging are high-risk — there is no environment to verify migrations, dependency upgrades, or config changes before they affect real users.

#### ❌ No database migration strategy in CD

How do migrations run in deployment? Before the new code starts? After? On the running instance? Without a defined strategy:
- Running migrations before deployment can cause old code to fail on new schema
- Running migrations after deployment can cause new code to fail on old schema

The safe pattern (expand/contract or blue-green) is not documented.

**Add to constitution:**
```
Database migrations follow the expand-contract pattern:
1. Expand: Add new columns/tables as nullable. Deploy.
2. Migrate data. Deploy code using new columns.
3. Contract: Remove old columns in a follow-up migration.
Never add a NOT NULL column without a default in a single deployment.
```

#### ❌ No container image scanning

Docker images are built in the repo (`docker-compose.yml`, `.dockerignore`). No mention of scanning images for vulnerabilities (Trivy, Docker Scout, Snyk Container).

#### ❌ No rollback procedure

The constitution documents `alembic downgrade -1` for migrations, but there is no rollback procedure for application deployments. What happens when a deployment fails in production?

#### ❌ No secrets management beyond `.env`

The constitution says "never commit `.env`" and "keep `.env.example` updated." But for production, `.env` files are not an acceptable secrets management strategy. Industry standard: a secrets manager (AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager, or at minimum GitHub Actions secrets for CI).

---

### 9. AI / Agent Layer — 7/10

This is the constitution's strongest area, reflecting genuine 2025/2026 AI engineering maturity.

#### ✅ What is correct
- TriageAgent as sole entry point (prevents prompt injection surface sprawl)
- 7-layer injection firewall (blocklist → regex → heuristics → canary → SDK guardrails)
- Canary token injection + MINJA protection
- PII redaction on output
- Per-user rate limiting (30 req/min)
- `max_handoff_depth=5` to prevent infinite loops
- MCP tools read-only
- No direct AI DB writes
- Mem0 for persistent memory
- OpenAI tracing disabled (correct for Gemini via OpenAI-compatible endpoint)

#### ❌ No AI cost monitoring or budget limits

The constitution specifies a Gemini model and API key but has no requirement for:
- Per-user or per-month token budget caps
- Cost alerting when spend exceeds a threshold
- Model fallback if the primary model is unavailable or over budget

Uncontrolled AI API costs are a common production failure mode.

**Add to constitution:**
```
AI API calls MUST log input_tokens and output_tokens per request to usage_events.
A hard per-user daily token budget MUST be enforced (configurable via env var).
Implement a fallback model (e.g., gemini-flash → gemini-nano) for when the 
primary model returns 429 or 5xx.
```

#### ❌ No model version pinning strategy

`GEMINI_MODEL=gemini/gemini-3-flash-preview` uses a preview model. The constitution has no strategy for:
- When to migrate to a stable model version
- How to test a model upgrade before deploying to production
- What to do when a model is deprecated

#### ⚠️ No AI response caching

Common AI queries (e.g., "list vendors for weddings in Karachi") will produce near-identical responses for different users. No caching layer is mentioned, causing unnecessary Gemini API calls and cost.

---

### 10. Architecture Patterns — 6/10

#### ✅ What is correct
- Event-driven architecture with `domain_events` table
- Outbox pattern (event + data in same transaction)
- Dependency injection via `Depends()`
- Singleton services (appropriate for stateless FastAPI)
- `event_bus` for decoupled side effects

#### ❌ No outbox polling requirement

The constitution describes the outbox pattern (write event to DB in same transaction) but does not mandate the second half: **a poller that re-processes undelivered events after a crash**. Without this, in-process listeners are the only delivery mechanism — a process restart silently drops all in-flight events.

**Add to constitution:**
```
The outbox pattern requires two components:
1. Transactional write: event persisted to domain_events in same DB transaction as the business change.
2. Outbox poller: a background worker that picks up domain_events WHERE processed_at IS NULL 
   and fires them, then marks them processed. This ensures at-least-once delivery.
The poller must run even if in-process listeners already fired.
```

#### ❌ No circuit breaker pattern for external APIs

The platform calls Gemini (embeddings + chat), Mem0 (memory), and Google OAuth on every authenticated request and every booking. The constitution has no circuit breaker, retry, or timeout policy for these external dependencies.

Industry standard: wrap all external API calls in a circuit breaker (exponential backoff with jitter, max retries, open/half-open/closed states). Libraries: `tenacity` for Python, `axios-retry` for Node.

#### ❌ No feature flag system

Zero mention of feature flags. For a production marketplace, shipping unfinished features to production behind a flag is standard practice. Without flags, every in-progress feature must be on a long-lived branch, increasing merge conflicts.

#### ⚠️ Singleton services with mutable state are not safe without locks

The constitution mandates singleton services (`my_service = MyService()` at module level). This is fine for stateless services, but services like `SSEConnectionManager` hold per-user mutable queues. The constitution says nothing about protecting shared mutable state in an async context.

---

## Summary of Required Constitution Additions

These are the highest-priority additions to bring the constitution to industry standard:

### P0 — Add immediately (production blockers)

1. **Refresh token re-use detection** — revoke entire session family on re-use
2. **`SELECT FOR UPDATE` / locking rule** — mandate for all check-then-act DB operations
3. **Idempotency key requirement** — all financial write endpoints
4. **Outbox poller requirement** — second half of outbox pattern
5. **Dependency vulnerability scanning** — `pip-audit` + `pnpm audit` in CI
6. **Security headers policy** — HSTS, CSP, X-Frame-Options, etc.
7. **Error tracking** — Sentry or equivalent, required in production

### P1 — Add before scaling

8. **Cursor-based pagination rule** — for all high-write tables
9. **Coverage thresholds** — minimum 80% line, 70% branch in CI
10. **E2E testing requirement** — Playwright for critical user journeys
11. **RS256/ES256 JWT** — for multi-service token verification
12. **OpenTelemetry distributed tracing** — across all services
13. **Liveness vs readiness health probes** — `/health/live` + `/health/ready`
14. **Staging environment requirement** — mandatory before production deployments
15. **Database migration CD strategy** — expand-contract pattern documented

### P2 — Add for production polish

16. **AI cost monitoring and budget caps** — per-user token budgets
17. **WCAG 2.1 AA requirement** — accessibility minimum
18. **Circuit breaker pattern** — for Gemini, Mem0, Google OAuth
19. **Absolute session expiry + idle timeout** — force re-auth after N days
20. **i18n/Urdu language requirement** — appropriate for Pakistan-focused platform
21. **API deprecation/sunset header policy** — before removing any endpoint
22. **SLO definitions** — latency + availability targets

---

## Overall Verdict

The constitution is **well above average for a solo or student project** and reflects genuine knowledge of modern backend patterns (async-first, outbox, event-driven, pgvector, agent security). The AI security section in particular is ahead of most production systems.

However, it falls short of **production-grade** in three categories that matter most:

**Observability is almost absent.** No tracing, no metrics, no error tracking, no SLOs. A production incident in this codebase would be very difficult to diagnose.

**Security is incomplete.** The right intentions are there (httpOnly cookies, rate limiting, CSRF mention) but the specifics are missing: no security headers, no CVE scanning, no CSRF mechanism detail, no audit logging requirement.

**Operational readiness is not covered.** No staging environment, no migration CD strategy, no rollback procedure, no secrets management beyond `.env` files.

The constitution reads like it was written by someone who knows backend engineering well but has not yet operated a production system under failure conditions. The fixes are well-defined — they are additive rules, not rewrites.
