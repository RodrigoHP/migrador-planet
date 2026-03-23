<template>
  <div class="table-inspector">
    <!-- Geral -->
    <InspectorSection title="Geral" :collapsible="true">
      <InspectorField label="Nome" :value="props.node?.name ?? '—'" />
      <InspectorField label="Fonte de Dados" :value="(p['binding'] as string) || (props.node?.binding ?? '—')" />
    </InspectorSection>

    <!-- Colunas (clicáveis para seleção de célula) -->
    <InspectorSection title="Colunas" :collapsible="true">
      <div v-if="columns.length > 0" class="table-inspector__col-table" role="grid" aria-label="Colunas da tabela">
        <div class="table-inspector__col-header">
          <span></span><span>Campo</span><span>Largura</span><span>Alinhamento</span><span></span>
        </div>
        <div
          v-for="(col, i) in columns"
          :key="i"
          class="table-inspector__col-row"
          :class="{ 'table-inspector__col-row--selected': selectedCell?.col === i }"
          draggable="true"
          @click="selectCell(0, i)"
          @dragstart="onColDragStart($event, i)"
          @dragover.prevent
          @drop="onColDrop($event, i)"
        >
          <span class="table-inspector__drag-handle" title="Arrastar para reordenar">⠿</span>
          <span>{{ col.field ?? '—' }}</span>
          <input
            class="table-inspector__col-input"
            type="number"
            :value="col.width ?? ''"
            placeholder="auto"
            :aria-label="`Largura da coluna ${col.field ?? i}`"
            @input="updateColWidth(i, ($event.target as HTMLInputElement).value)"
            @click.stop
          />
          <select
            class="table-inspector__col-select"
            :value="col.align ?? 'left'"
            :aria-label="`Alinhamento da coluna ${col.field ?? i}`"
            @change="updateColAlign(i, ($event.target as HTMLSelectElement).value)"
            @click.stop
          >
            <option value="left">left</option>
            <option value="center">center</option>
            <option value="right">right</option>
          </select>
          <button
            class="table-inspector__col-remove"
            type="button"
            :aria-label="`Remover coluna ${col.field ?? i}`"
            @click.stop="removeColumn(i)"
          >×</button>
        </div>
        <button class="table-inspector__col-add" type="button" @click="addColumn">
          + Coluna
        </button>
      </div>
      <div v-else>
        <InspectorField label="Colunas" value="—" />
        <button class="table-inspector__col-add" type="button" @click="addColumn">
          + Coluna
        </button>
      </div>
      <div aria-live="polite" class="sr-only">{{ colAnnouncement }}</div>
    </InspectorSection>

    <!-- TableCellEditor (when cell selected) -->
    <TableCellEditor
      v-if="selectedCell && props.node?.id"
      :table-node-id="props.node.id"
      :row="selectedCell.row"
      :col="selectedCell.col"
      :cell-props="selectedCellProps"
      @deselect="selectedCell = null"
    />

    <!-- Linhas -->
    <InspectorSection title="Linhas" :collapsible="true">
      <InspectorField label="Altura da Linha" :value="pxValue('row_height')" />
      <InspectorField label="Padding" :value="pxValue('row_padding')" />
      <InspectorCheckbox
        label="Border Collapse"
        :model-value="Boolean(p['border_collapse'] ?? true)"
        @update:model-value="setTableProp('border_collapse', $event)"
      />
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
import { computed, ref } from 'vue'
import type { TreeNode } from '@/types/template.types'
import type { CellProperties } from '@/types/template.types'
import { getCellKey, createDefaultCellProperties } from '@/types/template.types'
import InspectorField from '@/molecules/InspectorField.vue'
import InspectorSection from '@/molecules/InspectorSection.vue'
import InspectorCheckbox from '@/molecules/InspectorCheckbox.vue'
import InspectorInput from '@/molecules/InspectorInput.vue'
import VisibilityControl from '@/molecules/VisibilityControl.vue'
import type { VisibilityConfig } from '@/molecules/VisibilityControl.vue'
import TableCellEditor from './TableCellEditor.vue'
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

// ─── Column editing (Story 14.12) ────────────────────────────────────────────
const colAnnouncement = ref('')
const dragSourceIndex = ref<number | null>(null)

function updateColWidth(index: number, raw: string) {
  if (!props.node?.id) return
  const cols = [...columns.value]
  const num = raw === '' ? undefined : parseFloat(raw)
  cols[index] = { ...cols[index], width: num !== undefined && !isNaN(num) ? String(num) : undefined }
  templateStore.updateNodeProperty(props.node.id, 'columns', cols)
}

function updateColAlign(index: number, value: string) {
  if (!props.node?.id) return
  const cols = [...columns.value]
  cols[index] = { ...cols[index], align: value }
  templateStore.updateNodeProperty(props.node.id, 'columns', cols)
}

function removeColumn(index: number) {
  if (!props.node?.id) return
  const cols = columns.value.filter((_, i) => i !== index)
  templateStore.updateNodeProperty(props.node.id, 'columns', cols)
  colAnnouncement.value = `Coluna ${index + 1} removida`
}

function addColumn() {
  if (!props.node?.id) return
  const cols = [...columns.value, { field: `col_${columns.value.length + 1}` }]
  templateStore.updateNodeProperty(props.node.id, 'columns', cols)
  colAnnouncement.value = `Coluna ${cols.length} adicionada`
}

function onColDragStart(event: DragEvent, index: number) {
  dragSourceIndex.value = index
  event.dataTransfer?.setData('text/plain', String(index))
}

function onColDrop(_event: DragEvent, targetIndex: number) {
  if (dragSourceIndex.value === null || dragSourceIndex.value === targetIndex || !props.node?.id) return
  const cols = [...columns.value]
  const [moved] = cols.splice(dragSourceIndex.value, 1)
  cols.splice(targetIndex, 0, moved!)
  templateStore.updateNodeProperty(props.node.id, 'columns', cols)
  colAnnouncement.value = `Coluna movida da posição ${dragSourceIndex.value + 1} para ${targetIndex + 1}`
  dragSourceIndex.value = null
}

// ─── Cell Selection (Story 14.4) ─────────────────────────────────────────────
const selectedCell = ref<{ row: number; col: number } | null>(null)

function selectCell(row: number, col: number) {
  if (selectedCell.value?.row === row && selectedCell.value?.col === col) {
    selectedCell.value = null
  } else {
    selectedCell.value = { row, col }
  }
}

const selectedCellProps = computed<CellProperties>(() => {
  if (!selectedCell.value) return createDefaultCellProperties()
  const cells = (p.value['cells'] as Record<string, CellProperties>) ?? {}
  const key = getCellKey(selectedCell.value.row, selectedCell.value.col)
  return cells[key] ?? createDefaultCellProperties()
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
  grid-template-columns: 1.25rem 1fr 3.5rem 4.5rem 1.25rem;
  gap: 0.375rem;
  color: var(--color-neutral-400, #9ca3af);
  font-weight: 600;
  padding: 0.125rem 0;
  border-bottom: 1px solid var(--color-neutral-700, #374151);
}

.table-inspector__col-row {
  display: grid;
  grid-template-columns: 1.25rem 1fr 3.5rem 4.5rem 1.25rem;
  gap: 0.375rem;
  align-items: center;
  color: var(--color-neutral-200, #e5e7eb);
  padding: 0.125rem 0;
  cursor: pointer;
  border-radius: 0.125rem;
  transition: background 0.15s;
}

.table-inspector__col-row:hover {
  background: var(--color-neutral-700, #374151);
}

.table-inspector__col-row--selected {
  background: var(--color-primary-900, #312e81);
  outline: 1px solid var(--color-primary-500, #6366f1);
}

.table-inspector__drag-handle {
  cursor: grab;
  color: var(--color-neutral-500, #6b7280);
  user-select: none;
  font-size: 0.625rem;
  line-height: 1;
}

.table-inspector__col-input {
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  color: var(--color-neutral-100, #f3f4f6);
  font-size: 0.6875rem;
  padding: 0.0625rem 0.25rem;
  width: 100%;
  outline: none;
}

.table-inspector__col-select {
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  color: var(--color-neutral-100, #f3f4f6);
  font-size: 0.6875rem;
  padding: 0.0625rem 0.125rem;
  width: 100%;
  outline: none;
  cursor: pointer;
}

.table-inspector__col-remove {
  background: none;
  border: none;
  color: var(--color-neutral-500, #6b7280);
  cursor: pointer;
  font-size: 0.75rem;
  padding: 0;
  line-height: 1;
  border-radius: 0.125rem;
}

.table-inspector__col-remove:hover {
  color: var(--color-error-400, #f87171);
}

.table-inspector__col-add {
  background: none;
  border: 1px dashed var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  color: var(--color-neutral-400, #9ca3af);
  cursor: pointer;
  font-size: 0.6875rem;
  padding: 0.25rem;
  margin-top: 0.25rem;
  width: 100%;
  transition: border-color 0.15s, color 0.15s;
}

.table-inspector__col-add:hover {
  border-color: var(--color-primary-500, #6366f1);
  color: var(--color-primary-400, #818cf8);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
</style>
