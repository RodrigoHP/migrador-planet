<template>
  <div class="inspector-color-picker">
    <label class="inspector-color-picker__label">{{ label }}</label>
    <div class="inspector-color-picker__wrap">
      <input
        class="inspector-color-picker__swatch"
        type="color"
        :value="modelValue || '#000000'"
        @input="onInput"
      />
      <span class="inspector-color-picker__hex">{{ modelValue || '—' }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    label: string
    modelValue: string | undefined | null
  }>(),
  {},
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLInputElement).value)
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
}
</style>
