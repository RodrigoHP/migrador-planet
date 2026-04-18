<template>
  <div class="chart-preview">
    <canvas ref="canvasRef" class="chart-preview__canvas" />
    <div v-if="error" class="chart-preview__error">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import type { ChartType, ChartDataset, ChartStyles } from '@/stores/chartStore'

// ─── Props ────────────────────────────────────────────────────────────────────

const props = withDefaults(
  defineProps<{
    chartId?: string
    type: ChartType
    stacked?: boolean
    datasets: ChartDataset[]
    styles: ChartStyles
  }>(),
  {
    chartId: '',
    stacked: false,
  },
)

// ─── Refs ─────────────────────────────────────────────────────────────────────

const canvasRef = ref<HTMLCanvasElement | null>(null)
const error = ref<string | null>(null)

let chartInstance: import('chart.js').Chart | null = null

// ─── Sample data for preview ──────────────────────────────────────────────────

const SAMPLE_LABELS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun']

function buildChartData() {
  const datasets = props.datasets.map((ds, i) => {
    const sampleValues = [12, 19, 7, 15, 22, 8].map((v) => v + i * 5)
    return {
      label: ds.label || `Dataset ${i + 1}`,
      data: sampleValues,
      backgroundColor: ds.color || `hsl(${i * 60}, 70%, 60%)`,
      borderColor: ds.color || `hsl(${i * 60}, 70%, 40%)`,
      borderWidth: 1,
    }
  })
  return { labels: SAMPLE_LABELS, datasets }
}

/** Map logical ChartType to Chart.js native type for preview */
function getPreviewType(type: ChartType): string {
  if (type === 'area') return 'line'
  return type
}

function buildOptions() {
  const isPie = props.type === 'pie' || props.type === 'doughnut' || props.type === 'polarArea'
  const isArea = props.type === 'area'
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: props.styles.animation ? 200 : 0 },
    ...(isArea ? { fill: true } : {}),
    plugins: {
      legend: { display: props.styles.showLegend },
    },
    ...(isPie
      ? {}
      : {
          scales: {
            x: {
              display: props.styles.showGrid,
              stacked: props.stacked,
              title: {
                display: !!props.styles.xAxisLabel,
                text: props.styles.xAxisLabel,
              },
            },
            y: {
              display: props.styles.showGrid,
              stacked: props.stacked,
              title: {
                display: !!props.styles.yAxisLabel,
                text: props.styles.yAxisLabel,
              },
            },
          },
        }),
  }
}

// ─── Chart lifecycle ──────────────────────────────────────────────────────────

async function initChart() {
  if (!canvasRef.value) return
  error.value = null

  try {
    // Dynamic import so Chart.js is in its own chunk
    const { Chart, registerables } = await import('chart.js')
    Chart.register(...registerables)

    if (chartInstance) {
      chartInstance.destroy()
      chartInstance = null
    }

    // Resolve effective type: 'area' maps to 'line' in Chart.js
    const effectiveType = getPreviewType(props.type)

    chartInstance = new Chart(canvasRef.value, {
      type: effectiveType as import('chart.js').ChartType,
      data: buildChartData(),
      options: buildOptions(),
    })
  } catch {
    error.value = 'Erro ao renderizar preview'
  }
}

function updateChart() {
  if (!chartInstance) {
    initChart()
    return
  }
  chartInstance.data = buildChartData()
  chartInstance.options = buildOptions()
  ;(chartInstance.config as { type?: string }).type = getPreviewType(props.type)
  chartInstance.update()
}

onMounted(async () => {
  await nextTick()
  await initChart()
})

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
})

// Re-render when config changes
watch(
  () => [props.type, props.stacked, props.datasets, props.styles],
  () => updateChart(),
  { deep: true },
)
</script>

<style scoped>
.chart-preview {
  position: relative;
  width: 100%;
  height: 160px;
  background: var(--color-neutral-900, #111827);
  border: 1px solid var(--color-neutral-700, #374151);
  border-radius: 0.375rem;
  overflow: hidden;
}

.chart-preview__canvas {
  width: 100% !important;
  height: 100% !important;
}

.chart-preview__error {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  color: var(--color-neutral-400, #9ca3af);
  background: var(--color-neutral-900, #111827);
}
</style>
