# Testing OAuth Fix Locally (Before Deployment)

## Prerequisites
- Backend running: `pnpm dev:backend` (port 5000)
- Frontend running: `pnpm dev:user` (port 3003)
- PostgreSQL running: `pnpm db:up`

## Local Test Steps

### 1. Start Services
```bash
# Terminal 1: Start database
pnpm db:up

# Terminal 2: Start backend
pnpm dev:backend

# Terminal 3: Start frontend
pnpm dev:user
```

### 2. Test OAuth Login
1. Open: http://localhost:3003/login
2. Click "Continue with Google"
3. Choose Google account
4. **Expected:** Redirect to http://localhost:3003/dashboard

### 3. Verify in DevTools Console
```
[OAuth Callback] error: null
[OAuth Callback] accessToken: present
[OAuth Callback] refreshToken: present
[OAuth Callback] Storing tokens in localStorage
```

### 4. Verify localStorage
1. DevTools → Application tab → Local Storage → http://localhost:3003
2. Should see:
   - `access_token`: `eyJ...` (long JWT string)
   - `refresh_token`: `eyJ...` (long JWT string)

### 5. Verify API Request Headers
1. DevTools → Network tab
2. Look for request to `/api/v1/users/me`
3. Click on it → Headers tab
4. **Check Request Headers:**
   ```
   Authorization: Bearer eyJ...
   ```

### 6. Verify SSE Connection
1. Network tab → Filter: `stream`
2. Look for `/api/v1/sse/stream?token=...`
3. Status should be `200` (pending/streaming)
4. Type should be `eventsource`

### 7. Test Navigation (should all work without 401)
- http://localhost:3003/dashboard ✅
- http://localhost:3003/marketplace ✅
- http://localhost:3003/bookings ✅
- http://localhost:3003/chat ✅
- http://localhost:3003/profile ✅

### 8. Test Logout
1. Click user menu in navbar
2. Click "Sign out"
3. **Verify:**
   - Redirects to `/login`
   - localStorage cleared (check Application tab)
   - Can log in again

## Expected vs Previous Behavior

### ❌ BEFORE (Broken)
```
1. Click "Continue with Google" ✅
2. OAuth succeeds, tokens generated ✅
3. Redirect to callback ✅
4. Store in localStorage ✅
5. Redirect to dashboard ❌ (redirects back to login)
6. Console shows: 401 Unauthorized errors ❌
7. SSE fails with 401 ❌
```

### ✅ AFTER (Fixed)
```
1. Click "Continue with Google" ✅
2. OAuth succeeds, tokens generated ✅
3. Redirect to callback ✅
4. Store in localStorage ✅
5. Redirect to dashboard ✅ (stays on dashboard)
6. Console shows: No 401 errors ✅
7. SSE connects successfully ✅
8. API requests include Authorization header ✅
```

## Debug Commands

### Check if tokens are being sent:
```bash
# In frontend, modify api.ts temporarily:
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token');
    console.log('📤 Sending request with token:', token ? 'PRESENT' : 'MISSING');
    console.log('📤 To URL:', config.url);
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});
```

### Check backend token validation:
Look at backend console when making requests:
```
INFO: GET /api/v1/users/me
INFO: Authorization header present: True
INFO: Token valid: True
```

## Common Local Issues

### Issue: "Could not connect to database"
**Fix:**
```bash
pnpm db:down
pnpm db:up
pnpm db:migrate:dev
```

### Issue: Backend not starting
**Fix:**
```bash
cd packages/backend
uv sync
uv run uvicorn src.main:app --reload --port 5000
```

### Issue: Frontend build errors
**Fix:**
```bash
cd packages/user
pnpm install
pnpm dev
```

### Issue: Google OAuth error "redirect_uri_mismatch"
**Fix:** Make sure Google Console has this redirect URI:
```
http://localhost:5000/api/v1/auth/google/callback
```

### Issue: CORS errors
**Fix:** Check `.env` has:
```env
CORS_ORIGINS=http://localhost:3003,http://localhost:3002,http://localhost:3000
```

## Local Environment Variables

### Backend (.env)
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/eventai
DIRECT_URL=postgresql://postgres:postgres@localhost:5432/eventai
JWT_SECRET=your-super-secret-jwt-key-min-32-chars
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/api/v1/auth/google/callback
CORS_ORIGINS=http://localhost:3003,http://localhost:3002,http://localhost:3000
FRONTEND_URL=http://localhost:3003
```

### Frontend (.env)
```env
NEXT_PUBLIC_API_URL=http://localhost:5000/api/v1
```

## Manual Token Test

If OAuth doesn't work locally, test with manual token:

### 1. Register a user via API:
```bash
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!",
    "first_name": "Test",
    "last_name": "User"
  }'
```

### 2. Login to get token:
```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=TestPass123!"
```

### 3. Copy access_token from response

### 4. Manually set in browser:
```javascript
// In browser console (http://localhost:3003):
localStorage.setItem('access_token', 'YOUR_TOKEN_HERE');
localStorage.setItem('refresh_token', 'YOUR_REFRESH_TOKEN_HERE');

// Reload page
location.reload();
```

### 5. Test API calls work:
```javascript
// In console:
fetch('http://localhost:5000/api/v1/users/me', {
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('access_token')
  }
}).then(r => r.json()).then(console.log);
```

## Success Checklist

Local testing passes when:
- [x] OAuth completes without redirect loop
- [x] Tokens stored in localStorage
- [x] Dashboard loads after login
- [x] No 401 errors in console
- [x] `/users/me` returns 200 with user data
- [x] Request headers include `Authorization: Bearer ...`
- [x] SSE connection shows in Network tab (200, eventsource)
- [x] Can navigate to all pages
- [x] Logout clears tokens and redirects to login
- [x] Can login again successfully

## Next Step
Once local testing passes → Deploy to production (see `DEPLOYMENT_CHECKLIST.md`)
