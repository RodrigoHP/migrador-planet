<template>
  <div
    v-if="visible"
    ref="backdropRef"
    class="evm-backdrop"
    role="dialog"
    aria-modal="true"
    aria-labelledby="evm-title"
    @click.self="onCancel"
  >
    <div class="evm-modal">
      <h3 id="evm-title" class="evm-title">Validação Pré-Exportação</h3>

      <!-- Blocking errors -->
      <section v-if="blockingErrors.length > 0" class="evm-section evm-section--error">
        <h4 class="evm-section__heading">
          <span class="evm-section__icon" aria-hidden="true">✖</span>
          Erros Bloqueantes ({{ blockingErrors.length }})
        </h4>
        <ul class="evm-list">
          <li
            v-for="err in blockingErrors"
            :key="err.code"
            class="evm-list__item evm-list__item--error"
          >
            <span class="evm-list__code">[{{ err.code }}]</span>
            {{ err.message }}
          </li>
        </ul>
        <p class="evm-hint">Corrija os erros acima antes de exportar.</p>
      </section>

      <!-- Warnings -->
      <section v-if="warnings.length > 0" class="evm-section evm-section--warning">
        <h4 class="evm-section__heading">
          <span class="evm-section__icon" aria-hidden="true">⚠</span>
          Avisos ({{ warnings.length }})
        </h4>
        <ul class="evm-list">
          <li v-for="w in warnings" :key="w.code" class="evm-list__item evm-list__item--warning">
            <span class="evm-list__code">[{{ w.code }}]</span>
            {{ w.message }}
          </li>
        </ul>
        <p v-if="blockingErrors.length === 0" class="evm-hint">
          Os avisos não impedem a exportação.
        </p>
      </section>

      <!-- No issues -->
      <section
        v-if="blockingErrors.length === 0 && warnings.length === 0"
        class="evm-section evm-section--success"
      >
        <p class="evm-success-msg">
          <span aria-hidden="true">✔</span> Template validado com sucesso. Pronto para exportar.
        </p>
      </section>

      <!-- Actions -->
      <div class="evm-actions">
        <button
          v-if="blockingErrors.length > 0"
          type="button"
          class="evm-btn evm-btn--primary"
          @click="onCancel"
        >
          Corrigir
        </button>

        <template v-else>
          <button type="button" class="evm-btn evm-btn--secondary" @click="onCancel">
            Cancelar
          </button>
          <button type="button" class="evm-btn evm-btn--export" @click="onConfirm">
            {{ warnings.length > 0 ? 'Exportar mesmo assim' : 'Exportar' }}
          </button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, toRef } from 'vue'
import { useFocusTrap } from '@/composables/useFocusTrap'
import type { PreExportError } from '@/composables/usePreExportValidation'

interface Props {
  visible?: boolean
  blockingErrors?: PreExportError[]
  warnings?: PreExportError[]
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  blockingErrors: () => [],
  warnings: () => [],
})

// Story 40.5 — A11Y-001: Focus trap
const backdropRef = ref<HTMLElement | null>(null)
useFocusTrap(backdropRef, toRef(props, 'visible'))

const emit = defineEmits<{
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()

function onConfirm() {
  emit('confirm')
}

function onCancel() {
  emit('cancel')
}
</script>

<style scoped>
.evm-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100;
}

.evm-modal {
  background: var(--color-neutral-900, #111827);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.5rem;
  padding: 1.5rem;
  min-width: 24rem;
  max-width: 40rem;
  width: 90vw;
  max-height: 80vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  color: var(--color-neutral-100, #f3f4f6);
}

.evm-title {
  margin: 0;
  font-size: 1.0625rem;
  font-weight: 600;
}

/* Sections */
.evm-section {
  border-radius: 0.375rem;
  padding: 0.875rem 1rem;
}

.evm-section--error {
  background: rgba(220, 38, 38, 0.12);
  border: 1px solid rgba(220, 38, 38, 0.4);
}

.evm-section--warning {
  background: rgba(217, 119, 6, 0.12);
  border: 1px solid rgba(217, 119, 6, 0.4);
}

.evm-section--success {
  background: rgba(22, 163, 74, 0.12);
  border: 1px solid rgba(22, 163, 74, 0.4);
}

.evm-section__heading {
  margin: 0 0 0.5rem;
  font-size: 0.9375rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.evm-section--error .evm-section__heading {
  color: #fca5a5;
}

.evm-section--warning .evm-section__heading {
  color: #fcd34d;
}

.evm-section__icon {
  font-size: 0.875rem;
}

/* List */
.evm-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.evm-list__item {
  font-size: 0.8125rem;
  line-height: 1.4;
}

.evm-list__item--error {
  color: #fca5a5;
}

.evm-list__item--warning {
  color: #fcd34d;
}

.evm-list__code {
  font-family: monospace;
  font-size: 0.75rem;
  opacity: 0.75;
  margin-right: 0.25rem;
}

.evm-hint {
  margin: 0.5rem 0 0;
  font-size: 0.8125rem;
  opacity: 0.8;
}

.evm-success-msg {
  margin: 0;
  font-size: 0.9375rem;
  color: #86efac;
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

/* Actions */
.evm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding-top: 0.25rem;
}

.evm-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.875rem;
  border-radius: 0.375rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  border: 1px solid;
  transition: background 0.15s;
}

.evm-btn--primary {
  background: var(--color-neutral-700, #374151);
  border-color: var(--color-neutral-600, #4b5563);
  color: var(--color-neutral-100, #f3f4f6);
}

.evm-btn--primary:hover {
  background: var(--color-neutral-600, #4b5563);
}

.evm-btn--secondary {
  background: var(--color-neutral-700, #374151);
  border-color: var(--color-neutral-600, #4b5563);
  color: var(--color-neutral-100, #f3f4f6);
}

.evm-btn--secondary:hover {
  background: var(--color-neutral-600, #4b5563);
}

.evm-btn--export {
  background: var(--color-primary-700, #1d4ed8);
  border-color: var(--color-primary-600, #2563eb);
  color: #ffffff;
}

.evm-btn--export:hover {
  background: var(--color-primary-600, #2563eb);
}
</style>
