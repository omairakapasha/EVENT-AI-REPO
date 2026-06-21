# Event-AI Deployment Summary

## 🎉 Successfully Deployed!

### Live URLs

#### Frontend Applications (Vercel)
- **User Portal:** https://event-user.vercel.app
- **Vendor Portal:** https://event-vendor-two.vercel.app  
- **Admin Portal:** https://event-admin-umber.vercel.app

#### Backend Services (Render)
- **Backend API:** https://eventai-backend-upym.onrender.com
- **AI Orchestrator:** https://eventai-orchestrator.onrender.com

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND LAYER                        │
│                        (Vercel)                              │
├───────────────┬───────────────┬───────────────────────────┐
│  User Portal  │ Vendor Portal │      Admin Portal          │
│  (Next.js)    │  (Next.js)    │      (Next.js)             │
└───────┬───────┴───────┬───────┴───────────┬────────────────┘
        │               │                   │
        └───────────────┼───────────────────┘
                        │ HTTPS/REST API
        ┌───────────────┴───────────────────────┐
        │         BACKEND LAYER (Render)         │
        ├──────────────────┬─────────────────────┤
        │  Backend API     │  AI Orchestrator    │
        │  (FastAPI)       │  (FastAPI)          │
        └────────┬─────────┴──────────┬──────────┘
                 │                    │
        ┌────────┴────────────────────┴──────────┐
        │         DATA LAYER                      │
        ├────────────────┬────────────────────────┤
        │  PostgreSQL    │      Redis             │
        │  (Neon)        │      (Render)          │
        │  + pgvector    │                        │
        └────────────────┴────────────────────────┘
                 │
        ┌────────┴────────────────────────────────┐
        │      EXTERNAL SERVICES                   │
        ├──────────────────────────────────────────┤
        │  • Cloudflare R2 (Object Storage)        │
        │  • Gemini AI (LLM)                       │
        │  • Mem0 (AI Memory)                      │
        │  • Brevo (Email/SMTP)                    │
        │  • Google OAuth 2.0                      │
        │  • Twilio (SMS - Optional)               │
        └──────────────────────────────────────────┘
```

---

## Tech Stack Summary

### Frontend
- **Framework:** Next.js 16 (React 19)
- **Styling:** Tailwind CSS v4
- **UI Components:** shadcn/ui
- **State Management:** React Query
- **Type Safety:** TypeScript (strict mode)
- **Hosting:** Vercel (free tier)

### Backend
- **Language:** Python 3.13
- **Framework:** FastAPI
- **ORM:** SQLModel + SQLAlchemy
- **Async Runtime:** asyncio + asyncpg
- **Database:** PostgreSQL (Neon) + pgvector
- **Cache:** Redis (Render Key-Value)
- **Migrations:** Alembic
- **Authentication:** Custom JWT + Google OAuth 2.0
- **Logging:** Structlog
- **Hosting:** Render (free tier)

### AI Layer
- **Framework:** OpenAI Agents SDK
- **LLM:** Gemini 2.5 Flash (via LiteLLM)
- **RAG:** LangChain (Agentic RAG only)
- **Memory:** Mem0 (persistent per-user memory)
- **Vector Search:** pgvector (768-dim embeddings)
- **Hosting:** Render (free tier)

### Infrastructure
- **Monorepo:** Turborepo + pnpm workspaces
- **CI/CD:** GitHub Actions
- **Containerization:** Docker (multi-stage builds)
- **Package Manager (Python):** uv
- **Package Manager (JS):** pnpm

---

## Environment Configuration

### Production Environment Variables

#### Backend (`eventai-backend`)
- `DATABASE_URL` - Neon pooled connection
- `DIRECT_URL` - Neon direct connection (Alembic)
- `REDIS_URL` - Auto-injected by Render
- `AI_SERVICE_URL` - Auto-configured
- `CORS_ORIGINS` - All 3 Vercel URLs
- `FRONTEND_URL` - User portal URL
- `GOOGLE_REDIRECT_URI` - Backend callback URL
- OAuth, SMTP, R2 credentials

#### AI Orchestrator (`eventai-orchestrator`)
- `DATABASE_URL` / `APP_DATABASE_URL` - Same Neon DB
- `REDIS_URL` - Auto-injected
- `BACKEND_API_URL` - Auto-configured
- `GEMINI_API_KEY`, `MEM0_API_KEY`

#### Frontends (all 3 Vercel projects)
- `NEXT_PUBLIC_API_URL` - Points to backend API

---

## Key Features Deployed

### For Users
- ✅ AI-powered event planning chat
- ✅ Vendor search (semantic + keyword hybrid)
- ✅ Booking management with price negotiation
- ✅ Real-time notifications (SSE)
- ✅ Google OAuth login
- ✅ Email verification

### For Vendors
- ✅ Service management
- ✅ Availability calendar
- ✅ Booking requests handling
- ✅ Quote negotiation
- ✅ Review management

### For Admins
- ✅ Vendor moderation & approval
- ✅ User management
- ✅ Platform analytics
- ✅ AI chat logs & feedback
- ✅ Embedding backfill triggers

---

## Database Schema Highlights

**Core Tables:**
- `users` - Authentication, profiles, roles
- `vendors` - Business listings, ratings
- `services` - Vendor offerings
- `bookings` - Full lifecycle with state machine
- `events` - User event planning
- `domain_events` - Event sourcing (append-only)
- `vendor_embeddings` - Vector search (pgvector)

**AI Tables (`ai.*`):**
- `chat_sessions` - User chat history
- `messages` - Individual messages
- `agent_executions` - Agent run logs
- `message_feedback` - User feedback

---

## Performance & Scalability

### Free Tier Limitations
- **Render:** Services sleep after 15 min idle, 30-60s cold start
- **Neon:** 0.5 GB storage, shared compute
- **Vercel:** 100 GB bandwidth/month
- **Good for:** Portfolio showcase, demos, MVPs
- **Not suitable for:** High-traffic production

### Upgrade Path
- Render: $7/month per service (no sleep)
- Neon: $19/month (dedicated compute)
- Vercel: $20/month per project (team features)

---

## Security Features

- ✅ JWT with refresh token rotation
- ✅ Rate limiting on all endpoints
- ✅ Prompt injection firewall (AI layer)
- ✅ Input validation (Pydantic)
- ✅ CORS protection
- ✅ HTTPS everywhere
- ✅ Secrets via environment variables
- ✅ Security headers middleware

---

## Monitoring & Debugging

### Health Endpoints
- Backend: `/api/v1/health`
- Orchestrator: `/health`

### Logs
- Render: Built-in log viewer per service
- Vercel: Real-time function logs

### Error Tracking
- FastAPI: Structured logging (structlog)
- Next.js: Console + Vercel logs

---

## Resume Bullet Points

**Suggested Resume Entry:**

**Event-AI Platform** | Full-Stack AI Developer | Jun 2026
- Architected and deployed an AI-powered event planning marketplace serving users, vendors, and admins across 5 microservices
- Built multi-agent AI pipeline using OpenAI Agents SDK + Gemini 2.5 Flash with agentic RAG for semantic vendor discovery
- Implemented real-time notification system using Server-Sent Events (SSE) with per-user event queues
- Designed event-driven architecture with PostgreSQL event sourcing, enabling full audit trails and async workflows
- Integrated pgvector for hybrid semantic + keyword search across 768-dimensional embeddings
- Deployed on Vercel (3 Next.js frontends) + Render (2 FastAPI services) with Docker containerization
- Tech: Next.js 16, FastAPI, PostgreSQL + pgvector, Redis, Gemini AI, Turborepo, TypeScript, Python 3.13

**Key Metrics:**
- 5 independently deployable services
- 3 role-based portals (user, vendor, admin)
- 40+ API endpoints
- Multi-agent AI orchestration with 5 specialist agents
- Hybrid search combining semantic + trigram matching

---

## Next Steps (Post-Deployment)

### Optional Enhancements
1. **Custom Domain:** Buy domain + point to Vercel/Render
2. **Database Seeding:** Add realistic vendor data
3. **Demo Accounts:** Create test users for recruiters
4. **Monitoring:** Add Sentry for error tracking
5. **Analytics:** Google Analytics or Vercel Analytics
6. **CI/CD:** Expand GitHub Actions for automated testing
7. **Documentation:** OpenAPI/Swagger docs for API

### Known Limitations (Free Tier)
- Cold start delay on first request after 15 min idle
- Limited concurrent connections
- No autoscaling
- Basic monitoring/metrics

---

## Useful Commands

### Local Development
```bash
pnpm dev:all     # All services
pnpm dev:u       # Backend + AI + User portal
pnpm dev:v       # Backend + AI + Vendor portal
pnpm dev:a       # Backend + AI + Admin portal
```

### Database
```bash
pnpm db:migrate  # Run migrations
pnpm db:studio   # Open DB GUI
```

### Deployments
- **Render:** Auto-deploys on push to `main`
- **Vercel:** Auto-deploys on push to `main`

---

## Support & Resources

- **Repository:** https://github.com/omairakapasha/Event
- **Render Dashboard:** https://dashboard.render.com
- **Vercel Dashboard:** https://vercel.com/dashboard
- **Neon Console:** https://console.neon.tech

---

**Deployed:** June 21, 2026  
**Commit:** df69317  
**Status:** ✅ Production Ready
