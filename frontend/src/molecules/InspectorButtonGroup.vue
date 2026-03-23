<template>
  <div class="inspector-btn-group">
    <label v-if="label" class="inspector-btn-group__label">{{ label }}</label>
    <div class="inspector-btn-group__buttons" role="group">
      <button
        v-for="opt in options"
        :key="opt.value"
        type="button"
        class="inspector-btn-group__btn"
        :class="{ 'inspector-btn-group__btn--active': isActive(opt.value) }"
        :aria-pressed="isActive(opt.value)"
        :title="opt.label"
        @click="onToggle(opt.value)"
      >
        {{ opt.icon }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface ButtonGroupOption {
  value: string
  icon: string
  label: string
}

const props = withDefaults(
  defineProps<{
    label?: string
    options: ButtonGroupOption[]
    modelValue: string
    multiple?: boolean
  }>(),
  { label: '', multiple: false },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

function isActive(value: string): boolean {
  if (props.multiple) {
    const values = props.modelValue.split(' ').filter(Boolean)
    return values.includes(value)
  }
  return props.modelValue === value
}

function onToggle(value: string) {
  if (props.multiple) {
    const values = props.modelValue.split(' ').filter(Boolean)
    const idx = values.indexOf(value)
    if (idx >= 0) {
      values.splice(idx, 1)
    } else {
      values.push(value)
    }
    emit('update:modelValue', values.length > 0 ? values.join(' ') : 'none')
  } else {
    emit('update:modelValue', value)
  }
}
</script>

<style scoped>
.inspector-btn-group {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.25rem 0;
}

.inspector-btn-group__label {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  user-select: none;
}

.inspector-btn-group__buttons {
  display: flex;
  gap: 0;
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  overflow: hidden;
}

.inspector-btn-group__btn {
  flex: 1;
  padding: 0.25rem 0.375rem;
  font-size: 0.75rem;
  background: var(--color-neutral-800, #1f2937);
  color: var(--color-neutral-300, #d1d5db);
  border: none;
  border-right: 1px solid var(--color-neutral-600, #4b5563);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  text-align: center;
  line-height: 1.2;
}

.inspector-btn-group__btn:last-child {
  border-right: none;
}

.inspector-btn-group__btn:hover {
  background: var(--color-neutral-700, #374151);
}

.inspector-btn-group__btn--active {
  background: var(--color-primary-600, #4f46e5);
  color: #fff;
}

.inspector-btn-group__btn--active:hover {
  background: var(--color-primary-500, #6366f1);
}
</style>
