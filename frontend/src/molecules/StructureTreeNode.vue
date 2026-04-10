<template>
  <div>
    <!-- Node row -->
    <div
      class="structure-tree-node"
      :class="{
        'structure-tree-node--selected': isSelected,
        'structure-tree-node--has-children': hasChildren,
        'structure-tree-node--dragging': isDragging,
        'structure-tree-node--drag-over': isDragOver,
      }"
      :style="{ paddingLeft: depth * 16 + 'px' }"
      role="treeitem"
      :aria-expanded="hasChildren ? isExpanded : undefined"
      :aria-selected="isSelected"
      draggable="true"
      @click.stop="handleClick"
      @contextmenu.prevent.stop="handleContextMenu"
      @dragstart.stop="handleDragStart"
      @dragend.stop="handleDragEnd"
      @dragover.prevent.stop="handleDragOver"
      @dragleave.stop="handleDragLeave"
      @drop.prevent.stop="handleDrop"
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
      <span class="structure-tree-node__name">{{ node.name || node.type }}</span>

      <!-- Story 28.7: Binding status badge for text/field nodes -->
      <span
        v-if="isBindable"
        class="structure-tree-node__badge"
        :class="badgeClass"
        :title="badgeTooltip"
        >●</span
      >
      <span v-if="isBindable && node.binding" class="structure-tree-node__binding-text">{{
        truncatedBinding
      }}</span>

      <!-- Story 28.7: Coverage mini-bar for container nodes -->
      <template v-if="isContainer && coverageTotal > 0">
        <span class="structure-tree-node__coverage-text"
          >{{ coverageBound }}/{{ coverageTotal }}</span
        >
        <div class="structure-tree-node__coverage-bar">
          <div
            class="structure-tree-node__coverage-fill"
            :style="{ width: coveragePercent + '%' }"
          />
        </div>
      </template>

      <!-- Optional badge -->
      <span v-if="node.isOptional" class="structure-tree-node__optional" title="Elemento opcional">
        ⚠
      </span>
    </div>

    <!-- Drop indicator line (between siblings) -->
    <div v-if="showDropIndicator" class="structure-tree-node__drop-indicator" />

    <!-- Children (recursive) -->
    <template v-if="isExpanded && hasChildren">
      <StructureTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :depth="depth + 1"
        :expanded-nodes="expandedNodes"
        :selected-node-id="selectedNodeId"
        :drag-source-id="dragSourceId"
        @toggle="$emit('toggle', $event)"
        @select="$emit('select', $event)"
        @context-menu="$emit('context-menu', $event)"
        @drag-start="$emit('drag-start', $event)"
        @drag-end="$emit('drag-end')"
        @drop-node="$emit('drop-node', $event)"
        @drop-field="$emit('drop-field', $event)"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { TreeNode, NodeType } from '@/types/template.types'
import { useMappingStore } from '@/stores/mapping'

// ─── Props ────────────────────────────────────────────────────────────────
interface Props {
  node: TreeNode
  depth: number
  expandedNodes: Set<string>
  selectedNodeId: string | null
  dragSourceId?: string | null
}

const props = defineProps<Props>()

const mappingStore = useMappingStore()

// ─── Emits ────────────────────────────────────────────────────────────────
const emit = defineEmits<{
  toggle: [nodeId: string]
  select: [node: TreeNode]
  'context-menu': [payload: { node: TreeNode; x: number; y: number }]
  'drag-start': [nodeId: string]
  'drag-end': []
  'drop-node': [
    payload: { draggedId: string; targetId: string; position: 'before' | 'after' | 'inside' },
  ]
  'drop-field': [payload: { nodeId: string; fieldPath: string }]
}>()

// ─── Type Icon Map ────────────────────────────────────────────────────────
const typeIcons: Record<NodeType, string> = {
  document: '📄',
  section: '📦',
  header: '📦',
  footer: '📦',
  flow: '📦',
  text: '🔤',
  field: 'abc',
  label: '🔤',
  value: '🔤',
  likely_dynamic: '~',
  dynamic: '🔤',
  table: '📋',
  chart: '📊',
  image: '🖼',
  container: '📦',
  barcode: '|||',
}

// ─── Local state ──────────────────────────────────────────────────────────
const isDragging = ref(false)
const isDragOver = ref(false)
const showDropIndicator = ref(false)

// ─── Computed ─────────────────────────────────────────────────────────────
const typeIcon = computed<string>(() => typeIcons[props.node.type] ?? '📄')
const hasChildren = computed<boolean>(() => props.node.children.length > 0)
const isExpanded = computed<boolean>(() => props.expandedNodes.has(props.node.id))
const isSelected = computed<boolean>(() => props.selectedNodeId === props.node.id)

// ─── Story 28.7: Binding badges + coverage bars ──────────────────────────
const BINDABLE_TYPES = new Set<NodeType>(['text', 'field', 'value', 'likely_dynamic', 'dynamic'])
const CONTAINER_TYPES = new Set<NodeType>(['section', 'header', 'footer', 'flow', 'container'])

const isBindable = computed(() => BINDABLE_TYPES.has(props.node.type))
const isContainer = computed(() => CONTAINER_TYPES.has(props.node.type))

/** Compute binding status for text/field nodes */
const bindingStatus = computed<'mapped' | 'unbound' | 'unconfirmed'>(() => {
  if (!isBindable.value) return 'mapped' // containers don't use this
  if (!props.node.binding) return 'unbound'
  const navItem = mappingStore.fieldNavItems.find(
    (f) => f.path === props.node.binding || f.nodeId === props.node.id,
  )
  if (navItem?.status === 'unconfirmed') return 'unconfirmed'
  return 'mapped'
})

const badgeClass = computed(() => ({
  'badge--mapped': bindingStatus.value === 'mapped',
  'badge--unbound': bindingStatus.value === 'unbound',
  'badge--unconfirmed': bindingStatus.value === 'unconfirmed',
}))

const badgeTooltip = computed(() =>
  bindingStatus.value === 'unbound'
    ? 'sem binding — selecione no Inspector para vincular'
    : (props.node.binding ?? ''),
)

const truncatedBinding = computed(() => {
  const b = props.node.binding ?? ''
  return b.length > 20 ? b.substring(0, 17) + '...' : b
})

/** Recursively collect all descendants of a node */
function getAllDescendants(node: TreeNode): TreeNode[] {
  const result: TreeNode[] = []
  for (const child of node.children ?? []) {
    result.push(child)
    result.push(...getAllDescendants(child))
  }
  return result
}

const coverageTotal = computed(() => {
  if (!isContainer.value) return 0
  return getAllDescendants(props.node).filter((n) => BINDABLE_TYPES.has(n.type)).length
})

const coverageBound = computed(() => {
  if (!isContainer.value) return 0
  return getAllDescendants(props.node).filter((n) => BINDABLE_TYPES.has(n.type) && !!n.binding)
    .length
})

const coveragePercent = computed(() =>
  coverageTotal.value === 0 ? 0 : Math.round((coverageBound.value / coverageTotal.value) * 100),
)

// ─── Handlers ─────────────────────────────────────────────────────────────
function handleToggle() {
  if (hasChildren.value) {
    emit('toggle', props.node.id)
  }
}

function handleClick() {
  // Story 28.6 — select only; toggle is handled exclusively by the ▶/▼ icon (@click.stop)
  emit('select', props.node)
}

function handleContextMenu(event: MouseEvent) {
  emit('context-menu', { node: props.node, x: event.clientX, y: event.clientY })
}

// ─── Drag & Drop ──────────────────────────────────────────────────────────
function handleDragStart(event: DragEvent) {
  isDragging.value = true
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', props.node.id)
  }
  emit('drag-start', props.node.id)
}

function handleDragEnd() {
  isDragging.value = false
  isDragOver.value = false
  showDropIndicator.value = false
  emit('drag-end')
}

function handleDragOver(event: DragEvent) {
  if (props.dragSourceId === props.node.id) return
  isDragOver.value = true

  // Determine drop position based on mouse position within element
  const el = event.currentTarget as HTMLElement
  const rect = el.getBoundingClientRect()
  const relY = event.clientY - rect.top
  const threshold = rect.height * 0.3

  if (relY < threshold) {
    showDropIndicator.value = true
    isDragOver.value = false
  } else if (relY > rect.height - threshold) {
    showDropIndicator.value = true
    isDragOver.value = false
  } else {
    showDropIndicator.value = false
    isDragOver.value = true
  }
}

function handleDragLeave() {
  isDragOver.value = false
  showDropIndicator.value = false
}

function handleDrop(event: DragEvent) {
  isDragOver.value = false
  showDropIndicator.value = false

  const dragType = event.dataTransfer?.getData('drag-type')

  // Field drop from FieldNavigator
  if (dragType === 'field') {
    const fieldPath = event.dataTransfer?.getData('field-path')
    if (fieldPath) {
      emit('drop-field', { nodeId: props.node.id, fieldPath })
    }
    return
  }

  // Node reorder drop
  const draggedId = event.dataTransfer?.getData('text/plain')
  if (!draggedId || draggedId === props.node.id) return

  // Determine drop position
  const el = event.currentTarget as HTMLElement
  const rect = el.getBoundingClientRect()
  const relY = event.clientY - rect.top
  const threshold = rect.height * 0.3

  let position: 'before' | 'after' | 'inside'
  if (relY < threshold) {
    position = 'before'
  } else if (relY > rect.height - threshold) {
    position = 'after'
  } else {
    position = 'inside'
  }

  emit('drop-node', { draggedId, targetId: props.node.id, position })
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

.structure-tree-node--dragging {
  opacity: 0.4;
}

.structure-tree-node--drag-over {
  background: var(--color-blue-50, #eff6ff);
  outline: 2px dashed var(--color-blue-400, #60a5fa);
  outline-offset: -2px;
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
  .structure-tree-node--drag-over {
    background: rgba(96, 165, 250, 0.1);
  }
}

.structure-tree-node__toggle {
  display: inline-flex;
  width: 14px;
  flex-shrink: 0;
}

.structure-tree-node__arrow {
  font-size: 0.6rem;
  color: var(--color-neutral-500, #525252);
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

/* Story 28.7: binding status badge */
.structure-tree-node__badge {
  flex-shrink: 0;
  font-size: 0.5rem;
  cursor: help;
}

.badge--mapped {
  color: var(--color-green-500, #22c55e);
}

.badge--unbound {
  color: var(--color-red-500, #ef4444);
  opacity: 0.8;
}

.badge--unconfirmed {
  color: var(--color-yellow-400, #facc15);
}

.structure-tree-node__binding-text {
  font-size: 0.6875rem;
  color: var(--color-indigo-400, #818cf8);
  font-family: monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100px;
}

/* Story 28.7: coverage mini-bar for containers */
.structure-tree-node__coverage-text {
  font-size: 0.5625rem;
  color: var(--color-neutral-500, #525252);
  flex-shrink: 0;
  white-space: nowrap;
}

.structure-tree-node__coverage-bar {
  width: 28px;
  height: 3px;
  background: var(--color-neutral-700, #374151);
  border-radius: 1.5px;
  flex-shrink: 0;
  overflow: hidden;
}

.structure-tree-node__coverage-fill {
  height: 100%;
  background: var(--color-green-500, #22c55e);
  border-radius: 1.5px;
  transition: width 0.2s ease;
  min-width: 0;
}

.structure-tree-node__optional {
  font-size: 0.75rem;
  flex-shrink: 0;
}

.structure-tree-node__drop-indicator {
  height: 2px;
  background: var(--color-blue-400, #60a5fa);
  margin: 0 4px;
  border-radius: 1px;
}
</style>
