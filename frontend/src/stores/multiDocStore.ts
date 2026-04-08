import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { PdfDocument, VariationMatrix, Detection, PipelineResult } from '@/types/multi-doc.types'
import { useTemplateStore } from '@/stores/templateStore'

export const useMultiDocStore = defineStore('multiDoc', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const pdfList = ref<PdfDocument[]>([])
  const variationMatrix = ref<VariationMatrix | null>(null)
  const detections = ref<Detection[]>([])
  const confirmedDetections = ref<Set<string>>(new Set())

  // ─── Getters ─────────────────────────────────────────────────────────────
  const baseDocuments = computed<PdfDocument[]>(() =>
    pdfList.value.filter((p) => p.role === 'base'),
  )

  const variationDocuments = computed<PdfDocument[]>(() =>
    pdfList.value.filter((p) => p.role === 'variation'),
  )

  /** AC #2 — show analyzer only when multiple PDFs are present */
  const hasMultiplePdfs = computed<boolean>(() => pdfList.value.length > 1)

  /** Active (non-rejected) detections */
  const activeDetections = computed<Detection[]>(() => detections.value)

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

  /** Add a single detection (e.g. from operator visibility change — Story 14.13) */
  function addDetection(detection: Detection) {
    detections.value = [...detections.value, detection]
  }

  /** Remove detection by description label match (Story 14.13 — bidirectional sync) */
  function removeDetectionByLabel(label: string) {
    detections.value = detections.value.filter(
      (d) => !d.description.includes(label),
    )
  }

  /**
   * Populate store from a pipeline analysis result.
   * AC #3 / #4 / #5 — fills pdfs, matrix, and detections in one call.
   */
  function populateFromPipeline(pipelineResult: PipelineResult) {
    pdfList.value = pipelineResult.pdfs
    variationMatrix.value = pipelineResult.matrix
    detections.value = pipelineResult.detections
    confirmedDetections.value = new Set()
  }

  /**
   * AC #6 / #7 — Operator confirms an inference.
   * Updates templateStore if a nodeBinding is present on the detection.
   */
  function confirmDetection(id: string) {
    confirmedDetections.value = new Set([...confirmedDetections.value, id])

    const detection = detections.value.find((d) => d.id === id)
    if (!detection) return

    // useTemplateStore is safe to call here (inside an action, after Pinia is up)
    const templateStore = useTemplateStore()

    if (!detection.nodeBinding) return

    const nodes = templateStore.getNodesByType('field')
    const target = nodes.find((n) => n.binding === detection.nodeBinding)
    if (!target) return

    if (detection.type === 'required') {
      templateStore.updateNodeProperties(target.id, { visibility: { mode: 'always' } })
    } else if (detection.type === 'optional_field') {
      templateStore.updateNodeProperties(target.id, {
        visibility: { mode: 'conditional', conditions: [] },
        koIf: detection.nodeBinding,
      })
    } else if (detection.type === 'optional_section' || detection.type === 'conditional_section') {
      // Story 35.8: Apply ko if to all grouped blocks if available
      if (detection.groupedBlocks?.length) {
        for (const blockId of detection.groupedBlocks) {
          const blockNode = nodes.find((n) => n.binding === blockId)
          if (blockNode) {
            templateStore.updateNodeProperties(blockNode.id, {
              visibility: { mode: 'conditional', conditions: [] },
              koIf: blockId,
            })
          }
        }
      } else {
        templateStore.updateNodeProperties(target.id, {
          visibility: { mode: 'conditional', conditions: [] },
          koIf: detection.nodeBinding,
        })
      }
    } else if (detection.type === 'dynamic_table') {
      templateStore.updateNodeProperties(target.id, {
        foreach: detection.nodeBinding,
        dynamicRows: true,
      })
    }
  }

  /**
   * AC #6 — Operator rejects an inference; removes it from active detections.
   */
  function rejectDetection(id: string) {
    detections.value = detections.value.filter((d) => d.id !== id)
    const next = new Set(confirmedDetections.value)
    next.delete(id)
    confirmedDetections.value = next
  }

  /**
   * Derive detections automatically from the variation matrix.
   * AC #5 — applies detection rules based on field presence across documents.
   */
  function analyzeVariations(): Promise<void> {
    if (!variationMatrix.value) return Promise.resolve()

    const matrix = variationMatrix.value
    // total doc count = base (1) + variations
    const docCount = matrix.variationIds.length + 1
    const generatedDetections: Detection[] = []
    let idx = 0

    for (const layoutId of matrix.layoutIds) {
      const rowCells = matrix.cells[layoutId]
      if (!rowCells) continue

      const presenceValues = Object.values(rowCells)
      const presentCount = presenceValues.filter(Boolean).length

      let type: Detection['type']
      let description: string

      if (presentCount === docCount) {
        // AC #5a: present in all docs → required field
        type = 'required'
        description = `Campo "${layoutId}" presente em todos os documentos → campo obrigatório`
      } else if (presentCount > 1 && presentCount < docCount) {
        // AC #5b: present in some → optional field (ko if)
        type = 'optional_field'
        description = `Campo "${layoutId}" presente em ${presentCount}/${docCount} documentos → campo opcional (ko if: ${layoutId})`
      } else if (presentCount === 1) {
        // AC #5d: present in only 1 → conditional section
        type = 'conditional_section'
        description = `Campo "${layoutId}" presente em apenas 1 documento → seção condicional`
      } else {
        continue
      }

      generatedDetections.push({
        id: `det-${idx++}-${layoutId}`,
        pdfId: '',
        type,
        description,
        confidence:
          presentCount === docCount
            ? 1.0
            : Math.round((presentCount / docCount) * 100) / 100,
        nodeBinding: layoutId,
      })
    }

    detections.value = generatedDetections
    return Promise.resolve()
  }

  return {
    pdfList,
    variationMatrix,
    detections,
    confirmedDetections,
    baseDocuments,
    variationDocuments,
    hasMultiplePdfs,
    activeDetections,
    addPdf,
    removePdf,
    setVariationMatrix,
    setDetections,
    addDetection,
    removeDetectionByLabel,
    populateFromPipeline,
    confirmDetection,
    rejectDetection,
    analyzeVariations,
  }
})
