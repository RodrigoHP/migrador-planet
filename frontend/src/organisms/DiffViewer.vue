<template>
  <div class="diff-viewer">
    <!-- Toolbar: document selector -->
    <header class="diff-viewer__toolbar">
      <DocumentSelector />
    </header>

    <!-- Split panels -->
    <div class="diff-viewer__panels">
      <!-- Panel A -->
      <div class="diff-viewer__panel" data-testid="diff-panel-a">
        <div class="diff-viewer__panel-header">
          <span class="diff-viewer__panel-label">Documento A</span>
          <span v-if="diffStore.documentA" class="diff-viewer__panel-name">
            {{ docNameA }}
          </span>
        </div>
        <div class="diff-viewer__canvas-wrapper">
          <!-- Loading state -->
          <div v-if="isLoadingA" class="diff-viewer__loading" aria-busy="true">Carregando PDF…</div>
          <!-- Error state -->
          <div v-else-if="errorA" class="diff-viewer__error" role="alert">
            {{ errorA }}
          </div>
          <!-- Empty state -->
          <div v-else-if="!diffStore.documentA" class="diff-viewer__empty">
            Selecione o Documento A
          </div>

          <!-- Canvas + highlights -->
          <div
            v-show="!isLoadingA && !errorA && diffStore.documentA"
            class="diff-viewer__canvas-inner"
          >
            <canvas ref="canvasARef" class="diff-viewer__canvas" aria-label="Documento A" />
            <!-- Diff highlights for doc A -->
            <DiffHighlight
              v-for="item in highlightsA"
              :key="item.elementId"
              :type="item.diffType"
              :bounds="item.boundsA!"
            />
          </div>
        </div>
        <!-- Page nav A -->
        <div class="diff-viewer__page-nav">
          <button
            type="button"
            class="diff-viewer__nav-btn"
            :disabled="currentPageA <= 1 || isLoadingA"
            aria-label="Página anterior A"
            @click="prevA"
          >
            ◀
          </button>
          <span class="diff-viewer__page-info" aria-live="polite">
            {{ currentPageA }} / {{ totalPagesA || '–' }}
          </span>
          <button
            type="button"
            class="diff-viewer__nav-btn"
            :disabled="currentPageA >= totalPagesA || isLoadingA"
            aria-label="Próxima página A"
            @click="nextA"
          >
            ▶
          </button>
        </div>
      </div>

      <!-- Divider -->
      <div class="diff-viewer__divider" aria-hidden="true" />

      <!-- Panel B -->
      <div class="diff-viewer__panel" data-testid="diff-panel-b">
        <div class="diff-viewer__panel-header">
          <span class="diff-viewer__panel-label">Documento B</span>
          <span v-if="diffStore.documentB" class="diff-viewer__panel-name">
            {{ docNameB }}
          </span>
        </div>
        <div class="diff-viewer__canvas-wrapper">
          <!-- Loading state -->
          <div v-if="isLoadingB" class="diff-viewer__loading" aria-busy="true">Carregando PDF…</div>
          <!-- Error state -->
          <div v-else-if="errorB" class="diff-viewer__error" role="alert">
            {{ errorB }}
          </div>
          <!-- Empty state -->
          <div v-else-if="!diffStore.documentB" class="diff-viewer__empty">
            Selecione o Documento B
          </div>

          <!-- Canvas + highlights -->
          <div
            v-show="!isLoadingB && !errorB && diffStore.documentB"
            class="diff-viewer__canvas-inner"
          >
            <canvas ref="canvasBRef" class="diff-viewer__canvas" aria-label="Documento B" />
            <!-- Diff highlights for doc B -->
            <DiffHighlight
              v-for="item in highlightsB"
              :key="item.elementId"
              :type="item.diffType"
              :bounds="item.boundsB!"
            />
          </div>
        </div>
        <!-- Page nav B -->
        <div class="diff-viewer__page-nav">
          <button
            type="button"
            class="diff-viewer__nav-btn"
            :disabled="currentPageB <= 1 || isLoadingB"
            aria-label="Página anterior B"
            @click="prevB"
          >
            ◀
          </button>
          <span class="diff-viewer__page-info" aria-live="polite">
            {{ currentPageB }} / {{ totalPagesB || '–' }}
          </span>
          <button
            type="button"
            class="diff-viewer__nav-btn"
            :disabled="currentPageB >= totalPagesB || isLoadingB"
            aria-label="Próxima página B"
            @click="nextB"
          >
            ▶
          </button>
        </div>
      </div>
    </div>

    <!-- Story 35.4: Inference results panel -->
    <section
      v-if="diffStore.isActive && diffStore.inferences.length > 0"
      class="diff-viewer__inferences"
      data-testid="diff-inferences-panel"
    >
      <div class="diff-viewer__inferences-header">
        <h3 class="diff-viewer__inferences-title">Resultado</h3>
        <span class="diff-viewer__inferences-badge" data-testid="pending-count">
          {{ diffStore.inferences.length }} pendente{{
            diffStore.inferences.length !== 1 ? 's' : ''
          }}
        </span>
      </div>

      <!-- Diff summary counts (Story 35.3) -->
      <div class="diff-viewer__summary" data-testid="diff-summary">
        <span class="diff-viewer__summary-item diff-viewer__summary-item--identical">
          Iguais: {{ diffStore.diffSummary.identical }}
        </span>
        <span class="diff-viewer__summary-item diff-viewer__summary-item--moved">
          Movidos: {{ diffStore.diffSummary.moved }}
        </span>
        <span class="diff-viewer__summary-item diff-viewer__summary-item--added">
          Adicionados: {{ diffStore.diffSummary.added }}
        </span>
        <span class="diff-viewer__summary-item diff-viewer__summary-item--removed">
          Removidos: {{ diffStore.diffSummary.removed }}
        </span>
      </div>

      <ul class="diff-viewer__inferences-list">
        <li v-for="inf in diffStore.inferences" :key="inf.id" class="diff-viewer__inference-item">
          <div class="diff-viewer__inference-body">
            <span
              class="diff-viewer__inference-type"
              :class="`diff-viewer__inference-type--${inf.type}`"
            >
              {{ inf.type }}
            </span>
            <span class="diff-viewer__inference-desc">{{ inf.description }}</span>
            <span class="diff-viewer__inference-confidence">
              {{ Math.round(inf.confidence * 100) }}%
            </span>
          </div>
          <div class="diff-viewer__inference-actions">
            <button
              type="button"
              class="diff-viewer__inference-btn diff-viewer__inference-btn--confirm"
              aria-label="Confirmar inferência"
              @click="diffStore.confirmInference(inf.id)"
            >
              Confirmar
            </button>
            <button
              type="button"
              class="diff-viewer__inference-btn diff-viewer__inference-btn--reject"
              aria-label="Rejeitar inferência"
              @click="diffStore.rejectInference(inf.id)"
            >
              Rejeitar
            </button>
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { PDFDocumentProxy } from 'pdfjs-dist'
import { useDiffStore } from '@/stores/diffStore'
import { useMultiDocStore } from '@/stores/multiDocStore'
import { useSessionStore } from '@/stores/session'
import DocumentSelector from '@/molecules/DocumentSelector.vue'
import DiffHighlight from '@/atoms/DiffHighlight.vue'

// ─── Diff scale: max 150 DPI (scale = 1.5) ───────────────────────────────────
const DIFF_SCALE = 1.5

let pdfjsLib: typeof import('pdfjs-dist') | null = null

async function ensurePdfJs() {
  if (pdfjsLib) return pdfjsLib
  const lib = await import('pdfjs-dist')
  const worker = await import('pdfjs-dist/build/pdf.worker.min.mjs?url')
  lib.GlobalWorkerOptions.workerSrc = worker.default
  pdfjsLib = lib
  return lib
}

const diffStore = useDiffStore()
const multiDocStore = useMultiDocStore()
const sessionStore = useSessionStore()

// ─── Panel A state ────────────────────────────────────────────────────────────
const canvasARef = ref<HTMLCanvasElement | null>(null)
const pdfDocA = ref<PDFDocumentProxy | null>(null)
const currentPageA = ref(1)
const totalPagesA = ref(0)
const isLoadingA = ref(false)
const errorA = ref<string | null>(null)

// ─── Panel B state ────────────────────────────────────────────────────────────
const canvasBRef = ref<HTMLCanvasElement | null>(null)
const pdfDocB = ref<PDFDocumentProxy | null>(null)
const currentPageB = ref(1)
const totalPagesB = ref(0)
const isLoadingB = ref(false)
const errorB = ref<string | null>(null)

// ─── Computed doc names ───────────────────────────────────────────────────────
const docNameA = computed(() => {
  const pdf = multiDocStore.pdfList.find((p) => p.id === diffStore.documentA)
  return pdf?.name ?? ''
})

const docNameB = computed(() => {
  const pdf = multiDocStore.pdfList.find((p) => p.id === diffStore.documentB)
  return pdf?.name ?? ''
})

// ─── Highlights: only items with bounds for their side ───────────────────────
const highlightsA = computed(() => diffStore.diffData.filter((item) => item.boundsA))

const highlightsB = computed(() => diffStore.diffData.filter((item) => item.boundsB))

// ─── PDF helpers ─────────────────────────────────────────────────────────────

function getPdfBytes(docId: string): ArrayBuffer | null {
  // Look in uploadedPdfs by name (session store uses PdfFile with name + bytes)
  const pdfMeta = multiDocStore.pdfList.find((p) => p.id === docId)
  if (!pdfMeta) return null
  const uploaded = sessionStore.uploadedPdfs.find((u) => u.name === pdfMeta.name)
  return uploaded?.bytes ?? null
}

async function loadPanelA(docId: string) {
  if (!docId) return
  const bytes = getPdfBytes(docId)
  if (!bytes) {
    errorA.value = 'PDF não encontrado no projeto.'
    return
  }
  isLoadingA.value = true
  errorA.value = null
  try {
    if (pdfDocA.value) {
      await pdfDocA.value.destroy()
      pdfDocA.value = null
    }
    const lib = await ensurePdfJs()
    const task = lib.getDocument({ data: bytes })
    pdfDocA.value = await task.promise
    totalPagesA.value = pdfDocA.value.numPages
    currentPageA.value = 1
    await renderA()
  } catch (err) {
    errorA.value = err instanceof Error ? err.message : 'Erro ao carregar PDF A'
  } finally {
    isLoadingA.value = false
  }
}

async function loadPanelB(docId: string) {
  if (!docId) return
  const bytes = getPdfBytes(docId)
  if (!bytes) {
    errorB.value = 'PDF não encontrado no projeto.'
    return
  }
  isLoadingB.value = true
  errorB.value = null
  try {
    if (pdfDocB.value) {
      await pdfDocB.value.destroy()
      pdfDocB.value = null
    }
    const lib = await ensurePdfJs()
    const task = lib.getDocument({ data: bytes })
    pdfDocB.value = await task.promise
    totalPagesB.value = pdfDocB.value.numPages
    currentPageB.value = 1
    await renderB()
  } catch (err) {
    errorB.value = err instanceof Error ? err.message : 'Erro ao carregar PDF B'
  } finally {
    isLoadingB.value = false
  }
}

async function renderA() {
  if (!pdfDocA.value || !canvasARef.value) return
  try {
    const page = await pdfDocA.value.getPage(currentPageA.value)
    const viewport = page.getViewport({ scale: DIFF_SCALE })
    const ctx = canvasARef.value.getContext('2d')
    if (!ctx) return
    canvasARef.value.width = viewport.width
    canvasARef.value.height = viewport.height
    await page.render({ canvasContext: ctx, viewport }).promise
  } catch (err) {
    errorA.value = err instanceof Error ? err.message : 'Erro ao renderizar'
  }
}

async function renderB() {
  if (!pdfDocB.value || !canvasBRef.value) return
  try {
    const page = await pdfDocB.value.getPage(currentPageB.value)
    const viewport = page.getViewport({ scale: DIFF_SCALE })
    const ctx = canvasBRef.value.getContext('2d')
    if (!ctx) return
    canvasBRef.value.width = viewport.width
    canvasBRef.value.height = viewport.height
    await page.render({ canvasContext: ctx, viewport }).promise
  } catch (err) {
    errorB.value = err instanceof Error ? err.message : 'Erro ao renderizar'
  }
}

async function prevA() {
  if (currentPageA.value > 1) {
    currentPageA.value--
    await renderA()
  }
}

async function nextA() {
  if (currentPageA.value < totalPagesA.value) {
    currentPageA.value++
    await renderA()
  }
}

async function prevB() {
  if (currentPageB.value > 1) {
    currentPageB.value--
    await renderB()
  }
}

async function nextB() {
  if (currentPageB.value < totalPagesB.value) {
    currentPageB.value++
    await renderB()
  }
}

// ─── Watchers: load PDFs when selection changes ───────────────────────────────
watch(
  () => diffStore.documentA,
  (docId) => {
    if (docId) loadPanelA(docId)
  },
)

watch(
  () => diffStore.documentB,
  (docId) => {
    if (docId) loadPanelB(docId)
  },
)
</script>

<style scoped>
.diff-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--color-neutral-50, #f9fafb);
}

.diff-viewer__toolbar {
  display: flex;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: var(--color-neutral-100, #f3f4f6);
  border-bottom: 1px solid var(--color-neutral-300, #d1d5db);
  flex-shrink: 0;
}

.diff-viewer__panels {
  display: flex;
  flex: 1;
  overflow: hidden;
  gap: 0;
}

.diff-viewer__panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.diff-viewer__panel-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  background: var(--color-neutral-100, #f3f4f6);
  border-bottom: 1px solid var(--color-neutral-200, #e5e7eb);
  flex-shrink: 0;
}

.diff-viewer__panel-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-neutral-500, #525252);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.diff-viewer__panel-name {
  font-size: 0.8125rem;
  color: var(--color-neutral-700, #374151);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.diff-viewer__divider {
  width: 1px;
  background: var(--color-neutral-300, #d1d5db);
  flex-shrink: 0;
  align-self: stretch;
}

.diff-viewer__canvas-wrapper {
  flex: 1;
  overflow: auto;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 0.5rem;
  position: relative;
}

.diff-viewer__canvas-inner {
  position: relative;
  display: inline-block;
}

.diff-viewer__canvas {
  max-width: 100%;
  border-radius: 0.375rem;
  border: 1px solid var(--color-neutral-200, #e5e7eb);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  display: block;
}

.diff-viewer__loading,
.diff-viewer__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  width: 100%;
  font-size: 0.875rem;
  color: var(--color-neutral-400, #9ca3af);
}

.diff-viewer__error {
  margin: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 0.375rem;
  color: #dc2626;
  font-size: 0.8125rem;
}

.diff-viewer__page-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  background: var(--color-neutral-100, #f3f4f6);
  border-top: 1px solid var(--color-neutral-200, #e5e7eb);
  flex-shrink: 0;
}

.diff-viewer__nav-btn {
  padding: 0.125rem 0.5rem;
  border: 1px solid var(--color-neutral-300, #d1d5db);
  border-radius: 0.25rem;
  background: #fff;
  font-size: 0.75rem;
  cursor: pointer;
  transition: background 0.15s;
}

.diff-viewer__nav-btn:hover:not(:disabled) {
  background: var(--color-neutral-200, #e5e7eb);
}

.diff-viewer__nav-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.diff-viewer__page-info {
  font-size: 0.8125rem;
  color: var(--color-neutral-600, #4b5563);
  min-width: 4rem;
  text-align: center;
}

/* Story 35.4: Inference panel */
.diff-viewer__inferences {
  flex-shrink: 0;
  border-top: 1px solid var(--color-neutral-300, #d1d5db);
  background: var(--color-neutral-50, #f9fafb);
  max-height: 14rem;
  overflow-y: auto;
}

.diff-viewer__inferences-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--color-neutral-100, #f3f4f6);
  border-bottom: 1px solid var(--color-neutral-200, #e5e7eb);
  position: sticky;
  top: 0;
  z-index: 5;
}

.diff-viewer__inferences-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-neutral-700, #374151);
  margin: 0;
  flex: 1;
}

.diff-viewer__inferences-badge {
  font-size: 0.6875rem;
  font-weight: 600;
  background: var(--color-primary-100, #dbeafe);
  color: var(--color-primary-700, #1d4ed8);
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
}

/* Summary counts */
.diff-viewer__summary {
  display: flex;
  gap: 0.75rem;
  padding: 0.375rem 0.75rem;
  border-bottom: 1px solid var(--color-neutral-200, #e5e7eb);
}

.diff-viewer__summary-item {
  font-size: 0.6875rem;
  font-weight: 600;
}

.diff-viewer__summary-item--identical {
  color: #16a34a;
}
.diff-viewer__summary-item--moved {
  color: #ca8a04;
}
.diff-viewer__summary-item--added {
  color: #dc2626;
}
.diff-viewer__summary-item--removed {
  color: #dc2626;
}

/* Inference list */
.diff-viewer__inferences-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.diff-viewer__inference-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  border-bottom: 1px solid var(--color-neutral-200, #e5e7eb);
}

.diff-viewer__inference-body {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.diff-viewer__inference-type {
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.0625rem 0.375rem;
  border-radius: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  flex-shrink: 0;
}

.diff-viewer__inference-type--moved {
  background: rgba(234, 179, 8, 0.15);
  color: #ca8a04;
}
.diff-viewer__inference-type--added {
  background: rgba(239, 68, 68, 0.15);
  color: #dc2626;
}
.diff-viewer__inference-type--removed {
  background: rgba(239, 68, 68, 0.15);
  color: #dc2626;
}

.diff-viewer__inference-desc {
  flex: 1;
  font-size: 0.8125rem;
  color: var(--color-neutral-700, #374151);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.diff-viewer__inference-confidence {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-neutral-500, #525252);
  flex-shrink: 0;
}

.diff-viewer__inference-actions {
  display: flex;
  gap: 0.25rem;
  flex-shrink: 0;
}

.diff-viewer__inference-btn {
  padding: 0.125rem 0.5rem;
  border: 1px solid var(--color-neutral-300, #d1d5db);
  border-radius: 0.25rem;
  font-size: 0.6875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.diff-viewer__inference-btn--confirm {
  background: rgba(34, 197, 94, 0.1);
  border-color: rgba(34, 197, 94, 0.4);
  color: #16a34a;
}

.diff-viewer__inference-btn--confirm:hover {
  background: rgba(34, 197, 94, 0.2);
}

.diff-viewer__inference-btn--reject {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.4);
  color: #dc2626;
}

.diff-viewer__inference-btn--reject:hover {
  background: rgba(239, 68, 68, 0.2);
}
</style>
