<template>
  <div class="chart-inspector">
    <!-- ─── Header: nome editável + badge de confiança ─────────────────────── -->
    <InspectorSection title="Geral" :collapsible="true">
      <InspectorInput label="Nome" :model-value="chartName" @update:model-value="onNameChange" />
      <div class="chart-inspector__confidence">
        <span class="chart-inspector__confidence-label">Confiança</span>
        <span
          class="chart-inspector__confidence-badge"
          :class="
            isHighConfidence
              ? 'chart-inspector__confidence-badge--high'
              : 'chart-inspector__confidence-badge--low'
          "
        >
          {{ confidenceValue }}
        </span>
        <span v-if="!isHighConfidence" class="chart-inspector__confidence-hint">
          Selecione o tipo manualmente
        </span>
      </div>
    </InspectorSection>

    <!-- ─── Tipo de gráfico ───────────────────────────────────────────────── -->
    <InspectorSection title="Tipo" :collapsible="true">
      <InspectorSelect
        label="Tipo de Gráfico"
        :model-value="chartType"
        :options="chartTypeOptions"
        placeholder="Selecione o tipo"
        @update:model-value="onTypeChange"
      />
      <InspectorCheckbox
        v-if="chartType === 'bar'"
        label="Barras empilhadas"
        :model-value="chartStacked"
        @update:model-value="onStackedChange"
      />
    </InspectorSection>

    <!-- ─── Binding de dados ──────────────────────────────────────────────── -->
    <InspectorSection title="Dados" :collapsible="true">
      <InspectorSelect
        label="Campo Labels"
        :model-value="labelsField"
        :options="availableFields"
        placeholder="Selecione campo"
        @update:model-value="onLabelsFieldChange"
      />

      <!-- Datasets list -->
      <div class="chart-inspector__datasets-header">
        <span class="chart-inspector__datasets-title">Datasets</span>
      </div>
      <div v-for="(ds, idx) in chartDatasets" :key="idx" class="chart-inspector__dataset-item">
        <div class="chart-inspector__dataset-row">
          <span class="chart-inspector__dataset-index">{{ idx + 1 }}</span>
          <button
            v-if="chartDatasets.length > 1"
            class="chart-inspector__dataset-remove"
            type="button"
            title="Remover dataset"
            @click="removeDataset(idx)"
          >
            ✕
          </button>
        </div>
        <InspectorInput
          label="Label"
          :model-value="ds.label"
          @update:model-value="(v) => updateDatasetLabel(idx, String(v))"
        />
        <InspectorSelect
          label="Campo"
          :model-value="ds.field"
          :options="availableFields"
          placeholder="Selecione campo"
          @update:model-value="(v) => updateDatasetField(idx, v)"
        />
        <InspectorColorPicker
          label="Cor"
          :model-value="ds.color"
          @update:model-value="(v) => updateDatasetColor(idx, v)"
        />
      </div>

      <button class="chart-inspector__add-dataset" type="button" @click="addDataset">
        + Adicionar dataset
      </button>
    </InspectorSection>

    <!-- ─── Dimensões ─────────────────────────────────────────────────────── -->
    <InspectorSection title="Dimensões" :collapsible="true">
      <InspectorInput
        label="Largura (px)"
        type="number"
        :min="50"
        :max="2000"
        :model-value="chartWidth"
        @update:model-value="(v) => onDimensionChange('width', Number(v))"
      />
      <InspectorInput
        label="Altura (px)"
        type="number"
        :min="50"
        :max="2000"
        :model-value="chartHeight"
        @update:model-value="(v) => onDimensionChange('height', Number(v))"
      />
    </InspectorSection>

    <!-- ─── Estilo (colapsável) ───────────────────────────────────────────── -->
    <InspectorSection title="Estilo" :collapsible="true">
      <InspectorCheckbox
        label="Legenda"
        :model-value="chartStyles.showLegend"
        @update:model-value="(v) => onStyleChange('showLegend', v)"
      />
      <InspectorCheckbox
        label="Grid"
        :model-value="chartStyles.showGrid"
        @update:model-value="(v) => onStyleChange('showGrid', v)"
      />
      <InspectorCheckbox
        label="Animação"
        :model-value="chartStyles.animation"
        @update:model-value="(v) => onStyleChange('animation', v)"
      />
      <InspectorInput
        label="Label Eixo X"
        :model-value="chartStyles.xAxisLabel"
        @update:model-value="(v) => onStyleChange('xAxisLabel', String(v))"
      />
      <InspectorInput
        label="Label Eixo Y"
        :model-value="chartStyles.yAxisLabel"
        @update:model-value="(v) => onStyleChange('yAxisLabel', String(v))"
      />
    </InspectorSection>

    <!-- ─── Preview ───────────────────────────────────────────────────────── -->
    <InspectorSection title="Preview" :collapsible="true">
      <ChartPreview
        v-if="!chartFallback"
        :chart-id="chartId"
        :type="chartType as ChartType"
        :stacked="chartStacked"
        :datasets="chartDatasets"
        :styles="chartStyles"
      />
      <div v-else class="chart-inspector__fallback-preview">
        <span>Imagem estática será usada</span>
      </div>
    </InspectorSection>

    <!-- ─── Posição (mantido do original) ────────────────────────────────── -->
    <InspectorSection title="Posição" :collapsible="true">
      <InspectorField label="Âncora" :value="strValue('anchor')" />
      <InspectorField label="Manter Junto" :value="boolLabel('keep_together')" />
    </InspectorSection>

    <!-- ─── Visibilidade (mantido do original) ───────────────────────────── -->
    <InspectorSection title="Visibilidade" :collapsible="true">
      <VisibilityControl :model-value="visibilityConfig" @update:model-value="updateVisibility" />
    </InspectorSection>

    <!-- ─── Fallback ─────────────────────────────────────────────────────── -->
    <InspectorSection title="Fallback" :collapsible="true">
      <InspectorCheckbox
        label="Usar imagem estática"
        :model-value="chartFallback"
        @update:model-value="onFallbackChange"
      />
      <p class="chart-inspector__fallback-hint">Quando ativo, gera img em vez de canvas.</p>
    </InspectorSection>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TreeNode } from '@/types/template.types'
import InspectorField from '@/molecules/InspectorField.vue'
import InspectorInput from '@/molecules/InspectorInput.vue'
import InspectorSelect from '@/molecules/InspectorSelect.vue'
import InspectorCheckbox from '@/molecules/InspectorCheckbox.vue'
import InspectorColorPicker from '@/molecules/InspectorColorPicker.vue'
import InspectorSection from '@/molecules/InspectorSection.vue'
import VisibilityControl from '@/molecules/VisibilityControl.vue'
import ChartPreview from '@/molecules/ChartPreview.vue'
import type { VisibilityConfig } from '@/molecules/VisibilityControl.vue'
import { useTemplateStore } from '@/stores/templateStore'
import { useChartStore } from '@/stores/chartStore'
import type { ChartDataset, ChartStyles, ChartType } from '@/stores/chartStore'

// ─── Props ────────────────────────────────────────────────────────────────────

const props = withDefaults(defineProps<{ node?: TreeNode | null }>(), { node: null })

// ─── Stores ───────────────────────────────────────────────────────────────────

const templateStore = useTemplateStore()
const chartStore = useChartStore()

// ─── Raw node properties (for legacy fields) ──────────────────────────────────

const p = computed(() => (props.node?.properties ?? {}) as Record<string, unknown>)

function strValue(key: string): string {
  const v = p.value[key]
  return v !== undefined && v !== null ? String(v) : '—'
}

function boolLabel(key: string): string {
  return p.value[key] ? 'Sim' : 'Não'
}

// ─── ChartStore integration ───────────────────────────────────────────────────

const chartId = computed<string>(() => props.node?.id ?? '')

const liveChart = computed(() => {
  if (!chartId.value) return null
  return chartStore.chartById(chartId.value) ?? null
})

function ensureRegistered() {
  if (!props.node) return
  const id = props.node.id
  if (!chartStore.chartById(id)) {
    const conf = (p.value['confidence'] as number | undefined) ?? 0
    const detectedType = p.value['chart_type'] as string | undefined
    chartStore.registerChart({ id, name: props.node.name, confidence: conf, detectedType })
  }
}

// ─── Computed state ───────────────────────────────────────────────────────────

const chartName = computed(() => {
  ensureRegistered()
  return liveChart.value?.name ?? props.node?.name ?? '—'
})

const confidenceValue = computed(() => {
  const v = liveChart.value?.confidence ?? (p.value['confidence'] as number | undefined)
  return v !== undefined ? `${v}%` : '—'
})

const isHighConfidence = computed(() => {
  ensureRegistered()
  const v = liveChart.value?.confidence ?? (p.value['confidence'] as number | undefined) ?? 0
  return v >= 60
})

const chartType = computed(() => {
  ensureRegistered()
  return liveChart.value?.type ?? 'bar'
})

const chartStacked = computed(() => liveChart.value?.stacked ?? false)
const labelsField = computed(() => liveChart.value?.labelsField ?? '')

const chartDatasets = computed<ChartDataset[]>(() => {
  ensureRegistered()
  return liveChart.value?.datasets ?? [{ label: 'Dataset', field: '', color: '#6366f1' }]
})

const chartWidth = computed(() => liveChart.value?.dimensions?.width ?? 400)
const chartHeight = computed(() => liveChart.value?.dimensions?.height ?? 250)

const chartStyles = computed<ChartStyles>(
  () =>
    liveChart.value?.styles ?? {
      showLegend: true,
      showGrid: true,
      animation: true,
      xAxisLabel: '',
      yAxisLabel: '',
    },
)

const chartFallback = computed(() => liveChart.value?.useFallback ?? false)

// ─── Chart type options ───────────────────────────────────────────────────────

const chartTypeOptions = [
  { value: 'bar', label: 'Barras' },
  { value: 'line', label: 'Linha' },
  { value: 'area', label: 'Área' },
  { value: 'pie', label: 'Pizza' },
  { value: 'doughnut', label: 'Rosca' },
  { value: 'polarArea', label: 'Área Polar' },
]

// ─── Available fields ─────────────────────────────────────────────────────────

const availableFields = computed(() => {
  const fields = templateStore.getNodesByType('field').map((n) => ({
    value: n.name,
    label: n.name,
  }))
  if (!fields.length) {
    return [
      { value: 'campo1', label: 'campo1' },
      { value: 'campo2', label: 'campo2' },
      { value: 'campo3', label: 'campo3' },
    ]
  }
  return fields
})

// ─── Handlers ─────────────────────────────────────────────────────────────────

function onNameChange(v: string | number) {
  ensureRegistered()
  chartStore.updateChart(chartId.value, { name: String(v) })
  if (props.node?.id) templateStore.updateNodeProperty(props.node.id, 'name', String(v))
}

function onTypeChange(v: string) {
  ensureRegistered()
  chartStore.updateChart(chartId.value, { type: v as ChartType })
}

function onStackedChange(v: boolean) {
  ensureRegistered()
  chartStore.updateChart(chartId.value, { stacked: v })
}

function onLabelsFieldChange(v: string) {
  ensureRegistered()
  chartStore.updateChart(chartId.value, { labelsField: v })
}

function addDataset() {
  ensureRegistered()
  chartStore.addDataset(chartId.value)
}

function removeDataset(idx: number) {
  ensureRegistered()
  chartStore.removeDataset(chartId.value, idx)
}

function updateDatasetLabel(idx: number, v: string) {
  ensureRegistered()
  const datasets = [...chartDatasets.value]
  datasets[idx] = { ...datasets[idx]!, label: v }
  chartStore.updateChart(chartId.value, { datasets })
}

function updateDatasetField(idx: number, v: string) {
  ensureRegistered()
  const datasets = [...chartDatasets.value]
  datasets[idx] = { ...datasets[idx]!, field: v }
  chartStore.updateChart(chartId.value, { datasets })
}

function updateDatasetColor(idx: number, v: string) {
  ensureRegistered()
  const datasets = [...chartDatasets.value]
  datasets[idx] = { ...datasets[idx]!, color: v }
  chartStore.updateChart(chartId.value, { datasets })
}

function onDimensionChange(key: 'width' | 'height', v: number) {
  ensureRegistered()
  const current = liveChart.value?.dimensions ?? { width: 400, height: 250 }
  chartStore.updateChart(chartId.value, { dimensions: { ...current, [key]: v } })
}

function onStyleChange(key: keyof ChartStyles, v: boolean | string) {
  ensureRegistered()
  const current = liveChart.value?.styles ?? {
    showLegend: true,
    showGrid: true,
    animation: true,
    xAxisLabel: '',
    yAxisLabel: '',
  }
  chartStore.updateChart(chartId.value, { styles: { ...current, [key]: v } })
}

function onFallbackChange(v: boolean) {
  ensureRegistered()
  chartStore.setFallback(chartId.value, v)
}

// ─── Visibility (original logic preserved) ────────────────────────────────────

const visibilityConfig = computed<VisibilityConfig>(() => {
  const raw = p.value['visibility']
  if (raw && typeof raw === 'object' && 'mode' in (raw as object)) return raw as VisibilityConfig
  const mode = (raw as string) || 'always'
  return { mode: mode as VisibilityConfig['mode'] }
})

function updateVisibility(config: VisibilityConfig) {
  if (props.node?.id) templateStore.updateNodeProperty(props.node.id, 'visibility', config)
}
</script>

<style scoped>
.chart-inspector {
  display: flex;
  flex-direction: column;
}

.chart-inspector__confidence {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0;
  flex-wrap: wrap;
}

.chart-inspector__confidence-label {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.chart-inspector__confidence-badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
}

.chart-inspector__confidence-badge--high {
  background: var(--color-green-800, #166534);
  color: var(--color-green-200, #bbf7d0);
}

.chart-inspector__confidence-badge--low {
  background: var(--color-yellow-800, #713f12);
  color: var(--color-yellow-200, #fef08a);
}

.chart-inspector__confidence-hint {
  font-size: 0.6875rem;
  color: var(--color-yellow-400, #facc15);
  font-style: italic;
}

.chart-inspector__datasets-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.375rem 0 0.25rem;
}

.chart-inspector__datasets-title {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.chart-inspector__dataset-item {
  border: 1px solid var(--color-neutral-700, #374151);
  border-radius: 0.375rem;
  padding: 0.375rem 0.5rem 0.25rem;
  margin-bottom: 0.5rem;
}

.chart-inspector__dataset-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.25rem;
}

.chart-inspector__dataset-index {
  font-size: 0.6875rem;
  color: var(--color-neutral-500, #525252);
  font-weight: 600;
}

.chart-inspector__dataset-remove {
  background: none;
  border: none;
  color: var(--color-red-400, #f87171);
  font-size: 0.75rem;
  cursor: pointer;
  padding: 0 0.25rem;
  line-height: 1;
}

.chart-inspector__dataset-remove:hover {
  color: var(--color-red-300, #fca5a5);
}

.chart-inspector__add-dataset {
  width: 100%;
  padding: 0.3125rem 0.5rem;
  margin-top: 0.25rem;
  font-size: 0.75rem;
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-200, #e5e7eb);
  border: 1px dashed var(--color-neutral-500, #525252);
  border-radius: 0.25rem;
  cursor: pointer;
  text-align: center;
  transition: background 0.15s;
}

.chart-inspector__add-dataset:hover {
  background: var(--color-neutral-600, #4b5563);
}

.chart-inspector__fallback-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 80px;
  background: var(--color-neutral-900, #111827);
  border: 1px solid var(--color-neutral-700, #374151);
  border-radius: 0.375rem;
  font-size: 0.75rem;
  color: var(--color-neutral-400, #9ca3af);
  font-style: italic;
}

.chart-inspector__fallback-hint {
  font-size: 0.6875rem;
  color: var(--color-neutral-500, #525252);
  margin: 0.25rem 0 0;
  line-height: 1.4;
}
</style>
