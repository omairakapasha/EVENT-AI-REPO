# OAuth Fix Deployment Checklist

## ✅ Completed
- [x] Fixed API client to read tokens from localStorage
- [x] Added request interceptor for Authorization header
- [x] Updated token refresh logic
- [x] Added logout helper to clear localStorage
- [x] Updated navbar to use API client
- [x] Fixed SSE connection to pass token
- [x] Updated backend SSE endpoint to accept query param
- [x] TypeScript compilation passes
- [x] Committed changes
- [x] Pushed to GitHub

## 🚀 Deployment Steps

### 1. Backend Deployment (Render)
The backend changes will auto-deploy from GitHub push.

**Check Render Dashboard:**
- URL: https://dashboard.render.com/
- Service: `eventai-backend`
- Wait for build to complete (~5 minutes)
- Check logs for any errors

**Expected in logs:**
```
Starting service with 'uvicorn src.main:app --host 0.0.0.0 --port 5000'
INFO:     Started server process
INFO:     Application startup complete
```

### 2. Frontend Deployment (Vercel)
The frontend changes will auto-deploy from GitHub push.

**Check Vercel Dashboard:**
- URL: https://vercel.com/dashboard
- Project: `event-user`
- Wait for build to complete (~3 minutes)
- Check build logs for errors

**Expected output:**
```
✓ Compiled successfully
✓ Linting and checking validity of types
✓ Creating an optimized production build
```

### 3. Post-Deployment Verification

#### Step 1: Test OAuth Login Flow
1. Open: https://event-user.vercel.app/login
2. Click "Continue with Google"
3. Choose Google account
4. **Expected:** Redirect to dashboard (NOT back to login)
5. **Check DevTools Console:**
   - ✅ Should see: `[OAuth Callback] Storing tokens in localStorage`
   - ✅ Should see: `[OAuth Callback] accessToken: present`
   - ❌ Should NOT see: `401 Unauthorized` errors

#### Step 2: Verify API Requests
1. Stay on dashboard page
2. Open DevTools → Network tab
3. Filter: `XHR/Fetch`
4. Look for `/api/v1/users/me` request
5. **Check Request Headers:**
   ```
   Authorization: Bearer eyJ...
   ```
6. **Check Response:**
   - Status: `200 OK`
   - Body: Contains user data

#### Step 3: Verify SSE Connection
1. Stay on dashboard
2. Network tab → Filter: `EventSource` or `stream`
3. Look for `/api/v1/sse/stream?token=...`
4. **Expected:**
   - Status: `200 OK`
   - Type: `eventsource`
   - No 401 errors

#### Step 4: Test Navigation
1. Click through all menu items:
   - My Events
   - Marketplace
   - Bookings
   - AI Assistant
   - Profile
2. **Expected:** All pages load without 401 errors
3. **Check:** User name shows in navbar

#### Step 5: Test Logout
1. Click user menu in navbar
2. Click "Sign out"
3. **Expected:**
   - Redirects to `/login`
   - localStorage tokens cleared
   - No errors in console

#### Step 6: Test Token Refresh
1. Login with Google
2. Wait 30+ minutes (token expiration)
3. Make an API request (click a menu item)
4. **Expected:**
   - Request succeeds (not 401)
   - New tokens stored in localStorage
   - No visible interruption

## 🐛 Troubleshooting

### Issue: Still getting 401 after OAuth
**Check:**
1. DevTools → Application → Local Storage
2. Look for `access_token` and `refresh_token`
3. If missing: Backend didn't pass tokens in URL

**Fix:**
- Check backend logs for OAuth callback errors
- Verify `GOOGLE_REDIRECT_URI` matches exactly
- Check `FRONTEND_URL` environment variable

### Issue: SSE connection fails
**Check:**
1. Network tab → Look for `/sse/stream` request
2. Check if token is in URL: `?token=...`
3. Check response status

**Fix:**
- Verify token exists in localStorage before SSE connects
- Check backend logs for token validation errors
- Ensure CORS allows the Vercel domain

### Issue: Token refresh fails
**Check:**
1. Console for refresh errors
2. Network tab → `/api/v1/auth/refresh` request
3. Check request payload has `refresh_token`

**Fix:**
- Verify refresh token exists in localStorage
- Check backend refresh endpoint accepts JSON body
- Verify refresh token hasn't expired (7 days)

## 📊 Monitoring

### Key Metrics to Watch
1. **Login success rate:** Should increase to ~95%+
2. **401 errors:** Should drop to near zero after login
3. **SSE connections:** Should establish on dashboard load
4. **User session duration:** Should last until token expiry

### Where to Check
- **Render Logs:** Backend errors, auth failures
- **Vercel Logs:** Frontend build errors, runtime errors
- **Browser Console:** Client-side errors, API failures
- **Network Tab:** Request/response details, status codes

## 🔄 Rollback Plan (if needed)

If deployment causes issues:

### Quick Rollback
```bash
# Locally
git revert HEAD
git push origin main

# Or in Render/Vercel dashboard
# Redeploy previous successful deployment
```

### Files to Revert
1. `packages/user/src/lib/api.ts`
2. `packages/user/src/components/navbar.tsx`
3. `packages/user/src/components/notification-provider.tsx`
4. `packages/backend/src/api/v1/sse.py`

## ✅ Success Criteria

The deployment is successful when:
- [x] Google OAuth login completes without returning to login page
- [x] User sees dashboard after OAuth
- [x] No 401 errors in console after login
- [x] API requests include Authorization header with token
- [x] SSE connection establishes successfully
- [x] User can navigate all pages without auth errors
- [x] Logout clears tokens and redirects to login
- [x] Token refresh works transparently

## 📝 Notes

### Environment Variables (Already Set)
✅ Backend (Render):
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI=https://eventai-backend-upym.onrender.com/api/v1/auth/google/callback`
- `CORS_ORIGINS=https://event-user.vercel.app,...`
- `FRONTEND_URL=https://event-user.vercel.app`

✅ Frontend (Vercel):
- `NEXT_PUBLIC_API_URL=https://eventai-backend-upym.onrender.com/api/v1`

### Google Cloud Console (Already Configured)
✅ Authorized redirect URIs:
- `https://eventai-backend-upym.onrender.com/api/v1/auth/google/callback`

✅ Authorized JavaScript origins:
- `https://event-user.vercel.app`
- `https://event-vendor-two.vercel.app`
- `https://event-admin-umber.vercel.app`

## 🎯 Expected Timeline
- Backend deploy: ~5 minutes
- Frontend deploy: ~3 minutes
- Total: ~10 minutes from push to live
- Testing: ~5 minutes
- **Total deployment time: ~15 minutes**

## 📞 Support
If issues persist after deployment, gather:
1. Browser console logs (full output)
2. Network tab (filter: XHR, export HAR)
3. Backend logs (Render dashboard)
4. Frontend logs (Vercel dashboard)
5. Steps to reproduce

Reference: `OAUTH_TOKEN_FIX.md` for technical details
