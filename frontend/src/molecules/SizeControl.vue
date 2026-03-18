<template>
  <div class="size-control">
    <span class="size-control__title">{{ title }}</span>
    <div class="size-control__row">
      <div class="size-control__item">
        <label class="size-control__label">W</label>
        <input
          class="size-control__input"
          :class="{ 'size-control__input--error': wError }"
          type="number"
          :min="minWidth ?? 0"
          :value="width"
          @input="onWidthInput"
          @blur="wTouched = true"
        />
        <span v-if="wError && wTouched" class="size-control__tooltip">{{ wError }}</span>
      </div>
      <div class="size-control__item">
        <label class="size-control__label">H</label>
        <input
          class="size-control__input"
          :class="{ 'size-control__input--error': hError }"
          type="number"
          :min="0"
          :value="height"
          @input="onHeightInput"
          @blur="hTouched = true"
        />
        <span v-if="hError && hTouched" class="size-control__tooltip">{{ hError }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = withDefaults(
  defineProps<{
    title?: string
    width: number | undefined | null
    height: number | undefined | null
    minWidth?: number
  }>(),
  { title: 'Tamanho', minWidth: 0 },
)

const emit = defineEmits<{
  'update:width': [value: number]
  'update:height': [value: number]
}>()

const wTouched = ref(false)
const hTouched = ref(false)

const wError = computed(() => {
  if (!wTouched.value) return ''
  const v = Number(props.width)
  if (isNaN(v)) return 'Inválido'
  const min = props.minWidth ?? 0
  if (v < min) return `Mínimo: ${min}`
  return ''
})

const hError = computed(() => {
  if (!hTouched.value) return ''
  const v = Number(props.height)
  if (isNaN(v)) return 'Inválido'
  if (v < 0) return 'Mínimo: 0'
  return ''
})

function onWidthInput(e: Event) {
  const v = parseFloat((e.target as HTMLInputElement).value)
  if (!isNaN(v)) emit('update:width', v)
}

function onHeightInput(e: Event) {
  const v = parseFloat((e.target as HTMLInputElement).value)
  if (!isNaN(v)) emit('update:height', v)
}
</script>

<style scoped>
.size-control {
  padding: 0.25rem 0;
}

.size-control__title {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  user-select: none;
  display: block;
  margin-bottom: 0.25rem;
}

.size-control__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}

.size-control__item {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.size-control__label {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
}

.size-control__input {
  width: 100%;
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  color: var(--color-neutral-100, #f3f4f6);
  font-size: 0.8125rem;
  padding: 0.25rem 0.5rem;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
}

.size-control__input:focus {
  border-color: var(--color-primary-500, #6366f1);
}

.size-control__input--error {
  border-color: var(--color-error-500, #ef4444) !important;
}

.size-control__tooltip {
  position: absolute;
  top: calc(100% + 0.25rem);
  left: 0;
  z-index: 10;
  background: var(--color-error-600, #dc2626);
  color: #fff;
  font-size: 0.6875rem;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  white-space: nowrap;
  pointer-events: none;
}
</style>
