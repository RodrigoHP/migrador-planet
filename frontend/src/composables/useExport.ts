/**
 * useExport — Story 8.2 / Story 8.5 / Epic 31
 *
 * Orchestrates the full export flow:
 *  1. Pre-export validation (Story 8.5 — real implementation)
 *  2. Gather content from codeStore (Monaco edits prevail — Story 31.4)
 *  3. Process HTML for self-contained ZIP (Story 31.3 / 31.5)
 *  4. Extract inline assets (Story 31.2)
 *  5. Inject pagination functions (Story 31.7)
 *  6. Include custom fonts (Story 31.6)
 *  7. Package into a ZIP via JSZip
 *  8. Trigger browser download via Blob + URL.createObjectURL
 */
import { ref } from 'vue'
import JSZip from 'jszip'
import { usePreExportValidation } from './usePreExportValidation'
import type { PreExportValidationResult } from './usePreExportValidation'
import { useSessionStore } from '@/stores/session'
import { useTestDataStore } from '@/stores/testDataStore'
import { useCodeStore } from '@/stores/codeStore'
import {
  generateQuebraTabelaFn,
  generateCriarNovaPaginaFn,
  generateReposicionarElementoFixoFn,
} from '@/stores/baseJsGenerators'
import { useBibliotecas, SYSTEM_LIBS } from './useBibliotecas'
import type { BibliotecaFile } from './useBibliotecas'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export interface ExportOptions {
  /** When true, include test datasets in test_data/ directory */
  includeTestData?: boolean
  /**
   * When true, skip validation warnings and proceed with export even if
   * there are non-blocking warnings. Blocking errors always stop the export.
   */
  skipWarnings?: boolean
}

export interface ExportResult {
  success: boolean
  error?: string
  blockingErrors?: string[]
  /** Only present when validation produces warnings but no blocking errors */
  hasWarnings?: boolean
}

// ─── CDN URLs for self-contained ZIP (Story 31.3) ────────────────────────────

const CDN_KNOCKOUT =
  'https://cdnjs.cloudflare.com/ajax/libs/knockout/3.4.2/knockout-min.js'
const CDN_CHARTJS =
  'https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js'
const CDN_CHARTJS_DATALABELS =
  'https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2'
const CDN_JSBARCODE =
  'https://cdn.jsdelivr.net/npm/jsbarcode@3/dist/JsBarcode.all.min.js'

// ─── Bibliotecas reference patterns ──────────────────────────────────────────

const BIBLIOTECAS_KO_RE =
  /(<script\s+src=["'])\.\.\/Bibliotecas\/js\/knockout[^"']*\.js(["'][^>]*><\/script>)/gi
const BIBLIOTECAS_CHART_RE =
  /(<script\s+src=["'])\.\.\/Bibliotecas\/js\/Chart\.min\.js(["'][^>]*><\/script>)/gi
const BIBLIOTECAS_CHART_DL_RE =
  /(<script\s+src=["'])\.\.\/Bibliotecas\/js\/chartjs-plugin-datalabels[^"']*\.js(["'][^>]*><\/script>)/gi
const BIBLIOTECAS_RESET_CSS_RE =
  /<link\s+rel=["']stylesheet["']\s+href=["']\.\.\/Bibliotecas\/css\/reset\.css["'][^>]*>/gi

// ─── System fonts that do NOT need @font-face ────────────────────────────────

const SYSTEM_FONTS = new Set([
  'arial', 'helvetica', 'times', 'times-new-roman', 'timesnewroman',
  'courier', 'courier-new', 'couriernew', 'verdana', 'georgia',
  'trebuchet', 'tahoma', 'sans-serif', 'serif', 'monospace',
])

export function useExport() {
  const isExporting = ref(false)
  const exportError = ref<string | null>(null)
  /** Last validation result — exposed so caller can show ExportValidationModal */
  const lastValidation = ref<PreExportValidationResult | null>(null)

  const { validate } = usePreExportValidation()

  /**
   * Main export function.
   * AC1: uses codeStore content (Monaco edits prevail — Story 31.4)
   * AC2: ZIP structure template/index.html, template/css/style.css, template/js/base.js, template/js/exemplo.js, template/assets/
   * AC3: optionally includes test_data/ folder
   * AC7: blocked if pre-export validation finds blocking errors
   * AC8: warns but allows export when only non-blocking warnings
   */
  async function exportZip(options: ExportOptions = {}): Promise<ExportResult> {
    isExporting.value = true
    exportError.value = null

    try {
      // AC7/AC8: Run pre-export validation
      const validationResult = validate()
      lastValidation.value = validationResult

      if (validationResult.hasBlockingErrors) {
        const messages = validationResult.errors
          .filter((e) => e.blocking)
          .map((e) => e.message)
        exportError.value = messages.join(', ')
        return { success: false, blockingErrors: messages }
      }

      // If only warnings and caller wants to surface them before proceeding
      if (validationResult.warnings.length > 0 && !options.skipWarnings) {
        // Return early — caller should show ExportValidationModal, then call again with skipWarnings: true
        isExporting.value = false
        return { success: false, hasWarnings: true }
      }

      // Story 31.4: Use codeStore content directly (Monaco edits prevail)
      const codeStore = useCodeStore()
      let html = codeStore.fileContents.html ?? ''
      let css = codeStore.fileContents.css ?? ''
      let js = codeStore.fileContents.js ?? ''
      const exemplo = codeStore.fileContents.exemplo ?? ''

      // If codeStore has no content, fallback to /api/generate
      if (!html.trim() && !css.trim() && !js.trim()) {
        const generated = await _fetchGenerated()
        if (!generated) {
          const msg = 'Falha na geração do template'
          exportError.value = msg
          return { success: false, error: msg }
        }
        html = generated.html ?? ''
        css = generated.css ?? ''
        js = generated.js ?? ''
      }

      // Story 31.3: Load JS libs from IDB for bundling
      const bundledLibs = new Set<string>()
      const libFileContents = new Map<string, { filename: string; data: ArrayBuffer }>()

      try {
        const bibliotecas = useBibliotecas()
        await bibliotecas.loadFiles()
        const jsFiles = bibliotecas.getByCategory('js')

        // Map SYSTEM_LIBS names to bundled lib keys
        const LIB_KEY_MAP: Record<string, string> = {
          'knockout-3.4.2.js': 'knockout',
          'knockout.mapping.js': 'knockout.mapping',
          'Chart.min.js': 'Chart.min.js',
          'chartjs-plugin-datalabels.min.js': 'chartjs-plugin-datalabels',
        }

        for (const libFile of jsFiles) {
          const key = LIB_KEY_MAP[libFile.name]
          if (key && libFile.data.byteLength > 0) {
            bundledLibs.add(key)
            const localFilename = LIB_LOCAL_PATHS[key]
              ? LIB_LOCAL_PATHS[key].replace('js/lib/', '')
              : libFile.name
            libFileContents.set(key, { filename: localFilename, data: libFile.data })
          }
        }
      } catch {
        // IDB unavailable — CDN fallback will be used
      }

      // Story 31.3/31.5: Rewrite HTML for self-contained ZIP (bundled or CDN fallback)
      html = rewriteHtmlForExport(html, bundledLibs)

      // Story 31.2: Extract inline data URIs to assets
      const { html: processedHtml, assets } = extractInlineAssets(html)
      html = processedHtml

      // Story 31.7: Inject pagination functions into JS
      js = injectPaginationFunctions(js)

      // Story 31.6: Load font files from IDB for real inclusion
      const fontFileContents = new Map<string, { filename: string; data: ArrayBuffer }[]>()
      const availableFonts = new Map<string, string[]>()

      try {
        const bibliotecas = useBibliotecas()
        await bibliotecas.loadFiles()
        const fontFiles = bibliotecas.getByCategory('fonts')

        for (const fontFile of fontFiles) {
          const dotIdx = fontFile.name.lastIndexOf('.')
          if (dotIdx === -1) continue
          const baseName = fontFile.name.slice(0, dotIdx).toLowerCase()
          const ext = fontFile.name.slice(dotIdx).toLowerCase()

          if (!availableFonts.has(baseName)) {
            availableFonts.set(baseName, [])
          }
          availableFonts.get(baseName)!.push(ext)

          if (!fontFileContents.has(baseName)) {
            fontFileContents.set(baseName, [])
          }
          fontFileContents.get(baseName)!.push({
            filename: fontFile.name,
            data: fontFile.data,
          })
        }
      } catch {
        // IDB unavailable — fonts will be skipped
      }

      // Story 31.6: Generate @font-face rules with real available fonts
      const { css: processedCss, fontFaces } = generateFontFaceRules(css, availableFonts)
      css = processedCss

      // AC2: Build ZIP structure
      const zip = new JSZip()
      const templateFolder = zip.folder('template')!

      templateFolder.file('index.html', html)

      const cssFolder = templateFolder.folder('css')!
      cssFolder.file('style.css', css)

      const jsFolder = templateFolder.folder('js')!
      jsFolder.file('base.js', js)
      jsFolder.file('exemplo.js', exemplo)

      // Story 31.3: Include bundled JS libs in template/js/lib/
      if (libFileContents.size > 0) {
        const libFolder = jsFolder.folder('lib')!
        for (const [, { filename, data }] of libFileContents) {
          libFolder.file(filename, data)
        }
      }

      // Story 31.2: Include extracted assets
      const assetsFolder = templateFolder.folder('assets')!
      if (assets.length > 0) {
        for (const asset of assets) {
          assetsFolder.file(asset.filename, asset.data)
        }
      } else {
        // Empty assets/ placeholder
        assetsFolder.file('.gitkeep', '')
      }

      // Story 31.6: Include real font files from IDB
      if (fontFaces.length > 0) {
        const fontsFolder = templateFolder.folder('fonts')!
        let hasRealFonts = false
        for (const { className } of fontFaces) {
          const files = fontFileContents.get(className)
          if (files) {
            for (const { filename, data } of files) {
              fontsFolder.file(filename, data)
              hasRealFonts = true
            }
          }
        }
        if (!hasRealFonts) {
          fontsFolder.file('.gitkeep', '')
        }
      }

      // AC3: Optionally include test datasets
      if (options.includeTestData) {
        const testDataStore = useTestDataStore()
        if (testDataStore.datasets.length > 0) {
          const testDataFolder = zip.folder('test_data')!
          for (const dataset of testDataStore.datasets) {
            const filename = `${dataset.id}.json`
            testDataFolder.file(filename, JSON.stringify(dataset.fields, null, 2))
          }
        }
      }

      // Trigger download
      const sessionStore = useSessionStore()
      const templateName = sessionStore.template_name ?? 'template'
      const zipBlob = await zip.generateAsync({ type: 'blob' })
      downloadBlob(zipBlob, `${templateName}.zip`)

      return { success: true }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      exportError.value = msg
      return { success: false, error: msg }
    } finally {
      isExporting.value = false
    }
  }

  return { exportZip, isExporting, exportError, lastValidation }
}

// ─── Internal helpers ─────────────────────────────────────────────────────────

/** Trigger a file download using Blob + URL.createObjectURL */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}

/** Trigger a JSON file download */
export function downloadJson(data: unknown, filename: string): void {
  const json = JSON.stringify(data, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  downloadBlob(blob, filename)
}

/**
 * Fallback: fetch generated content from /api/generate.
 * Used only when codeStore has no content (Monaco not initialized).
 */
async function _fetchGenerated(): Promise<{
  html?: string
  css?: string
  js?: string
  exemplo?: string
} | null> {
  try {
    const { useTemplateStore } = await import('@/stores/templateStore')
    const { useMappingStore } = await import('@/stores/mapping')
    const { useLayoutStore } = await import('@/stores/layout')
    const sessionStore = useSessionStore()
    const templateStore = useTemplateStore()
    const mappingStore = useMappingStore()
    const layoutStore = useLayoutStore()

    const payload = {
      template_name: sessionStore.template_name ?? 'template',
      document_structure: templateStore.documentTree,
      field_mappings: mappingStore.fields,
      layout_types: layoutStore.layoutTypes,
      active_layout_id: layoutStore.activeLayoutId,
    }

    const response = await fetch(`${API_BASE}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (!response.ok) return null
    return await response.json()
  } catch {
    return null
  }
}

// ─── Story 31.3 / 31.5: Rewrite HTML for self-contained export ──────────────

/**
 * Map of lib filename patterns to their local bundled path inside the ZIP.
 * Used when libs are available from IDB (offline mode).
 */
const LIB_LOCAL_PATHS: Record<string, string> = {
  'knockout': 'js/lib/knockout-3.4.2.js',
  'Chart.min.js': 'js/lib/Chart.min.js',
  'chartjs-plugin-datalabels': 'js/lib/chartjs-plugin-datalabels.min.js',
  'JsBarcode': 'js/lib/JsBarcode.all.min.js',
}

/**
 * Rewrite HTML to replace ../Bibliotecas/ references with local bundled paths
 * (when bundledLibs are available) or CDN URLs as fallback.
 * Also injects JsBarcode when barcode elements are detected (Story 31.5).
 *
 * @param html - source HTML
 * @param bundledLibs - Set of lib keys available locally in the ZIP (e.g. 'knockout', 'Chart.min.js')
 */
export function rewriteHtmlForExport(html: string, bundledLibs?: Set<string>): string {
  if (!html) return html

  const hasLib = (key: string) => bundledLibs?.has(key) ?? false

  // Replace Knockout reference
  let result = html.replace(
    BIBLIOTECAS_KO_RE,
    hasLib('knockout')
      ? `<script src="${LIB_LOCAL_PATHS['knockout']}"></script>`
      : `<!-- CDN fallback --><script src="${CDN_KNOCKOUT}"></script>`,
  )

  // Replace Chart.js reference
  result = result.replace(
    BIBLIOTECAS_CHART_RE,
    hasLib('Chart.min.js')
      ? `<script src="${LIB_LOCAL_PATHS['Chart.min.js']}"></script>`
      : `<!-- CDN fallback --><script src="${CDN_CHARTJS}"></script>`,
  )

  // Replace chartjs-plugin-datalabels reference
  result = result.replace(
    BIBLIOTECAS_CHART_DL_RE,
    hasLib('chartjs-plugin-datalabels')
      ? `<script src="${LIB_LOCAL_PATHS['chartjs-plugin-datalabels']}"></script>`
      : `<!-- CDN fallback --><script src="${CDN_CHARTJS_DATALABELS}"></script>`,
  )

  // Remove Bibliotecas reset.css reference (CSS reset is in style.css)
  result = result.replace(BIBLIOTECAS_RESET_CSS_RE, '')

  // Story 31.5: Inject JsBarcode if barcodes are present
  const hasBarcodes = /data-type=["']barcode["']/.test(result) ||
    /data-format=["']CODE\d+["']/.test(result) ||
    /JsBarcode/.test(result)

  if (hasBarcodes && !result.includes('jsbarcode') && !result.includes('JsBarcode')) {
    const insertPoint = result.indexOf('</head>')
    if (insertPoint !== -1) {
      const tag = hasLib('JsBarcode')
        ? `  <script src="${LIB_LOCAL_PATHS['JsBarcode']}"></script>\n`
        : `  <!-- CDN fallback --><script src="${CDN_JSBARCODE}"></script>\n`
      result =
        result.slice(0, insertPoint) +
        tag +
        result.slice(insertPoint)
    }
  }

  // Detect charts and inject if not already present
  const hasCharts = /data-chart-type=/.test(result) || /Chart\./.test(result)
  if (hasCharts && !result.includes('chart.js') && !result.includes('Chart.min.js') && !result.includes('chart.umd.min.js')) {
    const insertPoint = result.indexOf('</head>')
    if (insertPoint !== -1) {
      const chartTag = hasLib('Chart.min.js')
        ? `  <script src="${LIB_LOCAL_PATHS['Chart.min.js']}"></script>\n`
        : `  <!-- CDN fallback --><script src="${CDN_CHARTJS}"></script>\n`
      const dlTag = hasLib('chartjs-plugin-datalabels')
        ? `  <script src="${LIB_LOCAL_PATHS['chartjs-plugin-datalabels']}"></script>\n`
        : `  <!-- CDN fallback --><script src="${CDN_CHARTJS_DATALABELS}"></script>\n`
      result =
        result.slice(0, insertPoint) +
        chartTag +
        dlTag +
        result.slice(insertPoint)
    }
  }

  // Ensure Knockout is present if KO bindings exist
  const hasKoBindings = /data-bind=/.test(result) || /<!-- ko /.test(result)
  if (hasKoBindings && !result.includes('knockout') && !result.includes('knockout-min.js') && !result.includes('knockout-3.4.2.js')) {
    const insertPoint = result.indexOf('</head>')
    if (insertPoint !== -1) {
      const tag = hasLib('knockout')
        ? `  <script src="${LIB_LOCAL_PATHS['knockout']}"></script>\n`
        : `  <!-- CDN fallback --><script src="${CDN_KNOCKOUT}"></script>\n`
      result =
        result.slice(0, insertPoint) +
        tag +
        result.slice(insertPoint)
    }
  }

  return result
}

// ─── Story 31.2: Extract inline data URI assets ──────────────────────────────

export interface ExtractedAsset {
  filename: string
  data: Uint8Array
}

/**
 * Extract data URI images from HTML and replace with relative asset paths.
 * Returns processed HTML and array of extracted assets.
 */
export function extractInlineAssets(html: string): {
  html: string
  assets: ExtractedAsset[]
} {
  if (!html) return { html, assets: [] }

  const assets: ExtractedAsset[] = []
  let counter = 0

  const result = html.replace(
    /src=["'](data:(image\/(?:png|jpeg|webp|svg\+xml));base64,([^"']+))["']/g,
    (_match, _fullUri, mimeType: string, base64Data: string) => {
      counter++
      const ext = mimeType === 'image/png' ? '.png'
        : mimeType === 'image/jpeg' ? '.jpg'
        : mimeType === 'image/webp' ? '.webp'
        : '.svg'
      const filename = `img-${counter}${ext}`

      try {
        const binary = atob(base64Data)
        const bytes = new Uint8Array(binary.length)
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i)
        }
        assets.push({ filename, data: bytes })
      } catch {
        // Invalid base64 — skip extraction, keep original
        return `src="${_fullUri}"`
      }

      return `src="assets/${filename}"`
    },
  )

  return { html: result, assets }
}

// ─── Story 31.7: Inject pagination functions ─────────────────────────────────

/**
 * Inject pagination runtime functions into base.js if not already present.
 * Uses generators from baseJsGenerators.ts.
 */
export function injectPaginationFunctions(js: string): string {
  if (!js) return js

  const functions: string[] = []

  if (!js.includes('quebrarTabelaEntrePaginas')) {
    functions.push(generateQuebraTabelaFn())
  }

  if (!js.includes('criarNovaPagina')) {
    functions.push(generateCriarNovaPaginaFn())
  }

  if (!js.includes('reposicionarElementoFixo')) {
    functions.push(generateReposicionarElementoFixoFn())
  }

  if (functions.length === 0) return js

  const paginationBlock = [
    '',
    '/* ──────────────────────────────────────────────────────────────────────',
    '   Funções de paginação runtime (geradas automaticamente — Epic 31)',
    '   ────────────────────────────────────────────────────────────────────── */',
    '',
    ...functions,
    '',
  ].join('\n')

  return js + paginationBlock
}

// ─── Story 31.6: Generate @font-face rules ───────────────────────────────────

interface FontFaceEntry {
  fontFamily: string
  className: string
}

/**
 * Detect custom font classes (.f-{name}) in CSS and prepend @font-face rules.
 * System fonts (Arial, Helvetica, etc.) are skipped.
 *
 * When `availableFonts` is provided, only generates @font-face for fonts that
 * actually exist (avoiding broken references). The map keys are classNames,
 * values are arrays of available extensions (e.g. ['.woff2', '.ttf']).
 *
 * When `availableFonts` is NOT provided, falls back to guessing all 3 extensions
 * (woff2, woff, ttf) for backwards compatibility.
 */
export function generateFontFaceRules(css: string, availableFonts?: Map<string, string[]>): {
  css: string
  fontFaces: FontFaceEntry[]
} {
  if (!css) return { css, fontFaces: [] }

  const fontFaces: FontFaceEntry[] = []
  // Match .f-{class} { font-family: '{name}', ... }
  const fontClassRe = /\.f-([\w-]+)\s*\{\s*font-family:\s*'([^']+)'/g
  let match: RegExpExecArray | null

  while ((match = fontClassRe.exec(css)) !== null) {
    const className = match[1]
    const fontFamily = match[2]
    const normalized = className.toLowerCase().replace(/[^a-z0-9]/g, '')

    if (SYSTEM_FONTS.has(normalized)) continue

    // Story 31.6: If availableFonts provided, skip fonts without real files
    if (availableFonts) {
      const exts = availableFonts.get(className)
      if (!exts || exts.length === 0) continue
    }

    fontFaces.push({ fontFamily, className })
  }

  if (fontFaces.length === 0) return { css, fontFaces }

  const FORMAT_MAP: Record<string, string> = {
    '.woff2': 'woff2',
    '.woff': 'woff',
    '.ttf': 'truetype',
    '.otf': 'opentype',
  }

  // Generate @font-face rules (referencing fonts/ directory)
  const fontFaceRules = fontFaces
    .map(({ fontFamily, className }) => {
      let srcLines: string[]

      if (availableFonts) {
        const exts = availableFonts.get(className) ?? []
        srcLines = exts.map((ext) => {
          const format = FORMAT_MAP[ext] ?? 'truetype'
          return `url('fonts/${className}${ext}') format('${format}')`
        })
      } else {
        // Fallback: guess common extensions (backwards compat)
        srcLines = [
          `url('fonts/${className}.woff2') format('woff2')`,
          `url('fonts/${className}.woff') format('woff')`,
          `url('fonts/${className}.ttf') format('truetype')`,
        ]
      }

      const srcValue = srcLines.length === 1
        ? `  src: ${srcLines[0]};`
        : `  src: ${srcLines[0]},\n` +
          srcLines.slice(1).map((l, i) => i === srcLines.length - 2 ? `       ${l};` : `       ${l},`).join('\n')

      return [
        `@font-face {`,
        `  font-family: '${fontFamily}';`,
        srcValue,
        `  font-display: swap;`,
        `}`,
      ].join('\n')
    })
    .join('\n\n')

  return {
    css: fontFaceRules + '\n\n' + css,
    fontFaces,
  }
}
