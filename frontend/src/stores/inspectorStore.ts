import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { TreeNode, NodeType } from '@/types/template.types'
import type { InspectorLevel } from '@/types/inspector.types'

const LEVEL_MAP: Partial<Record<NodeType, InspectorLevel>> = {
  document: 'page',
  // Story 33.1: header/footer/flow route to SectionInspector (editable height, padding, repeat, visibility)
  // Previously routed to 'structural' (Story 28.6), but StructuralNodeInfo is read-only.
  header: 'section',
  footer: 'section',
  flow: 'section',
  section: 'section',
  table: 'component',
  chart: 'component',
  image: 'component',
  container: 'component',
  barcode: 'component',
  text: 'element',
  field: 'element',
}

function detectLevel(type: NodeType): InspectorLevel {
  return LEVEL_MAP[type] ?? 'element'
}

export const useInspectorStore = defineStore('inspector', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const selectedNode = ref<TreeNode | null>(null)
  const level = ref<InspectorLevel>('page')
  const properties = ref<Record<string, unknown>>({})
  /** ID do nó selecionado apenas por initFromTree (não por user action).
   *  Usado pela StructureTree para NÃO destacar o nó raiz na inicialização. */
  const initNodeId = ref<string | null>(null)

  // ─── Getters ─────────────────────────────────────────────────────────────
  const hasSelection = computed(() => selectedNode.value !== null)

  const currentLevelLabel = computed<string>(() => {
    const labels: Record<InspectorLevel, string> = {
      page: 'Page',
      section: 'Section',
      component: 'Component',
      element: 'Element',
      structural: 'Structural',
    }
    return labels[level.value]
  })

  // ─── Actions ─────────────────────────────────────────────────────────────
  function selectNode(node: TreeNode) {
    selectedNode.value = node
    level.value = detectLevel(node.type)
    properties.value = { ...node.properties }
    initNodeId.value = null // user selection clears init flag
  }

  function clearSelection() {
    selectedNode.value = null
    properties.value = {}
    level.value = 'page'
    initNodeId.value = null
  }

  function setLevel(newLevel: InspectorLevel) {
    level.value = newLevel
  }

  /**
   * Initialize inspector from document tree root.
   * Selects the root node as initial state (level = 'page').
   * Called from session.ts loadFromPipelineResult() after templateStore is loaded.
   */
  function initFromTree(rootNode: TreeNode) {
    selectedNode.value = rootNode
    level.value = detectLevel(rootNode.type)
    properties.value = { ...rootNode.properties }
    initNodeId.value = rootNode.id // flag: this selection is init-only, not user-driven
  }

  return {
    selectedNode,
    level,
    properties,
    initNodeId,
    hasSelection,
    currentLevelLabel,
    selectNode,
    clearSelection,
    setLevel,
    initFromTree,
  }
})
