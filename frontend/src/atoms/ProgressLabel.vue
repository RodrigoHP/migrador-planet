<template>
  <div class="progress-label">
    <span class="progress-label__spinner" aria-hidden="true" />
    <span>{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  text: string
}>()
</script>

<style scoped>
.progress-label {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--color-neutral-700);
}

.progress-label__spinner {
  width: 0.875rem;
  height: 0.875rem;
  border-radius: 9999px;
  border: 2px solid var(--color-neutral-200);
  border-top-color: var(--color-primary-600);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
