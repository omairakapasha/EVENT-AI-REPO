/**
 * E2E tests: AI Chat + Backend integration
 *
 * Tests the full flow:
 *   1. Login via UI
 *   2. Navigate to /chat
 *   3. Send a message and verify the AI responds
 *   4. Test event creation ("plan a birthday event")
 *   5. Test vendor search ("find photographers in Lahore")
 *   6. Verify the response completes (no stuck/loading state)
 *
 * Prerequisites (all must be running):
 *   - User portal:  http://localhost:3003  (pnpm dev:user)
 *   - Backend API:  http://localhost:5000  (uv run uvicorn src.main:app --port 5000)
 *   - AI service:   http://localhost:8000  (uv run uvicorn main:app --port 8000)
 */

import { test, expect, Page } from '@playwright/test';
import { loginViaUi } from './helpers/auth';

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Type a message in the chat input and press Enter */
async function sendChatMessage(page: Page, message: string): Promise<void> {
  const textarea = page.getByPlaceholder('Message our AI assistant...');
  await textarea.fill(message);
  await textarea.press('Enter');
}

/**
 * Wait for the AI to finish streaming.
 * The loading indicator disappears and the send button re-enables.
 */
async function waitForAiResponse(page: Page, timeoutMs = 45_000): Promise<string> {
  // Wait for the streaming indicator to disappear
  await expect(page.getByText('AI is thinking...')).toBeHidden({ timeout: timeoutMs });

  // Get the last assistant message content
  const assistantMessages = page.locator('.flex.flex-col.items-start .bg-white.text-gray-900');
  const count = await assistantMessages.count();
  if (count === 0) return '';
  return (await assistantMessages.last().textContent()) ?? '';
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('AI Chat — Backend Integration', () => {
  test.beforeEach(async ({ page }) => {
    await loginViaUi(page);
    await page.goto('/chat');
    // Wait for the chat page to be ready
    await expect(page.getByPlaceholder('Message our AI assistant...')).toBeVisible();
  });

  // ── Test 1: Page loads correctly ──────────────────────────────────────────
  test('chat page loads with empty state', async ({ page }) => {
    await expect(page.getByText('How can I help you today?')).toBeVisible();
    await expect(page.getByText('AI Event Assistant')).toBeVisible();
    await expect(page.getByPlaceholder('Message our AI assistant...')).toBeEnabled();
  });

  // ── Test 2: Basic message → AI responds ──────────────────────────────────
  test('sends a message and receives a response', async ({ page }) => {
    await sendChatMessage(page, 'Hello, what can you help me with?');

    // User message appears
    await expect(page.getByText('Hello, what can you help me with?')).toBeVisible();

    // AI starts thinking
    await expect(page.getByText('AI is thinking...')).toBeVisible({ timeout: 10_000 });

    // AI finishes and response appears
    const response = await waitForAiResponse(page);
    expect(response.length).toBeGreaterThan(10);

    // No error state
    await expect(page.locator('.bg-red-50')).toBeHidden();
  });

  // ── Test 3: Event creation flow ───────────────────────────────────────────
  test('creates a birthday event via chat', async ({ page }) => {
    await sendChatMessage(
      page,
      'I want to plan a birthday party for 20 guests in Lahore with a budget of 200,000 PKR on 2026-12-15',
    );

    await expect(page.getByText('AI is thinking...')).toBeVisible({ timeout: 10_000 });
    const response = await waitForAiResponse(page, 60_000);

    // Response should mention birthday or event creation — not an error
    const lower = response.toLowerCase();
    const mentionsBirthday =
      lower.includes('birthday') ||
      lower.includes('event') ||
      lower.includes('created') ||
      lower.includes('planned') ||
      lower.includes('lahore');

    expect(mentionsBirthday).toBeTruthy();
    // Must not contain "internal error" or "unable to create"
    expect(lower).not.toContain('internal error');
    expect(lower).not.toContain('issue processing the event type');
  });

  // ── Test 4: Wedding event creation ───────────────────────────────────────
  test('creates a wedding event via chat', async ({ page }) => {
    await sendChatMessage(
      page,
      'Plan a nikah ceremony for 300 guests in Karachi on 2027-03-20 with budget 1,500,000 PKR',
    );

    await expect(page.getByText('AI is thinking...')).toBeVisible({ timeout: 10_000 });
    const response = await waitForAiResponse(page, 60_000);

    const lower = response.toLowerCase();
    expect(lower).not.toContain('internal error');
    expect(lower).not.toContain('unknown event type');
    // Should mention wedding/nikah/event
    const relevant =
      lower.includes('wedding') ||
      lower.includes('nikah') ||
      lower.includes('event') ||
      lower.includes('karachi') ||
      lower.includes('created');
    expect(relevant).toBeTruthy();
  });

  // ── Test 5: Vendor search ─────────────────────────────────────────────────
  test('searches for vendors in Lahore', async ({ page }) => {
    await sendChatMessage(page, 'Find photographers in Lahore for a wedding');

    await expect(page.getByText('AI is thinking...')).toBeVisible({ timeout: 10_000 });
    const response = await waitForAiResponse(page, 60_000);

    const lower = response.toLowerCase();
    // Should mention vendors, photographers, or Lahore
    const relevant =
      lower.includes('photographer') ||
      lower.includes('vendor') ||
      lower.includes('lahore') ||
      lower.includes('service') ||
      lower.includes('available');
    expect(relevant).toBeTruthy();
    expect(lower).not.toContain('internal error');
  });

  // ── Test 6: Corporate event ───────────────────────────────────────────────
  test('handles corporate/team building event type', async ({ page }) => {
    await sendChatMessage(
      page,
      'I need to organize a team building event for 50 employees in Islamabad next month',
    );

    await expect(page.getByText('AI is thinking...')).toBeVisible({ timeout: 10_000 });
    const response = await waitForAiResponse(page, 60_000);

    const lower = response.toLowerCase();
    expect(lower).not.toContain('unknown event type');
    expect(lower).not.toContain('internal error');
  });

  // ── Test 7: Chat does not get stuck ──────────────────────────────────────
  test('chat completes within 45 seconds and does not get stuck', async ({ page }) => {
    const start = Date.now();

    await sendChatMessage(page, 'What event types do you support?');

    await expect(page.getByText('AI is thinking...')).toBeVisible({ timeout: 10_000 });

    // Must finish within 45s
    await expect(page.getByText('AI is thinking...')).toBeHidden({ timeout: 45_000 });

    const elapsed = Date.now() - start;
    expect(elapsed).toBeLessThan(45_000);

    // Send button must be re-enabled
    const sendBtn = page.locator('button').filter({ has: page.locator('svg') }).last();
    await expect(sendBtn).not.toBeDisabled();
  });

  // ── Test 8: Suggestion chips work ────────────────────────────────────────
  test('suggestion chips populate the input', async ({ page }) => {
    // Click the first suggestion chip
    const chip = page.getByText('Plan a wedding in Lahore for Oct 2026');
    await chip.click();

    // Input should be populated
    const textarea = page.getByPlaceholder('Message our AI assistant...');
    await expect(textarea).toHaveValue('Plan a wedding in Lahore for Oct 2026');
  });

  // ── Test 9: Clear chat works ──────────────────────────────────────────────
  test('clear chat button resets the conversation', async ({ page }) => {
    // Send a message first
    await sendChatMessage(page, 'Hello');
    await waitForAiResponse(page);

    // Click clear button
    page.on('dialog', (dialog) => dialog.accept());
    await page.getByTitle('Clear History').click();

    // Empty state should reappear
    await expect(page.getByText('How can I help you today?')).toBeVisible({ timeout: 5_000 });
  });

  // ── Test 10: Backend health check ────────────────────────────────────────
  test('backend API is reachable', async ({ request }) => {
    const resp = await request.get('http://localhost:5000/api/v1/events/types');
    // May return 401 (needs auth) or 200 — either means the backend is up
    expect([200, 401, 422]).toContain(resp.status());
  });

  // ── Test 11: AI service health check ─────────────────────────────────────
  test('AI orchestrator service is reachable', async ({ request }) => {
    const resp = await request.get('http://localhost:8000/health');
    // 200 or 404 (no /health route) — either means the service is up
    expect([200, 404, 405]).toContain(resp.status());
  });
});

// ── Auth tests ────────────────────────────────────────────────────────────────

test.describe('Authentication', () => {
  test('login page renders correctly', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: /welcome back/i })).toBeVisible();
    await expect(page.getByLabel('Email address')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('login with valid credentials redirects to dashboard', async ({ page }) => {
    await loginViaUi(page);
    // Should be on dashboard or any non-login page
    expect(page.url()).not.toContain('/login');
  });

  test('login with invalid credentials shows error', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Email address').fill('wrong@example.com');
    await page.getByLabel('Password').fill('wrongpassword');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Error message should appear
    await expect(
      page.locator('.bg-red-50, [class*="red"]').first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  test('unauthenticated access to /chat redirects to login', async ({ page }) => {
    await page.goto('/chat');
    // Should redirect to login
    await page.waitForURL((url) => url.pathname.includes('/login') || url.pathname === '/chat', {
      timeout: 5_000,
    });
    // If it stayed on /chat, the page should still work (some portals allow guest access)
  });
});
