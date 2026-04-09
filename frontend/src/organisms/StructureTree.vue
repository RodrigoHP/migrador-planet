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
        :drag-source-id="dragSourceId"
        @toggle="handleToggle"
        @select="handleSelect"
        @context-menu="handleContextMenu"
        @drag-start="handleDragStart"
        @drag-end="handleDragEnd"
        @drop-node="handleDropNode"
        @drop-field="handleDropField"
      />
    </div>

    <!-- Context Menu -->
    <ContextMenu
      :visible="contextMenuVisible"
      :position="contextMenuPosition"
      :items="contextMenuItems"
      @close="closeContextMenu"
      @item-click="handleContextMenuItem"
    />

    <!-- Field binding confirmation dialog -->
    <div v-if="fieldBindingConfirm" class="structure-tree__confirm-overlay">
      <div class="structure-tree__confirm-dialog">
        <p class="structure-tree__confirm-msg">
          O nó <strong>{{ fieldBindingConfirm.nodeName }}</strong> já possui binding
          <code>{{ fieldBindingConfirm.existingBinding }}</code>.<br>
          Substituir por <code>{{ fieldBindingConfirm.newFieldPath }}</code>?
        </p>
        <div class="structure-tree__confirm-actions">
          <button class="structure-tree__confirm-btn structure-tree__confirm-btn--cancel" @click="cancelFieldBinding">
            Cancelar
          </button>
          <button class="structure-tree__confirm-btn structure-tree__confirm-btn--confirm" @click="applyFieldBinding">
            Substituir
          </button>
        </div>
      </div>
    </div>

    <!-- Save as component dialog -->
    <div v-if="saveComponentDialog.visible" class="structure-tree__confirm-overlay">
      <div class="structure-tree__confirm-dialog">
        <p class="structure-tree__confirm-msg">
          Salvar "<strong>{{ saveComponentDialog.nodeName }}</strong>" como componente:
        </p>
        <input
          v-model="saveComponentDialog.name"
          class="structure-tree__input"
          placeholder="Nome do componente"
          @keydown.enter="executeSaveComponent"
        />
        <div class="structure-tree__confirm-actions">
          <button class="structure-tree__confirm-btn structure-tree__confirm-btn--cancel" @click="saveComponentDialog.visible = false">
            Cancelar
          </button>
          <button class="structure-tree__confirm-btn structure-tree__confirm-btn--save" @click="executeSaveComponent">
            Salvar
          </button>
        </div>
      </div>
    </div>

    <!-- Remove confirmation dialog -->
    <div v-if="removeConfirmNode" class="structure-tree__confirm-overlay">
      <div class="structure-tree__confirm-dialog">
        <p class="structure-tree__confirm-msg">
          Remover "<strong>{{ removeConfirmNode.name }}</strong>" e todos os seus filhos?
        </p>
        <div class="structure-tree__confirm-actions">
          <button class="structure-tree__confirm-btn structure-tree__confirm-btn--cancel" @click="cancelRemove">
            Cancelar
          </button>
          <button class="structure-tree__confirm-btn structure-tree__confirm-btn--confirm" @click="confirmRemove">
            Remover
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import StructureTreeNode from '@/molecules/StructureTreeNode.vue'
import ContextMenu from '@/molecules/ContextMenu.vue'
import type { ContextMenuItem } from '@/molecules/ContextMenu.vue'
import { useTemplateStore } from '@/stores/templateStore'
import { useInspectorStore } from '@/stores/inspectorStore'
import { useEditorStore } from '@/stores/editorStore'
import { useLayoutStore } from '@/stores/layout'
import { useMappingStore } from '@/stores/mapping'
import { useBibliotecas } from '@/composables/useBibliotecas'
import type { TreeNode, NodeType } from '@/types/template.types'

// ─── Stores ───────────────────────────────────────────────────────────────
const templateStore = useTemplateStore()
const inspectorStore = useInspectorStore()
const editorStore = useEditorStore()
const layoutStore = useLayoutStore()
const mappingStore = useMappingStore()
const bibliotecas = useBibliotecas()

// ─── Local state ──────────────────────────────────────────────────────────
const expandedNodes = ref<Set<string>>(new Set())
const selectedNodeId = ref<string | null>(null)

// ─── Drag state ───────────────────────────────────────────────────────────
const dragSourceId = ref<string | null>(null)

// ─── Context menu state ───────────────────────────────────────────────────
const contextMenuVisible = ref(false)
const contextMenuPosition = ref({ x: 0, y: 0 })
const contextMenuTargetNode = ref<TreeNode | null>(null)

// ─── Remove confirmation ──────────────────────────────────────────────────
const removeConfirmNode = ref<TreeNode | null>(null)

// ─── Field binding confirmation ───────────────────────────────────────────
interface FieldBindingConfirm {
  nodeId: string
  nodeName: string
  existingBinding: string
  newFieldPath: string
}
const fieldBindingConfirm = ref<FieldBindingConfirm | null>(null)

// ─── Computed ─────────────────────────────────────────────────────────────
const rootNode = computed<TreeNode | null>(() => templateStore.getRootNode)

// Keep selectedNodeId in sync with inspectorStore.
// Guard: if selectedNode was set by initFromTree (not user action), don't highlight in tree.
const inspectorSelectedId = computed<string | null>(() => {
  const id = inspectorStore.selectedNode?.id ?? null
  if (id !== null && id === inspectorStore.initNodeId) return null
  return id
})

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

// Watch activeLayoutId — reset selection when layout changes
watch(
  () => layoutStore.activeLayoutId,
  () => {
    inspectorStore.clearSelection()
    selectedNodeId.value = null
  },
)

// ─── Tree handlers ─────────────────────────────────────────────────────────
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
  inspectorStore.selectNode(node)
  editorStore.selectElement(node.id)
}

// ─── Drag & Drop handlers ─────────────────────────────────────────────────
function handleDragStart(nodeId: string) {
  dragSourceId.value = nodeId
}

function handleDragEnd() {
  dragSourceId.value = null
}

function handleDropNode(payload: {
  draggedId: string
  targetId: string
  position: 'before' | 'after' | 'inside'
}) {
  const { draggedId, targetId, position } = payload
  if (draggedId === targetId) return

  const root = templateStore.getRootNode
  if (!root) return

  if (position === 'inside') {
    // Drop inside target node → append as last child
    templateStore.moveNode(draggedId, targetId)
    // Expand the target to show the new child
    const next = new Set(expandedNodes.value)
    next.add(targetId)
    expandedNodes.value = next
  } else {
    // Drop before/after → same parent as target
    const targetParent = templateStore.findParent(targetId)
    if (!targetParent) return

    const targetIdx = targetParent.children.findIndex((c) => c.id === targetId)
    const insertIdx = position === 'before' ? targetIdx : targetIdx + 1

    templateStore.moveNode(draggedId, targetParent.id, insertIdx)
  }

  dragSourceId.value = null
}

// ─── Context Menu ─────────────────────────────────────────────────────────
function handleContextMenu(payload: { node: TreeNode; x: number; y: number }) {
  contextMenuTargetNode.value = payload.node
  contextMenuPosition.value = { x: payload.x, y: payload.y }
  contextMenuVisible.value = true
}

function closeContextMenu() {
  contextMenuVisible.value = false
  contextMenuTargetNode.value = null
}

const contextMenuItems = computed<ContextMenuItem[]>(() => {
  const node = contextMenuTargetNode.value
  if (!node) return []

  // Determine available "Move to" targets
  const moveTargets: ContextMenuItem[] = []
  if (node.type !== 'header') {
    const headerNode = templateStore.getNodesByType('header')[0]
    if (headerNode) {
      moveTargets.push({
        id: 'move-header',
        label: 'Header',
        icon: '📦',
        action: () => templateStore.moveNode(node.id, headerNode.id),
      })
    }
  }
  if (node.type !== 'flow') {
    const flowNode = templateStore.getNodesByType('flow')[0]
    if (flowNode) {
      moveTargets.push({
        id: 'move-flow',
        label: 'Flow',
        icon: '📦',
        action: () => templateStore.moveNode(node.id, flowNode.id),
      })
    }
  }
  if (node.type !== 'footer') {
    const footerNode = templateStore.getNodesByType('footer')[0]
    if (footerNode) {
      moveTargets.push({
        id: 'move-footer',
        label: 'Footer',
        icon: '📦',
        action: () => templateStore.moveNode(node.id, footerNode.id),
      })
    }
  }

  const elementTypes: NodeType[] = ['text', 'table', 'chart', 'image', 'container']
  const typeLabels: Record<string, string> = {
    text: 'Texto',
    table: 'Tabela',
    chart: 'Gráfico',
    image: 'Imagem',
    container: 'Container',
  }
  const typeIcons: Record<string, string> = {
    text: '🔤',
    table: '📋',
    chart: '📊',
    image: '🖼',
    container: '📦',
  }

  const addSubmenu: ContextMenuItem[] = elementTypes.map((t) => ({
    id: `add-${t}`,
    label: typeLabels[t] ?? t,
    icon: typeIcons[t],
    action: () => {
      const newNode = templateStore.addNode(node.id, t)
      if (newNode) {
        const next = new Set(expandedNodes.value)
        next.add(node.id)
        expandedNodes.value = next
      }
    },
  }))

  const items: ContextMenuItem[] = [
    {
      id: 'add-element',
      label: 'Adicionar elemento',
      icon: '➕',
      submenu: addSubmenu,
    },
    {
      id: 'group',
      label: 'Agrupar em seção',
      icon: '📦',
      disabled: !node,
      action: () => {
        const parent = templateStore.findParent(node.id)
        if (parent) {
          const grouped = templateStore.groupNodes([node.id], parent.id)
          if (grouped) {
            const next = new Set(expandedNodes.value)
            next.add(grouped.id)
            expandedNodes.value = next
          }
        }
      },
    },
    {
      id: 'duplicate',
      label: 'Duplicar',
      icon: '📋',
      action: () => templateStore.duplicateNode(node.id),
    },
    { id: 'sep-1', label: '', type: 'separator' },
    ...(moveTargets.length > 0
      ? [
          {
            id: 'move-to',
            label: 'Mover para...',
            icon: '↗️',
            submenu: moveTargets,
          } as ContextMenuItem,
          { id: 'sep-2', label: '', type: 'separator' as const },
        ]
      : []),
    ...(node.binding
      ? [
          { id: 'sep-binding', label: '', type: 'separator' as const },
          {
            id: 'remove-binding',
            label: 'Remover binding',
            icon: '🔗',
            action: () => mappingStore.removeBinding(node.id),
          } as ContextMenuItem,
        ]
      : []),
    { id: 'sep-save', label: '', type: 'separator' },
    {
      id: 'save-component',
      label: 'Salvar como componente',
      icon: '💾',
      action: () => promptSaveComponent(node),
    },
    {
      id: 'remove',
      label: 'Remover',
      icon: '🗑',
      danger: true,
      action: () => handleRemoveRequest(node),
    },
  ]

  return items
})

function handleContextMenuItem(_item: ContextMenuItem) {
  // Actions are called via item.action() — nothing extra needed here
}

// ─── Save as component ───────────────────────────────────────────────────────
const saveComponentDialog = reactive({
  visible: false,
  name: '',
  nodeName: '',
  node: null as TreeNode | null,
})

function promptSaveComponent(node: TreeNode) {
  saveComponentDialog.name = node.name
  saveComponentDialog.nodeName = node.name
  saveComponentDialog.node = node
  saveComponentDialog.visible = true
}

async function executeSaveComponent() {
  if (!saveComponentDialog.node || !saveComponentDialog.name.trim()) return
  await bibliotecas.saveComponent(saveComponentDialog.name.trim(), saveComponentDialog.node)
  saveComponentDialog.visible = false
  saveComponentDialog.node = null
}

// ─── Drop field (from FieldNavigator drag) ────────────────────────────────
function handleDropField(payload: { nodeId: string; fieldPath: string }) {
  const { nodeId, fieldPath } = payload
  const node = templateStore.getNodeById(nodeId)
  if (!node) return

  if (node.binding && node.binding !== fieldPath) {
    // Show confirmation before replacing existing binding
    fieldBindingConfirm.value = {
      nodeId,
      nodeName: node.name,
      existingBinding: node.binding,
      newFieldPath: fieldPath,
    }
  } else {
    mappingStore.mapField(nodeId, fieldPath)
  }
}

function applyFieldBinding() {
  if (!fieldBindingConfirm.value) return
  const { nodeId, newFieldPath } = fieldBindingConfirm.value
  mappingStore.mapField(nodeId, newFieldPath)
  fieldBindingConfirm.value = null
}

function cancelFieldBinding() {
  fieldBindingConfirm.value = null
}

// ─── Remove with confirmation ─────────────────────────────────────────────
function handleRemoveRequest(node: TreeNode) {
  if (node.children.length > 0) {
    // Show confirmation dialog
    removeConfirmNode.value = node
  } else {
    // Leaf node: remove directly
    templateStore.removeNode(node.id)
    if (selectedNodeId.value === node.id) {
      selectedNodeId.value = null
      inspectorStore.clearSelection()
    }
  }
}

function cancelRemove() {
  removeConfirmNode.value = null
}

function confirmRemove() {
  if (!removeConfirmNode.value) return
  const id = removeConfirmNode.value.id
  templateStore.removeNode(id)
  if (selectedNodeId.value === id) {
    selectedNodeId.value = null
    inspectorStore.clearSelection()
  }
  removeConfirmNode.value = null
}
</script>

<style scoped>
.structure-tree {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  position: relative;
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

/* ─── Confirmation dialog ─────────────────────────────────────────── */
.structure-tree__confirm-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.structure-tree__confirm-dialog {
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 8px;
  padding: 16px;
  max-width: 260px;
  width: 90%;
}

.structure-tree__confirm-msg {
  font-size: 0.8125rem;
  color: var(--color-neutral-200, #e5e7eb);
  margin: 0 0 12px;
  line-height: 1.4;
}

.structure-tree__confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.structure-tree__confirm-btn {
  font-size: 0.75rem;
  padding: 5px 12px;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  font-weight: 500;
}

.structure-tree__confirm-btn--cancel {
  background: var(--color-neutral-600, #4b5563);
  color: var(--color-neutral-100, #f3f4f6);
}

.structure-tree__confirm-btn--cancel:hover {
  background: var(--color-neutral-500, #6b7280);
}

.structure-tree__confirm-btn--confirm {
  background: var(--color-red-600, #dc2626);
  color: #fff;
}

.structure-tree__confirm-btn--confirm:hover {
  background: var(--color-red-700, #b91c1c);
}

.structure-tree__confirm-btn--save {
  background: var(--color-primary-600, #2563eb);
  color: #fff;
}

.structure-tree__confirm-btn--save:hover {
  background: var(--color-primary-700, #1d4ed8);
}

.structure-tree__input {
  width: 100%;
  padding: 5px 8px;
  font-size: 0.8125rem;
  border: 1px solid var(--color-neutral-500, #6b7280);
  border-radius: 4px;
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-100, #f3f4f6);
  margin-bottom: 8px;
  box-sizing: border-box;
}

.structure-tree__input:focus {
  outline: 2px solid var(--color-primary-500, #3b82f6);
  outline-offset: -1px;
}
</style>
