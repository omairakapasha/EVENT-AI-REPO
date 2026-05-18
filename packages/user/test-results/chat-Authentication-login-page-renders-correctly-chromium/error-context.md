# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: chat.spec.ts >> Authentication >> login page renders correctly
- Location: e2e\chat.spec.ts:224:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByLabel('Password')
Expected: visible
Error: strict mode violation: getByLabel('Password') resolved to 2 elements:
    1) <input value="" required="" id="password" type="password" placeholder="Enter your password" class="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 pr-11 text-sm shadow-sm placeholder:text-gray-400 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#1A3D64]/40 focus:border-[#1A3D64] transition-all duration-150"/> aka getByRole('textbox', { name: 'Password' })
    2) <button type="button" aria-label="Show password" class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors">…</button> aka getByRole('button', { name: 'Show password' })

Call log:
  - Expect "toBeVisible" with timeout 15000ms
  - waiting for getByLabel('Password')

```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
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
            - textbox "Email address" [ref=e58]:
              - /placeholder: you@example.com
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
  128 |   // ── Test 5: Vendor search ─────────────────────────────────────────────────
  129 |   test('searches for vendors in Lahore', async ({ page }) => {
  130 |     await sendChatMessage(page, 'Find photographers in Lahore for a wedding');
  131 | 
  132 |     await expect(page.getByText('AI is thinking...')).toBeVisible({ timeout: 10_000 });
  133 |     const response = await waitForAiResponse(page, 60_000);
  134 | 
  135 |     const lower = response.toLowerCase();
  136 |     // Should mention vendors, photographers, or Lahore
  137 |     const relevant =
  138 |       lower.includes('photographer') ||
  139 |       lower.includes('vendor') ||
  140 |       lower.includes('lahore') ||
  141 |       lower.includes('service') ||
  142 |       lower.includes('available');
  143 |     expect(relevant).toBeTruthy();
  144 |     expect(lower).not.toContain('internal error');
  145 |   });
  146 | 
  147 |   // ── Test 6: Corporate event ───────────────────────────────────────────────
  148 |   test('handles corporate/team building event type', async ({ page }) => {
  149 |     await sendChatMessage(
  150 |       page,
  151 |       'I need to organize a team building event for 50 employees in Islamabad next month',
  152 |     );
  153 | 
  154 |     await expect(page.getByText('AI is thinking...')).toBeVisible({ timeout: 10_000 });
  155 |     const response = await waitForAiResponse(page, 60_000);
  156 | 
  157 |     const lower = response.toLowerCase();
  158 |     expect(lower).not.toContain('unknown event type');
  159 |     expect(lower).not.toContain('internal error');
  160 |   });
  161 | 
  162 |   // ── Test 7: Chat does not get stuck ──────────────────────────────────────
  163 |   test('chat completes within 45 seconds and does not get stuck', async ({ page }) => {
  164 |     const start = Date.now();
  165 | 
  166 |     await sendChatMessage(page, 'What event types do you support?');
  167 | 
  168 |     await expect(page.getByText('AI is thinking...')).toBeVisible({ timeout: 10_000 });
  169 | 
  170 |     // Must finish within 45s
  171 |     await expect(page.getByText('AI is thinking...')).toBeHidden({ timeout: 45_000 });
  172 | 
  173 |     const elapsed = Date.now() - start;
  174 |     expect(elapsed).toBeLessThan(45_000);
  175 | 
  176 |     // Send button must be re-enabled
  177 |     const sendBtn = page.locator('button').filter({ has: page.locator('svg') }).last();
  178 |     await expect(sendBtn).not.toBeDisabled();
  179 |   });
  180 | 
  181 |   // ── Test 8: Suggestion chips work ────────────────────────────────────────
  182 |   test('suggestion chips populate the input', async ({ page }) => {
  183 |     // Click the first suggestion chip
  184 |     const chip = page.getByText('Plan a wedding in Lahore for Oct 2026');
  185 |     await chip.click();
  186 | 
  187 |     // Input should be populated
  188 |     const textarea = page.getByPlaceholder('Message our AI assistant...');
  189 |     await expect(textarea).toHaveValue('Plan a wedding in Lahore for Oct 2026');
  190 |   });
  191 | 
  192 |   // ── Test 9: Clear chat works ──────────────────────────────────────────────
  193 |   test('clear chat button resets the conversation', async ({ page }) => {
  194 |     // Send a message first
  195 |     await sendChatMessage(page, 'Hello');
  196 |     await waitForAiResponse(page);
  197 | 
  198 |     // Click clear button
  199 |     page.on('dialog', (dialog) => dialog.accept());
  200 |     await page.getByTitle('Clear History').click();
  201 | 
  202 |     // Empty state should reappear
  203 |     await expect(page.getByText('How can I help you today?')).toBeVisible({ timeout: 5_000 });
  204 |   });
  205 | 
  206 |   // ── Test 10: Backend health check ────────────────────────────────────────
  207 |   test('backend API is reachable', async ({ request }) => {
  208 |     const resp = await request.get('http://localhost:5000/api/v1/events/types');
  209 |     // May return 401 (needs auth) or 200 — either means the backend is up
  210 |     expect([200, 401, 422]).toContain(resp.status());
  211 |   });
  212 | 
  213 |   // ── Test 11: AI service health check ─────────────────────────────────────
  214 |   test('AI orchestrator service is reachable', async ({ request }) => {
  215 |     const resp = await request.get('http://localhost:8000/health');
  216 |     // 200 or 404 (no /health route) — either means the service is up
  217 |     expect([200, 404, 405]).toContain(resp.status());
  218 |   });
  219 | });
  220 | 
  221 | // ── Auth tests ────────────────────────────────────────────────────────────────
  222 | 
  223 | test.describe('Authentication', () => {
  224 |   test('login page renders correctly', async ({ page }) => {
  225 |     await page.goto('/login');
  226 |     await expect(page.getByRole('heading', { name: /welcome back/i })).toBeVisible();
  227 |     await expect(page.getByLabel('Email address')).toBeVisible();
> 228 |     await expect(page.getByLabel('Password')).toBeVisible();
      |                                               ^ Error: expect(locator).toBeVisible() failed
  229 |     await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  230 |   });
  231 | 
  232 |   test('login with valid credentials redirects to dashboard', async ({ page }) => {
  233 |     await loginViaUi(page);
  234 |     // Should be on dashboard or any non-login page
  235 |     expect(page.url()).not.toContain('/login');
  236 |   });
  237 | 
  238 |   test('login with invalid credentials shows error', async ({ page }) => {
  239 |     await page.goto('/login');
  240 |     await page.getByLabel('Email address').fill('wrong@example.com');
  241 |     await page.getByLabel('Password').fill('wrongpassword');
  242 |     await page.getByRole('button', { name: /sign in/i }).click();
  243 | 
  244 |     // Error message should appear
  245 |     await expect(
  246 |       page.locator('.bg-red-50, [class*="red"]').first(),
  247 |     ).toBeVisible({ timeout: 10_000 });
  248 |   });
  249 | 
  250 |   test('unauthenticated access to /chat redirects to login', async ({ page }) => {
  251 |     await page.goto('/chat');
  252 |     // Should redirect to login
  253 |     await page.waitForURL((url) => url.pathname.includes('/login') || url.pathname === '/chat', {
  254 |       timeout: 5_000,
  255 |     });
  256 |     // If it stayed on /chat, the page should still work (some portals allow guest access)
  257 |   });
  258 | });
  259 | 
```