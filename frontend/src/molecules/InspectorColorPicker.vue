<template>
  <div class="inspector-color-picker">
    <label class="inspector-color-picker__label">{{ label }}</label>

    <!-- Main row: swatch + hex display + preset buttons -->
    <div class="inspector-color-picker__wrap">
      <input
        class="inspector-color-picker__swatch"
        type="color"
        :value="currentHex"
        @input="onColorInput"
      />
      <span class="inspector-color-picker__hex">{{ displayValue }}</span>

      <!-- Preset buttons: Transparent / Inherit -->
      <button
        v-if="showPresets"
        class="inspector-color-picker__preset"
        type="button"
        aria-label="Definir como transparente"
        :class="{ 'inspector-color-picker__preset--active': modelValue === 'transparent' }"
        @click="onPreset('transparent')"
      >
        T
      </button>
      <button
        v-if="showPresets"
        class="inspector-color-picker__preset"
        type="button"
        aria-label="Herdar cor do elemento pai"
        :class="{ 'inspector-color-picker__preset--active': modelValue === 'inherit' }"
        @click="onPreset('inherit')"
      >
        H
      </button>
    </div>

    <!-- Opacity slider -->
    <div v-if="enableAlpha && !isSpecialValue" class="inspector-color-picker__opacity">
      <label class="inspector-color-picker__opacity-label">Opacidade</label>
      <input
        type="range"
        min="0"
        max="100"
        :value="currentOpacity"
        class="inspector-color-picker__opacity-slider"
        aria-label="Opacidade"
        :aria-valuetext="`${currentOpacity} porcento`"
        @input="onOpacityInput"
      />
      <span class="inspector-color-picker__opacity-value">{{ currentOpacity }}%</span>
    </div>

    <!-- Document Colors palette -->
    <div
      v-if="documentColors.length > 0"
      class="inspector-color-picker__palette"
      role="listbox"
      aria-label="Cores do documento"
    >
      <span class="inspector-color-picker__palette-title">Documento</span>
      <div class="inspector-color-picker__swatches">
        <button
          v-for="color in documentColors"
          :key="'doc-' + color"
          type="button"
          class="inspector-color-picker__swatch-btn"
          role="option"
          :aria-label="`Cor ${color}`"
          :aria-selected="modelValue === color"
          :style="{ backgroundColor: color }"
          @click="onSwatchClick(color)"
        />
      </div>
    </div>

    <!-- Recent Colors -->
    <div
      v-if="recentColorsList.length > 0"
      class="inspector-color-picker__palette"
      role="listbox"
      aria-label="Cores recentes"
    >
      <span class="inspector-color-picker__palette-title">Recentes</span>
      <div class="inspector-color-picker__swatches">
        <button
          v-for="color in recentColorsList"
          :key="'recent-' + color"
          type="button"
          class="inspector-color-picker__swatch-btn"
          role="option"
          :aria-label="`Cor ${color}`"
          :aria-selected="modelValue === color"
          :style="{ backgroundColor: color }"
          @click="onSwatchClick(color)"
        />
      </div>
    </div>

    <!-- aria-live for color change announcements -->
    <div aria-live="polite" class="inspector-color-picker__sr-only">
      {{ announcement }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { parseColor, hexToRgba } from '@/utils/colorUtils'
import { useRecentColors } from '@/composables/useRecentColors'

const props = withDefaults(
  defineProps<{
    label: string
    modelValue: string | undefined | null
    enableAlpha?: boolean
    showPresets?: boolean
    documentColors?: string[]
  }>(),
  {
    enableAlpha: true,
    showPresets: false,
    documentColors: () => [],
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const { recentColors, addRecentColor } = useRecentColors()
const recentColorsList = computed(() => recentColors.value)

const announcement = ref('')

const isSpecialValue = computed(() => {
  const v = (props.modelValue ?? '').trim()
  return v === 'transparent' || v === 'inherit'
})

const parsed = computed(() => {
  if (!props.modelValue) return null
  return parseColor(props.modelValue)
})

const currentHex = computed(() => parsed.value?.hex ?? '#000000')
const currentOpacity = computed(() => parsed.value?.opacity ?? 100)

const displayValue = computed(() => {
  const v = props.modelValue
  if (!v) return '—'
  if (v === 'transparent' || v === 'inherit') return v
  if (v.startsWith('rgba')) return v
  return v
})

function emitColor(hex: string, opacity: number) {
  let value: string
  if (opacity < 100) {
    value = hexToRgba(hex, opacity)
  } else {
    value = hex
  }
  emit('update:modelValue', value)
  addRecentColor(value)
  announcement.value = `Cor alterada para ${value}`
}

function onColorInput(e: Event) {
  const hex = (e.target as HTMLInputElement).value
  emitColor(hex, currentOpacity.value)
}

function onOpacityInput(e: Event) {
  const opacity = parseInt((e.target as HTMLInputElement).value, 10)
  emitColor(currentHex.value, opacity)
}

function onPreset(value: 'transparent' | 'inherit') {
  emit('update:modelValue', value)
  announcement.value = value === 'transparent' ? 'Cor definida como transparente' : 'Cor definida como herdar'
}

function onSwatchClick(color: string) {
  emit('update:modelValue', color)
  addRecentColor(color)
  announcement.value = `Cor alterada para ${color}`
}
</script>

<style scoped>
.inspector-color-picker {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.25rem 0;
}

.inspector-color-picker__label {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  user-select: none;
}

.inspector-color-picker__wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.inspector-color-picker__swatch {
  width: 2rem;
  height: 1.5rem;
  padding: 0;
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  background: none;
  cursor: pointer;
}

.inspector-color-picker__hex {
  font-size: 0.8125rem;
  color: var(--color-neutral-100, #f3f4f6);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.inspector-color-picker__preset {
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.625rem;
  font-weight: 600;
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-300, #d1d5db);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  cursor: pointer;
  transition: background 0.15s;
}

.inspector-color-picker__preset:hover {
  background: var(--color-neutral-600, #4b5563);
}

.inspector-color-picker__preset--active {
  background: var(--color-primary-700, #4338ca);
  border-color: var(--color-primary-500, #6366f1);
  color: var(--color-neutral-100, #f3f4f6);
}

.inspector-color-picker__opacity {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  margin-top: 0.25rem;
}

.inspector-color-picker__opacity-label {
  font-size: 0.625rem;
  color: var(--color-neutral-400, #9ca3af);
  white-space: nowrap;
  min-width: 3.5rem;
}

.inspector-color-picker__opacity-slider {
  flex: 1;
  height: 0.25rem;
  cursor: pointer;
}

.inspector-color-picker__opacity-value {
  font-size: 0.6875rem;
  color: var(--color-neutral-300, #d1d5db);
  min-width: 2.25rem;
  text-align: right;
}

.inspector-color-picker__palette {
  margin-top: 0.375rem;
}

.inspector-color-picker__palette-title {
  font-size: 0.5625rem;
  color: var(--color-neutral-500, #6b7280);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.inspector-color-picker__swatches {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-top: 0.125rem;
}

.inspector-color-picker__swatch-btn {
  width: 1.25rem;
  height: 1.25rem;
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.1875rem;
  cursor: pointer;
  padding: 0;
  transition: transform 0.1s;
}

.inspector-color-picker__swatch-btn:hover {
  transform: scale(1.15);
}

.inspector-color-picker__swatch-btn[aria-selected='true'] {
  outline: 2px solid var(--color-primary-500, #6366f1);
  outline-offset: 1px;
}

.inspector-color-picker__sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}
</style>
