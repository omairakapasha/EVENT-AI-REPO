# AI Chat Connection Fix

## Issue
**Error**: `Failed to connect to AI assistant`

The AI chat feature was failing because the API routes were trying to read authentication tokens from httpOnly cookies, but the authentication system was changed to use localStorage tokens during the OAuth fix.

## Root Cause

After fixing the OAuth flow, the authentication system was updated to:
- Store tokens in `localStorage` (not httpOnly cookies)
- Attach tokens via `Authorization` header on all API requests

However, the AI chat API routes were still looking for tokens in cookies:

```typescript
// OLD CODE (broken)
const cookieStore = await cookies();
const accessToken = cookieStore.get("access_token")?.value || "";
```

This caused the AI service requests to be unauthenticated, resulting in connection failures.

## Solution

### 1. Updated AI Chat Stream Route (`packages/user/src/app/api/ai/chat/stream/route.ts`)

**Before:**
```typescript
import { cookies } from "next/headers";

// Read from httpOnly cookies (doesn't exist anymore)
const cookieStore = await cookies();
const accessToken = cookieStore.get("access_token")?.value || "";
const authHeader = accessToken ? `Bearer ${accessToken}` : req.headers.get("authorization") ?? "";
```

**After:**
```typescript
// Get Authorization header from client (localStorage token)
const authHeader = req.headers.get("authorization") ?? "";
```

### 2. Updated Chat Page to Send Auth Header (`packages/user/src/app/chat/page.tsx`)

**Chat Stream Request:**
```typescript
const accessToken = localStorage.getItem('access_token');

const response = await fetch('/api/ai/chat/stream', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        ...(accessToken ? { 'Authorization': `Bearer ${accessToken}` } : {}),
    },
    body: JSON.stringify({
        message: userMessage.content,
        session_id: sessionId,
    }),
});
```

**Feedback Request:**
```typescript
const accessToken = localStorage.getItem('access_token');

await fetch('/api/ai/feedback', { 
    method: 'POST',
    headers: { 
        'Content-Type': 'application/json',
        ...(accessToken ? { 'Authorization': `Bearer ${accessToken}` } : {}),
    },
    body: JSON.stringify({ message_id: messageId, feedback: type }) 
});
```

## Files Modified

1. ✅ `packages/user/src/app/api/ai/chat/stream/route.ts` - Removed cookie dependency
2. ✅ `packages/user/src/app/chat/page.tsx` - Added Authorization header to requests
3. ✅ `packages/user/src/app/api/ai/feedback/route.ts` - Already correct (no changes needed)

## Authentication Flow (AI Chat)

```
User opens /chat
  ↓
User types message
  ↓
Chat page reads access_token from localStorage
  ↓
Sends POST /api/ai/chat/stream with Authorization header
  ↓
Next.js API route forwards request to AI service with header
  ↓
AI service validates token and processes request
  ↓
Streams response back to user
  ✅ Success!
```

## Testing Checklist

- [x] AI chat loads without errors
- [x] User can send messages
- [x] AI responds with streaming tokens
- [x] Vendor suggestions display correctly
- [x] Feedback buttons work
- [x] Authentication persists across page refreshes
- [x] Error messages display properly when AI service is down

## Related Issues Fixed

This fix is part of the larger OAuth authentication refactor:
1. ✅ OAuth login working (commit `154ae9a`)
2. ✅ Email/password login working (commit `dd6dbc7`)
3. ✅ Tokens stored in localStorage (consistent across all auth methods)
4. ✅ AI chat authentication fixed (commit `ff5f9d5`)

## Deployment

**Status**: ✅ Deployed to production

**Commit**: `ff5f9d5` - fix: update AI chat to use localStorage tokens instead of cookies

**Vercel**: Auto-deployed after push

## Environment Variables Required

The following environment variables must be set in Vercel for AI chat to work:

```bash
# AI Service Configuration
AI_SERVICE_URL=https://your-ai-service.onrender.com
AI_SERVICE_API_KEY=your_api_key_here
AGENT_SERVICE_URL=https://your-ai-service.onrender.com  # Fallback
```

## Result

✅ **AI Chat is now working with localStorage-based authentication**

Users can:
- Send messages to the AI assistant
- Receive streaming responses
- Get vendor suggestions
- Provide feedback on responses
- Maintain chat history
- Use all AI features without connection errors
