import { test, expect } from './fixtures/auth.fixture'
import { installApiMocks } from './fixtures/api-mocks.fixture'
import { UploadPage } from './pages/UploadPage'
import { AnalyzingPage } from './pages/AnalyzingPage'

test.describe('Smoke: Upload PDF -> Pipeline -> Editor', () => {
  test('uploads PDF + XSD, runs pipeline, and loads the editor', async ({
    authenticatedPage: page,
  }) => {
    await installApiMocks(page)

    // 1. Navigate to upload page
    const upload = new UploadPage(page)
    await page.goto('/upload')

    // 2. Verify upload page loaded
    await expect(upload.pageTitle).toHaveText('Upload de Arquivos')

    // 3. Fill template name
    await upload.setTemplateName('E2E Smoke Template')

    // 4. Upload a PDF file (synthetic)
    await upload.uploadPdf()

    // 5. Upload an XSD file (synthetic)
    await upload.uploadXsd()

    // 6. The analyze button should be enabled
    await expect(upload.analyzeButton).toBeEnabled()

    // 7. Start analysis
    await upload.startAnalysis()

    // 8. Should navigate to analyzing page
    const analyzing = new AnalyzingPage(page)
    await analyzing.waitForUrl()

    // 9. Wait for pipeline to complete (CompletedSummary renders "Abrir no Editor" button)
    // This validates: upload → /analyzing navigation → SSE stream → pipeline_completed event
    const openEditorBtn = page.locator('.btn-editor')
    await expect(openEditorBtn).toBeVisible({ timeout: 20_000 })
  })
})
