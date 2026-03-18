import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// ─── Mock idb ────────────────────────────────────────────────────────────────
vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      get: vi.fn(() => Promise.resolve(undefined)),
      put: vi.fn(() => Promise.resolve()),
    }),
  ),
}))

// ─── Mock JSZip ───────────────────────────────────────────────────────────────
vi.mock('jszip', () => {
  const makeFolder = (): unknown => ({
    file: vi.fn().mockReturnThis(),
    folder: vi.fn().mockImplementation(makeFolder),
  })

  // Use regular function so `new JSZip()` returns an instance with the mocked methods
  function MockJSZip(this: Record<string, unknown>) {
    this.folder = vi.fn().mockImplementation(makeFolder)
    this.generateAsync = vi.fn().mockResolvedValue(new Blob(['zip-content'], { type: 'application/zip' }))
  }

  return { default: MockJSZip }
})

// ─── Common setup ─────────────────────────────────────────────────────────────
const mockGenerateResponse = {
  html: '<html></html>',
  css: 'body {}',
  js: '// base',
  exemplo: '// exemplo',
}

function setupDownloadMocks() {
  global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
  global.URL.revokeObjectURL = vi.fn()
  const clickSpy = vi.fn()
  const originalCreate = document.createElement.bind(document)
  vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
    if (tag === 'a') return { href: '', download: '', click: clickSpy } as unknown as HTMLElement
    return originalCreate(tag)
  })
  return { clickSpy }
}

describe('usePreExportValidation', () => {
  it('stub always returns hasBlockingErrors: false', async () => {
    const { usePreExportValidation } = await import('./usePreExportValidation')
    const { validate } = usePreExportValidation()
    const result = validate()
    expect(result.hasBlockingErrors).toBe(false)
    expect(result.errors).toEqual([])
  })
})

describe('downloadBlob', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('creates an anchor and clicks it', async () => {
    const { downloadBlob } = await import('./useExport')
    const { clickSpy } = setupDownloadMocks()
    const blob = new Blob(['test'], { type: 'text/plain' })
    downloadBlob(blob, 'test.txt')
    expect(global.URL.createObjectURL).toHaveBeenCalledWith(blob)
    expect(clickSpy).toHaveBeenCalled()
  })
})

describe('downloadJson', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('serializes data and triggers download', async () => {
    const { downloadJson } = await import('./useExport')
    const { clickSpy } = setupDownloadMocks()
    downloadJson({ foo: 'bar' }, 'data.json')
    expect(global.URL.createObjectURL).toHaveBeenCalled()
    expect(clickSpy).toHaveBeenCalled()
  })
})

describe('useExport', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockGenerateResponse,
    } as Response)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('exportZip calls /api/generate and triggers download on success', async () => {
    const { useExport } = await import('./useExport')
    const { clickSpy } = setupDownloadMocks()

    const { exportZip, isExporting } = useExport()

    expect(isExporting.value).toBe(false)
    const result = await exportZip()
    expect(result.success).toBe(true)
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/generate'),
      expect.objectContaining({ method: 'POST' }),
    )
    expect(global.URL.createObjectURL).toHaveBeenCalled()
    expect(clickSpy).toHaveBeenCalled()
  })

  it('exportZip returns error when /api/generate fails', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    } as Response)

    const { useExport } = await import('./useExport')
    const { exportZip } = useExport()
    const result = await exportZip()
    expect(result.success).toBe(false)
    expect(result.error).toBeDefined()
  })

  it('isExporting resets to false after export completes', async () => {
    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip, isExporting } = useExport()
    await exportZip()
    expect(isExporting.value).toBe(false)
  })

  it('exportZip with includeTestData succeeds with datasets', async () => {
    const { useTestDataStore } = await import('@/stores/testDataStore')
    const testDataStore = useTestDataStore()
    testDataStore.datasets = [{ id: 'ds-1', name: 'Dataset 1', fields: { foo: 'bar' }, rawContent: '{}', createdAt: '2026-01-01', size: 10, status: 'valid' }]

    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip } = useExport()
    const result = await exportZip({ includeTestData: true })
    expect(result.success).toBe(true)
  })

  it('exportZip returns ExportResult shape', async () => {
    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip } = useExport()
    const result = await exportZip()
    expect('success' in result).toBe(true)
  })

  it('isExporting is a Vue ref with initial value false', async () => {
    const { useExport } = await import('./useExport')
    const { isExporting } = useExport()
    expect('value' in isExporting).toBe(true)
    expect(isExporting.value).toBe(false)
  })
})
