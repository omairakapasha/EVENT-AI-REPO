# Feature Specification: Real-Time Updates

**Feature Branch**: `008-real-time-updates`  
**Created**: 2026-04-07  
**Status**: Draft  
**Input**: User description: "Real-Time Updates    SSE/WebSocket for live booking status, chat"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Live Booking Status Notifications (Priority: P1)

As a user (event organizer or vendor), I want to receive immediate updates when my booking status changes (e.g., confirmed, declined, rescheduled), so that I can respond promptly without having to manually check the application.

**Why this priority**: Booking status changes are time-sensitive. Users need to know immediately when a vendor responds to an inquiry or when their own booking request is accepted/declined. Without real-time updates, users waste time refreshing or may miss opportunities. This is the highest value real-time use case for the marketplace.

**Independent Test**: Can be tested by a user with an open browser page; a vendor (or admin acting as vendor) changes the status of a booking request associated with that user. Within 1 second, the user sees a notification (toast, badge update, or page refresh) indicating the new status. No manual refresh required.

**Acceptance Scenarios**:

1. **Given** I am an event organizer viewing my event details page, **When** a vendor accepts my booking request, **Then** I immediately see a notification (e.g., "Vendor X has accepted your booking!") and the booking status updates to "confirmed" without me refreshing the page.

2. **Given** a vendor declines my booking, **When** the status changes to "declined", **Then** I receive an immediate notification with the vendor's optional message and the status reflects the change.

3. **Given** a booking is rescheduled (vendor proposes new date/time), **When** the update occurs, **Then** I see the new proposed date/time instantly and can accept or propose alternatives.

4. **Given** I am a vendor viewing my booking queue, **When** an event organizer sends me a new booking inquiry, **Then** it appears in my queue immediately, and I see a visual indicator (badge count increase, sound alert optional).

5. **Given** I have multiple browser tabs open, **When** a booking update happens, **Then** all tabs receive the update consistently (no race conditions or missed updates).

---

### User Story 2 - Real-Time Chat Messaging (Priority: P2)

As a user involved in an event planning conversation (either with a vendor or with the AI assistant), I want to send and receive messages in real-time, so that the conversation feels responsive and natural, like instant messaging.

**Why this priority**: Chat is a core interaction mode—both vendor-user communication and AI agent chat. Users expect near-instant message delivery. Without WebSocket/SSE, chat would require polling (inefficient, delayed). P2 because booking notifications are more urgent, but chat is equally important for UX.

**Independent Test**: Can be tested by two users (or user and vendor) opening chat interfaces (or AI chat) and exchanging messages. When one sends a message, the other sees it appear within 1 second without page refresh. Messages appear in chronological order. Typing indicators ("User is typing...") may also update in real-time.

**Acceptance Scenarios**:

1. **Given** I am in a chat conversation with a vendor, **When** I send a message, **Then** it appears in my chat window immediately (optimistic update) and is delivered to the vendor within 1 second, appearing in their chat window.

2. **Given** the vendor replies to my message, **When** they send it, **Then** I see their message appear in my chat window instantly, and the conversation scrolls to show the latest.

3. **Given** I am chatting with the AI assistant (from `006-ai-agent-chat`), **When** the AI is generating a response, **Then** I see a "typing" indicator and then the response streams token-by-token (if using streaming) or appears in full within 2 seconds.

4. **Given** I have a poor network connection, **When** messages fail to send, **Then** I see a status indicator (failed) and can retry. The system should queue messages while offline and send when reconnected (at least for non-critical chat).

5. **Given** multiple participants are in a group chat (if supported), **When** any participant sends a message, **Then** all other participants receive it in real-time with correct ordering.

---

### User Story 3 - Subscription Management and Reconnection (Priority: P3)

As a user with intermittent network connectivity, I want the real-time connection to automatically reconnect and catch up on missed events, so that I don't lose important updates during temporary disconnections.

**Why this priority**: Network reliability is crucial for a good user experience. Automatic reconnection prevents users from missing updates when they switch networks, lock their device, or experience brief outages. This is an enhancement that improves reliability but is not strictly required for initial MVP (P3).

**Independent Test**: Can be tested by a user with an open real-time connection (chat or booking updates) and then disabling network (airplane mode) for 10 seconds, then re-enabling. The system should detect the disconnection, attempt to reconnect automatically, and upon reconnection, deliver any events that occurred during the disconnect period (or at least inform the user of missed events). The reconnection should happen within a few seconds.

**Acceptance Scenarios**:

1. **Given** I am viewing a chat or event dashboard with live updates, **When** my internet connection drops, **Then** the UI shows a "disconnected" status and the system begins automatically reconnecting with exponential backoff.

2. **Given** the connection was lost for 15 seconds, **When** reconnection succeeds, **Then** the system delivers any missed events (e.g., booking status changes, chat messages) that occurred during the disconnect, in the correct order, and the UI updates accordingly.

3. **Given** reconnection fails repeatedly (server down), **When** max retries are exhausted, **Then** the UI shows a persistent error and suggests manual refresh or checking service status.

4. **Given** I switch between pages while the connection is healthy, **When** I navigate to a new page that also subscribes to real-time events, **Then** the connection is reused (same underlying WebSocket/SSE) and subscriptions update accordingly without creating multiple connections.

5. **Given** I close and reopen the browser tab after a short time (<5 minutes), **When** I log back in, **Then** the system restores my subscriptions and I receive updates relevant to my current context without needing to refresh manually.

---

### Edge Cases

- What happens when the WebSocket/SSE connection exceeds concurrent connection limits? The system should enforce per-user or per-IP limits (e.g., 5 connections per user), reject excess with clear error, and encourage reusing existing connections.

- What happens when a user's authentication token expires while a real-time connection is active? The connection should be closed gracefully, and the client should re-authenticate (refresh token) and reconnect. Or use token refresh mechanism transparently.

- What happens when a user subscribes to updates for events they are not authorized to view (e.g., someone else's bookings)? The subscription request must be validated; unauthorized subscriptions are rejected, and the user receives only events for resources they have permission to access.

- What happens when the server needs to broadcast a high volume of updates (e.g., 10,000 concurrent users all receiving a system announcement)? The system must handle fan-out efficiently using a message broker (Redis pub/sub or NATS) and not overload the database or individual connections.

- What happens when a client cannot keep up with the message rate (slow consumer)? The server should implement backpressure: if a client's outbound buffer is full, either drop messages (with a warning) or temporarily suspend sending. Client should request missed data via fallback API if needed.

- What happens when a subscription is no longer needed (user navigates away, closes page)? The client must unsubscribe and close the connection (or return to connection pool). Server should clean up subscriptions to avoid memory leaks.

- What happens when the real-time infrastructure component (WebSocket server) crashes or restarts? The system should be resilient: connections are lost, clients automatically reconnect, and service recovers quickly. Consider using load balancer with sticky sessions if needed.

- What happens when a user tries to send a message via chat while disconnected? The client should queue messages and send them when reconnected, or show failed status and allow retry. Ordering must be preserved.

- What happens when security vulnerabilities are exploited (e.g., malicious WebSocket messages, cross-site WebSocket hijacking)? The system must validate all incoming messages, enforce same-origin policies, use secure wss:// (TLS), authenticate connections at connection establishment.

- What happens when different clients need different subscription lifetimes (some short-lived, some long-lived)? The system should allow setting TTLs on subscriptions and automatically expire them after inactivity.

- What happens when events are delivered out of order due to network realities? The client should handle reordering based on event timestamps or sequence numbers. Events may have a monotonically increasing sequence per channel.

- What happens when the real-time system needs to scale horizontally? The architecture should support multiple WebSocket server instances behind a load balancer, with subscription state shared via Redis or similar pub/sub so that events can be routed to the correct server instance.

- What happens when a user is accessing from a browser that does not support WebSocket or SSE? The system should fall back to long-polling or have graceful degradation (notifications only, no real-time). However, given target modern browsers, this is low priority.

- What happens when an event update references data that has since been deleted (e.g., booking canceled and removed)? The system should handle "not found" gracefully—perhaps send a tombstone event indicating deletion.

- What happens when too many distinct event types are subscribed to by a single client, causing memory pressure? The server could limit number of subscriptions per connection; client should be selective.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide Server-Sent Events (SSE) endpoints for unidirectional server-to-client updates, allowing clients to subscribe to event streams by specifying event types or subscription parameters.

- **FR-002**: The system MUST provide WebSocket endpoints for bidirectional real-time communication, supporting full-duplex message exchange between clients and server (used for chat applications and interactive updates).

- **FR-003**: The system MUST authenticate all real-time connections using JWT tokens (passed via query parameter or subprotocol handshake). Connections without valid tokens are rejected immediately.

- **FR-004**: The system MUST implement an event subscription model where clients can subscribe to specific event channels (e.g., `booking:{booking_id}`, `user:{user_id}`, `chat:{conversation_id}`) and only receive events relevant to those subscriptions.

- **FR-005**: The system MUST broadcast domain events from the Backend service (e.g., `booking.created`, `booking.status_changed`, `vendor.approved`) to real-time subscribers via the event bus (Fastify hooks or external message broker).

- **FR-006**: The system MUST support at least the following real-time use cases:
  - Booking status updates (to event organizer and vendor)
  - Chat message delivery (both user-vendor and AI chat)
  - Admin notifications (approval queue updates)
  - Event plan update notifications

- **FR-007**: The system MUST implement reconnection logic on the client side: if a connection drops, the client automatically attempts to reconnect with exponential backoff and resume subscriptions. Server must handle reconnects gracefully and resubscribe the client.

- **FR-008**: The system MUST ensure at-least-once delivery semantics for critical events (booking updates, chat messages). Each event must have a unique event ID and timestamp; clients can deduplicate if needed.

- **FR-009**: The system MUST scale horizontally: support multiple WebSocket/SSE server instances with a shared subscription state using a distributed pub/sub (Redis or NATS) so events can be routed to the correct instance.

- **FR-010**: The system MUST implement rate limiting per user/IP to prevent abuse: maximum 100 messages per minute per user for chat, and maximum 50 event streams per user for subscriptions.

- **FR-011**: The system MUST log all connection events (connect, disconnect, errors), subscriptions (subscribe/unsubscribe), and delivered messages with timestamps, user IDs, and event IDs for audit and debugging.

- **FR-012**: The system MUST provide health check endpoints for the real-time service (e.g., `/health/websocket`) reporting connection counts, subscription counts, and message rates.

- **FR-013**: The system SHOULD support message buffering or offline queuing for authenticated users: if a user is offline, important notifications (booking changes) can be stored and delivered upon next connection (subject to TTL).

- **FR-014**: The system MUST enforce authorization on subscription: when a client subscribes to a channel (e.g., `booking:123`), the server verifies that the user has permission to receive events for that resource before adding the subscription.

- **FR-015**: The system MUST use TLS (wss:// for WebSocket, https:// for SSE) in production to secure data in transit.

- **FR-016**: The system SHOULD allow clients to unsubscribe from specific channels without closing the entire connection, to conserve bandwidth.

- **FR-017**: The system MUST handle backpressure: if a client is slow to read messages, the server should not buffer indefinitely; it should either drop messages (with warning) or close the connection to prevent memory exhaustion.

- **FR-018**: The system MUST support heartbeats/pings to keep connections alive and detect dead clients (stale connections). Both sides send periodic pings; if no pong received, connection is closed.

- **FR-019**: The system SHOULD collect metrics: number of active connections, messages per second, subscription counts, connection duration, error rates. These metrics should be exposed for monitoring.

- **FR-020**: The system MUST support graceful shutdown: connections are closed with a "server going down" message, allowing clients to reconnect to a new instance.

### Key Entities

- **Connection**: Represents an active real-time connection (SSE or WebSocket) from a client to the server. Attributes include: connection ID (UUID), user ID (if authenticated), connection type (SSE/WebSocket), connected at timestamp, last activity timestamp, IP address, user agent, status (connected, disconnected, closed). Connections are ephemeral and stored in memory (or Redis for multi-instance).

- **Subscription**: Represents a client's subscription to an event channel. Attributes: subscription ID, connection ID, channel name (e.g., `booking:123`, `user:456`, `chat:789`), subscribed at timestamp, optional expiration TTL. Subscriptions tie a connection to a channel of interest. Many subscriptions per connection.

- **RealtimeEvent**: Represents an event published to the real-time system for delivery to subscribers. Attributes: event ID (UUID), event type (e.g., `booking.status_changed`), channel (or list of channels to broadcast), timestamp, payload (JSON with event data), source service (backend, ai, admin). Events are transient; consumed by the real-time server and delivered to connections.

- **MessageQueue** (conceptual): For offline queuing (FR-013). Represents pending messages for a user who is not currently connected. Attributes: user ID, message payload, enqueue timestamp, TTL. Processed when user reconnects.

- **DeliveryAttempt**: For audit and reliability. Records each attempt to deliver an event to a connection. Attributes: attempt ID, connection ID, event ID, delivered at (or failed), error if any. Useful for debugging and metrics.

**Note**: These entities are runtime state, not necessarily persisted to the database (except maybe delivery logs for audit). They exist in memory/Redis.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Event delivery latency: 95% of real-time events (booking updates, chat messages) are delivered to the client within 1 second of the event being published (measured from server event to client receipt).

- **SC-002**: Connection reliability: 99.9% of WebSocket/SSE connections remain stable without unexpected drops during a typical 1-hour chat session (excluding client-side network issues).

- **SC-003**: Reconnection success: When a client disconnects unexpectedly, the system automatically re-establishes the connection within 5 seconds (median reconnection time) and restores subscriptions.

- **SC-004**: Scalability: The real-time service supports at least 10,000 concurrent connections without degradation (delivery latency remains <1 second, CPU and memory within reasonable limits).

- **SC-005**: Authorization enforcement: Zero incidents of a user receiving real-time events for resources they are not authorized to access (as measured by audit logs and penetration tests).

- **SC-006**: System availability: Real-time endpoints maintain ≥99.5% uptime during business hours (9 AM - 9 PM), with graceful handling of backend dependencies (if pub/sub or database is down, connections stay alive but events may be delayed).

- **SC-007**: Message ordering: For events on the same channel, 100% are delivered in the order of publication (FIFO per channel) to ensure consistency (e.g., a booking status change from "pending" to "confirmed" should not appear out of order).

### User Satisfaction

- Users rate real-time notification timeliness ≥4.5/5.
- Chat users report conversation feels "responsive" ≥4/5.
- Vendor users report that booking notifications are reliable ≥4/5.

### Business Impact

- Reduce time to vendor response: vendors respond to booking inquiries 50% faster due to immediate notifications, leading to higher conversion rates.
- Improve user engagement: users with real-time enabled are 30% more likely to complete a booking.
- Reduce support tickets related to "status not updating" or "did my message send?" by 70%.
- Differentiate platform with live, interactive chat and instant updates, improving perceived quality and modern UX.

## Assumptions

- The Backend service (`packages/backend`) is the source of truth for domain events (booking.created, booking.status_changed, vendor.approved). These events are published to the event bus (currently in-process EventEmitter) and will be published to a distributed pub/sub (Redis/NATS) for real-time consumption.

- The real-time service is implemented as part of the Backend package (Fastify server) using Fastify's SSE and WebSocket support (fastify-websocket plugin). It is not a separate microservice initially, but designed to be separable later.

- Client-side implementations: Frontend portals (`packages/user`, `packages/admin`, `packages/vendor`) use standard WebSocket or EventSource APIs to connect and subscribe. Libraries like `socket.io` are not used; native APIs suffice with fallback to SSE if WebSocket unavailable.

- Authentication: JWT tokens from `002-user-auth` are used. Upon connection, the token is validated (via shared auth service or JWT verification). The user ID is associated with the connection and used for authorization checks on subscriptions.

- Subscription model: Clients subscribe to channels that correspond to resource IDs they own or are authorized for (e.g., a user can subscribe to `user:{user_id}` to receive all their own booking updates, or `booking:{booking_id}` for a specific booking). Server verifies ownership before allowing subscription.

- Message ordering: Within a single channel, events are delivered in order of publication. The pub/sub (Redis) preserves order per channel. If multiple server instances, a given channel is always routed to the same instance to maintain order (via consistent hashing on channel name).

- Offline queuing: For critical events like booking status changes, if the user is offline, the event can be stored in a short-lived queue (Redis list with TTL) and delivered upon reconnection. Non-critical chat messages may be discarded if recipient offline (chat history retrieved via API on reconnect).

- Rate limiting: Enforced per connection or per user ID. Excess attempts result in temporary suspension (e.g., 5 minutes). Limits can be tuned.

- Scaling: Initially single server instance can handle development and early production (up to a few thousand connections). For 10,000+ connections, multiple instances behind a load balancer with sticky sessions (based on connection ID or user ID). Subscription state stored in Redis for cross-instance visibility.

- Heartbeats: Both server and client send pings/pongs to detect dead connections. Default interval 30 seconds. If no ping received for 90 seconds, connection closed.

- Backpressure: Implemented via configurable buffer limits per connection. If buffer exceeds, either drop oldest non-critical events or close connection. Client should handle missed events by re-fetching state.

- Authorization: Simple ownership checks: user can subscribe to channels where they are the resource owner (event organizer for their event, vendor for their bookings, participant in chat conversation). Admin users may have broader access.

- Event schema: All real-time events follow an envelope:
  ```json
  {
    "eventId": "uuid",
    "eventType": "booking.status_changed",
    "timestamp": "2026-04-07T12:34:56Z",
    "channel": "booking:123",
    "data": { ... event-specific payload ... }
  }
  ```

- The system does not currently address end-to-end encryption for chat messages; TLS is used in transit to server. Messages are stored in database (for persistence) but could be encrypted at rest separately. End-to-end encryption is out of scope.

- Internationalization: Event types and messages are in English initially. Could support Urdu later.

- The system will monitor connection count and resource usage. Alert if connections exceed expected thresholds (e.g., >80% capacity).

- Conformity to constitutional standards:
  - Uses constitutional event-driven patterns (domain events).
  - Follows event envelope standard.
  - Rate limiting aligns with constitution (Section VIII mentions rate limiting on public endpoints, though these are authenticated).
  - Async-first: all handlers are async.
  - Structured logging with Pino.

- The real-time infrastructure may later be replaced with a dedicated message broker like NATS JetStream for Phase 2 scaling. The current design uses Redis for simplicity, but the API should be abstracted to allow swapping.

- The chat use case (`006-ai-agent-chat`) already uses SSE for streaming AI responses. That is a separate endpoint (`/api/v1/ai/chat/stream`) focused on streaming a single conversation turn. The real-time updates feature here is about bidirectional messaging and event streaming for multiple event types, potentially using WebSocket for full duplex. They can coexist without conflict.

- The system should not expose internal errors to clients. Errors are logged and a generic "connection error" may be shown.

- Offline queuing TTL: 5 minutes. If user reconnects within 5 minutes, they get missed events; otherwise, they fetch missed updates via standard API calls (polling fallback).

- The system should handle client-side time synchronization: event timestamps are server-generated; clients display relative times.
