<template>
  <div class="layer-panel">
    <!-- Toolbar -->
    <div class="layer-panel__toolbar">
      <button
        type="button"
        title="Bring to Front"
        aria-label="Trazer para frente"
        :disabled="!selectedId"
        @click="bringToFront(selectedId!)"
      >
        ⬆⬆
      </button>
      <button
        type="button"
        title="Move Up"
        aria-label="Mover para cima"
        :disabled="!selectedId"
        @click="moveLayerUp(selectedId!)"
      >
        ⬆
      </button>
      <button
        type="button"
        title="Move Down"
        aria-label="Mover para baixo"
        :disabled="!selectedId"
        @click="moveLayerDown(selectedId!)"
      >
        ⬇
      </button>
      <button
        type="button"
        title="Send to Back"
        aria-label="Enviar para trás"
        :disabled="!selectedId"
        @click="sendToBack(selectedId!)"
      >
        ⬇⬇
      </button>
      <span class="layer-panel__separator" />
      <button
        type="button"
        title="Group"
        aria-label="Agrupar selecionados"
        :disabled="multiSelection.size < 2"
        @click="onGroup"
      >
        G
      </button>
      <button
        type="button"
        title="Ungroup"
        aria-label="Desagrupar"
        :disabled="!canUngroup"
        @click="onUngroup"
      >
        U
      </button>
    </div>

    <!-- Layer list -->
    <div
      class="layer-panel__list"
      role="listbox"
      aria-label="Camadas do template"
      @keydown="onListKeydown"
    >
      <div
        v-for="(layer, idx) in orderedLayers"
        :key="layer.id"
        class="layer-panel__item"
        :class="{
          'layer-panel__item--selected': layer.id === selectedId,
          'layer-panel__item--group': layer.isGroup,
        }"
        role="option"
        :aria-selected="layer.id === selectedId"
        :tabindex="layer.id === selectedId ? 0 : -1"
        :data-layer-index="idx"
        @click="selectLayer(layer.id)"
        @dblclick="onToggleGroupExpand(layer)"
      >
        <span class="layer-panel__item-icon">{{ typeIcon(layer.type) }}</span>
        <span class="layer-panel__item-name">{{ layer.name }}</span>
        <!-- Story 33.10: visibility toggle -->
        <button
          type="button"
          class="layer-panel__item-action"
          :class="{ 'layer-panel__item-action--off': isHidden(layer.id) }"
          :title="isHidden(layer.id) ? 'Mostrar' : 'Ocultar'"
          :aria-label="isHidden(layer.id) ? `Mostrar ${layer.name}` : `Ocultar ${layer.name}`"
          @click.stop="toggleVisibility(layer.id)"
        >
          {{ isHidden(layer.id) ? '◻' : '◼' }}
        </button>
        <!-- Story 33.10: lock toggle -->
        <button
          type="button"
          class="layer-panel__item-action"
          :class="{ 'layer-panel__item-action--locked': isLocked(layer.id) }"
          :title="isLocked(layer.id) ? 'Desbloquear' : 'Bloquear'"
          :aria-label="isLocked(layer.id) ? `Desbloquear ${layer.name}` : `Bloquear ${layer.name}`"
          @click.stop="toggleLock(layer.id)"
        >
          {{ isLocked(layer.id) ? '🔒' : '🔓' }}
        </button>
        <span class="layer-panel__item-z">z:{{ layer.zIndex }}</span>
      </div>
    </div>

    <!-- aria-live region for announcements -->
    <div aria-live="polite" class="layer-panel__sr-only">{{ announcement }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useLayerOrder } from '@/composables/useLayerOrder'
import { useGrouping } from '@/composables/useGrouping'
import { useEditorStore } from '@/stores/editorStore'
import { useCanvasInteraction } from '@/composables/useCanvasInteraction'
import { useTemplateStore } from '@/stores/templateStore'
import { useGenerationStore } from '@/stores/generation'

const editorStore = useEditorStore()
const templateStore = useTemplateStore()
const generationStore = useGenerationStore()
const { multiSelection } = useCanvasInteraction()
const { orderedLayers, bringToFront, sendToBack, moveLayerUp, moveLayerDown, selectLayer } =
  useLayerOrder()
const { createGroup, ungroupNode } = useGrouping()

const announcement = ref('')
const selectedId = computed(() => editorStore.selectedElementId)

const canUngroup = computed(() => {
  if (!selectedId.value) return false
  const node = templateStore.getNodeById(selectedId.value)
  return node?.properties['isGroup'] === true
})

// Story 33.10: visibility and lock state helpers
function isHidden(layerId: string): boolean {
  const node = templateStore.getNodeById(layerId)
  if (!node) return false
  const vis = node.properties['visibility']
  if (vis && typeof vis === 'object' && 'mode' in (vis as Record<string, unknown>)) {
    return (vis as { mode: string }).mode === 'hidden'
  }
  return vis === false
}

function isLocked(layerId: string): boolean {
  const node = templateStore.getNodeById(layerId)
  return Boolean(node?.properties['locked'])
}

function toggleVisibility(layerId: string) {
  const hidden = isHidden(layerId)
  if (hidden) {
    templateStore.updateNodeProperty(layerId, 'visibility', { mode: 'always' })
  } else {
    templateStore.updateNodeProperty(layerId, 'visibility', { mode: 'hidden' })
  }
  generationStore.patchNodeVisibility(layerId, hidden)
  announcement.value = hidden ? 'Elemento visível' : 'Elemento oculto'
}

function toggleLock(layerId: string) {
  const locked = isLocked(layerId)
  templateStore.updateNodeProperty(layerId, 'locked', !locked)
  announcement.value = locked ? 'Elemento desbloqueado' : 'Elemento bloqueado'
}

function typeIcon(type: string): string {
  const icons: Record<string, string> = {
    field: 'T',
    section: '□',
    table: '▦',
    chart: '📊',
    image: '🖼',
  }
  return icons[type] ?? '◇'
}

function onGroup() {
  const ids = [...multiSelection.value]
  const group = createGroup(ids)
  if (group) {
    editorStore.selectElement(group.id)
    announcement.value = `${ids.length} elementos agrupados`
  }
}

function onUngroup() {
  if (!selectedId.value) return
  const ok = ungroupNode(selectedId.value)
  if (ok) {
    announcement.value = 'Grupo desfeito'
    editorStore.selectElement(null)
  }
}

function onToggleGroupExpand(_layer: { isGroup: boolean }) {
  // Reserved for group collapse/expand
}

function onListKeydown(e: KeyboardEvent) {
  if (!selectedId.value) return
  const idx = orderedLayers.value.findIndex((l) => l.id === selectedId.value)
  if (idx < 0) return

  if (e.key === 'ArrowUp' && !e.altKey) {
    e.preventDefault()
    const prev = idx > 0 ? orderedLayers.value[idx - 1] : null
    if (prev) selectLayer(prev.id)
  } else if (e.key === 'ArrowDown' && !e.altKey) {
    e.preventDefault()
    const next = idx < orderedLayers.value.length - 1 ? orderedLayers.value[idx + 1] : null
    if (next) selectLayer(next.id)
  } else if (e.key === 'ArrowUp' && e.altKey) {
    e.preventDefault()
    moveLayerUp(selectedId.value)
    const layer = orderedLayers.value.find((l) => l.id === selectedId.value)
    announcement.value = `${layer?.name ?? 'Elemento'} movido para cima`
  } else if (e.key === 'ArrowDown' && e.altKey) {
    e.preventDefault()
    moveLayerDown(selectedId.value)
    const layer = orderedLayers.value.find((l) => l.id === selectedId.value)
    announcement.value = `${layer?.name ?? 'Elemento'} movido para baixo`
  }
}
</script>

<style scoped>
.layer-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.layer-panel__toolbar {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.5rem;
  border-bottom: 1px solid var(--color-neutral-700, #374151);
  flex-shrink: 0;
}

.layer-panel__toolbar button {
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-200, #e5e7eb);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  font-size: 0.625rem;
  cursor: pointer;
}

.layer-panel__toolbar button:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.layer-panel__toolbar button:hover:not(:disabled) {
  background: var(--color-neutral-600, #4b5563);
}

.layer-panel__separator {
  width: 1px;
  height: 1rem;
  background: var(--color-neutral-600, #4b5563);
  margin: 0 0.25rem;
}

.layer-panel__list {
  flex: 1;
  overflow-y: auto;
  padding: 0.25rem 0;
}

.layer-panel__item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.5rem;
  cursor: pointer;
  user-select: none;
  font-size: 0.75rem;
  color: var(--color-neutral-200, #e5e7eb);
  transition: background 0.1s;
}

.layer-panel__item:hover {
  background: var(--color-neutral-700, #374151);
}

.layer-panel__item--selected {
  background: var(--color-primary-900, #312e81);
  border-left: 2px solid var(--color-primary-500, #6366f1);
}

.layer-panel__item--group {
  font-weight: 600;
}

.layer-panel__item-icon {
  font-size: 0.6875rem;
  width: 1rem;
  text-align: center;
  flex-shrink: 0;
}

.layer-panel__item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.layer-panel__item-action {
  background: none;
  border: none;
  color: var(--color-neutral-400, #9ca3af);
  cursor: pointer;
  font-size: 0.625rem;
  padding: 0 0.125rem;
  line-height: 1;
  flex-shrink: 0;
  border-radius: 0.125rem;
  transition: color 0.15s;
}

.layer-panel__item-action:hover {
  color: var(--color-neutral-100, #f3f4f6);
}

.layer-panel__item-action--off {
  opacity: 0.4;
}

.layer-panel__item-action--locked {
  color: var(--color-warning-400, #fbbf24);
}

.layer-panel__item-z {
  font-size: 0.5625rem;
  color: var(--color-neutral-500, #525252);
  flex-shrink: 0;
}

.layer-panel__sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}
</style>
