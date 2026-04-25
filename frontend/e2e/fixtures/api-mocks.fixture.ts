import type { Page, Route } from '@playwright/test'

/**
 * Mock API responses for E2E smoke tests.
 * Intercepts backend calls so tests don't depend on a running FastAPI server.
 */

const MOCK_JOB_ID = 'e2e-job-00000000-0000-0000-0000-000000000001'

/** Pipeline SSE events matching the RawSSEData format the app expects */
const SSE_EVENTS = [
  `data: {"stage":1,"status":"running"}\n\n`,
  `data: {"stage":1,"status":"completed"}\n\n`,
  `data: {"stage":2,"status":"running"}\n\n`,
  `data: {"stage":2,"status":"completed"}\n\n`,
  `data: {"stage":3,"status":"running"}\n\n`,
  `data: {"stage":3,"status":"completed"}\n\n`,
  `data: {"stage":4,"status":"running"}\n\n`,
  `data: {"stage":4,"status":"completed"}\n\n`,
  `data: {"stage":5,"status":"running"}\n\n`,
  `data: {"stage":5,"status":"completed"}\n\n`,
  `data: {"event":"pipeline_completed"}\n\n`,
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
  // Upload endpoint (files upload + job creation)
  await page.route('**/api/upload', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ job_id: MOCK_JOB_ID, template_name: 'E2E Test Template' }),
    })
  })

  // Start pipeline endpoint (called by AnalyzingPage on mount)
  await page.route('**/api/v1/analyze', async (route: Route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ job_id: MOCK_JOB_ID }),
      })
    }
  })

  // SSE progress stream (correct URL: /api/v1/analyze/{jobId}/progress)
  await page.route(`**/api/v1/analyze/${MOCK_JOB_ID}/progress`, async (route: Route) => {
    const body = SSE_EVENTS.join('')
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      headers: { 'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no' },
      body,
    })
  })

  // Pipeline result (correct URL: /api/v1/analyze/{jobId}/result)
  await page.route(`**/api/v1/analyze/${MOCK_JOB_ID}/result`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'completed', result: PIPELINE_RESULT }),
    })
  })

  // Job status polling (correct URL: /api/v1/analyze/{jobId}/status)
  await page.route(`**/api/v1/analyze/${MOCK_JOB_ID}/status`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'completed', progress: 100 }),
    })
  })

  // Export ZIP
  await page.route('**/api/export**', async (route: Route) => {
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
