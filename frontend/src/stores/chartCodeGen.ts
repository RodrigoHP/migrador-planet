/**
 * Chart.js code generation helpers — Story 9.7
 * AC#10: generate <canvas> HTML + Chart.js base.js initialization block
 * AC#11: reference ../Bibliotecas/js/Chart.min.js
 */
import type { ChartConfig } from './chartStore'

/** Sanitize name to valid JS/HTML identifier */
function safeId(name: string): string {
  return name.replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_]/g, '')
}

/**
 * Generate `<canvas>` or `<img>` HTML snippet for a chart node.
 * AC#9 (fallback): `<img src="assets/{name}.png">`
 * AC#10 (canvas): `<canvas id="{name}" width="{w}" height="{h}"></canvas>`
 */
export function generateChartHtmlSnippet(chart: ChartConfig): string {
  const id = safeId(chart.name)
  if (chart.useFallback) {
    return `<img src="assets/${id}.png" alt="${chart.name}" width="${chart.dimensions.width}" height="${chart.dimensions.height}" />`
  }
  return `<canvas id="${id}" width="${chart.dimensions.width}" height="${chart.dimensions.height}"></canvas>`
}

/**
 * Generate Chart.js initialization block for base.js.
 * AC#10: `new Chart(document.getElementById('{name}'), { type: '{type}', data: {...}, options: {...} })`
 * AC#11: references `../Bibliotecas/js/Chart.min.js` and `../Bibliotecas/js/chartjs-plugin-datalabels.min.js`
 */
export function generateChartJsBlock(chart: ChartConfig): string {
  if (chart.useFallback) return ''
  const id = safeId(chart.name)
  const labelsField = chart.labelsField || 'labels'
  const stacked = chart.stacked ? '\n      stacked: true,' : ''
  const datasetsCode = chart.datasets
    .map((ds) => {
      const field = ds.field || 'campo'
      return (
        `    {\n` +
        `      label: '${ds.label}',\n` +
        `      data: ko.unwrap(data.${field}),\n` +
        `      backgroundColor: '${ds.color}',\n` +
        `      borderColor: '${ds.color}',\n` +
        `      borderWidth: 1\n` +
        `    }`
      )
    })
    .join(',\n')

  return (
    `new Chart(document.getElementById('${id}'), {\n` +
    `  type: '${chart.type}',\n` +
    `  data: {\n` +
    `    labels: ko.unwrap(data.${labelsField}),\n` +
    `    datasets: [\n${datasetsCode}\n    ]\n` +
    `  },\n` +
    `  options: {\n` +
    `    responsive: false,\n` +
    `    plugins: {\n` +
    `      legend: { display: ${chart.styles.showLegend} },\n` +
    `      datalabels: { display: false }\n` +
    `    },\n` +
    `    scales: {\n` +
    `      x: { display: ${chart.styles.showGrid},${stacked} title: { display: ${!!chart.styles.xAxisLabel}, text: '${chart.styles.xAxisLabel}' } },\n` +
    `      y: { display: ${chart.styles.showGrid},${stacked} title: { display: ${!!chart.styles.yAxisLabel}, text: '${chart.styles.yAxisLabel}' } }\n` +
    `    },\n` +
    `    animation: { duration: ${chart.styles.animation ? 300 : 0} }\n` +
    `  }\n` +
    `});`
  )
}

/** Chart.js library script tags (for HTML head) */
export const CHARTJS_SCRIPT_TAGS =
  '  <script src="../Bibliotecas/js/Chart.min.js"><\\/script>\n' +
  '  <script src="../Bibliotecas/js/chartjs-plugin-datalabels.min.js"><\\/script>'

/** Build the Chart.js initialization section for base.js */
export function buildChartJsSection(charts: ChartConfig[]): string {
  const active = charts.filter((c) => !c.useFallback)
  if (!active.length) return ''
  const blocks = active.map((c) => generateChartJsBlock(c)).filter(Boolean)
  if (!blocks.length) return ''
  return (
    '\n// ─── Chart.js initialization ──────────────────────────────\n' +
    'var initCharts = function (data) {\n' +
    `  ${blocks.join('\n\n  ')}\n` +
    '};\n'
  )
}
