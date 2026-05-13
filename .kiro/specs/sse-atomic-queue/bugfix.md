# Bugfix Requirements Document

## Introduction

The `SSEConnectionManager.push()` method in `packages/backend/src/services/sse_manager.py` uses a non-atomic evict-oldest pattern when a user's queue is full. When multiple coroutines call `push()` concurrently for the same user (e.g., a `booking.created` event triggering both an SSE push and a notification push in parallel), each coroutine independently observes `QueueFull`, each calls `q.get_nowait()` to evict one message, and each then inserts its new message. This causes N evictions for N concurrent pushes when only 1 eviction was needed — silently losing more messages than expected and corrupting the `dropped_count` counter.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN N concurrent `push()` calls are made for the same user whose queue is at capacity THEN the system evicts N messages instead of the minimum required (≤ N), causing excess message loss.

1.2 WHEN multiple coroutines each observe `asyncio.QueueFull` and each call `q.get_nowait()` before any of them calls `q.put_nowait()` THEN the system removes more items from the queue than the number of new items being inserted, leaving the queue below capacity.

1.3 WHEN excess evictions occur THEN the system increments `dropped_count` by N (once per concurrent push) even though only 1 eviction was necessary, producing an inflated and inaccurate dropped message count.

1.4 WHEN the queue is at capacity and a single `push()` call evicts one message and inserts a new one THEN the system correctly maintains queue size at `maxsize`, but this correctness is not guaranteed under concurrent load.

### Expected Behavior (Correct)

2.1 WHEN N concurrent `push()` calls are made for the same user whose queue is at capacity THEN the system SHALL ensure exactly N messages are in the queue after all pushes complete (no more, no less than `maxsize`).

2.2 WHEN the evict-and-insert operation is performed THEN the system SHALL execute it atomically so that no other concurrent push can interleave between the eviction and the insertion for the same user queue.

2.3 WHEN a message is evicted to make room for a new one THEN the system SHALL increment `dropped_count` by exactly 1 per eviction that actually occurs, accurately reflecting the true number of dropped messages.

2.4 WHEN the queue is at capacity and a new message arrives THEN the system SHALL drop the oldest message and enqueue the newest message without the queue ever exceeding `maxsize`.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user's queue is below capacity THEN the system SHALL CONTINUE TO enqueue new messages immediately without any eviction.

3.2 WHEN a user connects via SSE THEN the system SHALL CONTINUE TO create a per-user queue with the configured `maxsize`.

3.3 WHEN a user disconnects from SSE THEN the system SHALL CONTINUE TO remove their queue and clean up the connection entry.

3.4 WHEN a user has no active SSE connections THEN the system SHALL CONTINUE TO silently ignore `push()` calls for that user.

3.5 WHEN a user has multiple concurrent SSE connections THEN the system SHALL CONTINUE TO push messages to all of their active queues.

3.6 WHEN `dropped_count` is queried for a user THEN the system SHALL CONTINUE TO return the cumulative count of evicted messages for that user since the manager was initialised.

3.7 WHEN the SSE stream is consumed by a client THEN the system SHALL CONTINUE TO deliver messages in FIFO order from the queue.
