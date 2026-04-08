import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useMultiDocStore } from '@/stores/multiDocStore'
import { useTemplateStore } from '@/stores/templateStore'
import { useCoverageStore } from '@/stores/coverageStore'

// ─── Types ────────────────────────────────────────────────────────────────────

export type DiffType = 'identical' | 'moved' | 'added' | 'removed'

export interface DiffBounds {
  x: number
  y: number
  w: number
  h: number
}

export interface DiffItem {
  elementId: string
  diffType: DiffType
  boundsA?: DiffBounds
  boundsB?: DiffBounds
}

export interface DiffInference {
  id: string
  type: string
  description: string
  confidence: number
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useDiffStore = defineStore('diff', () => {
  // ─── State ──────────────────────────────────────────────────────────────
  const isActive = ref<boolean>(false)
  const documentA = ref<string | null>(null)
  const documentB = ref<string | null>(null)
  const diffData = ref<DiffItem[]>([])
  const inferences = ref<DiffInference[]>([])

  // ─── Getters ─────────────────────────────────────────────────────────────
  const highlightsByType = computed<Record<DiffType, DiffItem[]>>(() => {
    const result: Record<DiffType, DiffItem[]> = {
      identical: [],
      moved: [],
      added: [],
      removed: [],
    }
    for (const item of diffData.value) {
      result[item.diffType].push(item)
    }
    return result
  })

  /** Story 35.3: Summary counts by diff type */
  const diffSummary = computed<Record<DiffType, number>>(() => {
    const counts: Record<DiffType, number> = { identical: 0, moved: 0, added: 0, removed: 0 }
    for (const item of diffData.value) {
      counts[item.diffType]++
    }
    return counts
  })

  // ─── Actions ─────────────────────────────────────────────────────────────
  function toggleDiffMode() {
    isActive.value = !isActive.value
  }

  function setDocuments(docA: string, docB: string) {
    documentA.value = docA
    documentB.value = docB
    computeDiff()
  }

  /**
   * Compute diff between documentA and documentB.
   * Uses template nodes as a proxy for element identity.
   * Algorithm: compare by elementId — if present in both layouts → check position.
   * Positions are approximated from node properties (x, y, w, h).
   */
  function computeDiff() {
    if (!documentA.value || !documentB.value) {
      diffData.value = []
      inferences.value = []
      return
    }

    const templateStore = useTemplateStore()
    const multiDocStore = useMultiDocStore()

    // Use template nodes as elements. Each node has an id and optional bounds.
    const allNodes = Array.from(templateStore.flatNodes?.values() ?? [])

    const pdfList = multiDocStore.pdfList
    const idxA = pdfList.findIndex((p) => p.id === documentA.value)
    const idxB = pdfList.findIndex((p) => p.id === documentB.value)

    const items: DiffItem[] = []

    // Simplified diff: compare nodes using the variationMatrix (if available)
    const matrix = multiDocStore.variationMatrix

    if (matrix && idxA >= 0 && idxB >= 0) {
      // Determine which doc IDs are at idxA and idxB
      const docAId = pdfList[idxA]?.id ?? ''
      const docBId = pdfList[idxB]?.id ?? ''

      // Story 35.5: Use overlay data from coverageStore for per-document bbox
      const coverageStore = useCoverageStore()

      // Build per-doc overlay maps for accurate bbox lookup
      const overlayCanvasA = coverageStore.getOverlayData(docAId, 'canvas')
      const overlayCanvasB = coverageStore.getOverlayData(docBId, 'canvas')
      const overlayPdfA = coverageStore.getOverlayData(docAId, 'pdf')
      const overlayPdfB = coverageStore.getOverlayData(docBId, 'pdf')

      for (const layoutId of matrix.layoutIds) {
        const row = matrix.cells[layoutId]
        if (!row) continue

        const inA = row[docAId] ?? false
        const inB = row[docBId] ?? false

        if (!inA && !inB) continue

        // Find node matching this layoutId
        const node = allNodes.find((n) => n.binding === layoutId || n.id === layoutId)
        const props = node?.properties as Record<string, unknown> | undefined

        // Try overlay data first, fallback to node props
        const overlayA = overlayCanvasA.find((o) => o.elementId === layoutId)
        const overlayB = overlayCanvasB.find((o) => o.elementId === layoutId)

        const boundsA: DiffBounds | undefined =
          inA
            ? overlayA
              ? { x: overlayA.boundingBox.x, y: overlayA.boundingBox.y, w: overlayA.boundingBox.w, h: overlayA.boundingBox.h }
              : props?.x !== undefined
                ? { x: (props.x as number) ?? 0, y: (props.y as number) ?? 0, w: (props.width as number) ?? 100, h: (props.height as number) ?? 20 }
                : undefined
            : undefined

        const boundsB: DiffBounds | undefined =
          inB
            ? overlayB
              ? { x: overlayB.boundingBox.x, y: overlayB.boundingBox.y, w: overlayB.boundingBox.w, h: overlayB.boundingBox.h }
              : props?.x !== undefined
                ? { x: (props.x as number) ?? 0, y: (props.y as number) ?? 0, w: (props.width as number) ?? 100, h: (props.height as number) ?? 20 }
                : undefined
            : undefined

        // Story 35.3: Detect 'moved' — present in both but position differs > 5px
        let diffType: DiffType
        if (inA && inB) {
          if (boundsA && boundsB && (Math.abs(boundsA.x - boundsB.x) > 5 || Math.abs(boundsA.y - boundsB.y) > 5)) {
            diffType = 'moved'
          } else {
            diffType = 'identical'
          }
        } else if (inA && !inB) {
          diffType = 'removed'
        } else {
          diffType = 'added'
        }

        items.push({ elementId: layoutId, diffType, boundsA, boundsB })
      }
    } else {
      // Fallback: use all template nodes, mark as identical (no matrix)
      for (const node of allNodes) {
        const props = node.properties as Record<string, unknown> | undefined
        const bounds: DiffBounds | undefined =
          props?.x !== undefined
            ? {
                x: (props.x as number) ?? 0,
                y: (props.y as number) ?? 0,
                w: (props.width as number) ?? 100,
                h: (props.height as number) ?? 20,
              }
            : undefined

        items.push({ elementId: node.id, diffType: 'identical', boundsA: bounds, boundsB: bounds })
      }
    }

    diffData.value = items

    // Derive inferences from diff items
    inferences.value = items
      .filter((i) => i.diffType !== 'identical')
      .map((item) => ({
        id: item.elementId,
        type: item.diffType,
        description: inferenceDescription(item),
        confidence: item.diffType === 'moved' ? 0.7 : 0.9,
      }))
  }

  function inferenceDescription(item: DiffItem): string {
    switch (item.diffType) {
      case 'moved':
        return `Elemento "${item.elementId}" está em posição diferente nos dois documentos`
      case 'added':
        return `Elemento "${item.elementId}" presente apenas no Documento B`
      case 'removed':
        return `Elemento "${item.elementId}" presente apenas no Documento A`
      default:
        return `Elemento "${item.elementId}" idêntico nos dois documentos`
    }
  }

  /** Delegates to multiDocStore.confirmDetection */
  function confirmInference(id: string) {
    const multiDocStore = useMultiDocStore()
    multiDocStore.confirmDetection(id)
    inferences.value = inferences.value.filter((inf) => inf.id !== id)
  }

  /** Delegates to multiDocStore.rejectDetection */
  function rejectInference(id: string) {
    const multiDocStore = useMultiDocStore()
    multiDocStore.rejectDetection(id)
    inferences.value = inferences.value.filter((inf) => inf.id !== id)
    diffData.value = diffData.value.filter((item) => item.elementId !== id)
  }

  return {
    isActive,
    documentA,
    documentB,
    diffData,
    inferences,
    highlightsByType,
    diffSummary,
    toggleDiffMode,
    setDocuments,
    computeDiff,
    confirmInference,
    rejectInference,
  }
})
