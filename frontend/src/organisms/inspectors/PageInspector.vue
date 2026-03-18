<template>
  <div class="page-inspector">
    <!-- Dimensões -->
    <InspectorSection title="Dimensões" :collapsible="true">
      <InspectorSelect
        label="Tamanho"
        :model-value="(p['size'] as string) || 'A4'"
        :options="pageSizeOptions"
        @update:model-value="setPageProp('size', $event)"
      />
      <template v-if="(p['size'] as string) === 'custom'">
        <InspectorInput
          label="Largura (mm)"
          type="number"
          :min="1"
          :model-value="(p['page_width'] as number)"
          @update:model-value="setPageProp('page_width', $event)"
        />
        <InspectorInput
          label="Altura (mm)"
          type="number"
          :min="1"
          :model-value="(p['page_height'] as number)"
          @update:model-value="setPageProp('page_height', $event)"
        />
      </template>
      <div class="page-inspector__radio-group">
        <span class="page-inspector__radio-label">Orientação</span>
        <label class="page-inspector__radio-opt">
          <input
            type="radio"
            name="orientation"
            value="portrait"
            :checked="orientation === 'portrait'"
            @change="setPageProp('orientation', 'portrait')"
          />
          Retrato
        </label>
        <label class="page-inspector__radio-opt">
          <input
            type="radio"
            name="orientation"
            value="landscape"
            :checked="orientation === 'landscape'"
            @change="setPageProp('orientation', 'landscape')"
          />
          Paisagem
        </label>
      </div>
    </InspectorSection>

    <!-- Margens -->
    <InspectorSection title="Margens" :collapsible="true">
      <InspectorInput
        label="Topo (mm)"
        type="number"
        :min="0"
        :max="marginMaxV"
        :model-value="(p['margin_top'] as number)"
        @update:model-value="setPageProp('margin_top', $event)"
      />
      <InspectorInput
        label="Base (mm)"
        type="number"
        :min="0"
        :max="marginMaxV"
        :model-value="(p['margin_bottom'] as number)"
        @update:model-value="setPageProp('margin_bottom', $event)"
      />
      <InspectorInput
        label="Esquerda (mm)"
        type="number"
        :min="0"
        :max="marginMaxH"
        :model-value="(p['margin_left'] as number)"
        @update:model-value="setPageProp('margin_left', $event)"
      />
      <InspectorInput
        label="Direita (mm)"
        type="number"
        :min="0"
        :max="marginMaxH"
        :model-value="(p['margin_right'] as number)"
        @update:model-value="setPageProp('margin_right', $event)"
      />
    </InspectorSection>

    <!-- Estrutura -->
    <InspectorSection title="Estrutura" :collapsible="true">
      <InspectorInput
        label="Altura do Header (px)"
        type="number"
        :min="0"
        :model-value="(p['header_height'] as number)"
        @update:model-value="setPageProp('header_height', $event)"
      />
      <InspectorInput
        label="Altura do Footer (px)"
        type="number"
        :min="0"
        :model-value="(p['footer_height'] as number)"
        @update:model-value="setPageProp('footer_height', $event)"
      />
      <InspectorField label="Área de Conteúdo" :value="contentAreaValue" />
    </InspectorSection>

    <!-- Grid -->
    <InspectorSection title="Grid" :collapsible="true">
      <InspectorCheckbox
        label="Ativar Grid"
        :model-value="Boolean(p['grid_enabled'])"
        @update:model-value="setPageProp('grid_enabled', $event)"
      />
      <InspectorInput
        v-if="p['grid_enabled']"
        label="Tamanho do Grid (px)"
        type="number"
        :min="1"
        :model-value="(p['grid_size'] as number)"
        @update:model-value="setPageProp('grid_size', $event)"
      />
    </InspectorSection>

    <!-- Colunas -->
    <InspectorSection title="Colunas" :collapsible="true">
      <InspectorField label="Colunas Detectadas" :value="columnsCount" />
      <InspectorField label="Posições" :value="columnsPositions" />
      <InspectorCheckbox
        label="Travar Colunas"
        :model-value="Boolean(p['columns_locked'])"
        @update:model-value="setPageProp('columns_locked', $event)"
      />
    </InspectorSection>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TreeNode } from '@/types/template.types'
import InspectorField from '@/molecules/InspectorField.vue'
import InspectorSection from '@/molecules/InspectorSection.vue'
import InspectorInput from '@/molecules/InspectorInput.vue'
import InspectorSelect from '@/molecules/InspectorSelect.vue'
import InspectorCheckbox from '@/molecules/InspectorCheckbox.vue'
import { useTemplateStore } from '@/stores/templateStore'

const props = withDefaults(
  defineProps<{ node?: TreeNode | null }>(),
  { node: null },
)

const templateStore = useTemplateStore()

const p = computed(() => (props.node?.properties ?? {}) as Record<string, unknown>)

const pageSizeOptions = [
  { value: 'A4', label: 'A4 (210×297mm)' },
  { value: 'letter', label: 'Letter (216×279mm)' },
  { value: 'custom', label: 'Personalizado' },
]

const orientation = computed(() => {
  const raw = p.value['orientation'] as string | undefined
  return raw === 'landscape' ? 'landscape' : 'portrait'
})

const pageHeight = computed(() => Number(p.value['page_height'] ?? 297))
const pageWidth = computed(() => Number(p.value['page_width'] ?? 210))

const marginMaxV = computed(() => Math.max(0, pageHeight.value - 1))
const marginMaxH = computed(() => Math.max(0, pageWidth.value - 1))

const contentAreaValue = computed(() => {
  const headerH = Number(p.value['header_height'] ?? 0)
  const footerH = Number(p.value['footer_height'] ?? 0)
  const marginTop = Number(p.value['margin_top'] ?? 0)
  const marginBottom = Number(p.value['margin_bottom'] ?? 0)
  const area = pageHeight.value - (headerH / 3.7795) - (footerH / 3.7795) - marginTop - marginBottom
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

function setPageProp(key: string, value: unknown) {
  if (props.node?.id) {
    templateStore.updateNodeProperty(props.node.id, key, value)
  }
}
</script>

<style scoped>
.page-inspector {
  display: flex;
  flex-direction: column;
}

.page-inspector__radio-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.25rem 0;
}

.page-inspector__radio-label {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  user-select: none;
}

.page-inspector__radio-opt {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: var(--color-neutral-100, #f3f4f6);
  cursor: pointer;
  user-select: none;
}

.page-inspector__radio-opt input {
  accent-color: var(--color-primary-500, #6366f1);
  cursor: pointer;
}
</style>
