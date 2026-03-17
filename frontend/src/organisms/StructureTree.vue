<template>
  <div class="structure-tree" role="tree" aria-label="Árvore de estrutura do documento">
    <!-- Empty state when no tree loaded -->
    <div v-if="!rootNode" class="structure-tree__empty">
      <span class="structure-tree__empty-text">Nenhum documento carregado</span>
    </div>

    <!-- Tree content -->
    <div v-else class="structure-tree__scroll">
      <StructureTreeNode
        :node="rootNode"
        :depth="0"
        :expanded-nodes="expandedNodes"
        :selected-node-id="selectedNodeId"
        @toggle="handleToggle"
        @select="handleSelect"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import StructureTreeNode from '@/molecules/StructureTreeNode.vue'
import { useTemplateStore } from '@/stores/templateStore'
import { useInspectorStore } from '@/stores/inspectorStore'
import { useEditorStore } from '@/stores/editorStore'
import { useLayoutStore } from '@/stores/layout'
import type { TreeNode } from '@/types/template.types'

// ─── Stores ───────────────────────────────────────────────────────────────
const templateStore = useTemplateStore()
const inspectorStore = useInspectorStore()
const editorStore = useEditorStore()
const layoutStore = useLayoutStore()

// ─── Local state ──────────────────────────────────────────────────────────
const expandedNodes = ref<Set<string>>(new Set())
const selectedNodeId = ref<string | null>(null)

// ─── Computed ─────────────────────────────────────────────────────────────
const rootNode = computed<TreeNode | null>(() => templateStore.getRootNode)

// Keep selectedNodeId in sync with inspectorStore
const inspectorSelectedId = computed<string | null>(
  () => inspectorStore.selectedNode?.id ?? null,
)

watch(inspectorSelectedId, (id) => {
  selectedNodeId.value = id
})

// Expand root node by default when tree loads
watch(
  rootNode,
  (node) => {
    if (node) {
      expandedNodes.value = new Set([node.id])
    }
  },
  { immediate: true },
)

// Watch activeLayoutId — reset selection when layout changes (AC: 7)
watch(
  () => layoutStore.activeLayoutId,
  () => {
    inspectorStore.clearSelection()
    selectedNodeId.value = null
  },
)

// ─── Handlers ─────────────────────────────────────────────────────────────
function handleToggle(nodeId: string) {
  const next = new Set(expandedNodes.value)
  if (next.has(nodeId)) {
    next.delete(nodeId)
  } else {
    next.add(nodeId)
  }
  expandedNodes.value = next
}

function handleSelect(node: TreeNode) {
  selectedNodeId.value = node.id
  // AC 5: update inspectorStore and editorStore
  inspectorStore.selectNode(node)
  editorStore.selectElement(node.id)
}
</script>

<style scoped>
.structure-tree {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.structure-tree__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 16px;
}

.structure-tree__empty-text {
  font-size: 0.8125rem;
  color: var(--color-neutral-400, #9ca3af);
  font-style: italic;
}

.structure-tree__scroll {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}
</style>
