/**
 * Keyboard shortcuts for canvas element manipulation (Story 14.7)
 *
 * Arrow: move 1px | Shift+Arrow: move gridSize | Alt+Arrow: resize 1px
 * Ctrl+D: duplicate | Delete: remove
 */
import { useEditorStore } from '@/stores/editorStore'
import { useTemplateStore } from '@/stores/templateStore'
import { useClipboard } from '@/composables/useClipboard'

// Debounce undo snapshots for rapid consecutive moves
let undoTimer: ReturnType<typeof setTimeout> | null = null
let undoPending = false

function debouncedUndo(templateStore: ReturnType<typeof useTemplateStore>) {
  if (!undoPending) {
    templateStore.pushUndoSnapshot()
    undoPending = true
  }
  if (undoTimer) clearTimeout(undoTimer)
  undoTimer = setTimeout(() => {
    undoPending = false
  }, 300)
}

export function useCanvasKeyboard() {
  const editorStore = useEditorStore()
  const templateStore = useTemplateStore()
  const { copySelection, pasteFromClipboard } = useClipboard()

  function handleKeyDown(e: KeyboardEvent) {
    // Don't intercept when focus is in input/textarea/contenteditable
    const tag = (e.target as HTMLElement)?.tagName?.toLowerCase()
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return
    if ((e.target as HTMLElement)?.isContentEditable) return

    // Ctrl+C: copy (works even without selection for multi-select)
    if (e.key === 'c' && (e.ctrlKey || e.metaKey) && !e.shiftKey) {
      if (editorStore.selectedElementId) {
        e.preventDefault()
        copySelection()
      }
      return
    }

    // Ctrl+V: paste
    if (e.key === 'v' && (e.ctrlKey || e.metaKey) && !e.shiftKey) {
      e.preventDefault()
      pasteFromClipboard()
      return
    }

    const id = editorStore.selectedElementId
    if (!id) return

    const node = templateStore.getNodeById(id)
    if (!node) return

    const gridSize = editorStore.gridSize || 10

    // Arrow keys: move or resize
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
      e.preventDefault()

      if (e.altKey) {
        // Alt+Arrow: resize
        debouncedUndo(templateStore)
        const w = (node.properties.width as number) ?? 100
        const h = (node.properties.height as number) ?? 100
        let nw = w
        let nh = h
        switch (e.key) {
          case 'ArrowRight': nw = w + 1; break
          case 'ArrowLeft': nw = Math.max(1, w - 1); break
          case 'ArrowDown': nh = h + 1; break
          case 'ArrowUp': nh = Math.max(1, h - 1); break
        }
        templateStore.resizeElement(id, nw, nh)
      } else {
        // Move: 1px or gridSize with Shift
        const step = e.shiftKey ? gridSize : 1
        debouncedUndo(templateStore)
        let dx = 0
        let dy = 0
        switch (e.key) {
          case 'ArrowLeft': dx = -step; break
          case 'ArrowRight': dx = step; break
          case 'ArrowUp': dy = -step; break
          case 'ArrowDown': dy = step; break
        }
        templateStore.moveElement(id, dx, dy)
      }
      return
    }

    // Ctrl+D: duplicate
    if (e.key === 'd' && (e.ctrlKey || e.metaKey) && !e.shiftKey) {
      e.preventDefault()
      const clone = templateStore.duplicateNode(id)
      if (clone) {
        // Offset +10px
        templateStore.moveElement(clone.id, 10, 10)
        editorStore.selectElement(clone.id)
      }
      return
    }

    // Delete/Backspace: remove element (Story 30.7 — Backspace no longer requires metaKey)
    // Input fields already guarded at the top of handleKeyDown
    if (e.key === 'Delete' || e.key === 'Backspace') {
      e.preventDefault()
      templateStore.removeNode(id)
      editorStore.selectElement(null)
      return
    }
  }

  return {
    handleKeyDown,
  }
}
