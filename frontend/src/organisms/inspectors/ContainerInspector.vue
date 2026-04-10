<template>
  <div class="container-inspector">
    <!-- Geral -->
    <InspectorSection title="Geral" :collapsible="true">
      <InspectorField label="Nome" :value="props.node?.name ?? '—'" />
      <InspectorField label="Tipo de Container" :value="strValue('container_type')" />
    </InspectorSection>

    <!-- Layout -->
    <InspectorSection title="Layout" :collapsible="true">
      <InspectorField label="Direção" :value="directionLabel" />
      <InspectorField label="Gap" :value="pxValue('gap')" />
      <InspectorField label="Alinhamento" :value="strValue('align')" />
    </InspectorSection>

    <!-- Visibilidade -->
    <InspectorSection title="Visibilidade" :collapsible="true">
      <InspectorField label="Estado" :value="visibilityLabel" type="badge" />
      <InspectorField label="Camada" :value="strValue('layer')" />
    </InspectorSection>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TreeNode } from '@/types/template.types'
import InspectorField from '@/molecules/InspectorField.vue'
import InspectorSection from '@/molecules/InspectorSection.vue'

const props = withDefaults(defineProps<{ node?: TreeNode | null }>(), { node: null })

const p = computed(() => (props.node?.properties ?? {}) as Record<string, unknown>)

function pxValue(key: string): string {
  const v = p.value[key]
  return v !== undefined ? `${v}px` : '—'
}

function strValue(key: string): string {
  const v = p.value[key]
  return v !== undefined && v !== null ? String(v) : '—'
}

const directionLabels: Record<string, string> = {
  row: 'Horizontal (row)',
  column: 'Vertical (column)',
}

const directionLabel = computed(() => {
  const d = p.value['direction'] as string | undefined
  return directionLabels[d ?? ''] ?? d ?? '—'
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
.container-inspector {
  display: flex;
  flex-direction: column;
}
</style>
