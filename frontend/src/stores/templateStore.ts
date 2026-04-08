import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { DocumentTree, TreeNode, NodeType, NodeProperties, CellProperties } from '@/types/template.types'
import { getCellKey } from '@/types/template.types'
// ARQUITETURA: templateStore → generationStore (dependência unidirecional).
// generation.ts NÃO deve importar templateStore — evitaria circular de módulo.
import { useGenerationStore } from './generation'

// ─── Undo stack max size ──────────────────────────────────────────────────────
const UNDO_MAX = 20

// ─── ID generator ─────────────────────────────────────────────────────────────
let _idCounter = 1
export function generateNodeId(): string {
  return `node-${Date.now()}-${_idCounter++}`
}

// ─── Deep clone helper ────────────────────────────────────────────────────────
export function deepCloneNode(node: TreeNode): TreeNode {
  return {
    ...node,
    id: generateNodeId(),
    children: node.children.map((c) => deepCloneNode(c)),
    properties: { ...node.properties },
  }
}

// ─── Default properties by type ───────────────────────────────────────────────
function defaultPropertiesForType(_type: NodeType): NodeProperties {
  return {}
}

export const useTemplateStore = defineStore('template', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const documentTree = ref<DocumentTree | null>(null)
  const flatNodes = ref<Map<string, TreeNode>>(new Map())
  const documentType = ref<string | null>(null)

  /**
   * Monotonically increasing counter — bumped after canvas-relevant mutations:
   * moveElement, resizeElement, updateNodeProperty.
   * ADR-029: Opção C — usado por consumers que precisam reagir a mutações visuais.
   *
   * Cobertura completa (Story 29.7): mutações estruturais (addNode, removeNode,
   * moveNode) também incrementam este contador. Para observar mutações,
   * use watch(documentTree, { deep: true }).
   */
  const mutationVersion = ref(0)
  /** Incremented only when binding-related properties change (binding, xsd_path). */
  const bindingVersion = ref(0)

  // ─── Undo Stack ───────────────────────────────────────────────────────────
  const undoStack = ref<string[]>([]) // JSON snapshots of documentTree

  // ─── Helpers ─────────────────────────────────────────────────────────────
  function buildFlatMap(node: TreeNode, map: Map<string, TreeNode>) {
    map.set(node.id, node)
    for (const child of (node.children ?? [])) {
      buildFlatMap(child, map)
    }
  }

  function rebuildFlatMap() {
    if (!documentTree.value) return
    const map = new Map<string, TreeNode>()
    buildFlatMap(documentTree.value.root, map)
    flatNodes.value = map
  }

  /** Find the parent node of a given node id */
  function findParent(nodeId: string, current: TreeNode): TreeNode | null {
    for (const child of current.children) {
      if (child.id === nodeId) return current
      const found = findParent(nodeId, child)
      if (found) return found
    }
    return null
  }

  // ─── Getters ─────────────────────────────────────────────────────────────
  const getRootNode = computed<TreeNode | null>(() => {
    return documentTree.value?.root ?? null
  })

  function getNodeById(id: string): TreeNode | undefined {
    return flatNodes.value.get(id)
  }

  function getNodesByType(type: NodeType): TreeNode[] {
    const result: TreeNode[] = []
    for (const node of flatNodes.value.values()) {
      if (node.type === type) result.push(node)
    }
    return result
  }

  function getChildren(parentId: string): TreeNode[] {
    const parent = flatNodes.value.get(parentId)
    return parent?.children ?? []
  }

  // ─── Actions ─────────────────────────────────────────────────────────────

  /**
   * Walk tree and auto-set visibility.mode = 'conditional' for optional nodes
   * that have not yet been assigned an explicit VisibilityConfig object.
   */
  function applyOptionalVisibility(node: TreeNode) {
    if (node.isOptional) {
      const current = node.properties['visibility']
      const hasConfig =
        current !== null &&
        typeof current === 'object' &&
        'mode' in (current as Record<string, unknown>)
      if (!hasConfig) {
        node.properties = {
          ...node.properties,
          visibility: { mode: 'conditional', conditions: [] },
        }
      }
    }
    for (const child of (node.children ?? [])) {
      applyOptionalVisibility(child)
    }
  }

  function loadTree(tree: DocumentTree) {
    if (!tree?.root) return
    documentTree.value = tree
    const map = new Map<string, TreeNode>()
    buildFlatMap(tree.root, map)
    flatNodes.value = map
    undoStack.value = []
    // AC #8 — auto-configure optional nodes as Conditional
    applyOptionalVisibility(tree.root)
  }

  /**
   * Bulk update multiple properties on a node.
   * Story 33.3: calls patch for each property and increments mutationVersion.
   */
  function updateNodeProperties(id: string, props: Partial<NodeProperties>) {
    const node = flatNodes.value.get(id)
    if (!node) return
    pushUndoSnapshot()
    node.properties = { ...node.properties, ...props }

    // Dispatch patches for known property types
    const gen = useGenerationStore()
    const geometryKeys = ['x', 'y', 'width', 'height']
    const hasGeometry = geometryKeys.some((k) => k in props)
    if (hasGeometry) {
      gen.patchNodeGeometry(
        id,
        (node.properties.x as number) ?? 0,
        (node.properties.y as number) ?? 0,
        (node.properties.width as number) ?? 0,
        (node.properties.height as number) ?? 0,
      )
    }
    if ('text' in props && typeof props.text === 'string') {
      gen.patchNodeText(id, props.text)
    }
    if ('visibility' in props) {
      const vis = props.visibility
      if (vis && typeof vis === 'object' && 'mode' in (vis as Record<string, unknown>)) {
        const mode = (vis as { mode: string }).mode
        gen.patchNodeVisibility(id, mode !== 'hidden')
      } else if (typeof vis === 'boolean') {
        gen.patchNodeVisibility(id, vis)
      }
    }
    // Style properties
    const styleKeys = ['font_size', 'font_weight', 'font_style', 'color', 'background_color']
    for (const sk of styleKeys) {
      if (sk in props) {
        gen.patchNodeStyle(id, sk, String(props[sk as keyof NodeProperties] ?? ''))
      }
    }

    mutationVersion.value++
  }

  /**
   * Update a single property path on a node (dot-notation supported for nested).
   * Pushes undo snapshot before mutation.
   */
  function updateNodeProperty(nodeId: string, path: string, value: unknown) {
    const node = flatNodes.value.get(nodeId)
    if (!node) return
    pushUndoSnapshot()
    const keys = path.split('.')
    if (keys.length === 1) {
      node.properties = { ...node.properties, [path]: value }
    } else {
      const top = keys[0]!
      let nested = { ...((node.properties[top] as Record<string, unknown>) ?? {}) }
      let cur: Record<string, unknown> = nested
      for (let i = 1; i < keys.length - 1; i++) {
        const k = keys[i]!
        cur[k] = { ...((cur[k] as Record<string, unknown>) ?? {}) }
        cur = cur[k] as Record<string, unknown>
      }
      cur[keys[keys.length - 1]!] = value
      node.properties = { ...node.properties, [top]: nested }
    }
    mutationVersion.value++
    const BINDING_PATHS = ['binding', 'xsd_path', 'suggested_binding']
    if (BINDING_PATHS.includes(path)) bindingVersion.value++
    if (path === 'text' && typeof value === 'string') {
      useGenerationStore().patchNodeText(nodeId, value)
    }
    // Story 33.4: patch style properties in real-time
    const styleProps = ['font_size', 'font_weight', 'font_style', 'color', 'background_color']
    if (styleProps.includes(path) && (typeof value === 'string' || typeof value === 'number')) {
      useGenerationStore().patchNodeStyle(nodeId, path, String(value))
    }
    // Story 33.5: detect VisibilityConfig object via value.mode, not typeof === 'boolean'
    if (path === 'visibility') {
      if (value && typeof value === 'object' && 'mode' in (value as Record<string, unknown>)) {
        const mode = (value as { mode: string }).mode
        useGenerationStore().patchNodeVisibility(nodeId, mode !== 'hidden')
      } else if (typeof value === 'boolean') {
        useGenerationStore().patchNodeVisibility(nodeId, value)
      }
    }
  }

  /**
   * Update a property directly on the root (page/document) node.
   * Pushes undo snapshot before mutation.
   */
  function updatePageProperty(key: string, value: unknown) {
    if (!documentTree.value) return
    pushUndoSnapshot()
    const root = documentTree.value.root
    root.properties = { ...root.properties, [key]: value }
  }

  // ─── Undo Stack ───────────────────────────────────────────────────────────
  function pushUndoSnapshot() {
    if (!documentTree.value) return
    const snapshot = JSON.stringify(documentTree.value)
    undoStack.value.push(snapshot)
    if (undoStack.value.length > UNDO_MAX) {
      undoStack.value.shift()
    }
  }

  function undoLastAction() {
    if (undoStack.value.length === 0) return
    const snapshot = undoStack.value.pop()!
    documentTree.value = JSON.parse(snapshot) as DocumentTree
    rebuildFlatMap()
  }

  // ─── moveNode ─────────────────────────────────────────────────────────────
  /**
   * Move a node to a new parent at a given index.
   * @param nodeId - ID of node to move
   * @param targetParentId - ID of the new parent
   * @param targetIndex - position within new parent's children (default: append)
   */
  function moveNode(nodeId: string, targetParentId: string, targetIndex?: number) {
    if (!documentTree.value) return
    const root = documentTree.value.root

    // Prevent moving to self or into own subtree
    if (nodeId === targetParentId) return

    const sourceParent = findParent(nodeId, root)
    if (!sourceParent) return

    const targetParent = flatNodes.value.get(targetParentId)
    if (!targetParent) return

    // Prevent moving into own child
    const isDescendant = (ancestor: TreeNode, id: string): boolean => {
      for (const c of ancestor.children) {
        if (c.id === id) return true
        if (isDescendant(c, id)) return true
      }
      return false
    }
    const movingNode = flatNodes.value.get(nodeId)
    if (!movingNode) return
    if (isDescendant(movingNode, targetParentId)) return

    pushUndoSnapshot()

    // Remove from source
    const srcIdx = sourceParent.children.findIndex((c) => c.id === nodeId)
    sourceParent.children.splice(srcIdx, 1)

    // Insert into target
    const idx = targetIndex !== undefined ? targetIndex : targetParent.children.length
    targetParent.children.splice(idx, 0, movingNode)

    rebuildFlatMap()
    mutationVersion.value++
    useGenerationStore().patchMoveNode(nodeId, targetParentId)
  }

  // ─── convertToTable ───────────────────────────────────────────────────────
  /**
   * Convert a section/flow/container node to a table node.
   * The node's original children become children of a new 'section' row node.
   * Story 30.2 — "Converter para Tabela" context menu action.
   */
  const CONVERTIBLE_TO_TABLE: NodeType[] = ['section', 'flow', 'container']

  function convertToTable(nodeId: string): boolean {
    if (!documentTree.value) return false

    const node = flatNodes.value.get(nodeId)
    if (!node) return false
    if (!CONVERTIBLE_TO_TABLE.includes(node.type)) return false
    if (node.type === 'table') return false

    pushUndoSnapshot()

    // Wrap original children in a new section (first row)
    const rowNode: TreeNode = {
      id: generateNodeId(),
      type: 'section',
      name: 'Linha 1',
      binding: '',
      isOptional: false,
      children: node.children,
      properties: {},
      visibility: true,
    }

    // Convert node to table with row as sole child
    node.type = 'table'
    node.name = node.name || 'Tabela'
    node.children = [rowNode]

    // Register row in flat map
    flatNodes.value.set(rowNode.id, rowNode)
    for (const child of rowNode.children) {
      buildFlatMap(child, flatNodes.value)
    }

    mutationVersion.value++
    useGenerationStore().patchConvertNodeToTable(nodeId, rowNode)

    return true
  }

  // ─── addNode ──────────────────────────────────────────────────────────────
  /**
   * Add a new node of the given type as a child of parentId.
   */
  function addNode(parentId: string, type: NodeType, index?: number): TreeNode | null {
    if (!documentTree.value) return null

    const parent = flatNodes.value.get(parentId)
    if (!parent) return null

    pushUndoSnapshot()

    const newNode: TreeNode = {
      id: generateNodeId(),
      type,
      name: `Novo ${type}`,
      binding: '',
      isOptional: false,
      children: [],
      properties: defaultPropertiesForType(type),
      visibility: true,
    }

    const idx = index !== undefined ? index : parent.children.length
    parent.children.splice(idx, 0, newNode)
    flatNodes.value.set(newNode.id, newNode)
    mutationVersion.value++
    useGenerationStore().patchAddNode(newNode, parentId)

    return newNode
  }

  // ─── addNodeFromSync ──────────────────────────────────────────────────────
  /**
   * Insert a pre-built TreeNode (with a specific ID) as a child of parentId.
   * Used by codeStore.syncHtmlToTree to preserve the exact data-node-id from the HTML.
   * Does NOT push undo snapshot — sync is a reconciliation, not a user action.
   * Story 30.3 — HTML parser full sync.
   */
  function addNodeFromSync(newNode: TreeNode, parentId: string): boolean {
    if (!documentTree.value) return false
    const parent = flatNodes.value.get(parentId)
    if (!parent) return false

    parent.children.push(newNode)
    buildFlatMap(newNode, flatNodes.value)
    mutationVersion.value++
    useGenerationStore().patchAddNode(newNode, parentId)
    return true
  }

  // ─── duplicateNode ────────────────────────────────────────────────────────
  /**
   * Deep-clone a node and insert it after the original.
   */
  function duplicateNode(nodeId: string): TreeNode | null {
    if (!documentTree.value) return null

    const original = flatNodes.value.get(nodeId)
    if (!original) return null

    const parent = findParent(nodeId, documentTree.value.root)
    if (!parent) return null

    pushUndoSnapshot()

    const clone = deepCloneNode(original)
    const srcIdx = parent.children.findIndex((c) => c.id === nodeId)
    parent.children.splice(srcIdx + 1, 0, clone)

    // Register clone and all descendants in flat map
    buildFlatMap(clone, flatNodes.value)

    return clone
  }

  // ─── removeNode ───────────────────────────────────────────────────────────
  /**
   * Remove a node from the tree.
   * Returns true on success.
   */
  function removeNode(nodeId: string): boolean {
    if (!documentTree.value) return false

    const parent = findParent(nodeId, documentTree.value.root)
    if (!parent) return false

    pushUndoSnapshot()

    const idx = parent.children.findIndex((c) => c.id === nodeId)
    if (idx === -1) return false

    const [removed] = parent.children.splice(idx, 1)
    if (!removed) return false

    // Remove from flat map (including descendants)
    function removeFromMap(node: TreeNode) {
      flatNodes.value.delete(node.id)
      for (const c of node.children) removeFromMap(c)
    }
    removeFromMap(removed)
    mutationVersion.value++
    useGenerationStore().patchRemoveNode(nodeId)

    return true
  }

  // ─── groupNodes ───────────────────────────────────────────────────────────
  /**
   * Wrap the given node IDs into a new section node within targetParentId.
   * All nodeIds must be direct children of targetParentId.
   */
  function groupNodes(nodeIds: string[], targetParentId: string): TreeNode | null {
    if (!documentTree.value) return null
    if (nodeIds.length === 0) return null

    const parent = flatNodes.value.get(targetParentId)
    if (!parent) return null

    // Verify all nodes are children of targetParent
    const childIds = new Set(parent.children.map((c) => c.id))
    if (!nodeIds.every((id) => childIds.has(id))) return null

    pushUndoSnapshot()

    // Collect the nodes in order
    const toGroup = parent.children.filter((c) => nodeIds.includes(c.id))
    const firstIdx = parent.children.findIndex((c) => c.id === toGroup[0]?.id)

    // Remove them from parent
    parent.children = parent.children.filter((c) => !nodeIds.includes(c.id))

    // Create section wrapper
    const section: TreeNode = {
      id: generateNodeId(),
      type: 'section',
      name: 'Nova seção',
      children: toGroup,
      properties: {},
      visibility: true,
    }

    // Insert section at original position
    parent.children.splice(firstIdx, 0, section)

    // Update flat map
    buildFlatMap(section, flatNodes.value)

    return section
  }

  // ─── Canvas visual drag/resize actions ────────────────────────────────────

  /**
   * Move element by delta (dx, dy) — updates x/y properties.
   * Pushes undo snapshot before change for Story 7.2 undo stack integration.
   */
  function moveElement(id: string, dx: number, dy: number) {
    const node = flatNodes.value.get(id)
    if (!node) return
    pushUndoSnapshot()
    const currentX = (node.properties.x as number) ?? 0
    const currentY = (node.properties.y as number) ?? 0
    const newX = currentX + dx
    const newY = currentY + dy
    node.properties = { ...node.properties, x: newX, y: newY }
    mutationVersion.value++
    useGenerationStore().patchNodeGeometry(
      id, newX, newY,
      (node.properties.width as number) ?? 0,
      (node.properties.height as number) ?? 0,
    )
  }

  /**
   * Resize element to new dimensions.
   * Pushes undo snapshot before change for Story 7.2 undo stack integration.
   */
  function resizeElement(id: string, newWidth: number, newHeight: number) {
    const node = flatNodes.value.get(id)
    if (!node) return
    pushUndoSnapshot()
    node.properties = { ...node.properties, width: newWidth, height: newHeight }
    mutationVersion.value++
    useGenerationStore().patchNodeGeometry(
      id,
      (node.properties.x as number) ?? 0,
      (node.properties.y as number) ?? 0,
      newWidth, newHeight,
    )
  }

  // ─── Cell Property Update (Story 14.4) ──────────────────────────────────
  function updateCellProperty(tableNodeId: string, row: number, col: number, cellPatch: Partial<CellProperties>) {
    const node = flatNodes.value.get(tableNodeId)
    if (!node) return
    pushUndoSnapshot()
    const cells = { ...((node.properties.cells as Record<string, CellProperties>) ?? {}) }
    const key = getCellKey(row, col)
    cells[key] = { ...(cells[key] ?? {}), ...cellPatch }
    node.properties = { ...node.properties, cells }
  }

  return {
    documentTree,
    flatNodes,
    undoStack,
    mutationVersion,
    bindingVersion,
    getRootNode,
    getNodeById,
    getNodesByType,
    getChildren,
    loadTree,
    updateNodeProperties,
    updateNodeProperty,
    updatePageProperty,
    pushUndoSnapshot,
    undoLastAction,
    moveNode,
    moveElement,
    resizeElement,
    addNode,
    addNodeFromSync,
    convertToTable,
    duplicateNode,
    removeNode,
    groupNodes,
    // expose helper for tests
    findParent: (id: string) =>
      documentTree.value ? findParent(id, documentTree.value.root) : null,
    updateCellProperty,
    // expose for testing AC #8
    applyOptionalVisibility,
    // document type detection (Story 12.8)
    documentType,
    setDocumentType: (type: string) => { documentType.value = type },
  }
})
