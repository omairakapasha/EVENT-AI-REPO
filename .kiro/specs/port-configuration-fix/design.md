# Port Configuration Fix Bugfix Design

## Overview

This bugfix addresses a critical OAuth redirect failure caused by a port mismatch between the backend's `FRONTEND_URL` configuration and the frontend vendor portal's actual runtime port. After Google OAuth login, users experience `ERR_CONNECTION_REFUSED` errors because the backend redirects to `localhost:3001/dashboard`, but the frontend vendor portal runs on `localhost:3000` by default.

The fix is minimal and targeted: update the `FRONTEND_URL` environment variable in `packages/backend/.env` from `http://localhost:3001` to `http://localhost:3000` to match the frontend vendor portal's default Next.js dev server port. This ensures OAuth callbacks redirect to the correct, reachable port.

Additionally, we verify that all other port configurations across the system are correct and consistent to prevent similar connectivity issues.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when the backend's `FRONTEND_URL` is set to port 3001 but the frontend vendor portal runs on port 3000
- **Property (P)**: The desired behavior - OAuth callbacks should redirect to the correct frontend port where the application is actually running
- **Preservation**: All other port configurations (user portal on 3003, admin portal on 3002, backend API on 5000, orchestrator on 8000) must remain unchanged
- **FRONTEND_URL**: Environment variable in `packages/backend/.env` that specifies the base URL for post-OAuth browser redirects
- **OAuth Callback Flow**: The sequence where Google redirects to the backend callback endpoint, which then redirects to the frontend with JWT tokens in query parameters
- **Vendor Portal**: The frontend application in `packages/vendor/` that runs on port 3000 by default with `next dev`

## Bug Details

### Bug Condition

The bug manifests when a user completes Google OAuth login and the backend attempts to redirect them to the frontend dashboard. The `google_oauth_callback` handler in `packages/backend/src/api/v1/auth.py` constructs a redirect URL using `settings.frontend_url` from the configuration, but this URL points to port 3001 while the frontend vendor portal actually runs on port 3000.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type OAuthCallbackRequest
  OUTPUT: boolean
  
  RETURN input.isSuccessfulOAuthCallback == true
         AND settings.frontend_url == "http://localhost:3001"
         AND actualFrontendPort == 3000
         AND redirect_url contains "localhost:3001"
END FUNCTION
```

### Examples

- **Example 1**: User clicks "Login with Google" on vendor portal (port 3000) → Google redirects to backend callback → Backend redirects to `http://localhost:3001/dashboard?token=...` → Browser shows `ERR_CONNECTION_REFUSED` because nothing is listening on port 3001
- **Example 2**: User completes OAuth flow → Backend successfully issues JWT tokens → Redirect URL is `http://localhost:3001/dashboard?token=abc&refresh_token=xyz` → User cannot access the dashboard because port 3001 is unreachable
- **Example 3**: Frontend vendor portal starts with `next dev` (default port 3000) → Backend `.env` has `FRONTEND_URL=http://localhost:3001` → Port mismatch causes all OAuth redirects to fail
- **Edge Case**: If user manually starts frontend on port 3001 with `next dev -p 3001`, OAuth would work, but this is not the default configuration and not documented

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- User portal must continue to run on port 3003 (configured with `next dev -p 3003`)
- Admin portal must continue to run on port 3002 (configured with `next dev -p 3002`)
- Backend API server must continue to run on port 5000
- Agentic event orchestrator must continue to run on port 8000
- Google OAuth callback URI must remain `http://localhost:5000/api/v1/auth/google/callback`
- CORS origins must continue to include all necessary frontend ports (3000, 3001, 3002, 3003)
- User portal and admin portal OAuth flows must continue to work with their respective configured ports

**Scope:**
All OAuth flows and API calls that do NOT involve the vendor portal on port 3000 should be completely unaffected by this fix. This includes:
- User portal OAuth flow (port 3003)
- Admin portal OAuth flow (port 3002)
- Direct API calls to backend (port 5000)
- AI orchestrator API calls (port 8000)
- Non-OAuth authentication flows (email/password login)

## Hypothesized Root Cause

Based on the bug description and code analysis, the root cause is:

1. **Incorrect Environment Variable Value**: The `FRONTEND_URL` in `packages/backend/.env` is set to `http://localhost:3001`, but this does not match the frontend vendor portal's default port
   - The frontend vendor portal uses Next.js default port 3000 when started with `next dev`
   - The backend configuration was likely copied from another portal (user/admin) or set incorrectly during initial setup

2. **Configuration Mismatch**: The backend's `Settings` class in `packages/backend/src/config/database.py` has a default value of `http://localhost:3003` for `frontend_url`, but the `.env` file overrides this with `http://localhost:3001`
   - The default in code (3003) is for the user portal
   - The `.env` override (3001) doesn't match any running service

3. **No Port Validation**: There is no runtime validation to ensure the configured `FRONTEND_URL` port matches an actually running frontend service

4. **Documentation Gap**: The relationship between `FRONTEND_URL` and the vendor portal's default port is not clearly documented

## Correctness Properties

Property 1: Bug Condition - OAuth Redirect to Correct Port

_For any_ OAuth callback where the user successfully authenticates with Google and the vendor portal is running on port 3000, the backend SHALL redirect to `http://localhost:3000/dashboard` (or the appropriate path) with valid JWT tokens in the query parameters, ensuring the user can access the application.

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation - Other Port Configurations Unchanged

_For any_ service or portal that is NOT the vendor portal (user portal on 3003, admin portal on 3002, backend API on 5000, orchestrator on 8000), the fixed configuration SHALL produce exactly the same behavior as the original configuration, preserving all existing port assignments and OAuth flows for those services.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `packages/backend/.env`

**Environment Variable**: `FRONTEND_URL`

**Specific Changes**:
1. **Update FRONTEND_URL Value**: Change from `http://localhost:3001` to `http://localhost:3000`
   - Line: `FRONTEND_URL=http://localhost:3001`
   - New value: `FRONTEND_URL=http://localhost:3000`
   - Rationale: Match the frontend vendor portal's default Next.js dev server port

2. **Verify Other Port Configurations**: Ensure all other port-related environment variables are correct
   - `PORT=3001` (backend API port) - should remain 5000 (verify this is correct)
   - `CORS_ORIGINS` includes `http://localhost:3000` - verify this is present
   - `GOOGLE_REDIRECT_URI=http://localhost:5000/api/v1/auth/google/callback` - verify this is correct

3. **Verify Frontend Port Configuration**: Ensure the frontend vendor portal's package.json dev script uses default port
   - Check `packages/vendor/package.json` for `"dev": "next dev"` (no explicit port means 3000)
   - If explicit port is set, ensure it matches the new `FRONTEND_URL`

4. **Verify User and Admin Portal Configurations**: Ensure their OAuth flows use correct ports
   - User portal should have its own OAuth configuration for port 3003
   - Admin portal should have its own OAuth configuration for port 3002
   - These should not be affected by the vendor portal fix

5. **Documentation Update**: Add a comment in `.env` file explaining the port relationship
   - Add comment above `FRONTEND_URL` explaining it should match the vendor portal's runtime port

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Manually test the OAuth flow with the UNFIXED configuration to observe the connection failure. Document the exact error message and redirect URL. Then inspect the `.env` file to confirm the port mismatch.

**Test Cases**:
1. **OAuth Redirect Failure Test**: Start vendor portal on port 3000, complete Google OAuth login, observe redirect to port 3001 and `ERR_CONNECTION_REFUSED` (will fail on unfixed code)
2. **Environment Variable Inspection**: Read `packages/backend/.env` and verify `FRONTEND_URL=http://localhost:3001` (will show mismatch on unfixed code)
3. **Frontend Port Verification**: Start vendor portal with `next dev` and verify it runs on port 3000 (will confirm port mismatch on unfixed code)
4. **Backend Redirect URL Construction**: Add logging to `auth.py` callback handler to print the constructed redirect URL and verify it contains port 3001 (will show incorrect URL on unfixed code)

**Expected Counterexamples**:
- OAuth callback redirects to `http://localhost:3001/dashboard?token=...&refresh_token=...`
- Browser displays `ERR_CONNECTION_REFUSED` when trying to access port 3001
- Possible causes: incorrect `.env` value, port mismatch between backend config and frontend runtime

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL oauthCallback WHERE isBugCondition(oauthCallback) DO
  result := handleOAuthCallback_fixed(oauthCallback)
  ASSERT result.redirect_url contains "localhost:3000"
  ASSERT result.redirect_url does NOT contain "localhost:3001"
  ASSERT browserCanReach(result.redirect_url) == true
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL request WHERE NOT isBugCondition(request) DO
  ASSERT handleRequest_original(request) = handleRequest_fixed(request)
END FOR
```

**Testing Approach**: Manual testing is sufficient for this configuration fix because:
- The change is a single environment variable value
- The input domain is small (OAuth callbacks for different portals)
- We can manually verify each portal's OAuth flow works correctly
- Property-based testing would be overkill for a simple configuration change

**Test Plan**: Observe behavior on UNFIXED code first for user portal (3003) and admin portal (3002) OAuth flows, then verify these continue to work after fixing the vendor portal configuration.

**Test Cases**:
1. **User Portal OAuth Preservation**: Verify user portal OAuth flow on port 3003 works correctly before and after fix
2. **Admin Portal OAuth Preservation**: Verify admin portal OAuth flow on port 3002 works correctly before and after fix
3. **Backend API Port Preservation**: Verify backend API continues to run on port 5000 and accept requests
4. **CORS Configuration Preservation**: Verify CORS origins still include all necessary ports (3000, 3001, 3002, 3003)

### Unit Tests

- Test that OAuth callback constructs redirect URL using `settings.frontend_url`
- Test that `Settings` class correctly loads `FRONTEND_URL` from environment
- Test that redirect URL includes correct query parameters (token, refresh_token)
- Test error cases (OAuth denial, missing code/state) redirect to correct login page

### Property-Based Tests

Not applicable for this fix. The change is a simple configuration value update, not a complex algorithmic change that would benefit from property-based testing.

### Integration Tests

- **Full OAuth Flow Test**: Start vendor portal on port 3000, initiate Google OAuth, complete authentication, verify redirect to `http://localhost:3000/dashboard` with valid tokens
- **Multi-Portal Test**: Start all three portals (vendor on 3000, admin on 3002, user on 3003), test OAuth flow for each, verify each redirects to its correct port
- **API Connectivity Test**: Verify all frontend portals can successfully make API calls to backend on port 5000
- **Cross-Origin Request Test**: Verify CORS allows requests from all configured frontend ports
