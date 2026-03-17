import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { DocumentTree, TreeNode, NodeType, NodeProperties } from '@/types/template.types'

export const useTemplateStore = defineStore('template', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const documentTree = ref<DocumentTree | null>(null)
  const flatNodes = ref<Map<string, TreeNode>>(new Map())

  // ─── Helpers ─────────────────────────────────────────────────────────────
  function buildFlatMap(node: TreeNode, map: Map<string, TreeNode>) {
    map.set(node.id, node)
    for (const child of node.children) {
      buildFlatMap(child, map)
    }
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
  function loadTree(tree: DocumentTree) {
    documentTree.value = tree
    const map = new Map<string, TreeNode>()
    buildFlatMap(tree.root, map)
    flatNodes.value = map
  }

  function updateNodeProperties(id: string, props: Partial<NodeProperties>) {
    const node = flatNodes.value.get(id)
    if (!node) return
    node.properties = { ...node.properties, ...props }
  }

  return {
    documentTree,
    flatNodes,
    getRootNode,
    getNodeById,
    getNodesByType,
    getChildren,
    loadTree,
    updateNodeProperties,
  }
})
