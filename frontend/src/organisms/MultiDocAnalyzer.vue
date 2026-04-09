<template>
  <div class="multi-doc-analyzer">
    <!-- Title bar / toggle -->
    <div class="multi-doc-analyzer__titlebar" @click="toggleCollapse">
      <button
        type="button"
        class="multi-doc-analyzer__toggle"
        :aria-label="collapsed ? 'Expandir analisador' : 'Colapsar analisador'"
        :aria-expanded="!collapsed"
      >
        <span class="multi-doc-analyzer__toggle-icon">
          {{ collapsed ? '→' : '↓' }}
        </span>
      </button>
      <span class="multi-doc-analyzer__title">Analisador Multi-Documento</span>
      <span class="multi-doc-analyzer__pdf-count"> {{ multiDocStore.pdfList.length }} PDFs </span>
    </div>

    <!-- Collapsible body -->
    <div v-if="!collapsed" class="multi-doc-analyzer__body">
      <!-- Section: PDF list -->
      <section class="multi-doc-analyzer__section">
        <h3 class="multi-doc-analyzer__section-title">Documentos</h3>
        <ul class="multi-doc-analyzer__pdf-list">
          <li
            v-for="pdf in multiDocStore.pdfList"
            :key="pdf.id"
            class="multi-doc-analyzer__pdf-item"
          >
            <span
              class="multi-doc-analyzer__pdf-role"
              :class="
                pdf.role === 'base'
                  ? 'multi-doc-analyzer__pdf-role--base'
                  : 'multi-doc-analyzer__pdf-role--variation'
              "
            >
              {{ pdf.role === 'base' ? 'base' : 'variação' }}
            </span>
            <span class="multi-doc-analyzer__pdf-name">{{ pdf.name }}</span>
            <span class="multi-doc-analyzer__pdf-check" aria-label="carregado">✔</span>
          </li>
        </ul>
      </section>

      <!-- Section: Variation Matrix -->
      <section v-if="matrixRows.length > 0" class="multi-doc-analyzer__section">
        <h3 class="multi-doc-analyzer__section-title">Matriz de Variação</h3>
        <div
          class="multi-doc-analyzer__matrix"
          :style="{ gridTemplateColumns: `1fr repeat(${multiDocStore.pdfList.length}, 2.5rem)` }"
          role="table"
          aria-label="Matriz de variação de campos"
        >
          <!-- Header row -->
          <div class="multi-doc-analyzer__matrix-header" role="columnheader">Campo</div>
          <div
            v-for="(pdf, idx) in multiDocStore.pdfList"
            :key="pdf.id"
            class="multi-doc-analyzer__matrix-header multi-doc-analyzer__matrix-header--doc"
            role="columnheader"
            :title="pdf.name"
          >
            D{{ idx + 1 }}
          </div>

          <!-- Data rows -->
          <VariationRow
            v-for="row in matrixRows"
            :key="row.fieldName"
            :field-name="row.fieldName"
            :presence-per-doc="row.presencePerDoc"
          />
        </div>
      </section>

      <!-- Section: Automatic detections -->
      <section v-if="multiDocStore.detections.length > 0" class="multi-doc-analyzer__section">
        <h3 class="multi-doc-analyzer__section-title">Inferências Automáticas</h3>
        <ul class="multi-doc-analyzer__detections">
          <li v-for="det in multiDocStore.detections" :key="det.id">
            <DetectionCard :detection="det" @confirm="onConfirm" @reject="onReject" />
          </li>
        </ul>
      </section>

      <p v-else class="multi-doc-analyzer__empty">
        Nenhuma inferência disponível. Execute a análise após carregar os PDFs.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useMultiDocStore } from '@/stores/multiDocStore'
import VariationRow from '@/molecules/VariationRow.vue'
import DetectionCard from '@/molecules/DetectionCard.vue'
import type { VariationRowData } from '@/types/multi-doc.types'

const multiDocStore = useMultiDocStore()

// ─── Collapse state ────────────────────────────────────────────────────────
const collapsed = ref(false)

function toggleCollapse() {
  collapsed.value = !collapsed.value
}

// ─── Variation matrix rows ─────────────────────────────────────────────────
// Story 35.6: Prefer field-level matrix (Campos × PDFs) over layout-level
const matrixRows = computed<VariationRowData[]>(() => {
  const matrix = multiDocStore.variationMatrix
  if (!matrix) return []

  const pdfs = multiDocStore.pdfList
  const docIds = pdfs.map((p) => p.id)

  // Use field-level matrix when available (Story 35.6)
  if (matrix.fieldIds?.length && matrix.fieldCells) {
    return matrix.fieldIds.map((fieldId) => {
      const rowCells = matrix.fieldCells![fieldId] ?? {}
      const presencePerDoc = docIds.map((docId) => !!rowCells[docId])
      // Classify mixed patterns as optional
      const allPresent = presencePerDoc.every(Boolean)
      const nonePresent = presencePerDoc.every((p) => !p)
      const fieldName = !allPresent && !nonePresent ? `${fieldId} (opcional)` : fieldId
      return { fieldName, presencePerDoc }
    })
  }

  // Fallback: layout-level matrix
  return matrix.layoutIds.map((layoutId) => {
    const rowCells = matrix.cells[layoutId] ?? {}
    const presencePerDoc = docIds.map((docId) => !!rowCells[docId])
    return { fieldName: layoutId, presencePerDoc }
  })
})

// ─── Detection handlers ────────────────────────────────────────────────────
function onConfirm(id: string) {
  multiDocStore.confirmDetection(id)
}

function onReject(id: string) {
  multiDocStore.rejectDetection(id)
}
</script>

<style scoped>
.multi-doc-analyzer {
  background: var(--color-neutral-800, #1f2937);
  border-top: 1px solid var(--color-neutral-700, #374151);
  border-bottom: 1px solid var(--color-neutral-700, #374151);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Title bar */
.multi-doc-analyzer__titlebar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0 0.75rem;
  height: 2.25rem;
  cursor: pointer;
  user-select: none;
  flex-shrink: 0;
  background: var(--color-neutral-850, #111827);
  border-bottom: 1px solid var(--color-neutral-700, #374151);
  transition: background 0.12s;
}

.multi-doc-analyzer__titlebar:hover {
  background: var(--color-neutral-700, #374151);
}

.multi-doc-analyzer__toggle {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-neutral-400, #9ca3af);
  font-size: 0.75rem;
  padding: 0;
  line-height: 1;
}

.multi-doc-analyzer__toggle-icon {
  display: inline-block;
  width: 1rem;
  text-align: center;
}

.multi-doc-analyzer__title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-neutral-200, #e5e7eb);
  flex: 1;
}

.multi-doc-analyzer__pdf-count {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  background: var(--color-neutral-700, #374151);
  padding: 0.125rem 0.375rem;
  border-radius: 9999px;
}

/* Body */
.multi-doc-analyzer__body {
  overflow-y: auto;
  max-height: 24rem;
  padding: 0.5rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

/* Sections */
.multi-doc-analyzer__section {
  padding: 0 0.75rem;
}

.multi-doc-analyzer__section-title {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-neutral-400, #9ca3af);
  margin: 0.25rem 0 0.375rem;
}

/* PDF list */
.multi-doc-analyzer__pdf-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.multi-doc-analyzer__pdf-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
}

.multi-doc-analyzer__pdf-role {
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.0625rem 0.375rem;
  border-radius: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.multi-doc-analyzer__pdf-role--base {
  background: rgba(96, 165, 250, 0.15);
  color: #60a5fa;
}

.multi-doc-analyzer__pdf-role--variation {
  background: rgba(167, 139, 250, 0.15);
  color: #a78bfa;
}

.multi-doc-analyzer__pdf-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-neutral-200, #e5e7eb);
}

.multi-doc-analyzer__pdf-check {
  color: #22c55e;
  font-weight: 700;
  font-size: 0.75rem;
}

/* Variation Matrix */
.multi-doc-analyzer__matrix {
  display: grid;
  border: 1px solid var(--color-neutral-700, #374151);
  border-radius: 0.25rem;
  overflow: hidden;
}

.multi-doc-analyzer__matrix-header {
  padding: 0.25rem 0.5rem;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-neutral-400, #9ca3af);
  background: var(--color-neutral-700, #374151);
  border-bottom: 1px solid var(--color-neutral-600, #4b5563);
}

.multi-doc-analyzer__matrix-header--doc {
  text-align: center;
}

/* Detections */
.multi-doc-analyzer__detections {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.multi-doc-analyzer__empty {
  padding: 0.5rem 0.75rem;
  font-size: 0.8125rem;
  color: var(--color-neutral-500, #6b7280);
  font-style: italic;
  margin: 0;
}
</style>
