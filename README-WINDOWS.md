# Running Event-AI on Windows

## Recommended: Docker Desktop (zero friction)

The entire stack runs identically on Windows via Docker Desktop + WSL2.
No Python, no Node, no uv, no pnpm needed on the host.

### Prerequisites

1. Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. Enable WSL2 backend in Docker Desktop → Settings → General → "Use WSL 2 based engine"
3. Copy `.env.example` to `.env` and fill in your secrets

### Start the full stack

```powershell
docker compose up --build
```

| Service        | URL                          |
|----------------|------------------------------|
| Backend API    | http://localhost:5000        |
| Vendor portal  | http://localhost:3002        |
| User portal    | http://localhost:3003        |
| Admin portal   | http://localhost:3004        |
| AI orchestrator| http://localhost:8000        |

### Stop

```powershell
docker compose down
```

---

## Alternative: Native Windows (WSL2 recommended)

If you want to run services natively (for faster hot-reload), use WSL2 with Ubuntu.
All commands in the project docs assume a Linux/macOS shell — they work identically
inside WSL2.

### Setup WSL2

```powershell
# In PowerShell (admin)
wsl --install -d Ubuntu
```

Then open the Ubuntu terminal and follow the standard Linux setup in the main README.

### Why not plain Windows CMD/PowerShell?

| Tool | Windows native | Notes |
|------|---------------|-------|
| pnpm | ✅ | Works fine |
| uv   | ✅ | Has Windows binaries |
| Node/Next.js | ✅ | Works fine |
| FastAPI/uvicorn | ✅ | Works fine |
| asyncpg | ⚠️ | Needs Visual C++ Build Tools if no wheel available |
| Shell scripts (`.sh`) | ❌ | Require Git Bash or WSL2 |

### Install prerequisites (native)

1. [Node.js 20+](https://nodejs.org/)
2. [pnpm](https://pnpm.io/installation#on-windows) — `corepack enable`
3. [uv](https://docs.astral.sh/uv/getting-started/installation/) — `winget install astral-sh.uv`
4. [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) — needed for asyncpg

### Run services natively

```powershell
# Install Node dependencies
pnpm install

# Backend (from packages/backend/)
uv sync
uv run uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload

# AI orchestrator (from packages/agentic_event_orchestrator/)
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend portals (from repo root)
pnpm dev:vendor   # http://localhost:3002
pnpm dev:user     # http://localhost:3003
pnpm dev:admin    # http://localhost:3004
```

---

## Cross-OS notes

- All `npm run` calls in the project have been replaced with `pnpm run` — no npm needed.
- The vendor portal dev cache uses `.next-dev/` (local folder) instead of `/tmp/` — works on all OSes.
- Python scripts use `asyncio` and standard library only — no Unix-specific syscalls.
- Alembic migrations use `DIRECT_URL` (Neon) — no local Postgres needed.
