<template>
  <button
    class="btn"
    :class="[variantClass, sizeClass]"
    :disabled="disabled || loading"
    :aria-busy="loading ? 'true' : 'false'"
  >
    <span v-if="loading" class="btn__spinner" aria-hidden="true" />
    <slot />
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
    size?: 'sm' | 'md' | 'lg'
    loading?: boolean
    disabled?: boolean
  }>(),
  {
    variant: 'primary',
    size: 'md',
    loading: false,
    disabled: false,
  },
)

const variantClass = computed(() => `btn--${props.variant}`)
const sizeClass = computed(() => `btn--${props.size}`)
</script>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border-radius: 0.5rem;
  border: 1px solid transparent;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 150ms ease, border-color 150ms ease, color 150ms ease;
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn--sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
}

.btn--md {
  padding: 0.5rem 1rem;
  font-size: 0.9375rem;
}

.btn--lg {
  padding: 0.625rem 1.25rem;
  font-size: 1rem;
}

.btn--primary {
  color: #fff;
  background: var(--color-primary-600);
}

.btn--primary:hover:not(:disabled) {
  background: var(--color-primary-700);
}

.btn--secondary {
  color: var(--color-neutral-900);
  background: var(--color-neutral-100);
  border-color: var(--color-neutral-200);
}

.btn--secondary:hover:not(:disabled) {
  background: var(--color-neutral-200);
}

.btn--ghost {
  color: var(--color-primary-600);
  background: transparent;
  border-color: var(--color-primary-600);
}

.btn--ghost:hover:not(:disabled) {
  background: #eff6ff;
}

.btn--danger {
  color: #fff;
  background: var(--color-error-600);
}

.btn--danger:hover:not(:disabled) {
  filter: brightness(0.92);
}

.btn__spinner {
  width: 0.875rem;
  height: 0.875rem;
  border-radius: 9999px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
