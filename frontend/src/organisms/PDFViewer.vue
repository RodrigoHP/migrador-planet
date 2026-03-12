<template>
  <div class="pdf-viewer">
    <header class="pdf-viewer__header">
      <strong>PDF</strong>
      <div class="pdf-viewer__pager">
        <button type="button" :disabled="currentPage <= 1 || isLoading" @click="goTo(currentPage - 1)">Anterior</button>
        <span>{{ currentPage }} / {{ totalPages }}</span>
        <button type="button" :disabled="currentPage >= totalPages || isLoading" @click="goTo(currentPage + 1)">Próxima</button>
      </div>
    </header>

    <p v-if="!pdfBytes" class="pdf-viewer__empty">PDF indisponível para visualização.</p>
    <canvas v-else ref="canvasRef" class="pdf-viewer__canvas" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

type Box = { x: number; y: number; width: number; height: number } | null

const props = defineProps<{
  pdfBytes: ArrayBuffer | null
  pageRef: number | null
  boundingBox: Box
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const currentPage = ref(1)
const totalPages = ref(1)
const isLoading = ref(false)

let pdfjsLib: typeof import('pdfjs-dist') | null = null
let pdfDoc: any = null

async function ensurePdfJs() {
  if (pdfjsLib) return pdfjsLib
  const lib = await import('pdfjs-dist')
  const worker = await import('pdfjs-dist/build/pdf.worker.min.mjs?url')
  lib.GlobalWorkerOptions.workerSrc = worker.default
  pdfjsLib = lib
  return lib
}

async function loadDocument() {
  if (!props.pdfBytes) return
  const lib = await ensurePdfJs()
  isLoading.value = true
  try {
    const loadingTask = lib.getDocument({ data: props.pdfBytes })
    pdfDoc = await loadingTask.promise
    totalPages.value = pdfDoc.numPages
    currentPage.value = Math.min(Math.max(1, props.pageRef ?? 1), totalPages.value)
    await renderPage()
  } finally {
    isLoading.value = false
  }
}

async function renderPage() {
  if (!pdfDoc || !canvasRef.value) return
  const page = await pdfDoc.getPage(currentPage.value)
  const viewport = page.getViewport({ scale: 1.2 })
  const canvas = canvasRef.value
  const context = canvas.getContext('2d')
  if (!context) return

  canvas.width = viewport.width
  canvas.height = viewport.height
  await page.render({ canvasContext: context, viewport }).promise

  if (props.boundingBox) {
    context.save()
    context.strokeStyle = '#ef4444'
    context.lineWidth = 2
    context.strokeRect(
      props.boundingBox.x,
      props.boundingBox.y,
      props.boundingBox.width,
      props.boundingBox.height,
    )
    context.restore()
  }
}

async function goTo(pageNumber: number) {
  if (!pdfDoc) return
  currentPage.value = Math.min(Math.max(1, pageNumber), totalPages.value)
  await renderPage()
}

watch(() => props.pdfBytes, async () => {
  if (props.pdfBytes) await loadDocument()
}, { immediate: true })

watch(() => props.pageRef, async (pageRef) => {
  if (pageRef && pageRef > 0 && totalPages.value > 0) {
    currentPage.value = Math.min(Math.max(1, pageRef), totalPages.value)
    await renderPage()
  }
})

watch(() => props.boundingBox, async () => {
  await renderPage()
})

</script>

<style scoped>
.pdf-viewer {
  display: grid;
  gap: 0.75rem;
}

.pdf-viewer__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.pdf-viewer__pager {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.pdf-viewer__pager button {
  border: 1px solid var(--color-neutral-200);
  background: #fff;
  border-radius: 0.5rem;
  padding: 0.35rem 0.6rem;
  cursor: pointer;
}

.pdf-viewer__pager button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pdf-viewer__empty {
  margin: 0;
  color: var(--color-neutral-700);
}

.pdf-viewer__canvas {
  width: 100%;
  border-radius: 0.5rem;
  border: 1px solid var(--color-neutral-200);
}
</style>
