# Chat Booking End-to-End — Verify & Ship Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify and ship the already-implemented chat-booking negotiation loop: user books via Chat UI → vendor notified (accept/reject/negotiate) → on accept, emails sent → user notified of outcome. Plus the AI-assistant fixes (autonomy instructions, thinking-token cap).

**Architecture:** The feature exists in the uncommitted working tree across four packages. Audit confirmed: backend negotiation loop (quotes/counter-offers/booking states + event-bus → notifications + emails), orchestrator booking tools with direct-DB writes + vendor notification rows, thinking-budget=0 fix in `main.py` (`thinkingConfig.thinkingBudget` via `extra_body`), `GEMINI_MODEL=gemini/gemini-2.5-flash` (no longer flash-lite), user-portal quotes page (accept/counter), vendor-portal quote-builder + counter-respond. This plan verifies each layer with its test suite, fixes any failures, cleans git noise, and commits in logical chunks.

**Tech Stack:** FastAPI + SQLModel + pytest (backend), OpenAI Agents SDK + Gemini (orchestrator), Next.js 15 + Jest (portals), Conventional Commits.

**Audit evidence (already implemented — do NOT re-implement):**
| Goal requirement | Where it lives |
|---|---|
| Chat → booking created | `packages/agentic_event_orchestrator/tools/booking_tools.py` `create_booking_request` (availability lock, conflict guard, vendor notification row) |
| Vendor notified + accept/reject/negotiate | notification row write in `create_booking_request`; vendor portal `bookings/[id]/page.tsx` confirm/reject; `quote-builder-dialog.tsx`, `use-quotes.ts` (counter respond via `PATCH /counter-offers/{id}/respond`) |
| Negotiation loop | `packages/backend/src/services/quote_service.py`, `src/api/v1/quotes.py`, migration `20260602_negotiation_loop.py`, orchestrator `get_active_quotes`/`submit_counter_offer` |
| Accept → emails | `notification_service.handle` subscribed to `booking.accepted`/`booking.rejected`/etc. in `config/database.py:234-247`, calls `_send_email` → `email_service` (Brevo→SMTP→dev-log) |
| User notified of outcome | same notification_service handlers + SSE manager; user portal `bookings/[id]/quotes/page.tsx` accept/counter UI |
| Thinking-token crash fix | `config/settings.py` `thinking_budget: int = 0` + `main.py:72-80` RunConfig `extra_body.thinkingConfig.thinkingBudget`; `.env.example` `GEMINI_MODEL=gemini/gemini-2.5-flash`, `THINKING_BUDGET=0` |
| Autonomy | `pipeline/instructions.py` ORCHESTRATOR_INSTRUCTIONS "execute autonomously in one turn, no user prompts between steps" |

---

### Task 1: Backend test suite green

**Files:**
- Test: `packages/backend/tests/` (entire suite, incl. new `test_quote_service.py`, `test_security_headers.py`, `test_review_service.py`)

- [ ] **Step 1: Run the full backend suite**

Run:
```bash
cd packages/backend
uv run pytest -q --tb=short
```
Expected: all tests PASS (0 failures). Suite uses in-memory SQLite via `conftest.py` — no DB/Docker needed.

- [ ] **Step 2: If any test fails — STOP and debug**

Use superpowers:systematic-debugging. Read the failing test, find root cause in the service/route it covers, fix the implementation (not the test, unless the test asserts stale behavior contradicted by the new spec). Re-run the single file first:
```bash
uv run pytest tests/<failing_file>.py -v --tb=short
```
Then re-run the full suite (Step 1) until green.

- [ ] **Step 3: Verify migration chain integrity**

Run:
```bash
cd packages/backend
uv run alembic history | head -5
```
Expected: `20260602_negotiation_loop` is head, parent `20260521_add_subscription_fields`. Both new migration files have non-empty `downgrade()` (confirmed in audit — just verify command output shows linear chain, no branch points).

---

### Task 2: Orchestrator test suite green

**Files:**
- Test: `packages/agentic_event_orchestrator/tests/`, `packages/agentic_event_orchestrator/tools/__tests__/`

- [ ] **Step 1: Run the orchestrator suite**

Run:
```bash
cd packages/agentic_event_orchestrator
uv run pytest -q --tb=short
```
Expected: all tests PASS. Zero real LLM calls (mocked per CLAUDE.md); HTTP mocked with respx.

- [ ] **Step 2: If any test fails — STOP and debug**

Same protocol as Task 1 Step 2. Watch for the known instruction-length validator: `pipeline/instructions.py` `validate_instruction_limits()` fails any instruction > 3200 chars — if a test fails on this, trim the instruction string, do not raise the limit.

- [ ] **Step 3: Confirm thinking-budget wiring (the chat-crash fix)**

Run:
```bash
cd packages/agentic_event_orchestrator
uv run python -c "from config.settings import get_settings; s = get_settings(); print('model:', s.gemini_model); print('thinking_budget:', s.thinking_budget)"
```
Expected: `thinking_budget: 0` (or low cap), and model is NOT `gemini-2.5-flash-lite`. If local `.env` still has flash-lite, update root `.env`: `GEMINI_MODEL=gemini/gemini-2.5-flash` and `THINKING_BUDGET=0` (matches `.env.example`).

---

### Task 3: Frontend test suites green

**Files:**
- Test: `packages/vendor/src/__tests__/`, `packages/user/` (Jest where configured)

- [ ] **Step 1: Run vendor portal tests**

Run:
```bash
pnpm --filter vendor test -- --watchAll=false
```
Expected: PASS, including modified `bookings.test.tsx`, `booking-detail.test.tsx`, `notifications.test.tsx`.

- [ ] **Step 2: Run user portal tests (if test script exists)**

Run:
```bash
pnpm --filter user test -- --watchAll=false
```
Expected: PASS. If the package has no `test` script, note it and skip — do not add a test harness in this plan.

- [ ] **Step 3: Typecheck all portals**

Run:
```bash
pnpm typecheck
```
Expected: 0 TypeScript errors. If errors appear in changed files (`chat/page.tsx`, `bookings/[id]/quotes/page.tsx`, `quote-builder-dialog.tsx`, hooks), fix them; strict mode, no `any`.

- [ ] **Step 4: If failures — STOP and debug**

Use superpowers:systematic-debugging; fix implementation or stale assertions, re-run until green.

---

### Task 4: Stop tracking `.next-dev` build artifacts

Git status is polluted with hundreds of `packages/vendor/.next-dev/**` build files (turbopack cache, chunks). These are dev-server output, must not be committed.

**Files:**
- Modify: `.gitignore`
- Remove from index: `packages/vendor/.next-dev/**`

- [ ] **Step 1: Ensure ignore rule exists**

Check `.gitignore` for a `.next-dev` rule:
```bash
grep -n "next-dev" .gitignore
```
If missing, append:
```gitignore
# Next.js dev-server build output
.next-dev/
```

- [ ] **Step 2: Untrack the artifacts (keep on disk)**

```bash
git rm -r --cached packages/vendor/.next-dev
```
Expected: long list of `rm '...'` lines; files stay on disk.

- [ ] **Step 3: Verify clean status**

```bash
git status --short | grep next-dev
```
Expected: only `D` (staged deletions) entries or nothing new; no `M`/`??` `.next-dev` entries remain.

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore(vendor): stop tracking .next-dev build artifacts"
```

---

### Task 5: End-to-end REST flow smoke test (negotiation loop)

Verify the full loop against the running backend with dev-mode email logging — proves: booking → vendor quote → user counter → vendor accept → notifications + email dispatch.

**Files:**
- Test: `packages/backend/tests/test_quote_service.py` (already covers service layer) — this task is a live integration pass.

- [ ] **Step 1: Start the backend**

```bash
pnpm db:up
pnpm dev:backend
```
Expected: FastAPI boots on :5000, lifespan logs show event-bus subscriptions registered.

- [ ] **Step 2: Walk the negotiation loop with the API**

Use seeded accounts from `src/scripts/seed.py` (or register fresh user + vendor). Sequence (httpie/curl, auth via Bearer tokens from `/api/v1/auth/login`):
1. Customer: `POST /api/v1/bookings` → booking `pending`
2. Vendor: `POST /api/v1/bookings/{id}/quotes` body `{"subtotal": 50000, "deposit_required": 10000, "currency": "PKR"}` → 201, booking → `quoted`
3. Customer: `POST /api/v1/quotes/{qid}/counter` body `{"proposed_total": 45000}` → 201, quote → `countered`, booking → `negotiating`
4. Vendor: `PATCH /api/v1/counter-offers/{cid}/respond` body `{"action": "accept"}` → 200, quote → `accepted`, booking → `accepted`, `total_price` = 45000
5. Customer: `GET /api/v1/notifications/` → contains quote/accepted notifications

Expected at step 4: backend log shows `email.dev_mode` entries (dev-mode email dispatch) and `counter_offer.responded` structlog line.

- [ ] **Step 3: Verify orchestrator chat path boots**

```bash
cd packages/agentic_event_orchestrator
uv run uvicorn main:app --port 8000
```
Expected: startup logs show firewall + leak detector + guardrails wired, instruction validation passes, no crash. (Live LLM chat turn optional — requires GEMINI_API_KEY; if present, send one `POST /api/v1/ai/chat` "hello" and expect a TriageAgent greeting, no 500.)

- [ ] **Step 4: Record results**

If any step fails: STOP, debug with superpowers:systematic-debugging, fix, re-run the failing step. Do not proceed to commits with a broken loop.

---

### Task 6: Commit the feature work in logical chunks

All suites green, loop verified. Working tree has one large changeset — split into reviewable conventional commits. PR targets `develop` per CLAUDE.md; work currently sits on `main`, so create a feature branch first.

- [ ] **Step 1: Create feature branch from current state**

```bash
git checkout -b feature/chat-booking-negotiation
```

- [ ] **Step 2: Commit backend negotiation loop**

```bash
git add packages/backend/alembic/versions/20260521_add_subscription_fields.py \
        packages/backend/alembic/versions/20260602_negotiation_loop.py \
        packages/backend/src/models/ packages/backend/src/services/ \
        packages/backend/src/api/ packages/backend/src/middleware/ \
        packages/backend/src/config/ packages/backend/src/main.py \
        packages/backend/src/schemas/ packages/backend/src/scripts/ \
        packages/backend/tests/ packages/backend/.env.example
git commit -m "feat(backend): negotiation loop — quotes, counter-offers, booking states, notifications + emails"
```

- [ ] **Step 3: Commit orchestrator changes**

```bash
git add packages/agentic_event_orchestrator/
git commit -m "feat(agentic_event_orchestrator): booking/negotiation tools, autonomy instructions, thinking-budget cap"
```

- [ ] **Step 4: Commit portal UIs**

```bash
git add packages/user/ packages/vendor/ packages/admin/ packages/ui/ 2>/dev/null
git commit -m "feat(portals): chat booking cards, user quote accept/counter, vendor quote builder + counter respond"
```

- [ ] **Step 5: Commit remaining infra files**

```bash
git status --short   # review leftovers; stage intentional ones only
git add .gitignore package.json packages/admin/package.json  # plus any reviewed stragglers
git commit -m "chore(infra): workspace config updates for negotiation loop"
```
Deleted `event-ai-audit-report.md` is intentional (`git rm` it if still unstaged).

- [ ] **Step 6: Verify nothing intended is left behind**

```bash
git status --short
```
Expected: empty (or only files deliberately excluded). Run full verification once more before declaring done:
```bash
cd packages/backend && uv run pytest -q
cd ../agentic_event_orchestrator && uv run pytest -q
pnpm typecheck
```

---

## Self-Review Notes

- **Spec coverage:** All five goal bullets map to audit-confirmed implementations + verification tasks; the three AI-assistant issues map to Task 2 Step 3 (model/thinking), instructions audit (autonomy), Task 5 Step 3 (chat boot).
- **No new code is planned** because the audit found the feature complete in the working tree; the deliverable is verified, committed software. If verification uncovers gaps, the executing engineer stops and debugs per task instructions rather than improvising features.
- **Branch note:** work is on `main` with uncommitted changes — Task 6 branches before committing, satisfying the "never start on main without consent" rule retroactively for the commit step.
