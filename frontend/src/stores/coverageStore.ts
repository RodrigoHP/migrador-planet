import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { CoverageData, CoverageThreshold, OverlayItemData, OverlayTarget } from '@/types/coverage.types'
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
    setOverlayData,
  }
})
