# Bugfix Requirements Document

## Introduction

The `BookingBase` model in `packages/backend/src/models/booking.py` defaults the `currency` field to `"USD"`. This platform is built exclusively for the Pakistani market (weddings, mehndi, baraat, walima events). All vendors price services in PKR and all financial reporting is in PKR. The USD default causes meaningless revenue figures in admin stats, a mismatch between vendor pricing and booking records, and incorrect revenue calculations across the platform.

The fix has three parts: change the default currency to `"PKR"`, add a currency allowlist to `BookingCreate` to prevent invalid codes, and migrate existing `NULL` or `"USD"` records to `"PKR"` via an Alembic data migration.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a booking is created without an explicit `currency` value THEN the system stores `"USD"` as the currency

1.2 WHEN admin stats aggregate booking revenue THEN the system reports totals denominated in `"USD"`, which is meaningless for a PKR-only operation

1.3 WHEN a vendor prices a service in PKR and a booking is created without specifying currency THEN the system records the booking with `"USD"`, creating a currency mismatch between the service price and the booking record

1.4 WHEN `BookingCreate` receives an arbitrary string for `currency` (e.g., `"DOLLAR"`, `"XYZ"`, `""`) THEN the system accepts and stores the invalid currency code without validation

1.5 WHEN existing booking records have `currency = "USD"` or `currency = NULL` THEN the system continues to report those records in USD, perpetuating incorrect historical revenue data

### Expected Behavior (Correct)

2.1 WHEN a booking is created without an explicit `currency` value THEN the system SHALL store `"PKR"` as the default currency

2.2 WHEN admin stats aggregate booking revenue THEN the system SHALL report totals denominated in `"PKR"` for bookings that did not specify a currency

2.3 WHEN a vendor prices a service in PKR and a booking is created without specifying currency THEN the system SHALL record the booking with `"PKR"`, keeping the service price and booking currency consistent

2.4 WHEN `BookingCreate` receives an invalid `currency` value (e.g., `"DOLLAR"`, `"XYZ"`, `""`) THEN the system SHALL reject the request with a validation error (HTTP 422)

2.5 WHEN the Alembic data migration runs THEN the system SHALL update all existing booking records where `currency` is `NULL` or `"USD"` to `"PKR"`

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a booking is created with an explicit valid ISO 4217 currency code (e.g., `"USD"`, `"EUR"`, `"GBP"`) THEN the system SHALL CONTINUE TO store and return that exact currency code

3.2 WHEN a booking is created with `currency = "PKR"` explicitly supplied THEN the system SHALL CONTINUE TO store `"PKR"` without modification

3.3 WHEN booking records that already have a valid non-USD currency (e.g., `"EUR"`) exist before the migration THEN the system SHALL CONTINUE TO preserve those values unchanged after the migration runs

3.4 WHEN all other booking fields (status, payment_status, unit_price, total_price, event_date, etc.) are submitted THEN the system SHALL CONTINUE TO validate and store them as before

3.5 WHEN the booking state machine transitions (pending → confirmed → in_progress → completed) are executed THEN the system SHALL CONTINUE TO enforce the same transition rules regardless of the currency value

---

## Bug Condition Pseudocode

**Bug Condition Function** — identifies inputs that trigger the bug:

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type BookingCreate
  OUTPUT: boolean

  // Bug fires when currency is absent (defaults to USD) or is an invalid code
  RETURN X.currency IS NOT PROVIDED
      OR X.currency NOT IN VALID_ISO_4217_CODES
END FUNCTION
```

**Property: Fix Checking** — correct behavior for buggy inputs:

```pascal
// Property: Fix Checking — Default Currency
FOR ALL X WHERE X.currency IS NOT PROVIDED DO
  result ← create_booking'(X)
  ASSERT result.currency = "PKR"
END FOR

// Property: Fix Checking — Invalid Currency Rejection
FOR ALL X WHERE X.currency NOT IN VALID_ISO_4217_CODES DO
  result ← create_booking'(X)
  ASSERT result IS ValidationError(422)
END FOR
```

**Property: Preservation Checking** — non-buggy inputs must be unaffected:

```pascal
// Property: Preservation Checking
FOR ALL X WHERE X.currency IN VALID_ISO_4217_CODES DO
  ASSERT create_booking(X).currency = create_booking'(X).currency
END FOR
```

Where:
- **F** = `create_booking` — original function (defaults to `"USD"`, no allowlist)
- **F'** = `create_booking'` — fixed function (defaults to `"PKR"`, allowlist enforced)
