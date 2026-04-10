/**
 * Story 40.6 — FE-003: Extracted from session.ts loadFromPipelineResult()
 *
 * Each function is < 50 LOC and handles one store's data loading.
 * The orchestrator `loadAllStores()` calls them sequentially with error handling.
 */
import type { PipelineResult, LayoutType, GridInfo } from '@/types/pipeline.types'
import type { DocumentTree, TreeNode } from '@/types/template.types'
import type { FieldMappingEntry } from '@/types/pipeline.types'
import type { ConfidenceFactors } from '@/types/confidence.types'
import type { CoverageData } from '@/types/coverage.types'
import type { DataFile } from '@/types'

// ─── Utility Functions ───────────────────────────────────────────────────────

/** TD-38.2: Sanitize template_name — strip HTML, limit charset, max 100 chars. */
export function sanitizeTemplateName(name: string): string {
  return name
    .replace(/<[^>]*>/g, '')
    .replace(/[^\w\s\-.]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 100)
}

/**
 * Walk a document tree and set `properties.is_table_cell = true` on any node
 * whose block_id (or whose children's block_id) is present in tableCellBlockIds.
 *
 * Story 14.14 — Fix: is_table_cell flag
 */
export function applyTableCellFlags(node: TreeNode, tableCellBlockIds: Set<string>): void {
  const blockId = node.block_id
  if (blockId && tableCellBlockIds.has(blockId)) {
    node.properties = { ...node.properties, is_table_cell: true }
  }
  for (const child of node.children ?? []) {
    const childBlockId = child.block_id
    if (childBlockId && tableCellBlockIds.has(childBlockId)) {
      node.properties = { ...node.properties, is_table_cell: true }
      child.properties = { ...child.properties, is_table_cell: true }
    }
  }
  for (const child of node.children ?? []) {
    applyTableCellFlags(child, tableCellBlockIds)
  }
}

/**
 * Extract GridInfo from a document tree by scanning section nodes for column_positions.
 * Story 39.3 — Column Snap
 */
export function extractGridInfoFromTree(tree: DocumentTree | undefined): GridInfo | undefined {
  if (!tree?.root) return undefined

  const colPositions: number[] = []

  function walk(node: Record<string, unknown>): void {
    const cp = node.column_positions as number[] | undefined
    if (cp && Array.isArray(cp) && cp.length > 0 && colPositions.length === 0) {
      colPositions.push(...cp)
    }
    const children = node.children as Record<string, unknown>[] | undefined
    if (children && Array.isArray(children)) {
      for (const child of children) walk(child)
    }
  }

  walk(tree.root as unknown as Record<string, unknown>)

  if (colPositions.length === 0) return undefined

  return {
    columns: colPositions.length,
    rows: 0,
    columnPositions: colPositions,
    rowPositions: [],
  }
}

/**
 * Connect field_mappings -> templateStore node bindings -> fieldNavItem.nodeId.
 * Story 28.1 — reconcile field bindings
 */
export function reconcileFieldBindings(
  fieldMappings: Array<{ block_id?: string; xsd_field_path?: string }>,
  templateStore: {
    documentTree: DocumentTree | null
    updateNodeProperty: (id: string, path: string, value: unknown) => void
  },
  mappingStore: {
    fieldNavItems: Array<{ path: string; nodeId?: string; status?: string; binding?: string }>
  },
): void {
  if (!fieldMappings.length || !templateStore.documentTree?.root) return

  const blockIdToNode = new Map<string, TreeNode>()
  function walkForBlockId(node: TreeNode): void {
    if (node.id) blockIdToNode.set(node.id, node)
    const explicitBlockId = node.block_id
    if (explicitBlockId && explicitBlockId !== node.id) blockIdToNode.set(explicitBlockId, node)
    for (const child of node.children ?? []) walkForBlockId(child)
  }
  walkForBlockId(templateStore.documentTree.root)

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

  // Story 34.7: Apply suggested_binding from tree nodes
  for (const [_blockId, node] of blockIdToNode) {
    const suggestedBinding = node.suggested_binding
    if (!suggestedBinding) continue
    if (node.binding) continue
    if (mappedBlockIds.has(node.id)) continue
    templateStore.updateNodeProperty(node.id, 'binding', suggestedBinding)
    const navItem = mappingStore.fieldNavItems.find(
      (i) => i.nodeId === node.id || i.path === suggestedBinding,
    )
    if (navItem) {
      navItem.status = 'unconfirmed'
      navItem.binding = suggestedBinding
      if (!navItem.nodeId) navItem.nodeId = node.id
    }
  }
}

/**
 * Parse a DataFile into a JSON object for testDataStore.
 * Story 36.5, Story 36.7 Fix 3
 */
export async function parseDataFile(dataFile: DataFile): Promise<Record<string, unknown> | null> {
  try {
    const decoder = new TextDecoder()
    const text = decoder.decode(dataFile.bytes)

    try {
      const parsed = JSON.parse(text)
      if (typeof parsed === 'object' && parsed !== null) return parsed as Record<string, unknown>
    } catch {
      // Not JSON — try XML
    }

    if (text.trim().startsWith('<')) {
      const { parseXmlToJson } = await import('./testDataStore')
      const result = parseXmlToJson(text)
      if (Object.keys(result).length > 0) return result
    }

    return null
  } catch {
    return null
  }
}

/** Known project file versions. Story 36.7 Fix 2 */
export const KNOWN_PROJECT_VERSIONS = new Set(['2.0', '2.1'])

// ─── Build table-cell block ID set from field mappings ──────────────────────

function buildTableCellBlockIds(
  fieldMappings: Array<{ block_id?: string; is_table_cell?: boolean }> | undefined,
): Set<string> {
  return new Set<string>(
    (fieldMappings ?? [])
      .filter((m) => m.is_table_cell === true && m.block_id)
      .map((m) => m.block_id as string),
  )
}

// ─── Individual Store Loaders ────────────────────────────────────────────────

export function loadLayoutStoreData(
  result: PipelineResult,
  layoutStore: { loadLayoutTypes: (layouts: LayoutType[]) => void },
): void {
  if (!result.layout_types) return

  const layouts = result.layout_types as LayoutType[]
  const tableCellBlockIds = buildTableCellBlockIds(
    result.field_mappings as Array<{ block_id?: string; is_table_cell?: boolean }>,
  )

  if (result.trees_by_layout) {
    for (const lt of layouts) {
      if (result.trees_by_layout[lt.id]) {
        lt.documentTree = result.trees_by_layout[lt.id]
        if (tableCellBlockIds.size > 0 && lt.documentTree?.root) {
          applyTableCellFlags(lt.documentTree.root, tableCellBlockIds)
        }
      }
    }
  }

  // Story 39.3 — Extract gridInfo
  for (const lt of layouts) {
    if (!lt.gridInfo && lt.documentTree) {
      lt.gridInfo = extractGridInfoFromTree(lt.documentTree)
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

export function loadTemplateStoreData(
  result: PipelineResult,
  layoutStore: { activeLayoutId: string | null },
  templateStore: {
    loadTree: (tree: DocumentTree) => void
    setDocumentType: (type: string) => void
    documentTree: DocumentTree | null
  },
): void {
  const activeId = layoutStore.activeLayoutId
  if (result.trees_by_layout && activeId && result.trees_by_layout[activeId]) {
    const rawEntry = result.trees_by_layout[activeId] as unknown
    const docTree: DocumentTree =
      rawEntry && typeof rawEntry === 'object' && 'root' in (rawEntry as object)
        ? (rawEntry as DocumentTree)
        : { root: rawEntry as TreeNode }
    templateStore.loadTree(docTree)
  } else if (result.document_structure?.root) {
    templateStore.loadTree(result.document_structure as DocumentTree)
  }

  if (result.document_type) templateStore.setDocumentType(result.document_type)

  // Story 14.14 — Propagate is_table_cell flag
  if (result.field_mappings && templateStore.documentTree?.root) {
    const tableCellBlockIds = buildTableCellBlockIds(
      result.field_mappings as Array<{ block_id?: string; is_table_cell?: boolean }>,
    )
    if (tableCellBlockIds.size > 0) {
      applyTableCellFlags(templateStore.documentTree.root, tableCellBlockIds)
    }
  }
}

export function loadMappingStoreData(
  result: PipelineResult,
  mappingStore: {
    loadPipelineFields: (
      fields: FieldMappingEntry[],
      ambiguous?: Array<{ xsd_path: string; candidates: string[] }>,
    ) => void
    setFlatPaths: (paths: string[]) => void
    setUnmappedXsdFields: (
      fields: Array<{ xsd_path: string; required: boolean; reason?: string }>,
    ) => void
  },
): void {
  if (result.field_mappings) {
    mappingStore.loadPipelineFields(
      result.field_mappings as FieldMappingEntry[],
      result.ambiguous_fields ?? [],
    )
  }

  const fieldTree = (result as Record<string, unknown>)['field_tree'] as
    | { flat_paths?: string[] }
    | undefined
  if (fieldTree?.flat_paths?.length) {
    mappingStore.setFlatPaths(fieldTree.flat_paths)
  }

  // Story 28.2 — unmapped XSD fields
  if (result.validation_result?.unmapped_xsd_fields?.length) {
    const rawXsdFields = result.validation_result.unmapped_xsd_fields as unknown[]
    const normalized = rawXsdFields.map((f) =>
      typeof f === 'string'
        ? { xsd_path: f, required: false }
        : (f as { xsd_path: string; required: boolean; reason?: string }),
    )
    mappingStore.setUnmappedXsdFields(normalized)
  }
}

export function loadConfidenceStoreData(
  result: PipelineResult,
  confidenceStore: { loadConfidence: (data: Record<string, ConfidenceFactors>) => void },
): void {
  if (result.confidence_scores) {
    confidenceStore.loadConfidence(result.confidence_scores as Record<string, ConfidenceFactors>)
  }
}

export function loadCoverageStoreData(
  result: PipelineResult,
  coverageStore: {
    loadCoverage: (data: Record<string, CoverageData>) => void
    loadOverlayItems: (items: unknown) => void
    loadAnchors: (anchors: unknown) => void
  },
): void {
  if (result.coverage) {
    coverageStore.loadCoverage(result.coverage as Record<string, CoverageData>)
  }
  if (result.overlay_items) coverageStore.loadOverlayItems(result.overlay_items)
  if (result.anchors) coverageStore.loadAnchors(result.anchors)
}

export function loadGenerationStoreData(
  result: PipelineResult,
  generationStore: { loadTemplateDraft: (draft: unknown) => void },
): void {
  if (result.template_draft) generationStore.loadTemplateDraft(result.template_draft)
}

export function loadInspectorStoreData(
  result: PipelineResult,
  inspectorStore: { initFromTree: (root: TreeNode) => void },
): void {
  if (result.document_structure?.root) {
    inspectorStore.initFromTree(result.document_structure.root)
  }
}

export function loadMultiDocStoreData(
  result: PipelineResult,
  multiDocStore: { populateFromPipeline: (data: unknown) => void },
): void {
  if (result.multi_doc) {
    multiDocStore.populateFromPipeline(result.multi_doc)
  }
}

export async function loadTestDataStoreData(
  result: PipelineResult,
  dataFile: DataFile | null,
  testDataStore: { addDataset: (dataset: unknown) => void },
): Promise<void> {
  const exampleData = (result as Record<string, unknown>)['example_data'] as
    | Record<string, unknown>
    | undefined
  const dataFileContent = dataFile ? await parseDataFile(dataFile) : null

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
}
