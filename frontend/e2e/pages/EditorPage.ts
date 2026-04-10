import type { Locator, Page } from '@playwright/test'

export class EditorPage {
  readonly page: Page
  readonly editorLayout: Locator
  readonly canvas: Locator
  readonly inspectorPanel: Locator
  readonly leftPanel: Locator
  readonly toolbar: Locator

  constructor(page: Page) {
    this.page = page
    this.editorLayout = page.locator('.editor-layout, [class*="editor-layout"]')
    this.canvas = page.locator('.canvas, iframe, [class*="canvas"]').first()
    this.inspectorPanel = page.locator(
      '.inspector, [class*="inspector"], [class*="right-panel"]',
    ).first()
    this.leftPanel = page.locator(
      '.left-panel, [class*="left-panel"], [class*="sidebar"]',
    ).first()
    this.toolbar = page.locator(
      '.toolbar, [class*="toolbar"], [class*="topbar"]',
    ).first()
  }

  async waitForLoad(timeout = 10_000) {
    await this.page.waitForURL('**/editor', { timeout })
    // Wait for the layout to render
    await this.editorLayout.waitFor({ state: 'visible', timeout })
  }

  async getPageTitle() {
    return this.page.title()
  }
}
