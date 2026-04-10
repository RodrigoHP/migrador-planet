import { test as base, type Page } from '@playwright/test'

/**
 * Auth fixture — bypasses Supabase OAuth by injecting a mock session
 * into localStorage before navigation, so the auth guard lets the user through.
 */
export const MOCK_SESSION = {
  access_token: 'e2e-test-token-abc123',
  refresh_token: 'e2e-refresh-token',
  expires_in: 3600,
  expires_at: Math.floor(Date.now() / 1000) + 3600,
  token_type: 'bearer',
  user: {
    id: 'e2e-user-00000000-0000-0000-0000-000000000001',
    email: 'e2e-test@migrador-planet.test',
    aud: 'authenticated',
    role: 'authenticated',
    app_metadata: { provider: 'google' },
    user_metadata: { full_name: 'E2E Tester', avatar_url: '' },
  },
}

/**
 * Inject the mock Supabase session into localStorage so the auth store
 * picks it up on page load (same key Supabase JS client uses).
 */
async function injectAuthSession(page: Page) {
  const supabaseUrl = process.env.VITE_SUPABASE_URL ?? 'http://localhost:54321'
  // Supabase stores session under: sb-<project-ref>-auth-token
  // For local dev the key varies; we use a wildcard-safe approach.
  const projectRef = new URL(supabaseUrl).hostname.split('.')[0] ?? 'localhost'
  const storageKey = `sb-${projectRef}-auth-token`

  await page.addInitScript(
    ({ key, session }) => {
      window.localStorage.setItem(key, JSON.stringify(session))
    },
    { key: storageKey, session: MOCK_SESSION },
  )
}

/**
 * Extended test fixture that provides an authenticated page.
 * Usage: `import { test, expect } from '../fixtures/auth.fixture'`
 */
export const test = base.extend<{ authenticatedPage: Page }>({
  authenticatedPage: async ({ page }, use) => {
    await injectAuthSession(page)
    await use(page)
  },
})

export { expect } from '@playwright/test'
