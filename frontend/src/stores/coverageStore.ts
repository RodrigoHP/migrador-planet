import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { CoverageData, CoverageThreshold, OverlayItemData, OverlayTarget } from '@/types/coverage.types'
import type { BackendOverlayItem } from '@/types/pipeline.types'
import { useLayoutStore } from './layout'

export const useCoverageStore = defineStore('coverage', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const coverageByLayout = ref<Map<string, CoverageData>>(new Map())
  // overlayDataByLayout: layoutId → { canvas: [...], pdf: [...] }
  const overlayDataByLayout = ref<Map<string, Record<OverlayTarget, OverlayItemData[]>>>(new Map())

  // ─── Helpers ─────────────────────────────────────────────────────────────
  function computeThreshold(percentage: number): CoverageThreshold {
    if (percentage >= 95) return 'complete'
    if (percentage >= 80) return 'review'
    return 'incomplete'
  }

  // ─── Getters ─────────────────────────────────────────────────────────────
  function getForLayout(layoutId: string): CoverageData | undefined {
    return coverageByLayout.value.get(layoutId)
  }

  function getOverlayData(layoutId: string, target: OverlayTarget): OverlayItemData[] {
    const byLayout = overlayDataByLayout.value.get(layoutId)
    if (!byLayout) return []
    return byLayout[target] ?? []
  }

  const activeLayoutCoverage = computed<CoverageData | undefined>(() => {
    const layoutStore = useLayoutStore()
    const id = (layoutStore as unknown as { activeLayoutId?: string }).activeLayoutId
    if (!id) return undefined
    return coverageByLayout.value.get(id)
  })

  const thresholdLevel = computed<CoverageThreshold>(() => {
    const coverage = activeLayoutCoverage.value
    if (!coverage) return 'incomplete'
    return computeThreshold(coverage.percentage)
  })

  // ─── Actions ─────────────────────────────────────────────────────────────
  function loadCoverage(data: Record<string, CoverageData>) {
    const map = new Map<string, CoverageData>()
    for (const [layoutId, coverage] of Object.entries(data)) {
      map.set(layoutId, coverage)
    }
    coverageByLayout.value = map
  }

  function updateForLayout(layoutId: string, coverage: CoverageData) {
    coverageByLayout.value.set(layoutId, coverage)
  }

  function loadOverlayData(data: Record<string, Record<OverlayTarget, OverlayItemData[]>>) {
    const map = new Map<string, Record<OverlayTarget, OverlayItemData[]>>()
    for (const [layoutId, targets] of Object.entries(data)) {
      map.set(layoutId, targets)
    }
    overlayDataByLayout.value = map
  }

  function setOverlayData(layoutId: string, target: OverlayTarget, items: OverlayItemData[]) {
    const existing = overlayDataByLayout.value.get(layoutId) ?? { canvas: [], pdf: [] }
    existing[target] = items
    overlayDataByLayout.value.set(layoutId, existing)
  }

  function loadOverlayItems(itemsByLayout: Record<string, BackendOverlayItem[]>) {
    const map = new Map<string, Record<OverlayTarget, OverlayItemData[]>>()
    for (const [layoutId, items] of Object.entries(itemsByLayout)) {
      const canvasItems: OverlayItemData[] = items.map(item => ({
        elementId: item.node_id ?? 'unknown',
        boundingBox: { x: item.bbox_canvas.left, y: item.bbox_canvas.top, w: item.bbox_canvas.width, h: item.bbox_canvas.height },
        status: item.status,
        type: item.overlay_type ?? 'field',
        overlay_type: item.overlay_type,
      }))
      const pdfItems: OverlayItemData[] = items.map(item => ({
        elementId: item.node_id ?? 'unknown',
        boundingBox: { x: item.bbox_pdf.left, y: item.bbox_pdf.top, w: item.bbox_pdf.width, h: item.bbox_pdf.height },
        status: item.status,
        type: item.overlay_type ?? 'field',
        overlay_type: item.overlay_type,
      }))
      map.set(layoutId, { canvas: canvasItems, pdf: pdfItems })
    }
    overlayDataByLayout.value = map
  }

  return {
    coverageByLayout,
    overlayDataByLayout,
    getForLayout,
    getOverlayData,
    activeLayoutCoverage,
    thresholdLevel,
    loadCoverage,
    updateForLayout,
    loadOverlayData,
    loadOverlayItems,
    setOverlayData,
  }
})
