<template>
  <div v-if="isVisible" class="font-warning">
    <div class="font-warning__header">
      <span class="font-warning__icon">⚠️</span>
      <span class="font-warning__title">Fonte não encontrada</span>
    </div>

    <div class="font-warning__body">
      <div class="font-warning__row">
        <span class="font-warning__label">Detectada:</span>
        <span class="font-warning__value font-warning__value--detected">{{ detectedFont }}</span>
      </div>
      <div class="font-warning__row">
        <span class="font-warning__label">Fallback:</span>
        <span class="font-warning__value font-warning__value--fallback">{{ fallbackFont }}</span>
      </div>
    </div>

    <div class="font-warning__actions">
      <input
        ref="fileInputRef"
        type="file"
        accept=".ttf,.otf,.woff,.woff2"
        class="font-warning__file-input"
        @change="handleFileChange"
      />
      <button
        class="font-warning__btn"
        type="button"
        @click="openFilePicker"
      >
        Upload fonte
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { FontStatus } from '@/composables/useFontCascade'

// ─── Props ────────────────────────────────────────────────────────────────────

const props = defineProps<{
  detectedFont: string
  fallbackFont: string
  status: FontStatus
}>()

// ─── Emits ────────────────────────────────────────────────────────────────────

const emit = defineEmits<{
  upload: [file: File]
}>()

// ─── Local state ──────────────────────────────────────────────────────────────

const fileInputRef = ref<HTMLInputElement | null>(null)

// ─── Computed ─────────────────────────────────────────────────────────────────

/** FontWarning is only visible when font is not found in catalog */
const isVisible = computed(() => props.status === 'not_found')

// ─── Handlers ─────────────────────────────────────────────────────────────────

function openFilePicker() {
  fileInputRef.value?.click()
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    emit('upload', file)
    // Reset input so the same file can be selected again
    input.value = ''
  }
}
</script>

<style scoped>
.font-warning {
  background: var(--color-amber-950, #451a03);
  border: 1px solid var(--color-amber-700, #b45309);
  border-radius: 0.375rem;
  padding: 0.625rem;
  margin-top: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.font-warning__header {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.font-warning__icon {
  font-size: 0.875rem;
  flex-shrink: 0;
}

.font-warning__title {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-amber-300, #fcd34d);
}

.font-warning__body {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.font-warning__row {
  display: flex;
  gap: 0.375rem;
  align-items: baseline;
}

.font-warning__label {
  font-size: 0.6875rem;
  color: var(--color-amber-400, #fbbf24);
  flex-shrink: 0;
  min-width: 4.5rem;
}

.font-warning__value {
  font-size: 0.6875rem;
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.font-warning__value--detected {
  color: var(--color-red-400, #f87171);
}

.font-warning__value--fallback {
  color: var(--color-neutral-300, #d1d5db);
}

.font-warning__actions {
  display: flex;
  align-items: center;
}

.font-warning__file-input {
  display: none;
}

.font-warning__btn {
  font-size: 0.6875rem;
  padding: 0.25rem 0.625rem;
  background: var(--color-amber-700, #b45309);
  color: var(--color-amber-100, #fef3c7);
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  font-weight: 500;
  transition: background 100ms ease;
}

.font-warning__btn:hover {
  background: var(--color-amber-600, #d97706);
}
</style>
