<template>
  <div class="document-selector">
    <!-- Document A -->
    <div class="document-selector__group">
      <label for="doc-selector-a" class="document-selector__label">Documento A:</label>
      <select
        id="doc-selector-a"
        class="document-selector__select"
        :value="diffStore.documentA ?? ''"
        aria-label="Selecionar Documento A"
        @change="onChangeA"
      >
        <option value="" disabled>Selecione...</option>
        <option
          v-for="pdf in multiDocStore.pdfList"
          :key="pdf.id"
          :value="pdf.id"
        >
          {{ pdf.name }}
        </option>
      </select>
    </div>

    <span class="document-selector__vs" aria-hidden="true">vs</span>

    <!-- Document B -->
    <div class="document-selector__group">
      <label for="doc-selector-b" class="document-selector__label">Documento B:</label>
      <select
        id="doc-selector-b"
        class="document-selector__select"
        :value="diffStore.documentB ?? ''"
        aria-label="Selecionar Documento B"
        @change="onChangeB"
      >
        <option value="" disabled>Selecione...</option>
        <option
          v-for="pdf in multiDocStore.pdfList"
          :key="pdf.id"
          :value="pdf.id"
        >
          {{ pdf.name }}
        </option>
      </select>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useMultiDocStore } from '@/stores/multiDocStore'
import { useDiffStore } from '@/stores/diffStore'

const multiDocStore = useMultiDocStore()
const diffStore = useDiffStore()

function onChangeA(event: Event) {
  const target = event.target as HTMLSelectElement
  const docA = target.value
  const docB = diffStore.documentB ?? ''
  if (docA && docB) {
    diffStore.setDocuments(docA, docB)
  } else {
    diffStore.documentA = docA || null
  }
}

function onChangeB(event: Event) {
  const target = event.target as HTMLSelectElement
  const docB = target.value
  const docA = diffStore.documentA ?? ''
  if (docA && docB) {
    diffStore.setDocuments(docA, docB)
  } else {
    diffStore.documentB = docB || null
  }
}
</script>

<style scoped>
.document-selector {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.document-selector__group {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.document-selector__label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-neutral-600, #4b5563);
  white-space: nowrap;
}

.document-selector__select {
  font-size: 0.8125rem;
  border: 1px solid var(--color-neutral-300, #d1d5db);
  border-radius: 0.375rem;
  padding: 0.25rem 0.5rem;
  background: #fff;
  color: var(--color-neutral-800, #1f2937);
  cursor: pointer;
  min-width: 8rem;
}

.document-selector__vs {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
</style>
