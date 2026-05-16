# ── Vendor Portal — Next.js / pnpm monorepo ──────────────────────────────────
# Build context: repo root (docker-compose sets context: .)
# Multi-stage: deps → builder → runner (standalone output only).
# syntax=docker/dockerfile:1

# ── Stage 1: deps ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS deps
RUN corepack enable && corepack prepare pnpm@9.0.0 --activate
WORKDIR /app

# Copy monorepo manifests first — layer cache: deps only reinstall when these change
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

# Copy workspace package manifests (needed for pnpm to resolve workspace deps)
COPY packages/vendor/package.json ./packages/vendor/
COPY packages/ui/package.json     ./packages/ui/

# Install all workspace deps with cache mount
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

# ── Stage 2: builder ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder
RUN corepack enable && corepack prepare pnpm@9.0.0 --activate
WORKDIR /app

# Copy installed node_modules from deps stage
COPY --from=deps /app/node_modules         ./node_modules
COPY --from=deps /app/packages/vendor/node_modules ./packages/vendor/node_modules
COPY --from=deps /app/packages/ui/node_modules     ./packages/ui/node_modules

# Copy source for the packages we need
COPY packages/vendor/ ./packages/vendor/
COPY packages/ui/     ./packages/ui/

# Copy root config files needed by Next.js build
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./

# NEXT_PUBLIC_* vars are baked at build time
ARG NEXT_PUBLIC_API_URL=http://localhost:5000/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

RUN pnpm --filter @event-ai/vendor run build

# ── Stage 3: runner ───────────────────────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app

RUN addgroup --system --gid 1001 appgroup \
 && adduser  --system --uid 1001 --ingroup appgroup appuser

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

# Next.js standalone output — only what's needed to run (~30MB vs 300MB+)
COPY --from=builder --chown=appuser:appgroup /app/packages/vendor/.next/standalone ./
COPY --from=builder --chown=appuser:appgroup /app/packages/vendor/.next/static     ./.next/static
COPY --from=builder --chown=appuser:appgroup /app/packages/vendor/public           ./public

USER appuser
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -qO- http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
