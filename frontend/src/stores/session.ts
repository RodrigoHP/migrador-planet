import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  PdfFile,
  XsdFile,
  DataFile,
  CrossValidation,
  ExtractionResult,
  SavedProjectV2,
} from '@/types'
import type { PipelineResult } from '@/types/pipeline.types'

import {
  sanitizeTemplateName,
  reconcileFieldBindings,
  parseDataFile,
  KNOWN_PROJECT_VERSIONS,
  loadLayoutStoreData,
  loadTemplateStoreData,
  loadMappingStoreData,
  loadConfidenceStoreData,
  loadCoverageStoreData,
  loadGenerationStoreData,
  loadInspectorStoreData,
  loadMultiDocStoreData,
  loadTestDataStoreData,
} from './session.loadPipelineResult'

export interface SessionStore {
  currentStep: 0 | 1 | 2 | 3 | 4 | 5
  jobId: string | null
  template_name: string | null
  uploadedPdfs: PdfFile[]
  analysisCompleted: boolean
  isProcessing: boolean
  processingStep: string
  processingPct: number
  error: string | null
  pdfFile: PdfFile | null
  xsdFile: XsdFile | null
  dataFile: DataFile | null
  crossValidation: CrossValidation
  extraction: ExtractionResult | null
}

export const useSessionStore = defineStore('session', () => {
  const currentStep = ref<0 | 1 | 2 | 3 | 4 | 5>(0)
  const jobId = ref<string | null>(null)
  const template_name = ref<string | null>(null)
  const uploadedPdfs = ref<PdfFile[]>([])
  const analysisCompleted = ref(false)
  const isProcessing = ref(false)
  const processingStep = ref('')
  const processingPct = ref(0)
  const error = ref<string | null>(null)
  const pdfFile = ref<PdfFile | null>(null)
  const xsdFile = ref<XsdFile | null>(null)
  const dataFile = ref<DataFile | null>(null)
  const crossValidation = ref<CrossValidation>({ status: null, divergences: [] })
  const extraction = ref<ExtractionResult | null>(null)

  const allFilesSelected = computed(
    () => pdfFile.value !== null && xsdFile.value !== null && dataFile.value !== null,
  )

  function setError(msg: string | null) {
    error.value = msg
  }

  function resetProcessing() {
    error.value = null
    isProcessing.value = false
    jobId.value = null
    analysisCompleted.value = false
    processingPct.value = 0
    processingStep.value = ''
  }

  async function loadFromPipelineResult(result: PipelineResult) {
    error.value = null
    // Story 38.6: Populate template_name from pipeline result
    const resultTemplateName = (result as unknown as Record<string, unknown>)['template_name'] as
      | string
      | undefined
    if (resultTemplateName && !template_name.value) {
      template_name.value = sanitizeTemplateName(resultTemplateName)
    }

    const { useTemplateStore } = await import('./templateStore')
    const { useMappingStore } = await import('./mapping')
    const { useConfidenceStore } = await import('./confidenceStore')
    const { useCoverageStore } = await import('./coverageStore')
    const { useLayoutStore } = await import('./layout')
    const { useGenerationStore } = await import('./generation')
    const { useInspectorStore } = await import('./inspectorStore')
    const { useMultiDocStore } = await import('./multiDocStore')
    const { useTestDataStore } = await import('./testDataStore')

    const templateStore = useTemplateStore()
    const mappingStore = useMappingStore()
    const confidenceStore = useConfidenceStore()
    const coverageStore = useCoverageStore()
    const layoutStore = useLayoutStore()
    const generationStore = useGenerationStore()
    const inspectorStore = useInspectorStore()
    const multiDocStore = useMultiDocStore()
    const testDataStore = useTestDataStore()

    // Story 40.6: Each store loader is an extracted < 50 LOC function
    const storeLoaders: Array<{ name: string; fn: () => void }> = [
      { name: 'layoutStore', fn: () => loadLayoutStoreData(result, layoutStore) },
      {
        name: 'templateStore',
        fn: () => loadTemplateStoreData(result, layoutStore, templateStore),
      },
      { name: 'mappingStore', fn: () => loadMappingStoreData(result, mappingStore as unknown as Parameters<typeof loadMappingStoreData>[1]) },
      { name: 'confidenceStore', fn: () => loadConfidenceStoreData(result, confidenceStore) },
      { name: 'coverageStore', fn: () => loadCoverageStoreData(result, coverageStore as unknown as Parameters<typeof loadCoverageStoreData>[1]) },
      { name: 'generationStore', fn: () => loadGenerationStoreData(result, generationStore as unknown as Parameters<typeof loadGenerationStoreData>[1]) },
      { name: 'inspectorStore', fn: () => loadInspectorStoreData(result, inspectorStore) },
      { name: 'multiDocStore', fn: () => loadMultiDocStoreData(result, multiDocStore as unknown as Parameters<typeof loadMultiDocStoreData>[1]) },
    ]

    for (const { name, fn } of storeLoaders) {
      try {
        fn()
      } catch (e) {
        error.value = `Erro ao carregar ${name}: ${e instanceof Error ? e.message : String(e)}`
        return
      }
    }

    // Reconcile field bindings
    try {
      reconcileFieldBindings(
        (result.field_mappings ?? []) as Array<{ block_id?: string; xsd_field_path?: string }>,
        templateStore,
        mappingStore,
      )
    } catch (e) {
      error.value = `Erro ao reconciliar bindings: ${e instanceof Error ? e.message : String(e)}`
      return
    }

    // Story 36.5: Auto-populate testDataStore (non-critical)
    try {
      await loadTestDataStoreData(result, dataFile.value, testDataStore as unknown as Parameters<typeof loadTestDataStoreData>[2])
    } catch {
      // Non-critical: failing to populate test data should not block the pipeline
    }

    analysisCompleted.value = true
  }

  /**
   * Restore editor state from a SavedProjectV2 JSON file (Story 8.2, AC6/AC7).
   */
  async function loadFromSavedProject(data: SavedProjectV2) {
    const { useTemplateStore } = await import('./templateStore')
    const { useMappingStore } = await import('./mapping')
    const { useConfidenceStore } = await import('./confidenceStore')
    const { useCoverageStore } = await import('./coverageStore')
    const { useLayoutStore } = await import('./layout')
    const { useEditorStore } = await import('./editorStore')
    const { useCodeStore } = await import('./codeStore')
    const { useTestDataStore } = await import('./testDataStore')

    const templateStore = useTemplateStore()
    const mappingStore = useMappingStore()
    const confidenceStore = useConfidenceStore()
    const coverageStore = useCoverageStore()
    const layoutStore = useLayoutStore()
    const editorStore = useEditorStore()
    const codeStore = useCodeStore()
    const testDataStore = useTestDataStore()

    // Story 36.7 Fix 2: Validate version
    const fileVersion = (data as unknown as Record<string, unknown>).version as string | undefined
    if (fileVersion && !KNOWN_PROJECT_VERSIONS.has(fileVersion)) {
      if (import.meta.env.DEV) {
        console.warn(
          `[session] Versao desconhecida do projeto: "${fileVersion}". ` +
            `Versoes conhecidas: ${[...KNOWN_PROJECT_VERSIONS].join(', ')}. Tentando carregar mesmo assim.`,
        )
      }
    }

    try {
      template_name.value = data.templateName ? sanitizeTemplateName(data.templateName) : null

      if (data.documentTree) {
        templateStore.loadTree(data.documentTree)
      }

      if (data.fieldMappings?.length) {
        mappingStore.loadPipelineFields(data.fieldMappings)
      }

      if (data.layoutTypes?.length) {
        layoutStore.loadLayoutTypes(data.layoutTypes)
        if (data.activeLayoutId) {
          layoutStore.$patch({ activeLayoutId: data.activeLayoutId })
        }
      }

      if (data.confidence) {
        confidenceStore.loadConfidence(data.confidence)
      }

      if (data.coverage) {
        coverageStore.loadCoverage(data.coverage)
      }

      if (data.editorState) {
        const es = data.editorState
        editorStore.$patch({
          activeCenterTab: es.activeCenterTab,
          activeLeftTab: es.activeLeftTab,
          zoomLevel: es.zoomLevel,
          selectedElementId: es.selectedElementId,
          activeSidebarTab: es.activeSidebarTab,
          pdfZoom: es.pdfZoom,
          coverageMode: es.toggles?.coverageMode ?? false,
          diffMode: es.toggles?.diffMode ?? false,
          snapEnabled: es.toggles?.snapEnabled ?? true,
          autoFixEnabled: es.toggles?.autoFixEnabled ?? false,
          showGuides: es.toggles?.showGuides ?? false,
        })
      }

      if (data.codeFiles) {
        if (data.codeFiles.html) codeStore.setFileContent('html', data.codeFiles.html)
        if (data.codeFiles.css) codeStore.setFileContent('css', data.codeFiles.css)
        if (data.codeFiles.js) codeStore.setFileContent('js', data.codeFiles.js)
      }

      if (data.testDatasets?.length) {
        for (const dataset of data.testDatasets) {
          testDataStore.addDataset(dataset)
        }
      }

      if (data.xsdFlatPaths?.length) {
        mappingStore.setFlatPaths(data.xsdFlatPaths)
      }

      analysisCompleted.value = true
    } catch (e) {
      throw new Error(`Falha ao restaurar projeto: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  return {
    currentStep,
    jobId,
    template_name,
    uploadedPdfs,
    analysisCompleted,
    isProcessing,
    processingStep,
    processingPct,
    error,
    pdfFile,
    xsdFile,
    dataFile,
    crossValidation,
    extraction,
    allFilesSelected,
    setError,
    resetProcessing,
    loadFromPipelineResult,
    loadFromSavedProject,
  }
})

// Re-export parseDataFile for consumers that import it from this module
export { parseDataFile }
