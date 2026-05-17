<p align="center">
  <h1 align="center">Event-AI</h1>
  <p align="center">Intelligent Event Planning Marketplace for Pakistan</p>
  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.13+-blue?logo=python&logoColor=white" alt="Python 3.13" />
    <img src="https://img.shields.io/badge/FastAPI-0.135-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/Next.js-16-black?logo=next.js&logoColor=white" alt="Next.js 16" />
    <img src="https://img.shields.io/badge/PostgreSQL-pgvector-336791?logo=postgresql&logoColor=white" alt="PostgreSQL" />
    <img src="https://img.shields.io/badge/pnpm-9.0.0-F69220?logo=pnpm&logoColor=white" alt="pnpm" />
    <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker" />
  </p>
</p>

---

## 🌟 Overview

**Event-AI** is a sophisticated, AI-native marketplace platform designed to revolutionize event planning in Pakistan. It connects users with verified vendors for weddings, corporate events, and parties through a multi-agent AI system and semantic search capabilities.

Built as a high-performance monorepo, the platform features a robust FastAPI backend, an advanced AI orchestrator, and three specialized Next.js portals for users, vendors, and administrators.

---

## 🏗️ Architecture

The project is organized as a **Turborepo** monorepo, separating concerns across specialized packages:

```text
C:\Users\omair\OneDrive\Desktop\Event\
├── packages/
│   ├── backend/                     # FastAPI REST API (Auth, Bookings, Events)
│   ├── agentic_event_orchestrator/  # AI Agent Service (Triage, Planning, Discovery)
│   ├── user/                        # User Portal (Next.js 16) — AI Chat & Discovery
│   ├── vendor/                      # Vendor Portal (Next.js 16) — Booking & Service Mgmt
│   ├── admin/                       # Admin Portal (Next.js 16) — Platform Moderation
│   └── ui/                          # Shared Design System (Tailwind v4)
├── infra/                           # Docker and Nginx configurations
├── specs/                           # Technical specifications and architectural docs
└── docker-compose.yml               # Full-stack orchestration
```

### Port Map

| Service | Dev Port | Docker Port |
|---------|----------|-------------|
| **Backend API** | 5000 | 5000 |
| **AI Orchestrator** | 8000 | 8000 |
| **User Portal** | 3003 | 3000 |
| **Vendor Portal** | 3002 | 3001 |
| **Admin Portal** | 3004 | 3004 |

---

## 🛠️ Tech Stack

- **Backend:** Python 3.13, FastAPI, SQLModel, PostgreSQL (Neon) + `pgvector`.
- **AI Service:** OpenAI Agents SDK, Gemini (via OpenAI-compatible endpoint), Mem0.
- **Frontend:** Next.js 16, React 19, Tailwind CSS v4, React Query, SSE.
- **Infrastructure:** Turborepo, pnpm, Docker, uv (Python pkg mgr).
- **Security:** 7-layer Prompt Firewall, JWT Rotation, Google OAuth2, PII Redaction.

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** >= 20.0.0
- **pnpm** >= 9.0.0
- **Python** >= 3.13
- **uv** (for Python dependency management)
- **Docker** & **Docker Compose**

### 1. Environment Setup

Copy `.env.example` to `.env` in the root and fill in the required keys:

```bash
# Root directory
cp .env.example .env
```

Key variables needed: `DATABASE_URL`, `JWT_SECRET_KEY`, `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.

### 2. Installation

Install Node and Python dependencies:

```bash
# Install Node dependencies
pnpm install

# Install Python dependencies (Backend)
cd packages/backend && uv sync && cd ../..

# Install Python dependencies (AI Service)
cd packages/agentic_event_orchestrator && uv sync && cd ../..
```

### 3. Database & Migrations

```bash
# Start local database (optional if using Neon)
pnpm db:up

# Run migrations
pnpm db:migrate:dev
```

### 4. Running the Project

**Using Docker (Recommended):**
```bash
docker compose up --build
```

**Native Development:**
```bash
# Run all portals (User, Vendor, Admin)
pnpm dev

# Run Backend (in a separate terminal)
cd packages/backend
uv run uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload

# Run AI Orchestrator (in a separate terminal)
cd packages/agentic_event_orchestrator
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🧩 Key Features

- **Multi-Agent AI Orchestrator:** Intelligent agents (Triage, Planner, Discovery, Booking) that collaborate to fulfill user requests.
- **Hybrid Semantic Search:** Combines Trigram keyword search with `pgvector` similarity search for highly relevant vendor discovery.
- **Real-time Notifications:** SSE-powered live updates for bookings, status changes, and messages.
- **Advanced Security:** Production-grade 7-layer prompt injection firewall and output leak detection.
- **Vendor Workflow:** Complete lifecycle management from registration and approval to service listing and booking confirmation.
- **Admin Insights:** Comprehensive dashboard for platform statistics, user management, and vendor moderation.

---

## 🧪 Testing

The project maintains a high test coverage across backend and frontend:

```bash
# Backend Tests (FastAPI)
cd packages/backend
uv run pytest

# Frontend Typecheck
pnpm typecheck

# Linting
pnpm lint
```

---

## 📖 Documentation

- [Project Status](PROJECT_STATUS.md) - Detailed current build progress.
- [AI System](packages/agentic_event_orchestrator/README.md) - Deep dive into agent architecture.
- [Windows Guide](README-WINDOWS.md) - Setup instructions for Windows users.

---

## 📄 License

MIT © 2026 Event-AI Team
