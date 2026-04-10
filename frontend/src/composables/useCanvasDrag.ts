/**
 * Story 40.6 — FE-002: Drag-drop field handling for HTMLCanvas.
 *
 * Extracted from HTMLCanvas.vue to reduce component LOC.
 * Handles field drag-over, drag-leave, drop, and drag-end events.
 */
import { ref } from 'vue'
import { useTemplateStore } from '@/stores/templateStore'
import { useMappingStore } from '@/stores/mapping'
import type { BoundingBox } from '@/composables/useCanvasInteraction'

export function useCanvasDrag(elementBoxes: { value: Map<string, BoundingBox> }) {
  const templateStore = useTemplateStore()
  const mappingStore = useMappingStore()

  /** nodeId of the element currently under the drag cursor (drop target) */
  const dropTargetNodeId = ref<string | null>(null)

  /**
   * Find the canvas node whose bounding box contains the given screen coordinates.
   */
  function getNodeAtScreenPosition(clientX: number, clientY: number): string | null {
    for (const [nodeId, box] of elementBoxes.value.entries()) {
      if (
        clientX >= box.x &&
        clientX <= box.x + box.width &&
        clientY >= box.y &&
        clientY <= box.y + box.height
      ) {
        return nodeId
      }
    }
    return null
  }

  function onFieldDragOver(event: DragEvent) {
    const types = event.dataTransfer?.types ?? []
    if (!types.includes('drag-type') && !types.includes('field-path')) {
      return
    }
    const nodeId = getNodeAtScreenPosition(event.clientX, event.clientY)
    dropTargetNodeId.value = nodeId
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = nodeId ? 'copy' : 'none'
    }
  }

  function onFieldDragLeave(event: DragEvent) {
    const canvas = event.currentTarget as HTMLElement | null
    if (!canvas?.contains(event.relatedTarget as Node | null)) {
      dropTargetNodeId.value = null
    }
  }

  async function onFieldDrop(event: DragEvent) {
    const dragType = event.dataTransfer?.getData('drag-type')
    if (dragType !== 'field') {
      dropTargetNodeId.value = null
      return
    }

    const xsdPath = event.dataTransfer?.getData('field-path')
    const targetNodeId = dropTargetNodeId.value
    dropTargetNodeId.value = null

    if (!targetNodeId || !xsdPath) return

    const targetNode = templateStore.getNodeById(targetNodeId)
    if (targetNode?.binding) {
      const confirmed = window.confirm(
        `Substituir binding de "${targetNode.binding}" por "${xsdPath}"?`,
      )
      if (!confirmed) return
    }

    mappingStore.updateNodeBinding(targetNodeId, xsdPath)
  }

  function onFieldDragEnd() {
    dropTargetNodeId.value = null
  }

  return {
    dropTargetNodeId,
    getNodeAtScreenPosition,
    onFieldDragOver,
    onFieldDragLeave,
    onFieldDrop,
    onFieldDragEnd,
  }
}
