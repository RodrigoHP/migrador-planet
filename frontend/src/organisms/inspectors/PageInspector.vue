<template>
  <div class="page-inspector">
    <!-- Dimensões -->
    <InspectorSection title="Dimensões" :collapsible="true">
      <InspectorField label="Tamanho" :value="props.node?.properties?.['size'] as string ?? 'A4'" />
      <InspectorField label="Orientação" :value="orientationLabel" />
    </InspectorSection>

    <!-- Margens -->
    <InspectorSection title="Margens" :collapsible="true">
      <InspectorField label="Topo" :value="mmValue('margin_top')" />
      <InspectorField label="Base" :value="mmValue('margin_bottom')" />
      <InspectorField label="Esquerda" :value="mmValue('margin_left')" />
      <InspectorField label="Direita" :value="mmValue('margin_right')" />
    </InspectorSection>

    <!-- Estrutura -->
    <InspectorSection title="Estrutura" :collapsible="true">
      <InspectorField label="Altura do Header" :value="pxValue('header_height')" />
      <InspectorField label="Altura do Footer" :value="pxValue('footer_height')" />
      <InspectorField label="Área de Conteúdo" :value="contentAreaValue" />
    </InspectorSection>

    <!-- Grid -->
    <InspectorSection title="Grid" :collapsible="true">
      <InspectorField label="Grid" :value="gridActive ? 'Ativo' : 'Inativo'" type="badge" />
      <InspectorField label="Tamanho do Grid" :value="pxValue('grid_size')" />
    </InspectorSection>

    <!-- Colunas -->
    <InspectorSection title="Colunas" :collapsible="true">
      <InspectorField label="Colunas Detectadas" :value="columnsCount" />
      <InspectorField label="Posições" :value="columnsPositions" />
    </InspectorSection>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TreeNode } from '@/types/template.types'
import InspectorField from '@/molecules/InspectorField.vue'
import InspectorSection from '@/molecules/InspectorSection.vue'

const props = withDefaults(
  defineProps<{ node?: TreeNode | null }>(),
  { node: null },
)

const p = computed(() => (props.node?.properties ?? {}) as Record<string, unknown>)

function pxValue(key: string): string {
  const v = p.value[key]
  return v !== undefined ? `${v}px` : '—'
}

function mmValue(key: string): string {
  const v = p.value[key]
  return v !== undefined ? `${v}mm` : '—'
}

const orientationLabel = computed(() => {
  const raw = p.value['orientation'] as string | undefined
  if (raw === 'landscape') return 'Paisagem'
  return 'Retrato'
})

const gridActive = computed(() => Boolean(p.value['grid_enabled']))

const contentAreaValue = computed(() => {
  const pageH = Number(p.value['page_height'] ?? 297)
  const headerH = Number(p.value['header_height'] ?? 0)
  const footerH = Number(p.value['footer_height'] ?? 0)
  const marginTop = Number(p.value['margin_top'] ?? 0)
  const marginBottom = Number(p.value['margin_bottom'] ?? 0)
  const area = pageH - (headerH / 3.7795) - (footerH / 3.7795) - marginTop - marginBottom
  return `${Math.round(area)}mm`
})

const columnsCount = computed(() => {
  const cols = p.value['detected_columns']
  if (Array.isArray(cols)) return String(cols.length)
  return String(p.value['columns_count'] ?? '—')
})

const columnsPositions = computed(() => {
  const cols = p.value['detected_columns']
  if (Array.isArray(cols)) return (cols as number[]).join(', ')
  return String(p.value['columns_positions'] ?? '—')
})
</script>

<style scoped>
.page-inspector {
  display: flex;
  flex-direction: column;
}
</style>
