<template>
  <div class="pdf-reference">
    <!-- Toolbar -->
    <header class="pdf-reference__toolbar" aria-label="PDF Reference toolbar">
      <!-- Document selector -->
      <div class="pdf-reference__doc-select">
        <label for="pdf-doc-selector" class="pdf-reference__label">Documento:</label>
        <select
          id="pdf-doc-selector"
          v-model="selectedDocIndex"
          class="pdf-reference__select"
          aria-label="Selecionar documento"
          @change="onDocumentChange"
        >
          <option v-if="uploadedPdfs.length === 0" value="-1" disabled>Nenhum PDF carregado</option>
          <option
            v-for="(pdf, idx) in uploadedPdfs"
            :key="pdf.name"
            :value="idx"
          >
            {{ pdf.name }}
          </option>
        </select>
      </div>

      <!-- Page navigation -->
      <div class="pdf-reference__nav" role="group" aria-label="Navegação de página">
        <button
          class="pdf-reference__nav-btn"
          type="button"
          :disabled="renderer.currentPage.value <= 1 || renderer.isLoading.value"
          aria-label="Página anterior"
          @click="onPrev"
        >
          ◀ Anterior
        </button>
        <span class="pdf-reference__page-indicator" aria-live="polite">
          Página {{ renderer.currentPage.value }} de {{ renderer.totalPages.value || '–' }}
        </span>
        <button
          class="pdf-reference__nav-btn"
          type="button"
          :disabled="renderer.currentPage.value >= renderer.totalPages.value || renderer.isLoading.value"
          aria-label="Próxima página"
          @click="onNext"
        >
          Próxima ▶
        </button>
      </div>

      <!-- Cluster indicator -->
      <div
        v-if="clusterPageCount > 1"
        class="pdf-reference__cluster"
        role="status"
        aria-label="Indicador de cluster"
      >
        Página representativa de {{ clusterPageCount }} páginas
      </div>

      <!-- Zoom controls -->
      <div class="pdf-reference__zoom" role="group" aria-label="Controles de zoom do PDF">
        <button
          class="pdf-reference__zoom-btn"
          type="button"
          :disabled="editorStore.pdfZoom <= 50"
          aria-label="Diminuir zoom"
          @click="onZoomOut"
        >
          −
        </button>
        <span class="pdf-reference__zoom-level" aria-live="polite">{{ editorStore.pdfZoom }}%</span>
        <button
          class="pdf-reference__zoom-btn"
          type="button"
          :disabled="editorStore.pdfZoom >= 200"
          aria-label="Aumentar zoom"
          @click="onZoomIn"
        >
          +
        </button>
      </div>
    </header>

    <!-- Error state -->
    <div v-if="renderer.error.value" class="pdf-reference__error" role="alert">
      {{ renderer.error.value }}
    </div>

    <!-- Loading state -->
    <div v-else-if="renderer.isLoading.value && !renderer.pdfDocument.value" class="pdf-reference__loading" aria-busy="true">
      Carregando PDF…
    </div>

    <!-- Empty state -->
    <div v-else-if="uploadedPdfs.length === 0" class="pdf-reference__empty">
      Nenhum PDF disponível para visualização.
    </div>

    <!-- Canvas + coverage overlay wrapper -->
    <div class="pdf-reference__canvas-wrapper">
      <div class="pdf-reference__canvas-inner">
        <canvas
          ref="canvasRef"
          class="pdf-reference__canvas"
          :class="{ 'pdf-reference__canvas--hidden': !renderer.pdfDocument.value }"
          aria-label="Visualizador de PDF"
        />
        <!-- Coverage overlay for PDF reference -->
        <CoverageOverlay
          target="pdf"
          :visible="editorStore.coverageMode"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useLayoutStore } from '@/stores/layout'
import { useEditorStore } from '@/stores/editorStore'
import { usePdfRenderer } from '@/composables/usePdfRenderer'
import CoverageOverlay from '@/organisms/CoverageOverlay.vue'

const sessionStore = useSessionStore()
const layoutStore = useLayoutStore()
const editorStore = useEditorStore()
const renderer = usePdfRenderer()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const selectedDocIndex = ref<number>(0)

const uploadedPdfs = computed(() => sessionStore.uploadedPdfs)

/** Cluster page count from active layout — 0 or 1 hides the indicator */
const clusterPageCount = computed<number>(() => {
  const layout = layoutStore.activeLayout
  if (!layout) return 0
  return layout.pageCount ?? 0
})

/** Representative page from active layout (first representative page, 1-based) */
const representativePage = computed<number>(() => {
  const layout = layoutStore.activeLayout
  if (!layout || !layout.representativePages || layout.representativePages.length === 0) return 1
  return layout.representativePages[0] ?? 1
})

async function loadSelectedDoc() {
  const pdf = uploadedPdfs.value[selectedDocIndex.value]
  if (!pdf) return
  await renderer.loadPdf(pdf.bytes)
  // After loading, navigate to representative page
  renderer.goToPage(representativePage.value)
  await renderCurrentPage()
}

async function renderCurrentPage() {
  if (canvasRef.value && renderer.pdfDocument.value) {
    await renderer.renderPage(renderer.currentPage.value, canvasRef.value)
  }
}

function onDocumentChange() {
  loadSelectedDoc()
}

async function onPrev() {
  renderer.prevPage()
  await renderCurrentPage()
}

async function onNext() {
  renderer.nextPage()
  await renderCurrentPage()
}

async function onZoomIn() {
  renderer.zoomIn()
  await renderCurrentPage()
}

async function onZoomOut() {
  renderer.zoomOut()
  await renderCurrentPage()
}

// Watch page changes to re-render
watch(() => renderer.currentPage.value, async () => {
  await renderCurrentPage()
})

// Watch zoom changes to re-render
watch(() => editorStore.pdfZoom, async () => {
  await renderCurrentPage()
})

// Watch active layout representative page
watch(representativePage, async (page) => {
  renderer.goToPage(page)
  await renderCurrentPage()
})

// Load first PDF on mount
onMounted(async () => {
  if (uploadedPdfs.value.length > 0) {
    selectedDocIndex.value = 0
    await loadSelectedDoc()
  }
})
</script>

<style scoped>
.pdf-reference {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--color-neutral-50, #f9fafb);
}

.pdf-reference__toolbar {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  flex-shrink: 0;
  padding: 0.5rem 0.75rem;
  background: var(--color-neutral-100, #f3f4f6);
  border-bottom: 1px solid var(--color-neutral-300, #d1d5db);
}

.pdf-reference__label {
  font-size: 0.8125rem;
  color: var(--color-neutral-600, #4b5563);
  font-weight: 500;
}

.pdf-reference__doc-select {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.pdf-reference__select {
  font-size: 0.8125rem;
  border: 1px solid var(--color-neutral-300, #d1d5db);
  border-radius: 0.375rem;
  padding: 0.25rem 0.5rem;
  background: #fff;
  color: var(--color-neutral-800, #1f2937);
  cursor: pointer;
}

.pdf-reference__nav {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.pdf-reference__nav-btn {
  padding: 0.25rem 0.625rem;
  border: 1px solid var(--color-neutral-300, #d1d5db);
  border-radius: 0.375rem;
  background: #fff;
  font-size: 0.8125rem;
  cursor: pointer;
  transition: background 0.15s;
}

.pdf-reference__nav-btn:hover:not(:disabled) {
  background: var(--color-neutral-200, #e5e7eb);
}

.pdf-reference__nav-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.pdf-reference__page-indicator {
  font-size: 0.8125rem;
  color: var(--color-neutral-700, #374151);
  white-space: nowrap;
}

.pdf-reference__cluster {
  font-size: 0.75rem;
  color: var(--color-primary-600, #2563eb);
  background: var(--color-primary-50, #eff6ff);
  border: 1px solid var(--color-primary-200, #bfdbfe);
  border-radius: 9999px;
  padding: 0.125rem 0.625rem;
  white-space: nowrap;
}

.pdf-reference__zoom {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  margin-left: auto;
}

.pdf-reference__zoom-btn {
  width: 1.75rem;
  height: 1.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-neutral-300, #d1d5db);
  border-radius: 0.375rem;
  background: #fff;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  line-height: 1;
  transition: background 0.15s;
}

.pdf-reference__zoom-btn:hover:not(:disabled) {
  background: var(--color-neutral-200, #e5e7eb);
}

.pdf-reference__zoom-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.pdf-reference__zoom-level {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-neutral-700, #374151);
  min-width: 2.5rem;
  text-align: center;
}

.pdf-reference__error {
  padding: 0.75rem 1rem;
  margin: 0.75rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  color: #dc2626;
  font-size: 0.875rem;
}

.pdf-reference__loading,
.pdf-reference__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  font-size: 0.9375rem;
  color: var(--color-neutral-500, #6b7280);
}

.pdf-reference__canvas-wrapper {
  flex: 1;
  overflow: auto;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 0.75rem;
}

.pdf-reference__canvas-inner {
  position: relative;
  display: inline-block;
}

.pdf-reference__canvas {
  max-width: 100%;
  border-radius: 0.5rem;
  border: 1px solid var(--color-neutral-200, #e5e7eb);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.pdf-reference__canvas--hidden {
  display: none;
}
</style>
