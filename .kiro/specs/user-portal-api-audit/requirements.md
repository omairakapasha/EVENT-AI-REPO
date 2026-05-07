# Requirements Document

## Introduction

This feature is an audit and verification pass over the user portal (`packages/user`) to confirm
that every page makes correct API calls against the actual backend endpoints, that the
authentication flow is consistent end-to-end, and that no integrations are missing, broken, or
mismatched. The audit covers ten portal pages, two Next.js API proxy routes, the shared API
client (`packages/user/src/lib/api.ts`), and the backend routes in `packages/backend/src/api/v1/`.

Known issues discovered during initial analysis are captured as explicit requirements so they can
be tracked and verified as fixed.

---

## Glossary

- **User_Portal**: The Next.js application in `packages/user/`.
- **API_Client**: The axios instance defined in `packages/user/src/lib/api.ts`, which uses
  `localStorage.getItem('userToken')` as the bearer token.
- **Backend**: The FastAPI application in `packages/backend/src/api/v1/`.
- **Frontend_API_Lib**: The shared axios instance in `packages/vendor/src/lib/api.ts`, which
  uses `localStorage.getItem('accessToken')` as the bearer token.
- **Chat_Page**: `packages/user/src/app/chat/page.tsx`.
- **AI_Stream_Proxy**: The Next.js route handler at
  `packages/user/src/app/api/ai/chat/stream/route.ts`.
- **AI_Service**: The external Python agent service proxied by AI_Stream_Proxy, reachable at
  `AI_SERVICE_URL` (default `http://localhost:8000`).
- **Token_Key**: The localStorage key used to store the user's access token.
- **Audit_Tool**: The automated script or test suite produced by this feature to perform the
  checks described below.

---

## Requirements

### Requirement 1: Token Key Consistency

**User Story:** As a developer, I want all user portal pages to read the auth token from the same
localStorage key, so that authenticated API calls do not silently fail due to a key mismatch.

#### Acceptance Criteria

1. THE Audit_Tool SHALL identify every location in the User_Portal source that reads a token from
   localStorage and report the key name used at each location.
2. WHEN the Audit_Tool detects that Chat_Page reads `localStorage.getItem('userToken')` while
   API_Client reads `localStorage.getItem('userToken')`, THE Audit_Tool SHALL confirm the keys
   match and report no mismatch for this pair.
3. WHEN the Audit_Tool detects that any page imports from `packages/vendor/src/lib/api.ts`
   (which uses `localStorage.getItem('accessToken')`), THE Audit_Tool SHALL flag a token-key
   mismatch because the User_Portal stores tokens under `'userToken'`, not `'accessToken'`.
4. THE Audit_Tool SHALL produce a report listing each unique Token_Key found, the files that use
   it, and a PASS or FAIL verdict for consistency.

---

### Requirement 2: Login Page API Endpoint Correctness

**User Story:** As a developer, I want the login page to call the correct backend endpoint with
the correct HTTP method and payload shape, so that users can authenticate successfully.

#### Acceptance Criteria

1. WHEN a user submits the login form on `/login`, THE User_Portal SHALL send a `POST` request to
   `{NEXT_PUBLIC_API_URL}/users/login` with a JSON body containing `email` and `password`.
2. WHEN the Backend returns `{ success: true, data: { token, refresh_token, user } }`, THE
   User_Portal SHALL store `data.token` under localStorage key `'userToken'`, store `data.user`
   under `'userData'`, and set a `userToken` cookie with `max-age=604800`.
3. WHEN the Backend returns `{ code: "PENDING_APPROVAL" }`, THE User_Portal SHALL display a
   pending-approval message and SHALL NOT redirect to `/dashboard`.
4. WHEN the Backend returns `{ code: "ACCOUNT_REJECTED" }`, THE User_Portal SHALL display a
   rejection message and SHALL NOT redirect to `/dashboard`.
5. IF the Backend returns HTTP 401 or 403, THEN THE User_Portal SHALL display an error message
   and SHALL NOT store any token.
6. THE Audit_Tool SHALL verify that the login endpoint called by the User_Portal (`/users/login`)
   exists in the Backend and accepts `{ email, password }` as a JSON body.

---

### Requirement 3: Registration Endpoint Consistency

**User Story:** As a developer, I want both registration pages (`/signup` and `/register`) to
call consistent, existing backend endpoints, so that new users can create accounts without
encountering 404 errors.

#### Acceptance Criteria

1. WHEN a user submits the signup form on `/signup`, THE User_Portal SHALL send a `POST` request
   to `{NEXT_PUBLIC_API_URL}/users/register` with a JSON body containing `firstName`, `lastName`,
   `email`, `password`, and optionally `phone`.
2. WHEN a user submits the registration form on `/register`, THE User_Portal SHALL send a `POST`
   request to `{NEXT_PUBLIC_API_URL}/auth/register` with the required fields.
3. THE Audit_Tool SHALL verify that both `/users/register` and `/auth/register` exist as `POST`
   routes in the Backend.
4. THE Audit_Tool SHALL flag that `/signup` and `/register` call different endpoints and confirm
   whether both endpoints are intentional and functional.
5. WHEN registration succeeds, THE User_Portal SHALL redirect to `/login?registered=true`.

---

### Requirement 4: Token Refresh Flow Correctness

**User Story:** As a developer, I want the token refresh mechanism in the API_Client to call the
correct backend endpoint and handle the response envelope correctly, so that sessions are
maintained without forcing users to re-login unnecessarily.

#### Acceptance Criteria

1. WHEN API_Client receives an HTTP 401 response, THE API_Client SHALL attempt to refresh the
   token by sending a `POST` request to `{NEXT_PUBLIC_API_URL}/auth/refresh` with body
   `{ refresh_token: <stored_refresh_token> }`.
2. WHEN the Backend returns `{ data: { access_token, refresh_token } }` from `/auth/refresh`,
   THE API_Client SHALL extract `data.access_token` and `data.refresh_token` and store them
   correctly.
3. THE Audit_Tool SHALL verify that the Backend `/auth/refresh` endpoint accepts
   `{ refresh_token }` as a JSON body and returns a token pair.
4. THE Audit_Tool SHALL confirm that API_Client's refresh logic correctly handles both the
   `response.data.data` envelope and the flat `response.data` fallback.
5. IF the refresh token is absent or the refresh call returns HTTP 401, THEN THE API_Client SHALL
   clear all stored tokens and redirect the user to `/login`.

---

### Requirement 5: Dashboard Page API Coverage

**User Story:** As a developer, I want the dashboard page to call only existing, correctly-shaped
backend endpoints, so that event and booking counts are displayed accurately.

#### Acceptance Criteria

1. WHEN the dashboard page loads, THE User_Portal SHALL call `GET /events` to retrieve the
   authenticated user's events.
2. WHEN the dashboard page loads, THE User_Portal SHALL call `GET /bookings` to retrieve the
   authenticated user's bookings.
3. WHEN the dashboard page calls `POST /users/resend-verification`, THE Audit_Tool SHALL verify
   this endpoint exists in the Backend.
4. THE Audit_Tool SHALL verify that `GET /events` and `GET /bookings` exist in the Backend and
   return arrays accessible at `response.data.data` or `response.data.events` /
   `response.data.bookings`.
5. THE Audit_Tool SHALL flag any dashboard API call that targets an endpoint not present in the
   Backend.

---

### Requirement 6: Bookings Page API Coverage

**User Story:** As a developer, I want the bookings page to retrieve and display bookings using
the correct backend endpoint and response shape, so that users see an accurate list of their
bookings.

#### Acceptance Criteria

1. WHEN the bookings page loads, THE User_Portal SHALL call `GET /bookings` via API_Client.
2. THE Audit_Tool SHALL verify that the Backend `GET /bookings/` route exists and returns a
   paginated envelope with bookings accessible at `data.data` or `data.bookings`.
3. THE Audit_Tool SHALL confirm that the bookings page correctly handles both `data.bookings` and
   `data.data` response shapes.
4. WHEN a booking has status `pending`, `confirmed`, `cancelled`, `completed`, or `rejected`, THE
   User_Portal SHALL render the correct status badge for each value.

---

### Requirement 7: Marketplace Page API Coverage

**User Story:** As a developer, I want the marketplace page to call the correct public vendor
search endpoint with the right query parameters, so that vendor listings are populated correctly.

#### Acceptance Criteria

1. WHEN the marketplace page loads or the user changes the search query or category filter, THE
   User_Portal SHALL call `GET /public_vendors/` with query parameters `q` (search string) and
   optionally `category`.
2. THE Audit_Tool SHALL verify that the Backend `GET /public_vendors/` route exists and accepts
   `q` as a query parameter.
3. THE Audit_Tool SHALL flag that the API_Client passes both `q` and `search` as query parameters
   to `/public_vendors/` (via `{ params: { q: params?.search, ...params } }`), which results in
   a redundant `search` parameter being sent; the Backend only recognises `q`.
4. WHEN the Backend returns vendor data, THE User_Portal SHALL extract vendors from
   `response.data.vendors` or `response.data.data`.
5. THE Audit_Tool SHALL verify that the vendor detail route `GET /public_vendors/{id}` exists in
   the Backend.

---

### Requirement 8: Profile Page API Coverage

**User Story:** As a developer, I want the profile page to call existing backend endpoints for
reading and updating user data, so that profile changes are persisted correctly.

#### Acceptance Criteria

1. WHEN the profile page loads, THE User_Portal SHALL call `GET /users/me` via API_Client to
   fetch the current user's profile.
2. WHEN the user saves profile changes, THE User_Portal SHALL call `PUT /users/me` with body
   `{ firstName, lastName, phone }`.
3. WHEN the user changes their password, THE User_Portal SHALL call `PUT /users/me/password` with
   body `{ currentPassword, newPassword }`.
4. THE Audit_Tool SHALL verify that `GET /users/me`, `PUT /users/me`, and `PUT /users/me/password`
   exist as routes in the Backend.
5. THE Audit_Tool SHALL flag that the API_Client helper `updateUserProfile` uses `PATCH /users/me`
   while the profile page component uses `PUT /users/me`; both HTTP methods SHALL be verified
   against the Backend to confirm which is accepted.
6. THE Audit_Tool SHALL flag that the API_Client helper `changePassword` uses
   `PATCH /users/me/password` while the profile page component uses `PUT /users/me/password`;
   both SHALL be verified against the Backend.

---

### Requirement 9: Messages Page API Coverage

**User Story:** As a developer, I want the messages page to use the correct booking-messages
endpoints so that users can send and receive messages on their bookings.

#### Acceptance Criteria

1. WHEN the messages page loads, THE User_Portal SHALL call `GET /bookings/` via API_Client to
   list the user's bookings for the sidebar.
2. WHEN the user selects a booking, THE User_Portal SHALL call
   `GET /bookings/{bookingId}/messages` to load the message thread.
3. WHEN the user sends a message, THE User_Portal SHALL call
   `POST /bookings/{bookingId}/messages` with body `{ message, sender_type: 'client' }`.
4. THE Audit_Tool SHALL verify that `GET /bookings/{id}/messages` and
   `POST /bookings/{id}/messages` exist in the Backend.
5. THE Audit_Tool SHALL verify that the Backend `POST /bookings/{id}/messages` accepts
   `sender_type` as a field in the request body.

---

### Requirement 10: Create-Event Page API Coverage

**User Story:** As a developer, I want the create-event page to call the correct backend endpoint
with a correctly-shaped payload, so that new events are persisted successfully.

#### Acceptance Criteria

1. WHEN the user submits the create-event form, THE User_Portal SHALL call `POST /events` via
   API_Client with a JSON body containing `eventType`, `eventName`, `eventDate`, `location`,
   `attendees`, `budget`, and optionally `preferences`.
2. THE Audit_Tool SHALL verify that `POST /events/` exists in the Backend and accepts the fields
   listed above.
3. THE Audit_Tool SHALL verify that the Backend response includes `data.event.id` or an
   equivalent field so the portal can redirect to `/dashboard?eventId={id}`.
4. WHEN the Backend returns a success response, THE User_Portal SHALL redirect to
   `/dashboard?eventId={event.id}` if an event ID is present, otherwise to `/dashboard`.

---

### Requirement 11: Chat Page Authentication and Proxy Correctness

**User Story:** As a developer, I want the chat page to authenticate correctly and route AI
requests through the correct proxy, so that users can interact with the AI assistant without
auth failures.

#### Acceptance Criteria

1. WHEN the chat page mounts, THE Chat_Page SHALL read the token from
   `localStorage.getItem('userToken')` and redirect to `/login` if the token is absent.
2. WHEN the user sends a message, THE Chat_Page SHALL send a `POST` request to
   `/api/ai/chat/stream` with header `Authorization: Bearer {userToken}` and body
   `{ message, session_id }`.
3. THE AI_Stream_Proxy SHALL forward the request to
   `{AI_SERVICE_URL}/api/v1/ai/chat/stream` with the `Authorization` header and
   `X-API-Key` header preserved.
4. WHEN the AI_Stream_Proxy receives an SSE stream from AI_Service, THE AI_Stream_Proxy SHALL
   pass it through to the browser with `Content-Type: text/event-stream`.
5. WHEN the upstream AI_Service returns a non-2xx status, THE AI_Stream_Proxy SHALL return the
   same HTTP status code to the browser.
6. THE Audit_Tool SHALL confirm that the Chat_Page does NOT import or use Frontend_API_Lib
   (which uses `'accessToken'`), ensuring no token-key mismatch occurs on the chat page.
7. THE Audit_Tool SHALL verify that the `isAuthenticated` state variable set in Chat_Page is
   actually used to gate UI rendering or API calls; if it is declared but never read, THE
   Audit_Tool SHALL flag it as dead code.

---

### Requirement 12: API Client Base URL Consistency

**User Story:** As a developer, I want all API calls from the user portal to target the same base
URL, so that requests are not silently routed to the wrong service.

#### Acceptance Criteria

1. THE API_Client in `packages/user/src/lib/api.ts` SHALL use
   `process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001/api/v1'` as its base URL.
2. THE Audit_Tool SHALL flag that the login page (`/login`) constructs its own `API_URL` as
   `process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api/v1'` (port 5000), while
   API_Client defaults to port 3001; these defaults are inconsistent and SHALL be reconciled.
3. THE Audit_Tool SHALL flag that the signup page (`/signup`) constructs its own `API_URL` as
   `process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001/api/v1'` (port 3001), which
   matches API_Client but differs from the login page default.
4. THE Audit_Tool SHALL produce a report listing every unique base URL default found across all
   User_Portal files and flag any that differ from the canonical value.
5. WHERE `NEXT_PUBLIC_API_URL` is set in the environment, THE User_Portal SHALL use that value
   consistently across all pages and the API_Client.

---

### Requirement 13: Missing Backend Endpoint Detection

**User Story:** As a developer, I want to know which API calls made by the user portal have no
corresponding backend route, so that I can implement the missing endpoints before they cause
runtime errors.

#### Acceptance Criteria

1. THE Audit_Tool SHALL enumerate all HTTP calls made by the User_Portal (pages and API_Client)
   and cross-reference them against the Backend route definitions.
2. THE Audit_Tool SHALL flag `POST /users/resend-verification` as potentially missing and verify
   whether it exists in the Backend.
3. THE Audit_Tool SHALL flag `GET /users/me`, `PUT /users/me`, and `PUT /users/me/password` as
   requiring verification against the Backend's `/users` router.
4. THE Audit_Tool SHALL flag `GET /marketplace/{vendorId}/reviews` and
   `POST /marketplace/{vendorId}/reviews` (used in API_Client helper functions) as requiring
   verification; no `/marketplace` prefix route is visible in the Backend route files.
5. THE Audit_Tool SHALL flag `POST /ai/chat` (used in `planEventWithAI` and
   `discoverVendorsWithAI` helpers in API_Client) as requiring verification against the Backend
   or AI_Service.
6. WHEN the Audit_Tool identifies a missing endpoint, THE Audit_Tool SHALL record the calling
   file, the HTTP method, the path, and a severity level of HIGH (used by a rendered page) or
   LOW (used only by an unused helper function).

---

### Requirement 14: Response Envelope Compatibility

**User Story:** As a developer, I want every page to correctly unwrap the backend's standard
response envelope `{ success, data, meta }`, so that components receive the data they expect
rather than undefined values.

#### Acceptance Criteria

1. THE Audit_Tool SHALL verify that each page correctly accesses the data field from the Backend
   envelope (e.g., `response.data.data`, `response.data.events`, `response.data.bookings`).
2. WHEN the Backend returns `{ success: true, data: [...], meta: { total, page, limit } }`, THE
   User_Portal SHALL not attempt to access `response.data` directly as an array.
3. THE Audit_Tool SHALL flag the `getUserBookings` helper in API_Client, which calls
   `GET /bookings` (no trailing slash), while the Backend route is registered as `GET /bookings/`
   (with trailing slash); the Audit_Tool SHALL verify whether the Backend handles both forms.
4. THE Audit_Tool SHALL flag the `createBooking` helper in API_Client, which calls
   `POST /bookings` (no trailing slash), and verify the same trailing-slash behaviour.
5. THE Audit_Tool SHALL flag the `createEvent` helper in API_Client, which calls `POST /events`
   (no trailing slash), and verify the same trailing-slash behaviour.

---

### Requirement 15: Google OAuth Flow Correctness

**User Story:** As a developer, I want the Google OAuth sign-in flow to redirect to the correct
backend endpoint with the portal origin, so that after authentication the user is returned to the
user portal rather than another portal.

#### Acceptance Criteria

1. WHEN the user clicks "Continue with Google" on the login page, THE User_Portal SHALL redirect
   the browser to `{API_URL}/auth/google?frontend_origin={encodeURIComponent(window.location.origin)}`.
2. WHEN the user clicks "Sign up with Google" on the signup page, THE User_Portal SHALL redirect
   the browser to `{API_URL}/auth/google` without a `frontend_origin` parameter.
3. THE Audit_Tool SHALL flag that the signup page does not pass `frontend_origin` to
   `/auth/google`, which may cause the OAuth callback to redirect to the wrong portal.
4. WHEN the Backend `/auth/google/callback` completes successfully, THE Backend SHALL redirect to
   `{frontend_origin}/dashboard?token=...&refresh_token=...`.
5. THE Audit_Tool SHALL verify that the User_Portal has a mechanism to consume the `token` and
   `refresh_token` query parameters on the `/dashboard` route after a Google OAuth redirect.

---

### Requirement 16: Audit Report Completeness

**User Story:** As a developer, I want a single consolidated audit report that summarises all
findings, so that I can prioritise and track remediation work.

#### Acceptance Criteria

1. THE Audit_Tool SHALL produce a report with sections: Token Consistency, Endpoint Coverage,
   Base URL Consistency, Response Envelope Compatibility, and OAuth Flow.
2. FOR EACH finding, THE Audit_Tool SHALL record: file path, line number (where applicable),
   finding type (MISMATCH, MISSING, INCONSISTENCY, DEAD_CODE), severity (HIGH / MEDIUM / LOW),
   and a plain-English description.
3. THE Audit_Tool SHALL produce a summary count of findings by severity.
4. WHEN all findings have been resolved, THE Audit_Tool SHALL produce a report with zero HIGH and
   zero MEDIUM severity findings.
5. THE Audit_Tool SHALL be runnable as a single command from the repository root without
   requiring a running backend or frontend server.
