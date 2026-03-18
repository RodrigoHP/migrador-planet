<template>
  <div class="barcode-inspector">
    <!-- Format -->
    <InspectorSection title="Formato" :collapsible="true">
      <div class="barcode-inspector__field">
        <label class="barcode-inspector__label">Formato</label>
        <select
          class="barcode-inspector__select"
          :value="localFormat"
          @change="onFormatChange"
        >
          <option v-for="fmt in BARCODE_FORMATS" :key="fmt.value" :value="fmt.value">
            {{ fmt.label }}
          </option>
        </select>
      </div>
    </InspectorSection>

    <!-- Data Binding -->
    <InspectorSection title="Dados" :collapsible="true">
      <div class="barcode-inspector__field">
        <label class="barcode-inspector__label">Campo</label>
        <select
          class="barcode-inspector__select"
          :value="localField"
          @change="onFieldChange"
        >
          <option value="">— Selecione —</option>
          <option v-for="field in availableFields" :key="field" :value="field">
            {{ field }}
          </option>
        </select>
      </div>
    </InspectorSection>

    <!-- Options -->
    <InspectorSection title="Opções" :collapsible="true">
      <div class="barcode-inspector__field">
        <label class="barcode-inspector__label">Largura barra</label>
        <input
          class="barcode-inspector__input"
          type="number"
          :value="localLineWidth"
          min="1"
          max="5"
          step="1"
          @change="onLineWidthChange"
        />
      </div>
      <div class="barcode-inspector__field">
        <label class="barcode-inspector__label">Altura</label>
        <input
          class="barcode-inspector__input"
          type="number"
          :value="localHeight"
          min="20"
          max="300"
          step="5"
          @change="onHeightChange"
        />
      </div>
      <div class="barcode-inspector__field barcode-inspector__field--checkbox">
        <label class="barcode-inspector__label">Mostrar texto</label>
        <input
          class="barcode-inspector__checkbox"
          type="checkbox"
          :checked="localDisplayValue"
          @change="onDisplayValueChange"
        />
      </div>
    </InspectorSection>

    <!-- Preview -->
    <InspectorSection title="Preview" :collapsible="true">
      <div class="barcode-inspector__preview" aria-label="Barcode preview">
        <div class="barcode-inspector__bars">
          <div
            v-for="(bar, i) in previewBars"
            :key="i"
            class="barcode-inspector__bar"
            :style="{ width: bar.width + 'px', background: bar.dark ? '#d1d5db' : 'transparent' }"
          />
        </div>
        <div v-if="localDisplayValue" class="barcode-inspector__preview-text">
          {{ previewValue }}
        </div>
      </div>
    </InspectorSection>

    <!-- Generated code -->
    <InspectorSection title="Código gerado" :collapsible="true">
      <div class="barcode-inspector__code">
        <pre class="barcode-inspector__pre">{{ generatedHtml }}</pre>
      </div>
    </InspectorSection>
  </div>
</template>

<script lang="ts">
// ─── Constants exported for use in spec files ────────────────────────────────
export const BARCODE_FORMATS = [
  { value: 'CODE128', label: 'CODE128' },
  { value: 'CODE39', label: 'CODE39' },
  { value: 'EAN13', label: 'EAN-13' },
  { value: 'EAN8', label: 'EAN-8' },
  { value: 'UPC', label: 'UPC-A' },
  { value: 'ITF', label: 'ITF' },
  { value: 'MSI', label: 'MSI' },
] as const

export type BarcodeFormat = (typeof BARCODE_FORMATS)[number]['value']
</script>

<script setup lang="ts">
import { computed } from 'vue'
import type { TreeNode } from '@/types/template.types'
import InspectorSection from '@/molecules/InspectorSection.vue'
import { useTemplateStore } from '@/stores/templateStore'

// ─── Props ────────────────────────────────────────────────────────────────────

const props = withDefaults(defineProps<{ node?: TreeNode | null }>(), { node: null })

// ─── Stores ───────────────────────────────────────────────────────────────────

const templateStore = useTemplateStore()

// ─── Helpers ──────────────────────────────────────────────────────────────────

const p = computed(() => (props.node?.properties ?? {}) as Record<string, unknown>)

function getProp<T>(key: string, fallback: T): T {
  const v = p.value[key]
  return v !== undefined && v !== null ? (v as T) : fallback
}

// ─── Local state (derived from node properties) ───────────────────────────────

const localFormat = computed<string>(() => getProp('barcodeFormat', 'CODE128'))
const localField = computed<string>(() => getProp('barcodeField', ''))
const localLineWidth = computed<number>(() => getProp('barcodeLineWidth', 2))
const localHeight = computed<number>(() => getProp('barcodeHeight', 60))
const localDisplayValue = computed<boolean>(() => getProp('barcodeDisplayValue', true))

// ─── Available fields from template store ─────────────────────────────────────

const availableFields = computed<string[]>(() => {
  const fields: string[] = []
  for (const node of templateStore.flatNodes.values()) {
    if (node.binding && !fields.includes(node.binding)) {
      fields.push(node.binding)
    }
  }
  return fields.sort()
})

// ─── Handlers ─────────────────────────────────────────────────────────────────

function updateProp(key: string, value: unknown) {
  if (props.node?.id) {
    templateStore.updateNodeProperty(props.node.id, key, value)
  }
}

function onFormatChange(event: Event) {
  updateProp('barcodeFormat', (event.target as HTMLSelectElement).value)
}

function onFieldChange(event: Event) {
  updateProp('barcodeField', (event.target as HTMLSelectElement).value)
}

function onLineWidthChange(event: Event) {
  updateProp('barcodeLineWidth', Number((event.target as HTMLInputElement).value))
}

function onHeightChange(event: Event) {
  updateProp('barcodeHeight', Number((event.target as HTMLInputElement).value))
}

function onDisplayValueChange(event: Event) {
  updateProp('barcodeDisplayValue', (event.target as HTMLInputElement).checked)
}

// ─── Preview ──────────────────────────────────────────────────────────────────

const previewValue = computed(() => localField.value || '123456789')

/** Generate a simple visual barcode pattern (CSS lines, not real barcode) */
const previewBars = computed(() => {
  const seed = previewValue.value
  const bars: { width: number; dark: boolean }[] = []
  // Simple deterministic pseudo-barcode from string hash
  for (let i = 0; i < 40; i++) {
    const charCode = seed.charCodeAt(i % seed.length) ?? 0
    bars.push({
      width: ((charCode + i) % 3) + 1,
      dark: (charCode + i) % 3 !== 0,
    })
  }
  return bars
})

// ─── Generated code ───────────────────────────────────────────────────────────

const barcodeId = computed(() => props.node?.id ?? 'barcode-1')

const generatedHtml = computed(() => {
  const field = localField.value || 'fieldName'
  const format = localFormat.value
  const lineWidth = localLineWidth.value
  const height = localHeight.value
  const displayValue = localDisplayValue.value

  const htmlTag = `<svg id="${barcodeId.value}"></svg>`
  const jsInit =
    `JsBarcode("#${barcodeId.value}", ko.unwrap(data.${field}), ` +
    `{ format: "${format}", lineColor: "#000", width: ${lineWidth}, height: ${height}, displayValue: ${displayValue} })`

  return `<!-- HTML -->\n${htmlTag}\n\n<!-- base.js -->\n${jsInit}`
})
</script>

<style scoped>
.barcode-inspector {
  display: flex;
  flex-direction: column;
}

.barcode-inspector__field {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.1875rem 0;
}

.barcode-inspector__field--checkbox {
  justify-content: space-between;
}

.barcode-inspector__label {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  min-width: 5rem;
  flex-shrink: 0;
}

.barcode-inspector__select,
.barcode-inspector__input {
  flex: 1;
  font-size: 0.6875rem;
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-100, #f3f4f6);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  padding: 0.1875rem 0.375rem;
  min-width: 0;
}

.barcode-inspector__select:focus,
.barcode-inspector__input:focus {
  outline: 1px solid var(--color-blue-500, #3b82f6);
}

.barcode-inspector__checkbox {
  width: 1rem;
  height: 1rem;
  cursor: pointer;
}

/* ─── Preview ──────────────────────────────────── */
.barcode-inspector__preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem;
  background: var(--color-neutral-900, #111827);
  border-radius: 0.25rem;
  min-height: 3.5rem;
}

.barcode-inspector__bars {
  display: flex;
  align-items: stretch;
  height: 2rem;
  gap: 0;
}

.barcode-inspector__bar {
  height: 100%;
  min-width: 1px;
}

.barcode-inspector__preview-text {
  font-size: 0.625rem;
  font-family: monospace;
  color: var(--color-neutral-400, #9ca3af);
}

/* ─── Code ─────────────────────────────────────── */
.barcode-inspector__code {
  overflow: auto;
  max-height: 8rem;
}

.barcode-inspector__pre {
  font-size: 0.625rem;
  font-family: monospace;
  color: var(--color-neutral-300, #d1d5db);
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
</style>
