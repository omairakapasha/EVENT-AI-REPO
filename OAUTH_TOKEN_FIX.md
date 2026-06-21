# OAuth Token Authentication Fix

## Problem
The Google OAuth flow was generating tokens successfully but the frontend wasn't attaching them to subsequent API requests, causing 401 errors after login.

## Root Cause
**Token storage vs. API client mismatch:**
- OAuth callback stored tokens in `localStorage` (for cross-origin Vercel deployment)
- API client (`api.ts`) only used httpOnly cookies and didn't read from `localStorage`
- Result: Tokens were stored but never sent with requests

## Changes Made

### 1. Frontend API Client (`packages/user/src/lib/api.ts`)

#### Added Request Interceptor
```typescript
// Request interceptor — attach access token from localStorage if available
api.interceptors.request.use(
    (config) => {
        if (typeof window !== 'undefined') {
            const accessToken = localStorage.getItem('access_token');
            if (accessToken) {
                config.headers.Authorization = `Bearer ${accessToken}`;
            }
        }
        return config;
    },
    (error) => Promise.reject(error)
);
```

#### Updated Response Interceptor for Token Refresh
- Now reads `refresh_token` from localStorage
- Updates both tokens in localStorage after successful refresh
- Clears localStorage on refresh failure
- Falls back to cookie-based refresh if no localStorage token

#### Added Logout Helper
```typescript
export const logout = async () => {
    try {
        await api.post("/auth/logout");
    } catch (error) {
        console.error("Logout error:", error);
    } finally {
        // Always clear localStorage tokens
        if (typeof window !== 'undefined') {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
        }
    }
};
```

### 2. Navbar Component (`packages/user/src/components/navbar.tsx`)

- Replaced raw `fetch` calls with API client functions
- Now uses `getUserProfile()` instead of direct fetch
- Uses new `logout()` helper that clears localStorage
- Automatically benefits from request interceptor (tokens attached)

### 3. Notification Provider (`packages/user/src/components/notification-provider.tsx`)

- Updated SSE connection to pass token as query parameter
- Added token presence check before connecting
- `EventSource` doesn't support custom headers, so token passed in URL

```typescript
const token = localStorage.getItem('access_token');
if (!token) {
    console.warn('[SSE] No access token found, skipping SSE connection');
    return;
}
eventSource = new EventSource(`${API_URL}/sse/stream?token=${token}`);
```

### 4. Backend SSE Endpoint (`packages/backend/src/api/v1/sse.py`)

- Added support for token query parameter
- Now accepts token from either:
  1. Query param: `?token=<jwt>` (for cross-origin EventSource)
  2. Cookie: `access_token` (fallback for same-origin)

```python
@router.get("/stream")
async def sse_stream(
    request: Request,
    token: str | None = None,  # Query param for EventSource
    cm: SSEConnectionManager = Depends(get_connection_manager),
):
    auth_token = token or request.cookies.get("access_token")
    # ...
```

## How It Works Now

### OAuth Flow
1. User clicks "Continue with Google"
2. Backend handles OAuth, generates tokens
3. Redirects to `/auth/callback?access_token=...&refresh_token=...`
4. Callback stores tokens in localStorage
5. Redirects to dashboard

### API Requests
1. Request interceptor reads `access_token` from localStorage
2. Adds `Authorization: Bearer <token>` header automatically
3. All API calls now authenticated

### Token Refresh
1. 401 response triggers refresh interceptor
2. Reads `refresh_token` from localStorage
3. Calls `/auth/refresh` with refresh token
4. Updates both tokens in localStorage
5. Retries original request with new token

### SSE Connection
1. Notification provider reads token from localStorage
2. Passes as query parameter: `/sse/stream?token=<jwt>`
3. Backend validates token from query param
4. Real-time updates work properly

## Testing Checklist

- [ ] Google OAuth login completes successfully
- [ ] User redirected to dashboard after login
- [ ] `/users/me` returns user data (no 401)
- [ ] SSE connection establishes without 401
- [ ] API requests include Authorization header
- [ ] Token refresh works on 401
- [ ] Logout clears localStorage tokens
- [ ] Page refresh maintains session

## Deployment Notes

### Environment Variables Required
```env
# Frontend (.env)
NEXT_PUBLIC_API_URL=https://eventai-backend-upym.onrender.com/api/v1

# Backend (.env)
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>
GOOGLE_REDIRECT_URI=https://eventai-backend-upym.onrender.com/api/v1/auth/google/callback
CORS_ORIGINS=https://event-user.vercel.app,https://event-vendor-two.vercel.app,https://event-admin-umber.vercel.app
FRONTEND_URL=https://event-user.vercel.app
```

### Google Cloud Console Setup
**Authorized JavaScript origins:**
- `https://event-user.vercel.app`
- `https://event-vendor-two.vercel.app`
- `https://event-admin-umber.vercel.app`

**Authorized redirect URIs:**
- `https://eventai-backend-upym.onrender.com/api/v1/auth/google/callback`

## Why This Approach?

### localStorage vs Cookies
- **Cookies (httpOnly):** More secure, immune to XSS, but CORS-complex
- **localStorage + Authorization header:** Required for cross-origin deployments (Vercel → Render)
- **Hybrid approach:** Support both methods for flexibility

### SSE Token in Query Param
- EventSource API doesn't support custom headers
- Can't use Authorization header with native EventSource
- Query param is the standard workaround
- Token validated server-side same as header token

## Security Considerations

✅ **Maintained:**
- Backend validates JWT on every request
- Tokens expire (access: 30min, refresh: 7 days)
- Rate limiting still active
- CORS properly configured

⚠️ **Trade-offs:**
- localStorage tokens visible in browser DevTools
- SSE token visible in browser network tab
- Acceptable for deployment, necessary for cross-origin

🔒 **Mitigations:**
- Short token expiration times
- HTTPS required in production
- Refresh token rotation on use
- Token stored only if needed (OAuth flow)

## Files Changed
1. `packages/user/src/lib/api.ts` - Request/response interceptors
2. `packages/user/src/components/navbar.tsx` - Use API helpers
3. `packages/user/src/components/notification-provider.tsx` - SSE with token
4. `packages/backend/src/api/v1/sse.py` - Accept query param token
5. `OAUTH_TOKEN_FIX.md` - This documentation

## Next Steps
1. Deploy backend changes to Render
2. Deploy frontend changes to Vercel
3. Test complete OAuth flow
4. Verify SSE connection works
5. Monitor for 401 errors in production
