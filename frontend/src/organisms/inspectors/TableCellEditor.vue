<template>
  <div class="table-cell-editor">
    <div class="table-cell-editor__header">
      <span class="table-cell-editor__title">Célula [{{ row }}, {{ col }}]</span>
      <button class="table-cell-editor__close" type="button" @click="$emit('deselect')">✕</button>
    </div>

    <!-- Bordas -->
    <InspectorSection title="Bordas da Célula" :collapsible="true">
      <BorderEditor :model-value="cellBorderConfig" @update:model-value="onBorderChange" />
    </InspectorSection>

    <!-- Background -->
    <InspectorSection title="Fundo" :collapsible="true">
      <InspectorColorPicker
        label="Cor de Fundo"
        :model-value="cellProps.backgroundColor || ''"
        @update:model-value="onBgChange"
      />
    </InspectorSection>

    <!-- Padding -->
    <InspectorSection title="Padding" :collapsible="true">
      <div class="table-cell-editor__padding-grid">
        <InspectorInput
          label="Topo (px)"
          type="number"
          :min="0"
          :model-value="cellPadding.top"
          @update:model-value="onPaddingChange('top', $event as number)"
        />
        <InspectorInput
          label="Direita (px)"
          type="number"
          :min="0"
          :model-value="cellPadding.right"
          @update:model-value="onPaddingChange('right', $event as number)"
        />
        <InspectorInput
          label="Baixo (px)"
          type="number"
          :min="0"
          :model-value="cellPadding.bottom"
          @update:model-value="onPaddingChange('bottom', $event as number)"
        />
        <InspectorInput
          label="Esquerda (px)"
          type="number"
          :min="0"
          :model-value="cellPadding.left"
          @update:model-value="onPaddingChange('left', $event as number)"
        />
      </div>
    </InspectorSection>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BorderConfig, CellProperties, CellPadding } from '@/types/template.types'
import { createDefaultBorderConfig } from '@/types/template.types'
import InspectorSection from '@/molecules/InspectorSection.vue'
import InspectorInput from '@/molecules/InspectorInput.vue'
import InspectorColorPicker from '@/molecules/InspectorColorPicker.vue'
import BorderEditor from '@/molecules/BorderEditor.vue'
import { useTemplateStore } from '@/stores/templateStore'

const props = defineProps<{
  tableNodeId: string
  row: number
  col: number
  cellProps: CellProperties
}>()

defineEmits<{
  deselect: []
}>()

const templateStore = useTemplateStore()

const cellBorderConfig = computed<BorderConfig>(() => {
  return props.cellProps.border ?? createDefaultBorderConfig()
})

const cellPadding = computed<CellPadding>(() => {
  return props.cellProps.padding ?? { top: 0, right: 0, bottom: 0, left: 0 }
})

function onBorderChange(config: BorderConfig) {
  templateStore.updateCellProperty(props.tableNodeId, props.row, props.col, { border: config })
}

function onBgChange(color: string) {
  templateStore.updateCellProperty(props.tableNodeId, props.row, props.col, {
    backgroundColor: color,
  })
}

function onPaddingChange(side: keyof CellPadding, value: number) {
  const current = { ...cellPadding.value }
  current[side] = value
  templateStore.updateCellProperty(props.tableNodeId, props.row, props.col, { padding: current })
}
</script>

<style scoped>
.table-cell-editor__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.375rem 0.75rem;
  border-bottom: 1px solid var(--color-neutral-700, #374151);
}

.table-cell-editor__title {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-primary-400, #818cf8);
}

.table-cell-editor__close {
  background: none;
  border: none;
  color: var(--color-neutral-400, #9ca3af);
  cursor: pointer;
  font-size: 0.75rem;
  padding: 0.125rem;
}

.table-cell-editor__close:hover {
  color: var(--color-neutral-200, #e5e7eb);
}

.table-cell-editor__padding-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.25rem;
}
</style>
