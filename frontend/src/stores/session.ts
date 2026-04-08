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

  // Build block_id → tree node map by walking the full tree.
  // The backend sets node.id = block_id (stage5_template_generation.py), so we
  // index by node.id. Also check an explicit 'block_id' property for older saves.
  const blockIdToNode = new Map<string, TreeNode>()
  function walkForBlockId(node: TreeNode): void {
    if (node.id) blockIdToNode.set(node.id, node)
    const explicitBlockId = (node as unknown as Record<string, unknown>)['block_id'] as string | undefined
    if (explicitBlockId && explicitBlockId !== node.id) blockIdToNode.set(explicitBlockId, node)
    for (const child of (node.children ?? [])) walkForBlockId(child)
  }
  walkForBlockId(templateStore.documentTree.root)

  // For each mapped field: set node.binding and fieldNavItem.nodeId
  const mappedBlockIds = new Set<string>()
  for (const m of fieldMappings) {
    if (!m.block_id || !m.xsd_field_path) continue
    const node = blockIdToNode.get(m.block_id)
    if (!node) continue
    templateStore.updateNodeProperty(node.id, 'binding', m.xsd_field_path)
    mappedBlockIds.add(m.block_id)
    const navItem = mappingStore.fieldNavItems.find((i) => i.path === m.xsd_field_path)
    if (navItem && !navItem.nodeId) navItem.nodeId = node.id
  }

  // Story 34.7: Apply suggested_binding from tree nodes (auto-bind semantic)
  // Nodes with suggested_binding that don't already have a mapping → set as unconfirmed
  for (const [_blockId, node] of blockIdToNode) {
    const suggestedBinding = (node as unknown as Record<string, unknown>)['suggested_binding'] as string | undefined
    if (!suggestedBinding) continue
    if (node.binding) continue // already mapped by stage4
    if (mappedBlockIds.has(node.id)) continue
    // Set suggested binding and mark as unconfirmed in fieldNavItems
    templateStore.updateNodeProperty(node.id, 'binding', suggestedBinding)
    const navItem = mappingStore.fieldNavItems.find(
      (i) => i.nodeId === node.id || i.path === suggestedBinding,
    )
    if (navItem) {
      navItem.status = 'unconfirmed' as 'mapped' | 'unmapped' | 'unconfirmed'
      navItem.binding = suggestedBinding
      if (!navItem.nodeId) navItem.nodeId = node.id
    }
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
          // AC6: Load tree from active layout's trees_by_layout, falling back to document_structure.
          // IMPORTANT: trees_by_layout values are raw TreeNode objects (bare root), NOT DocumentTree
          // wrappers ({root: TreeNode}). We must normalize before calling loadTree() — otherwise
          // tree.root is undefined and loadTree() silently returns leaving flatNodes empty, which
          // causes ALL FieldNavigator clicks (Vincular, mapped field) to find no node and do nothing.
          const activeId = layoutStore.activeLayoutId
          if (result.trees_by_layout && activeId && result.trees_by_layout[activeId]) {
            const rawEntry = result.trees_by_layout[activeId] as unknown
            // Normalize: if entry already has a .root it is a DocumentTree; otherwise wrap it.
            const docTree: DocumentTree = (rawEntry && typeof rawEntry === 'object' && 'root' in (rawEntry as object))
              ? rawEntry as DocumentTree
              : { root: rawEntry as import('@/types/template.types').TreeNode }
            templateStore.loadTree(docTree)
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
          if (result.field_mappings) mappingStore.loadPipelineFields(
            result.field_mappings as FieldMappingEntry[],
            result.ambiguous_fields ?? [],
          )
          // Story 28.1 — persist XSD flat_paths for the BindingEditor dropdown
          const fieldTree = (result as Record<string, unknown>)['field_tree'] as { flat_paths?: string[] } | undefined
          if (fieldTree?.flat_paths?.length) {
            mappingStore.setFlatPaths(fieldTree.flat_paths)
          }
          // Story 28.2 — surface XSD fields with no PDF match.
          // Backend sends unmapped_xsd_fields as string[] (bare XSD path strings).
          // Frontend UnmappedXsdField requires {xsd_path, required, reason} objects.
          // Normalize strings → UnmappedXsdField before storing.
          if (result.validation_result?.unmapped_xsd_fields?.length) {
            const rawXsdFields = result.validation_result.unmapped_xsd_fields as unknown[]
            const normalized = rawXsdFields.map((f) =>
              typeof f === 'string'
                ? { xsd_path: f, required: false }
                : f as import('@/types/pipeline.types').UnmappedXsdField,
            )
            mappingStore.setUnmappedXsdFields(normalized)
          }
        } },
        { name: 'confidenceStore', fn: () => { if (result.confidence_scores) confidenceStore.loadConfidence(result.confidence_scores as Record<string, ConfidenceFactors>) } },
        { name: 'coverageStore', fn: () => { if (result.coverage) coverageStore.loadCoverage(result.coverage as Record<string, CoverageData>); if (result.overlay_items) coverageStore.loadOverlayItems(result.overlay_items); if (result.anchors) coverageStore.loadAnchors(result.anchors) } },
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

      // Story 36.5: Auto-populate testDataStore from upload data
      try {
        const exampleData = (result as Record<string, unknown>)['example_data'] as Record<string, unknown> | undefined
        const dataFileContent = this.dataFile ? await this._parseDataFile(this.dataFile) : null

        const initialData = exampleData || dataFileContent
        if (initialData && typeof initialData === 'object' && Object.keys(initialData).length > 0) {
          testDataStore.addDataset({
            id: `upload-initial-${Date.now()}`,
            name: 'Upload inicial',
            fields: initialData,
            rawContent: JSON.stringify(initialData, null, 2),
            createdAt: new Date().toISOString(),
            size: JSON.stringify(initialData).length,
            status: 'unvalidated',
          })
        }
      } catch {
        // Non-critical: failing to populate test data should not block the pipeline
      }

      this.analysisCompleted = true
    },

    /**
     * Story 36.5: Parse a DataFile into a JSON object for testDataStore.
     * Handles JSON and XML formats.
     */
    async _parseDataFile(dataFile: DataFile): Promise<Record<string, unknown> | null> {
      try {
        const decoder = new TextDecoder()
        const text = decoder.decode(dataFile.bytes)

        // Try JSON first
        try {
          const parsed = JSON.parse(text)
          if (typeof parsed === 'object' && parsed !== null) return parsed as Record<string, unknown>
        } catch {
          // Not JSON — try XML
        }

        // Try XML
        if (text.trim().startsWith('<')) {
          const { parseXmlToJson } = await import('./testDataStore')
          const result = parseXmlToJson(text)
          if (Object.keys(result).length > 0) return result
        }

        return null
      } catch {
        return null
      }
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

        // Story 36.3: Restore code files into codeStore
        if (data.codeFiles) {
          if (data.codeFiles.html) codeStore.setFileContent('html', data.codeFiles.html)
          if (data.codeFiles.css) codeStore.setFileContent('css', data.codeFiles.css)
          if (data.codeFiles.js) codeStore.setFileContent('js', data.codeFiles.js)
        }

        // Story 36.3: Restore test datasets
        if (data.testDatasets?.length) {
          for (const dataset of data.testDatasets) {
            testDataStore.addDataset(dataset)
          }
        }

        // Story 36.3: Restore XSD flat paths
        if (data.xsdFlatPaths?.length) {
          mappingStore.setFlatPaths(data.xsdFlatPaths)
        }

        // AC7: mark analysis completed so /editor guard passes
        this.analysisCompleted = true
      } catch (e) {
        throw new Error(`Falha ao restaurar projeto: ${e instanceof Error ? e.message : String(e)}`)
      }
    },
  },
})
