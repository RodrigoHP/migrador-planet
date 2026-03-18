<template>
  <Teleport to="body">
    <div
      v-if="visible && ancestorIds.length > 0"
      ref="popupRef"
      class="hierarchy-popup"
      :style="popupStyle"
      data-testid="hierarchy-popup"
      role="menu"
      aria-label="Selecionar nível hierárquico"
      @click.stop
    >
      <div class="hierarchy-popup__header">Selecionar elemento:</div>
      <button
        v-for="(id, idx) in ancestorIds"
        :key="id"
        class="hierarchy-popup__item"
        :style="{ paddingLeft: `${8 + idx * 12}px` }"
        data-testid="hierarchy-item"
        role="menuitem"
        @click="onSelect(id)"
      >
        <span class="hierarchy-popup__icon">{{ nodeIcon(id) }}</span>
        <span class="hierarchy-popup__label">{{ nodeLabel(id) }}</span>
        <span class="hierarchy-popup__type">{{ nodeType(id) }}</span>
      </button>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { useTemplateStore } from '@/stores/templateStore'
import type { NodeType } from '@/types/template.types'

interface Props {
  visible: boolean
  x: number
  y: number
  ancestorIds: string[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'select', elementId: string): void
  (e: 'close'): void
}>()

const templateStore = useTemplateStore()
const popupRef = ref<HTMLElement | null>(null)

// ─── Positioning ──────────────────────────────────────────────────────────────

const popupStyle = computed(() => ({
  position: 'fixed' as const,
  left: `${props.x}px`,
  top: `${props.y}px`,
  zIndex: 9999,
}))

// ─── Node info helpers ────────────────────────────────────────────────────────

const NODE_ICONS: Partial<Record<NodeType, string>> = {
  document: '📄',
  header: '📦',
  footer: '📦',
  flow: '📦',
  section: '◻',
  table: '⊞',
  chart: '📊',
  image: '🖼',
  container: '⬛',
  text: '𝐓',
  field: '{}',
}

function nodeIcon(id: string): string {
  const node = templateStore.getNodeById(id)
  if (!node) return '◻'
  return NODE_ICONS[node.type] ?? '◻'
}

function nodeLabel(id: string): string {
  const node = templateStore.getNodeById(id)
  return node?.name ?? id
}

function nodeType(id: string): string {
  const node = templateStore.getNodeById(id)
  return node?.type ?? ''
}

// ─── Events ───────────────────────────────────────────────────────────────────

function onSelect(elementId: string) {
  emit('select', elementId)
  emit('close')
}

function onClickOutside(event: MouseEvent) {
  if (popupRef.value && !popupRef.value.contains(event.target as Node)) {
    emit('close')
  }
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      document.addEventListener('mousedown', onClickOutside)
    } else {
      document.removeEventListener('mousedown', onClickOutside)
    }
  },
  { immediate: true },
)

onUnmounted(() => {
  document.removeEventListener('mousedown', onClickOutside)
})
</script>

<style scoped>
.hierarchy-popup {
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 6px;
  padding: 4px 0;
  min-width: 180px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  font-size: 0.8125rem;
  color: var(--color-neutral-100, #f3f4f6);
  user-select: none;
}

.hierarchy-popup__header {
  padding: 6px 12px;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid var(--color-neutral-700, #374151);
  margin-bottom: 2px;
}

.hierarchy-popup__item {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 5px 12px;
  background: none;
  border: none;
  color: var(--color-neutral-100, #f3f4f6);
  cursor: pointer;
  text-align: left;
  font-size: 0.8125rem;
  transition: background 0.1s;
}

.hierarchy-popup__item:hover {
  background: var(--color-neutral-700, #374151);
}

.hierarchy-popup__icon {
  flex-shrink: 0;
  font-size: 0.75rem;
  width: 16px;
  text-align: center;
}

.hierarchy-popup__label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hierarchy-popup__type {
  font-size: 0.6875rem;
  color: var(--color-neutral-500, #6b7280);
  flex-shrink: 0;
}
</style>
