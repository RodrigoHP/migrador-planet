<template>
  <div class="inspector-select">
    <label class="inspector-select__label">{{ label }}</label>
    <select class="inspector-select__field" :value="modelValue" @change="onChange">
      <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
      <option
        v-for="opt in options"
        :key="typeof opt === 'string' ? opt : opt.value"
        :value="typeof opt === 'string' ? opt : opt.value"
      >
        {{ typeof opt === 'string' ? opt : opt.label }}
      </option>
    </select>
  </div>
</template>

<script setup lang="ts">
export interface SelectOption {
  value: string
  label: string
}

withDefaults(
  defineProps<{
    label: string
    modelValue: string | undefined | null
    options: Array<string | SelectOption>
    placeholder?: string
  }>(),
  { placeholder: '' },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

function onChange(e: Event) {
  emit('update:modelValue', (e.target as HTMLSelectElement).value)
}
</script>

<style scoped>
.inspector-select {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.25rem 0;
}

.inspector-select__label {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  user-select: none;
}

.inspector-select__field {
  width: 100%;
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  color: var(--color-neutral-100, #f3f4f6);
  font-size: 0.8125rem;
  padding: 0.25rem 0.5rem;
  outline: none;
  cursor: pointer;
  transition: border-color 0.15s;
}

.inspector-select__field:focus {
  border-color: var(--color-primary-500, #6366f1);
}
</style>
