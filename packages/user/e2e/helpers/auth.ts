/**
 * Auth helpers for Playwright e2e tests.
 * Logs in via the backend API directly (no UI) and stores cookies/token
 * so subsequent page navigations are authenticated.
 */
import { Page, BrowserContext, request } from '@playwright/test';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:5000/api/v1';

export interface TestCredentials {
  email: string;
  password: string;
}

/** Default test user — must exist in the DB */
export const TEST_USER: TestCredentials = {
  email: 'testuser@example.com',
  password: 'TestPass123!',
};

/**
 * Log in via the backend REST API and inject the JWT into the browser context
 * as a cookie so the Next.js portal treats the user as authenticated.
 */
export async function loginViaApi(
  context: BrowserContext,
  credentials: TestCredentials = TEST_USER,
): Promise<string> {
  const apiContext = await request.newContext();

  const resp = await apiContext.post(`${API_URL}/users/login`, {
    data: { email: credentials.email, password: credentials.password },
  });

  if (!resp.ok()) {
    throw new Error(
      `Login failed for ${credentials.email}: ${resp.status()} ${await resp.text()}`,
    );
  }

  const body = await resp.json();
  const token: string = body.access_token ?? body.data?.token ?? body.data?.access_token ?? '';

  if (!token) {
    throw new Error(`No access_token in login response: ${JSON.stringify(body)}`);
  }

  // Store token in localStorage so the portal's fetch calls include it
  await context.addInitScript((t) => {
    window.localStorage.setItem('access_token', t);
  }, token);

  await apiContext.dispose();
  return token;
}

/**
 * Log in through the UI login form.
 */
export async function loginViaUi(
  page: Page,
  credentials: TestCredentials = TEST_USER,
): Promise<void> {
  await page.goto('/login');
  await page.getByLabel('Email address').fill(credentials.email);
  await page.getByLabel('Password').fill(credentials.password);
  await page.getByRole('button', { name: /sign in/i }).click();
  // Wait for redirect away from /login
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15_000 });
}
