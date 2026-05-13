# Requirements Document

## Introduction

This feature produces optimized, lightweight Docker images for every service in the Event-AI
monorepo. The project contains five independently deployable services:

| Service | Runtime | Port |
|---|---|---|
| `packages/backend` | Python 3.13 / FastAPI / uv | 5000 |
| `packages/agentic_event_orchestrator` | Python 3.12 / FastAPI / uv | 8000 |
| `packages/vendor` | Next.js / pnpm | 3002 (dev) / 3000 (container) |
| `packages/user` | Next.js / pnpm | 3003 (dev) / 3000 (container) |
| `packages/admin` | Next.js / pnpm | 3004 (dev) / 3000 (container) |

The goal is to minimise final image size and attack surface through multi-stage builds, correct
package-manager usage (uv for Python, pnpm for Node — never pip or npm), non-root runtime users,
and tight `.dockerignore` files. A root-level `docker-compose.yml` must wire all five services
together with health checks, resource limits, and correct port mappings.

## Glossary

- **Builder stage**: A Docker build stage whose sole purpose is compiling or installing
  dependencies; it is discarded and never shipped.
- **Runner stage**: The final, minimal Docker stage that is shipped as the production image.
- **Standalone output**: Next.js build mode (`output: 'standalone'`) that emits a self-contained
  `server.js` plus only the node_modules it actually needs, reducing the runtime image to
  ~30 MB instead of ~300 MB.
- **uv**: The Python package manager used by this project. Must be used in all Python Dockerfiles
  instead of pip.
- **pnpm**: The Node package manager used by this project. Must be used in all Node Dockerfiles
  instead of npm.
- **Build_System**: The Docker build pipeline (Dockerfiles + docker-compose.yml) that produces
  all service images.
- **Python_Service**: Either `packages/backend` or `packages/agentic_event_orchestrator`.
- **Node_Service**: Any of `packages/vendor`, `packages/user`, or `packages/admin`.
- **Orchestrator**: The `packages/agentic_event_orchestrator` service.
- **Non_Root_User**: A system user with UID 1001 and no login shell, created inside the image.

---

## Requirements

### Requirement 1: Multi-Stage Build for Python Services

**User Story:** As a DevOps engineer, I want Python service images built with multi-stage
Dockerfiles using uv, so that the final image contains only the virtualenv and application
source — no build tools, no uv binary, no dev dependencies.

#### Acceptance Criteria

1. THE Build_System SHALL use a dedicated builder stage that copies the uv binary from
   `ghcr.io/astral-sh/uv:latest` and installs production dependencies into `/app/.venv`
   using `uv sync --frozen --no-dev --no-install-project`.
2. THE Build_System SHALL use a separate runner stage based on `python:3.13-slim` (backend)
   and `python:3.12-slim` (orchestrator) that copies only `/app/.venv` from the builder stage.
3. IF the builder stage is omitted or the uv binary is present in the runner stage, THEN
   THE Build_System SHALL fail the build.
4. THE Build_System SHALL mount a uv cache (`--mount=type=cache,target=/root/.cache/uv`) in
   the builder stage to avoid re-downloading packages on repeated builds.
5. THE Build_System SHALL set `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1` in the
   runner stage environment.
6. THE Build_System SHALL activate the virtualenv by prepending `/app/.venv/bin` to `PATH`
   rather than calling `source activate`.

---

### Requirement 2: Correct Entry Point for the Orchestrator Service

**User Story:** As a developer, I want the Orchestrator container to start the correct FastAPI
application, so that the service is reachable on port 8000 and health checks pass.

#### Acceptance Criteria

1. THE Build_System SHALL set the Orchestrator CMD to
   `["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]`.
2. WHEN the Orchestrator container starts, THE Build_System SHALL expose port 8000.
3. THE Build_System SHALL include a HEALTHCHECK that polls `http://localhost:8000/health`
   with a 30-second interval, 5-second timeout, 15-second start period, and 3 retries.

---

### Requirement 3: Multi-Stage Build for Node Services

**User Story:** As a DevOps engineer, I want Next.js service images built with three-stage
Dockerfiles using pnpm and Next.js standalone output, so that the final image ships only the
compiled server artefacts and no source code or node_modules.

#### Acceptance Criteria

1. THE Build_System SHALL use a `deps` stage based on `node:20-alpine` that installs
   dependencies via `pnpm install --frozen-lockfile` with a pnpm store cache mount.
2. THE Build_System SHALL use a `builder` stage that copies `node_modules` from the `deps`
   stage, copies application source, and runs `pnpm run build`.
3. THE Build_System SHALL use a `runner` stage based on `node:20-alpine` that copies only
   `.next/standalone`, `.next/static`, and `public` from the builder stage.
4. THE Build_System SHALL set `NODE_ENV=production`, `NEXT_TELEMETRY_DISABLED=1`, and
   `HOSTNAME=0.0.0.0` in the runner stage environment.
5. THE Build_System SHALL set the runner CMD to `["node", "server.js"]`.
6. WHEN the `user` or `admin` Dockerfile is built, THE Build_System SHALL NOT invoke `npm`
   at any stage; all Node package operations SHALL use `pnpm`.

---

### Requirement 4: Standalone Output Enabled for All Next.js Services

**User Story:** As a DevOps engineer, I want all three Next.js portals configured with
`output: 'standalone'`, so that the Docker runner stage can use the minimal standalone bundle
instead of the full node_modules tree.

#### Acceptance Criteria

1. THE Build_System SHALL require `output: 'standalone'` to be present in `next.config.ts`
   (or `next.config.js`) for the `user`, `admin`, and `vendor` packages.
2. WHEN `output: 'standalone'` is absent from a Next.js config, THE Build_System SHALL
   produce an empty `.next/standalone` directory, causing the runner stage CMD to fail at
   startup — this is the expected failure signal.
3. WHERE the `user` or `admin` portal depends on the `@event-ai/ui` workspace package,
   THE Build_System SHALL include `transpilePackages: ["@event-ai/ui"]` in the Next.js
   config alongside `output: 'standalone'`.

---

### Requirement 5: Non-Root Runtime User in All Images

**User Story:** As a security engineer, I want every container to run as a non-root system
user, so that a container escape does not grant root access to the host.

#### Acceptance Criteria

1. THE Build_System SHALL create a system group `appgroup` (GID 1001) and system user
   `appuser` (UID 1001) in every runner stage.
2. THE Build_System SHALL copy all application files with `--chown=appuser:appgroup` in
   every runner stage.
3. THE Build_System SHALL include `USER appuser` as the last instruction before `EXPOSE`
   in every runner stage.
4. IF a Dockerfile sets `USER root` after the `USER appuser` instruction, THEN
   THE Build_System SHALL be considered non-compliant.

---

### Requirement 6: Tight .dockerignore Files

**User Story:** As a DevOps engineer, I want each service to have a `.dockerignore` that
excludes all non-essential files, so that build context size is minimised and secrets are
never sent to the Docker daemon.

#### Acceptance Criteria

1. THE Build_System SHALL exclude `.env`, `.env.*`, and all secret files from every build
   context via `.dockerignore`.
2. THE Build_System SHALL exclude `node_modules/`, `.next/`, `__pycache__/`, `.venv/`,
   `*.pyc`, and test directories from every build context.
3. THE Build_System SHALL exclude `.git/`, `.vscode/`, `.idea/`, and `*.log` from every
   build context.
4. WHEN a `.dockerignore` file is absent from a service directory, THE Build_System SHALL
   treat the entire directory as the build context, which is a non-compliant state.

---

### Requirement 7: Health Checks on All Services

**User Story:** As a DevOps engineer, I want every service image to declare a HEALTHCHECK
instruction, so that Docker and docker-compose can detect unhealthy containers and restart them.

#### Acceptance Criteria

1. THE Build_System SHALL declare a HEALTHCHECK in every Dockerfile with an interval of
   30 seconds, a timeout of 5 seconds, a start period of at least 15 seconds, and 3 retries.
2. WHEN the backend health check runs, THE Build_System SHALL poll
   `http://localhost:5000/api/v1/health/db` using `python -c "import urllib.request; ..."`.
3. WHEN the orchestrator health check runs, THE Build_System SHALL poll
   `http://localhost:8000/health` using `python -c "import urllib.request; ..."`.
4. WHEN a Node service health check runs, THE Build_System SHALL poll
   `http://localhost:3000/` using `wget -qO-`.

---

### Requirement 8: Root docker-compose.yml Covers All Five Services

**User Story:** As a developer, I want a single `docker-compose.yml` at the repo root that
defines all five services with correct ports, health checks, resource limits, and inter-service
dependencies, so that the full stack can be started with one command.

#### Acceptance Criteria

1. THE Build_System SHALL define services `backend`, `orchestrator`, `vendor`, `user`, and
   `admin` in the root `docker-compose.yml`.
2. THE Build_System SHALL map host ports 5000→5000 (backend), 8000→8000 (orchestrator),
   3002→3000 (vendor), 3003→3000 (user), and 3004→3000 (admin).
3. THE Build_System SHALL set `depends_on` with `condition: service_healthy` so that
   `vendor`, `user`, and `admin` wait for `backend` to be healthy before starting.
4. THE Build_System SHALL set `depends_on` with `condition: service_healthy` so that
   `orchestrator` waits for `backend` to be healthy before starting.
5. THE Build_System SHALL apply memory and CPU resource limits to every service:
   Python services SHALL be limited to 512 MB RAM and 1.0 CPU; Node services SHALL be
   limited to 256 MB RAM and 0.5 CPU.
6. THE Build_System SHALL set `restart: unless-stopped` on every service.
7. THE Build_System SHALL define a shared `public` bridge network and attach all services
   to it.
8. WHEN `NEXT_PUBLIC_API_URL` is required at Next.js build time, THE Build_System SHALL
   pass it as a build ARG in the docker-compose service definition.

---

### Requirement 9: Package Manager Compliance

**User Story:** As a developer, I want all Dockerfiles to use the project-mandated package
managers (uv for Python, pnpm for Node), so that the images are consistent with local
development and banned practices are not introduced.

#### Acceptance Criteria

1. THE Build_System SHALL NOT invoke `pip install` in any Dockerfile; all Python dependency
   installation SHALL use `uv sync` or `uv pip install`.
2. THE Build_System SHALL NOT invoke `npm install` or `npm ci` in any Dockerfile; all Node
   dependency installation SHALL use `pnpm install`.
3. WHEN enabling pnpm in a Node Dockerfile, THE Build_System SHALL use
   `corepack enable && corepack prepare pnpm@latest --activate` rather than
   `npm install -g pnpm`.
4. THE Build_System SHALL pin the Python base image to `python:3.13-slim` for the backend
   and `python:3.12-slim` for the orchestrator, matching each service's `requires-python`
   constraint.

---

### Requirement 10: Build Cache Optimisation

**User Story:** As a developer, I want Dockerfiles to order instructions so that dependency
installation layers are cached separately from application source, so that source-only changes
do not trigger a full dependency reinstall.

#### Acceptance Criteria

1. THE Build_System SHALL copy dependency manifests (`pyproject.toml`, `uv.lock`,
   `package.json`, `pnpm-lock.yaml`) before copying application source in every Dockerfile.
2. THE Build_System SHALL use `--mount=type=cache` for the uv cache in Python builder stages
   and for the pnpm store in Node deps stages.
3. WHEN only application source files change and dependency manifests are unchanged,
   THE Build_System SHALL reuse the cached dependency layer without reinstalling packages.
