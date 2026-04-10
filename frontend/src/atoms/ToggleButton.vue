<template>
  <button
    type="button"
    class="toggle-button"
    :class="{ 'toggle-button--active': active }"
    :aria-pressed="active"
    :title="label"
    @click="emit('click')"
  >
    <span class="toggle-button__icon">
      <component :is="icon" v-if="typeof icon !== 'string'" :size="14" :stroke-width="2" />
      <template v-else>{{ icon }}</template>
    </span>
    <span class="toggle-button__label">{{ label }}</span>
  </button>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  icon: string | Component
  label: string
  active: boolean
}>()

const emit = defineEmits<{
  (e: 'click'): void
}>()
</script>

<style scoped>
.toggle-button {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.3125rem 0.625rem;
  background: transparent;
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.375rem;
  cursor: pointer;
  color: var(--color-neutral-300, #d1d5db);
  font-size: 0.75rem;
  font-weight: 500;
  transition:
    background 0.15s,
    color 0.15s,
    border-color 0.15s;
  white-space: nowrap;
}

.toggle-button:hover {
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-100, #f3f4f6);
}

.toggle-button--active {
  background: var(--color-primary-600, #2563eb);
  border-color: var(--color-primary-500, #3b82f6);
  color: #fff;
}

.toggle-button--active:hover {
  background: var(--color-primary-700, #1d4ed8);
}

.toggle-button__icon {
  display: inline-flex;
  align-items: center;
  font-size: 0.875rem;
}

.toggle-button__label {
  font-size: 0.75rem;
}
</style>
