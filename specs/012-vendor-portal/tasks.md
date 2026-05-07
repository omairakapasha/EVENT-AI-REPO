# Tasks: Vendor Portal

**Input**: Design documents from `/specs/012-vendor-portal/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Component test coverage ≥ 60% — explicitly required by spec (SC-007). Backend RBAC integration tests required.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., [US1], [US2], …, [US7])
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `packages/backend/src/`
- **Frontend**: `packages/vendor/src/`
- **Database**: `packages/backend/prisma/`
- Paths below reflect the monorepo structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify existing models, add any missing schema fields, and ensure environment/config readiness for the vendor portal feature.

- [ ] T001 [P] Verify Prisma schema has all required Vendor fields (status enum includes SUSPENDED, logoUrl, keywords, serviceAreas, tier, rating) in packages/backend/prisma/schema.prisma
- [ ] T002 [P] Verify VendorAvailability model has composite unique key (vendorId + date + serviceId) and status enum (available/blocked) in packages/backend/prisma/schema.prisma
- [ ] T003 [P] Verify PriceHistory model has oldPrice, newPrice, changeReason, changedAt fields in packages/backend/prisma/schema.prisma
- [ ] T004 [P] Verify PriceUpload model has total, processed, failed, errorLog fields in packages/backend/prisma/schema.prisma
- [ ] T005 [P] Verify BookingMessage model has senderType enum (vendor/client/system) in packages/backend/prisma/schema.prisma
- [ ] T006 Create database migration for any schema additions from T001–T005 (if needed)
- [ ] T007 [P] Add any missing environment variables (SSE/WebSocket config, CSV upload limits) in packages/backend/.env.example

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend RBAC hardening and shared service layer that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T008 Ensure all vendor.routes.ts endpoints use authMiddleware + requirePermission('vendor:read'|'vendor:write') in packages/backend/src/routes/vendor.routes.ts
- [ ] T009 [P] Ensure all services.routes.ts endpoints use authMiddleware + requirePermission('vendor:write') in packages/backend/src/routes/services.routes.ts
- [ ] T010 [P] Ensure pricing.routes.ts endpoints use authMiddleware + requirePermission('pricing:read'|'pricing:write') in packages/backend/src/routes/pricing.routes.ts
- [ ] T011 [P] Ensure bookings.routes.ts vendor-facing endpoints use authMiddleware + requirePermission('vendor:read'|'vendor:write') in packages/backend/src/routes/bookings.routes.ts
- [ ] T012 [P] Add Zod schemas for vendor profile update (name, description, contact, logoUrl, serviceAreas, keywords, category) in packages/backend/src/schemas/index.ts
- [ ] T013 [P] Add Zod schemas for availability management (date range, status enum) in packages/backend/src/schemas/index.ts
- [ ] T014 [P] Add Zod schemas for earnings query (dateFrom, dateTo, page, limit) in packages/backend/src/schemas/index.ts
- [ ] T015 [P] Verify SSE / EventBus infrastructure exists for real-time push to vendor frontends via packages/backend/src/services/event-bus.service.ts

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — Vendor Profile Management (Priority: P1) 🎯 MVP

**Goal**: Vendors can manage their full business profile — name, description, contact, logo, service areas, keywords, and category

**Independent Test**: Log in as a vendor, update business description and keywords, verify changes persist on refresh and a `vendor.updated` domain event is emitted.

### Backend Implementation for US1

- [ ] T016 [US1] Expand PUT /api/v1/vendor/profile endpoint with full CRUD (name, description, contact, logo, serviceAreas, keywords, category) in packages/backend/src/routes/vendor.routes.ts
- [ ] T017 [US1] Emit `vendor.updated` domain event on profile update via EventBus in packages/backend/src/routes/vendor.routes.ts
- [ ] T018 [US1] Add logo upload endpoint (POST /api/v1/vendor/profile/logo) using CDN service pre-signed URLs in packages/backend/src/routes/vendor.routes.ts
- [ ] T019 [P] [US1] Enforce vendor status check — return HTTP 403 if vendor.status === 'SUSPENDED' in vendor profile routes
- [ ] T020 [US1] Add input validation: required fields, email/phone format, URL validation, length limits per Zod schemas
- [ ] T021 [P] [US1] Add audit logging for vendor profile changes using existing AuditLog model

### Frontend Implementation for US1

- [ ] T022 [P] [US1] Build profile page form using react-hook-form + zod resolver in packages/vendor/src/app/profile/page.tsx
- [ ] T023 [US1] Integrate React Query mutation for profile update with cache invalidation in packages/vendor/src/app/profile/page.tsx
- [ ] T024 [US1] Add logo upload UI with preview and progress indicator in packages/vendor/src/app/profile/page.tsx
- [ ] T025 [P] [US1] Add form validation error display with descriptive messages

**Checkpoint**: Vendor Profile Management is fully testable independently

---

## Phase 4: User Story 2 — Service & Pricing Management (Priority: P1) 🎯 MVP

**Goal**: Vendors can create, edit, and deactivate services with pricing tiers, and bulk-upload prices via CSV

**Independent Test**: Create a service with a pricing tier, verify it appears in the vendor's service list and is bookable.

### Backend Implementation for US2

- [ ] T026 [P] [US2] Add Zod schema for service create/update (category, description, capacity, unitType, isActive) in packages/backend/src/schemas/index.ts
- [ ] T027 [US2] Verify service CRUD endpoints (POST/GET/PUT/DELETE /api/v1/vendor/services) in packages/backend/src/routes/services.routes.ts
- [ ] T028 [US2] Implement pricing tier CRUD within services (POST/PUT/DELETE /api/v1/vendor/services/:id/pricing) in packages/backend/src/routes/pricing.routes.ts
- [ ] T029 [US2] Create PriceHistory record on pricing update (old/new price, changeReason) in pricing routes
- [ ] T030 [US2] Implement CSV bulk price upload endpoint (POST /api/v1/vendor/pricing/upload) with PriceUpload tracking (total/processed/failed/errorLog) in packages/backend/src/routes/pricing.routes.ts
- [ ] T031 [US2] On service deactivation (isActive=false), verify service excluded from user search but existing bookings remain intact

### Frontend Implementation for US2

- [ ] T032 [P] [US2] Build service list page with active/inactive filter in packages/vendor/src/app/services/page.tsx
- [ ] T033 [US2] Build service create/edit form with pricing tier management in packages/vendor/src/app/services/new/page.tsx and packages/vendor/src/app/services/[id]/page.tsx
- [ ] T034 [US2] Integrate React Query hooks for service CRUD with cache invalidation
- [ ] T035 [US2] Build CSV bulk upload UI with progress and error report display in packages/vendor/src/app/pricing/page.tsx

**Checkpoint**: Service & Pricing Management is fully testable independently

---

## Phase 5: User Story 3 — Booking Calendar & Management (Priority: P1) 🎯 MVP

**Goal**: Vendors view bookings in a calendar, filter by status, and confirm/reject/progress bookings

**Independent Test**: Navigate to bookings page, verify pending bookings appear, confirm one, verify calendar updates status.

### Backend Implementation for US3

- [ ] T036 [US3] Implement vendor booking list endpoint (GET /api/v1/vendor/bookings) with date range and status filters, pagination in packages/backend/src/routes/bookings.routes.ts
- [ ] T037 [US3] Implement booking status transition endpoint (PATCH /api/v1/vendor/bookings/:id/status) supporting: pending → confirmed → in_progress → completed, and pending → rejected in packages/backend/src/routes/bookings.routes.ts
- [ ] T038 [US3] Emit domain events on booking status changes (booking.confirmed, booking.rejected, booking.completed) via EventBus
- [ ] T039 [US3] Set confirmedAt, confirmedBy fields on booking confirmation
- [ ] T040 [US3] Release availability slot on booking rejection
- [ ] T041 [US3] Add conflict detection — flag if vendor has another confirmed booking for the same service on the same date

### Frontend Implementation for US3

- [ ] T042 [P] [US3] Build booking calendar view (BigCalendar or equivalent) with status color indicators in packages/vendor/src/app/bookings/page.tsx
- [ ] T043 [US3] Add confirm/reject/progress action buttons with confirmation modals (reject requires reason)
- [ ] T044 [US3] Integrate React Query hooks for booking list with cache invalidation on mutations
- [ ] T045 [US3] Integrate SSE subscription via EventBus — auto invalidate React Query cache on booking.created / booking.status_changed events for real-time calendar updates
- [ ] T046 [US3] Display conflict indicators on calendar dates with overlapping confirmed bookings

**Checkpoint**: Booking Calendar & Management is fully testable independently

---

## Phase 6: User Story 4 — Availability Management (Priority: P1) 🎯 MVP

**Goal**: Vendors block/unblock specific dates, preventing users from booking blocked dates

**Independent Test**: Block a date via the availability page, then attempt to book on that date and verify rejection.

### Backend Implementation for US4

- [ ] T047 [US4] Implement availability block endpoint (POST /api/v1/vendor/availability/block) creating VendorAvailability records with status='blocked' for date ranges in packages/backend/src/routes/vendor.routes.ts
- [ ] T048 [US4] Implement availability unblock endpoint (DELETE /api/v1/vendor/availability/block) setting status back to 'available' in packages/backend/src/routes/vendor.routes.ts
- [ ] T049 [US4] Implement availability check endpoint (GET /api/v1/vendor/availability) returning per-date status for a given range
- [ ] T050 [US4] Ensure booking creation validates against VendorAvailability — reject with { available: false, reason: "Vendor not available on this date" } if date is blocked

### Frontend Implementation for US4

- [ ] T051 [P] [US4] Build availability calendar page with drag-and-block UI (BigCalendar or similar) in packages/vendor/src/app/availability/page.tsx
- [ ] T052 [US4] Integrate React Query hooks for availability CRUD with cache invalidation
- [ ] T053 [US4] Display blocked dates visually (distinct color/pattern) on the calendar

**Checkpoint**: Availability Management is fully testable independently

---

## Phase 7: User Story 5 — Earnings Dashboard (Priority: P2)

**Goal**: Vendors view total revenue, monthly breakdown, and per-booking earnings from completed bookings

**Independent Test**: Complete 3 bookings with different prices, navigate to earnings, verify total matches sum of completed booking prices.

### Backend Implementation for US5

- [ ] T054 [US5] Implement earnings summary endpoint (GET /api/v1/vendor/earnings) calculating total revenue (SUM of totalPrice WHERE status='completed'), monthly breakdown (grouped by eventDate month), and completed booking count in packages/backend/src/routes/vendor.routes.ts
- [ ] T055 [US5] Add time period filter (thisMonth, last3Months, thisYear, custom dateRange) to earnings endpoint
- [ ] T056 [US5] Implement per-booking earnings detail with pagination (GET /api/v1/vendor/earnings/bookings)

### Frontend Implementation for US5

- [ ] T057 [P] [US5] Build earnings dashboard page with total revenue, booking count, and empty state in packages/vendor/src/app/earnings/page.tsx
- [ ] T058 [US5] Add monthly bar chart using recharts or shadcn charts in earnings page
- [ ] T059 [US5] Add time period filter selector (this month, last 3 months, this year)
- [ ] T060 [US5] Integrate React Query hooks for earnings data with cache invalidation

**Checkpoint**: Earnings Dashboard is fully testable independently

---

## Phase 8: User Story 6 — Vendor Dashboard Overview (Priority: P2)

**Goal**: Quick summary: total/active services, total/pending bookings, recent activity log

**Independent Test**: Log in as vendor, verify dashboard displays correct counts and recent audit log entries.

### Backend Implementation for US6

- [ ] T061 [US6] Implement dashboard summary endpoint (GET /api/v1/vendor/dashboard) returning totalServices, activeServices, totalBookings, pendingBookings in packages/backend/src/routes/vendor.routes.ts
- [ ] T062 [US6] Include last 10 AuditLog entries (action, timestamp, entityType) in dashboard response

### Frontend Implementation for US6

- [ ] T063 [P] [US6] Build dashboard page with stat cards (totalServices, activeServices, totalBookings, pendingBookings) in packages/vendor/src/app/dashboard/page.tsx
- [ ] T064 [US6] Display recent activity log list (last 10 entries) with action, timestamp, entity type
- [ ] T065 [US6] Integrate SSE subscription for real-time dashboard updates — no polling

**Checkpoint**: Dashboard Overview is fully testable independently

---

## Phase 9: User Story 7 — Vendor Booking Messages (Priority: P3)

**Goal**: Vendors view and send messages on individual bookings to coordinate with clients

**Independent Test**: Open a confirmed booking, send a message, verify it appears in the thread for vendor and client.

### Backend Implementation for US7

- [ ] T066 [US7] Implement message list endpoint (GET /api/v1/vendor/bookings/:id/messages) returning messages in chronological order with senderType (vendor/client/system) in packages/backend/src/routes/messages.routes.ts
- [ ] T067 [US7] Implement message send endpoint (POST /api/v1/vendor/bookings/:id/messages) creating BookingMessage with senderType='vendor' in packages/backend/src/routes/messages.routes.ts
- [ ] T068 [US7] Emit notification event on new vendor message so client receives in-app notification

### Frontend Implementation for US7

- [ ] T069 [P] [US7] Build booking detail message thread UI with send form in packages/vendor/src/app/bookings/[id]/page.tsx
- [ ] T070 [US7] Integrate React Query hooks for message list and send with cache invalidation
- [ ] T071 [US7] Add real-time message updates via SSE — new messages appear without refresh

**Checkpoint**: Booking Messages fully testable independently

---

## Phase 10: Integration & Cross-Cutting Concerns

**Purpose**: Security hardening, rate limiting, performance, and polish across all stories

### Rate Limiting
- [ ] T072 [P] Apply rate limiting to vendor endpoints: 60 req/min per spec (FR-009) in packages/backend/src/middleware/rateLimit.middleware.ts
- [ ] T073 [P] Apply rate limiting to price upload: 10 req/min per spec in packages/backend/src/middleware/rateLimit.middleware.ts

### Authorization & Security
- [ ] T074 [P] Verify all vendor endpoints enforce vendor ownership (requireVendorAccess middleware) — no cross-vendor data access
- [ ] T075 [P] Verify CORS config explicitly lists vendor portal origin — no wildcard * per constitution
- [ ] T076 [P] Add input sanitization: strip HTML from vendor descriptions, enforce text length limits per spec

### Error Handling & Validation
- [ ] T077 [P] Ensure all error responses follow API envelope format { success: false, error: { code, message } } with error taxonomy (AUTH_*, VALIDATION_*, NOT_FOUND_*, CONFLICT_*)
- [ ] T078 [P] Handle database constraint violations gracefully (unique, foreign key) with user-friendly messages

### Real-Time & Performance
- [ ] T079 [P] Verify SSE/WebSocket push works end-to-end for booking calendar and dashboard (no polling fallback)
- [ ] T080 [P] Ensure calendar loads within 2 seconds with up to 100 bookings (SC-002)

### Monitoring & Observability
- [ ] T081 [P] Log key business events: vendor.updated, booking.confirmed, booking.rejected, booking.completed, availability.blocked, pricing.updated
- [ ] T082 [P] Add business metrics: booking processing time, earnings calculation latency, CSV upload success/failure

---

## Phase 11: Testing

**Purpose**: Achieve ≥ 60% component test coverage (SC-007) and backend RBAC integration tests

### Frontend Tests
- [ ] T083 [P] Write React Testing Library tests for profile page form interactions in packages/vendor/src/__tests__/
- [ ] T084 [P] Write React Testing Library tests for service CRUD form interactions
- [ ] T085 [P] Write React Testing Library tests for booking calendar status transitions
- [ ] T086 [P] Write React Testing Library tests for earnings dashboard rendering and filters

### Backend Tests
- [ ] T087 [P] Write integration tests for vendor RBAC enforcement — non-vendor tokens rejected on all vendor routes
- [ ] T088 [P] Write integration tests for booking status transitions — invalid transitions rejected
- [ ] T089 [P] Write integration tests for availability blocking — booking rejected on blocked dates
- [ ] T090 [P] Write integration tests for earnings calculation accuracy

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3–9)**: All depend on Foundational phase completion
  - P1 stories can proceed in parallel (if staffed) or sequentially: US1 → US2 → US3 → US4
  - P2 stories (US5, US6) depend on booking lifecycle from US3 being functional
  - P3 story (US7) is fully independent after Phase 2
- **Integration (Phase 10)**: Depends on all user stories being complete
- **Testing (Phase 11)**: Can begin per-story after each story's implementation is complete

### Within Each User Story

- Backend endpoints before frontend pages
- Zod schemas before route handlers
- Core CRUD before polish (audit logging, error handling)
- React Query hooks before UI components that depend on them

### Important Cross-Story Dependencies

- **US2 (Services)**: Pricing tier management integrates with US3 bookings — services must exist before bookings reference them
- **US3 (Bookings)**: Calendar depends on US4 availability data for conflict detection
- **US4 (Availability)**: Availability blocking must integrate with booking creation flow (T050)
- **US5 (Earnings)**: Depends on US3 booking lifecycle being complete (only completed bookings count)
- **US6 (Dashboard)**: Aggregates data from US1 (services count) and US3 (bookings count)

---

## Parallel Opportunities

**Phase 1 (Setup)**:
- T001–T005 all verify schema fields → can run in parallel (read-only checks)
- T006 (migration) depends on T001–T005 findings
- T007 (env vars) independent

**Phase 2 (Foundational)**:
- T008–T011 (RBAC enforcement) touch different route files → **PARALLEL**
- T012–T014 (Zod schemas) modify same file → **SERIALIZE**
- T015 (SSE verification) independent

**Phase 3–9 (User Stories)**:
- Backend [P] tasks within each story are parallelizable
- Frontend tasks generally depend on backend endpoints being ready
- Across stories: US1–US4 (P1) can be parallelized with separate developers

**Phase 10 (Integration)**:
- T072–T082 mostly independent across different concerns → **PARALLEL**

**Phase 11 (Testing)**:
- T083–T090 all independent → **FULLY PARALLEL**

---

## Implementation Strategy

### MVP First (User Stories 1–4)

1. Complete Phase 1: Setup (verify schema, env vars)
2. Complete Phase 2: Foundational (RBAC, Zod schemas, SSE) — **BLOCKS**
3. Complete Phase 3: US1 (vendor profile) — backend then frontend
4. Complete Phase 4: US2 (services & pricing) — backend then frontend
5. Complete Phase 5: US3 (booking calendar) — backend then frontend
6. Complete Phase 6: US4 (availability) — backend then frontend
7. **STOP and VALIDATE**: Test US1–US4 independently:
   - Vendor can update profile, logo uploaded, `vendor.updated` event emitted
   - Vendor can create services with pricing tiers, CSV upload works
   - Booking calendar shows bookings, status transitions work, real-time updates
   - Blocked dates prevent bookings, calendar reflects availability
8. Deploy/demo if ready

### Incremental Delivery

After MVP (US1–US4) is stable:

1. Add Phase 7: US5 (earnings dashboard) → Test independently
2. Add Phase 8: US6 (vendor dashboard) → Test independently
3. Add Phase 9: US7 (booking messages) → Test independently
4. Add Phase 10: Integration & polish
5. Add Phase 11: Testing to ≥ 60% coverage

---

## Notes

- **[P]** tasks = different files, no dependencies within same phase
- **[Story]** label maps task to specific user story for traceability ([US1]–[US7])
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Existing codebase already has Vendor, Service, VendorUser, VendorAvailability, Pricing, PriceHistory, PriceUpload, BookingMessage models — extend, don't duplicate
- Existing auth/RBAC middleware should be reused with requirePermission/requireRole
- Existing rate limiting configs exist in packages/backend/src/middleware/rateLimit.middleware.ts — reuse them
- Vendor routes exist at packages/backend/src/routes/vendor.routes.ts — extend them
- Services routes exist at packages/backend/src/routes/services.routes.ts — extend them
- Pricing routes exist at packages/backend/src/routes/pricing.routes.ts — extend them
- Bookings routes exist at packages/backend/src/routes/bookings.routes.ts — extend them
- Messages routes exist at packages/backend/src/routes/messages.routes.ts — extend them
- CDN service exists at packages/backend/src/services/cdn.service.ts — reuse for logo upload
- EventBus service exists at packages/backend/src/services/event-bus.service.ts — reuse for domain events
- Notification service exists at packages/backend/src/services/notification.service.ts — extend for booking message notifications
- Frontend pages already exist at packages/vendor/src/app/{dashboard,profile,services,bookings,availability,pricing}/ — extend them
- All API responses MUST follow envelope format: { success, data, meta } / { success, error }
- All frontend state MUST use React Query (TanStack Query) — no raw fetch/useState for server data
- Suspended vendors (status=SUSPENDED) MUST be blocked from profile updates with HTTP 403

---

**Feature**: 012-vendor-portal
**Date**: 2026-04-08
**Total Estimated Tasks**: 90
**MVP Scope**: US1–US4 (T001–T053) ≈ 53 tasks
**Parallelizable Tasks**: ~45% (marked [P])
