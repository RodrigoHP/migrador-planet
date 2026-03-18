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

      <!-- Font Warning: shown when font is not found in catalog -->
      <FontWarning
        v-if="detectedFont"
        :detected-font="detectedFont"
        :fallback-font="fontFallback"
        :status="fontCascade.fontStatus.value"
        @upload="handleFontUpload"
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
import InspectorField from '@/molecules/InspectorField.vue'
import InspectorSection from '@/molecules/InspectorSection.vue'
import VisibilityControl from '@/molecules/VisibilityControl.vue'
import type { VisibilityConfig } from '@/molecules/VisibilityControl.vue'
import FormatStringEditor from '@/molecules/FormatStringEditor.vue'
import ConditionalStyleSection from '@/molecules/ConditionalStyleSection.vue'
import FontWarning from '@/molecules/FontWarning.vue'
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
</style>
