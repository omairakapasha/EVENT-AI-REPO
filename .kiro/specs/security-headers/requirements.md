# Requirements Document

## Introduction

The FastAPI backend (`packages/backend/src/main.py`) currently sends no HTTP security headers. The OWASP Secure Headers Project and industry standards require a defined set of headers on every HTTP response to mitigate XSS, clickjacking, MIME-sniffing, and information-leakage attacks. Because the backend uses httpOnly cookies for authentication, XSS mitigation is especially critical. This feature adds a `SecurityHeadersMiddleware` that injects all required headers on every response, respects headers already set by individual route handlers, and conditionally applies HSTS only in production environments.

## Glossary

- **Middleware**: A FastAPI/Starlette ASGI component that wraps every request/response cycle.
- **SecurityHeadersMiddleware**: The new middleware class defined in `packages/backend/src/middleware/security_headers.py` that injects HTTP security headers.
- **HSTS**: HTTP Strict Transport Security — the `Strict-Transport-Security` response header that instructs browsers to use HTTPS exclusively.
- **CSP**: Content Security Policy — the `Content-Security-Policy` response header that restricts resource loading to mitigate XSS.
- **Route Handler**: A FastAPI path operation function that may set its own response headers before the middleware processes the response.
- **Production Environment**: The runtime state where the `ENVIRONMENT` environment variable is set to the value `production`.
- **Non-Production Environment**: Any runtime state where the `ENVIRONMENT` environment variable is absent or set to any value other than `production`.

## Requirements

### Requirement 1: Security Headers Middleware Module

**User Story:** As a backend engineer, I want a dedicated middleware module for security headers, so that the security concern is isolated, testable, and easy to audit independently of business logic.

#### Acceptance Criteria

1. THE `SecurityHeadersMiddleware` SHALL be defined in `packages/backend/src/middleware/security_headers.py` as a class compatible with FastAPI's `add_middleware` API.
2. THE `SecurityHeadersMiddleware` SHALL be registered in `packages/backend/src/main.py` via `app.add_middleware(SecurityHeadersMiddleware)`.
3. THE `SecurityHeadersMiddleware` SHALL process every HTTP response regardless of route, HTTP method, or response status code.

---

### Requirement 2: Inject X-Content-Type-Options Header

**User Story:** As a security engineer, I want every response to carry `X-Content-Type-Options: nosniff`, so that browsers cannot MIME-sniff responses away from the declared content type.

#### Acceptance Criteria

1. WHEN the `SecurityHeadersMiddleware` processes a response that does not already contain an `X-Content-Type-Options` header, THE `SecurityHeadersMiddleware` SHALL set `X-Content-Type-Options` to `nosniff`.
2. WHEN the `SecurityHeadersMiddleware` processes a response that already contains an `X-Content-Type-Options` header set by a route handler, THE `SecurityHeadersMiddleware` SHALL preserve the existing value without modification.

---

### Requirement 3: Inject X-Frame-Options Header

**User Story:** As a security engineer, I want every response to carry `X-Frame-Options: DENY`, so that the application cannot be embedded in a frame or iframe, preventing clickjacking attacks.

#### Acceptance Criteria

1. WHEN the `SecurityHeadersMiddleware` processes a response that does not already contain an `X-Frame-Options` header, THE `SecurityHeadersMiddleware` SHALL set `X-Frame-Options` to `DENY`.
2. WHEN the `SecurityHeadersMiddleware` processes a response that already contains an `X-Frame-Options` header set by a route handler, THE `SecurityHeadersMiddleware` SHALL preserve the existing value without modification.

---

### Requirement 4: Inject Referrer-Policy Header

**User Story:** As a security engineer, I want every response to carry `Referrer-Policy: strict-origin-when-cross-origin`, so that the full URL is not leaked to third-party origins via the `Referer` header.

#### Acceptance Criteria

1. WHEN the `SecurityHeadersMiddleware` processes a response that does not already contain a `Referrer-Policy` header, THE `SecurityHeadersMiddleware` SHALL set `Referrer-Policy` to `strict-origin-when-cross-origin`.
2. WHEN the `SecurityHeadersMiddleware` processes a response that already contains a `Referrer-Policy` header set by a route handler, THE `SecurityHeadersMiddleware` SHALL preserve the existing value without modification.

---

### Requirement 5: Inject Permissions-Policy Header

**User Story:** As a security engineer, I want every response to carry a `Permissions-Policy` header that disables camera, microphone, and geolocation access, so that the application cannot silently request sensitive browser APIs.

#### Acceptance Criteria

1. WHEN the `SecurityHeadersMiddleware` processes a response that does not already contain a `Permissions-Policy` header, THE `SecurityHeadersMiddleware` SHALL set `Permissions-Policy` to `camera=(), microphone=(), geolocation=()`.
2. WHEN the `SecurityHeadersMiddleware` processes a response that already contains a `Permissions-Policy` header set by a route handler, THE `SecurityHeadersMiddleware` SHALL preserve the existing value without modification.

---

### Requirement 6: Inject Content-Security-Policy Header

**User Story:** As a security engineer, I want every response to carry a restrictive `Content-Security-Policy` header appropriate for a JSON API backend, so that XSS attacks are mitigated and the API cannot be framed.

#### Acceptance Criteria

1. WHEN the `SecurityHeadersMiddleware` processes a response that does not already contain a `Content-Security-Policy` header, THE `SecurityHeadersMiddleware` SHALL set `Content-Security-Policy` to `default-src 'none'; frame-ancestors 'none'`.
2. WHEN the `SecurityHeadersMiddleware` processes a response that already contains a `Content-Security-Policy` header set by a route handler, THE `SecurityHeadersMiddleware` SHALL preserve the existing value without modification.

---

### Requirement 7: Conditional HSTS Header (Production Only)

**User Story:** As a security engineer, I want `Strict-Transport-Security` to be set only in production, so that local HTTP development is not broken by HSTS preloading while production traffic is still protected.

#### Acceptance Criteria

1. WHILE the `ENVIRONMENT` environment variable equals `production`, WHEN the `SecurityHeadersMiddleware` processes a response that does not already contain a `Strict-Transport-Security` header, THE `SecurityHeadersMiddleware` SHALL set `Strict-Transport-Security` to `max-age=31536000; includeSubDomains`.
2. WHILE the `ENVIRONMENT` environment variable is absent or set to any value other than `production`, THE `SecurityHeadersMiddleware` SHALL NOT set the `Strict-Transport-Security` header on any response.
3. WHEN the `SecurityHeadersMiddleware` processes a response in a Production Environment that already contains a `Strict-Transport-Security` header set by a route handler, THE `SecurityHeadersMiddleware` SHALL preserve the existing value without modification.

---

### Requirement 8: Preserve Route Handler Headers

**User Story:** As a backend engineer, I want the middleware to never overwrite headers already set by route handlers, so that individual endpoints retain the ability to customise security policy for their specific response type.

#### Acceptance Criteria

1. FOR ALL HTTP responses, THE `SecurityHeadersMiddleware` SHALL only inject a security header when that header is absent from the response at the time the middleware processes it.
2. FOR ALL HTTP responses, THE `SecurityHeadersMiddleware` SHALL preserve every header set by a route handler that is not a security header managed by this middleware.

---

### Requirement 9: Middleware Does Not Alter Response Body or Status

**User Story:** As a backend engineer, I want the security headers middleware to be transparent to response content, so that adding it cannot break existing API consumers.

#### Acceptance Criteria

1. THE `SecurityHeadersMiddleware` SHALL NOT modify the HTTP response status code of any response.
2. THE `SecurityHeadersMiddleware` SHALL NOT modify the HTTP response body of any response.

---

### Requirement 10: Property-Based Correctness of Header Injection

**User Story:** As a quality engineer, I want property-based tests to verify that security headers are present and correct across arbitrary backend responses, so that regressions are caught automatically.

#### Acceptance Criteria

1. FOR ALL HTTP responses returned by the backend, THE test suite SHALL verify that `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and `Content-Security-Policy` are present with their specified values.
2. WHEN the test environment sets `ENVIRONMENT=production`, THE test suite SHALL verify that `Strict-Transport-Security` is present with the value `max-age=31536000; includeSubDomains`.
3. WHEN the test environment does not set `ENVIRONMENT=production`, THE test suite SHALL verify that `Strict-Transport-Security` is absent from all responses.
4. WHEN a route handler sets a security header before the middleware runs, THE test suite SHALL verify that the middleware preserves the route-handler-supplied value and does not overwrite it.
