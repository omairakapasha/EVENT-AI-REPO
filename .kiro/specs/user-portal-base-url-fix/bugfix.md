# Bugfix Requirements Document

## Introduction

The user portal (`packages/user`) hardcodes `localhost:3001` as the fallback base URL for all API calls when `NEXT_PUBLIC_API_URL` is not set. Port `3001` is the Docker vendor portal port — not the backend API. The backend API runs on port `5000`. Any user portal deployment without an explicit `NEXT_PUBLIC_API_URL` environment variable will silently route all API traffic to the wrong service, causing every API call to fail (connection refused or wrong service response). The same wrong default appears in five source files across the package.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN `NEXT_PUBLIC_API_URL` is not set AND the axios instance in `packages/user/src/lib/api.ts` is initialised THEN the system uses `http://localhost:3001/api/v1` as the base URL, routing all API calls to the Docker vendor portal port instead of the backend API

1.2 WHEN `NEXT_PUBLIC_API_URL` is not set AND the signup page (`packages/user/src/app/signup/page.tsx`) makes an API call THEN the system uses `http://localhost:3001/api/v1` as the base URL, causing the request to target the wrong port

1.3 WHEN `NEXT_PUBLIC_API_URL` is not set AND the OAuth callback page (`packages/user/src/app/auth/callback/page.tsx`) verifies auth via `/users/me` THEN the system uses `http://localhost:3001/api/v1` as the base URL, causing the auth verification to fail

1.4 WHEN `NEXT_PUBLIC_API_URL` is not set AND the notification provider (`packages/user/src/components/notification-provider.tsx`) opens an SSE connection THEN the system uses `http://localhost:3001/api/v1` as the base URL, causing the SSE stream to connect to the wrong port

1.5 WHEN `NEXT_PUBLIC_API_URL` is not set AND the navbar (`packages/user/src/components/navbar.tsx`) fetches user data or performs logout THEN the system uses `http://localhost:3001/api/v1` as the base URL, causing those requests to target the wrong port

### Expected Behavior (Correct)

2.1 WHEN `NEXT_PUBLIC_API_URL` is not set AND the axios instance in `packages/user/src/lib/api.ts` is initialised THEN the system SHALL use `http://localhost:5000/api/v1` as the base URL, matching the backend API port defined in the project port map

2.2 WHEN `NEXT_PUBLIC_API_URL` is not set AND the signup page makes an API call THEN the system SHALL use `http://localhost:5000/api/v1` as the base URL

2.3 WHEN `NEXT_PUBLIC_API_URL` is not set AND the OAuth callback page verifies auth via `/users/me` THEN the system SHALL use `http://localhost:5000/api/v1` as the base URL

2.4 WHEN `NEXT_PUBLIC_API_URL` is not set AND the notification provider opens an SSE connection THEN the system SHALL use `http://localhost:5000/api/v1` as the base URL

2.5 WHEN `NEXT_PUBLIC_API_URL` is not set AND the navbar fetches user data or performs logout THEN the system SHALL use `http://localhost:5000/api/v1` as the base URL

### Unchanged Behavior (Regression Prevention)

3.1 WHEN `NEXT_PUBLIC_API_URL` is explicitly set to any value THEN the system SHALL CONTINUE TO use that value as the base URL, ignoring the fallback entirely

3.2 WHEN `NEXT_PUBLIC_API_URL` is set to a production URL THEN the system SHALL CONTINUE TO route all API calls to that production URL without modification

3.3 WHEN the axios instance makes any API call with a valid base URL THEN the system SHALL CONTINUE TO attach the correct `Content-Type` header and send credentials via `withCredentials: true`

3.4 WHEN a 401 response is received and the token refresh flow is triggered THEN the system SHALL CONTINUE TO retry the original request after a successful refresh and redirect to `/login` on refresh failure

3.5 WHEN `NEXT_PUBLIC_SOCKET_URL` is not set AND the socket provider initialises THEN the system SHALL CONTINUE TO use its existing fallback (this is a separate env var and is out of scope for this fix)

---

## Bug Condition (Pseudocode)

```pascal
FUNCTION isBugCondition(env)
  INPUT: env — the process environment at runtime
  OUTPUT: boolean

  RETURN env.NEXT_PUBLIC_API_URL = undefined OR env.NEXT_PUBLIC_API_URL = null OR env.NEXT_PUBLIC_API_URL = ""
END FUNCTION
```

```pascal
// Property: Fix Checking — all fallback URLs must resolve to port 5000
FOR ALL env WHERE isBugCondition(env) DO
  baseURL ← resolveBaseURL'(env)
  ASSERT baseURL = "http://localhost:5000/api/v1"
END FOR
```

```pascal
// Property: Preservation Checking — explicit env var is always honoured
FOR ALL env WHERE NOT isBugCondition(env) DO
  ASSERT resolveBaseURL'(env) = resolveBaseURL(env)
END FOR
```
