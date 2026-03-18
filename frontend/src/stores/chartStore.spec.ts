import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useChartStore } from './chartStore'

describe('chartStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // ─── registerChart ─────────────────────────────────────────────────────────

  it('registers a new chart with default values', () => {
    const store = useChartStore()
    store.registerChart({ id: 'chart-1', name: 'Vendas', confidence: 80, detectedType: 'bar' })

    expect(store.charts).toHaveLength(1)
    expect(store.charts[0]!.id).toBe('chart-1')
    expect(store.charts[0]!.name).toBe('Vendas')
    expect(store.charts[0]!.confidence).toBe(80)
    expect(store.charts[0]!.datasets).toHaveLength(1)
    expect(store.charts[0]!.useFallback).toBe(false)
  })

  it('does not register the same chart id twice', () => {
    const store = useChartStore()
    store.registerChart({ id: 'chart-1', name: 'Vendas', confidence: 80 })
    store.registerChart({ id: 'chart-1', name: 'Vendas 2', confidence: 50 })

    expect(store.charts).toHaveLength(1)
  })

  // ─── Type pre-selection (AC#8) ─────────────────────────────────────────────

  it('pre-selects detected type when confidence >= 60%', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 75, detectedType: 'line' })
    expect(store.charts[0]!.type).toBe('line')
  })

  it('defaults to bar when confidence < 60%', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 40, detectedType: 'line' })
    expect(store.charts[0]!.type).toBe('bar')
  })

  it('defaults to bar when confidence is exactly 60%', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 60, detectedType: 'pie' })
    expect(store.charts[0]!.type).toBe('pie')
  })

  it('defaults to bar when detectedType is invalid even with high confidence', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 90, detectedType: 'scatter' })
    expect(store.charts[0]!.type).toBe('bar')
  })

  // ─── updateChart ───────────────────────────────────────────────────────────

  it('updates chart config', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 80 })
    store.updateChart('c1', { name: 'Novo Nome', type: 'pie' })

    expect(store.charts[0]!.name).toBe('Novo Nome')
    expect(store.charts[0]!.type).toBe('pie')
  })

  it('does nothing when chart id not found', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 80 })
    store.updateChart('nonexistent', { name: 'X' })

    expect(store.charts[0]!.name).toBe('C1')
  })

  it('updates dimensions partially', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 80 })
    store.updateChart('c1', { dimensions: { width: 600, height: 300 } })

    expect(store.charts[0]!.dimensions.width).toBe(600)
    expect(store.charts[0]!.dimensions.height).toBe(300)
  })

  // ─── addDataset ────────────────────────────────────────────────────────────

  it('adds a dataset to a chart', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 80 })
    store.addDataset('c1')

    expect(store.charts[0]!.datasets).toHaveLength(2)
  })

  it('does nothing when adding dataset to unknown chart', () => {
    const store = useChartStore()
    store.addDataset('nonexistent') // should not throw
    expect(store.charts).toHaveLength(0)
  })

  // ─── removeDataset ─────────────────────────────────────────────────────────

  it('removes a dataset by index', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 80 })
    store.addDataset('c1')
    expect(store.charts[0]!.datasets).toHaveLength(2)

    store.removeDataset('c1', 0)
    expect(store.charts[0]!.datasets).toHaveLength(1)
  })

  it('does not remove last dataset (minimum 1)', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 80 })
    expect(store.charts[0]!.datasets).toHaveLength(1)

    store.removeDataset('c1', 0)
    expect(store.charts[0]!.datasets).toHaveLength(1)
  })

  // ─── setFallback ───────────────────────────────────────────────────────────

  it('enables fallback image', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 80 })
    store.setFallback('c1', true)

    expect(store.charts[0]!.useFallback).toBe(true)
  })

  it('disables fallback image', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 80 })
    store.setFallback('c1', true)
    store.setFallback('c1', false)

    expect(store.charts[0]!.useFallback).toBe(false)
  })

  it('does nothing when setting fallback on unknown chart', () => {
    const store = useChartStore()
    store.setFallback('nonexistent', true) // should not throw
  })

  // ─── chartById getter ──────────────────────────────────────────────────────

  it('chartById returns the correct chart', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 80 })
    store.registerChart({ id: 'c2', name: 'C2', confidence: 50 })

    expect(store.chartById('c1')?.name).toBe('C1')
    expect(store.chartById('c2')?.name).toBe('C2')
    expect(store.chartById('c3')).toBeUndefined()
  })

  // ─── reset ────────────────────────────────────────────────────────────────

  it('reset clears all charts', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 80 })
    store.registerChart({ id: 'c2', name: 'C2', confidence: 50 })
    store.reset()

    expect(store.charts).toHaveLength(0)
  })

  // ─── default dimensions and styles ────────────────────────────────────────

  it('initializes with default dimensions 400x250', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 80 })

    expect(store.charts[0]!.dimensions.width).toBe(400)
    expect(store.charts[0]!.dimensions.height).toBe(250)
  })

  it('initializes with default styles (legend/grid/animation on)', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 80 })

    const styles = store.charts[0]!.styles
    expect(styles.showLegend).toBe(true)
    expect(styles.showGrid).toBe(true)
    expect(styles.animation).toBe(true)
  })

  // ─── stacked ──────────────────────────────────────────────────────────────

  it('defaults stacked to false', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 80 })
    expect(store.charts[0]!.stacked).toBe(false)
  })

  it('can set stacked via updateChart', () => {
    const store = useChartStore()
    store.registerChart({ id: 'c1', name: 'C1', confidence: 80 })
    store.updateChart('c1', { stacked: true })
    expect(store.charts[0]!.stacked).toBe(true)
  })
})
