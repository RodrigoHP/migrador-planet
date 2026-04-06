import { defineStore } from 'pinia'
import type { PdfFile, XsdFile, DataFile, CrossValidation, ExtractionResult, SavedProjectV2 } from '@/types'
import type { PipelineResult, LayoutType } from '@/types/pipeline.types'
import type { DocumentTree, TreeNode } from '@/types/template.types'
import type { FieldMappingEntry } from '@/types/pipeline.types'
import type { ConfidenceFactors } from '@/types/confidence.types'
import type { CoverageData } from '@/types/coverage.types'

/**
 * Walk a document tree and set `properties.is_table_cell = true` on any node
 * whose block_id (or whose children's block_id) is present in tableCellBlockIds.
 *
 * This propagates the `is_table_cell` flag from the flat field_mappings list
 * into the document tree so that ElementInspector.vue can detect table cells
 * regardless of whether the node type is "field", "value", or "cell".
 *
 * Story 14.14 — Fix: is_table_cell flag não garantida em nós de célula de tabela
 */
function applyTableCellFlags(node: TreeNode, tableCellBlockIds: Set<string>): void {
  const nodeAsAny = node as unknown as Record<string, unknown>
  const blockId = nodeAsAny['block_id'] as string | undefined

  // Check if this node's block_id is a table cell
  if (blockId && tableCellBlockIds.has(blockId)) {
    node.properties = { ...node.properties, is_table_cell: true }
  }

  // Check if any child's block_id marks this node as containing a table cell
  // (e.g. a "field" node whose "value" child has a table-cell block_id)
  for (const child of (node.children ?? [])) {
    const childAny = child as unknown as Record<string, unknown>
    const childBlockId = childAny['block_id'] as string | undefined
    if (childBlockId && tableCellBlockIds.has(childBlockId)) {
      // Mark both the parent field node AND the child value node
      node.properties = { ...node.properties, is_table_cell: true }
      ;(child as unknown as { properties: Record<string, unknown> }).properties = {
        ...(child as unknown as { properties: Record<string, unknown> }).properties,
        is_table_cell: true,
      }
    }
  }

  // Recurse into children
  for (const child of (node.children ?? [])) {
    applyTableCellFlags(child, tableCellBlockIds)
  }
}

/**
 * Connect field_mappings → templateStore node bindings → fieldNavItem.nodeId.
 *
 * The backend returns field_mappings with `block_id` (matches tree node's extra
 * block_id property) and `xsd_field_path` (the XSD binding path). Without this
 * reconciliation step, clicking a field in FieldNavigator does nothing because:
 * - TreeNodes start with binding=''
 * - fieldNavItems have nodeId=undefined and binding=undefined
 */
function reconcileFieldBindings(
  fieldMappings: Array<{ block_id?: string; xsd_field_path?: string }>,
  templateStore: { documentTree: DocumentTree | null; updateNodeProperty: (id: string, path: string, value: unknown) => void },
  mappingStore: { fieldNavItems: Array<{ path: string; nodeId?: string }> },
): void {
  if (!fieldMappings.length || !templateStore.documentTree?.root) return

  // Build block_id → tree node map by walking the full tree
  const blockIdToNode = new Map<string, TreeNode>()
  function walkForBlockId(node: TreeNode): void {
    const blockId = (node as unknown as Record<string, unknown>)['block_id'] as string | undefined
    if (blockId) blockIdToNode.set(blockId, node)
    for (const child of (node.children ?? [])) walkForBlockId(child)
  }
  walkForBlockId(templateStore.documentTree.root)

  // For each mapped field: set node.binding and fieldNavItem.nodeId
  for (const m of fieldMappings) {
    if (!m.block_id || !m.xsd_field_path) continue
    const node = blockIdToNode.get(m.block_id)
    if (!node) continue
    templateStore.updateNodeProperty(node.id, 'binding', m.xsd_field_path)
    const navItem = mappingStore.fieldNavItems.find((i) => i.path === m.xsd_field_path)
    if (navItem && !navItem.nodeId) navItem.nodeId = node.id
  }
}

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
            // Story 14.14 — Build table-cell block_id set once for all tree mutations
            const tableCellBlockIds = new Set<string>(
              (result.field_mappings as Array<{ block_id?: string; is_table_cell?: boolean }> ?? [])
                .filter((m) => m.is_table_cell === true && m.block_id)
                .map((m) => m.block_id as string),
            )
            if (result.trees_by_layout) {
              for (const lt of layouts) {
                if (result.trees_by_layout[lt.id]) {
                  lt.documentTree = result.trees_by_layout[lt.id]
                  // Propagate is_table_cell flag into all pre-populated layout trees
                  if (tableCellBlockIds.size > 0 && lt.documentTree?.root) {
                    applyTableCellFlags(lt.documentTree.root, tableCellBlockIds)
                  }
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
          // Story 14.14 — Propagate is_table_cell flag from field_mappings to tree nodes
          if (result.field_mappings && templateStore.documentTree?.root) {
            const tableCellBlockIds = new Set<string>(
              (result.field_mappings as Array<{ block_id?: string; is_table_cell?: boolean }>)
                .filter((m) => m.is_table_cell === true && m.block_id)
                .map((m) => m.block_id as string),
            )
            if (tableCellBlockIds.size > 0) {
              applyTableCellFlags(templateStore.documentTree.root, tableCellBlockIds)
            }
          }
        }},
        { name: 'mappingStore', fn: () => {
          if (result.field_mappings) mappingStore.loadPipelineFields(result.field_mappings as FieldMappingEntry[])
          // Story 28.1 — persist XSD flat_paths for the BindingEditor dropdown
          const fieldTree = (result as Record<string, unknown>)['field_tree'] as { flat_paths?: string[] } | undefined
          if (fieldTree?.flat_paths?.length) {
            mappingStore.setFlatPaths(fieldTree.flat_paths)
          }
          // Story 28.2 — surface XSD fields with no PDF match
          if (result.validation_result?.unmapped_xsd_fields?.length) {
            mappingStore.setUnmappedXsdFields(result.validation_result.unmapped_xsd_fields)
          }
        } },
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

      // Reconcile field bindings: connect templateStore nodes ↔ fieldNavItems
      // using block_id as the bridge between field_mappings and tree nodes.
      // Without this step, clicking a field in FieldNavigator does nothing because
      // fieldNavItem.nodeId is never set and node.binding is always ''.
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
