import type { Locator, Page } from '@playwright/test'

export class UploadPage {
  readonly page: Page
  readonly pageTitle: Locator
  readonly templateNameInput: Locator
  readonly pdfDropzone: Locator
  readonly xsdDropzone: Locator
  readonly analyzeButton: Locator
  readonly progressBar: Locator
  readonly errorAlert: Locator
  readonly hint: Locator

  constructor(page: Page) {
    this.page = page
    this.pageTitle = page.locator('.upload__title')
    this.templateNameInput = page.locator('#template-name')
    this.pdfDropzone = page.locator('.dropzone').first()
    this.xsdDropzone = page.locator('.dropzone').nth(1)
    this.analyzeButton = page.locator('.upload__submit')
    this.progressBar = page.locator('.upload__progress')
    this.errorAlert = page.locator('.upload__error')
    this.hint = page.locator('.upload__hint')
  }

  async goto() {
    await this.page.goto('/upload')
  }

  async setTemplateName(name: string) {
    await this.templateNameInput.fill(name)
  }

  /**
   * Upload a PDF file via the hidden file input.
   * Uses a minimal synthetic PDF buffer when no real file is provided.
   */
  async uploadPdf(filePath?: string) {
    const pdfInput = this.page.locator('input[type="file"][accept=".pdf"]')
    if (filePath) {
      await pdfInput.setInputFiles(filePath)
    } else {
      // Minimal valid PDF header for the file input to accept
      const minimalPdf = Buffer.from(
        '%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n' +
          '2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n' +
          '3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n' +
          'xref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF',
      )
      await pdfInput.setInputFiles({
        name: 'test-document.pdf',
        mimeType: 'application/pdf',
        buffer: minimalPdf,
      })
    }
  }

  async uploadXsd(filePath?: string) {
    const xsdInput = this.page.locator('input[type="file"][accept=".xsd"]')
    if (filePath) {
      await xsdInput.setInputFiles(filePath)
    } else {
      const minimalXsd = Buffer.from(
        '<?xml version="1.0"?>\n<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">\n' +
          '  <xs:element name="root"><xs:complexType><xs:sequence>\n' +
          '    <xs:element name="title" type="xs:string"/>\n' +
          '    <xs:element name="body" type="xs:string"/>\n' +
          '  </xs:sequence></xs:complexType></xs:element>\n</xs:schema>',
      )
      await xsdInput.setInputFiles({
        name: 'test-schema.xsd',
        mimeType: 'application/xml',
        buffer: minimalXsd,
      })
    }
  }

  async startAnalysis() {
    await this.analyzeButton.click()
  }
}
