<template>
  <label class="color-picker">
    <span class="color-picker__label">{{ label }}</span>
    <div class="color-picker__controls">
      <input :value="modelValue" type="color" @input="onInput" />
      <span class="color-picker__swatch" :style="{ backgroundColor: modelValue }" />
      <code>{{ modelValue }}</code>
    </div>
  </label>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string
  label?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

function onInput(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.value)
}
</script>

<style scoped>
.color-picker {
  display: grid;
  gap: 0.35rem;
}

.color-picker__label {
  font-size: 0.8125rem;
  color: var(--color-neutral-700);
}

.color-picker__controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.color-picker__swatch {
  width: 1rem;
  height: 1rem;
  border-radius: 0.2rem;
  border: 1px solid var(--color-neutral-200);
}

code {
  font-size: 0.75rem;
  color: var(--color-neutral-700);
}
</style>
