<template>
  <div class="element-inspector">
    <!-- Posição -->
    <InspectorSection title="Posição" :collapsible="true">
      <InspectorField label="X" :value="pxValue('x')" />
      <InspectorField label="Y" :value="pxValue('y')" />
    </InspectorSection>

    <!-- Dimensões -->
    <InspectorSection title="Dimensões" :collapsible="true">
      <InspectorField label="Largura" :value="pxValue('width')" />
      <InspectorField label="Altura" :value="pxValue('height')" />
    </InspectorSection>

    <!-- Tipografia -->
    <InspectorSection title="Tipografia" :collapsible="true">
      <InspectorField label="Família da Fonte" :value="strValue('font_family')" />
      <InspectorField label="Tamanho" :value="pxValue('font_size')" />
      <InspectorField label="Peso" :value="strValue('font_weight')" />
      <InspectorField
        label="Cor"
        :value="strValue('color')"
        :type="p['color'] ? 'color' : 'text'"
      />
      <InspectorField label="Line-Height" :value="strValue('line_height')" />
      <InspectorField label="Espaçamento" :value="strValue('letter_spacing')" />
    </InspectorSection>

    <!-- Dados -->
    <InspectorSection title="Dados" :collapsible="true">
      <InspectorField label="Tipo de Campo" :value="fieldTypeLabel" type="badge" />
      <InspectorField label="Binding" :value="(props.node?.binding ?? strValue('binding'))" />
    </InspectorSection>

    <!-- Posição Avançada -->
    <InspectorSection title="Posição Avançada" :collapsible="true">
      <InspectorField label="Âncora" :value="strValue('anchor')" />
    </InspectorSection>

    <!-- Visibilidade -->
    <InspectorSection title="Visibilidade" :collapsible="true">
      <InspectorField label="Estado" :value="visibilityLabel" type="badge" />
      <InspectorField label="Camada" :value="strValue('layer')" />
      <InspectorField label="Bloqueio" :value="boolLabel('locked')" />
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

function strValue(key: string): string {
  const v = p.value[key]
  return v !== undefined && v !== null ? String(v) : '—'
}

function boolLabel(key: string): string {
  return p.value[key] ? 'Sim' : 'Não'
}

const fieldTypeLabels: Record<string, string> = {
  text: 'Texto',
  number: 'Número',
  currency_brl: 'Moeda (BRL)',
  date: 'Data',
  cpf: 'CPF',
  cnpj: 'CNPJ',
  percentage: 'Percentual',
  phone: 'Telefone',
  custom: 'Personalizado',
}

const fieldTypeLabel = computed(() => {
  const t = p.value['field_type'] as string | undefined
  return fieldTypeLabels[t ?? ''] ?? (t ?? '—')
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
.element-inspector {
  display: flex;
  flex-direction: column;
}
</style>
