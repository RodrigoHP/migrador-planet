<template>
  <div class="position-control">
    <span class="position-control__title">{{ title }}</span>
    <div class="position-control__row">
      <div class="position-control__item">
        <label class="position-control__label">X</label>
        <input
          class="position-control__input"
          :class="{ 'position-control__input--error': xError }"
          type="number"
          :min="0"
          :value="x"
          @input="onXInput"
          @blur="xTouched = true"
        />
        <span v-if="xError && xTouched" class="position-control__tooltip">{{ xError }}</span>
      </div>
      <div class="position-control__item">
        <label class="position-control__label">Y</label>
        <input
          class="position-control__input"
          :class="{ 'position-control__input--error': yError }"
          type="number"
          :min="0"
          :value="y"
          @input="onYInput"
          @blur="yTouched = true"
        />
        <span v-if="yError && yTouched" class="position-control__tooltip">{{ yError }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = withDefaults(
  defineProps<{
    title?: string
    x: number | undefined | null
    y: number | undefined | null
  }>(),
  { title: 'Posição' },
)

const emit = defineEmits<{
  'update:x': [value: number]
  'update:y': [value: number]
}>()

const xTouched = ref(false)
const yTouched = ref(false)

const xError = computed(() => {
  if (!xTouched.value) return ''
  const v = Number(props.x)
  if (isNaN(v)) return 'Inválido'
  if (v < 0) return 'Mínimo: 0'
  return ''
})

const yError = computed(() => {
  if (!yTouched.value) return ''
  const v = Number(props.y)
  if (isNaN(v)) return 'Inválido'
  if (v < 0) return 'Mínimo: 0'
  return ''
})

function onXInput(e: Event) {
  const v = parseFloat((e.target as HTMLInputElement).value)
  if (!isNaN(v)) emit('update:x', v)
}

function onYInput(e: Event) {
  const v = parseFloat((e.target as HTMLInputElement).value)
  if (!isNaN(v)) emit('update:y', v)
}
</script>

<style scoped>
.position-control {
  padding: 0.25rem 0;
}

.position-control__title {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  user-select: none;
  display: block;
  margin-bottom: 0.25rem;
}

.position-control__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}

.position-control__item {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.position-control__label {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
}

.position-control__input {
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

.position-control__input:focus {
  border-color: var(--color-primary-500, #6366f1);
}

.position-control__input--error {
  border-color: var(--color-error-500, #ef4444) !important;
}

.position-control__tooltip {
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
