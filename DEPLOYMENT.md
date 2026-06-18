# Deployment Guide — Event-AI

The platform is **5 deployable services + 2 data stores**, not one app. Split across hosts:

| Service | Type | Host | Config |
|---|---|---|---|
| `packages/user` | Next.js 16 | **Vercel** | `packages/user/vercel.json` |
| `packages/admin` | Next.js 16 | **Vercel** | `packages/admin/vercel.json` |
| `packages/vendor` | Next.js 16 | **Vercel** | `packages/vendor/vercel.json` |
| `packages/backend` | FastAPI (py3.13) | **Render or Railway** | `render.yaml` / `packages/backend/railway.toml` |
| `packages/agentic_event_orchestrator` | FastAPI (py3.12) | **Render or Railway** | `render.yaml` / `.../railway.toml` |
| Postgres + pgvector | data | Render PG / Railway PG / Neon | — |
| Redis | data | Render Key Value / Railway Redis | — |

> Pick **one** backend host (Render **or** Railway). Both configs ship in the repo — don't run both. Frontends always go to Vercel.

---

## 1. Provision data stores first

Backend services need DB + Redis to exist before they boot.

- **Postgres** — needs the `vector` extension (pgvector).
  - **Neon** (current default): already has pgvector. Use its pooled URL for `DATABASE_URL`, direct URL for `DIRECT_URL`.
  - **Render managed PG**: created by `render.yaml`. After first deploy, open the DB's PSQL shell and run once:
    ```sql
    CREATE EXTENSION IF NOT EXISTS vector;
    ```
  - **Railway**: use the **pgvector** template (not plain Postgres).
- **Redis** — Render Key Value (in `render.yaml`) or Railway Redis plugin. Sets `REDIS_URL`.

Both Python services share **one** Postgres DB. Safe because each keeps a separate Alembic version table:
- backend → `alembic_version`
- orchestrator → `alembic_version_ai`

---

## 2. Deploy the backend stack

### Option A — Render (Blueprint)

1. Push repo to GitHub.
2. Render Dashboard → **New → Blueprint** → select repo. Render reads `render.yaml`.
3. It creates: `eventai-postgres`, `eventai-redis`, `eventai-backend`, `eventai-orchestrator`.
4. Fill every env var marked `sync: false` (see matrix in §4).
5. Enable pgvector on the DB (§1).
6. Migrations run automatically via `preDeployCommand: alembic upgrade head`.

### Option B — Railway

1. New project → deploy from GitHub repo.
2. Add **two services**, set Root Directory per service:
   - `packages/backend`
   - `packages/agentic_event_orchestrator`
   Each picks up its own `railway.toml` (Dockerfile build + preDeploy migrate + healthcheck).
3. Add **pgvector Postgres** + **Redis** plugins.
4. Map plugin connection strings into Variables: `DATABASE_URL`, `DIRECT_URL`, `APP_DATABASE_URL`, `REDIS_URL`.
5. Fill remaining secrets (§4). Railway injects `$PORT`; Dockerfiles honor it.

Both hosts: ports are platform-injected — no hardcoded port. Health: backend `/api/v1/health`, orchestrator `/health`.

---

## 3. Deploy the frontends (Vercel)

Create **3 separate Vercel projects** from the same repo:

| Project | Root Directory | Local dev port |
|---|---|---|
| user | `packages/user` | 3003 |
| admin | `packages/admin` | 3004 |
| vendor | `packages/vendor` | 3002 |

Per project:
1. Import repo → set **Root Directory** to the package path above.
2. Framework auto-detects as Next.js. `vercel.json` sets pnpm install + build.
3. Leave "Include files outside root directory" **on** (needed — `@event-ai/ui` is a `workspace:*` dep resolved from repo root).
4. Set env vars (§4). **`NEXT_PUBLIC_API_URL` is baked at build time** — set it before the first build, redeploy if changed.

---

## 4. Environment variable matrix

`build` = needed at frontend build time (Vercel). `runtime` = backend service env.

### Frontends (Vercel — all 3 projects)

| Var | Scope | Value |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | build | `https://<backend-host>/api/v1` |

### Backend (`eventai-backend`)

| Var | Source | Notes |
|---|---|---|
| `DATABASE_URL` | DB | pooled connection string |
| `DIRECT_URL` | DB | Alembic; direct (non-pooled) URL on Neon, same as DATABASE_URL elsewhere |
| `REDIS_URL` | Redis | |
| `AI_SERVICE_URL` | orchestrator internal URL | host:port of orchestrator |
| `AI_SERVICE_API_KEY` | **secret** | **must be identical** to orchestrator |
| `JWT_SECRET_KEY` | **secret** | `python -c "import secrets;print(secrets.token_urlsafe(64))"` (Render auto-gens) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | **secret** | Google Cloud OAuth |
| `GOOGLE_REDIRECT_URI` | **secret** | `https://<backend-host>/api/v1/auth/google/callback` |
| `CORS_ORIGINS` | **secret** | comma-separated prod Vercel domains |
| `FRONTEND_URL` | **secret** | primary frontend URL |
| `SMTP_USER` / `SMTP_PASSWORD` / `EMAIL_FROM` | **secret** | Brevo SMTP |
| `S3_ENDPOINT` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_BUCKET` | **secret** | R2 / S3 |
| `NODE_ENV=production`, `API_VERSION=v1`, `SMTP_HOST`, `SMTP_PORT=587`, `S3_REGION=auto`, `CDN_PROVIDER=r2` | static | defaults in `render.yaml` |

### Orchestrator (`eventai-orchestrator`)

| Var | Source | Notes |
|---|---|---|
| `DATABASE_URL` / `APP_DATABASE_URL` | DB | same DB as backend |
| `REDIS_URL` | Redis | |
| `BACKEND_API_URL` | backend internal URL | host:port of backend |
| `AI_SERVICE_API_KEY` | **secret** | **identical to backend** |
| `GEMINI_API_KEY` | **secret** | |
| `MEM0_API_KEY` | **secret** | persistent AI memory |
| `CHAINLIT_AUTH_SECRET` | **secret** | Render auto-gens |
| `GEMINI_MODEL`, `GEMINI_BASE_URL`, `LOG_LEVEL=info` | static | defaults in `render.yaml` |

---

## 5. Post-deploy checklist

- [ ] DB reachable; `CREATE EXTENSION vector` applied (non-Neon).
- [ ] Backend `/api/v1/health` returns 200.
- [ ] Orchestrator `/health` returns 200.
- [ ] Migrations applied: `alembic_version` + `alembic_version_ai` tables exist.
- [ ] `AI_SERVICE_API_KEY` identical in both Python services.
- [ ] `NEXT_PUBLIC_API_URL` points at prod backend (rebuild frontends after setting).
- [ ] `CORS_ORIGINS` includes every prod Vercel domain — else browser calls blocked.
- [ ] Google OAuth: prod redirect URI added in Google Cloud Console **and** `GOOGLE_REDIRECT_URI`.
- [ ] Login + signup flow works end-to-end against prod backend.
- [ ] AI chat stream (`/api/ai/chat/stream`) reaches orchestrator.

---

## 6. Architecture notes / gotchas

- **Build-time vs runtime env**: `NEXT_PUBLIC_*` is compiled into the JS bundle. Changing it requires a frontend **rebuild**, not just a restart.
- **Internal service URLs**: backend↔orchestrator talk over the host's private network. On Render use `fromService ... property: hostport`; on Railway use the private domain. Don't route service-to-service traffic through public URLs.
- **Migrations**: handled by `preDeployCommand` on both hosts. To run manually: shell into the service, `alembic upgrade head`.
- **Workers**: backend runs `uvicorn --workers 2`. Scale via host instance size, not by editing the Dockerfile.
- **Secrets hygiene**: never commit `.env`. `.env.example` is the source-of-truth template.
