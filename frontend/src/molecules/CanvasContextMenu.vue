<template>
  <Teleport to="body">
    <div
      v-if="visible"
      ref="menuRef"
      class="canvas-context-menu"
      :style="{ top: `${y}px`, left: `${x}px` }"
      role="menu"
      :aria-label="'Menu de ações do elemento'"
      data-testid="canvas-context-menu"
      @click.stop
      @keydown.escape="$emit('close')"
    >
      <button
        class="canvas-context-menu__item"
        role="menuitem"
        data-testid="ctx-map-field"
        @click="$emit('map-field')"
      >
        🔗 Mapear Campo
      </button>
      <button
        class="canvas-context-menu__item"
        role="menuitem"
        data-testid="ctx-convert-table"
        @click="$emit('convert-table')"
      >
        📋 Converter para Tabela
      </button>
      <button
        class="canvas-context-menu__item"
        role="menuitem"
        data-testid="ctx-mark-static"
        @click="$emit('mark-static')"
      >
        🔤 Marcar como Texto Estático
      </button>
      <hr class="canvas-context-menu__divider" />
      <button
        class="canvas-context-menu__item canvas-context-menu__item--danger"
        role="menuitem"
        data-testid="ctx-remove"
        @click="$emit('remove')"
      >
        <span>🗑 Remover Elemento</span>
        <kbd class="canvas-context-menu__kbd">Del</kbd>
      </button>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

const props = defineProps<{
  visible: boolean
  x: number
  y: number
}>()

defineEmits<{
  close: []
  'map-field': []
  'convert-table': []
  'mark-static': []
  remove: []
}>()

const menuRef = ref<HTMLElement | null>(null)

// Focus the menu when it opens for keyboard accessibility
watch(
  () => props.visible,
  async (val) => {
    if (val) {
      await nextTick()
      menuRef.value?.focus()
    }
  },
)
</script>

<style scoped>
.canvas-context-menu {
  position: fixed;
  z-index: 9999;
  min-width: 180px;
  background: var(--color-bg-elevated, #2a2a3e);
  border: 1px solid var(--color-border, #3b3b52);
  border-radius: 6px;
  padding: 4px 0;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  outline: none;
}

.canvas-context-menu__item {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 6px 12px;
  background: none;
  border: none;
  text-align: left;
  font-size: 12px;
  color: var(--color-text-primary, #e5e7eb);
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.1s;
}

.canvas-context-menu__item:hover,
.canvas-context-menu__item:focus {
  background: var(--color-bg-hover, #3a3a52);
  outline: none;
}

.canvas-context-menu__item--danger {
  color: var(--color-danger, #ef4444);
}

.canvas-context-menu__divider {
  margin: 4px 0;
  border: none;
  border-top: 1px solid var(--color-border, #3b3b52);
}

.canvas-context-menu__kbd {
  margin-left: auto;
  padding: 1px 5px;
  border: 1px solid var(--color-border, #3b3b52);
  border-radius: 3px;
  background: var(--color-bg-base, #1e1e2e);
  font-size: 10px;
  font-family: monospace;
  color: var(--color-text-muted, #9ca3af);
  line-height: 1.4;
}
</style>
