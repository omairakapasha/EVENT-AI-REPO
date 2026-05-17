# Bugfix Requirements Document

## Introduction

`BookingService._acquire_lock` uses a plain `SELECT` (via `_get_availability_row`) followed by a conditional `UPDATE`/`INSERT` to lock a `vendor_availability` row. Because no row-level database lock is held between the read and the write, two concurrent `POST /api/v1/bookings` requests for the same `vendor_id + service_id + event_date` can both observe the slot as available, both pass the status check, and both write `status=locked` — resulting in two bookings for the same slot (double-booking).

The fix replaces the plain `SELECT` inside `_acquire_lock` with `SELECT ... FOR UPDATE NOWAIT`, which acquires a PostgreSQL exclusive row-level lock atomically. A concurrent request that cannot immediately acquire the lock receives a lock-contention error that is mapped to HTTP 409 `CONFLICT_DATE_BEING_PROCESSED`. For slots that do not yet have a row, the first `INSERT` wins via the `uq_vendor_service_date` unique constraint; a concurrent insert is rejected and also mapped to 409.

---

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN two concurrent `POST /api/v1/bookings` requests arrive with identical `vendor_id`, `service_id`, and `event_date` THEN the system allows both requests to read the availability row as `available` (or absent) before either has written a lock, causing both to proceed past the availability check simultaneously.

1.2 WHEN both concurrent requests reach the write step of `_acquire_lock` after independently reading the slot as available THEN the system writes `status=locked` for both requests without detecting the conflict, resulting in two `VendorAvailability` rows (or two updates) and ultimately two `Booking` records for the same slot.

1.3 WHEN a `vendor_availability` row does not yet exist for the requested slot and two concurrent requests both reach the `INSERT` branch of `_acquire_lock` THEN the system may raise an unhandled `IntegrityError` on the `uq_vendor_service_date` unique constraint instead of returning a clean 409 response.

### Expected Behavior (Correct)

2.1 WHEN two concurrent `POST /api/v1/bookings` requests arrive with identical `vendor_id`, `service_id`, and `event_date` THEN the system SHALL allow only one request to acquire the row-level lock; the second request SHALL immediately receive HTTP 409 with error code `CONFLICT_DATE_BEING_PROCESSED` without waiting.

2.2 WHEN a request successfully acquires the `SELECT ... FOR UPDATE NOWAIT` lock on an available slot THEN the system SHALL atomically transition the slot to `status=locked` and proceed to create the booking, guaranteeing no other concurrent request can observe the slot as available until the transaction commits or rolls back.

2.3 WHEN a `vendor_availability` row does not yet exist for the requested slot and a concurrent `INSERT` races on the `uq_vendor_service_date` unique constraint THEN the system SHALL catch the `IntegrityError` and return HTTP 409 with error code `CONFLICT_DATE_BEING_PROCESSED` instead of propagating an unhandled 500 error.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a single (non-concurrent) `POST /api/v1/bookings` request is made for an available slot THEN the system SHALL CONTINUE TO acquire the lock, create the booking, and return HTTP 201 with the new booking data.

3.2 WHEN a booking request is made for a slot whose `status` is already `booked` THEN the system SHALL CONTINUE TO return HTTP 409 with error code `CONFLICT_DATE_UNAVAILABLE`.

3.3 WHEN a booking request is made for a slot whose `status` is `blocked` THEN the system SHALL CONTINUE TO return HTTP 409 with error code `CONFLICT_DATE_UNAVAILABLE`.

3.4 WHEN a booking request is made for a slot that has an active (non-expired) `locked` status held by a different request THEN the system SHALL CONTINUE TO return HTTP 409 with error code `CONFLICT_DATE_BEING_PROCESSED`.

3.5 WHEN a booking request is made for a slot that has an expired `locked` status THEN the system SHALL CONTINUE TO treat the slot as available and proceed with locking and booking.

3.6 WHEN `check_availability` is called for any slot THEN the system SHALL CONTINUE TO return the correct availability status without acquiring any write lock (read-only path is unaffected).

3.7 WHEN `VendorAvailabilityService.upsert_availability` or `bulk_upsert_availability` is called by a vendor to set a slot to `available` or `blocked` THEN the system SHALL CONTINUE TO perform the upsert correctly (these paths are a secondary concern and must not regress).

---

## Bug Condition Pseudocode

### Bug Condition Function

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type BookingRequest pair (R1, R2)
  OUTPUT: boolean

  // Returns true when two requests race on the same slot
  RETURN R1.vendor_id  = R2.vendor_id
     AND R1.service_id = R2.service_id
     AND R1.event_date = R2.event_date
     AND R1 and R2 arrive concurrently within the SELECT→UPDATE/INSERT window
END FUNCTION
```

### Fix-Checking Property

```pascal
// Property: Fix Checking — only one booking may be created per slot
FOR ALL (R1, R2) WHERE isBugCondition(R1, R2) DO
  (result1, result2) ← concurrent(_acquire_lock'(R1), _acquire_lock'(R2))
  ASSERT exactly_one_of(result1, result2) succeeds
  AND    the_other returns HTTP 409 CONFLICT_DATE_BEING_PROCESSED
END FOR
```

### Preservation Property

```pascal
// Property: Preservation Checking — non-concurrent requests are unaffected
FOR ALL R WHERE NOT isBugCondition(R) DO
  ASSERT _acquire_lock'(R) = _acquire_lock(R)   // same outcome as before the fix
END FOR
```
