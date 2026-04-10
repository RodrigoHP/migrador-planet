import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

// ─── Types ────────────────────────────────────────────────────────────────────

export type ChartType = 'bar' | 'line' | 'area' | 'pie' | 'doughnut' | 'polarArea'

export interface ChartDataset {
  label: string
  field: string
  color: string
}

export interface ChartDimensions {
  width: number
  height: number
}

export interface ChartStyles {
  showLegend: boolean
  showGrid: boolean
  animation: boolean
  xAxisLabel: string
  yAxisLabel: string
}

export interface ChartConfig {
  id: string
  name: string
  type: ChartType
  confidence: number
  labelsField: string
  datasets: ChartDataset[]
  dimensions: ChartDimensions
  styles: ChartStyles
  useFallback: boolean
  stacked: boolean
}

// ─── Default helpers ──────────────────────────────────────────────────────────

function defaultDataset(): ChartDataset {
  return { label: 'Dataset', field: '', color: '#6366f1' }
}

function defaultStyles(): ChartStyles {
  return {
    showLegend: true,
    showGrid: true,
    animation: true,
    xAxisLabel: '',
    yAxisLabel: '',
  }
}

function defaultDimensions(): ChartDimensions {
  return { width: 400, height: 250 }
}

/**
 * Pre-select chart type when confidence >= 60%
 * Otherwise defaults to 'bar' and operator selects manually.
 */
function resolveType(detectedType: string | undefined, confidence: number): ChartType {
  const valid: ChartType[] = ['bar', 'line', 'area', 'pie', 'doughnut', 'polarArea']
  if (confidence >= 60 && detectedType && valid.includes(detectedType as ChartType)) {
    return detectedType as ChartType
  }
  return 'bar'
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useChartStore = defineStore('chart', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const charts = ref<ChartConfig[]>([])

  // ─── Getters ──────────────────────────────────────────────────────────────
  const chartById = computed(() => (id: string) => charts.value.find((c) => c.id === id))

  // ─── Actions ──────────────────────────────────────────────────────────────

  /**
   * Register a new chart from Vision AI pipeline detection.
   * Pre-selects type when confidence >= 60%.
   */
  function registerChart(params: {
    id: string
    name: string
    confidence: number
    detectedType?: string
  }) {
    const existing = charts.value.find((c) => c.id === params.id)
    if (existing) return

    const type = resolveType(params.detectedType, params.confidence)
    charts.value.push({
      id: params.id,
      name: params.name,
      type,
      confidence: params.confidence,
      labelsField: '',
      datasets: [defaultDataset()],
      dimensions: defaultDimensions(),
      styles: defaultStyles(),
      useFallback: false,
      stacked: false,
    })
  }

  /** Update chart config (partial update) */
  function updateChart(id: string, config: Partial<Omit<ChartConfig, 'id'>>) {
    const chart = charts.value.find((c) => c.id === id)
    if (!chart) return
    Object.assign(chart, config)
  }

  /** Add a new dataset to a chart */
  function addDataset(chartId: string) {
    const chart = charts.value.find((c) => c.id === chartId)
    if (!chart) return
    chart.datasets.push(defaultDataset())
  }

  /** Remove a dataset from a chart by index */
  function removeDataset(chartId: string, datasetIndex: number) {
    const chart = charts.value.find((c) => c.id === chartId)
    if (!chart) return
    if (chart.datasets.length <= 1) return // keep at least one dataset
    chart.datasets.splice(datasetIndex, 1)
  }

  /** Toggle fallback image for a chart */
  function setFallback(chartId: string, useFallback: boolean) {
    const chart = charts.value.find((c) => c.id === chartId)
    if (!chart) return
    chart.useFallback = useFallback
  }

  /** Reset all charts (used on new session) */
  function reset() {
    charts.value = []
  }

  return {
    charts,
    chartById,
    registerChart,
    updateChart,
    addDataset,
    removeDataset,
    setFallback,
    reset,
  }
})
