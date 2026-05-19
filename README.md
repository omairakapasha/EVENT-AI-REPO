<div align="center">

# Event-AI

**AI-native event planning marketplace for Pakistan**

Connect users with verified vendors through intelligent multi-agent orchestration, semantic search, and real-time coordination.

[![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js&logoColor=white)](https://nextjs.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[Overview](#overview) · [Quick Start](#quick-start) · [Architecture](#architecture) · [API Reference](#api-reference) · [Contributing](#contributing)

</div>

---

## Overview

Event-AI is a full-stack marketplace that makes event planning in Pakistan fast, intelligent, and transparent. Users describe what they need — a wedding venue, a catering team, a photographer — and an AI agent pipeline handles discovery, comparison, and booking coordination end-to-end.

**What makes it different:**

- A **multi-agent AI system** (Triage → Planner → Discovery → Booking) that understands intent and acts on it
- **Hybrid semantic search** combining pgvector similarity with trigram keyword matching for precise vendor discovery
- **Three specialized portals** — one each for users, vendors, and platform administrators
- **Production-grade security** — 7-layer prompt injection firewall, canary token leak detection, JWT rotation

---

## Quick Start

### Prerequisites

| Tool | Version |
|---|---|
| Node.js | ≥ 20 |
| pnpm | ≥ 9 |
| Python | ≥ 3.13 |
| [uv](https://docs.astral.sh/uv/) | latest |
| Docker | optional |

### 1. Clone and configure

```bash
git clone https://github.com/your-org/event-ai.git
cd event-ai
cp .env.example .env
```

Edit `.env` and fill in:

```
DATABASE_URL=        # Neon PostgreSQL pooled URL
DIRECT_URL=          # Neon PostgreSQL direct URL (Alembic only)
JWT_SECRET_KEY=      # min 32 chars
GEMINI_API_KEY=      # from Google AI Studio
GEMINI_MODEL=        # e.g. gemini-2.5-flash-lite
GOOGLE_CLIENT_ID=    # Google OAuth2
GOOGLE_CLIENT_SECRET=
```

### 2. Install

```bash
pnpm install
cd packages/backend && uv sync && cd ../..
cd packages/agentic_event_orchestrator && uv sync && cd ../..
```

### 3. Migrate and run

```bash
# Apply database migrations
cd packages/backend && uv run alembic upgrade head && cd ../..

# Start everything
docker compose up --build
```

Or run services individually:

```bash
# Terminal 1 — Frontend portals
pnpm dev

# Terminal 2 — Backend API (port 5000)
cd packages/backend
uv run uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload

# Terminal 3 — AI Orchestrator (port 8000)
cd packages/agentic_event_orchestrator
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Architecture

Event-AI is a **Turborepo monorepo** with clear package boundaries:

```
event-ai/
├── packages/
│   ├── backend/                     # FastAPI REST API
│   ├── agentic_event_orchestrator/  # AI agent service
│   ├── user/                        # User portal — Next.js 16
│   ├── vendor/                      # Vendor portal — Next.js 16
│   ├── admin/                       # Admin portal — Next.js 16
│   └── ui/                          # Shared component library
├── docker-compose.yml
└── turbo.json
```

### Service ports

| Service | Dev | Docker |
|---|---|---|
| Backend API | 5000 | 5000 |
| AI Orchestrator | 8000 | 8000 |
| User Portal | 3003 | 3000 |
| Vendor Portal | 3002 | 3001 |
| Admin Portal | 3004 | 3004 |

### AI agent pipeline

All requests enter through a single `TriageAgent` and are routed to specialist agents:

```
User message
      │
      ▼
 TriageAgent ──────────────────────────────┐
      │                                    │
      ▼                                    ▼
 EventPlannerAgent              VendorDiscoveryAgent
                                          │
                                          ▼
                                    BookingAgent
                                          │
                                          ▼
                                  OrchestratorAgent
                               (multi-step coordination)
```

Each agent has access to typed function tools: `vendor_tools`, `booking_tools`, `event_tools`, `notification_tools`, `mail_tools`.

### Tech stack

| Layer | Stack |
|---|---|
| Backend | Python 3.13, FastAPI, SQLModel, asyncpg |
| Database | PostgreSQL (Neon) + pgvector, Alembic |
| AI | OpenAI Agents SDK, Gemini via OpenAI-compatible endpoint, Mem0 |
| Frontend | Next.js 16, React 19, Tailwind CSS v4, React Query |
| Auth | Custom JWT (HS256), Google OAuth2, refresh token rotation |
| Real-time | Server-Sent Events (SSE) |
| Tooling | Turborepo, pnpm, uv, Docker, Ruff |

---

## API Reference

All backend routes are versioned under `/api/v1/`.

| Prefix | Description |
|---|---|
| `/api/v1/auth` | Register, login, refresh, logout, Google OAuth |
| `/api/v1/users` | User profile |
| `/api/v1/vendors` | Vendor CRUD, services, availability |
| `/api/v1/public_vendors` | Public vendor discovery (no auth) |
| `/api/v1/bookings` | Booking lifecycle |
| `/api/v1/events` | Event management |
| `/api/v1/services` | Vendor service listings |
| `/api/v1/categories` | Service categories |
| `/api/v1/inquiries` | Vendor inquiries |
| `/api/v1/uploads` | File uploads |
| `/api/v1/notifications` | Notifications + preferences |
| `/api/v1/sse` | Real-time event stream |
| `/api/v1/admin/*` | Platform stats, moderation, AI chat logs |
| `/api/v1/ai/chat` | AI chat — non-streaming |
| `/api/v1/ai/chat/stream` | AI chat — SSE streaming |
| `/api/v1/ai/feedback` | Message feedback |
| `/api/v1/ai/memory` | Per-user persistent memory |

**Response envelope:**

```json
{ "success": true, "data": {}, "meta": {} }
{ "success": false, "error": { "code": "ERROR_CODE", "message": "..." } }
```

---

## Testing

```bash
# Backend
cd packages/backend
uv run pytest

# AI orchestrator
cd packages/agentic_event_orchestrator
uv run pytest

# Frontend
pnpm typecheck
pnpm lint
```

Tests run against an in-memory SQLite database — no external services required.

---

## Contributing

1. Branch from `develop`: `feature/<name>` or `hotfix/<name>`
2. Follow [Conventional Commits](https://www.conventionalcommits.org/): `feat(backend): ...`, `fix(user): ...`
3. All CI checks must pass before merge (lint, typecheck, pytest)
4. PRs target `develop`, never `main`

---

## License

MIT © 2026 Event-AI Team
