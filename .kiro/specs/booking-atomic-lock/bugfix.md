# Bugfix Requirements Document

## Introduction

`BookingService._acquire_lock` in `packages/backend/src/services/booking_service.py` contains a classic check-then-act race condition. It reads the `vendor_availability` row with a plain `SELECT` and then writes a `LOCKED` status in a separate statement. Under concurrent load, two requests for the same `(vendor_id, service_id, date)` slot can both pass the availability check before either write lands, resulting in two bookings being created for the same slot.

A secondary TOCTOU window exists in `_cleanup_expired_locks` (runs every 60 s): it can expire a lock between the moment a user acquires it and the moment `create_booking` commits, allowing a second user to acquire the same slot in that gap.

Neither a DB-level unique constraint on active bookings nor a row-level lock currently prevents these races.

---

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN two concurrent requests call `_acquire_lock` for the same `(vendor_id, service_id, date)` THEN both read the availability row as unlocked before either write completes, and both proceed to write a `LOCKED` row

1.2 WHEN both concurrent requests successfully acquire the lock THEN both proceed through `create_booking` and two `Booking` rows are inserted for the same vendor/service/date slot

1.3 WHEN `_cleanup_expired_locks` expires a lock between the time a user acquired it and the time `create_booking` commits THEN a second concurrent user can acquire the same slot and a duplicate booking is created

1.4 WHEN a `LOCKED` availability row is written by two concurrent requests THEN no database-level constraint prevents both inserts from succeeding, because there is no partial unique index on active bookings

### Expected Behavior (Correct)

2.1 WHEN two concurrent requests call `_acquire_lock` for the same `(vendor_id, service_id, date)` THEN the database SHALL serialize them at the row level via `SELECT FOR UPDATE`, so only one request proceeds and the other receives a 409 `CONFLICT_DATE_BEING_PROCESSED` response

2.2 WHEN `create_booking` is about to commit THEN the system SHALL re-validate within the same transaction that the lock row still belongs to the requesting user and has not expired, and SHALL raise 409 if the lock is no longer valid

2.3 WHEN a booking is being created THEN the system SHALL enforce a partial unique index `UNIQUE (vendor_id, service_id, date) WHERE status NOT IN ('CANCELLED', 'REJECTED', 'AVAILABLE')` at the database level as a last-resort safety net against duplicate active bookings

2.4 WHEN `_acquire_lock` reads the availability row THEN it SHALL use `SELECT FOR UPDATE` (or `SELECT FOR UPDATE SKIP LOCKED`) so that the read and the subsequent write are atomic within the transaction

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a single (non-concurrent) booking request is made for an available slot THEN the system SHALL CONTINUE TO create the booking successfully and return the new `Booking` object

3.2 WHEN a slot is already in `BOOKED` status THEN the system SHALL CONTINUE TO reject the request with 409 `CONFLICT_DATE_UNAVAILABLE`

3.3 WHEN a slot is in `BLOCKED` status THEN the system SHALL CONTINUE TO reject the request with 409 `CONFLICT_DATE_UNAVAILABLE`

3.4 WHEN a slot has an active (non-expired) lock held by a different user THEN the system SHALL CONTINUE TO reject the request with 409 `CONFLICT_DATE_BEING_PROCESSED`

3.5 WHEN a booking is cancelled or rejected THEN the system SHALL CONTINUE TO release the availability slot back to `AVAILABLE`

3.6 WHEN `_cleanup_expired_locks` runs THEN the system SHALL CONTINUE TO release genuinely expired locks, but SHALL NOT be the sole enforcement mechanism for preventing double-bookings

3.7 WHEN `check_availability` is called for a slot with an expired lock THEN the system SHALL CONTINUE TO report the slot as available

---

## Bug Condition Pseudocode

### Bug Condition Function

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type ConcurrentBookingRequest
         X.request_A = (vendor_id, service_id, date, user_id_A)
         X.request_B = (vendor_id, service_id, date, user_id_B)
  OUTPUT: boolean

  // Bug fires when two requests target the same slot concurrently
  // and the availability row is not locked at the DB level during the read
  RETURN X.request_A.vendor_id  = X.request_B.vendor_id
     AND X.request_A.service_id = X.request_B.service_id
     AND X.request_A.date       = X.request_B.date
     AND concurrent(X.request_A, X.request_B)
     AND NOT select_for_update_used()
END FUNCTION
```

### Fix-Checking Property

```pascal
// Property: at most one concurrent booking for the same slot succeeds
FOR ALL X WHERE isBugCondition(X) DO
  (result_A, result_B) ← asyncio.gather(create_booking'(X.request_A),
                                         create_booking'(X.request_B))
  success_count ← count(r for r in [result_A, result_B] if r.status_code = 201)
  conflict_count ← count(r for r in [result_A, result_B] if r.status_code = 409)
  ASSERT success_count  = 1
  ASSERT conflict_count = 1
END FOR
```

### Preservation Property

```pascal
// Property: non-concurrent or non-conflicting bookings are unaffected
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT create_booking'(X) = create_booking(X)
END FOR
```
