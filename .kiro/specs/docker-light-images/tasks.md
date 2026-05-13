# Implementation Plan: docker-light-images

## Overview

Most of the implementation is already in place. These tasks focus on verifying each
artefact against the requirements and design, patching any remaining gaps, writing the
structural assertion test suite (pytest) that encodes the 9 correctness properties, and
running a full smoke build to confirm everything compiles and starts correctly.

All test code is Python (pytest + subprocess + re/string matching). No PBT library is
needed — the properties are universally quantified over the finite, enumerable set of
Dockerfiles in the project.

---

## Tasks

- [ ] 1. Verify and finalise the backend Dockerfile
  - Read `packages/backend/Dockerfile` and cross-check every line against Requirements
    1.1–1.6, 5.1–5.4, 7.1–7.2, 9.1, 9.4, and 10.1–10.2.
  - Confirm: 2-stage build (builder + runner), uv binary copied from
    `ghcr.io/astral-sh/uv:latest` in builder only, `uv sync --frozen --no-dev
    --no-install-project` with `--mount=type=cache,target=/root/.cache/uv`, base image
    `python:3.13-slim` in both stages, manifests copied before source, `.venv` copied
    with `--chown=appuser:appgroup`, `appgroup` GID 1001 + `appuser` UID 1001 created,
    `USER appuser` before `EXPOSE`, `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1`
    set, `PATH=/app/.venv/bin:$PATH`, HEALTHCHECK polls `/api/v1/health/db` with correct
    parameters, CMD is `uvicorn src.main:app --host 0.0.0.0 --port 5000 --workers 2`.
  - Fix any deviations found.
  - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.6, 5.1, 5.2, 5.3, 7.1, 7.2, 9.1, 9.4, 10.1, 10.2_

- [ ] 2. Verify and finalise the orchestrator Dockerfile
  - Read `packages/agentic_event_orchestrator/Dockerfile` and cross-check against
    Requirements 1.1–1.6, 2.1–2.3, 5.1–5.4, 7.1, 7.3, 9.1, 9.4, and 10.1–10.2.
  - Confirm: base image `python:3.12-slim`, CMD is exactly
    `["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]`, HEALTHCHECK polls
    `http://localhost:8000/health`, `uv.lock` (not `uv.lock*`) copied in manifests COPY,
    all non-root user and chown requirements met, cache mount present.
  - Note: `uv.lock*` glob in the current file is acceptable but `uv.lock` (exact) is
    preferred — update if the lockfile is committed.
  - Fix any deviations found.
  - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 5.1, 5.2, 5.3, 7.1, 7.3, 9.1, 9.4, 10.1, 10.2_

- [ ] 3. Verify and finalise the vendor Dockerfile
  - Read `packages/vendor/Dockerfile` and cross-check against Requirements 3.1–3.6,
    4.1, 5.1–5.4, 7.1, 7.4, 9.2, 9.3, and 10.1–10.2.
  - Confirm: 3-stage build (deps → builder → runner), `corepack enable && corepack
    prepare pnpm@latest --activate` in deps and builder stages, pnpm store cache mount
    in deps stage, `pnpm install --frozen-lockfile`, `pnpm run build`, runner copies only
    `.next/standalone`, `.next/static`, `public`, `NODE_ENV=production`,
    `NEXT_TELEMETRY_DISABLED=1`, `HOSTNAME=0.0.0.0`, `PORT=3000`, CMD `["node",
    "server.js"]`, non-root user UID/GID 1001, HEALTHCHECK uses `wget -qO-` on port 3000.
  - Fix any deviations found.
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 5.1, 5.2, 5.3, 7.1, 7.4, 9.2, 9.3, 10.1, 10.2_

- [ ] 4. Verify and finalise the user Dockerfile
  - Read `packages/user/Dockerfile` and apply the same checklist as task 3.
  - Additionally confirm `NEXT_PUBLIC_API_URL` is accepted as a build ARG and baked into
    the builder ENV.
  - Fix any deviations found.
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 5.1, 5.2, 5.3, 7.1, 7.4, 9.2, 9.3, 10.1, 10.2_

- [ ] 5. Verify and finalise the admin Dockerfile
  - Read `packages/admin/Dockerfile` and apply the same checklist as task 3.
  - Fix any deviations found.
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 5.1, 5.2, 5.3, 7.1, 7.4, 9.2, 9.3, 10.1, 10.2_

- [ ] 6. Checkpoint — Dockerfiles complete
  - Ensure all five Dockerfiles pass a manual read-through against the checklist above.
    Ask the user if any ambiguity arises before proceeding.

- [ ] 7. Verify and finalise the backend .dockerignore
  - Read `packages/backend/.dockerignore` and confirm it excludes: `.env`, `.env.*`,
    `__pycache__/`, `*.pyc`, `*.pyo`, `.venv/`, `tests/`, `.git/`, `.vscode/`, `.idea/`,
    `*.log`, `.pytest_cache/`, `.coverage`, `htmlcov/`.
  - Note: the current file is missing `*.pyo` and `dist/` / `*.egg-info/` entries from
    the design spec — add them if absent.
  - Fix any gaps.
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 8. Verify and finalise the orchestrator .dockerignore
  - Read `packages/agentic_event_orchestrator/.dockerignore` and confirm it excludes the
    same Python set as task 7 plus `.env.local` and `.env.*` (currently only `.env` and
    `.env.local` are present — `.env.*` glob is missing).
  - Add `*.pyc`, `*.pyo`, `.pytest_cache/`, `tests/`, `dist/`, `*.egg-info/` if absent.
  - Fix any gaps.
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 9. Verify and finalise the Node service .dockerignore files
  - Read `packages/vendor/.dockerignore`, `packages/user/.dockerignore`, and
    `packages/admin/.dockerignore`.
  - Confirm each excludes: `node_modules/`, `.next/`, `.env`, `.env.*`, `.env.local`,
    `.env.*.local`, `*.log`, `.git/`, `.vscode/`, `.idea/`, `coverage/`, `__tests__/`,
    `.turbo/`, `*.test.ts`, `*.test.tsx`, `*.spec.ts`, `*.spec.tsx`.
  - Note: vendor `.dockerignore` is missing `.env.local`, `.env.*.local`, `.turbo/`, and
    test file globs — add them. User and admin are missing `.turbo/` and test file globs.
  - Fix any gaps across all three files.
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 10. Verify and finalise next.config files for standalone output
  - Read `packages/user/next.config.ts`, `packages/admin/next.config.ts`, and
    `packages/vendor/next.config.js`.
  - Confirm `output: 'standalone'` (or `"standalone"`) is present in all three.
  - Confirm `transpilePackages: ["@event-ai/ui"]` is present in `user` and `admin`
    configs (both portals depend on the shared UI package).
  - Confirm vendor config does NOT need `transpilePackages` (it does not import
    `@event-ai/ui`).
  - Fix any gaps.
  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 11. Verify and finalise docker-compose.yml
  - Read `docker-compose.yml` and cross-check against Requirements 8.1–8.8.
  - Confirm: all five services present (`backend`, `orchestrator`, `vendor`, `user`,
    `admin`), port mappings 5000→5000, 8000→8000, 3002→3000, 3003→3000, 3004→3000,
    `depends_on: backend: condition: service_healthy` on orchestrator/vendor/user/admin,
    `restart: unless-stopped` on all services, resource limits (Python: 512M/1.0 CPU,
    Node: 256M/0.5 CPU), `NEXT_PUBLIC_API_URL` passed as build ARG for vendor/user/admin,
    shared `public` bridge network, healthcheck definitions match Dockerfile HEALTHCHECKs.
  - Fix any deviations found.
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

- [ ] 12. Checkpoint — Configuration artefacts complete
  - All Dockerfiles, .dockerignore files, next.config files, and docker-compose.yml are
    verified and patched. Ask the user if questions arise before proceeding to tests.

- [ ] 13. Create the structural assertion test suite
  - Create `tests/docker/test_dockerfiles.py` at the repo root.
  - Set up pytest fixtures that read each Dockerfile as text and expose the runner-stage
    text separately from the full file text.
  - Implement Property 1 (no build tool leakage): assert `uv` binary path, `pip install`,
    `npm install`, `npm ci`, and `node_modules` do not appear in runner/final stage text
    for each Dockerfile.
  - Implement Property 2 (non-root user invariant): assert `appgroup` with GID 1001,
    `appuser` with UID 1001, `USER appuser`, and `--chown=appuser:appgroup` on every
    COPY in the runner stage of each Dockerfile; assert no `USER root` after `USER appuser`.
  - Implement Property 3 (build context secrets exclusion): assert each service directory
    has a `.dockerignore` containing `.env`, `.env.*`, `node_modules/`, `.next/`,
    `__pycache__/`, `.venv/`, `*.pyc`, `.git/`, `.vscode/`, `.idea/`, `*.log`.
  - Implement Property 4 (package manager compliance): assert no `pip install`, `npm
    install`, or `npm ci` string appears in any Dockerfile; assert Python Dockerfiles use
    `uv sync`; assert Node Dockerfiles use `pnpm install` and `corepack`.
  - Implement Property 5 (health check presence and parameters): assert `HEALTHCHECK`
    with `--interval=30s`, `--timeout=5s`, `--retries=3`, and `--start-period` ≥ 15s
    appears in each Dockerfile; assert Node Dockerfiles use `wget -qO-` on port 3000.
  - Implement Property 6 (cache mount presence): assert `--mount=type=cache,target=
    /root/.cache/uv` in Python builder stages; assert `--mount=type=cache,target=
    /root/.local/share/pnpm/store` in Node deps stages.
  - Implement Property 7 (manifest-first layer ordering): assert the line number of the
    manifest COPY (`pyproject.toml`/`uv.lock` or `package.json`/`pnpm-lock.yaml`) is
    lower than the line number of the source COPY in each stage.
  - Implement Property 8 (compose service invariants): parse `docker-compose.yml` with
    PyYAML and assert `restart: unless-stopped`, `deploy.resources.limits` with correct
    values, and `NEXT_PUBLIC_API_URL` build ARG for each Node service.
  - Implement Property 9 (standalone output configuration): assert `output.*standalone`
    regex matches in `packages/user/next.config.ts`, `packages/admin/next.config.ts`,
    and `packages/vendor/next.config.js`.
  - _Requirements: 1.1–1.6, 2.1–2.3, 3.1–3.6, 4.1, 5.1–5.4, 6.1–6.4, 7.1–7.4, 8.5–8.8, 9.1–9.4, 10.1–10.2_

- [ ] 14. Create tests/docker/conftest.py with shared fixtures
  - Create `tests/docker/__init__.py` (empty) and `tests/docker/conftest.py`.
  - Define a `SERVICES` constant mapping service name → package path and Dockerfile path.
  - Define a `dockerfile_text(service)` fixture that reads and returns the full Dockerfile
    text for a given service.
  - Define a `runner_stage_text(service)` fixture that extracts only the final `FROM ...
    AS runner` stage text from a Dockerfile (everything after the last `FROM` line).
  - Define a `compose_config` fixture that parses `docker-compose.yml` with PyYAML and
    returns the parsed dict.
  - _Requirements: (test infrastructure — supports all properties)_

- [ ]* 15. Run the structural assertion test suite and fix failures
  - Run `uv run pytest tests/docker/ -v` from the repo root (requires `pyyaml` in the
    test environment — add to `packages/backend/pyproject.toml` dev dependencies if
    absent, or run from a standalone venv with `pip install pytest pyyaml`).
  - Fix any Dockerfile, .dockerignore, next.config, or docker-compose.yml issues
    surfaced by failing tests.
  - All 9 property tests must pass before proceeding.
  - _Requirements: all_

- [ ] 16. Checkpoint — Test suite green
  - All structural assertion tests pass. Ask the user if questions arise.

- [ ]* 17. Run docker-compose build smoke test
  - From the repo root, run `docker-compose build --no-cache 2>&1 | tee /tmp/build.log`.
  - Confirm all five services build without error.
  - If any build fails, read the error from `/tmp/build.log`, identify the root cause
    (missing lockfile, wrong COPY path, missing ARG, etc.), fix the relevant Dockerfile
    or config, and re-run.
  - _Requirements: 1.1–1.6, 2.1–2.3, 3.1–3.6, 4.1–4.3, 8.1–8.8_

- [ ]* 18. Verify non-root UID at runtime
  - After a successful build, run `docker run --rm event-ai-backend id` and assert the
    output contains `uid=1001`.
  - Repeat for `event-ai-orchestrator`, `event-ai-vendor`, `event-ai-user`,
    `event-ai-admin`.
  - _Requirements: 5.1, 5.3_

- [ ] 19. Final checkpoint — All artefacts verified
  - All Dockerfiles, .dockerignore files, next.config files, and docker-compose.yml are
    correct. Structural tests pass. Smoke build succeeds. Ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster review pass, but
  the smoke build (task 17) is strongly recommended before merging.
- Each task references specific requirements for traceability.
- The test suite in tasks 13–15 encodes all 9 correctness properties from the design
  document as executable assertions — they serve as the permanent regression guard for
  this feature.
- PyYAML is needed only for the compose invariant tests (Property 8); it is already a
  transitive dependency in most Python environments but should be added to dev deps if
  `uv run pytest` cannot find it.
- The `tests/docker/` directory lives at the repo root (not inside `packages/backend`)
  because it tests cross-cutting infrastructure artefacts, not backend application logic.
