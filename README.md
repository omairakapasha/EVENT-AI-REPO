<div align="center">

# Event AI

**Plan any event in Pakistan by just talking to an AI.**

Tell Event-AI what you need a wedding venue, a caterer, a photographer and a team of AI agents finds the right vendors, compares them, and walks you through booking. No more juggling ten browser tabs and twenty WhatsApp chats.

[![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js&logoColor=white)](https://nextjs.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[Quick start](#quick-start) • [How it works](#how-it-works) • [Architecture](#architecture) • [API](#api) • [Contributing](#contributing)

</div>

## What is Event-AI?

Event planning is messy. You search for vendors in one place, message them somewhere else, track quotes in your notes app, and hope nobody double-books your date. Event-AI puts all of it in one place and adds an AI layer on top.

You chat with it in plain language. Behind the scenes, a pipeline of specialized agents handles the work:

- **Find** the right vendors using hybrid semantic search
- **Compare** them side by side
- **Book** and negotiate the price right inside the chat
- **Track** everything in real time across three dedicated portals

It's built for Pakistan first, but the architecture isn't tied to any one market.

## Quick start

You'll need Node 20+, pnpm 9+, Python 3.13+, [uv](https://docs.astral.sh/uv/), and (optionally) Docker.

**1. Clone and configure**

```bash
git clone https://github.com/omairakapasha/Event.git
cd Event
cp .env.example .env
```

Open `.env` and fill in the essentials:

```
DATABASE_URL=        # Neon Postgres pooled URL
DIRECT_URL=          # Neon Postgres direct URL (Alembic only)
JWT_SECRET_KEY=      # at least 32 characters
GEMINI_API_KEY=      # from Google AI Studio
GEMINI_MODEL=        # e.g. gemini/gemini-2.5-flash
THINKING_BUDGET=     # 0 turns off Gemini extended thinking (avoids chat timeouts)
GOOGLE_CLIENT_ID=    # Google OAuth2
GOOGLE_CLIENT_SECRET=
```

**2. Install everything**

```bash
pnpm install
cd packages/backend && uv sync && cd ../..
cd packages/agentic_event_orchestrator && uv sync && cd ../..
```

**3. Migrate the database and run**

```bash
cd packages/backend && uv run alembic upgrade head && cd ../..
docker compose up --build
```

Prefer to run services by hand? Open three terminals:

```bash
# Frontend portals
pnpm dev

# Backend API (port 5000)
cd packages/backend
uv run uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload

# AI orchestrator (port 8000)
cd packages/agentic_event_orchestrator
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Or use the shortcuts that boot the backend, the AI service, and a portal together:

```bash
pnpm dev:u    # + user portal
pnpm dev:v    # + vendor portal
pnpm dev:a    # + admin portal
pnpm dev:all  # + all three portals
```

## How it works

Every message enters through one front door: the `TriageAgent`. It reads your intent and hands the request to the right specialist. Those specialists pass work down the line until the job is done.

```
You: "I need a wedding venue in Lahore for 300 guests under 500k"
          │
          ▼
     TriageAgent ───────────────────────┐
          │                             │
          ▼                             ▼
  EventPlannerAgent           VendorDiscoveryAgent
                                        │
                                        ▼
                                  BookingAgent
                                        │
                                        ▼
                                OrchestratorAgent
                              (multi-step coordination)
```

Each agent is given a small set of typed tools  `vendor_tools`, `booking_tools`, `event_tools`, `notification_tools`, `mail_tools`. Searching and comparing vendors happens automatically in a single turn. Anything that spends money or changes a booking (placing it, countering an offer, cancelling) always waits for you to say "confirm" first.

### Negotiating a price

Booking isn't take-it-or-leave-it. Once a booking exists, you and the vendor can haggle before anyone commits:

```
pending → vendor sends a quote → quoted
quoted  → you send a counter   → negotiating
negotiating → vendor accepts   → accepted
accepted → you pay the deposit → awaiting_deposit → confirmed
```

Every step fires a domain event (`booking.quoted`, `booking.counter_offered`, `booking.accepted`, `booking.counter_rejected`) that fans out to in-app notifications and email, so nobody is left guessing.

## Architecture

Event-AI is a [Turborepo](https://turbo.build/repo) monorepo. Each package owns one job and stays out of the others' way.

```
event-ai/
├── packages/
│   ├── backend/                     # FastAPI REST API
│   ├── agentic_event_orchestrator/  # the AI agent service
│   ├── user/                        # user portal (Next.js 16)
│   ├── vendor/                      # vendor portal (Next.js 16)
│   ├── admin/                       # admin portal (Next.js 16)
│   └── ui/                          # shared component library
├── docker-compose.yml
└── turbo.json
```

### What runs where

| Service | Dev port | Docker port |
|---|---|---|
| Backend API | 5000 | 5000 |
| AI orchestrator | 8000 | 8000 |
| User portal | 3003 | 3000 |
| Vendor portal | 3002 | 3001 |
| Admin portal | 3004 | 3004 |

### The stack

| Layer | What we use |
|---|---|
| Backend | Python 3.13, FastAPI, SQLModel, asyncpg |
| Database | Postgres (Neon) with pgvector, Alembic for migrations |
| AI | OpenAI Agents SDK, Gemini through an OpenAI-compatible endpoint, Mem0 for memory |
| Frontend | Next.js 16, React 19, Tailwind CSS v4, React Query |
| Auth | Custom JWT (HS256), Google OAuth2, refresh-token rotation |
| Real-time | Server-Sent Events |
| Tooling | Turborepo, pnpm, uv, Docker, Ruff |

### A note on safety

The AI layer ships with guardrails on by default: a prompt-injection firewall that screens input before it reaches the model, a canary-token detector that catches prompt leaks in responses, and JWT rotation on the auth side. Booking actions need explicit user confirmation, so the agent can suggest but never spends your money on its own.

## API

Everything lives under `/api/v1/`.

| Prefix | What it does |
|---|---|
| `/auth` | Register, login, refresh, logout, Google OAuth |
| `/users` | User profiles |
| `/vendors` | Vendor CRUD, services, availability |
| `/public_vendors` | Public vendor discovery (no auth needed) |
| `/bookings` | The booking lifecycle |
| `/bookings/{id}/quotes`, `/quotes/*`, `/counter-offers/*` | Quotes and price negotiation |
| `/vendors/{id}/reviews` | Reviews and ratings |
| `/subscriptions` | AI subscription plans and usage |
| `/events` | Event planning |
| `/services`, `/categories` | Service listings and categories |
| `/inquiries` | Vendor inquiries |
| `/uploads` | File uploads |
| `/notifications` | Notifications and preferences |
| `/sse` | The real-time event stream |
| `/ai/chat`, `/ai/chat/stream` | AI chat, plain and streaming |
| `/ai/feedback`, `/ai/memory` | Message feedback and per-user memory |
| `/admin/*` | Stats, moderation, AI chat logs |

Every response uses the same shape, so clients never have to guess:

```json
{ "success": true, "data": {}, "meta": {} }
{ "success": false, "error": { "code": "ERROR_CODE", "message": "..." } }
```

## Testing

```bash
# Backend
cd packages/backend && uv run pytest

# AI orchestrator
cd packages/agentic_event_orchestrator && uv run pytest

# Frontend
pnpm typecheck && pnpm lint
```

Tests run against an in-memory SQLite database, so you don't need Docker or a live Postgres just to run the suite.

## Contributing

1. Branch off `develop`: `feature/<name>` or `hotfix/<name>`.
2. Write [Conventional Commits](https://www.conventionalcommits.org/): `feat(backend): ...`, `fix(user): ...`.
3. Make sure lint, typecheck, and pytest all pass.
4. Open your PR against `develop`, never straight into `main`.

## License

MIT © 2026 Event-AI Team
