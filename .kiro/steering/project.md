---
inclusion: always
---

# Event-AI Project Steering

## Commands

```bash
# Frontend portals (from repo root)
pnpm dev:vendor      # Vendor portal → http://localhost:3002
pnpm dev:user        # User portal → http://localhost:3003
pnpm dev:admin       # Admin portal → http://localhost:3004
pnpm dev             # All Node packages

# Backend — run from packages/backend
uv run uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload

# AI orchestrator — run from packages/agentic_event_orchestrator
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Database migrations — run from packages/backend
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "describe_change"

# Tests — run from packages/backend
uv run pytest

# Package managers
# Node → pnpm only (never npm)
# Python → uv only (never pip)
```

## Port Map

| Service | Port |
|---|---|
| Backend API | 5000 |
| Vendor portal | 3002 |
| User portal | 3003 |
| Admin portal | 3004 |
| AI orchestrator | 8000 |

## Package Names

| Directory | Package name |
|---|---|
| `packages/vendor` | `@event-ai/vendor` |
| `packages/user` | `@event-ai/user` |
| `packages/admin` | `@event-ai/admin` |
| `packages/backend` | `@event-ai/backend` |

## Auth (Non-Negotiable)

- All auth via `src/middleware/auth.middleware.py`
- Use `Depends(get_current_user)` on protected routes
- JWT in `Authorization: Bearer <token>` header
- **Banned:** NextAuth, Auth0, Clerk, Firebase Auth, localStorage JWT, sessionStorage JWT

## API Conventions

- Base URL: `/api/v1/<resource>`
- Response envelope: `{ "success": true, "data": {}, "meta": {} }`
- Error envelope: `{ "success": false, "error": { "code": "...", "message": "..." } }`

## Database

- `DIRECT_URL` for Alembic migrations (bypasses Neon pooler)
- `DATABASE_URL` (pooler) for runtime
- `asyncpg SSL`: use `connect_args={"ssl": "require"}` — not `?sslmode=require` in URL
- Every schema change needs a reversible Alembic migration

## Banned Practices

`NextAuth` · `Auth0` · `Clerk` · `Firebase Auth` · `localStorage JWT` · `sessionStorage JWT` · `sys.path.insert` · `nest_asyncio` · `npm` · `pip` · raw `os.environ` · LangChain for orchestration · real LLM/MCP calls in tests
