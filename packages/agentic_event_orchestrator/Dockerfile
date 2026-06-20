# ── Orchestrator — Python 3.12 / FastAPI / uv ────────────────────────────────
# Base: python:3.12-slim (Debian slim ~50MB) — NOT alpine (uv needs glibc).
# Multi-stage: builder installs deps into /app/.venv, runner copies only the venv.
# syntax=docker/dockerfile:1

# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Copy uv binary from official image — no pip, no OS package install needed
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy manifests first — layer cache: deps only reinstall when these change
COPY pyproject.toml uv.lock ./

# Install production deps into /app/.venv using build cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ── Stage 2: runner ───────────────────────────────────────────────────────────
FROM python:3.12-slim AS runner

# Non-root user
RUN groupadd --system --gid 1001 appgroup \
 && useradd  --system --uid 1001 --gid appgroup appuser

WORKDIR /app

# Copy only the virtualenv — no uv, no build tools in production image
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

# Copy only production application source — no dev/test files in the image
COPY --chown=appuser:appgroup main.py app.py server.py ./
COPY --chown=appuser:appgroup config ./config
COPY --chown=appuser:appgroup pipeline ./pipeline
COPY --chown=appuser:appgroup routers ./routers
COPY --chown=appuser:appgroup services ./services
COPY --chown=appuser:appgroup tools ./tools
COPY --chown=appuser:appgroup models ./models
COPY --chown=appuser:appgroup database ./database
COPY --chown=appuser:appgroup guardrails.py rate_limiter.py service_auth.py ./

# Alembic migrations — needed so the image can run `alembic upgrade head` on deploy
COPY --chown=appuser:appgroup alembic ./alembic
COPY --chown=appuser:appgroup alembic.ini ./
COPY --chown=appuser:appgroup start.sh run_migrations.py ./
RUN chmod +x start.sh run_migrations.py

# Activate venv via PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser

# Port is injected by the platform ($PORT on Railway/Render); defaults to 8000 locally.
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c \
        "import os,urllib.request; urllib.request.urlopen('http://localhost:'+os.environ.get('PORT','8000')+'/health')"

# Shell form so ${PORT} expands at runtime — honors platform-injected port.
CMD ["./start.sh"]
