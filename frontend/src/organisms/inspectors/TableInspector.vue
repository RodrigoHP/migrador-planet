<template>
  <div class="table-inspector">
    <!-- Geral -->
    <InspectorSection title="Geral" :collapsible="true">
      <InspectorField label="Nome" :value="props.node?.name ?? '—'" />
      <InspectorField label="Fonte de Dados" :value="(p['binding'] as string) || (props.node?.binding ?? '—')" />
    </InspectorSection>

    <!-- Colunas -->
    <InspectorSection title="Colunas" :collapsible="true">
      <div v-if="columns.length > 0" class="table-inspector__col-table">
        <div class="table-inspector__col-header">
          <span>Campo</span><span>Largura</span><span>Alinhamento</span>
        </div>
        <div
          v-for="(col, i) in columns"
          :key="i"
          class="table-inspector__col-row"
        >
          <span>{{ col.field ?? '—' }}</span>
          <span>{{ col.width ?? '—' }}</span>
          <span>{{ col.align ?? '—' }}</span>
        </div>
      </div>
      <InspectorField v-else label="Colunas" value="—" />
    </InspectorSection>

    <!-- Linhas -->
    <InspectorSection title="Linhas" :collapsible="true">
      <InspectorField label="Altura da Linha" :value="pxValue('row_height')" />
      <InspectorField label="Padding" :value="pxValue('row_padding')" />
    </InspectorSection>

    <!-- Paginação -->
    <InspectorSection title="Paginação" :collapsible="true">
      <InspectorField label="Quebra de Página" :value="boolLabel('page_break')" />
      <InspectorField label="Repetir Header" :value="boolLabel('repeat_header')" />
      <InspectorField label="Mínimo de Linhas" :value="strValue('min_rows')" />
    </InspectorSection>

    <!-- Posição -->
    <InspectorSection title="Posição" :collapsible="true">
      <InspectorField label="Âncora" :value="strValue('anchor')" />
      <InspectorField label="Manter Junto" :value="boolLabel('keep_together')" />
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

function boolLabel(key: string): string {
  return p.value[key] ? 'Sim' : 'Não'
}

function strValue(key: string): string {
  const v = p.value[key]
  return v !== undefined && v !== null ? String(v) : '—'
}

const columns = computed(() => {
  const cols = p.value['columns']
  if (Array.isArray(cols)) return cols as Array<{ field?: string; width?: string; align?: string }>
  return []
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
.table-inspector {
  display: flex;
  flex-direction: column;
}

.table-inspector__col-table {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  font-size: 0.75rem;
}

.table-inspector__col-header {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 0.5rem;
  color: var(--color-neutral-400, #9ca3af);
  font-weight: 600;
  padding: 0.125rem 0;
  border-bottom: 1px solid var(--color-neutral-700, #374151);
}

.table-inspector__col-row {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 0.5rem;
  color: var(--color-neutral-200, #e5e7eb);
  padding: 0.125rem 0;
}
</style>
