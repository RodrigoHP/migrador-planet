/**
 * chartCodeGen.spec.ts — Story 41.12
 * Tests for Chart.js code generation helpers, including 'area' type mapping.
 */
import { describe, it, expect } from 'vitest'
import {
  generateChartJsBlock,
  generateChartHtmlSnippet,
  buildChartJsSection,
} from '@/stores/chartCodeGen'
import type { ChartConfig } from '@/stores/chartStore'

// ─── Test helpers ─────────────────────────────────────────────────────────────

function makeChart(overrides: Partial<ChartConfig> = {}): ChartConfig {
  return {
    id: 'chart-1',
    name: 'Vendas',
    type: 'bar',
    confidence: 90,
    labelsField: 'meses',
    datasets: [{ label: 'Dataset 1', field: 'valores', color: '#6366f1' }],
    dimensions: { width: 400, height: 250 },
    styles: {
      showLegend: true,
      showGrid: true,
      animation: true,
      xAxisLabel: '',
      yAxisLabel: '',
    },
    useFallback: false,
    stacked: false,
    ...overrides,
  }
}

// ─── generateChartHtmlSnippet ─────────────────────────────────────────────────

describe('generateChartHtmlSnippet', () => {
  it('generates canvas element for normal chart', () => {
    const html = generateChartHtmlSnippet(makeChart())
    expect(html).toContain('<canvas')
    expect(html).toContain('id="Vendas"')
    expect(html).toContain('width="400"')
    expect(html).toContain('height="250"')
  })

  it('generates img element when useFallback is true', () => {
    const html = generateChartHtmlSnippet(makeChart({ useFallback: true }))
    expect(html).toContain('<img')
    expect(html).toContain('src="assets/Vendas.png"')
    expect(html).not.toContain('<canvas')
  })

  it('sanitizes chart name for id (spaces → underscores)', () => {
    const html = generateChartHtmlSnippet(makeChart({ name: 'Gráfico de Vendas' }))
    expect(html).toContain('id="Grfico_de_Vendas"')
  })
})

// ─── generateChartJsBlock — base types ───────────────────────────────────────

describe('generateChartJsBlock — base types', () => {
  it('returns empty string when useFallback is true', () => {
    const result = generateChartJsBlock(makeChart({ useFallback: true }))
    expect(result).toBe('')
  })

  it('generates bar chart block', () => {
    const result = generateChartJsBlock(makeChart({ type: 'bar' }))
    expect(result).toContain("type: 'bar'")
    expect(result).not.toContain('fill:')
  })

  it('generates line chart block', () => {
    const result = generateChartJsBlock(makeChart({ type: 'line' }))
    expect(result).toContain("type: 'line'")
    expect(result).not.toContain('fill:')
  })

  it('generates pie chart block', () => {
    const result = generateChartJsBlock(makeChart({ type: 'pie' }))
    expect(result).toContain("type: 'pie'")
    expect(result).not.toContain('fill:')
  })

  it('generates doughnut chart block', () => {
    const result = generateChartJsBlock(makeChart({ type: 'doughnut' }))
    expect(result).toContain("type: 'doughnut'")
    expect(result).not.toContain('fill:')
  })

  it('generates polarArea chart block', () => {
    const result = generateChartJsBlock(makeChart({ type: 'polarArea' }))
    expect(result).toContain("type: 'polarArea'")
    expect(result).not.toContain('fill:')
  })
})

// ─── generateChartJsBlock — area type (Story 41.12) ──────────────────────────

describe('generateChartJsBlock — area type (FR26)', () => {
  it('maps area type to Chart.js type: line', () => {
    const result = generateChartJsBlock(makeChart({ type: 'area' }))
    expect(result).toContain("type: 'line'")
  })

  it('does NOT emit type: area (not a native Chart.js type)', () => {
    const result = generateChartJsBlock(makeChart({ type: 'area' }))
    expect(result).not.toContain("type: 'area'")
  })

  it('emits fill: true in options when type is area', () => {
    const result = generateChartJsBlock(makeChart({ type: 'area' }))
    expect(result).toContain('fill: true')
  })

  it('does NOT emit fill: true for line type', () => {
    const result = generateChartJsBlock(makeChart({ type: 'line' }))
    expect(result).not.toContain('fill: true')
  })

  it('does NOT emit fill: true for bar type', () => {
    const result = generateChartJsBlock(makeChart({ type: 'bar' }))
    expect(result).not.toContain('fill: true')
  })

  it('includes labels field in area chart output', () => {
    const result = generateChartJsBlock(makeChart({ type: 'area', labelsField: 'meses' }))
    expect(result).toContain('ko.unwrap(data.meses)')
  })

  it('includes dataset field in area chart output', () => {
    const result = generateChartJsBlock(makeChart({ type: 'area' }))
    expect(result).toContain('ko.unwrap(data.valores)')
  })

  it('area chart uses responsive: false', () => {
    const result = generateChartJsBlock(makeChart({ type: 'area' }))
    expect(result).toContain('responsive: false')
  })
})

// ─── generateChartJsBlock — stacked ──────────────────────────────────────────

describe('generateChartJsBlock — stacked modifier', () => {
  it('emits stacked: true in scales when stacked is true', () => {
    const result = generateChartJsBlock(makeChart({ type: 'bar', stacked: true }))
    expect(result).toContain('stacked: true')
  })

  it('does not emit stacked when stacked is false', () => {
    const result = generateChartJsBlock(makeChart({ type: 'bar', stacked: false }))
    expect(result).not.toContain('stacked: true')
  })
})

// ─── buildChartJsSection ──────────────────────────────────────────────────────

describe('buildChartJsSection', () => {
  it('returns empty string when no active charts', () => {
    const result = buildChartJsSection([makeChart({ useFallback: true })])
    expect(result).toBe('')
  })

  it('wraps multiple chart blocks in initCharts function', () => {
    const charts = [makeChart({ id: 'c1', name: 'C1' }), makeChart({ id: 'c2', name: 'C2' })]
    const result = buildChartJsSection(charts)
    expect(result).toContain('var initCharts = function (data)')
    expect(result).toContain("getElementById('C1')")
    expect(result).toContain("getElementById('C2')")
  })

  it('includes area chart in section with type: line and fill: true', () => {
    const result = buildChartJsSection([makeChart({ type: 'area' })])
    expect(result).toContain("type: 'line'")
    expect(result).toContain('fill: true')
  })
})
