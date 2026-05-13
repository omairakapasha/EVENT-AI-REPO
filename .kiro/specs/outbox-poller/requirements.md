# Requirements Document

## Introduction

The outbox poller feature closes a reliability gap in the Event-AI backend's event-driven architecture. Domain events are already persisted to the `domain_events` table within the same database transaction as the business change (the outbox pattern). In-process listeners then fire SSE pushes and notification creation. However, if the process crashes or restarts between the DB commit and listener execution, the event is durably stored but its side effects are silently lost forever.

This feature adds a `processed_at` column to `domain_events`, marks events processed after successful in-process listener execution, and introduces a background poller that recovers any events missed due to crashes. Listeners must be made idempotent so that an event fired both in-process and by the poller does not produce duplicate notifications or SSE messages.

## Glossary

- **Domain_Event**: A record in the `domain_events` table representing a business fact that has occurred (e.g. `booking.confirmed`). Append-only; never deleted.
- **Outbox_Poller**: The background asyncio task that periodically queries for unprocessed domain events and re-fires them through the event bus.
- **Event_Bus**: The `EventBusService` singleton (`src/services/event_bus_service.py`) responsible for persisting and dispatching domain events to registered listeners.
- **Listener**: An async callable registered with the Event_Bus via `event_bus.subscribe()` that reacts to a specific event type (e.g. `notification_service.handle`).
- **processed_at**: A nullable UTC datetime column on `domain_events`. `NULL` means the event has not yet been successfully processed by all listeners. A non-null value means processing completed.
- **Grace_Period**: A 30-second window after `created_at` during which the Outbox_Poller deliberately skips an event, giving in-process listeners the opportunity to fire first.
- **Idempotency_Key**: The combination of `domain_events.id` and the listener's action type, used to detect and suppress duplicate side effects.
- **Notification_Service**: The `notification_service` singleton (`src/services/notification_service.py`) that creates `notifications` table records.
- **SSE_Manager**: The `SSEConnectionManager` singleton on `app.state.connection_manager` that pushes real-time events to connected browser clients.
- **Alembic_Migration**: A versioned, reversible database schema change managed by Alembic in `packages/backend/alembic/versions/`.

---

## Requirements

### Requirement 1: Add `processed_at` Column to `domain_events`

**User Story:** As a backend engineer, I want a `processed_at` column on `domain_events`, so that the system can distinguish events that have been fully processed from those that have not.

#### Acceptance Criteria

1. THE `domain_events` table SHALL contain a `processed_at` column of type `TIMESTAMP WITH TIME ZONE` that is nullable.
2. WHEN a new Domain_Event row is inserted, THE `domain_events` table SHALL store `NULL` in `processed_at` by default.
3. THE `DomainEvent` SQLModel class SHALL expose `processed_at` as an `Optional[datetime]` field with a default of `None`.
4. THE Alembic_Migration SHALL add the `processed_at` column in its `upgrade()` function.
5. THE Alembic_Migration SHALL remove the `processed_at` column in its `downgrade()` function, restoring the table to its prior state.
6. WHEN the migration is applied to a database that already contains Domain_Event rows, THE Alembic_Migration SHALL set `processed_at = NULL` for all pre-existing rows.

---

### Requirement 2: Mark Events Processed After In-Process Listener Execution

**User Story:** As a backend engineer, I want the Event_Bus to mark a domain event as processed after all in-process listeners complete successfully, so that the Outbox_Poller does not redundantly re-fire events that were already handled.

#### Acceptance Criteria

1. WHEN all Listeners registered for an event type complete without raising an exception, THE Event_Bus SHALL set `processed_at = now()` on the corresponding Domain_Event row within the same database session.
2. WHEN at least one Listener raises an exception during in-process execution, THE Event_Bus SHALL leave `processed_at` as `NULL` on the Domain_Event row.
3. WHEN an event type has no registered Listeners, THE Event_Bus SHALL set `processed_at = now()` on the Domain_Event row immediately after persistence.
4. THE Event_Bus SHALL persist the `processed_at` update within the same database transaction as the Domain_Event insert, so that the mark is atomic with the business change.
5. WHEN the database session is rolled back before commit, THE Event_Bus SHALL NOT persist a `processed_at` value for that Domain_Event.

---

### Requirement 3: Outbox Poller Background Task

**User Story:** As a backend engineer, I want a background poller that recovers unprocessed domain events, so that side effects (SSE pushes, notifications) are eventually delivered even if the process crashed before in-process listeners could fire.

#### Acceptance Criteria

1. THE Outbox_Poller SHALL run as an asyncio background task registered in the FastAPI lifespan context manager in `src/config/database.py`.
2. THE Outbox_Poller SHALL query `domain_events` for rows where `processed_at IS NULL AND created_at < now() - interval '30 seconds'` on each polling cycle.
3. THE Outbox_Poller SHALL execute one polling cycle every 30 seconds.
4. WHEN the Outbox_Poller finds unprocessed Domain_Events, THE Outbox_Poller SHALL dispatch each event through the Event_Bus listeners in the order of `created_at ASC`.
5. WHEN the Outbox_Poller successfully dispatches a Domain_Event, THE Outbox_Poller SHALL set `processed_at = now()` on that row and commit the update.
6. WHEN a Listener raises an exception during poller-triggered dispatch, THE Outbox_Poller SHALL log the error, leave `processed_at` as `NULL` for that Domain_Event, and continue processing the remaining unprocessed events.
7. WHEN the FastAPI application shuts down, THE Outbox_Poller background task SHALL be cancelled and awaited to allow clean shutdown.
8. THE Outbox_Poller SHALL open its own database session using `async_session_maker` and SHALL NOT reuse the session of any HTTP request handler.
9. WHEN no unprocessed Domain_Events are found, THE Outbox_Poller SHALL log a debug-level message and wait for the next polling interval without raising an exception.
10. IF the database is unreachable during a polling cycle, THEN THE Outbox_Poller SHALL log an error-level message and resume polling on the next scheduled interval without crashing the process.

---

### Requirement 4: Idempotent Listener Execution

**User Story:** As a backend engineer, I want all event listeners to be idempotent, so that an event fired both in-process and by the Outbox_Poller does not create duplicate notifications or duplicate SSE messages.

#### Acceptance Criteria

1. WHEN the Notification_Service receives a domain event whose `domain_event_id` already exists in the `notifications` table, THE Notification_Service SHALL skip notification creation and return without error.
2. WHEN the SSE_Manager receives a push request for a Domain_Event that has already been pushed to the same user within the same process session, THE SSE_Manager SHALL discard the duplicate push silently.
3. THE Notification_Service SHALL use the Domain_Event `id` as an idempotency key when inserting notification records, enforcing uniqueness at the database level via a unique constraint or an `ON CONFLICT DO NOTHING` clause.
4. WHEN a Listener is invoked by the Outbox_Poller for a Domain_Event that was already processed in-process, THE Listener SHALL complete without creating duplicate side effects.
5. THE idempotency check in the Notification_Service SHALL be performed within the same database transaction as the notification insert, preventing race conditions between concurrent poller cycles.

---

### Requirement 5: Poller Does Not Re-Fire Already-Processed Events

**User Story:** As a backend engineer, I want the Outbox_Poller to skip events that are already marked processed, so that successfully handled events are never dispatched a second time by the poller.

#### Acceptance Criteria

1. WHEN a Domain_Event has a non-null `processed_at` value, THE Outbox_Poller SHALL NOT include that event in any polling query result.
2. THE Outbox_Poller query SHALL filter exclusively on `processed_at IS NULL`, ensuring processed events are excluded at the database level rather than in application code.
3. WHEN the Event_Bus marks a Domain_Event as processed during in-process execution and the Outbox_Poller runs concurrently, THE Outbox_Poller SHALL NOT dispatch the same Domain_Event a second time.
4. THE Outbox_Poller SHALL use a `SELECT ... FOR UPDATE SKIP LOCKED` query to prevent two concurrent poller instances (e.g. during a rolling restart) from claiming the same unprocessed Domain_Event simultaneously.

---

### Requirement 6: Grace Period Prevents Double-Firing Under Normal Conditions

**User Story:** As a backend engineer, I want a 30-second grace period before the poller picks up an event, so that in-process listeners have time to fire and mark the event processed before the poller considers it a candidate for recovery.

#### Acceptance Criteria

1. THE Outbox_Poller SHALL only consider Domain_Events where `created_at < now() - interval '30 seconds'`, excluding events created within the last 30 seconds from each polling query.
2. WHEN an in-process Listener fires and marks `processed_at` within 30 seconds of `created_at`, THE Outbox_Poller SHALL NOT dispatch that Domain_Event on any subsequent polling cycle.
3. WHEN a Domain_Event is created and the process does not crash, THE Outbox_Poller SHALL NOT dispatch that event during the Grace_Period window even if `processed_at` is still `NULL`.
4. WHEN a Domain_Event remains unprocessed after the Grace_Period has elapsed, THE Outbox_Poller SHALL treat it as a missed event and dispatch it on the next polling cycle.

---

### Requirement 7: Observability and Logging

**User Story:** As a backend engineer, I want structured log output from the Outbox_Poller and updated Event_Bus, so that I can monitor recovery activity and diagnose delivery failures in production.

#### Acceptance Criteria

1. WHEN the Outbox_Poller dispatches a recovered Domain_Event, THE Outbox_Poller SHALL emit a structured log entry at `info` level containing `event_id`, `event_type`, and `created_at`.
2. WHEN the Outbox_Poller fails to dispatch a Domain_Event due to a Listener exception, THE Outbox_Poller SHALL emit a structured log entry at `error` level containing `event_id`, `event_type`, and the exception message.
3. WHEN the Event_Bus marks a Domain_Event as processed after in-process execution, THE Event_Bus SHALL emit a structured log entry at `debug` level containing `event_id` and `event_type`.
4. WHEN the Outbox_Poller completes a polling cycle that recovered one or more events, THE Outbox_Poller SHALL emit a structured log entry at `info` level containing the count of recovered events.
5. THE Outbox_Poller and Event_Bus SHALL use `structlog` for all log output, consistent with the existing logging convention in the codebase.
