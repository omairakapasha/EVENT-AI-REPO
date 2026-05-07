# Requirements Document

## Introduction

The Vendor Portal Complete feature delivers a fully functional vendor-facing web application within the Event-AI platform. Vendors are businesses (photographers, caterers, decorators, etc.) who offer services for Pakistani events (weddings, mehndi, baraat, walima, corporate events, birthdays). The portal runs on Next.js 15 at port 3002 and communicates exclusively with the FastAPI backend at port 5000 via `/api/v1/`.

The existing codebase has scaffolded pages for dashboard, bookings, services, availability, and profile — but several backend endpoints they depend on do not yet exist, the auth store has shape mismatches with the real backend, and key features (notifications with SSE, booking messages, booking detail view) are absent. This spec covers both the missing backend endpoints and the complete, production-ready frontend.

---

## Glossary

- **Vendor**: A business registered on Event-AI that offers event services (e.g., catering, photography, decoration).
- **Vendor_Portal**: The Next.js 15 frontend application at `packages/vendor`, running on port 3002.
- **Backend**: The FastAPI application at `packages/backend`, running on port 5000.
- **Auth_Store**: The Zustand store in `packages/vendor/src/lib/auth-store.ts` that manages JWT tokens and vendor session state.
- **Booking**: A reservation made by a customer for a vendor's service on a specific event date.
- **Service**: A specific offering created by a vendor (e.g., "Wedding Photography Package", "Catering for 200 guests").
- **Availability**: A vendor's calendar of open, blocked, or tentative dates per service.
- **Notification**: A real-time alert delivered to the vendor via SSE when a booking event occurs.
- **SSE_Stream**: The Server-Sent Events endpoint at `GET /api/v1/sse/stream` that pushes real-time events to authenticated clients.
- **Booking_Message**: A text message exchanged between a vendor and a customer within the context of a specific booking.
- **Dashboard_Stats**: Aggregated metrics (total bookings, pending bookings, active services, revenue) computed for the authenticated vendor.
- **Vendor_Availability**: A record in the `vendor_availability` table that marks a vendor's date as available, blocked, or tentative for a given service.

---

## Requirements

### Requirement 1: Authentication Alignment

**User Story:** As a vendor, I want to log in with my email and password and have my session persist correctly, so that I can access the portal without being unexpectedly logged out.

#### Acceptance Criteria

1. WHEN a vendor submits valid credentials to `POST /api/v1/users/login`, THE Auth_Store SHALL extract `token` and `refresh_token` from the `data` envelope and store them using `setAccessToken` and `setRefreshToken`.
2. WHEN the backend returns a `user` object with snake_case fields (`first_name`, `last_name`, `email_verified`), THE Auth_Store SHALL map them to camelCase fields (`firstName`, `lastName`, `emailVerified`) before storing.
3. WHEN the backend returns a vendor profile from `GET /api/v1/vendors/profile/me`, THE Auth_Store SHALL map `business_name` to `name`, `contact_email` to `contactEmail`, and `status` to the `Vendor.status` field.
4. WHEN a vendor's access token expires and a valid refresh token exists, THE Auth_Store SHALL call `POST /api/v1/auth/refresh` and retry the original request with the new token without requiring the vendor to log in again.
5. IF the refresh token is missing or the refresh call returns a 401, THEN THE Auth_Store SHALL clear all tokens and redirect the vendor to `/login`.
6. WHEN a vendor completes Google OAuth and the callback URL contains `?token=...&refresh_token=...`, THE Vendor_Portal SHALL call `loginWithTokens` and strip the tokens from the URL using `window.history.replaceState`.

---

### Requirement 2: Dashboard with Real Stats

**User Story:** As a vendor, I want to see a summary of my business performance on the dashboard, so that I can quickly understand my current booking and service status.

#### Acceptance Criteria

1. THE Backend SHALL expose `GET /api/v1/vendors/me/dashboard` that returns `{ total_bookings, pending_bookings, confirmed_bookings, active_services, total_services, recent_bookings[] }` for the authenticated vendor in a single database round-trip.
2. WHEN the dashboard page loads and the vendor is authenticated, THE Vendor_Portal SHALL call `GET /api/v1/vendors/me/dashboard` and display the returned stats in the four stat cards.
3. WHEN the API call is in flight, THE Vendor_Portal SHALL display skeleton shimmer placeholders in the stat cards and recent bookings table.
4. IF the dashboard API call fails, THEN THE Vendor_Portal SHALL display an inline error message with a retry button rather than crashing the page.
5. THE Vendor_Portal SHALL display the five most recent bookings in the "Recent Bookings" table, showing service name, event date, status badge, and total amount.
6. WHEN a booking status is `pending`, THE Vendor_Portal SHALL render the status badge with a yellow/warning colour; `confirmed` with blue; `completed` with green; `cancelled` or `rejected` with red/grey.

---

### Requirement 3: Service Management

**User Story:** As a vendor, I want to create, view, edit, and delete my service offerings, so that customers can discover and book the right service for their event.

#### Acceptance Criteria

1. THE Backend SHALL expose `GET /api/v1/vendors/me/services` that returns a paginated list of services belonging to the authenticated vendor, supporting optional `search` and `category` query parameters.
2. WHEN a vendor submits a new service form with a name, category, price range, and capacity, THE Backend SHALL create the service via `POST /api/v1/services/` and return the created service with HTTP 201.
3. WHEN a vendor edits an existing service, THE Backend SHALL update it via `PUT /api/v1/services/{id}` and return the updated service.
4. WHEN a vendor deletes a service, THE Backend SHALL soft-delete it (set `is_active = false`) via `DELETE /api/v1/services/{id}` and return HTTP 204.
5. WHEN the services page loads, THE Vendor_Portal SHALL fetch services from `GET /api/v1/vendors/me/services` and display them in a table with name, category, status, capacity, and price range columns.
6. WHEN a vendor clicks "Add Service", THE Vendor_Portal SHALL navigate to `/services/new` and display a form with fields: name (required), category (required, dropdown from `GET /api/v1/categories/`), description, price_min, price_max, capacity.
7. WHEN a vendor submits the new service form with missing required fields, THE Vendor_Portal SHALL display inline validation errors without submitting to the backend.
8. WHEN a vendor clicks the delete icon on a service row, THE Vendor_Portal SHALL display a confirmation dialog before calling the delete endpoint.
9. IF the delete call fails, THEN THE Vendor_Portal SHALL display a toast error message and leave the service in the list.

---

### Requirement 4: Booking Management

**User Story:** As a vendor, I want to view all my bookings, filter them by status, and confirm or reject pending bookings, so that I can manage my event schedule efficiently.

#### Acceptance Criteria

1. WHEN the bookings page loads, THE Vendor_Portal SHALL call `GET /api/v1/vendors/me/bookings` and display all bookings in a table sorted by event date descending.
2. WHEN a vendor selects a status filter tab, THE Vendor_Portal SHALL re-fetch bookings with the `status` query parameter and update the table without a full page reload.
3. WHEN a vendor clicks "Confirm" on a pending booking, THE Vendor_Portal SHALL call `PATCH /api/v1/vendors/me/bookings/{id}/status` with `{ "status": "confirmed" }` and update the row status in the table optimistically.
4. WHEN a vendor clicks "Reject" on a pending booking, THE Vendor_Portal SHALL display a modal asking for an optional rejection reason before calling `PATCH /api/v1/vendors/me/bookings/{id}/status` with `{ "status": "rejected", "reason": "..." }`.
5. IF the confirm or reject API call fails, THEN THE Vendor_Portal SHALL revert the optimistic update and display a toast error message.
6. WHEN a vendor clicks a booking row, THE Vendor_Portal SHALL navigate to `/bookings/{id}` and display the booking detail view.
7. THE booking detail view SHALL display: customer name, event date, service name, status, total price, event location, and the full booking messages thread.
8. WHEN a vendor types a message in the booking detail view and submits, THE Vendor_Portal SHALL call `POST /api/v1/bookings/{id}/messages` and append the new message to the thread without a full page reload.
9. WHEN the booking messages thread loads, THE Vendor_Portal SHALL call `GET /api/v1/bookings/{id}/messages` and display messages in chronological order, distinguishing vendor messages from customer messages visually.

---

### Requirement 5: Availability Calendar

**User Story:** As a vendor, I want to manage my availability calendar by marking dates as available, blocked, or tentative per service, so that customers and the AI agent can see when I am bookable.

#### Acceptance Criteria

1. THE Backend SHALL expose `GET /api/v1/vendors/me/availability` accepting `start_date`, `end_date`, and optional `service_id` query parameters, returning all `vendor_availability` records for the authenticated vendor in that date range.
2. THE Backend SHALL expose `POST /api/v1/vendors/me/availability` accepting `{ date, status, service_id?, notes? }` and upsert a `vendor_availability` record for the authenticated vendor.
3. THE Backend SHALL expose `POST /api/v1/vendors/me/availability/bulk` accepting `{ entries: [{ date, status, service_id?, notes? }] }` and upsert multiple records in a single transaction.
4. WHEN the availability page loads, THE Vendor_Portal SHALL fetch the current month's availability from `GET /api/v1/vendors/me/availability` and render a monthly calendar grid.
5. WHEN a vendor clicks a calendar day, THE Vendor_Portal SHALL display a modal with four status options: Available, Blocked, Tentative, and (read-only) Booked.
6. WHEN a vendor selects a status in the modal, THE Vendor_Portal SHALL call `POST /api/v1/vendors/me/availability` and update the calendar cell colour immediately (optimistic update).
7. WHEN a booking is confirmed for a date, THE Backend SHALL automatically upsert a `vendor_availability` record with `status = "booked"` for that date and service.
8. WHILE a vendor has the availability page open and a booking is confirmed via SSE, THE Vendor_Portal SHALL refresh the calendar data to reflect the newly booked date.
9. IF the availability upsert call fails, THEN THE Vendor_Portal SHALL revert the optimistic calendar update and display a toast error.

---

### Requirement 6: Vendor Profile Management

**User Story:** As a vendor, I want to view and update my business profile information, so that customers see accurate details about my business.

#### Acceptance Criteria

1. WHEN the profile page loads, THE Vendor_Portal SHALL call `GET /api/v1/vendors/profile/me` and populate the form fields with the returned data.
2. WHEN a vendor clicks "Edit Profile" and modifies fields, THE Vendor_Portal SHALL enable the save button and show a "Cancel" option.
3. WHEN a vendor submits the profile form, THE Vendor_Portal SHALL call `PUT /api/v1/vendors/profile/me` with the updated fields and display a success toast on HTTP 200.
4. WHEN the profile form is submitted with an empty business name, THE Vendor_Portal SHALL display an inline validation error and not call the backend.
5. WHEN the profile form is submitted with a malformed website URL (not starting with `http://` or `https://`), THE Vendor_Portal SHALL display an inline validation error and not call the backend.
6. IF the profile update call fails, THEN THE Vendor_Portal SHALL display the backend error message inline and keep the form in edit mode.
7. THE profile page SHALL display the vendor's current approval status (`PENDING`, `ACTIVE`, `SUSPENDED`, `REJECTED`) as a read-only badge.

---

### Requirement 7: Real-Time Notifications

**User Story:** As a vendor, I want to receive real-time notifications when customers make, confirm, or cancel bookings, so that I can respond promptly without refreshing the page.

#### Acceptance Criteria

1. WHEN a vendor is authenticated and any page in the Vendor_Portal is open, THE Vendor_Portal SHALL establish an SSE connection to `GET /api/v1/sse/stream` using the vendor's JWT token.
2. WHEN the SSE connection receives a `booking.created` event, THE Vendor_Portal SHALL display a toast notification with the message "New booking request received" and increment the unread notification badge count.
3. WHEN the SSE connection receives a `booking.confirmed` or `booking.cancelled` event, THE Vendor_Portal SHALL display a toast notification with the relevant status change message.
4. WHEN a vendor clicks the notification bell icon, THE Vendor_Portal SHALL call `GET /api/v1/notifications/` and display a dropdown list of the 10 most recent notifications.
5. WHEN a vendor clicks a notification in the dropdown, THE Vendor_Portal SHALL call `PATCH /api/v1/notifications/{id}/read` and mark it as read, removing the unread indicator.
6. WHEN a vendor clicks "Mark all as read", THE Vendor_Portal SHALL call `PATCH /api/v1/notifications/read-all` and clear the unread badge count.
7. IF the SSE connection drops, THEN THE Vendor_Portal SHALL attempt to reconnect with exponential backoff (1s, 2s, 4s, max 30s) and display a subtle "Reconnecting…" indicator.
8. THE Vendor_Portal SHALL call `GET /api/v1/notifications/unread-count` on initial page load and display the count in the notification bell badge.

---

### Requirement 8: Navigation and Layout

**User Story:** As a vendor, I want a consistent sidebar navigation and layout across all portal pages, so that I can move between sections without disorientation.

#### Acceptance Criteria

1. THE Vendor_Portal SHALL render a persistent left sidebar on all authenticated pages containing navigation links to: Dashboard, Services, Bookings, Availability, Profile.
2. WHEN a vendor is on a specific page, THE Vendor_Portal SHALL highlight the corresponding sidebar navigation item as active using a distinct visual style.
3. THE Vendor_Portal SHALL display the vendor's business name and approval status badge in the sidebar footer.
4. WHEN a vendor clicks "Logout" in the sidebar, THE Vendor_Portal SHALL call `POST /api/v1/auth/logout`, clear all tokens, and redirect to `/login`.
5. WHEN an unauthenticated user navigates to any protected route (dashboard, bookings, services, availability, profile), THE Vendor_Portal SHALL redirect them to `/login`.
6. WHEN an authenticated vendor navigates to `/login`, THE Vendor_Portal SHALL redirect them to `/dashboard`.
7. THE Vendor_Portal SHALL display a notification bell icon in the top header bar with an unread count badge when there are unread notifications.

---

### Requirement 9: Error Handling and Loading States

**User Story:** As a vendor, I want clear feedback when actions are loading or fail, so that I understand the state of the application at all times.

#### Acceptance Criteria

1. WHEN any API call is in flight, THE Vendor_Portal SHALL display a loading indicator (spinner or skeleton) in the relevant UI region and disable the triggering button to prevent duplicate submissions.
2. WHEN an API call returns a 4xx or 5xx error, THE Vendor_Portal SHALL extract the `error.message` from the backend envelope `{ success: false, error: { code, message } }` and display it to the vendor.
3. WHEN a network error occurs (no response from server), THE Vendor_Portal SHALL display "Unable to connect to server. Please check your connection." rather than a raw error object.
4. IF a form submission fails due to a validation error (HTTP 422), THEN THE Vendor_Portal SHALL display field-level error messages next to the relevant inputs.
5. THE Vendor_Portal SHALL use React Query for all data fetching, with `staleTime` of 30 seconds and automatic background refetch on window focus for booking and notification data.
