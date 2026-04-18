/**
 * Composable for z-index layer ordering (Story 14.8)
 *
 * Provides ordered layer list and reorder operations.
 * z-index is stored as a property on each node.
 */
import { computed } from 'vue'
import { useTemplateStore } from '@/stores/templateStore'
import { useEditorStore } from '@/stores/editorStore'
import type { TreeNode } from '@/types/template.types'

export interface LayerItem {
  id: string
  name: string
  type: string
  zIndex: number
  isGroup: boolean
  children: LayerItem[]
  visible: boolean
}

export function useLayerOrder() {
  const templateStore = useTemplateStore()
  const editorStore = useEditorStore()

  /** Get z-index from node properties (default 0) */
  function getZIndex(node: TreeNode): number {
    const z = node.properties['zIndex']
    return typeof z === 'number' ? z : 0
  }

  /** All leaf/field nodes ordered by z-index descending (highest on top) */
  const orderedLayers = computed<LayerItem[]>(() => {
    const items: LayerItem[] = []
    for (const [, node] of templateStore.flatNodes) {
      // Skip root and sections (layers are for positionable elements)
      if (node.type === 'document') continue
      const isGroup = node.children.length > 0 && (node.properties['isGroup'] as boolean) === true
      items.push({
        id: node.id,
        name: node.name || node.type,
        type: node.type,
        zIndex: getZIndex(node),
        isGroup,
        children: isGroup
          ? node.children.map((c) => ({
              id: c.id,
              name: c.name || c.type,
              type: c.type,
              zIndex: getZIndex(c),
              isGroup: false,
              children: [],
              visible: c.visibility !== false,
            }))
          : [],
        visible: node.visibility !== false,
      })
    }
    return items.sort((a, b) => b.zIndex - a.zIndex)
  })

  function setZIndex(nodeId: string, z: number) {
    templateStore.updateNodeProperty(nodeId, 'zIndex', z)
  }

  function bringToFront(nodeId: string) {
    const maxZ = orderedLayers.value.length > 0 ? orderedLayers.value[0]!.zIndex : 0
    setZIndex(nodeId, maxZ + 10)
  }

  function sendToBack(nodeId: string) {
    const minZ =
      orderedLayers.value.length > 0
        ? orderedLayers.value[orderedLayers.value.length - 1]!.zIndex
        : 0
    setZIndex(nodeId, minZ - 10)
  }

  function moveLayerUp(nodeId: string) {
    const idx = orderedLayers.value.findIndex((l) => l.id === nodeId)
    if (idx <= 0) return
    const above = orderedLayers.value[idx - 1]!
    const current = orderedLayers.value[idx]!
    // Swap z-indices
    setZIndex(nodeId, above.zIndex)
    setZIndex(above.id, current.zIndex)
  }

  function moveLayerDown(nodeId: string) {
    const idx = orderedLayers.value.findIndex((l) => l.id === nodeId)
    if (idx < 0 || idx >= orderedLayers.value.length - 1) return
    const below = orderedLayers.value[idx + 1]!
    const current = orderedLayers.value[idx]!
    setZIndex(nodeId, below.zIndex)
    setZIndex(below.id, current.zIndex)
  }

  function reorderByDrag(fromIndex: number, toIndex: number) {
    if (fromIndex === toIndex) return
    const layers = [...orderedLayers.value]
    const [moved] = layers.splice(fromIndex, 1)
    if (!moved) return
    layers.splice(toIndex, 0, moved)
    // Reassign z-indices: highest first
    templateStore.pushUndoSnapshot()
    const base = layers.length * 10
    for (let i = 0; i < layers.length; i++) {
      templateStore.updateNodeProperty(layers[i]!.id, 'zIndex', base - i * 10)
    }
  }

  function selectLayer(nodeId: string) {
    editorStore.selectElement(nodeId)
  }

  return {
    orderedLayers,
    setZIndex,
    bringToFront,
    sendToBack,
    moveLayerUp,
    moveLayerDown,
    reorderByDrag,
    selectLayer,
  }
}
