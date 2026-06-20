# Post-Deployment Checklist

## After Render Services are Live

### 1. Get Service URLs
Once all 3 services show "Live" status:
- Backend URL: https://eventai-backend.onrender.com
- Orchestrator URL: https://eventai-orchestrator.onrender.com

### 2. Run Database Migrations

#### For Backend:
1. Go to Render Dashboard → eventai-backend
2. Click "Shell" tab
3. Run: `alembic upgrade head`
4. Verify: Should see migration messages, no errors

#### For Orchestrator:
1. Go to Render Dashboard → eventai-orchestrator
2. Click "Shell" tab
3. Run: `alembic upgrade head`
4. Verify: Should see migration messages for AI tables

### 3. Verify Health Endpoints
Test these URLs in browser:
- Backend: https://eventai-backend.onrender.com/api/v1/health
  - Should return: `{"status": "healthy"}`
  
- Orchestrator: https://eventai-orchestrator.onrender.com/health
  - Should return: `{"status": "ok"}` or similar

### 4. Check Service Logs
Look for any startup errors:
- Backend logs should show: "Application startup complete"
- Orchestrator logs should show: "Application startup complete"

### 5. Update Google OAuth Redirect URI
Once you have the actual backend URL:
1. Go to: https://console.cloud.google.com/apis/credentials
2. Find your OAuth 2.0 Client ID
3. Add to "Authorized redirect URIs":
   - https://eventai-backend.onrender.com/api/v1/auth/google/callback
4. Save changes

### 6. Update Render Environment Variables
Go back to Render and update these with ACTUAL URLs:

#### For eventai-backend:
- GOOGLE_REDIRECT_URI=https://eventai-backend.onrender.com/api/v1/auth/google/callback
- CORS_ORIGINS=[actual Vercel URLs once we deploy frontends]
- FRONTEND_URL=[actual Vercel URL for user portal]

(We'll update CORS_ORIGINS and FRONTEND_URL after Vercel deployment)

---

## Next: Deploy Frontends to Vercel

After backend services are healthy, we'll deploy:
1. User Portal (packages/user)
2. Vendor Portal (packages/vendor)
3. Admin Portal (packages/admin)

Each will get its own Vercel project.
