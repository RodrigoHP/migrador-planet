<template>
  <div class="inspector-checkbox">
    <label class="inspector-checkbox__wrap">
      <input
        class="inspector-checkbox__input"
        type="checkbox"
        :checked="modelValue ?? false"
        @change="onChange"
      />
      <span class="inspector-checkbox__label">{{ label }}</span>
    </label>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    modelValue: boolean | undefined | null
  }>(),
  {},
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

function onChange(e: Event) {
  emit('update:modelValue', (e.target as HTMLInputElement).checked)
}
</script>

<style scoped>
.inspector-checkbox {
  padding: 0.25rem 0;
}

.inspector-checkbox__wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  user-select: none;
}

.inspector-checkbox__input {
  width: 0.875rem;
  height: 0.875rem;
  accent-color: var(--color-primary-500, #6366f1);
  cursor: pointer;
  flex-shrink: 0;
}

.inspector-checkbox__label {
  font-size: 0.8125rem;
  color: var(--color-neutral-100, #f3f4f6);
}
</style>
