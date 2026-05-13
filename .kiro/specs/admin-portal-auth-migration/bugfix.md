# Bugfix Requirements Document

## Introduction

The admin portal (`packages/admin`) uses `next-auth` for authentication, which is explicitly banned by the project constitution. The current implementation imports `getSession` and `signOut` from `next-auth/react`, attaches a JWT via an `Authorization: Bearer` header, and points to the wrong backend base URL (`http://localhost:3001/api/v1` instead of `http://localhost:5000/api/v1`). Additionally, the admin portal has no `middleware.ts`, meaning unauthenticated users and non-admin authenticated users can access protected routes without being redirected.

The fix must bring the admin portal into compliance with the project's mandated httpOnly cookie-based auth pattern (as already implemented in `packages/vendor`) and add an admin-role guard to the Next.js middleware.

---

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the admin portal makes any API request THEN the system imports `getSession` from `next-auth/react` and attaches the session's `accessToken` as an `Authorization: Bearer` header, violating the banned-practices rule.

1.2 WHEN the admin portal makes any API request THEN the system uses `http://localhost:3001/api/v1` as the base URL, which points to the wrong port and causes all API calls to fail against the running backend.

1.3 WHEN a 401 response is received THEN the system calls `signOut` from `next-auth/react` instead of attempting a cookie-based token refresh, causing an immediate logout without a refresh attempt.

1.4 WHEN an unauthenticated user navigates to any protected admin route THEN the system renders the page without redirecting to `/login`, because no `middleware.ts` exists in the admin portal.

1.5 WHEN an authenticated user with a non-admin role (e.g. `role === 'vendor'` or `role === 'user'`) navigates to any admin route THEN the system allows access without checking the role, because no role guard exists in the admin portal middleware.

### Expected Behavior (Correct)

2.1 WHEN the admin portal makes any API request THEN the system SHALL use `withCredentials: true` on the axios instance so that httpOnly cookies are sent automatically, with no manual `Authorization` header injection.

2.2 WHEN the admin portal initialises the axios instance THEN the system SHALL use `process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api/v1'` as the base URL, matching the correct backend port.

2.3 WHEN a 401 response is received on a non-auth route THEN the system SHALL attempt a token refresh via `POST /api/v1/auth/refresh` (cookie sent automatically via `withCredentials`), retry the original request on success, and redirect to `/login` only after a failed refresh — mirroring the vendor portal pattern.

2.4 WHEN an unauthenticated user (no `access_token` or `refresh_token` cookie) navigates to any protected admin route THEN the system SHALL redirect to `/login` via `middleware.ts` before the page renders.

2.5 WHEN an authenticated user whose decoded JWT `role` is not `'admin'` navigates to any admin route THEN the system SHALL redirect to `/403` via `middleware.ts`, preventing unauthorised access to admin functionality.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN an authenticated admin user navigates to any protected admin route THEN the system SHALL CONTINUE TO render the requested page without interruption.

3.2 WHEN the admin portal makes a successful API request THEN the system SHALL CONTINUE TO return the response data in the same shape consumed by existing page components (no changes to `getVendors`, `getUsers`, `getStats`, etc. return types).

3.3 WHEN a user navigates to `/login` or other explicitly public routes THEN the system SHALL CONTINUE TO serve those pages without redirecting, regardless of cookie state.

3.4 WHEN the backend issues a new token pair on refresh THEN the system SHALL CONTINUE TO set updated httpOnly cookies automatically via the backend `Set-Cookie` response headers, with no frontend token storage required.

3.5 WHEN Next.js static assets (`/_next/static`, `/_next/image`, `favicon.ico`, image files) are requested THEN the system SHALL CONTINUE TO serve them without triggering the auth middleware.

---

## Bug Condition Pseudocode

### Bug Condition Function

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type AdminPortalRequest
  OUTPUT: boolean

  // Bug is triggered when the admin portal uses NextAuth-based auth
  RETURN (
    X.usesNextAuth = true          // imports getSession/signOut from next-auth/react
    OR X.baseURL = "http://localhost:3001/api/v1"  // wrong backend port
    OR X.hasMiddleware = false     // no middleware.ts present
  )
END FUNCTION
```

### Property: Fix Checking

```pascal
// Property: Fix Checking — NextAuth removed, cookie auth in place
FOR ALL X WHERE isBugCondition(X) DO
  result ← adminApi'(X)
  ASSERT result.usesNextAuth = false
  ASSERT result.withCredentials = true
  ASSERT result.baseURL = "http://localhost:5000/api/v1"
  ASSERT result.hasAuthorizationHeader = false
  ASSERT result.hasMiddleware = true
  ASSERT result.middlewareChecksAdminRole = true
END FOR
```

### Property: Preservation Checking

```pascal
// Property: Preservation Checking — existing API call shapes unchanged
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT adminApi(X).responseShape = adminApi'(X).responseShape
END FOR
```
