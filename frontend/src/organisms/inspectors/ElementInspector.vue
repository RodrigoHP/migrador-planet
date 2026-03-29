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

    <!-- Box Model (Story 14.12) -->
    <InspectorSection title="Box Model" :collapsible="true">
      <BoxModelVisualization
        :margin="boxMargin"
        :border="boxBorder"
        :padding="boxPadding"
        :content-width="numValue('width')"
        :content-height="numValue('height')"
        @update:margin="onBoxUpdate('margin', $event)"
        @update:border="onBoxUpdate('border', $event)"
        @update:padding="onBoxUpdate('padding', $event)"
      />
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

      <!-- Font Warning: shown when font is not found in catalog -->
      <FontWarning
        v-if="detectedFont"
        :detected-font="detectedFont"
        :fallback-font="fontFallback"
        :status="fontCascade.fontStatus.value"
        @upload="handleFontUpload"
      />

      <!-- Text Alignment (Story 14.3) -->
      <InspectorButtonGroup
        label="Alinhamento"
        :options="TEXT_ALIGN_OPTIONS"
        :model-value="(p['text_align'] as string) || 'left'"
        @update:model-value="setTextProp('text_align', $event)"
      />

      <!-- Vertical Align — only for table cells -->
      <InspectorButtonGroup
        v-if="isTableCell"
        label="Alinhamento Vertical"
        :options="VERTICAL_ALIGN_OPTIONS"
        :model-value="(p['vertical_align'] as string) || 'top'"
        @update:model-value="setTextProp('vertical_align', $event)"
      />

      <!-- Font Style Italic + Text Decoration -->
      <InspectorButtonGroup
        label="Estilo"
        :options="fontStyleOptions"
        :model-value="fontStyleValue"
        :multiple="true"
        @update:model-value="onFontStyleDecoChange"
      />

      <!-- Text Transform -->
      <InspectorButtonGroup
        label="Transformação"
        :options="TEXT_TRANSFORM_OPTIONS"
        :model-value="(p['text_transform'] as string) || 'none'"
        @update:model-value="setTextProp('text_transform', $event)"
      />
    </InspectorSection>

    <!-- Aparência (Story 14.6) -->
    <InspectorSection title="Aparência" :collapsible="true">
      <InspectorColorPicker
        label="Cor de Fundo"
        :model-value="(p['background_color'] as string) || ''"
        :show-presets="true"
        :document-colors="documentColors"
        @update:model-value="onBackgroundColorChange"
      />
    </InspectorSection>

    <!-- Padding (Story 14.9) -->
    <InspectorSection title="Padding" :collapsible="true">
      <div class="element-inspector__padding-grid">
        <InspectorInput
          label="Top"
          type="number"
          :min="0"
          :model-value="paddingValue('padding_top')"
          @update:model-value="setPaddingProp('padding_top', $event)"
        />
        <InspectorInput
          label="Right"
          type="number"
          :min="0"
          :model-value="paddingValue('padding_right')"
          @update:model-value="setPaddingProp('padding_right', $event)"
        />
        <InspectorInput
          label="Bottom"
          type="number"
          :min="0"
          :model-value="paddingValue('padding_bottom')"
          @update:model-value="setPaddingProp('padding_bottom', $event)"
        />
        <InspectorInput
          label="Left"
          type="number"
          :min="0"
          :model-value="paddingValue('padding_left')"
          @update:model-value="setPaddingProp('padding_left', $event)"
        />
      </div>
    </InspectorSection>

    <!-- Bordas -->
    <InspectorSection title="Bordas" :collapsible="true">
      <BorderEditor
        :model-value="borderConfig"
        @update:model-value="onBorderChange"
      />
    </InspectorSection>

    <!-- Dados -->
    <InspectorSection title="Dados" :collapsible="true">
      <InspectorField label="Tipo de Campo" :value="fieldTypeLabel" type="badge" />
      <InspectorField label="Binding" :value="(props.node?.binding ?? strValue('binding'))" />
    </InspectorSection>

    <!-- Format String -->
    <InspectorSection title="Format String" :collapsible="true">
      <FormatStringEditor
        :modelValue="formatString"
        :testData="testDataRecord"
        @update:modelValue="onFormatStringChange"
      />
    </InspectorSection>

    <!-- Estilo Condicional -->
    <InspectorSection title="Estilo Condicional" :collapsible="true">
      <ConditionalStyleSection
        :modelValue="styleRules"
        @update:modelValue="onStyleRulesChange"
      />
    </InspectorSection>

    <!-- Posição Avançada -->
    <InspectorSection title="Posição Avançada" :collapsible="true">
      <InspectorField label="Âncora" :value="strValue('anchor')" />
    </InspectorSection>

    <!-- Visibilidade -->
    <InspectorSection title="Visibilidade" :collapsible="true">
      <VisibilityControl
        :model-value="visibilityConfig"
        :node-label="props.node?.name ?? ''"
        @update:model-value="updateVisibility"
      />
      <InspectorField label="Camada" :value="strValue('layer')" />
      <InspectorField label="Bloqueio" :value="boolLabel('locked')" />
    </InspectorSection>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import type { TreeNode } from '@/types/template.types'
import type { BorderConfig } from '@/types/template.types'
import { createDefaultBorderConfig, TEXT_ALIGN_OPTIONS, VERTICAL_ALIGN_OPTIONS, TEXT_DECORATION_OPTIONS, TEXT_TRANSFORM_OPTIONS } from '@/types/template.types'
import InspectorField from '@/molecules/InspectorField.vue'
import InspectorInput from '@/molecules/InspectorInput.vue'
import InspectorSection from '@/molecules/InspectorSection.vue'
import InspectorColorPicker from '@/molecules/InspectorColorPicker.vue'
import BorderEditor from '@/molecules/BorderEditor.vue'
import InspectorButtonGroup from '@/molecules/InspectorButtonGroup.vue'
import VisibilityControl from '@/molecules/VisibilityControl.vue'
import type { VisibilityConfig } from '@/molecules/VisibilityControl.vue'
import FormatStringEditor from '@/molecules/FormatStringEditor.vue'
import ConditionalStyleSection from '@/molecules/ConditionalStyleSection.vue'
import FontWarning from '@/molecules/FontWarning.vue'
import BoxModelVisualization from '@/molecules/BoxModelVisualization.vue'
import type { BoxSides } from '@/molecules/BoxModelVisualization.vue'
import { useTemplateStore } from '@/stores/templateStore'
import { useBibliotecas } from '@/composables/useBibliotecas'
import { useFontCascade } from '@/composables/useFontCascade'
import type { StyleRule } from '@/utils/formatStringGenerator'

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

function strValue(key: string): string {
  const v = p.value[key]
  return v !== undefined && v !== null ? String(v) : '—'
}

function boolLabel(key: string): string {
  return p.value[key] ? 'Sim' : 'Não'
}

function numValue(key: string): number {
  const v = p.value[key]
  return typeof v === 'number' ? v : 0
}

// ─── Box Model (Story 14.12) ────────────────────────────────────────────────
function boxSides(prefix: string): BoxSides {
  return {
    top: numValue(`${prefix}_top`),
    right: numValue(`${prefix}_right`),
    bottom: numValue(`${prefix}_bottom`),
    left: numValue(`${prefix}_left`),
  }
}

const boxMargin = computed(() => boxSides('margin'))
const boxBorder = computed(() => ({
  top: numValue('border_top_width'),
  right: numValue('border_right_width'),
  bottom: numValue('border_bottom_width'),
  left: numValue('border_left_width'),
}))
const boxPadding = computed(() => boxSides('padding'))

function onBoxUpdate(layer: 'margin' | 'border' | 'padding', sides: BoxSides) {
  if (!props.node?.id) return
  const id = props.node.id
  if (layer === 'border') {
    templateStore.updateNodeProperty(id, 'border_top_width', sides.top)
    templateStore.updateNodeProperty(id, 'border_right_width', sides.right)
    templateStore.updateNodeProperty(id, 'border_bottom_width', sides.bottom)
    templateStore.updateNodeProperty(id, 'border_left_width', sides.left)
  } else {
    templateStore.updateNodeProperty(id, `${layer}_top`, sides.top)
    templateStore.updateNodeProperty(id, `${layer}_right`, sides.right)
    templateStore.updateNodeProperty(id, `${layer}_bottom`, sides.bottom)
    templateStore.updateNodeProperty(id, `${layer}_left`, sides.left)
  }
}

// ─── Text Properties (Story 14.3) ────────────────────────────────────────────
const isTableCell = computed(() => {
  const t = props.node?.type as string | undefined
  // 'table-cell' is not in NodeType enum but backend may send it as a raw string
  // is_table_cell property is the canonical flag set by pipeline/session loaders
  return (
    t === 'table-cell' ||
    (p.value['is_table_cell'] as boolean) === true ||
    (typeof t === 'string' && t.toLowerCase().includes('cell'))
  )
})

const fontStyleOptions = computed(() => [
  { value: 'italic', icon: 'I', label: 'Itálico' },
  ...TEXT_DECORATION_OPTIONS,
])

const fontStyleValue = computed(() => {
  const parts: string[] = []
  if ((p.value['font_style'] as string) === 'italic') parts.push('italic')
  const deco = (p.value['text_decoration'] as string) || ''
  if (deco && deco !== 'none') {
    parts.push(...deco.split(' ').filter(Boolean))
  }
  return parts.length > 0 ? parts.join(' ') : 'none'
})

function setTextProp(key: string, value: unknown) {
  if (!props.node?.id) return
  templateStore.updateNodeProperty(props.node.id, key, value)
}

function onFontStyleDecoChange(value: string) {
  if (!props.node?.id) return
  const values = value === 'none' ? [] : value.split(' ').filter(Boolean)
  const isItalic = values.includes('italic')
  const decoValues = values.filter((v) => v !== 'italic')
  templateStore.updateNodeProperty(props.node.id, 'font_style', isItalic ? 'italic' : 'normal')
  templateStore.updateNodeProperty(props.node.id, 'text_decoration', decoValues.length > 0 ? decoValues.join(' ') : 'none')
}

// ─── Background Color (Story 14.6) ──────────────────────────────────────────
function onBackgroundColorChange(value: string) {
  if (!props.node?.id) return
  templateStore.updateNodeProperty(props.node.id, 'background_color', value)
}

/** Extract unique colors from all nodes for the document palette (max 12, by frequency) */
const documentColors = computed<string[]>(() => {
  const freq = new Map<string, number>()
  for (const node of templateStore.flatNodes.values()) {
    const np = node.properties as Record<string, unknown>
    for (const key of ['color', 'background_color']) {
      const v = np[key]
      if (typeof v === 'string' && v.startsWith('#') && v.length === 7) {
        freq.set(v, (freq.get(v) ?? 0) + 1)
      }
    }
  }
  return [...freq.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 12)
    .map(([color]) => color)
})

// ─── Padding (Story 14.9) ────────────────────────────────────────────────────
function paddingValue(key: string): number {
  const v = p.value[key]
  return typeof v === 'number' ? v : 0
}

function setPaddingProp(key: string, value: string | number) {
  if (!props.node?.id) return
  const num = typeof value === 'number' ? value : parseFloat(value)
  templateStore.updateNodeProperty(props.node.id, key, isNaN(num) ? 0 : Math.max(0, num))
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
  templateStore.updateNodeProperty(id, 'border_top_width', config.top.width)
  templateStore.updateNodeProperty(id, 'border_top_color', config.top.color)
  templateStore.updateNodeProperty(id, 'border_top_style', config.top.style)
  templateStore.updateNodeProperty(id, 'border_right_width', config.right.width)
  templateStore.updateNodeProperty(id, 'border_right_color', config.right.color)
  templateStore.updateNodeProperty(id, 'border_right_style', config.right.style)
  templateStore.updateNodeProperty(id, 'border_bottom_width', config.bottom.width)
  templateStore.updateNodeProperty(id, 'border_bottom_color', config.bottom.color)
  templateStore.updateNodeProperty(id, 'border_bottom_style', config.bottom.style)
  templateStore.updateNodeProperty(id, 'border_left_width', config.left.width)
  templateStore.updateNodeProperty(id, 'border_left_color', config.left.color)
  templateStore.updateNodeProperty(id, 'border_left_style', config.left.style)
  templateStore.updateNodeProperty(id, 'border_radius_top_left', config.radius.topLeft)
  templateStore.updateNodeProperty(id, 'border_radius_top_right', config.radius.topRight)
  templateStore.updateNodeProperty(id, 'border_radius_bottom_right', config.radius.bottomRight)
  templateStore.updateNodeProperty(id, 'border_radius_bottom_left', config.radius.bottomLeft)
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

// ─── Format String ──────────────────────────────────────────────────────────
const formatString = computed<string>(() => {
  const v = p.value['formatString']
  return typeof v === 'string' ? v : ''
})

function onFormatStringChange(value: string) {
  if (!props.node) return
  templateStore.updateNodeProperty(props.node.id, 'formatString', value)
}

// ─── Style Rules ────────────────────────────────────────────────────────────
const styleRules = computed<StyleRule[]>(() => {
  const v = p.value['styleRules']
  return Array.isArray(v) ? (v as StyleRule[]) : []
})

function onStyleRulesChange(rules: StyleRule[]) {
  if (!props.node) return
  templateStore.updateNodeProperty(props.node.id, 'styleRules', rules)
}

// ─── Test data for format string preview ───────────────────────────────────
const testDataRecord = computed<Record<string, string>>(() => {
  return {}
})

// ─── Font Cascade ────────────────────────────────────────────────────────────
const fontCascade = useFontCascade()
const { addFile } = useBibliotecas()

const detectedFont = computed<string>(() => {
  const ff = p.value['font_family']
  return typeof ff === 'string' && ff.trim() !== '' ? ff.trim() : ''
})

const fontFallback = computed<string>(() => {
  return fontCascade.suggestedAlternative.value ?? 'sans-serif'
})

// Trigger cascade resolution whenever the detected font changes
watch(
  detectedFont,
  async (font) => {
    if (font) {
      await fontCascade.resolveFontCascade(font)
    }
  },
  { immediate: true },
)

async function handleFontUpload(file: File) {
  await addFile(file, 'fonts')
  // Re-run cascade after upload
  if (detectedFont.value) {
    await fontCascade.resolveFontCascade(detectedFont.value)
  }
}
</script>

<style scoped>
.element-inspector {
  display: flex;
  flex-direction: column;
}

.element-inspector__padding-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.25rem 0.5rem;
}
</style>
