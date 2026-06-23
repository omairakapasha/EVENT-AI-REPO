# OAuth Debug Guide

## What I've Done

I've added extensive logging throughout the authentication flow to help identify where the redirect loop is occurring.

### Changes Made

1. **Removed middleware.ts** - No longer needed since auth is 100% client-side via localStorage tokens
2. **auth/callback/page.tsx** - Added detailed logs for token storage and redirect
3. **dashboard/page.tsx** - Added logs to confirm when dashboard mounts
4. **api.ts** - Added comprehensive logging for:
   - Every API request (with or without token)
   - 401 errors and refresh attempts
   - Token refresh success/failure
   - Redirect to login

## Testing Instructions

After Vercel deployment completes:

### 1. Test OAuth Flow

1. Open https://event-user.vercel.app/login
2. Open browser DevTools Console (F12)
3. Click "Continue with Google"
4. Complete Google OAuth

### 2. Check Console Logs

You should see logs in this order:

```
[OAuth Callback] error: null
[OAuth Callback] accessToken: present
[OAuth Callback] refreshToken: present
[OAuth Callback] Storing tokens in localStorage
[OAuth Callback] Current URL: https://event-user.vercel.app/auth/callback?access_token=...
[OAuth Callback] Tokens stored successfully: {access: true, refresh: true, accessPreview: "eyJhbGciOiJIUzI1NiIs..."}
[OAuth Callback] Cleared tokens from URL
[OAuth Callback] Redirecting to dashboard in 500ms
[OAuth Callback] Executing redirect now

[Dashboard] Page mounted - INITIAL
[Dashboard] Current URL: https://event-user.vercel.app/dashboard
[Dashboard] Pathname: /dashboard
[Dashboard] Tokens in localStorage: {access: true, refresh: true, accessPreview: "eyJhbGciOiJIUzI1NiIs..."}

[API Request] GET /users/me - Token attached
```

### 3. Possible Outcomes

#### A) Dashboard loads successfully ✅
- Console shows dashboard logs
- No 401 errors
- User stays on dashboard
- **Issue is FIXED!**

#### B) Dashboard redirects to login ❌
Console will show one of these patterns:

**Pattern 1: Token invalid/expired**
```
[API Request] GET /users/me - Token attached
[API 401] GET /users/me - Attempting refresh
[API Refresh] Using localStorage token
[API Refresh] Failed: AxiosError: Request failed with status code 401
[API] Refresh failed, clearing tokens and redirecting to login
[API] Executing redirect to /login
```
→ **Problem**: Tokens from backend are invalid/expired immediately after creation

**Pattern 2: No token in localStorage**
```
[Dashboard] Tokens in localStorage: {access: false, refresh: false}
[API Request] GET /users/me - No token found
[API 401] GET /users/me - Attempting refresh
[API Refresh] Using httpOnly cookie
[API Refresh] Failed
[API] Executing redirect to /login
```
→ **Problem**: Tokens not being stored in localStorage (storage blocked?)

**Pattern 3: Dashboard never mounts**
```
[OAuth Callback] Executing redirect now
```
No dashboard logs at all.
→ **Problem**: Client-side redirect happening before dashboard loads

## What to Send Me

After testing, please send me:

1. **Full console output** (copy everything from Console tab)
2. **Network tab screenshot** showing:
   - The /dashboard request
   - The /users/me request
   - Any redirects (look for 3xx status codes)
3. **Application tab screenshot** showing:
   - localStorage contents (should have access_token and refresh_token)

## Vercel Deployment Check

To ensure Vercel deployed successfully:

1. Check deployment logs at https://vercel.com/dashboard
2. Look for "Building..." → "Completed" (no build errors)
3. Click on the deployment and check "Source"
4. Verify commit hash matches: `594c582`

If deployment is still running, wait for it to complete before testing.

## Expected Fix

Based on previous debugging, the most likely issue is that **tokens are valid but the refresh endpoint is failing**. The new logs will tell us exactly why the refresh is failing (wrong token format, expired token, backend issue, etc.).

Once we see the exact error, we can fix it quickly.
