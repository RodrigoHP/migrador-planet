import { ref, computed } from 'vue'
import { useEditorStore } from '@/stores/editorStore'
import { useInspectorStore } from '@/stores/inspectorStore'
import { useTemplateStore } from '@/stores/templateStore'
import { useLayoutStore } from '@/stores/layout'
import { PDF_TO_CSS_SCALE } from '@/types/pipeline.types'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface BoundingBox {
  x: number
  y: number
  width: number
  height: number
}

export interface SelectionHandle {
  index: number // 0-7: TL, TM, TR, ML, MR, BL, BM, BR
  cursor: string
  x: number
  y: number
}

export interface SnapLine {
  orientation: 'horizontal' | 'vertical'
  position: number
  start: number
  end: number
}

export interface SelectionState {
  elementId: string | null
  boundingBox: BoundingBox | null
  handles: SelectionHandle[]
}

export interface DragState {
  isDragging: boolean
  startX: number
  startY: number
  currentX: number
  currentY: number
  originalBox: BoundingBox | null
  snapLines: SnapLine[]
}

export interface ResizeState {
  isResizing: boolean
  handleIndex: number
  startX: number
  startY: number
  originalBox: BoundingBox | null
  snapLines: SnapLine[]
}

// ─── Handle Cursors ───────────────────────────────────────────────────────────

const HANDLE_CURSORS: string[] = [
  'nwse-resize', // 0: TL
  'ns-resize', // 1: TM
  'nesw-resize', // 2: TR
  'ew-resize', // 3: ML
  'ew-resize', // 4: MR
  'nesw-resize', // 5: BL
  'ns-resize', // 6: BM
  'nwse-resize', // 7: BR
]

const GRID_SIZE = 8 // pixels for grid snap
const SNAP_THRESHOLD = 8 // pixels for magnetic snap

// ─── Module-level singletons (shared across all component instances) ──────────
// These refs are defined at module scope so every call to useCanvasInteraction()
// shares the same state. Previously they were inside the function, causing each
// component (HTMLCanvas, CanvasSelectionOverlay, etc.) to get isolated copies —
// elementBoxes registered in the overlay were invisible to selectFromTree in
// HTMLCanvas, breaking tree→canvas highlight completely.

const selectionState = ref<SelectionState>({
  elementId: null,
  boundingBox: null,
  handles: [],
})

const dragState = ref<DragState>({
  isDragging: false,
  startX: 0,
  startY: 0,
  currentX: 0,
  currentY: 0,
  originalBox: null,
  snapLines: [],
})

const resizeState = ref<ResizeState>({
  isResizing: false,
  handleIndex: -1,
  startX: 0,
  startY: 0,
  originalBox: null,
  snapLines: [],
})

const multiSelection = ref<Set<string>>(new Set())

// elementId → BoundingBox for all elements currently rendered
const elementBoxes = ref<Map<string, BoundingBox>>(new Map())

// hierarchy popup
const hierarchyPopup = ref<{
  visible: boolean
  x: number
  y: number
  ancestorIds: string[]
}>({
  visible: false,
  x: 0,
  y: 0,
  ancestorIds: [],
})

// ─── Composable ───────────────────────────────────────────────────────────────

export function useCanvasInteraction() {
  const editorStore = useEditorStore()
  const inspectorStore = useInspectorStore()
  const templateStore = useTemplateStore()
  const layoutStore = useLayoutStore()

  // ─── Active Snap Lines (Story 14.7) ─────────────────────────────────────────
  const activeSnapLines = computed<SnapLine[]>(() => {
    if (!editorStore.snapEnabled) return []
    if (dragState.value.isDragging) return dragState.value.snapLines
    if (resizeState.value.isResizing) return resizeState.value.snapLines
    return []
  })

  // ─── Computed ────────────────────────────────────────────────────────────────
  const snapEnabled = computed(() => editorStore.snapEnabled)
  const currentGridSize = computed(() => editorStore.gridSize ?? GRID_SIZE)

  const hasSelection = computed(() => selectionState.value.elementId !== null)

  const isMultiSelecting = computed(() => multiSelection.value.size > 1)

  // ─── Handle Positions ────────────────────────────────────────────────────────

  function computeHandles(box: BoundingBox): SelectionHandle[] {
    const { x, y, width, height } = box
    const hw = width / 2
    const hh = height / 2
    return [
      { index: 0, cursor: HANDLE_CURSORS[0]!, x: x, y: y }, // TL
      { index: 1, cursor: HANDLE_CURSORS[1]!, x: x + hw, y: y }, // TM
      { index: 2, cursor: HANDLE_CURSORS[2]!, x: x + width, y: y }, // TR
      { index: 3, cursor: HANDLE_CURSORS[3]!, x: x, y: y + hh }, // ML
      { index: 4, cursor: HANDLE_CURSORS[4]!, x: x + width, y: y + hh }, // MR
      { index: 5, cursor: HANDLE_CURSORS[5]!, x: x, y: y + height }, // BL
      { index: 6, cursor: HANDLE_CURSORS[6]!, x: x + hw, y: y + height }, // BM
      { index: 7, cursor: HANDLE_CURSORS[7]!, x: x + width, y: y + height }, // BR
    ]
  }

  // ─── Snap Calculation ────────────────────────────────────────────────────────

  function snapToGrid(value: number): number {
    const gs = currentGridSize.value
    return Math.floor((value + gs / 2 - 1) / gs) * gs
  }

  function calcSnapLines(movingBox: BoundingBox): { dx: number; dy: number; lines: SnapLine[] } {
    if (!snapEnabled.value) return { dx: 0, dy: 0, lines: [] }

    const lines: SnapLine[] = []
    let dx = 0
    let dy = 0

    // Grid snap
    const snappedX = snapToGrid(movingBox.x)
    const snappedY = snapToGrid(movingBox.y)
    const gridDx = snappedX - movingBox.x
    const gridDy = snappedY - movingBox.y

    if (Math.abs(gridDx) < SNAP_THRESHOLD) dx = gridDx
    if (Math.abs(gridDy) < SNAP_THRESHOLD) dy = gridDy

    // Element edge snap
    for (const [id, box] of elementBoxes.value.entries()) {
      if (id === selectionState.value.elementId) continue

      const candidates = [
        { axis: 'v' as const, val: box.x },
        { axis: 'v' as const, val: box.x + box.width },
        { axis: 'h' as const, val: box.y },
        { axis: 'h' as const, val: box.y + box.height },
      ]

      for (const c of candidates) {
        if (c.axis === 'v') {
          const edgeDx = c.val - movingBox.x
          const edgeDx2 = c.val - (movingBox.x + movingBox.width)
          const best = Math.abs(edgeDx) < Math.abs(edgeDx2) ? edgeDx : edgeDx2
          if (Math.abs(best) < SNAP_THRESHOLD && Math.abs(best) < Math.abs(dx)) {
            dx = best
            lines.push({
              orientation: 'vertical',
              position: c.val,
              start: Math.min(movingBox.y, box.y),
              end: Math.max(movingBox.y + movingBox.height, box.y + box.height),
            })
          }
        } else {
          const edgeDy = c.val - movingBox.y
          const edgeDy2 = c.val - (movingBox.y + movingBox.height)
          const best = Math.abs(edgeDy) < Math.abs(edgeDy2) ? edgeDy : edgeDy2
          if (Math.abs(best) < SNAP_THRESHOLD && Math.abs(best) < Math.abs(dy)) {
            dy = best
            lines.push({
              orientation: 'horizontal',
              position: c.val,
              start: Math.min(movingBox.x, box.x),
              end: Math.max(movingBox.x + movingBox.width, box.x + box.width),
            })
          }
        }
      }
    }

    // Story 39.3 — Column position snap (vertical guides from pipeline grid_info)
    const colPositions = (layoutStore.activeLayout?.gridInfo?.columnPositions ?? []).map((pt) =>
      Math.round(pt * PDF_TO_CSS_SCALE),
    )
    for (const colX of colPositions) {
      const edgeDx = colX - movingBox.x
      const edgeDx2 = colX - (movingBox.x + movingBox.width)
      const best = Math.abs(edgeDx) < Math.abs(edgeDx2) ? edgeDx : edgeDx2
      if (Math.abs(best) < SNAP_THRESHOLD && Math.abs(best) < Math.abs(dx)) {
        dx = best
        lines.push({
          orientation: 'vertical',
          position: colX,
          start: movingBox.y,
          end: movingBox.y + movingBox.height,
        })
      }
    }

    return { dx, dy, lines }
  }

  // ─── Selection ───────────────────────────────────────────────────────────────

  function selectElement(
    elementId: string,
    boundingBox: BoundingBox,
    options?: { ctrl?: boolean; shift?: boolean },
  ) {
    const ctrl = options?.ctrl ?? false
    const shift = options?.shift ?? false

    if (ctrl) {
      // Ctrl+Click: toggle individual from multi-selection
      const next = new Set(multiSelection.value)
      if (next.has(elementId)) {
        next.delete(elementId)
      } else {
        next.add(elementId)
      }
      multiSelection.value = next
    } else if (shift && selectionState.value.elementId) {
      // Shift+Click: add range — simplified: just add to multi
      const next = new Set(multiSelection.value)
      if (selectionState.value.elementId) next.add(selectionState.value.elementId)
      next.add(elementId)
      multiSelection.value = next
    } else {
      // Normal click: single select
      multiSelection.value = new Set([elementId])
    }

    selectionState.value = {
      elementId,
      boundingBox,
      handles: computeHandles(boundingBox),
    }

    // Update stores
    editorStore.selectElement(elementId)

    const node = templateStore.getNodeById(elementId)
    if (node) {
      inspectorStore.selectNode(node)
    }
  }

  function clearSelection() {
    selectionState.value = { elementId: null, boundingBox: null, handles: [] }
    multiSelection.value = new Set()
    editorStore.selectElement(null)
    inspectorStore.clearSelection()
  }

  /** Reset ALL module-level singleton state. Use in tests beforeEach. */
  function resetState() {
    selectionState.value = { elementId: null, boundingBox: null, handles: [] }
    dragState.value = {
      isDragging: false,
      startX: 0,
      startY: 0,
      currentX: 0,
      currentY: 0,
      originalBox: null,
      snapLines: [],
    }
    resizeState.value = {
      isResizing: false,
      handleIndex: -1,
      startX: 0,
      startY: 0,
      originalBox: null,
      snapLines: [],
    }
    multiSelection.value = new Set()
    elementBoxes.value = new Map()
    hierarchyPopup.value = { visible: false, x: 0, y: 0, ancestorIds: [] }
  }

  function updateSelectionBox(elementId: string, boundingBox: BoundingBox) {
    if (selectionState.value.elementId === elementId) {
      selectionState.value = {
        ...selectionState.value,
        boundingBox,
        handles: computeHandles(boundingBox),
      }
    }
    elementBoxes.value.set(elementId, boundingBox)
  }

  function registerElementBox(elementId: string, boundingBox: BoundingBox) {
    elementBoxes.value.set(elementId, boundingBox)
  }

  function clearElementBoxes() {
    elementBoxes.value.clear()
  }

  // ─── Drag ────────────────────────────────────────────────────────────────────

  function startDrag(clientX: number, clientY: number) {
    if (!selectionState.value.elementId || !selectionState.value.boundingBox) return

    dragState.value = {
      isDragging: true,
      startX: clientX,
      startY: clientY,
      currentX: clientX,
      currentY: clientY,
      originalBox: { ...selectionState.value.boundingBox },
      snapLines: [],
    }
  }

  function updateDrag(clientX: number, clientY: number) {
    if (!dragState.value.isDragging || !dragState.value.originalBox) return

    const rawDx = clientX - dragState.value.startX
    const rawDy = clientY - dragState.value.startY

    const tentativeBox: BoundingBox = {
      ...dragState.value.originalBox,
      x: dragState.value.originalBox.x + rawDx,
      y: dragState.value.originalBox.y + rawDy,
    }

    const { dx: snapDx, dy: snapDy, lines } = calcSnapLines(tentativeBox)

    const finalBox: BoundingBox = {
      ...tentativeBox,
      x: tentativeBox.x + snapDx,
      y: tentativeBox.y + snapDy,
    }

    dragState.value = {
      ...dragState.value,
      currentX: clientX,
      currentY: clientY,
      snapLines: lines,
    }

    if (selectionState.value.elementId) {
      selectionState.value = {
        ...selectionState.value,
        boundingBox: finalBox,
        handles: computeHandles(finalBox),
      }
    }
  }

  function endDrag() {
    if (!dragState.value.isDragging || !selectionState.value.elementId) return
    if (!dragState.value.originalBox || !selectionState.value.boundingBox) return

    const dx = selectionState.value.boundingBox.x - dragState.value.originalBox.x
    const dy = selectionState.value.boundingBox.y - dragState.value.originalBox.y

    if (dx !== 0 || dy !== 0) {
      // Apply to all selected elements (multi-selection), using moveElement for undo support
      const ids =
        multiSelection.value.size > 0 ? [...multiSelection.value] : [selectionState.value.elementId]

      for (const id of ids) {
        templateStore.moveElement(id, dx, dy)
      }
    }

    dragState.value = {
      isDragging: false,
      startX: 0,
      startY: 0,
      currentX: 0,
      currentY: 0,
      originalBox: null,
      snapLines: [],
    }
  }

  // ─── Resize ──────────────────────────────────────────────────────────────────

  function startResize(handleIndex: number, clientX: number, clientY: number) {
    if (!selectionState.value.boundingBox) return

    resizeState.value = {
      isResizing: true,
      handleIndex,
      startX: clientX,
      startY: clientY,
      originalBox: { ...selectionState.value.boundingBox },
      snapLines: [],
    }
  }

  function updateResize(clientX: number, clientY: number) {
    if (!resizeState.value.isResizing || !resizeState.value.originalBox) return

    const { handleIndex, startX, startY, originalBox } = resizeState.value
    const dx = clientX - startX
    const dy = clientY - startY

    let { x, y, width, height } = originalBox

    // Handle index mapping:
    // 0:TL, 1:TM, 2:TR, 3:ML, 4:MR, 5:BL, 6:BM, 7:BR
    switch (handleIndex) {
      case 0: // TL
        x += dx
        y += dy
        width -= dx
        height -= dy
        break
      case 1: // TM
        y += dy
        height -= dy
        break
      case 2: // TR
        y += dy
        width += dx
        height -= dy
        break
      case 3: // ML
        x += dx
        width -= dx
        break
      case 4: // MR
        width += dx
        break
      case 5: // BL
        x += dx
        width -= dx
        height += dy
        break
      case 6: // BM
        height += dy
        break
      case 7: // BR
        width += dx
        height += dy
        break
    }

    // Enforce minimum size
    width = Math.max(width, 10)
    height = Math.max(height, 10)

    // Snap edges if enabled and compute visual snap lines
    if (snapEnabled.value) {
      width = snapToGrid(width)
      height = snapToGrid(height)
      x = snapToGrid(x)
      y = snapToGrid(y)
    }

    const newBox: BoundingBox = { x, y, width, height }
    const { lines } = calcSnapLines(newBox)
    resizeState.value = { ...resizeState.value, snapLines: lines }

    selectionState.value = {
      ...selectionState.value,
      boundingBox: newBox,
      handles: computeHandles(newBox),
    }
  }

  function endResize() {
    if (!resizeState.value.isResizing || !selectionState.value.elementId) return
    if (!selectionState.value.boundingBox) return

    const { width, height } = selectionState.value.boundingBox
    templateStore.resizeElement(selectionState.value.elementId, width, height)

    resizeState.value = {
      isResizing: false,
      handleIndex: -1,
      startX: 0,
      startY: 0,
      originalBox: null,
      snapLines: [],
    }
  }

  // ─── Hierarchy Popup ─────────────────────────────────────────────────────────

  function showHierarchyPopup(elementId: string, clientX: number, clientY: number) {
    // Build ancestor chain
    const ancestors: string[] = []
    let currentId: string | undefined = elementId

    while (currentId) {
      ancestors.push(currentId)
      // Walk up the flatNodes to find parent
      let parentId: string | undefined
      for (const [id, node] of templateStore.flatNodes.entries()) {
        if (node.children.some((c) => c.id === currentId)) {
          parentId = id
          break
        }
      }
      currentId = parentId
    }

    hierarchyPopup.value = {
      visible: true,
      x: clientX,
      y: clientY,
      ancestorIds: ancestors,
    }
  }

  function hideHierarchyPopup() {
    hierarchyPopup.value = { ...hierarchyPopup.value, visible: false, ancestorIds: [] }
  }

  function selectFromHierarchy(elementId: string) {
    const box = elementBoxes.value.get(elementId)
    if (box) {
      selectElement(elementId, box)
    }
    hideHierarchyPopup()
  }

  // ─── Tree → Canvas sync ──────────────────────────────────────────────────────

  /**
   * Called when user selects a node from StructureTree.
   * Updates selectionState so the overlay highlights the element in canvas.
   * The actual bounding box will be provided by the overlay once the element
   * is located via postMessage or DOM traversal.
   */
  function selectFromTree(elementId: string) {
    const box = elementBoxes.value.get(elementId) ?? null
    selectionState.value = {
      elementId,
      boundingBox: box,
      handles: box ? computeHandles(box) : [],
    }
    editorStore.selectElement(elementId)
  }

  return {
    // state
    selectionState,
    dragState,
    resizeState,
    multiSelection,
    elementBoxes,
    hierarchyPopup,

    // computed
    snapEnabled,
    hasSelection,
    isMultiSelecting,
    activeSnapLines,

    // selection
    selectElement,
    clearSelection,
    updateSelectionBox,
    registerElementBox,
    clearElementBoxes,
    selectFromTree,

    // drag
    startDrag,
    updateDrag,
    endDrag,

    // resize
    startResize,
    updateResize,
    endResize,

    // snap
    calcSnapLines,
    snapToGrid,
    GRID_SIZE,
    SNAP_THRESHOLD,

    // hierarchy
    showHierarchyPopup,
    hideHierarchyPopup,
    selectFromHierarchy,

    // test utilities
    resetState,
  }
}
