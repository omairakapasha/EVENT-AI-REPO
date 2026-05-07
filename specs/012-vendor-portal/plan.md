# Implementation Plan: Vendor Portal

**Branch**: `feature/vendor-portal` | **Date**: 2026-04-07 | **Spec**: [specs/vendor-portal/spec.md](file:///home/ali/Desktop/Event-AI-Latest/specs/vendor-portal/spec.md)
**Input**: Feature specification from `/specs/vendor-portal/spec.md`

## Summary

The Vendor Portal is the primary interface for vendors to manage their business profiles, services, availability calendars, and booking pipelines. It standardizes the frontend onto Next.js 15 App Router using React Query and strict Zod validation, enforces JWT+RBAC auth on all endpoints, and triggers domain events to ensure semantic embeddings and notifications are kept up to date.

## Technical Context

**Language/Version**: Node.js ≥ 20 (Backend), React / Next.js 15 (Frontend)
**Primary Dependencies**: Fastify, Prisma, Zod, React Query, NextAuth.js, Tailwind CSS, shadcn/ui
**Storage**: Neon DB (PostgreSQL)
**Testing**: React Testing Library / Vitest (Frontend), Vitest (Backend)
**Target Platform**: Next.js browser portal
**Project Type**: Monorepo with web backend and web frontends
**Performance Goals**: Calendar and dashboard must load < 2 seconds.
**Constraints**: All server state managed by reacting to SSE and React Query cache invalidation.
**Scale/Scope**: Primary interface for Vendor side of the marketplace.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Next.js 15 App Router**: App router explicitly used; no legacy pages router.
- [x] **TanStack React Query**: State management avoids raw generic hooks.
- [x] **RBAC / Auth Middleware**: Routes secured via server-enforced JWT and specific roles.
- [x] **Emits Domain Events**: Vendor portal backend routes strictly emit facts, avoiding synchronous logic hooks.

## Project Structure

### Documentation

```text
specs/vendor-portal/
├── plan.md              # This file
├── spec.md              # Feature specification
└── verification.md      # Testing and verification sign-off
```

### Source Code Context

```text
packages/backend/
├── src/
│   ├── routes/
│   │   ├── vendor.routes.ts          # Extends dashboard and availability
│   │   └── services.routes.ts        # [NEW] Endpoints to manage vendor services

packages/vendor/
├── src/
│   ├── app/                          # Next.js App router
│   │   ├── dashboard/page.tsx        
│   │   ├── availability/page.tsx     
│   │   ├── bookings/page.tsx         
│   │   ├── profile/page.tsx          
│   │   ├── services/page.tsx         
│   │   └── earnings/page.tsx         # [NEW] Track completed revenue
│   ├── components/                   # specific vendor feature components
│   └── lib/
│       └── api/                      # generic react query fetchers
```

## Phase 1: API Enhancement & RBAC (Backend)

**Context**: Vendor routes currently cover dashboard and basic availability. They need to expand to full profile CRUD, services, and earnings.

**Tasks**:
1. Ensure all `vendor.routes.ts` routes use `authMiddleware` and `requirePermission()`.
2. Expand `/profile` endpoints to handle full vendor CRUD, ensuring `vendor.updated` domain events are emitted to the EventBus.
3. Build the `/earnings` endpoint calculating total revenue based strictly on bookings where `status='completed'`.
4. Ensure Zod validation boundaries are in place for all inputs.

## Phase 2: Booking Management & Real-Time Sync

**Context**: Vendors need a calendar UI to process bookings (`pending -> confirmed -> in_progress -> completed`).

**Tasks**:
1. Frontend `bookings/page.tsx` needs a React Query hook to fetch pending and confirmed bookings.
2. Build UI mutation buttons mapping to `PATCH /api/v1/bookings/:id/status`.
3. Integrate SSE context from `EventBusService` so the UI instantly invalidates the query cache when a `booking.created` or `booking.status_changed` event occurs.

## Phase 3: Profile & Service Management

**Context**: Core business data entry. 

**Tasks**:
1. Build `profile/page.tsx` using `react-hook-form` and `zod` resolver. Add logo upload field.
2. Build `services/page.tsx` and `services/new/page.tsx`. Allow specifying Category, Description, and attaching Pricing tiers.
3. Incorporate previously functioning CSV bulk price uploads visually.

## Phase 4: Earnings & Availability 

**Context**: Managing capacity and tracking returns.

**Tasks**:
1. Integrate the `BigCalendar` or similar component in `availability/page.tsx` for visual drag-and-block timeline.
2. Build `earnings/page.tsx` extracting stats from the backend earnings route. Provide simple bar charts for monthly breakdown using `recharts` or shadcn standard charts.

## Phase 5: Testing

**Tasks**:
1. Use React Testing Library to write tests for the complex `react-hook-form` interactions on Profile and Services pages.
2. Verify backend RBAC enforcement via simulated non-vendor auth tokens in Integration test suite.
