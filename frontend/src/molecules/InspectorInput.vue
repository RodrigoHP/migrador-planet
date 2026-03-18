<template>
  <div class="inspector-input">
    <label class="inspector-input__label">{{ label }}</label>
    <div class="inspector-input__wrap">
      <input
        class="inspector-input__field"
        :class="{ 'inspector-input__field--error': hasError }"
        :type="type"
        :min="min"
        :max="max"
        :step="step"
        :placeholder="placeholder"
        :value="modelValue"
        @input="onInput"
        @blur="onBlur"
      />
      <span v-if="hasError && errorMessage" class="inspector-input__tooltip">
        {{ errorMessage }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = withDefaults(
  defineProps<{
    label: string
    modelValue: string | number | null | undefined
    type?: 'text' | 'number'
    min?: number
    max?: number
    step?: number
    placeholder?: string
    required?: boolean
  }>(),
  {
    type: 'text',
    min: undefined,
    max: undefined,
    step: undefined,
    placeholder: '',
    required: false,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
}>()

const touched = ref(false)

const errorMessage = computed(() => {
  if (!touched.value) return ''
  const v = props.modelValue
  if (props.type === 'number') {
    const num = Number(v)
    if (v === '' || v === null || v === undefined) return props.required ? 'Campo obrigatório' : ''
    if (isNaN(num)) return 'Valor inválido'
    if (props.min !== undefined && num < props.min) return `Mínimo: ${props.min}`
    if (props.max !== undefined && num > props.max) return `Máximo: ${props.max}`
  }
  return ''
})

const hasError = computed(() => errorMessage.value !== '')

function onInput(e: Event) {
  const target = e.target as HTMLInputElement
  const raw = target.value
  if (props.type === 'number') {
    const num = parseFloat(raw)
    emit('update:modelValue', isNaN(num) ? raw : num)
  } else {
    emit('update:modelValue', raw)
  }
}

function onBlur() {
  touched.value = true
}
</script>

<style scoped>
.inspector-input {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.25rem 0;
}

.inspector-input__label {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  user-select: none;
}

.inspector-input__wrap {
  position: relative;
}

.inspector-input__field {
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

.inspector-input__field:focus {
  border-color: var(--color-primary-500, #6366f1);
}

.inspector-input__field--error {
  border-color: var(--color-error-500, #ef4444) !important;
}

.inspector-input__tooltip {
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
