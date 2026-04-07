import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { ConfidenceFactors, ConfidenceThreshold, BackendWarning } from '@/types/confidence.types'
import { useLayoutStore } from './layout'

export const useConfidenceStore = defineStore('confidence', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const confidenceByLayout = ref<Map<string, ConfidenceFactors>>(new Map())

  // Story 30.5 — backend warnings from pipeline processing
  const backendWarnings = ref<BackendWarning[]>([])

  // ─── Helpers ─────────────────────────────────────────────────────────────
  function computeThreshold(overall: number): ConfidenceThreshold {
    if (overall >= 95) return 'approved'
    if (overall >= 80) return 'review'
    return 'human_review'
  }

  // ─── Getters ─────────────────────────────────────────────────────────────
  function getForLayout(layoutId: string): ConfidenceFactors | undefined {
    return confidenceByLayout.value.get(layoutId)
  }

  const activeLayoutConfidence = computed<ConfidenceFactors | undefined>(() => {
    const layoutStore = useLayoutStore()
    const id = (layoutStore as unknown as { activeLayoutId?: string }).activeLayoutId
    if (!id) return undefined
    return confidenceByLayout.value.get(id)
  })

  const overallForActiveLayout = computed<number | undefined>(() => {
    return activeLayoutConfidence.value?.overall
  })

  const thresholdLevel = computed<ConfidenceThreshold>(() => {
    const confidence = activeLayoutConfidence.value
    if (!confidence) return 'human_review'
    return computeThreshold(confidence.overall)
  })

  // ─── Actions ─────────────────────────────────────────────────────────────
  function loadConfidence(data: Record<string, ConfidenceFactors>) {
    const map = new Map<string, ConfidenceFactors>()
    for (const [layoutId, factors] of Object.entries(data)) {
      map.set(layoutId, factors)
    }
    confidenceByLayout.value = map
  }

  function updateForLayout(layoutId: string, confidence: ConfidenceFactors) {
    confidenceByLayout.value.set(layoutId, confidence)
  }

  // Story 30.5 — backend warning actions
  function setBackendWarnings(warnings: BackendWarning[]) {
    backendWarnings.value = warnings
  }

  function clearBackendWarnings() {
    backendWarnings.value = []
  }

  return {
    confidenceByLayout,
    getForLayout,
    activeLayoutConfidence,
    overallForActiveLayout,
    thresholdLevel,
    loadConfidence,
    updateForLayout,
    backendWarnings,
    setBackendWarnings,
    clearBackendWarnings,
  }
})
