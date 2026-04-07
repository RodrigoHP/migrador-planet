import { ref, markRaw, onUnmounted } from 'vue'
import { useEditorStore } from '@/stores/editorStore'

let pdfjsLib: typeof import('pdfjs-dist') | null = null

async function ensurePdfJs() {
  if (pdfjsLib) return pdfjsLib
  const lib = await import('pdfjs-dist')
  const worker = await import('pdfjs-dist/build/pdf.worker.min.mjs?url')
  lib.GlobalWorkerOptions.workerSrc = worker.default
  pdfjsLib = lib
  return lib
}

export function usePdfRenderer() {
  const editorStore = useEditorStore()

  const pdfDocument = ref<any>(null)
  const currentPage = ref<number>(1)
  const totalPages = ref<number>(0)
  const isLoading = ref<boolean>(false)
  const error = ref<string | null>(null)

  let renderGeneration = 0

  /** Load a PDF from a URL or ArrayBuffer */
  async function loadPdf(source: string | ArrayBuffer) {
    isLoading.value = true
    error.value = null
    try {
      // Cleanup previous document
      if (pdfDocument.value) {
        await pdfDocument.value.destroy()
        pdfDocument.value = null
      }
      const lib = await ensurePdfJs()
      // pdfjs-dist v5.x transfers the ArrayBuffer to the Web Worker, detaching it.
      // Passing a Uint8Array copy avoids the "Cannot perform Construct on a detached
      // ArrayBuffer" error because pdfjs handles typed arrays differently from raw buffers.
      const data = source instanceof ArrayBuffer ? new Uint8Array(source.slice(0)) : source
      const src = typeof data === 'string' ? data : { data }
      const task = lib.getDocument(src)
      const doc = await task.promise
      pdfDocument.value = markRaw(doc)
      totalPages.value = doc.numPages
      currentPage.value = 1
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Erro ao carregar PDF'
    } finally {
      isLoading.value = false
    }
  }

  /** Render the current page on the provided canvas element */
  async function renderPage(pageNum: number, canvas: HTMLCanvasElement) {
    if (!pdfDocument.value || !canvas) return
    const generation = ++renderGeneration
    isLoading.value = true
    try {
      const page = await pdfDocument.value.getPage(pageNum)
      if (generation !== renderGeneration) return

      const scale = editorStore.pdfZoom / 100
      const viewport = page.getViewport({ scale, rotation: 0 })
      const context = canvas.getContext('2d')
      if (!context) return

      canvas.width = viewport.width
      canvas.height = viewport.height
      const task = page.render({ canvasContext: context, viewport })
      await task.promise
    } catch (err) {
      if (err instanceof Error && err.name === 'RenderingCancelledException') return
      error.value = err instanceof Error ? err.message : 'Erro ao renderizar página'
    } finally {
      isLoading.value = false
    }
  }

  function nextPage() {
    if (currentPage.value < totalPages.value) {
      currentPage.value++
    }
  }

  function prevPage() {
    if (currentPage.value > 1) {
      currentPage.value--
    }
  }

  function goToPage(num: number) {
    const clamped = Math.min(Math.max(1, num), totalPages.value || 1)
    currentPage.value = clamped
  }

  function zoomIn() {
    const next = Math.min(200, editorStore.pdfZoom + 10)
    editorStore.setPdfZoom(next)
  }

  function zoomOut() {
    const next = Math.max(50, editorStore.pdfZoom - 10)
    editorStore.setPdfZoom(next)
  }

  function setZoom(level: number) {
    const clamped = Math.min(200, Math.max(50, level))
    editorStore.setPdfZoom(clamped)
  }

  onUnmounted(async () => {
    if (pdfDocument.value) {
      await pdfDocument.value.destroy()
      pdfDocument.value = null
    }
  })

  return {
    pdfDocument,
    currentPage,
    totalPages,
    isLoading,
    error,
    loadPdf,
    renderPage,
    nextPage,
    prevPage,
    goToPage,
    zoomIn,
    zoomOut,
    setZoom,
  }
}
