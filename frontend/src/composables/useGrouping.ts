/**
 * Composable for group/ungroup operations (Story 14.8)
 *
 * Extends templateStore.groupNodes() with transformation propagation.
 */
import { useTemplateStore } from '@/stores/templateStore'
import type { TreeNode } from '@/types/template.types'

export function useGrouping() {
  const templateStore = useTemplateStore()

  /**
   * Create a group from the given node IDs.
   * Finds the common parent and delegates to templateStore.groupNodes().
   * Marks the group node with isGroup=true.
   */
  function createGroup(nodeIds: string[]): TreeNode | null {
    if (nodeIds.length < 2) return null

    // Find common parent
    const first = nodeIds[0]!
    const parent = templateStore.findParent(first)
    if (!parent) return null

    const group = templateStore.groupNodes(nodeIds, parent.id)
    if (!group) return null

    // Mark as group
    group.properties = { ...group.properties, isGroup: true }
    return group
  }

  /**
   * Ungroup: move children back to the group's parent and remove the group node.
   */
  function ungroupNode(groupNodeId: string): boolean {
    const group = templateStore.getNodeById(groupNodeId)
    if (!group || group.properties['isGroup'] !== true) return false

    const parent = templateStore.findParent(groupNodeId)
    if (!parent) return false

    templateStore.pushUndoSnapshot()

    // Find index of group in parent
    const idx = parent.children.findIndex((c) => c.id === groupNodeId)
    if (idx === -1) return false

    // Move children to parent at group's position
    const children = [...group.children]
    parent.children.splice(idx, 1, ...children)

    // Remove group from flatNodes, re-add children
    templateStore.flatNodes.delete(groupNodeId)

    return true
  }

  /**
   * Move all children of a group by delta.
   */
  function moveGroup(groupId: string, deltaX: number, deltaY: number) {
    const group = templateStore.getNodeById(groupId)
    if (!group) return

    templateStore.pushUndoSnapshot()
    for (const child of group.children) {
      templateStore.moveElement(child.id, deltaX, deltaY)
    }
  }

  /**
   * Resize group: scale all children proportionally.
   */
  function resizeGroup(groupId: string, scaleX: number, scaleY: number) {
    const group = templateStore.getNodeById(groupId)
    if (!group) return

    templateStore.pushUndoSnapshot()
    for (const child of group.children) {
      const w = (child.properties.width as number) ?? 0
      const h = (child.properties.height as number) ?? 0
      const x = (child.properties.x as number) ?? 0
      const y = (child.properties.y as number) ?? 0
      child.properties = {
        ...child.properties,
        width: Math.round(w * scaleX),
        height: Math.round(h * scaleY),
        x: Math.round(x * scaleX),
        y: Math.round(y * scaleY),
      }
    }
  }

  /**
   * Apply a property to all children of a group.
   */
  function applyBatchProperty(groupId: string, property: string, value: unknown) {
    const group = templateStore.getNodeById(groupId)
    if (!group) return

    templateStore.pushUndoSnapshot()
    for (const child of group.children) {
      templateStore.updateNodeProperty(child.id, property, value)
    }
  }

  return {
    createGroup,
    ungroupNode,
    moveGroup,
    resizeGroup,
    applyBatchProperty,
  }
}
