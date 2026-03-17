<template>
  <div class="section-inspector">
    <!-- Geral -->
    <InspectorSection title="Geral" :collapsible="true">
      <InspectorField label="Tipo" :value="sectionTypeLabel" type="badge" />
      <InspectorField label="Altura" :value="pxValue('height')" />
    </InspectorSection>

    <!-- Aparência -->
    <InspectorSection title="Aparência" :collapsible="true">
      <InspectorField
        label="Cor de Fundo"
        :value="(p['background_color'] as string) || '—'"
        :type="p['background_color'] ? 'color' : 'text'"
      />
      <InspectorField label="Imagem de Fundo" :value="(p['background_image'] as string) || '—'" />
    </InspectorSection>

    <!-- Espaçamento -->
    <InspectorSection title="Espaçamento" :collapsible="true">
      <InspectorField label="Padding Topo" :value="pxValue('padding_top')" />
      <InspectorField label="Padding Base" :value="pxValue('padding_bottom')" />
      <InspectorField label="Padding Esquerda" :value="pxValue('padding_left')" />
      <InspectorField label="Padding Direita" :value="pxValue('padding_right')" />
    </InspectorSection>

    <!-- Comportamento -->
    <InspectorSection title="Comportamento" :collapsible="true">
      <InspectorField label="Repetir por Página" :value="boolLabel('repeat_per_page')" />
      <InspectorField label="Bloquear Seção" :value="boolLabel('locked')" />
    </InspectorSection>

    <!-- Visibilidade -->
    <InspectorSection title="Visibilidade" :collapsible="true">
      <InspectorField label="Estado" :value="visibilityLabel" type="badge" />
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

function boolLabel(key: string): string {
  return p.value[key] ? 'Sim' : 'Não'
}

const sectionTypeLabels: Record<string, string> = {
  header: 'Header',
  flow: 'Flow',
  footer: 'Footer',
}

const sectionTypeLabel = computed(() => {
  const t = (p.value['section_type'] as string) || (props.node?.type as string) || ''
  return sectionTypeLabels[t] ?? (t || '—')
})

const visibilityLabels: Record<string, string> = {
  always: 'Sempre visível',
  conditional: 'Condicional',
  hidden: 'Escondido',
}

const visibilityLabel = computed(() => {
  const v = p.value['visibility'] as string | undefined
  return visibilityLabels[v ?? ''] ?? 'Sempre visível'
})
</script>

<style scoped>
.section-inspector {
  display: flex;
  flex-direction: column;
}
</style>
