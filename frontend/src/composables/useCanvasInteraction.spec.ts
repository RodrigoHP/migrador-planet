import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCanvasInteraction } from './useCanvasInteraction'
import type { BoundingBox } from './useCanvasInteraction'
import { useEditorStore } from '@/stores/editorStore'
import { useInspectorStore } from '@/stores/inspectorStore'
import { useTemplateStore } from '@/stores/templateStore'
import type { DocumentTree, TreeNode } from '@/types/template.types'

// ─── Mock idb (used by layoutStore if imported transitively) ────────────────
vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      get: vi.fn(() => Promise.resolve(undefined)),
      put: vi.fn(() => Promise.resolve()),
    }),
  ),
}))

function makeTree(): DocumentTree {
  const textNode: TreeNode = {
    id: 'text-1',
    type: 'text',
    name: 'Text',
    children: [],
    properties: { x: 10, y: 20, width: 100, height: 50 },
    visibility: true,
  }
  const cellNode: TreeNode = {
    id: 'cell-1',
    type: 'container',
    name: 'Cell',
    children: [textNode],
    properties: { x: 0, y: 0, width: 200, height: 100 },
    visibility: true,
  }
  const root: TreeNode = {
    id: 'doc-1',
    type: 'document',
    name: 'Document',
    children: [cellNode],
    properties: {},
    visibility: true,
  }
  return { root }
}

const BOX_A: BoundingBox = { x: 10, y: 20, width: 100, height: 50 }
const BOX_B: BoundingBox = { x: 200, y: 100, width: 80, height: 40 }

describe('useCanvasInteraction', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    // Reset module-level singleton state between tests
    const { resetState } = useCanvasInteraction()
    resetState()
  })

  // ─── selectElement ──────────────────────────────────────────────────────────
  describe('selectElement', () => {
    it('sets selectionState with elementId and boundingBox', () => {
      const { selectionState, selectElement } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      expect(selectionState.value.elementId).toBe('elem-1')
      expect(selectionState.value.boundingBox).toEqual(BOX_A)
    })

    it('generates 8 handles', () => {
      const { selectionState, selectElement } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      expect(selectionState.value.handles).toHaveLength(8)
    })

    it('handles have correct indices 0-7', () => {
      const { selectionState, selectElement } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      const indices = selectionState.value.handles.map((h) => h.index)
      expect(indices).toEqual([0, 1, 2, 3, 4, 5, 6, 7])
    })

    it('updates editorStore.selectedElementId', () => {
      const editorStore = useEditorStore()
      const { selectElement } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      expect(editorStore.selectedElementId).toBe('elem-1')
    })

    it('updates inspectorStore when node exists in templateStore', () => {
      const templateStore = useTemplateStore()
      const inspectorStore = useInspectorStore()
      templateStore.loadTree(makeTree())

      const { selectElement } = useCanvasInteraction()
      selectElement('text-1', BOX_A)

      expect(inspectorStore.selectedNode?.id).toBe('text-1')
    })

    it('normal click creates single selection and adds to multiSelection set', () => {
      const { selectElement, multiSelection } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      expect(multiSelection.value.has('elem-1')).toBe(true)
      expect(multiSelection.value.size).toBe(1)
    })

    it('Ctrl+Click adds element to multi-selection without replacing', () => {
      const { selectElement, multiSelection } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      selectElement('elem-2', BOX_B, { ctrl: true })
      expect(multiSelection.value.has('elem-1')).toBe(true)
      expect(multiSelection.value.has('elem-2')).toBe(true)
    })

    it('Ctrl+Click on already-selected element removes it', () => {
      const { selectElement, multiSelection } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      selectElement('elem-2', BOX_B, { ctrl: true })
      selectElement('elem-1', BOX_A, { ctrl: true })
      expect(multiSelection.value.has('elem-1')).toBe(false)
    })

    it('Shift+Click adds both current and new element to multi-selection', () => {
      const { selectElement, multiSelection, selectionState } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      // Force elementId in selection state before Shift+Click
      expect(selectionState.value.elementId).toBe('elem-1')
      selectElement('elem-2', BOX_B, { shift: true })
      expect(multiSelection.value.has('elem-1')).toBe(true)
      expect(multiSelection.value.has('elem-2')).toBe(true)
    })
  })

  // ─── clearSelection ─────────────────────────────────────────────────────────
  describe('clearSelection', () => {
    it('resets selectionState', () => {
      const { selectElement, clearSelection, selectionState } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      clearSelection()
      expect(selectionState.value.elementId).toBeNull()
      expect(selectionState.value.boundingBox).toBeNull()
      expect(selectionState.value.handles).toHaveLength(0)
    })

    it('clears multiSelection', () => {
      const { selectElement, clearSelection, multiSelection } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      selectElement('elem-2', BOX_B, { ctrl: true })
      clearSelection()
      expect(multiSelection.value.size).toBe(0)
    })

    it('clears editorStore.selectedElementId', () => {
      const editorStore = useEditorStore()
      const { selectElement, clearSelection } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      clearSelection()
      expect(editorStore.selectedElementId).toBeNull()
    })
  })

  // ─── Drag ───────────────────────────────────────────────────────────────────
  describe('drag (startDrag / updateDrag / endDrag)', () => {
    beforeEach(() => {
      const editorStore = useEditorStore()
      editorStore.snapEnabled = false
    })

    it('startDrag sets isDragging = true', () => {
      const { selectElement, startDrag, dragState } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      startDrag(50, 50)
      expect(dragState.value.isDragging).toBe(true)
    })

    it('startDrag without selection does nothing', () => {
      const { startDrag, dragState } = useCanvasInteraction()
      startDrag(50, 50)
      expect(dragState.value.isDragging).toBe(false)
    })

    it('updateDrag moves selection box by delta', () => {
      const { selectElement, startDrag, updateDrag, selectionState } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      startDrag(0, 0)
      updateDrag(30, 20)
      expect(selectionState.value.boundingBox!.x).toBe(BOX_A.x + 30)
      expect(selectionState.value.boundingBox!.y).toBe(BOX_A.y + 20)
    })

    it('endDrag commits position to templateStore via moveElement', () => {
      const templateStore = useTemplateStore()
      templateStore.loadTree(makeTree())
      const { selectElement, startDrag, updateDrag, endDrag } = useCanvasInteraction()
      selectElement('text-1', BOX_A)
      startDrag(0, 0)
      updateDrag(15, 10)
      endDrag()
      const node = templateStore.getNodeById('text-1')!
      // x started at 10, moved by ~15 (without snap)
      expect(node.properties.x).toBe(10 + 15) // 25
      expect(node.properties.y).toBe(20 + 10) // 30
    })

    it('endDrag resets isDragging to false', () => {
      const { selectElement, startDrag, updateDrag, endDrag, dragState } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      startDrag(0, 0)
      updateDrag(10, 10)
      endDrag()
      expect(dragState.value.isDragging).toBe(false)
    })

    it('endDrag without drag does nothing', () => {
      const { endDrag, dragState } = useCanvasInteraction()
      endDrag()
      expect(dragState.value.isDragging).toBe(false)
    })
  })

  // ─── Resize ─────────────────────────────────────────────────────────────────
  describe('resize (startResize / updateResize / endResize)', () => {
    beforeEach(() => {
      const editorStore = useEditorStore()
      editorStore.snapEnabled = false
    })

    it('startResize sets isResizing = true', () => {
      const { selectElement, startResize, resizeState } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      startResize(7, 100, 200) // handle BR
      expect(resizeState.value.isResizing).toBe(true)
      expect(resizeState.value.handleIndex).toBe(7)
    })

    it('updateResize BR handle increases width and height', () => {
      const { selectElement, startResize, updateResize, selectionState } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      startResize(7, 0, 0) // BR: drag right/down increases both
      updateResize(20, 15)
      expect(selectionState.value.boundingBox!.width).toBe(BOX_A.width + 20)
      expect(selectionState.value.boundingBox!.height).toBe(BOX_A.height + 15)
    })

    it('updateResize TL handle moves origin and decreases size', () => {
      const { selectElement, startResize, updateResize, selectionState } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      startResize(0, 0, 0) // TL: drag right/down decreases size
      updateResize(10, 5)
      expect(selectionState.value.boundingBox!.x).toBe(BOX_A.x + 10)
      expect(selectionState.value.boundingBox!.width).toBe(BOX_A.width - 10)
    })

    it('endResize commits dimensions to templateStore via resizeElement', () => {
      const templateStore = useTemplateStore()
      templateStore.loadTree(makeTree())
      const { selectElement, startResize, updateResize, endResize } = useCanvasInteraction()
      selectElement('text-1', BOX_A)
      startResize(7, 0, 0) // BR handle
      updateResize(20, 10)
      endResize()
      const node = templateStore.getNodeById('text-1')!
      expect(node.properties.width).toBe(BOX_A.width + 20)
      expect(node.properties.height).toBe(BOX_A.height + 10)
    })

    it('endResize resets isResizing to false', () => {
      const { selectElement, startResize, endResize, resizeState } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      startResize(7, 0, 0)
      endResize()
      expect(resizeState.value.isResizing).toBe(false)
    })

    it('enforces minimum size of 10px', () => {
      const { selectElement, startResize, updateResize, selectionState } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      startResize(7, 0, 0) // BR
      updateResize(-200, -200) // drag far left/up
      expect(selectionState.value.boundingBox!.width).toBeGreaterThanOrEqual(10)
      expect(selectionState.value.boundingBox!.height).toBeGreaterThanOrEqual(10)
    })

    it('updateResize populates resizeState.snapLines when snap enabled', () => {
      const editorStore = useEditorStore()
      editorStore.snapEnabled = true
      const { selectElement, startResize, updateResize, resizeState } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      startResize(7, 0, 0) // BR
      updateResize(20, 15)
      // snapLines is always an array (may be empty if no other elements)
      expect(Array.isArray(resizeState.value.snapLines)).toBe(true)
    })

    it('activeSnapLines returns lines during resize', () => {
      const editorStore = useEditorStore()
      editorStore.snapEnabled = true
      const { selectElement, startResize, updateResize, activeSnapLines } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      startResize(7, 0, 0)
      updateResize(20, 15)
      // activeSnapLines should return resizeState.snapLines during resize
      expect(Array.isArray(activeSnapLines.value)).toBe(true)
    })
  })

  // ─── Snap ───────────────────────────────────────────────────────────────────
  describe('snap', () => {
    it('snapEnabled mirrors editorStore.snapEnabled', () => {
      const editorStore = useEditorStore()
      const { snapEnabled } = useCanvasInteraction()
      expect(snapEnabled.value).toBe(true)
      editorStore.toggleSnap()
      expect(snapEnabled.value).toBe(false)
    })

    it('calcSnapLines returns no lines when snapEnabled = false', () => {
      const editorStore = useEditorStore()
      editorStore.snapEnabled = false
      const { calcSnapLines } = useCanvasInteraction()
      const result = calcSnapLines(BOX_A)
      expect(result.lines).toHaveLength(0)
    })

    it('snapToGrid rounds to nearest GRID_SIZE', () => {
      const { snapToGrid, GRID_SIZE } = useCanvasInteraction()
      expect(snapToGrid(5)).toBe(8) // nearest multiple of 8
      expect(snapToGrid(4)).toBe(0)
      expect(snapToGrid(12)).toBe(8)
      expect(snapToGrid(GRID_SIZE)).toBe(GRID_SIZE)
    })

    it('calcSnapLines produces snap line when element edge aligns with neighbor', () => {
      const editorStore = useEditorStore()
      editorStore.snapEnabled = true
      const { registerElementBox, calcSnapLines } = useCanvasInteraction()

      // Register neighbor element
      const neighbor: BoundingBox = { x: 110, y: 50, width: 80, height: 60 }
      registerElementBox('neighbor-1', neighbor)

      // Moving element whose right edge is close to neighbor's left (110)
      const moving: BoundingBox = { x: 6, y: 50, width: 100, height: 50 } // right = 106, close to 110
      const result = calcSnapLines(moving)

      // Should detect snap for the right/left edge alignment
      // The snap threshold is 8px, and 110-106=4 which is within threshold
      expect(result.lines.length).toBeGreaterThan(0)
    })
  })

  // ─── Multi-selection ────────────────────────────────────────────────────────
  describe('multi-selection', () => {
    it('isMultiSelecting is false with single selection', () => {
      const { selectElement, isMultiSelecting } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      expect(isMultiSelecting.value).toBe(false)
    })

    it('isMultiSelecting is true with more than one element', () => {
      const { selectElement, isMultiSelecting } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      selectElement('elem-2', BOX_B, { ctrl: true })
      expect(isMultiSelecting.value).toBe(true)
    })
  })

  // ─── registerElementBox ─────────────────────────────────────────────────────
  describe('registerElementBox', () => {
    it('stores bounding box for element', () => {
      const { registerElementBox, elementBoxes } = useCanvasInteraction()
      registerElementBox('elem-1', BOX_A)
      expect(elementBoxes.value.get('elem-1')).toEqual(BOX_A)
    })
  })

  // ─── updateSelectionBox ─────────────────────────────────────────────────────
  describe('updateSelectionBox', () => {
    it('updates boundingBox and handles when element is selected', () => {
      const { selectElement, updateSelectionBox, selectionState } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      const newBox: BoundingBox = { x: 50, y: 60, width: 120, height: 70 }
      updateSelectionBox('elem-1', newBox)
      expect(selectionState.value.boundingBox).toEqual(newBox)
    })

    it('does not update when element is not the current selection', () => {
      const { selectElement, updateSelectionBox, selectionState } = useCanvasInteraction()
      selectElement('elem-1', BOX_A)
      const newBox: BoundingBox = { x: 50, y: 60, width: 120, height: 70 }
      updateSelectionBox('elem-other', newBox)
      expect(selectionState.value.boundingBox).toEqual(BOX_A)
    })
  })

  // ─── selectFromTree ─────────────────────────────────────────────────────────
  describe('selectFromTree', () => {
    it('sets elementId even without bounding box', () => {
      const { selectFromTree, selectionState } = useCanvasInteraction()
      selectFromTree('elem-1')
      expect(selectionState.value.elementId).toBe('elem-1')
      expect(selectionState.value.boundingBox).toBeNull()
    })

    it('uses stored bounding box if available', () => {
      const { registerElementBox, selectFromTree, selectionState } = useCanvasInteraction()
      registerElementBox('elem-1', BOX_A)
      selectFromTree('elem-1')
      expect(selectionState.value.boundingBox).toEqual(BOX_A)
    })
  })

  // ─── Hierarchy Popup ────────────────────────────────────────────────────────
  describe('hierarchy popup', () => {
    it('showHierarchyPopup shows popup with ancestors', () => {
      const templateStore = useTemplateStore()
      templateStore.loadTree(makeTree())
      const { showHierarchyPopup, hierarchyPopup } = useCanvasInteraction()

      showHierarchyPopup('text-1', 100, 200)

      expect(hierarchyPopup.value.visible).toBe(true)
      expect(hierarchyPopup.value.x).toBe(100)
      expect(hierarchyPopup.value.y).toBe(200)
      expect(hierarchyPopup.value.ancestorIds).toContain('text-1')
    })

    it('hideHierarchyPopup hides popup', () => {
      const templateStore = useTemplateStore()
      templateStore.loadTree(makeTree())
      const { showHierarchyPopup, hideHierarchyPopup, hierarchyPopup } = useCanvasInteraction()
      showHierarchyPopup('text-1', 0, 0)
      hideHierarchyPopup()
      expect(hierarchyPopup.value.visible).toBe(false)
    })

    it('selectFromHierarchy selects element and hides popup', () => {
      const templateStore = useTemplateStore()
      templateStore.loadTree(makeTree())
      const { registerElementBox, showHierarchyPopup, selectFromHierarchy, hierarchyPopup, selectionState } = useCanvasInteraction()

      registerElementBox('cell-1', BOX_B)
      showHierarchyPopup('text-1', 0, 0)
      selectFromHierarchy('cell-1')

      expect(selectionState.value.elementId).toBe('cell-1')
      expect(hierarchyPopup.value.visible).toBe(false)
    })
  })

  // ─── Undo integration (Story 7.2 crossref) ──────────────────────────────────
  describe('undo stack integration', () => {
    it('endDrag pushes to undo stack via moveElement', () => {
      const templateStore = useTemplateStore()
      templateStore.loadTree(makeTree())
      const initialUndoLength = templateStore.undoStack.length

      const { selectElement, startDrag, updateDrag, endDrag } = useCanvasInteraction()
      selectElement('text-1', BOX_A)
      startDrag(0, 0)
      updateDrag(10, 5)
      endDrag()

      // moveElement calls pushUndoSnapshot
      expect(templateStore.undoStack.length).toBeGreaterThan(initialUndoLength)
    })

    it('endResize pushes to undo stack via resizeElement', () => {
      const templateStore = useTemplateStore()
      templateStore.loadTree(makeTree())
      const initialUndoLength = templateStore.undoStack.length

      const { selectElement, startResize, updateResize, endResize } = useCanvasInteraction()
      selectElement('text-1', BOX_A)
      startResize(7, 0, 0)
      updateResize(10, 10)
      endResize()

      expect(templateStore.undoStack.length).toBeGreaterThan(initialUndoLength)
    })
  })
})
