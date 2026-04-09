<template>
  <div class="border-editor">
    <!-- Uniform toggle -->
    <div class="border-editor__toggle">
      <label class="border-editor__toggle-label">
        <input type="checkbox" :checked="modelValue.uniform" @change="onToggleUniform" />
        Todos os lados
      </label>
    </div>

    <!-- Width section -->
    <div class="border-editor__group">
      <span class="border-editor__group-title">Espessura (px)</span>
      <div v-if="modelValue.uniform" class="border-editor__row">
        <InspectorInput
          label="Todos"
          type="number"
          :min="0"
          :model-value="modelValue.top.width"
          @update:model-value="onUniformWidth($event as number)"
        />
      </div>
      <div v-else class="border-editor__grid">
        <InspectorInput
          label="Topo"
          type="number"
          :min="0"
          :model-value="modelValue.top.width"
          @update:model-value="onSideChange('top', 'width', $event as number)"
        />
        <InspectorInput
          label="Direita"
          type="number"
          :min="0"
          :model-value="modelValue.right.width"
          @update:model-value="onSideChange('right', 'width', $event as number)"
        />
        <InspectorInput
          label="Baixo"
          type="number"
          :min="0"
          :model-value="modelValue.bottom.width"
          @update:model-value="onSideChange('bottom', 'width', $event as number)"
        />
        <InspectorInput
          label="Esquerda"
          type="number"
          :min="0"
          :model-value="modelValue.left.width"
          @update:model-value="onSideChange('left', 'width', $event as number)"
        />
      </div>
    </div>

    <!-- Color section -->
    <div class="border-editor__group">
      <span class="border-editor__group-title">Cor</span>
      <div v-if="modelValue.uniform" class="border-editor__row">
        <InspectorColorPicker
          label="Todos"
          :model-value="modelValue.top.color"
          @update:model-value="onUniformColor($event)"
        />
      </div>
      <div v-else class="border-editor__grid">
        <InspectorColorPicker
          label="Topo"
          :model-value="modelValue.top.color"
          @update:model-value="onSideChange('top', 'color', $event)"
        />
        <InspectorColorPicker
          label="Direita"
          :model-value="modelValue.right.color"
          @update:model-value="onSideChange('right', 'color', $event)"
        />
        <InspectorColorPicker
          label="Baixo"
          :model-value="modelValue.bottom.color"
          @update:model-value="onSideChange('bottom', 'color', $event)"
        />
        <InspectorColorPicker
          label="Esquerda"
          :model-value="modelValue.left.color"
          @update:model-value="onSideChange('left', 'color', $event)"
        />
      </div>
    </div>

    <!-- Style section -->
    <div class="border-editor__group">
      <span class="border-editor__group-title">Estilo</span>
      <div v-if="modelValue.uniform" class="border-editor__row">
        <InspectorSelect
          label="Todos"
          :model-value="modelValue.top.style"
          :options="BORDER_STYLE_OPTIONS"
          @update:model-value="onUniformStyle($event)"
        />
      </div>
      <div v-else class="border-editor__grid">
        <InspectorSelect
          label="Topo"
          :model-value="modelValue.top.style"
          :options="BORDER_STYLE_OPTIONS"
          @update:model-value="onSideChange('top', 'style', $event)"
        />
        <InspectorSelect
          label="Direita"
          :model-value="modelValue.right.style"
          :options="BORDER_STYLE_OPTIONS"
          @update:model-value="onSideChange('right', 'style', $event)"
        />
        <InspectorSelect
          label="Baixo"
          :model-value="modelValue.bottom.style"
          :options="BORDER_STYLE_OPTIONS"
          @update:model-value="onSideChange('bottom', 'style', $event)"
        />
        <InspectorSelect
          label="Esquerda"
          :model-value="modelValue.left.style"
          :options="BORDER_STYLE_OPTIONS"
          @update:model-value="onSideChange('left', 'style', $event)"
        />
      </div>
    </div>

    <!-- Radius section -->
    <div class="border-editor__group">
      <span class="border-editor__group-title">Raio (px)</span>
      <div class="border-editor__grid">
        <InspectorInput
          label="Sup-Esq"
          type="number"
          :min="0"
          :model-value="modelValue.radius.topLeft"
          @update:model-value="onRadiusChange('topLeft', $event as number)"
        />
        <InspectorInput
          label="Sup-Dir"
          type="number"
          :min="0"
          :model-value="modelValue.radius.topRight"
          @update:model-value="onRadiusChange('topRight', $event as number)"
        />
        <InspectorInput
          label="Inf-Dir"
          type="number"
          :min="0"
          :model-value="modelValue.radius.bottomRight"
          @update:model-value="onRadiusChange('bottomRight', $event as number)"
        />
        <InspectorInput
          label="Inf-Esq"
          type="number"
          :min="0"
          :model-value="modelValue.radius.bottomLeft"
          @update:model-value="onRadiusChange('bottomLeft', $event as number)"
        />
      </div>
    </div>

    <!-- Visual preview -->
    <div class="border-editor__preview-wrap">
      <span class="border-editor__group-title">Preview</span>
      <div class="border-editor__preview" :style="previewStyle"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import InspectorInput from './InspectorInput.vue'
import InspectorColorPicker from './InspectorColorPicker.vue'
import InspectorSelect from './InspectorSelect.vue'
import type { BorderConfig, BorderSideConfig, BorderRadiusConfig } from '../types/template.types'
import { BORDER_STYLE_OPTIONS } from '../types/template.types'

type Side = 'top' | 'right' | 'bottom' | 'left'
type SideProp = keyof BorderSideConfig
type RadiusCorner = keyof BorderRadiusConfig

const props = defineProps<{
  modelValue: BorderConfig
}>()

const emit = defineEmits<{
  'update:modelValue': [value: BorderConfig]
}>()

function clone(): BorderConfig {
  const v = props.modelValue
  return {
    top: { ...v.top },
    right: { ...v.right },
    bottom: { ...v.bottom },
    left: { ...v.left },
    radius: { ...v.radius },
    uniform: v.uniform,
  }
}

function onToggleUniform() {
  const next = clone()
  next.uniform = !next.uniform
  if (next.uniform) {
    next.right = { ...next.top }
    next.bottom = { ...next.top }
    next.left = { ...next.top }
  }
  emit('update:modelValue', next)
}

function onSideChange(side: Side, prop: SideProp, value: string | number) {
  const next = clone()
  ;(next[side] as Record<string, unknown>)[prop] = value
  emit('update:modelValue', next)
}

function onUniformWidth(value: number) {
  const next = clone()
  next.top.width = value
  next.right.width = value
  next.bottom.width = value
  next.left.width = value
  emit('update:modelValue', next)
}

function onUniformColor(value: string) {
  const next = clone()
  next.top.color = value
  next.right.color = value
  next.bottom.color = value
  next.left.color = value
  emit('update:modelValue', next)
}

function onUniformStyle(value: string) {
  const next = clone()
  next.top.style = value as BorderSideConfig['style']
  next.right.style = value as BorderSideConfig['style']
  next.bottom.style = value as BorderSideConfig['style']
  next.left.style = value as BorderSideConfig['style']
  emit('update:modelValue', next)
}

function onRadiusChange(corner: RadiusCorner, value: number) {
  const next = clone()
  next.radius[corner] = value
  emit('update:modelValue', next)
}

const previewStyle = computed(() => {
  const v = props.modelValue
  return {
    width: '60px',
    height: '60px',
    borderTop: `${v.top.width}px ${v.top.style} ${v.top.color}`,
    borderRight: `${v.right.width}px ${v.right.style} ${v.right.color}`,
    borderBottom: `${v.bottom.width}px ${v.bottom.style} ${v.bottom.color}`,
    borderLeft: `${v.left.width}px ${v.left.style} ${v.left.color}`,
    borderRadius: `${v.radius.topLeft}px ${v.radius.topRight}px ${v.radius.bottomRight}px ${v.radius.bottomLeft}px`,
    background: 'var(--color-neutral-700, #374151)',
    boxSizing: 'border-box' as const,
  }
})
</script>

<style scoped>
.border-editor {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.border-editor__toggle {
  padding: 0.25rem 0;
}

.border-editor__toggle-label {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  color: var(--color-neutral-300, #d1d5db);
  cursor: pointer;
  user-select: none;
}

.border-editor__toggle-label input[type='checkbox'] {
  accent-color: var(--color-primary-500, #6366f1);
}

.border-editor__group {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.border-editor__group-title {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  user-select: none;
}

.border-editor__row {
  display: flex;
  flex-direction: column;
}

.border-editor__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.25rem;
}

.border-editor__preview-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  align-items: flex-start;
}

.border-editor__preview {
  margin-top: 0.25rem;
}
</style>
