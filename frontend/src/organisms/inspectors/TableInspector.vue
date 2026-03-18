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

    <!-- Paginação (Story 9.5) -->
    <InspectorSection title="Paginação" :collapsible="true">
      <InspectorCheckbox
        label="Quebrar entre páginas"
        :model-value="Boolean(p['page_break'])"
        @update:model-value="setTableProp('page_break', $event)"
      />
      <InspectorCheckbox
        label="Repetir cabeçalho"
        :model-value="Boolean(p['repeat_header'])"
        @update:model-value="setTableProp('repeat_header', $event)"
      />
      <InspectorInput
        label="Mínimo de linhas por página"
        type="number"
        :min="1"
        :model-value="(p['min_rows'] as number) ?? 3"
        @update:model-value="setTableProp('min_rows', $event)"
      />
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
import InspectorCheckbox from '@/molecules/InspectorCheckbox.vue'
import InspectorInput from '@/molecules/InspectorInput.vue'
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

const columns = computed(() => {
  const cols = p.value['columns']
  if (Array.isArray(cols)) return cols as Array<{ field?: string; width?: string; align?: string }>
  return []
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

function setTableProp(key: string, value: unknown) {
  if (props.node?.id) {
    templateStore.updateNodeProperty(props.node.id, key, value)
  }
}
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
