import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import type {
  CoverageData,
  CoverageThreshold,
  OverlayItemData,
  OverlayTarget,
} from '@/types/coverage.types'
import type { BackendOverlayItem, AnchorEntry } from '@/types/pipeline.types'
import { useLayoutStore } from './layout'
import { useTemplateStore } from './templateStore'

export const useCoverageStore = defineStore('coverage', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const coverageByLayout = ref<Map<string, CoverageData>>(new Map())
  // overlayDataByLayout: layoutId → { canvas: [...], pdf: [...] }
  const overlayDataByLayout = ref<Map<string, Record<OverlayTarget, OverlayItemData[]>>>(new Map())
  // Story 35.1: anchors by layout for SyncView
  const anchorsByLayout = ref<Map<string, AnchorEntry[]>>(new Map())

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

  function getAnchors(layoutId: string): AnchorEntry[] {
    return anchorsByLayout.value.get(layoutId) ?? []
  }

  function getOverlayData(layoutId: string, target: OverlayTarget): OverlayItemData[] {
    const byLayout = overlayDataByLayout.value.get(layoutId)
    if (!byLayout) return []
    return byLayout[target] ?? []
  }

  const activeLayoutCoverage = computed<CoverageData | undefined>(() => {
    const layoutStore = useLayoutStore()
    const id = layoutStore.activeLayoutId
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

  function loadAnchors(data: Record<string, AnchorEntry[]>) {
    const map = new Map<string, AnchorEntry[]>()
    for (const [layoutId, anchors] of Object.entries(data)) {
      map.set(layoutId, anchors)
    }
    anchorsByLayout.value = map
  }

  function loadOverlayItems(itemsByLayout: Record<string, BackendOverlayItem[]>) {
    const map = new Map<string, Record<OverlayTarget, OverlayItemData[]>>()
    for (const [layoutId, items] of Object.entries(itemsByLayout)) {
      const canvasItems: OverlayItemData[] = items.map((item) => ({
        elementId: item.node_id ?? 'unknown',
        boundingBox: {
          x: item.bbox_canvas.left,
          y: item.bbox_canvas.top,
          w: item.bbox_canvas.width,
          h: item.bbox_canvas.height,
        },
        status: item.status,
        type: item.overlay_type ?? 'field',
        overlay_type: item.overlay_type,
      }))
      const pdfItems: OverlayItemData[] = items.map((item) => ({
        elementId: item.node_id ?? 'unknown',
        boundingBox: {
          x: item.bbox_pdf.left,
          y: item.bbox_pdf.top,
          w: item.bbox_pdf.width,
          h: item.bbox_pdf.height,
        },
        status: item.status,
        type: item.overlay_type ?? 'field',
        overlay_type: item.overlay_type,
      }))
      map.set(layoutId, { canvas: canvasItems, pdf: pdfItems })
    }
    overlayDataByLayout.value = map
  }

  // ─── Story 34.3: Real-time coverage recalculation ───────────────────────
  /**
   * Recalculate coverage for the active layout by counting nodes with bindings.
   * This provides a local approximation — the backend calculates the authoritative
   * coverage, but this keeps the UI responsive during editing.
   */
  function recalculateCoverage() {
    const layoutStore = useLayoutStore()
    const templateStore = useTemplateStore()
    const layoutId = layoutStore.activeLayoutId
    if (!layoutId) return

    const existing = coverageByLayout.value.get(layoutId)
    if (!existing) return

    // Count bound fields (nodes with non-empty binding)
    const BINDABLE_TYPES = new Set(['field', 'value', 'likely_dynamic', 'dynamic'])
    let mappedFields = 0
    let totalBindable = 0
    for (const node of templateStore.flatNodes.values()) {
      if (!BINDABLE_TYPES.has(node.type)) continue
      totalBindable++
      if (node.binding) mappedFields++
    }

    // Preserve totals from backend, only update mapped counts
    const fields = { mapped: mappedFields, total: existing.fields.total || totalBindable }
    const tables = existing.tables
    const images = existing.images
    const charts = existing.charts

    // Recalculate percentage: fields 55% + tables 25% + images 10% + charts 10%
    const fPct = fields.total ? (fields.mapped / fields.total) * 100 : 0
    const tPct = tables.total ? (tables.mapped / tables.total) * 100 : 100
    const iPct = images.total ? (images.mapped / images.total) * 100 : 100
    const cPct = charts.total ? (charts.mapped / charts.total) * 100 : 100
    const percentage = Math.round(fPct * 0.55 + tPct * 0.25 + iPct * 0.1 + cPct * 0.1)

    const updated: CoverageData = { fields, tables, images, charts, percentage }
    coverageByLayout.value.set(layoutId, updated)
  }

  // Watch templateStore.mutationVersion for binding changes
  // Deferred — only set up watcher after first loadCoverage call
  let watcherInitialized = false
  function initWatcher() {
    if (watcherInitialized) return
    watcherInitialized = true
    const templateStore = useTemplateStore()
    watch(
      () => templateStore.bindingVersion,
      () => {
        recalculateCoverage()
      },
    )
  }

  // Wrap loadCoverage to also init watcher
  const _originalLoadCoverage = loadCoverage
  function loadCoverageWithWatcher(data: Record<string, CoverageData>) {
    _originalLoadCoverage(data)
    initWatcher()
  }

  return {
    coverageByLayout,
    overlayDataByLayout,
    anchorsByLayout,
    getForLayout,
    getAnchors,
    getOverlayData,
    activeLayoutCoverage,
    thresholdLevel,
    loadCoverage: loadCoverageWithWatcher,
    updateForLayout,
    loadOverlayData,
    loadOverlayItems,
    loadAnchors,
    setOverlayData,
    recalculateCoverage,
  }
})
