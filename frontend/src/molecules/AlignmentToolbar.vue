<template>
  <div
    v-if="visible"
    class="alignment-toolbar"
    :style="toolbarStyle"
    role="toolbar"
    aria-label="Ferramentas de alinhamento"
  >
    <button
      v-for="btn in buttons"
      :key="btn.action"
      class="alignment-toolbar__btn"
      :class="{ 'alignment-toolbar__btn--disabled': btn.disabled }"
      :aria-label="btn.label"
      :aria-disabled="btn.disabled || undefined"
      :title="btn.disabled ? 'Selecione 3+ elementos' : btn.label"
      :disabled="btn.disabled"
      type="button"
      @click="onAction(btn)"
    >
      {{ btn.icon }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface ToolbarButton {
  action: string
  type: 'align' | 'distribute'
  icon: string
  label: string
  disabled: boolean
}

const props = defineProps<{
  visible: boolean
  position: { x: number; y: number }
  selectedCount: number
}>()

const emit = defineEmits<{
  align: [type: string]
  distribute: [type: string]
}>()

const toolbarStyle = computed(() => ({
  left: `${props.position.x}px`,
  top: `${props.position.y - 36}px`,
}))

const buttons = computed<ToolbarButton[]>(() => {
  const distDisabled = props.selectedCount < 3
  return [
    { action: 'left', type: 'align', icon: '⫷', label: 'Alinhar à esquerda', disabled: false },
    {
      action: 'center-h',
      type: 'align',
      icon: '⫶',
      label: 'Centralizar horizontalmente',
      disabled: false,
    },
    { action: 'right', type: 'align', icon: '⫸', label: 'Alinhar à direita', disabled: false },
    { action: 'top', type: 'align', icon: '⬆', label: 'Alinhar ao topo', disabled: false },
    {
      action: 'middle-v',
      type: 'align',
      icon: '⬌',
      label: 'Centralizar verticalmente',
      disabled: false,
    },
    { action: 'bottom', type: 'align', icon: '⬇', label: 'Alinhar à base', disabled: false },
    {
      action: 'distribute-h',
      type: 'distribute',
      icon: '⫼',
      label: 'Distribuir horizontalmente',
      disabled: distDisabled,
    },
    {
      action: 'distribute-v',
      type: 'distribute',
      icon: '⫽',
      label: 'Distribuir verticalmente',
      disabled: distDisabled,
    },
  ]
})

function onAction(btn: ToolbarButton) {
  if (btn.disabled) return
  if (btn.type === 'align') {
    emit('align', btn.action)
  } else {
    emit('distribute', btn.action)
  }
}
</script>

<style scoped>
.alignment-toolbar {
  position: absolute;
  display: flex;
  gap: 0;
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.375rem;
  padding: 0.125rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 100;
  pointer-events: auto;
}

.alignment-toolbar__btn {
  width: 1.75rem;
  height: 1.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  border-radius: 0.25rem;
  color: var(--color-neutral-200, #e5e7eb);
  font-size: 0.8125rem;
  cursor: pointer;
  transition: background 0.15s;
}

.alignment-toolbar__btn:hover:not(:disabled) {
  background: var(--color-neutral-700, #374151);
}

.alignment-toolbar__btn:focus-visible {
  outline: 2px solid var(--color-primary-500, #6366f1);
  outline-offset: -2px;
}

.alignment-toolbar__btn--disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
</style>
