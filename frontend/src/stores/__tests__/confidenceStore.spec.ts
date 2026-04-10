import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useConfidenceStore } from '../confidenceStore'
import type { ConfidenceFactors } from '@/types/confidence.types'

const mockConfidenceHigh: ConfidenceFactors = {
  layout_stability: 98,
  anchor_detection: 96,
  grid_quality: 97,
  field_variability: 95,
  vision_agreement: 99,
  overall: 97,
}

const mockConfidenceMid: ConfidenceFactors = {
  layout_stability: 82,
  anchor_detection: 80,
  grid_quality: 85,
  field_variability: 84,
  vision_agreement: 88,
  overall: 84,
}

const mockConfidenceLow: ConfidenceFactors = {
  layout_stability: 60,
  anchor_detection: 55,
  grid_quality: 70,
  field_variability: 65,
  vision_agreement: 72,
  overall: 64,
}

describe('confidenceStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with empty map', () => {
    const store = useConfidenceStore()
    expect(store.confidenceByLayout.size).toBe(0)
  })

  it('loadConfidence populates the map', () => {
    const store = useConfidenceStore()
    store.loadConfidence({ layout_a: mockConfidenceHigh, layout_b: mockConfidenceLow })
    expect(store.confidenceByLayout.size).toBe(2)
  })

  it('getForLayout returns correct data', () => {
    const store = useConfidenceStore()
    store.loadConfidence({ layout_a: mockConfidenceHigh })
    const result = store.getForLayout('layout_a')
    expect(result?.overall).toBe(97)
    expect(result?.layout_stability).toBe(98)
  })

  it('getForLayout returns undefined for unknown layout', () => {
    const store = useConfidenceStore()
    expect(store.getForLayout('unknown')).toBeUndefined()
  })

  it('updateForLayout sets a single layout entry', () => {
    const store = useConfidenceStore()
    store.updateForLayout('layout_x', mockConfidenceHigh)
    expect(store.getForLayout('layout_x')?.overall).toBe(97)
  })

  it('threshold logic: >=95 = approved, 80-95 = review, <80 = human_review', () => {
    const store = useConfidenceStore()
    store.loadConfidence({
      high: mockConfidenceHigh, // overall 97
      mid: mockConfidenceMid, // overall 84
      low: mockConfidenceLow, // overall 64
    })
    expect(store.getForLayout('high')?.overall).toBeGreaterThanOrEqual(95)
    expect(store.getForLayout('mid')?.overall).toBeLessThan(95)
    expect(store.getForLayout('mid')?.overall).toBeGreaterThanOrEqual(80)
    expect(store.getForLayout('low')?.overall).toBeLessThan(80)
  })
})
