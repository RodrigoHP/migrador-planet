<template>
  <div>
    <!-- Node row -->
    <div
      class="structure-tree-node"
      :class="{
        'structure-tree-node--selected': isSelected,
        'structure-tree-node--has-children': hasChildren,
      }"
      :style="{ paddingLeft: depth * 16 + 'px' }"
      role="treeitem"
      :aria-expanded="hasChildren ? isExpanded : undefined"
      :aria-selected="isSelected"
      @click.stop="handleClick"
    >
      <!-- Expand/collapse toggle -->
      <span class="structure-tree-node__toggle" @click.stop="handleToggle">
        <span v-if="hasChildren" class="structure-tree-node__arrow">
          {{ isExpanded ? '▼' : '▶' }}
        </span>
        <span v-else class="structure-tree-node__leaf">·</span>
      </span>

      <!-- Type icon -->
      <span class="structure-tree-node__icon">{{ typeIcon }}</span>

      <!-- Node name -->
      <span class="structure-tree-node__name">{{ node.name }}</span>

      <!-- Binding indicator -->
      <span v-if="node.binding" class="structure-tree-node__binding" :title="bindingLabel">
        → {{ bindingLabel }}
      </span>

      <!-- Optional badge -->
      <span v-if="node.isOptional" class="structure-tree-node__optional" title="Elemento opcional">
        ⚠
      </span>
    </div>

    <!-- Children (recursive) -->
    <template v-if="isExpanded && hasChildren">
      <StructureTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :depth="depth + 1"
        :expanded-nodes="expandedNodes"
        :selected-node-id="selectedNodeId"
        @toggle="$emit('toggle', $event)"
        @select="$emit('select', $event)"
      />
    </template>

    <!-- Empty placeholder -->
    <template v-if="isExpanded && !hasChildren && depth > 0">
      <!-- placeholder shown from parent if no children, not here -->
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TreeNode, NodeType } from '@/types/template.types'

// ─── Props ────────────────────────────────────────────────────────────────
interface Props {
  node: TreeNode
  depth: number
  expandedNodes: Set<string>
  selectedNodeId: string | null
}

const props = defineProps<Props>()

// ─── Emits ────────────────────────────────────────────────────────────────
const emit = defineEmits<{
  toggle: [nodeId: string]
  select: [node: TreeNode]
}>()

// ─── Type Icon Map ────────────────────────────────────────────────────────
const typeIcons: Record<NodeType, string> = {
  document: '📄',
  section: '📦',
  header: '📦',
  footer: '📦',
  flow: '📦',
  text: '🔤',
  field: '🔤',
  table: '📋',
  chart: '📊',
  image: '🖼',
  container: '📦',
}

// ─── Computed ─────────────────────────────────────────────────────────────
const typeIcon = computed<string>(() => typeIcons[props.node.type] ?? '📄')
const hasChildren = computed<boolean>(() => props.node.children.length > 0)
const isExpanded = computed<boolean>(() => props.expandedNodes.has(props.node.id))
const isSelected = computed<boolean>(() => props.selectedNodeId === props.node.id)
const bindingLabel = computed<string>(() =>
  props.node.binding ? `\u007b\u007b${props.node.binding}\u007d\u007d` : '',
)

// ─── Handlers ─────────────────────────────────────────────────────────────
function handleToggle() {
  if (hasChildren.value) {
    emit('toggle', props.node.id)
  }
}

function handleClick() {
  emit('select', props.node)
  if (hasChildren.value) {
    emit('toggle', props.node.id)
  }
}
</script>

<style scoped>
.structure-tree-node {
  display: flex;
  align-items: center;
  gap: 4px;
  padding-top: 3px;
  padding-bottom: 3px;
  padding-right: 8px;
  border-radius: 4px;
  cursor: pointer;
  user-select: none;
  font-size: 0.8125rem;
  color: var(--color-neutral-700, #374151);
  transition: background 80ms ease;
}

.structure-tree-node:hover {
  background: var(--color-neutral-100, #f3f4f6);
}

.structure-tree-node--selected {
  background: var(--color-blue-100, #dbeafe);
  color: var(--color-blue-900, #1e3a8a);
  font-weight: 500;
}

/* dark mode */
@media (prefers-color-scheme: dark) {
  .structure-tree-node {
    color: var(--color-neutral-300, #d1d5db);
  }
  .structure-tree-node:hover {
    background: var(--color-neutral-700, #374151);
  }
  .structure-tree-node--selected {
    background: var(--color-blue-900, #1e3a8a);
    color: var(--color-blue-100, #dbeafe);
  }
}

.structure-tree-node__toggle {
  display: inline-flex;
  width: 14px;
  flex-shrink: 0;
}

.structure-tree-node__arrow {
  font-size: 0.6rem;
  color: var(--color-neutral-500, #6b7280);
}

.structure-tree-node__leaf {
  font-size: 0.75rem;
  color: var(--color-neutral-400, #9ca3af);
}

.structure-tree-node__icon {
  flex-shrink: 0;
  font-size: 0.875rem;
}

.structure-tree-node__name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.structure-tree-node__binding {
  font-size: 0.7rem;
  color: var(--color-indigo-500, #6366f1);
  font-family: monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.structure-tree-node__optional {
  font-size: 0.75rem;
  flex-shrink: 0;
}
</style>
