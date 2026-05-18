# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: chat.spec.ts >> AI Chat — Backend Integration >> chat page loads with empty state
- Location: e2e\chat.spec.ts:56:7

# Error details

```
Error: locator.fill: Error: strict mode violation: getByLabel('Password') resolved to 2 elements:
    1) <input value="" required="" id="password" type="password" placeholder="Enter your password" class="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 pr-11 text-sm shadow-sm placeholder:text-gray-400 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#1A3D64]/40 focus:border-[#1A3D64] transition-all duration-150"/> aka getByRole('textbox', { name: 'Password' })
    2) <button type="button" aria-label="Show password" class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors">…</button> aka getByRole('button', { name: 'Show password' })

Call log:
  - waiting for getByLabel('Password')

```

# Page snapshot

```yaml
- generic [ref=e1]:
  - generic [ref=e2]:
    - generic [ref=e3]:
      - generic [ref=e7]:
        - img "Event-AI" [ref=e9]
        - generic [ref=e10]:
          - text: Event-AI
          - generic [ref=e11]:
            - img [ref=e12]
            - generic [ref=e15]: AI-Powered Planning
      - generic [ref=e16]:
        - generic [ref=e17]:
          - img [ref=e18]
          - text: Trusted by 10,000+ event planners in Pakistan
        - heading "Plan unforgettable events with AI" [level=2] [ref=e20]
        - paragraph [ref=e21]: Discover top vendors, get smart recommendations, and manage everything from weddings to corporate events — all in one place.
        - generic [ref=e22]:
          - generic [ref=e23]:
            - paragraph [ref=e24]: 10K+
            - paragraph [ref=e25]: Events Planned
          - generic [ref=e26]:
            - paragraph [ref=e27]: 500+
            - paragraph [ref=e28]: Verified Vendors
          - generic [ref=e29]:
            - paragraph [ref=e30]: 4.9★
            - paragraph [ref=e31]: Average Rating
      - generic [ref=e32]:
        - paragraph [ref=e33]: “Found the perfect photographer and caterer in one afternoon. Event-AI is a game changer.”
        - generic [ref=e34]:
          - generic [ref=e35]: A
          - generic [ref=e36]:
            - paragraph [ref=e37]: Ayesha Khan
            - paragraph [ref=e38]: Wedding Planner, Lahore
    - generic [ref=e40]:
      - generic [ref=e41]:
        - generic [ref=e42]:
          - heading "Welcome back" [level=1] [ref=e43]
          - paragraph [ref=e44]: Sign in to your Event-AI account
        - button "Continue with Google" [ref=e45]:
          - img [ref=e46]
          - text: Continue with Google
        - generic [ref=e55]: or
        - generic [ref=e56]:
          - generic [ref=e57]:
            - text: Email address
            - textbox "Email address" [active] [ref=e58]:
              - /placeholder: you@example.com
              - text: testuser@example.com
          - generic [ref=e59]:
            - generic [ref=e60]:
              - generic [ref=e61]: Password
              - link "Forgot password?" [ref=e62] [cursor=pointer]:
                - /url: /forgot-password
            - generic [ref=e63]:
              - textbox "Password" [ref=e64]:
                - /placeholder: Enter your password
              - button "Show password" [ref=e65]:
                - img [ref=e66]
          - button "Sign in" [ref=e69]
        - paragraph [ref=e70]:
          - text: Don't have an account?
          - link "Create one free" [ref=e71] [cursor=pointer]:
            - /url: /signup
      - generic [ref=e72]:
        - generic [ref=e73]:
          - img [ref=e74]
          - generic [ref=e76]: SSL Secured
        - generic [ref=e77]:
          - img [ref=e78]
          - generic [ref=e83]: 10K+ Users
        - generic [ref=e84]:
          - img [ref=e85]
          - generic [ref=e87]: 4.9 Rating
  - button "Open Next.js Dev Tools" [ref=e93] [cursor=pointer]:
    - img [ref=e94]
  - alert [ref=e97]
```

# Test source

```ts
  1  | /**
  2  |  * Auth helpers for Playwright e2e tests.
  3  |  * Logs in via the backend API directly (no UI) and stores cookies/token
  4  |  * so subsequent page navigations are authenticated.
  5  |  */
  6  | import { Page, BrowserContext, request } from '@playwright/test';
  7  | 
  8  | const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:5000/api/v1';
  9  | 
  10 | export interface TestCredentials {
  11 |   email: string;
  12 |   password: string;
  13 | }
  14 | 
  15 | /** Default test user — must exist in the DB */
  16 | export const TEST_USER: TestCredentials = {
  17 |   email: 'testuser@example.com',
  18 |   password: 'TestPass123!',
  19 | };
  20 | 
  21 | /**
  22 |  * Log in via the backend REST API and inject the JWT into the browser context
  23 |  * as a cookie so the Next.js portal treats the user as authenticated.
  24 |  */
  25 | export async function loginViaApi(
  26 |   context: BrowserContext,
  27 |   credentials: TestCredentials = TEST_USER,
  28 | ): Promise<string> {
  29 |   const apiContext = await request.newContext();
  30 | 
  31 |   const resp = await apiContext.post(`${API_URL}/users/login`, {
  32 |     data: { email: credentials.email, password: credentials.password },
  33 |   });
  34 | 
  35 |   if (!resp.ok()) {
  36 |     throw new Error(
  37 |       `Login failed for ${credentials.email}: ${resp.status()} ${await resp.text()}`,
  38 |     );
  39 |   }
  40 | 
  41 |   const body = await resp.json();
  42 |   const token: string = body.access_token ?? body.data?.token ?? body.data?.access_token ?? '';
  43 | 
  44 |   if (!token) {
  45 |     throw new Error(`No access_token in login response: ${JSON.stringify(body)}`);
  46 |   }
  47 | 
  48 |   // Store token in localStorage so the portal's fetch calls include it
  49 |   await context.addInitScript((t) => {
  50 |     window.localStorage.setItem('access_token', t);
  51 |   }, token);
  52 | 
  53 |   await apiContext.dispose();
  54 |   return token;
  55 | }
  56 | 
  57 | /**
  58 |  * Log in through the UI login form.
  59 |  */
  60 | export async function loginViaUi(
  61 |   page: Page,
  62 |   credentials: TestCredentials = TEST_USER,
  63 | ): Promise<void> {
  64 |   await page.goto('/login');
  65 |   await page.getByLabel('Email address').fill(credentials.email);
> 66 |   await page.getByLabel('Password').fill(credentials.password);
     |                                     ^ Error: locator.fill: Error: strict mode violation: getByLabel('Password') resolved to 2 elements:
  67 |   await page.getByRole('button', { name: /sign in/i }).click();
  68 |   // Wait for redirect away from /login
  69 |   await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15_000 });
  70 | }
  71 | 
```