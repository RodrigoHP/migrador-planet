import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { TreeNode, NodeType } from '@/types/template.types'
import type { InspectorLevel } from '@/types/inspector.types'

const LEVEL_MAP: Partial<Record<NodeType, InspectorLevel>> = {
  document: 'page',
  header: 'page',
  footer: 'page',
  flow: 'page',
  section: 'section',
  table: 'component',
  chart: 'component',
  image: 'component',
  container: 'component',
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

  // ─── Getters ─────────────────────────────────────────────────────────────
  const hasSelection = computed(() => selectedNode.value !== null)

  const currentLevelLabel = computed<string>(() => {
    const labels: Record<InspectorLevel, string> = {
      page: 'Page',
      section: 'Section',
      component: 'Component',
      element: 'Element',
    }
    return labels[level.value]
  })

  // ─── Actions ─────────────────────────────────────────────────────────────
  function selectNode(node: TreeNode) {
    selectedNode.value = node
    level.value = detectLevel(node.type)
    properties.value = { ...node.properties }
  }

  function clearSelection() {
    selectedNode.value = null
    properties.value = {}
    level.value = 'page'
  }

  function setLevel(newLevel: InspectorLevel) {
    level.value = newLevel
  }

  return {
    selectedNode,
    level,
    properties,
    hasSelection,
    currentLevelLabel,
    selectNode,
    clearSelection,
    setLevel,
  }
})
