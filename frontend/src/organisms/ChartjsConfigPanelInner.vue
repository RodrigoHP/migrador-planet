<template>
  <section class="chart-config">
    <header>
      <h3>Configuração Chart.js</h3>
    </header>

    <form class="chart-config__form" @submit.prevent="save">
      <label>
        <span>Tipo</span>
        <select v-model="draft.chartType">
          <option value="bar">Bar</option>
          <option value="line">Line</option>
          <option value="pie">Pie</option>
          <option value="doughnut">Doughnut</option>
        </select>
      </label>

      <label>
        <span>Campo de dados</span>
        <input v-model="draft.dataField" type="text" />
      </label>

      <label>
        <span>Campo de label</span>
        <input v-model="draft.labelField" type="text" />
      </label>

      <label>
        <span>Título</span>
        <input v-model="draft.title" type="text" />
      </label>

      <label>
        <span>Cores (hex separadas por vírgula)</span>
        <input v-model="colorsText" type="text" />
      </label>

      <button type="submit">Salvar configuração</button>
    </form>

    <canvas ref="canvasRef" class="chart-config__canvas" />
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import type { ChartjsConfig } from '@/types'

const props = defineProps<{
  initialConfig: ChartjsConfig
}>()

const emit = defineEmits<{
  save: [config: ChartjsConfig]
}>()

const draft = reactive<ChartjsConfig>({ ...props.initialConfig })
const canvasRef = ref<HTMLCanvasElement | null>(null)

const colorsText = computed({
  get: () => draft.colors.join(','),
  set: (value: string) => {
    draft.colors = value.split(',').map((item) => item.trim()).filter(Boolean)
  },
})

let chartApi: any = null
let chartInstance: any = null

async function renderChart() {
  if (!canvasRef.value) return
  if (!chartApi) {
    const chartjs = await import('chart.js')
    chartjs.Chart.register(...chartjs.registerables)
    chartApi = chartjs.Chart
  }

  chartInstance?.destroy()
  chartInstance = new chartApi(canvasRef.value, {
    type: draft.chartType,
    data: {
      labels: ['A', 'B', 'C', 'D'],
      datasets: [
        {
          label: draft.title || 'Série',
          data: [12, 19, 7, 15],
          backgroundColor: draft.colors.length > 0 ? draft.colors : ['#2563EB', '#16A34A', '#EAB308', '#DC2626'],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
    },
  })
}

function save() {
  emit('save', { ...draft })
}

onMounted(() => {
  renderChart()
})

onBeforeUnmount(() => {
  chartInstance?.destroy()
})

watch(
  () => [draft.chartType, draft.title, draft.colors.join('|')],
  () => {
    renderChart()
  },
)
</script>

<style scoped>
.chart-config {
  display: grid;
  gap: 0.8rem;
}

.chart-config h3 {
  margin: 0;
}

.chart-config__form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.6rem;
}

label {
  display: grid;
  gap: 0.3rem;
}

span {
  font-size: 0.8rem;
  color: var(--color-neutral-700);
}

input,
select {
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.45rem;
  padding: 0.45rem 0.5rem;
}

button {
  grid-column: 1 / -1;
  justify-self: end;
  border: 1px solid var(--color-primary-600);
  color: #fff;
  background: var(--color-primary-600);
  border-radius: 0.45rem;
  padding: 0.45rem 0.75rem;
}

.chart-config__canvas {
  width: 100%;
  min-height: 280px;
}
</style>
