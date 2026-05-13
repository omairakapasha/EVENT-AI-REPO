# Bugfix Requirements Document

## Introduction

Six violations were identified in `packages/backend/src/` spanning four files. The violations range from a critical runtime `NameError` that breaks every protected route, to banned coding practices (`raw os.environ`), missing security dependency usage, non-conformant error envelopes, and absent return type hints. Left unaddressed, the critical violation makes the entire authenticated API non-functional; the major violations introduce security gaps and inconsistent API contracts; the minor violation reduces type-safety across the CDN service.

Affected files:
- `src/middleware/auth.middleware.py` — missing `select` import (CRITICAL)
- `src/services/cdn_service.py` — raw `os.getenv` usage; missing return type hints (MAJOR + MINOR)
- `src/api/v1/admin/approvals.py` — inline role check instead of `require_admin`; non-envelope error responses (MAJOR)
- `src/api/v1/admin/vendors.py` — non-envelope error response (MAJOR)

---

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN any protected route is accessed and `get_current_user` in `auth.middleware.py` executes `select(User)` THEN the system raises a `NameError: name 'select' is not defined` because `select` is never imported from `sqlalchemy`

1.2 WHEN `CDNService` is instantiated (at module import time via the `cdn_service` singleton) THEN the system reads CDN configuration directly via `os.getenv(...)` in `__init__` and `_init_s3_client`, violating the project-wide ban on raw `os.environ` / `os.getenv`

1.3 WHEN `GET /api/v1/admin/approvals/` is called by a non-admin authenticated user THEN the system raises `HTTPException(status_code=403, detail="Requires administrator privileges")` with a plain string `detail` instead of the required error envelope `{"code": "AUTH_FORBIDDEN", "message": "..."}`

1.4 WHEN `POST /api/v1/admin/approvals/{approval_id}/process` is called by a non-admin authenticated user THEN the system raises `HTTPException(status_code=403, detail="Requires administrator privileges")` with a plain string `detail` instead of the required error envelope

1.5 WHEN `POST /api/v1/admin/approvals/{approval_id}/process` is called with a non-existent `approval_id` THEN the system raises `HTTPException(status_code=404, detail="Approval request not found")` with a plain string `detail` instead of the required error envelope `{"code": "NOT_FOUND_APPROVAL", "message": "..."}`

1.6 WHEN `PATCH /api/v1/admin/vendors/{vendor_id}/status` is called with a non-existent `vendor_id` THEN the system raises `HTTPException(status_code=404, detail="NOT_FOUND_VENDOR")` with a plain string `detail` instead of the required error envelope `{"code": "NOT_FOUND_VENDOR", "message": "Vendor not found."}`

1.7 WHEN `list_pending_approvals` or `process_approval` in `approvals.py` is called THEN the system performs an inline `if current_user.role != "admin"` check using `Depends(get_current_user)` instead of using the existing `require_admin` dependency from `src/api/deps.py`, duplicating role-check logic that is already centralised

1.8 WHEN any method on `CDNService` (`__init__`, `_init_s3_client`, `_get_extension`, `validate_file_type`) is called THEN the system provides no return type annotations, reducing static analysis coverage and violating the project convention of full type hints on all functions

### Expected Behavior (Correct)

2.1 WHEN any protected route is accessed and `get_current_user` in `auth.middleware.py` executes `select(User)` THEN the system SHALL resolve `select` correctly because `from sqlalchemy import select` is present in the module imports, and the route SHALL proceed without a `NameError`

2.2 WHEN `CDNService` is instantiated THEN the system SHALL read CDN configuration exclusively via `get_settings()` (the `@lru_cache` `Settings` instance from `src/config/database.py`), with all CDN fields (`cdn_provider`, `cdn_bucket_name`, `cdn_public_url`, `cdn_enabled`, `cdn_endpoint_url`, `cdn_access_key_id`, `cdn_secret_access_key`, `cdn_region`, `cdn_public_endpoint`) declared as `Optional[str]` / `bool` fields on the `Settings` class

2.3 WHEN `GET /api/v1/admin/approvals/` is called by a non-admin authenticated user THEN the system SHALL raise `HTTPException(status_code=403, detail={"code": "AUTH_FORBIDDEN", "message": "Administrator privileges required."})` conforming to the project error envelope

2.4 WHEN `POST /api/v1/admin/approvals/{approval_id}/process` is called by a non-admin authenticated user THEN the system SHALL raise `HTTPException(status_code=403, detail={"code": "AUTH_FORBIDDEN", "message": "Administrator privileges required."})` conforming to the project error envelope

2.5 WHEN `POST /api/v1/admin/approvals/{approval_id}/process` is called with a non-existent `approval_id` THEN the system SHALL raise `HTTPException(status_code=404, detail={"code": "NOT_FOUND_APPROVAL", "message": "Approval request not found."})` conforming to the project error envelope

2.6 WHEN `PATCH /api/v1/admin/vendors/{vendor_id}/status` is called with a non-existent `vendor_id` THEN the system SHALL raise `HTTPException(status_code=404, detail={"code": "NOT_FOUND_VENDOR", "message": "Vendor not found."})` conforming to the project error envelope

2.7 WHEN `list_pending_approvals` or `process_approval` in `approvals.py` is invoked THEN the system SHALL enforce admin access exclusively via `Depends(require_admin)` from `src/api/deps.py`, with all inline `if current_user.role != "admin"` checks and the `Depends(get_current_user)` dependency removed from those endpoints

2.8 WHEN any method on `CDNService` is defined THEN the system SHALL carry explicit return type annotations: `__init__ -> None`, `_init_s3_client -> None`, `_get_extension -> Optional[str]`, `validate_file_type -> bool`

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a valid JWT is presented on any protected route THEN the system SHALL CONTINUE TO authenticate the user successfully and return the expected response

3.2 WHEN `CDNService.generate_upload_url` is called with valid credentials and CDN enabled THEN the system SHALL CONTINUE TO generate and return a pre-signed upload URL and file key

3.3 WHEN `CDNService.get_public_url` is called with a file key THEN the system SHALL CONTINUE TO return the correct public URL

3.4 WHEN `GET /api/v1/admin/approvals/` is called by an authenticated admin user THEN the system SHALL CONTINUE TO return the paginated list of pending approvals

3.5 WHEN `POST /api/v1/admin/approvals/{approval_id}/process` is called by an authenticated admin user with a valid `approval_id` THEN the system SHALL CONTINUE TO process the approval and return the updated `ApprovalRequestRead` response

3.6 WHEN `GET /api/v1/admin/vendors/` is called by an authenticated admin user THEN the system SHALL CONTINUE TO return the paginated, filterable vendor list

3.7 WHEN `PATCH /api/v1/admin/vendors/{vendor_id}/status` is called by an authenticated admin user with a valid `vendor_id` THEN the system SHALL CONTINUE TO update the vendor status, emit the domain event, and return the updated vendor data

3.8 WHEN `require_admin` in `src/api/deps.py` is called with a non-admin user THEN the system SHALL CONTINUE TO raise `HTTPException(403)` as it does today (this dependency is not modified)

3.9 WHEN `CDNService` is instantiated with CDN disabled or boto3 unavailable THEN the system SHALL CONTINUE TO set `self.s3_client = None` and log the appropriate warning without raising an exception
