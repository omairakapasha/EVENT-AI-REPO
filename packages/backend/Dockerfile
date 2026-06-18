# ── Backend — Python 3.13 / FastAPI / uv ─────────────────────────────────────
# Base: python:3.13-slim (Debian slim ~50MB) — NOT alpine (uv needs glibc).
# Multi-stage: builder installs deps, runner copies only the venv.
# syntax=docker/dockerfile:1

# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

# Copy uv binary from official image — no OS package install needed
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy manifests first — layer cache: deps only reinstall when these change
COPY pyproject.toml uv.lock ./

# Install production deps into /app/.venv using build cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ── Stage 2: runner ───────────────────────────────────────────────────────────
FROM python:3.13-slim AS runner

# Non-root user
RUN groupadd --system --gid 1001 appgroup \
 && useradd  --system --uid 1001 --gid appgroup appuser

WORKDIR /app

# Copy only the virtualenv — no uv, no build tools in production image
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

# Copy application source
COPY --chown=appuser:appgroup src ./src
COPY --chown=appuser:appgroup alembic ./alembic
COPY --chown=appuser:appgroup alembic.ini ./

# Activate venv via PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser

# Port is injected by the platform ($PORT on Railway/Render); defaults to 5000 locally.
ENV PORT=5000
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c \
        "import os,urllib.request; urllib.request.urlopen('http://localhost:'+os.environ.get('PORT','5000')+'/api/v1/health')"

# Shell form so ${PORT} expands at runtime — honors platform-injected port.
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-5000} --workers 2
