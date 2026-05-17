# Implementation Plan

## Overview

Implements the AUTH-03 bugfix: add an `email_verified` guard to `get_current_user` in `packages/backend/src/middleware/auth.middleware.py`. Follows the exploratory bugfix workflow — write tests before the fix, apply the minimal one-line change, then verify both fix-checking and preservation properties pass.

## Task Dependency Graph

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1"] },
    { "wave": 2, "tasks": ["2"] },
    { "wave": 3, "tasks": ["3"] },
    { "wave": 4, "tasks": ["4"] }
  ]
}
```

## Tasks

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Unverified User Accesses Protected Route
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate that an unverified user currently receives 2xx on protected routes
  - **Scoped PBT Approach**: Scope the property to the concrete failing case — register a user, skip email verification, login to obtain a JWT, then call `GET /api/v1/users/me` and assert the response is `403` with `AUTH_EMAIL_NOT_VERIFIED`
  - Create `packages/backend/tests/test_email_verified_route_guard_exploration.py`
  - Use the `client` fixture from `conftest.py` (AsyncClient with SQLite in-memory DB)
  - Test setup: `POST /api/v1/auth/register` → do NOT call any email-verification endpoint → `POST /api/v1/auth/login` (form-encoded `data=`) → extract `access_token`
  - Bug condition: `isBugCondition(user, token)` where `user.is_active is True` AND `user.email_verified is False` AND token is valid and non-expired
  - Assert `response.status_code == 403` — this FAILS on unfixed code (currently returns `200`)
  - Assert `response.json()["success"] is False`
  - Assert `response.json()["error"]["code"] == "AUTH_EMAIL_NOT_VERIFIED"`
  - Assert `response.json()["error"]["message"] == "Email address has not been verified."`
  - Also test `POST /api/v1/bookings` and `POST /api/v1/events` with unverified JWT — assert `403` (currently returns `201` or `422`, never `403`)
  - Run test on UNFIXED code: `uv run pytest tests/test_email_verified_route_guard_exploration.py -v`
  - **EXPECTED OUTCOME**: Test FAILS (this is correct — it proves the bug exists)
  - Document counterexamples found (e.g., "`GET /api/v1/users/me` with unverified JWT returns `200 OK` instead of `403`")
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Non-Buggy Inputs Produce Unchanged Behavior
  - **IMPORTANT**: Follow observation-first methodology — run each case on UNFIXED code first, record the actual response, then write the assertion
  - Create `packages/backend/tests/test_email_verified_route_guard_preservation.py`
  - Use `hypothesis` with `@given` / `st.builds` for the verified-user property; use plain `pytest.mark.asyncio` for the deterministic cases
  - Use `@h_settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)` to match project convention
  - **Observe and encode the following baseline behaviors:**
  - **2a — Verified user gets 200**: register → verify email (set `email_verified=True` directly on the DB row via `db_session`) → login → `GET /api/v1/users/me` → observe `200 OK`; write property-based test generating arbitrary verified users (different names, UUIDs) and asserting `200` on protected routes (from Preservation Requirements in design)
  - **2b — Invalid/expired JWT gets 401**: send a malformed token string to `GET /api/v1/users/me` → observe `401` with `AUTH_UNAUTHORIZED`; write property-based test generating arbitrary invalid token strings and asserting `401` (from Preservation Requirements in design)
  - **2c — Inactive user gets 401**: register → set `is_active=False` on DB row → login → `GET /api/v1/users/me` → observe `401`; assert `401` is unchanged (from Preservation Requirements in design)
  - **2d — Public endpoints unaffected**: `POST /api/v1/auth/register` and `POST /api/v1/auth/login` without any token → observe `200`/`201`; assert these endpoints continue to work without email verification (from Preservation Requirements in design)
  - **2e — `get_current_user_optional` with unverified user returns user object**: register → skip verification → login → call an optional-auth endpoint → observe that the user object is present (not `None`, not `403`); assert this behavior is preserved (from Preservation Requirements in design, requirement 3.5)
  - Run tests on UNFIXED code: `uv run pytest tests/test_email_verified_route_guard_preservation.py -v`
  - **EXPECTED OUTCOME**: All tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 3. Fix for AUTH-03 — unverified users bypass email verification gate

  - [ ] 3.1 Implement the email-verified guard in `get_current_user`
    - File: `packages/backend/src/middleware/auth.middleware.py`
    - Function: `get_current_user`
    - After `user = await auth_service.verify_access_token(token, session)` and before `request.state.user = user`, insert:
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
    - Do NOT modify `get_current_user_optional` — its existing `except HTTPException: return None` block already catches the new `403`, satisfying requirement 3.5 with zero additional changes
    - Do NOT modify `verify_access_token` in `auth_service` — the guard belongs in the middleware layer so that `get_current_user_optional` naturally suppresses it
    - Do NOT add any Alembic migration — `email_verified` already exists on the `users` table with `default=False`
    - _Bug_Condition: `isBugCondition(user, token)` where `user.is_active is True` AND `user.email_verified is False` AND token is valid and non-expired_
    - _Expected_Behavior: `get_current_user` raises `HTTPException(status_code=403, detail={"code": "AUTH_EMAIL_NOT_VERIFIED", "message": "Email address has not been verified."})` for all inputs satisfying the bug condition_
    - _Preservation: verified users (`email_verified=True`) continue to receive the user object; invalid/expired tokens continue to receive `401 AUTH_UNAUTHORIZED`; inactive users continue to receive `401`; public endpoints are unaffected; `get_current_user_optional` continues to return the user object for unverified users_
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Unverified User Is Rejected with 403
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - The test from task 1 encodes the expected behavior (403 + `AUTH_EMAIL_NOT_VERIFIED`)
    - When this test passes, it confirms the fix is in place and the expected behavior is satisfied
    - Run: `uv run pytest tests/test_email_verified_route_guard_exploration.py -v`
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed — unverified users now receive `403`)
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Buggy Inputs Produce Unchanged Behavior
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run: `uv run pytest tests/test_email_verified_route_guard_preservation.py -v`
    - **EXPECTED OUTCOME**: All tests PASS (confirms no regressions — verified users still get `200`, invalid tokens still get `401`, inactive users still get `401`, public endpoints still work, `get_current_user_optional` still returns user object for unverified users)
    - Confirm all five preservation properties (2a–2e) still pass after the fix

- [ ] 4. Checkpoint — Ensure all tests pass
  - Run the full test suite: `uv run pytest -v` from `packages/backend`
  - Confirm `test_email_verified_route_guard_exploration.py` passes (bug fixed)
  - Confirm `test_email_verified_route_guard_preservation.py` passes (no regressions)
  - Confirm no pre-existing tests were broken by the one-line guard addition
  - Ask the user if any questions arise before closing the spec

## Notes

- The fix is a single `if not user.email_verified` guard in `get_current_user` — no schema migration, no changes to `get_current_user_optional` or `verify_access_token`
- `get_current_user_optional` naturally suppresses the new `403` via its existing `except HTTPException: return None` block, satisfying requirement 3.5 with zero additional code
- Tests use `sqlite+aiosqlite:///:memory:` via the `client` fixture in `conftest.py` — no real DB or Docker needed
- Use `uv run pytest` (never `pip` or bare `pytest`) per project conventions
- Property-based tests use `hypothesis` with `@h_settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)` to match the existing test suite pattern
- Login endpoint uses form-encoded `data=` (not JSON) — see `conftest.py` and existing auth tests
