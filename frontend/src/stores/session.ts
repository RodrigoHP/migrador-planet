import { defineStore } from 'pinia'
import type { PdfFile, XsdFile, DataFile, CrossValidation, ExtractionResult, SavedProjectV2 } from '@/types'
import type { PipelineResult, LayoutType } from '@/types/pipeline.types'
import type { DocumentTree } from '@/types/template.types'
import type { FieldMappingEntry } from '@/types/pipeline.types'
import type { ConfidenceFactors } from '@/types/confidence.types'
import type { CoverageData } from '@/types/coverage.types'

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
      const { useTemplateStore } = await import('./templateStore')
      const { useMappingStore } = await import('./mapping')
      const { useConfidenceStore } = await import('./confidenceStore')
      const { useCoverageStore } = await import('./coverageStore')
      const { useLayoutStore } = await import('./layout')
      const { useGenerationStore } = await import('./generation')
      const { useInspectorStore } = await import('./inspectorStore')
      const { useMultiDocStore } = await import('./multiDocStore')

      const templateStore = useTemplateStore()
      const mappingStore = useMappingStore()
      const confidenceStore = useConfidenceStore()
      const coverageStore = useCoverageStore()
      const layoutStore = useLayoutStore()
      const generationStore = useGenerationStore()
      const inspectorStore = useInspectorStore()
      const multiDocStore = useMultiDocStore()

      const storeLoaders: Array<{ name: string; fn: () => void }> = [
        { name: 'layoutStore', fn: () => {
          if (result.layout_types) {
            // AC4: Pre-populate ALL layouts with their rich state (tree, confidence, coverage)
            const layouts = result.layout_types as LayoutType[]
            if (result.trees_by_layout) {
              for (const lt of layouts) {
                if (result.trees_by_layout[lt.id]) {
                  lt.documentTree = result.trees_by_layout[lt.id]
                }
              }
            }
            if (result.confidence_scores) {
              for (const lt of layouts) {
                if (result.confidence_scores[lt.id]) {
                  lt.confidence = result.confidence_scores[lt.id]
                }
              }
            }
            if (result.coverage) {
              for (const lt of layouts) {
                if (result.coverage[lt.id]) {
                  lt.coverage = result.coverage[lt.id]
                }
              }
            }
            layoutStore.loadLayoutTypes(layouts)
          }
        }},
        { name: 'templateStore', fn: () => {
          // AC6: Load tree from active layout's trees_by_layout, falling back to document_structure
          const activeId = layoutStore.activeLayoutId
          if (result.trees_by_layout && activeId && result.trees_by_layout[activeId]) {
            templateStore.loadTree(result.trees_by_layout[activeId] as DocumentTree)
          } else if (result.document_structure?.root) {
            templateStore.loadTree(result.document_structure as DocumentTree)
          }
          if (result.document_type) templateStore.setDocumentType(result.document_type)
        }},
        { name: 'mappingStore', fn: () => { if (result.field_mappings) mappingStore.loadPipelineFields(result.field_mappings as FieldMappingEntry[]) } },
        { name: 'confidenceStore', fn: () => { if (result.confidence_scores) confidenceStore.loadConfidence(result.confidence_scores as Record<string, ConfidenceFactors>) } },
        { name: 'coverageStore', fn: () => { if (result.coverage) coverageStore.loadCoverage(result.coverage as Record<string, CoverageData>); if (result.overlay_items) coverageStore.loadOverlayItems(result.overlay_items) } },
        { name: 'generationStore', fn: () => { if (result.template_draft) generationStore.loadTemplateDraft(result.template_draft) } },
        { name: 'inspectorStore', fn: () => { if (result.document_structure?.root) inspectorStore.initFromTree(result.document_structure.root) } },
        // AC5: Connect to multiDocStore
        { name: 'multiDocStore', fn: () => {
          if (result.multi_doc) {
            multiDocStore.populateFromPipeline(result.multi_doc)
          }
        }},
      ]

      for (const { name, fn } of storeLoaders) {
        try {
          fn()
        } catch (e) {
          this.error = `Erro ao carregar ${name}: ${e instanceof Error ? e.message : String(e)}`
          return
        }
      }

      this.analysisCompleted = true
    },

    /**
     * Restore editor state from a SavedProjectV2 JSON file (Story 8.2, AC6/AC7).
     * Dispatches to all relevant stores and marks analysis as completed so
     * the /editor route guard passes.
     */
    async loadFromSavedProject(data: SavedProjectV2) {
      const { useTemplateStore } = await import('./templateStore')
      const { useMappingStore } = await import('./mapping')
      const { useConfidenceStore } = await import('./confidenceStore')
      const { useCoverageStore } = await import('./coverageStore')
      const { useLayoutStore } = await import('./layout')
      const { useEditorStore } = await import('./editorStore')

      const templateStore = useTemplateStore()
      const mappingStore = useMappingStore()
      const confidenceStore = useConfidenceStore()
      const coverageStore = useCoverageStore()
      const layoutStore = useLayoutStore()
      const editorStore = useEditorStore()

      try {
        // Restore template name
        this.template_name = data.templateName

        // Restore document tree
        if (data.documentTree) {
          templateStore.loadTree(data.documentTree)
        }

        // Restore field mappings
        if (data.fieldMappings?.length) {
          mappingStore.loadPipelineFields(data.fieldMappings)
        }

        // Restore layout types and active layout
        if (data.layoutTypes?.length) {
          layoutStore.loadLayoutTypes(data.layoutTypes)
          if (data.activeLayoutId) {
            layoutStore.$patch({ activeLayoutId: data.activeLayoutId })
          }
        }

        // Restore confidence
        if (data.confidence) {
          confidenceStore.loadConfidence(data.confidence)
        }

        // Restore coverage
        if (data.coverage) {
          coverageStore.loadCoverage(data.coverage)
        }

        // Restore editor UI state
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
            snapEnabled: es.toggles?.snapEnabled ?? false,
            autoFixEnabled: es.toggles?.autoFixEnabled ?? false,
            showGuides: es.toggles?.showGuides ?? false,
          })
        }

        // AC7: mark analysis completed so /editor guard passes
        this.analysisCompleted = true
      } catch (e) {
        throw new Error(`Falha ao restaurar projeto: ${e instanceof Error ? e.message : String(e)}`)
      }
    },
  },
})
