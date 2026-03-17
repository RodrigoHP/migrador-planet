import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { PdfDocument, VariationMatrix, Detection } from '@/types/multi-doc.types'

export const useMultiDocStore = defineStore('multiDoc', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const pdfList = ref<PdfDocument[]>([])
  const variationMatrix = ref<VariationMatrix | null>(null)
  const detections = ref<Detection[]>([])

  // ─── Getters ─────────────────────────────────────────────────────────────
  const baseDocuments = computed<PdfDocument[]>(() =>
    pdfList.value.filter((p) => p.role === 'base'),
  )

  const variationDocuments = computed<PdfDocument[]>(() =>
    pdfList.value.filter((p) => p.role === 'variation'),
  )

  // ─── Actions ─────────────────────────────────────────────────────────────
  function addPdf(pdf: PdfDocument) {
    pdfList.value.push(pdf)
  }

  function removePdf(id: string) {
    pdfList.value = pdfList.value.filter((p) => p.id !== id)
  }

  function setVariationMatrix(matrix: VariationMatrix) {
    variationMatrix.value = matrix
  }

  function setDetections(items: Detection[]) {
    detections.value = items
  }

  // Placeholder for Epic 9 — multi-doc analysis engine
  function analyzeVariations(): Promise<void> {
    return Promise.resolve()
  }

  return {
    pdfList,
    variationMatrix,
    detections,
    baseDocuments,
    variationDocuments,
    addPdf,
    removePdf,
    setVariationMatrix,
    setDetections,
    analyzeVariations,
  }
})
