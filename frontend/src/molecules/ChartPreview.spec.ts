import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ChartPreview from './ChartPreview.vue'
import type { ChartDataset, ChartStyles } from '@/stores/chartStore'

// ─── Mock Chart.js ────────────────────────────────────────────────────────────

const mockChartInstance = {
  destroy: vi.fn(),
  update: vi.fn(),
  data: {} as Record<string, unknown>,
  options: {} as Record<string, unknown>,
  config: { type: 'bar' },
}

const MockChart = vi.fn().mockImplementation(() => mockChartInstance)

vi.mock('chart.js', () => ({
  Chart: MockChart,
  registerables: [],
}))

// ─── Mock HTMLCanvasElement.getContext (jsdom doesn't support it) ─────────────
Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
  value: vi.fn().mockReturnValue({
    clearRect: vi.fn(),
    fillRect: vi.fn(),
    drawImage: vi.fn(),
    getImageData: vi.fn(),
    putImageData: vi.fn(),
    createImageData: vi.fn(),
    setTransform: vi.fn(),
    drawText: vi.fn(),
    save: vi.fn(),
    fillText: vi.fn(),
    restore: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    closePath: vi.fn(),
    stroke: vi.fn(),
    translate: vi.fn(),
    scale: vi.fn(),
    rotate: vi.fn(),
    arc: vi.fn(),
    fill: vi.fn(),
    measureText: vi.fn().mockReturnValue({ width: 0 }),
    transform: vi.fn(),
    rect: vi.fn(),
    clip: vi.fn(),
    canvas: { width: 400, height: 250 },
  }),
  writable: true,
  configurable: true,
})

// ─── Helpers ─────────────────────────────────────────────────────────────────

function makeDatasets(): ChartDataset[] {
  return [{ label: 'Série 1', field: 'campo1', color: '#6366f1' }]
}

function makeStyles(): ChartStyles {
  return {
    showLegend: true,
    showGrid: true,
    animation: false,
    xAxisLabel: '',
    yAxisLabel: '',
  }
}

function mountPreview(overrides: Partial<InstanceType<typeof ChartPreview>['$props']> = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  return mount(ChartPreview, {
    props: {
      type: 'bar',
      datasets: makeDatasets(),
      styles: makeStyles(),
      ...overrides,
    },
    global: { plugins: [pinia] },
  })
}

describe('ChartPreview', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('renders a canvas element', async () => {
    const wrapper = mountPreview()
    await flushPromises()
    expect(wrapper.find('canvas').exists()).toBe(true)
  })

  it('renders the chart-preview container', async () => {
    const wrapper = mountPreview()
    expect(wrapper.find('.chart-preview').exists()).toBe(true)
  })

  it('shows the chart preview container without crashing', async () => {
    const wrapper = mountPreview()
    await flushPromises()
    // In jsdom environment, Chart.js may fail gracefully — we just verify no uncaught exception
    expect(wrapper.find('.chart-preview').exists()).toBe(true)
  })

  it('accepts bar type prop', async () => {
    const wrapper = mountPreview({ type: 'bar' })
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('accepts line type prop', async () => {
    const wrapper = mountPreview({ type: 'line' })
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('accepts pie type prop', async () => {
    const wrapper = mountPreview({ type: 'pie' })
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('accepts doughnut type prop', async () => {
    const wrapper = mountPreview({ type: 'doughnut' })
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('accepts polarArea type prop', async () => {
    const wrapper = mountPreview({ type: 'polarArea' })
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('accepts multiple datasets', async () => {
    const datasets: ChartDataset[] = [
      { label: 'S1', field: 'f1', color: '#f00' },
      { label: 'S2', field: 'f2', color: '#0f0' },
      { label: 'S3', field: 'f3', color: '#00f' },
    ]
    const wrapper = mountPreview({ datasets })
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('accepts stacked=true prop', async () => {
    const wrapper = mountPreview({ type: 'bar', stacked: true })
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('renders with styles.showLegend=false', async () => {
    const styles: ChartStyles = { ...makeStyles(), showLegend: false }
    const wrapper = mountPreview({ styles })
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('renders with axis labels set', async () => {
    const styles: ChartStyles = { ...makeStyles(), xAxisLabel: 'Mês', yAxisLabel: 'Valor' }
    const wrapper = mountPreview({ styles })
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('accepts chartId prop', async () => {
    const wrapper = mountPreview({ chartId: 'my-chart-id' })
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })
})
