/**
 * useExport — Story 8.2 / Story 8.5
 *
 * Orchestrates the full export flow:
 *  1. Pre-export validation (Story 8.5 — real implementation)
 *  2. POST /api/generate to get html, css, js, exemplo
 *  3. Package into a ZIP via JSZip
 *  4. Trigger browser download via Blob + URL.createObjectURL
 */
import { ref } from 'vue'
import JSZip from 'jszip'
import { usePreExportValidation } from './usePreExportValidation'
import type { PreExportValidationResult } from './usePreExportValidation'
import { useSessionStore } from '@/stores/session'
import { useTestDataStore } from '@/stores/testDataStore'
import { useTemplateStore } from '@/stores/templateStore'
import { useMappingStore } from '@/stores/mapping'
import { useLayoutStore } from '@/stores/layout'

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

export function useExport() {
  const isExporting = ref(false)
  const exportError = ref<string | null>(null)
  /** Last validation result — exposed so caller can show ExportValidationModal */
  const lastValidation = ref<PreExportValidationResult | null>(null)

  const { validate } = usePreExportValidation()

  /**
   * Main export function.
   * AC1: calls /api/generate, packages ZIP, triggers download
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

      // AC1: Call /api/generate
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

      if (!response.ok) {
        const msg = `Geração falhou: ${response.status} ${response.statusText}`
        exportError.value = msg
        return { success: false, error: msg }
      }

      const generated = (await response.json()) as {
        html?: string
        css?: string
        js?: string
        exemplo?: string
      }

      // AC2: Build ZIP structure
      const zip = new JSZip()
      const templateFolder = zip.folder('template')!

      templateFolder.file('index.html', generated.html ?? '')

      const cssFolder = templateFolder.folder('css')!
      cssFolder.file('style.css', generated.css ?? '')

      const jsFolder = templateFolder.folder('js')!
      jsFolder.file('base.js', generated.js ?? '')
      jsFolder.file('exemplo.js', generated.exemplo ?? '')

      // Create empty assets/ placeholder (JSZip needs at least one file)
      templateFolder.folder('assets')!.file('.gitkeep', '')

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
