/**
 * Composable for copy/paste/duplicate operations (Story 14.9)
 */
import { ref } from 'vue'
import { useTemplateStore } from '@/stores/templateStore'
import { useEditorStore } from '@/stores/editorStore'
import { useCanvasInteraction } from '@/composables/useCanvasInteraction'
import type { TreeNode } from '@/types/template.types'
import { deepCloneNode } from '@/stores/templateStore'

interface ClipboardEntry {
  node: TreeNode
  relativeX: number
  relativeY: number
}

const clipboard = ref<ClipboardEntry[]>([])

export function useClipboard() {
  const templateStore = useTemplateStore()
  const editorStore = useEditorStore()
  const { multiSelection } = useCanvasInteraction()

  function copySelection() {
    const ids = multiSelection.value.size > 0
      ? [...multiSelection.value]
      : editorStore.selectedElementId ? [editorStore.selectedElementId] : []

    if (ids.length === 0) return

    // Find reference point (min x, min y) for relative positioning
    let minX = Infinity
    let minY = Infinity
    const nodes: TreeNode[] = []
    for (const id of ids) {
      const node = templateStore.getNodeById(id)
      if (!node) continue
      nodes.push(node)
      const x = (node.properties.x as number) ?? 0
      const y = (node.properties.y as number) ?? 0
      if (x < minX) minX = x
      if (y < minY) minY = y
    }

    clipboard.value = nodes.map((n) => ({
      node: JSON.parse(JSON.stringify(n)) as TreeNode,
      relativeX: ((n.properties.x as number) ?? 0) - minX,
      relativeY: ((n.properties.y as number) ?? 0) - minY,
    }))
  }

  function pasteFromClipboard(): TreeNode[] {
    if (clipboard.value.length === 0) return []

    templateStore.pushUndoSnapshot()
    const pasted: TreeNode[] = []

    // Find parent (root node)
    const root = templateStore.getRootNode
    if (!root) return []

    for (const entry of clipboard.value) {
      const clone = deepCloneNode(entry.node)
      // Offset +10px from original position
      clone.properties = {
        ...clone.properties,
        x: ((entry.node.properties.x as number) ?? 0) + 10,
        y: ((entry.node.properties.y as number) ?? 0) + 10,
      }
      root.children.push(clone)
      // Register in flatNodes
      registerInFlatMap(clone)
      pasted.push(clone)
    }

    // Select first pasted element
    if (pasted.length > 0) {
      editorStore.selectElement(pasted[0]!.id)
    }

    return pasted
  }

  function duplicateSelection(): TreeNode[] {
    const ids = multiSelection.value.size > 0
      ? [...multiSelection.value]
      : editorStore.selectedElementId ? [editorStore.selectedElementId] : []

    if (ids.length === 0) return []

    templateStore.pushUndoSnapshot()
    const duplicated: TreeNode[] = []

    for (const id of ids) {
      const clone = templateStore.duplicateNode(id)
      if (clone) {
        // Offset +10px
        templateStore.moveElement(clone.id, 10, 10)
        duplicated.push(clone)
      }
    }

    if (duplicated.length > 0) {
      editorStore.selectElement(duplicated[0]!.id)
    }

    return duplicated
  }

  function registerInFlatMap(node: TreeNode) {
    templateStore.flatNodes.set(node.id, node)
    for (const child of node.children) {
      registerInFlatMap(child)
    }
  }

  return {
    clipboard,
    copySelection,
    pasteFromClipboard,
    duplicateSelection,
  }
}
