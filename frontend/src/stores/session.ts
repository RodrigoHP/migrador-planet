import { defineStore } from 'pinia'
import type {
  PdfFile,
  XsdFile,
  DataFile,
  CrossValidation,
  ExtractionResult,
  SavedProjectV2,
} from '@/types'
import type { PipelineResult } from '@/types/pipeline.types'
import type { DocumentTree } from '@/types/template.types'

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

export const useSessionStore = defineStore('session', {
  state: (): SessionStore => ({
    currentStep: 0,
    jobId: null,
    template_name: null,
    uploadedPdfs: [],
    analysisCompleted: false,
    isProcessing: false,
    processingStep: '',
    processingPct: 0,
    error: null,
    pdfFile: null,
    xsdFile: null,
    dataFile: null,
    crossValidation: { status: null, divergences: [] },
    extraction: null,
  }),
  getters: {
    allFilesSelected: (state) =>
      state.pdfFile !== null && state.xsdFile !== null && state.dataFile !== null,
  },
  actions: {
    setError(msg: string | null) {
      this.error = msg
    },
    resetProcessing() {
      this.error = null
      this.isProcessing = false
      this.jobId = null
      this.analysisCompleted = false
      this.processingPct = 0
      this.processingStep = ''
    },
    async loadFromPipelineResult(result: PipelineResult) {
      this.error = null
      // Story 38.6: Populate template_name from pipeline result
      const resultTemplateName = (result as Record<string, unknown>).template_name as
        | string
        | undefined
      if (resultTemplateName && !this.template_name) {
        this.template_name = sanitizeTemplateName(resultTemplateName)
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
        { name: 'mappingStore', fn: () => loadMappingStoreData(result, mappingStore) },
        { name: 'confidenceStore', fn: () => loadConfidenceStoreData(result, confidenceStore) },
        { name: 'coverageStore', fn: () => loadCoverageStoreData(result, coverageStore) },
        { name: 'generationStore', fn: () => loadGenerationStoreData(result, generationStore) },
        { name: 'inspectorStore', fn: () => loadInspectorStoreData(result, inspectorStore) },
        { name: 'multiDocStore', fn: () => loadMultiDocStoreData(result, multiDocStore) },
      ]

      for (const { name, fn } of storeLoaders) {
        try {
          fn()
        } catch (e) {
          this.error = `Erro ao carregar ${name}: ${e instanceof Error ? e.message : String(e)}`
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
        this.error = `Erro ao reconciliar bindings: ${e instanceof Error ? e.message : String(e)}`
        return
      }

      // Story 36.5: Auto-populate testDataStore (non-critical)
      try {
        await loadTestDataStoreData(result, this.dataFile, testDataStore)
      } catch {
        // Non-critical: failing to populate test data should not block the pipeline
      }

      this.analysisCompleted = true
    },

    /**
     * Restore editor state from a SavedProjectV2 JSON file (Story 8.2, AC6/AC7).
     */
    async loadFromSavedProject(data: SavedProjectV2) {
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
      const fileVersion = (data as Record<string, unknown>).version as string | undefined
      if (fileVersion && !KNOWN_PROJECT_VERSIONS.has(fileVersion)) {
        console.warn(
          `[session] Versao desconhecida do projeto: "${fileVersion}". ` +
            `Versoes conhecidas: ${[...KNOWN_PROJECT_VERSIONS].join(', ')}. Tentando carregar mesmo assim.`,
        )
      }

      try {
        this.template_name = data.templateName ? sanitizeTemplateName(data.templateName) : null

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

        this.analysisCompleted = true
      } catch (e) {
        throw new Error(
          `Falha ao restaurar projeto: ${e instanceof Error ? e.message : String(e)}`,
          { cause: e },
        )
      }
    },
  },
})
