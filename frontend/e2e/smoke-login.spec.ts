import { test, expect } from '@playwright/test'
import { test as authTest } from './fixtures/auth.fixture'
import { LoginPage } from './pages/LoginPage'

test.describe('Smoke: Login Flow', () => {
  test('unauthenticated user is redirected to /login', async ({ page }) => {
    // Without auth session, navigating to home should redirect to login
    await page.goto('/')
    await page.waitForURL('**/login', { timeout: 5_000 })

    const loginPage = new LoginPage(page)
    await expect(loginPage.title).toHaveText('migrador-planet')
    await expect(loginPage.googleButton).toBeVisible()
    await expect(loginPage.googleButton).toContainText('Entrar com Google')
  })

  test('login page shows Google OAuth button', async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.goto()

    // Verify the login card is rendered with key elements
    await expect(loginPage.title).toBeVisible()
    await expect(loginPage.googleButton).toBeVisible()

    // Verify Google icon SVG is present
    const googleIcon = page.locator('.login__google-icon')
    await expect(googleIcon).toBeVisible()
  })

  test('google login button triggers OAuth redirect', async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.goto()

    // Intercept the Supabase OAuth call to prevent actual redirect
    let oauthCalled = false
    await page.route('**/auth/v1/authorize**', async (route) => {
      oauthCalled = true
      // Fulfill to prevent navigation failure
      await route.fulfill({
        status: 302,
        headers: { Location: '/auth/callback?code=mock-code' },
      })
    })

    await loginPage.clickGoogleLogin()

    // Button should show loading state
    await expect(loginPage.googleButton).toContainText('Redirecionando...')
  })
})

authTest.describe('Smoke: Authenticated Navigation', () => {
  authTest(
    'authenticated user can access home page',
    async ({ authenticatedPage: page }) => {
      await page.goto('/')
      // Should NOT redirect to /login
      await page.waitForTimeout(1_000)
      const url = page.url()
      expect(url).not.toContain('/login')
    },
  )
})
