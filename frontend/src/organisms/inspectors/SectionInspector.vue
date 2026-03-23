<template>
  <div class="section-inspector">
    <!-- Geral -->
    <InspectorSection title="Geral" :collapsible="true">
      <InspectorField label="Tipo" :value="sectionTypeLabel" type="badge" />
      <InspectorInput
        label="Altura (px)"
        type="number"
        :min="0"
        :model-value="(p['height'] as number)"
        @update:model-value="setProp('height', $event)"
      />
    </InspectorSection>

    <!-- Aparência -->
    <InspectorSection title="Aparência" :collapsible="true">
      <InspectorColorPicker
        label="Cor de Fundo"
        :model-value="(p['background_color'] as string) || ''"
        @update:model-value="setProp('background_color', $event)"
      />
      <div class="section-inspector__file-field">
        <span class="section-inspector__file-label">Imagem de Fundo</span>
        <div class="section-inspector__file-wrap">
          <span class="section-inspector__file-value">
            {{ (p['background_image'] as string) || '—' }}
          </span>
          <label class="section-inspector__file-btn">
            Escolher
            <input
              type="file"
              accept="image/*"
              class="section-inspector__file-input"
              @change="onBgImageChange"
            />
          </label>
        </div>
      </div>
    </InspectorSection>

    <!-- Bordas -->
    <InspectorSection title="Bordas" :collapsible="true">
      <BorderEditor
        :model-value="borderConfig"
        @update:model-value="onBorderChange"
      />
    </InspectorSection>

    <!-- Espaçamento -->
    <InspectorSection title="Espaçamento" :collapsible="true">
      <InspectorInput
        label="Padding Topo (px)"
        type="number"
        :min="0"
        :model-value="(p['padding_top'] as number)"
        @update:model-value="setProp('padding_top', $event)"
      />
      <InspectorInput
        label="Padding Base (px)"
        type="number"
        :min="0"
        :model-value="(p['padding_bottom'] as number)"
        @update:model-value="setProp('padding_bottom', $event)"
      />
      <InspectorInput
        label="Padding Esquerda (px)"
        type="number"
        :min="0"
        :model-value="(p['padding_left'] as number)"
        @update:model-value="setProp('padding_left', $event)"
      />
      <InspectorInput
        label="Padding Direita (px)"
        type="number"
        :min="0"
        :model-value="(p['padding_right'] as number)"
        @update:model-value="setProp('padding_right', $event)"
      />
    </InspectorSection>

    <!-- Comportamento -->
    <InspectorSection title="Comportamento" :collapsible="true">
      <!-- "Repetir em cada página" — visível apenas para Header e Footer (AC #2) -->
      <template v-if="isHeaderOrFooter">
        <InspectorCheckbox
          label="Repetir em cada página"
          :model-value="Boolean(p['repeat_per_page'])"
          @update:model-value="onRepeatChange"
        />
        <!-- Altura editável para header/footer quando repetição está ativa (AC #2) -->
        <InspectorInput
          v-if="Boolean(p['repeat_per_page'])"
          label="Altura do Header/Footer (px)"
          type="number"
          :min="0"
          :model-value="(p['height'] as number)"
          @update:model-value="onHeaderFooterHeightChange"
        />
      </template>
      <InspectorCheckbox
        label="Repetir por Página"
        :model-value="Boolean(p['repeat_per_page'])"
        @update:model-value="setProp('repeat_per_page', $event)"
        v-if="!isHeaderOrFooter"
      />
      <InspectorCheckbox
        label="Bloquear Seção"
        :model-value="Boolean(p['locked'])"
        @update:model-value="setProp('locked', $event)"
      />
    </InspectorSection>

    <!-- Visibilidade -->
    <InspectorSection title="Visibilidade" :collapsible="true">
      <VisibilityControl
        :model-value="visibilityConfig"
        @update:model-value="updateVisibility"
      />
    </InspectorSection>

    <!-- Remover -->
    <div class="section-inspector__remove-wrap">
      <button
        class="section-inspector__remove-btn"
        type="button"
        @click="onRemove"
      >
        Remover do template
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TreeNode } from '@/types/template.types'
import type { BorderConfig } from '@/types/template.types'
import { createDefaultBorderConfig } from '@/types/template.types'
import InspectorField from '@/molecules/InspectorField.vue'
import InspectorSection from '@/molecules/InspectorSection.vue'
import InspectorInput from '@/molecules/InspectorInput.vue'
import BorderEditor from '@/molecules/BorderEditor.vue'
import InspectorCheckbox from '@/molecules/InspectorCheckbox.vue'
import InspectorColorPicker from '@/molecules/InspectorColorPicker.vue'
import VisibilityControl from '@/molecules/VisibilityControl.vue'
import type { VisibilityConfig } from '@/molecules/VisibilityControl.vue'
import { useTemplateStore } from '@/stores/templateStore'
import { useInspectorStore } from '@/stores/inspectorStore'
import { usePagination } from '@/composables/usePagination'

const props = withDefaults(
  defineProps<{ node?: TreeNode | null }>(),
  { node: null },
)

const templateStore = useTemplateStore()
const inspectorStore = useInspectorStore()
const { setPageConfig } = usePagination()

const p = computed(() => (props.node?.properties ?? {}) as Record<string, unknown>)

const sectionTypeLabels: Record<string, string> = {
  header: 'Header',
  flow: 'Flow',
  footer: 'Footer',
}

const sectionTypeLabel = computed(() => {
  const t = (p.value['section_type'] as string) || (props.node?.type as string) || ''
  return sectionTypeLabels[t] ?? (t || '—')
})

/**
 * Whether the current section is a Header or Footer — controls visibility of
 * "Repetir em cada página" toggle (AC #2 Story 9.6).
 */
const isHeaderOrFooter = computed(() => {
  const t = (p.value['section_type'] as string) || (props.node?.type as string) || ''
  return t === 'header' || t === 'footer'
})

const visibilityConfig = computed<VisibilityConfig>(() => {
  const raw = p.value['visibility']
  if (raw && typeof raw === 'object' && 'mode' in (raw as object)) {
    return raw as VisibilityConfig
  }
  // Legacy string value or undefined
  const mode = (raw as string) || 'always'
  return { mode: mode as VisibilityConfig['mode'] }
})

function updateVisibility(config: VisibilityConfig) {
  setProp('visibility', config)
}

function setProp(key: string, value: unknown) {
  if (props.node?.id) {
    templateStore.updateNodeProperty(props.node.id, key, value)
  }
}

// ─── Border Config ──────────────────────────────────────────────────────────
const borderConfig = computed<BorderConfig>(() => {
  const d = createDefaultBorderConfig()
  const v = p.value
  const num = (k: string) => (typeof v[k] === 'number' ? (v[k] as number) : undefined)
  const str = (k: string) => (typeof v[k] === 'string' ? (v[k] as string) : undefined)
  return {
    top: { width: num('border_top_width') ?? d.top.width, color: str('border_top_color') ?? d.top.color, style: (str('border_top_style') as BorderConfig['top']['style']) ?? d.top.style },
    right: { width: num('border_right_width') ?? d.right.width, color: str('border_right_color') ?? d.right.color, style: (str('border_right_style') as BorderConfig['right']['style']) ?? d.right.style },
    bottom: { width: num('border_bottom_width') ?? d.bottom.width, color: str('border_bottom_color') ?? d.bottom.color, style: (str('border_bottom_style') as BorderConfig['bottom']['style']) ?? d.bottom.style },
    left: { width: num('border_left_width') ?? d.left.width, color: str('border_left_color') ?? d.left.color, style: (str('border_left_style') as BorderConfig['left']['style']) ?? d.left.style },
    radius: {
      topLeft: num('border_radius_top_left') ?? d.radius.topLeft,
      topRight: num('border_radius_top_right') ?? d.radius.topRight,
      bottomRight: num('border_radius_bottom_right') ?? d.radius.bottomRight,
      bottomLeft: num('border_radius_bottom_left') ?? d.radius.bottomLeft,
    },
    uniform: d.uniform,
  }
})

function onBorderChange(config: BorderConfig) {
  if (!props.node?.id) return
  const id = props.node.id
  setProp('border_top_width', config.top.width)
  setProp('border_top_color', config.top.color)
  setProp('border_top_style', config.top.style)
  setProp('border_right_width', config.right.width)
  setProp('border_right_color', config.right.color)
  setProp('border_right_style', config.right.style)
  setProp('border_bottom_width', config.bottom.width)
  setProp('border_bottom_color', config.bottom.color)
  setProp('border_bottom_style', config.bottom.style)
  setProp('border_left_width', config.left.width)
  setProp('border_left_color', config.left.color)
  setProp('border_left_style', config.left.style)
  setProp('border_radius_top_left', config.radius.topLeft)
  setProp('border_radius_top_right', config.radius.topRight)
  setProp('border_radius_bottom_right', config.radius.bottomRight)
  setProp('border_radius_bottom_left', config.radius.bottomLeft)
}

/**
 * Handle "Repetir em cada página" toggle for header/footer.
 * Updates the node property and triggers Layout Engine recalculation (AC #3).
 */
function onRepeatChange(value: boolean) {
  setProp('repeat_per_page', value)
  // Trigger Layout Engine recalculation by updating the page config
  const sectionType = (p.value['section_type'] as string) || (props.node?.type as string) || ''
  const height = (p.value['height'] as number) ?? 0
  if (sectionType === 'header') {
    setPageConfig({ headerHeight: value ? height : 0 })
  } else if (sectionType === 'footer') {
    setPageConfig({ footerHeight: value ? height : 0 })
  }
}

/**
 * Handle height change for header/footer with repeat enabled.
 * Propagates height change to the Layout Engine (AC #3).
 */
function onHeaderFooterHeightChange(value: string | number) {
  const numValue = typeof value === 'string' ? parseFloat(value) : value
  const safeValue = isNaN(numValue) ? 0 : numValue
  setProp('height', safeValue)
  const sectionType = (p.value['section_type'] as string) || (props.node?.type as string) || ''
  if (sectionType === 'header') {
    setPageConfig({ headerHeight: safeValue })
  } else if (sectionType === 'footer') {
    setPageConfig({ footerHeight: safeValue })
  }
}

function onBgImageChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const url = URL.createObjectURL(file)
  setProp('background_image', url)
}

function onRemove() {
  if (!props.node?.id) return
  const ok = confirm('Remover esta seção do template?')
  if (!ok) return
  templateStore.removeNode(props.node.id)
  inspectorStore.clearSelection()
}
</script>

<style scoped>
.section-inspector {
  display: flex;
  flex-direction: column;
}

.section-inspector__file-field {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.25rem 0;
}

.section-inspector__file-label {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  user-select: none;
}

.section-inspector__file-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.section-inspector__file-value {
  font-size: 0.75rem;
  color: var(--color-neutral-300, #d1d5db);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.section-inspector__file-btn {
  font-size: 0.75rem;
  padding: 0.1875rem 0.5rem;
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-200, #e5e7eb);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  cursor: pointer;
  white-space: nowrap;
  user-select: none;
}

.section-inspector__file-input {
  display: none;
}

.section-inspector__remove-wrap {
  padding: 0.75rem 0 0.25rem;
  border-top: 1px solid var(--color-neutral-700, #374151);
  margin-top: 0.5rem;
}

.section-inspector__remove-btn {
  width: 100%;
  padding: 0.375rem;
  font-size: 0.75rem;
  background: transparent;
  color: var(--color-error-400, #f87171);
  border: 1px solid var(--color-error-700, #b91c1c);
  border-radius: 0.25rem;
  cursor: pointer;
  transition: background 0.15s;
}

.section-inspector__remove-btn:hover {
  background: var(--color-error-900, #450a0a);
}
</style>
