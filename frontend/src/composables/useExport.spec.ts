import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// ─── Mock idb ────────────────────────────────────────────────────────────────
vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      get: vi.fn(() => Promise.resolve(undefined)),
      put: vi.fn(() => Promise.resolve()),
      getAll: vi.fn(() => Promise.resolve([])),
    }),
  ),
}))

// ─── Mock useBibliotecas for export tests ────────────────────────────────────
const mockBibliotecasFiles: {
  category: string
  name: string
  data: ArrayBuffer
  system?: boolean
}[] = []

vi.mock('./useBibliotecas', () => ({
  useBibliotecas: () => ({
    files: { value: mockBibliotecasFiles },
    isLoading: { value: false },
    error: { value: null },
    loadFiles: vi.fn(async () => {
      /* noop — files already set via mockBibliotecasFiles */
    }),
    getByCategory: vi.fn((category: string) =>
      mockBibliotecasFiles.filter((f) => f.category === category),
    ),
  }),
  SYSTEM_LIBS: [
    'knockout-3.4.2.js',
    'knockout.mapping.js',
    'Chart.min.js',
    'chartjs-plugin-datalabels.min.js',
    'JsBarcode.all.min.js',
  ],
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
    this.generateAsync = vi
      .fn()
      .mockResolvedValue(new Blob(['zip-content'], { type: 'application/zip' }))
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

/** Seed mandatory libs into mockBibliotecasFiles so exportZip doesn't fail */
function seedMandatoryLibs() {
  const koData = new TextEncoder().encode('/* knockout 3.4.2 */').buffer
  mockBibliotecasFiles.push({
    category: 'js',
    name: 'knockout-3.4.2.js',
    data: koData,
    system: true,
  })
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
  it('replaces Bibliotecas KO reference with placeholder when no bundledLibs', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    const html = '<script src="../Bibliotecas/js/knockout-3.4.2.js"></script>'
    const result = rewriteHtmlForExport(html)
    expect(result).toContain('não disponível')
    expect(result).not.toContain('Bibliotecas')
    expect(result).not.toContain('cdnjs.cloudflare.com')
    expect(result).not.toContain('cdn.jsdelivr.net')
  })

  it('replaces Bibliotecas KO reference with local path when bundled', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    const html = '<script src="../Bibliotecas/js/knockout-3.4.2.js"></script>'
    const bundled = new Set(['knockout'])
    const result = rewriteHtmlForExport(html, bundled)
    expect(result).toContain('js/lib/knockout-3.4.2.js')
    expect(result).not.toContain('cdnjs.cloudflare.com')
    expect(result).not.toContain('Bibliotecas')
  })

  it('replaces Bibliotecas Chart.js reference with placeholder when no bundledLibs', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    const html = '<script src="../Bibliotecas/js/Chart.min.js"></script>'
    const result = rewriteHtmlForExport(html)
    expect(result).toContain('não disponível')
    expect(result).not.toContain('Bibliotecas')
    expect(result).not.toContain('cdn.jsdelivr.net')
  })

  it('replaces Bibliotecas Chart.js reference with local path when bundled', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    const html = '<script src="../Bibliotecas/js/Chart.min.js"></script>'
    const bundled = new Set(['Chart.min.js'])
    const result = rewriteHtmlForExport(html, bundled)
    expect(result).toContain('js/lib/Chart.min.js')
    expect(result).not.toContain('cdn.jsdelivr.net')
  })

  it('removes Bibliotecas reset.css reference', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    const html = '<link rel="stylesheet" href="../Bibliotecas/css/reset.css">'
    const result = rewriteHtmlForExport(html)
    expect(result).not.toContain('reset.css')
    expect(result).not.toContain('Bibliotecas')
  })

  it('injects JsBarcode placeholder when barcodes are present but not bundled (Story 31.5)', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    const html =
      '<html><head></head><body><div data-type="barcode" data-format="CODE128"></div></body></html>'
    const result = rewriteHtmlForExport(html)
    expect(result).toContain('não disponível')
    expect(result).not.toContain('cdn.jsdelivr.net')
  })

  it('injects JsBarcode local path when bundled and barcodes present', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    const html =
      '<html><head></head><body><div data-type="barcode" data-format="CODE128"></div></body></html>'
    const bundled = new Set(['JsBarcode'])
    const result = rewriteHtmlForExport(html, bundled)
    expect(result).toContain('js/lib/JsBarcode.all.min.js')
    expect(result).not.toContain('cdn.jsdelivr.net')
  })

  it('does NOT inject JsBarcode when no barcodes', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    const html = '<html><head></head><body><div>Hello</div></body></html>'
    const result = rewriteHtmlForExport(html)
    expect(result).not.toContain('JsBarcode')
  })

  it('injects Knockout placeholder when KO bindings exist but no script tag and not bundled', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    const html = '<html><head></head><body><div data-bind="text: nome"></div></body></html>'
    const result = rewriteHtmlForExport(html)
    expect(result).toContain('não disponível')
    expect(result).not.toContain('cdnjs.cloudflare.com')
  })

  it('injects Knockout local path when KO bindings exist and bundled', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    const html = '<html><head></head><body><div data-bind="text: nome"></div></body></html>'
    const bundled = new Set(['knockout'])
    const result = rewriteHtmlForExport(html, bundled)
    expect(result).toContain('js/lib/knockout-3.4.2.js')
  })

  it('NEVER outputs CDN URLs (NFR7 compliance)', async () => {
    const { rewriteHtmlForExport } = await import('./useExport')
    const html =
      '<html><head></head><body><div data-bind="text: nome"></div><div data-type="barcode"></div><div data-chart-type="bar"></div></body></html>'
    const result = rewriteHtmlForExport(html)
    expect(result).not.toContain('cdnjs.cloudflare.com')
    expect(result).not.toContain('cdn.jsdelivr.net')
    expect(result).not.toContain('CDN fallback')
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
    const pngBase64 =
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
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
    const js =
      'function quebrarTabelaEntrePaginas() {}\nfunction criarNovaPagina() {}\nfunction reposicionarElementoFixo() {}'
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
  it('generates @font-face for custom fonts (backwards compat, no availableFonts)', async () => {
    const { generateFontFaceRules } = await import('./useExport')
    const css = `.f-myfont { font-family: 'MyFont', sans-serif; font-size: 12pt; }`
    const result = generateFontFaceRules(css)

    expect(result.fontFaces).toHaveLength(1)
    expect(result.fontFaces[0].fontFamily).toBe('MyFont')
    expect(result.css).toContain('@font-face')
    expect(result.css).toContain("font-family: 'MyFont'")
    expect(result.css).toContain('fonts/myfont.woff2')
  })

  it('generates @font-face only for available extensions (Story 31.6)', async () => {
    const { generateFontFaceRules } = await import('./useExport')
    const css = `.f-roboto { font-family: 'Roboto', sans-serif; }`
    const available = new Map([['roboto', ['.woff2']]])
    const result = generateFontFaceRules(css, available)

    expect(result.fontFaces).toHaveLength(1)
    expect(result.css).toContain('fonts/roboto.woff2')
    expect(result.css).toContain("format('woff2')")
    expect(result.css).not.toContain("fonts/roboto.woff'")
    expect(result.css).not.toContain('fonts/roboto.ttf')
  })

  it('skips font when availableFonts has no entry for className (Story 31.6)', async () => {
    const { generateFontFaceRules } = await import('./useExport')
    const css = `.f-myfont { font-family: 'MyFont', sans-serif; }`
    const available = new Map<string, string[]>() // empty — no fonts available
    const result = generateFontFaceRules(css, available)

    expect(result.fontFaces).toHaveLength(0)
    expect(result.css).not.toContain('@font-face')
    expect(result.css).toBe(css)
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
    mockBibliotecasFiles.length = 0
  })

  it('exportZip uses codeStore content instead of /api/generate (Story 31.4)', async () => {
    const fetchSpy = vi.fn()
    global.fetch = fetchSpy
    seedMandatoryLibs()

    const { useExport } = await import('./useExport')
    setupDownloadMocks()

    const { exportZip } = useExport()
    const result = await exportZip({ skipWarnings: true })

    expect(result.success).toBe(true)
    // Should NOT have called fetch since codeStore has content
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('exportZip triggers download on success', async () => {
    seedMandatoryLibs()
    const { useExport } = await import('./useExport')
    const { clickSpy } = setupDownloadMocks()

    const { exportZip } = useExport()
    const result = await exportZip({ skipWarnings: true })

    expect(result.success).toBe(true)
    expect(global.URL.createObjectURL).toHaveBeenCalled()
    expect(clickSpy).toHaveBeenCalled()
  })

  it('isExporting resets to false after export completes', async () => {
    seedMandatoryLibs()
    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip, isExporting } = useExport()
    await exportZip({ skipWarnings: true })
    expect(isExporting.value).toBe(false)
  })

  it('exportZip with includeTestData succeeds with datasets', async () => {
    seedMandatoryLibs()
    const { useTestDataStore } = await import('@/stores/testDataStore')
    const testDataStore = useTestDataStore()
    testDataStore.datasets = [
      {
        id: 'ds-1',
        name: 'Dataset 1',
        fields: { foo: 'bar' },
        rawContent: '{}',
        createdAt: '2026-01-01',
        size: 10,
        status: 'valid',
      },
    ]

    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip } = useExport()
    const result = await exportZip({ includeTestData: true, skipWarnings: true })
    expect(result.success).toBe(true)
  })

  it('exportZip returns ExportResult shape', async () => {
    seedMandatoryLibs()
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
    mockBibliotecasFiles.length = 0
  })

  it('ZIP contains expected folder structure', async () => {
    seedMandatoryLibs()
    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip } = useExport()
    await exportZip({ skipWarnings: true })

    expect(zipFolders).toContain('template')
  })

  it('ZIP HTML contains local lib path for Knockout when libs bundled (Story 31.3)', async () => {
    // Simulate IDB having real lib content for mandatory knockout
    const koData = new TextEncoder().encode('/* knockout 3.4.2 */').buffer
    mockBibliotecasFiles.push({
      category: 'js',
      name: 'knockout-3.4.2.js',
      data: koData,
      system: true,
    })

    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip } = useExport()
    await exportZip({ skipWarnings: true })

    const htmlContent = zipFiles['template/index.html']
    expect(htmlContent).toBeDefined()
    const htmlStr = typeof htmlContent === 'string' ? htmlContent : ''
    expect(htmlStr).toContain('js/lib/knockout-3.4.2.js')
    expect(htmlStr).not.toContain('CDN fallback')
    expect(htmlStr).not.toContain('cdnjs.cloudflare.com')

    mockBibliotecasFiles.length = 0
  })

  it('ZIP CSS is not empty (Story 31.1)', async () => {
    seedMandatoryLibs()
    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip } = useExport()
    await exportZip({ skipWarnings: true })

    const cssContent = zipFiles['template/css/style.css']
    expect(cssContent).toBeDefined()
    expect(typeof cssContent === 'string' ? cssContent.length : 0).toBeGreaterThan(0)
  })

  it('ZIP JS contains pagination functions (Story 31.7)', async () => {
    seedMandatoryLibs()
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

// ─── Story 31.3: Bundled libs in ZIP ────────────────────────────────────────

describe('Story 31.3: Bundled libs in ZIP', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    Object.keys(zipFiles).forEach((k) => delete zipFiles[k])
    zipFolders.length = 0
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    mockBibliotecasFiles.length = 0
  })

  it('includes bundled lib files in js/lib/ when IDB has real data', async () => {
    // Simulate IDB having real lib content
    const koData = new TextEncoder().encode('/* knockout 3.4.2 */').buffer
    mockBibliotecasFiles.push(
      { category: 'js', name: 'knockout-3.4.2.js', data: koData, system: true },
      {
        category: 'js',
        name: 'Chart.min.js',
        data: new TextEncoder().encode('/* chart */').buffer,
        system: true,
      },
    )

    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip } = useExport()
    await exportZip({ skipWarnings: true })

    // Check that lib files were added to ZIP
    expect(zipFiles['template/js/lib/knockout-3.4.2.js']).toBeDefined()
    expect(zipFiles['template/js/lib/Chart.min.js']).toBeDefined()

    // HTML should have local paths, not CDN
    const htmlContent = zipFiles['template/index.html']
    const htmlStr = typeof htmlContent === 'string' ? htmlContent : ''
    expect(htmlStr).toContain('js/lib/knockout-3.4.2.js')
    expect(htmlStr).not.toContain('cdnjs.cloudflare.com')
  })

  it('export FAILS when mandatory lib (knockout) has empty data (byteLength 0)', async () => {
    // System libs with empty ArrayBuffer — mandatory lib missing
    mockBibliotecasFiles.push({
      category: 'js',
      name: 'knockout-3.4.2.js',
      data: new ArrayBuffer(0),
      system: true,
    })

    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip } = useExport()
    const result = await exportZip({ skipWarnings: true })

    // Export should fail because mandatory knockout lib has no real data
    expect(result.success).toBe(false)
    expect(result.blockingErrors).toBeDefined()
    expect(result.blockingErrors![0]).toContain('knockout')
  })
})

// ─── Story 41.10: replaceImgWithSvgInline ────────────────────────────────────

describe('replaceImgWithSvgInline', () => {
  it('returns html unchanged when no nodes have svgInline', async () => {
    const { replaceImgWithSvgInline } = await import('./useExport')
    const html = '<img id="node-1" style="left:10px" src="img.svg" />'
    const nodes = [
      {
        id: 'node-1',
        type: 'image' as const,
        name: 'img',
        children: [],
        properties: { svgInline: false },
        visibility: true,
      },
    ]
    const result = replaceImgWithSvgInline(html, nodes)
    expect(result).toBe(html)
  })

  it('replaces <img> with <svg> preserving style when svgInline is true (AC7)', async () => {
    const { replaceImgWithSvgInline } = await import('./useExport')
    const svgContent = '<svg xmlns="http://www.w3.org/2000/svg"><circle r="10"/></svg>'
    const html = '<img id="node-1" style="left:10px;top:20px" src="icon.svg" />'
    const nodes = [
      {
        id: 'node-1',
        type: 'image' as const,
        name: 'img',
        children: [],
        properties: {
          svgInline: true,
          svgInlineContent: svgContent,
        },
        visibility: true,
      },
    ]
    const result = replaceImgWithSvgInline(html, nodes)
    expect(result).toContain('<svg')
    expect(result).toContain('id="node-1"')
    expect(result).toContain('style="left:10px;top:20px"')
    expect(result).not.toContain('<img')
    expect(result).toContain('<circle r="10"/>')
  })

  it('handles multiple nodes — replaces only SVG-inline nodes, leaves others untouched (AC2)', async () => {
    const { replaceImgWithSvgInline } = await import('./useExport')
    const svgContent = '<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
    const html =
      '<img id="node-1" style="width:100px" src="a.svg" />' +
      '<img id="node-2" style="width:200px" src="b.png" />'
    const nodes = [
      {
        id: 'node-1',
        type: 'image' as const,
        name: 'img1',
        children: [],
        properties: { svgInline: true, svgInlineContent: svgContent },
        visibility: true,
      },
      {
        id: 'node-2',
        type: 'image' as const,
        name: 'img2',
        children: [],
        properties: { svgInline: false },
        visibility: true,
      },
    ]
    const result = replaceImgWithSvgInline(html, nodes)
    // node-1 should be replaced
    expect(result).toContain('<svg')
    expect(result).toContain('id="node-1"')
    expect(result).toContain('style="width:100px"')
    // node-2 should remain as <img>
    expect(result).toContain('<img id="node-2"')
  })

  it('skips non-image nodes', async () => {
    const { replaceImgWithSvgInline } = await import('./useExport')
    const html = '<div id="node-text">text</div>'
    const nodes = [
      {
        id: 'node-text',
        type: 'text' as const,
        name: 'txt',
        children: [],
        properties: { svgInline: true, svgInlineContent: '<svg/>' },
        visibility: true,
      },
    ]
    const result = replaceImgWithSvgInline(html, nodes)
    expect(result).toBe(html)
  })

  it('returns original html unchanged when svgInlineContent is empty', async () => {
    const { replaceImgWithSvgInline } = await import('./useExport')
    const html = '<img id="node-1" style="left:0" src="img.svg" />'
    const nodes = [
      {
        id: 'node-1',
        type: 'image' as const,
        name: 'img',
        children: [],
        properties: { svgInline: true, svgInlineContent: '' },
        visibility: true,
      },
    ]
    const result = replaceImgWithSvgInline(html, nodes)
    expect(result).toBe(html)
  })

  it('returns html unchanged for empty input', async () => {
    const { replaceImgWithSvgInline } = await import('./useExport')
    expect(replaceImgWithSvgInline('', [])).toBe('')
  })
})

// ─── Story 31.6: Real font files in ZIP ─────────────────────────────────────

describe('Story 31.6: Real font files in ZIP', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    Object.keys(zipFiles).forEach((k) => delete zipFiles[k])
    zipFolders.length = 0
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    mockBibliotecasFiles.length = 0
  })

  it('includes real font file in fonts/ and generates matching @font-face', async () => {
    // Override mockFileContents for this test
    const savedCss = mockFileContents.css
    mockFileContents.css = `.f-roboto { font-family: 'Roboto', sans-serif; }`
    seedMandatoryLibs()

    const fontData = new Uint8Array([0x00, 0x01, 0x00, 0x00]).buffer
    mockBibliotecasFiles.push({ category: 'fonts', name: 'roboto.woff2', data: fontData })

    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip } = useExport()
    await exportZip({ skipWarnings: true })

    // Restore
    mockFileContents.css = savedCss

    // Font file should be in ZIP
    expect(zipFiles['template/fonts/roboto.woff2']).toBeDefined()

    // CSS should have @font-face with correct src
    const cssContent = zipFiles['template/css/style.css']
    const cssStr = typeof cssContent === 'string' ? cssContent : ''
    expect(cssStr).toContain('@font-face')
    expect(cssStr).toContain('fonts/roboto.woff2')
    expect(cssStr).toContain("format('woff2')")
  })

  it('does NOT generate @font-face when font file missing from IDB', async () => {
    const savedCss = mockFileContents.css
    mockFileContents.css = `.f-missing { font-family: 'MissingFont', sans-serif; }`
    seedMandatoryLibs()

    const { useExport } = await import('./useExport')
    setupDownloadMocks()
    const { exportZip } = useExport()
    await exportZip({ skipWarnings: true })

    // Restore
    mockFileContents.css = savedCss

    // CSS should NOT have broken @font-face
    const cssContent = zipFiles['template/css/style.css']
    const cssStr = typeof cssContent === 'string' ? cssContent : ''
    expect(cssStr).not.toContain('@font-face')
  })
})
