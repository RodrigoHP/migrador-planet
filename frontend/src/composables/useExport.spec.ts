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

// ─── Mock usePreExportValidation for useExport tests ─────────────────────────
// Validation logic is tested independently in usePreExportValidation.spec.ts
vi.mock('./usePreExportValidation', () => ({
  usePreExportValidation: () => ({
    validate: vi.fn(() => ({ hasBlockingErrors: false, errors: [], warnings: [] })),
  }),
  SYSTEM_LIBS: [],
  extractDataBindValues: vi.fn(() => []),
  extractBindingFields: vi.fn(() => []),
  isCssValid: vi.fn(() => ({ valid: true })),
  isHtmlWellFormed: vi.fn(() => ({ valid: true })),
  extractBibliotecaRefs: vi.fn(() => []),
  extractAssetRefs: vi.fn(() => []),
}))

// ─── Mock JSZip ───────────────────────────────────────────────────────────────
// Track files added to zip for structure assertions
const zipFiles: Record<string, string | Uint8Array> = {}
const zipFolders: string[] = []

vi.mock('jszip', () => {
  const makeFolder = (prefix: string): unknown => ({
    file: vi.fn((name: string, data: string | Uint8Array) => {
      zipFiles[`${prefix}/${name}`] = data
    }),
    folder: vi.fn().mockImplementation((name: string) => {
      const fullPath = `${prefix}/${name}`
      zipFolders.push(fullPath)
      return makeFolder(fullPath)
    }),
  })

  function MockJSZip(this: Record<string, unknown>) {
    this.folder = vi.fn().mockImplementation((name: string) => {
      zipFolders.push(name)
      return makeFolder(name)
    })
    this.generateAsync = vi.fn().mockResolvedValue(new Blob(['zip-content'], { type: 'application/zip' }))
  }

  return { default: MockJSZip }
})

// ─── Mock codeStore ──────────────────────────────────────────────────────────
const mockFileContents = {
  html: '<html><head></head><body><div data-bind="text: nome"></div><script src="../Bibliotecas/js/knockout-3.4.2.js"></script><script src="js/base.js"></script></body></html>',
  css: 'body { margin: 0; }',
  js: '"use strict"; var ViewModel = function(data) {};',
  exemplo: 'var data = {};',
}

vi.mock('@/stores/codeStore', () => ({
  useCodeStore: () => ({
    fileContents: { ...mockFileContents },
  }),
}))

// ─── Mock baseJsGenerators ──────────────────────────────────────────────────
vi.mock('@/stores/baseJsGenerators', () => ({
  generateQuebraTabelaFn: () => 'function quebrarTabelaEntrePaginas() {}',
  generateCriarNovaPaginaFn: () => 'function criarNovaPagina() {}',
  generateReposicionarElementoFixoFn: () => 'function reposicionarElementoFixo() {}',
}))

// ─── Common setup ─────────────────────────────────────────────────────────────

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

// ─── Story 31.3: rewriteHtmlForExport ────────────────────────────────────────

describe('rewriteHtmlForExport', () => {
  it('replaces Bibliotecas KO reference with CDN', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    const html = '<script src="../Bibliotecas/js/knockout-3.4.2.js"></script>'
    const result = rewriteHtmlForExport(html)
    expect(result).toContain('cdnjs.cloudflare.com/ajax/libs/knockout')
    expect(result).not.toContain('Bibliotecas')
  })

  it('replaces Bibliotecas Chart.js reference with CDN', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    const html = '<script src="../Bibliotecas/js/Chart.min.js"></script>'
    const result = rewriteHtmlForExport(html)
    expect(result).toContain('cdn.jsdelivr.net/npm/chart.js')
    expect(result).not.toContain('Bibliotecas')
  })

  it('removes Bibliotecas reset.css reference', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    const html = '<link rel="stylesheet" href="../Bibliotecas/css/reset.css">'
    const result = rewriteHtmlForExport(html)
    expect(result).not.toContain('reset.css')
    expect(result).not.toContain('Bibliotecas')
  })

  it('injects JsBarcode CDN when barcodes are present (Story 31.5)', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    const html = '<html><head></head><body><div data-type="barcode" data-format="CODE128"></div></body></html>'
    const result = rewriteHtmlForExport(html)
    expect(result).toContain('jsbarcode')
    expect(result).toContain('cdn.jsdelivr.net')
  })

  it('does NOT inject JsBarcode when no barcodes', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    const html = '<html><head></head><body><div>Hello</div></body></html>'
    const result = rewriteHtmlForExport(html)
    expect(result).not.toContain('jsbarcode')
  })

  it('injects Knockout CDN when KO bindings exist but no script tag', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    const html = '<html><head></head><body><div data-bind="text: nome"></div></body></html>'
    const result = rewriteHtmlForExport(html)
    expect(result).toContain('knockout-min.js')
  })

  it('returns empty string for empty input', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    expect(rewriteHtmlForExport('')).toBe('')
  })
})

// ─── Story 31.2: extractInlineAssets ─────────────────────────────────────────

describe('extractInlineAssets', () => {
  it('extracts data URI images and replaces with relative paths', async () => {
    const { extractInlineAssets } = await import('./useExport')
    // Simple 1x1 red PNG in base64
    const pngBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
    const html = `<img src="data:image/png;base64,${pngBase64}" />`
    const result = extractInlineAssets(html)

    expect(result.assets).toHaveLength(1)
    expect(result.assets[0].filename).toBe('img-1.png')
    expect(result.assets[0].data).toBeInstanceOf(Uint8Array)
    expect(result.html).toContain('src="assets/img-1.png"')
    expect(result.html).not.toContain('data:image')
  })

  it('handles multiple inline images', async () => {
    const { extractInlineAssets } = await import('./useExport')
    const b64 = 'AAAA'
    const html = `<img src="data:image/png;base64,${b64}" /><img src="data:image/jpeg;base64,${b64}" />`
    const result = extractInlineAssets(html)

    expect(result.assets).toHaveLength(2)
    expect(result.assets[0].filename).toBe('img-1.png')
    expect(result.assets[1].filename).toBe('img-2.jpg')
  })

  it('returns empty assets for HTML without data URIs', async () => {
    const { extractInlineAssets } = await import('./useExport')
    const html = '<img src="assets/logo.png" />'
    const result = extractInlineAssets(html)
    expect(result.assets).toHaveLength(0)
    expect(result.html).toBe(html)
  })

  it('handles empty HTML', async () => {
    const { extractInlineAssets } = await import('./useExport')
    const result = extractInlineAssets('')
    expect(result.html).toBe('')
    expect(result.assets).toHaveLength(0)
  })
})

// ─── Story 31.7: injectPaginationFunctions ───────────────────────────────────

describe('injectPaginationFunctions', () => {
  it('injects all three pagination functions when absent', async () => {
    const { injectPaginationFunctions } = await import('./useExport')
    const js = '"use strict"; var x = 1;'
    const result = injectPaginationFunctions(js)

    expect(result).toContain('quebrarTabelaEntrePaginas')
    expect(result).toContain('criarNovaPagina')
    expect(result).toContain('reposicionarElementoFixo')
    expect(result).toContain('Funções de paginação runtime')
  })

  it('does NOT inject when functions already present', async () => {
    const { injectPaginationFunctions } = await import('./useExport')
    const js = 'function quebrarTabelaEntrePaginas() {}\nfunction criarNovaPagina() {}\nfunction reposicionarElementoFixo() {}'
    const result = injectPaginationFunctions(js)

    // Should be unchanged — no duplication
    expect(result).toBe(js)
  })

  it('injects only missing functions', async () => {
    const { injectPaginationFunctions } = await import('./useExport')
    const js = 'function quebrarTabelaEntrePaginas() {} function criarNovaPagina() {}'
    const result = injectPaginationFunctions(js)

    expect(result).toContain('reposicionarElementoFixo')
    // Should not duplicate existing ones
    expect(result.match(/quebrarTabelaEntrePaginas/g)?.length).toBe(1)
  })

  it('handles empty JS', async () => {
    const { injectPaginationFunctions } = await import('./useExport')
    expect(injectPaginationFunctions('')).toBe('')
  })
})

// ─── Story 31.6: generateFontFaceRules ───────────────────────────────────────

describe('generateFontFaceRules', () => {
  it('generates @font-face for custom fonts', async () => {
    const { generateFontFaceRules } = await import('./useExport')
    const css = `.f-myfont { font-family: 'MyFont', sans-serif; font-size: 12pt; }`
    const result = generateFontFaceRules(css)

    expect(result.fontFaces).toHaveLength(1)
    expect(result.fontFaces[0].fontFamily).toBe('MyFont')
    expect(result.css).toContain("@font-face")
    expect(result.css).toContain("font-family: 'MyFont'")
    expect(result.css).toContain("fonts/myfont.woff2")
  })

  it('skips system fonts (Arial, Helvetica)', async () => {
    const { generateFontFaceRules } = await import('./useExport')
    const css = `.f-arial { font-family: 'Arial', sans-serif; }`
    const result = generateFontFaceRules(css)

    expect(result.fontFaces).toHaveLength(0)
    expect(result.css).not.toContain('@font-face')
  })

  it('handles CSS without font classes', async () => {
    const { generateFontFaceRules } = await import('./useExport')
    const css = 'body { margin: 0; }'
    const result = generateFontFaceRules(css)

    expect(result.fontFaces).toHaveLength(0)
    expect(result.css).toBe(css)
  })

  it('handles empty CSS', async () => {
    const { generateFontFaceRules } = await import('./useExport')
    const result = generateFontFaceRules('')
    expect(result.css).toBe('')
    expect(result.fontFaces).toHaveLength(0)
  })
})

// ─── Story 31.4: useExport uses codeStore ────────────────────────────────────

describe('useExport', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    // Clear tracked files
    Object.keys(zipFiles).forEach((k) => delete zipFiles[k])
    zipFolders.length = 0
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('exportZip uses codeStore content instead of /api/generate (Story 31.4)', async () => {
    const fetchSpy = vi.fn()
    global.fetch = fetchSpy

    const { useExport } = await import('./useExport')
    setupDownloadMocks()

    const { exportZip } = useExport()
    const result = await exportZip({ skipWarnings: true })

    expect(result.success).toBe(true)
    // Should NOT have called fetch since codeStore has content
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('exportZip triggers download on success', async () => {
    const { useExport } = await import('./useExport')
    const { clickSpy } = setupDownloadMocks()

    const { exportZip } = useExport()
    const result = await exportZip({ skipWarnings: true })

    expect(result.success).toBe(true)
    expect(global.URL.createObjectURL).toHaveBeenCalled()
    expect(clickSpy).toHaveBeenCalled()
  })

  it('isExporting resets to false after export completes', async () => {
    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip, isExporting } = useExport()
    await exportZip({ skipWarnings: true })
    expect(isExporting.value).toBe(false)
  })

  it('exportZip with includeTestData succeeds with datasets', async () => {
    const { useTestDataStore } = await import('@/stores/testDataStore')
    const testDataStore = useTestDataStore()
    testDataStore.datasets = [{ id: 'ds-1', name: 'Dataset 1', fields: { foo: 'bar' }, rawContent: '{}', createdAt: '2026-01-01', size: 10, status: 'valid' }]

    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip } = useExport()
    const result = await exportZip({ includeTestData: true, skipWarnings: true })
    expect(result.success).toBe(true)
  })

  it('exportZip returns ExportResult shape', async () => {
    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip } = useExport()
    const result = await exportZip({ skipWarnings: true })
    expect('success' in result).toBe(true)
  })

  it('isExporting is a Vue ref with initial value false', async () => {
    const { useExport } = await import('./useExport')
    const { isExporting } = useExport()
    expect('value' in isExporting).toBe(true)
    expect(isExporting.value).toBe(false)
  })
})

// ─── Story 31.8: E2E ZIP structure verification ──────────────────────────────

describe('E2E: ZIP structure (Story 31.8)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    Object.keys(zipFiles).forEach((k) => delete zipFiles[k])
    zipFolders.length = 0
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('ZIP contains expected folder structure', async () => {
    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip } = useExport()
    await exportZip({ skipWarnings: true })

    expect(zipFolders).toContain('template')
  })

  it('ZIP HTML contains CDN references for Knockout (Story 31.3)', async () => {
    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip } = useExport()
    await exportZip({ skipWarnings: true })

    const htmlContent = zipFiles['template/index.html']
    expect(htmlContent).toBeDefined()
    expect(typeof htmlContent === 'string' ? htmlContent : '').toContain('knockout-min.js')
  })

  it('ZIP CSS is not empty (Story 31.1)', async () => {
    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip } = useExport()
    await exportZip({ skipWarnings: true })

    const cssContent = zipFiles['template/css/style.css']
    expect(cssContent).toBeDefined()
    expect(typeof cssContent === 'string' ? cssContent.length : 0).toBeGreaterThan(0)
  })

  it('ZIP JS contains pagination functions (Story 31.7)', async () => {
    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip } = useExport()
    await exportZip({ skipWarnings: true })

    const jsContent = zipFiles['template/js/base.js']
    expect(jsContent).toBeDefined()
    const jsStr = typeof jsContent === 'string' ? jsContent : ''
    expect(jsStr).toContain('quebrarTabelaEntrePaginas')
    expect(jsStr).toContain('criarNovaPagina')
    expect(jsStr).toContain('reposicionarElementoFixo')
  })
})
