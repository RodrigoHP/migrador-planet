<template>
  <div class="chart-inspector">
    <!-- Geral -->
    <InspectorSection title="Geral" :collapsible="true">
      <InspectorField label="Nome" :value="props.node?.name ?? '—'" />
      <InspectorField label="Confiança" :value="confidenceValue" />
    </InspectorSection>

    <!-- Tipo -->
    <InspectorSection title="Tipo" :collapsible="true">
      <InspectorField label="Tipo Detectado" :value="chartTypeLabel" type="badge" />
    </InspectorSection>

    <!-- Dados -->
    <InspectorSection title="Dados" :collapsible="true">
      <InspectorField label="Labels" :value="strValue('labels_binding')" />
      <InspectorField label="Datasets" :value="strValue('datasets_binding')" />
    </InspectorSection>

    <!-- Dimensões -->
    <InspectorSection title="Dimensões" :collapsible="true">
      <InspectorField label="Largura" :value="pxValue('width')" />
      <InspectorField label="Altura" :value="pxValue('height')" />
    </InspectorSection>

    <!-- Estilo -->
    <InspectorSection title="Estilo" :collapsible="true">
      <InspectorField label="Legenda" :value="boolLabel('show_legend')" />
      <InspectorField label="Grid" :value="boolLabel('show_grid')" />
      <InspectorField label="Animação" :value="boolLabel('animation')" />
      <InspectorField label="Labels de Eixo" :value="boolLabel('show_axis_labels')" />
    </InspectorSection>

    <!-- Posição -->
    <InspectorSection title="Posição" :collapsible="true">
      <InspectorField label="Âncora" :value="strValue('anchor')" />
      <InspectorField label="Manter Junto" :value="boolLabel('keep_together')" />
    </InspectorSection>

    <!-- Visibilidade -->
    <InspectorSection title="Visibilidade" :collapsible="true">
      <VisibilityControl
        :model-value="visibilityConfig"
        @update:model-value="updateVisibility"
      />
    </InspectorSection>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TreeNode } from '@/types/template.types'
import InspectorField from '@/molecules/InspectorField.vue'
import InspectorSection from '@/molecules/InspectorSection.vue'
import VisibilityControl from '@/molecules/VisibilityControl.vue'
import type { VisibilityConfig } from '@/molecules/VisibilityControl.vue'
import { useTemplateStore } from '@/stores/templateStore'

const props = withDefaults(
  defineProps<{ node?: TreeNode | null }>(),
  { node: null },
)

const templateStore = useTemplateStore()

const p = computed(() => (props.node?.properties ?? {}) as Record<string, unknown>)

function pxValue(key: string): string {
  const v = p.value[key]
  return v !== undefined ? `${v}px` : '—'
}

function boolLabel(key: string): string {
  return p.value[key] ? 'Sim' : 'Não'
}

function strValue(key: string): string {
  const v = p.value[key]
  return v !== undefined && v !== null ? String(v) : '—'
}

const confidenceValue = computed(() => {
  const v = p.value['confidence']
  return v !== undefined ? `${v}%` : '—'
})

const chartTypeLabels: Record<string, string> = {
  bar: 'Barra',
  line: 'Linha',
  pie: 'Pizza',
  doughnut: 'Rosca',
  area: 'Área',
}

const chartTypeLabel = computed(() => {
  const t = p.value['chart_type'] as string | undefined
  return chartTypeLabels[t ?? ''] ?? (t ?? '—')
})

const visibilityConfig = computed<VisibilityConfig>(() => {
  const raw = p.value['visibility']
  if (raw && typeof raw === 'object' && 'mode' in (raw as object)) {
    return raw as VisibilityConfig
  }
  const mode = (raw as string) || 'always'
  return { mode: mode as VisibilityConfig['mode'] }
})

function updateVisibility(config: VisibilityConfig) {
  if (props.node?.id) {
    templateStore.updateNodeProperty(props.node.id, 'visibility', config)
  }
}
</script>

<style scoped>
.chart-inspector {
  display: flex;
  flex-direction: column;
}
</style>
