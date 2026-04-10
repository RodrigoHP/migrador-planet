import type { Page, Route } from '@playwright/test'

/**
 * Mock API responses for E2E smoke tests.
 * Intercepts backend calls so tests don't depend on a running FastAPI server.
 */

const MOCK_JOB_ID = 'e2e-job-00000000-0000-0000-0000-000000000001'

/** Pipeline SSE events simulating a successful analysis run */
const SSE_EVENTS = [
  `data: {"type":"stage_start","stage":"pdf_extraction","progress":0}\n\n`,
  `data: {"type":"stage_progress","stage":"pdf_extraction","progress":50}\n\n`,
  `data: {"type":"stage_complete","stage":"pdf_extraction","progress":100}\n\n`,
  `data: {"type":"stage_start","stage":"structure_analysis","progress":0}\n\n`,
  `data: {"type":"stage_complete","stage":"structure_analysis","progress":100}\n\n`,
  `data: {"type":"stage_start","stage":"template_generation","progress":0}\n\n`,
  `data: {"type":"stage_complete","stage":"template_generation","progress":100}\n\n`,
  `data: {"type":"pipeline_complete","progress":100}\n\n`,
]

/** Minimal pipeline result payload for hydrating the editor */
const PIPELINE_RESULT = {
  job_id: MOCK_JOB_ID,
  template_name: 'E2E Test Template',
  html: '<div class="page"><h1>{{title}}</h1><p>{{body}}</p></div>',
  css: '.page { padding: 20px; } h1 { color: #333; }',
  fields: [
    { xpath: '/title', label: 'Title', type: 'string', mapped: true },
    { xpath: '/body', label: 'Body', type: 'string', mapped: true },
  ],
  xsd_schema: { elements: [{ name: 'title' }, { name: 'body' }] },
  pages: [{ index: 0, width: 612, height: 792 }],
}

/**
 * Install all API route mocks on a Playwright page.
 * Call this before navigating to any app page.
 */
export async function installApiMocks(page: Page) {
  // Upload endpoint
  await page.route('**/api/upload', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ job_id: MOCK_JOB_ID, template_name: 'E2E Test Template' }),
    })
  })

  // SSE progress stream
  await page.route(`**/api/jobs/${MOCK_JOB_ID}/stream`, async (route: Route) => {
    const body = SSE_EVENTS.join('')
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body,
    })
  })

  // Pipeline result
  await page.route(`**/api/jobs/${MOCK_JOB_ID}/result`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(PIPELINE_RESULT),
    })
  })

  // Job status polling
  await page.route(`**/api/jobs/${MOCK_JOB_ID}/status`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'completed', progress: 100 }),
    })
  })

  // Export ZIP
  await page.route('**/api/export**', async (route: Route) => {
    // Return a minimal ZIP-like response
    await route.fulfill({
      status: 200,
      contentType: 'application/zip',
      body: Buffer.from('PK\x03\x04mock-zip-content'),
    })
  })

  // Field mapping updates
  await page.route('**/api/fields**', async (route: Route) => {
    if (route.request().method() === 'PUT' || route.request().method() === 'PATCH') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true }),
      })
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(PIPELINE_RESULT.fields),
      })
    }
  })
}

export { MOCK_JOB_ID, PIPELINE_RESULT }
