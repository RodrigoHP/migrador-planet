import type { Locator, Page } from '@playwright/test'

export class LoginPage {
  readonly page: Page
  readonly title: Locator
  readonly googleButton: Locator
  readonly errorMessage: Locator

  constructor(page: Page) {
    this.page = page
    this.title = page.locator('.login__title')
    this.googleButton = page.locator('.login__btn')
    this.errorMessage = page.locator('.login__error')
  }

  async goto() {
    await this.page.goto('/login')
  }

  async clickGoogleLogin() {
    await this.googleButton.click()
  }
}
