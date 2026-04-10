import type { Locator, Page } from '@playwright/test'

export class AnalyzingPage {
  readonly page: Page
  readonly progressSection: Locator
  readonly stageLabels: Locator

  constructor(page: Page) {
    this.page = page
    // The analyzing page shows pipeline progress; selectors depend on the actual component
    this.progressSection = page.locator('.analyzing, [class*="analyzing"], .progress')
    this.stageLabels = page.locator('.stage-label, .progress-stage, [class*="stage"]')
  }

  async waitForUrl() {
    await this.page.waitForURL('**/analyzing', { timeout: 10_000 })
  }

  async waitForCompletion(timeout = 15_000) {
    // Wait for navigation away from /analyzing (to /editor on success)
    await this.page.waitForURL('**/editor', { timeout })
  }
}
