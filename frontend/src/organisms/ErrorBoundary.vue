<template>
  <slot v-if="!error" />
  <div v-else class="error-boundary" role="alert">
    <div class="error-boundary__card">
      <h2 class="error-boundary__title">Algo deu errado</h2>
      <p class="error-boundary__message">Ocorreu um erro inesperado. Tente recarregar a pagina.</p>
      <pre v-if="isDev" class="error-boundary__stack">{{ errorDetails }}</pre>
      <div class="error-boundary__actions">
        <button class="error-boundary__btn" @click="recover">Recarregar pagina</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onErrorCaptured, computed } from 'vue'

const error = ref<Error | null>(null)
const isDev = import.meta.env.DEV

const errorDetails = computed(() => {
  if (!error.value) return ''
  return `${error.value.name}: ${error.value.message}\n\n${error.value.stack ?? ''}`
})

onErrorCaptured((err: Error, _instance, info) => {
  console.error('[ErrorBoundary] Captured error:', err, 'Info:', info)
  error.value = err
  // Returning false prevents the error from propagating further
  return false
})

function recover() {
  window.location.reload()
}

defineExpose({ error, recover })
</script>

<style scoped>
.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--color-neutral-50, #fafafa);
  padding: 2rem;
}

.error-boundary__card {
  background: white;
  border: 1px solid var(--color-neutral-200, #e5e5e5);
  border-radius: 0.75rem;
  padding: 2rem;
  max-width: 32rem;
  width: 100%;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  text-align: center;
}

.error-boundary__title {
  margin: 0 0 0.75rem;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-error-600, #dc2626);
}

.error-boundary__message {
  margin: 0 0 1.5rem;
  font-size: 0.9375rem;
  color: var(--color-neutral-600, #525252);
  line-height: 1.5;
}

.error-boundary__stack {
  text-align: left;
  font-size: 0.75rem;
  background: var(--color-neutral-900, #171717);
  color: #f5f5f5;
  padding: 1rem;
  border-radius: 0.5rem;
  overflow-x: auto;
  max-height: 16rem;
  margin: 0 0 1.5rem;
  white-space: pre-wrap;
  word-break: break-all;
}

.error-boundary__actions {
  display: flex;
  justify-content: center;
}

.error-boundary__btn {
  padding: 0.5rem 1.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: white;
  background: var(--color-primary-600, #2563eb);
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: background 0.15s;
}

.error-boundary__btn:hover {
  background: var(--color-primary-700, #1d4ed8);
}
</style>
