<template>
  <div class="visibility-control">
    <!-- Dropdown principal de visibilidade -->
    <div class="visibility-control__main">
      <label class="visibility-control__label">Visibilidade</label>
      <select class="visibility-control__select" :value="mode" @change="onModeChange">
        <option value="always">Sempre visível</option>
        <option value="conditional">Condicional</option>
        <option value="hidden">Escondido</option>
      </select>
    </div>

    <!-- Construtor de condições (apenas quando "Condicional") -->
    <div v-if="mode === 'conditional'" class="visibility-control__builder">
      <!-- Lista de condições -->
      <div v-for="(cond, idx) in conditions" :key="idx" class="visibility-control__condition-row">
        <!-- Indicador E/OU (exceto a primeira condição) -->
        <span
          v-if="idx > 0"
          class="visibility-control__logic-badge"
          :class="
            cond.logic === 'OR'
              ? 'visibility-control__logic-badge--or'
              : 'visibility-control__logic-badge--and'
          "
        >
          {{ cond.logic === 'OR' ? 'OU' : 'E' }}
        </span>

        <!-- Campo dropdown -->
        <select
          class="visibility-control__field-select"
          :value="cond.fieldPath"
          @change="(e) => updateCondition(idx, 'fieldPath', (e.target as HTMLSelectElement).value)"
        >
          <option value="" disabled>Selecionar campo…</option>
          <option v-for="field in fieldOptions" :key="field.value" :value="field.value">
            {{ field.label }}
          </option>
        </select>

        <!-- Operador dropdown -->
        <select
          class="visibility-control__op-select"
          :value="cond.operator"
          @change="(e) => updateCondition(idx, 'operator', (e.target as HTMLSelectElement).value)"
        >
          <option value="exists">existe</option>
          <option value="not_exists">não existe</option>
          <option value="equals">igual a</option>
          <option value="not_equals">diferente de</option>
          <option value="gt">maior que</option>
          <option value="lt">menor que</option>
          <option value="contains">contém</option>
        </select>

        <!-- Input de valor (oculto quando operador é exists/not_exists) -->
        <input
          v-if="cond.operator !== 'exists' && cond.operator !== 'not_exists'"
          class="visibility-control__value-input"
          type="text"
          placeholder="valor…"
          :value="cond.value"
          @input="(e) => updateCondition(idx, 'value', (e.target as HTMLInputElement).value)"
        />
        <span v-else class="visibility-control__value-placeholder" />

        <!-- Botão remover -->
        <button
          class="visibility-control__remove-btn"
          type="button"
          title="Remover condição"
          @click="removeCondition(idx)"
        >
          ×
        </button>
      </div>

      <!-- Botões adicionar E/OU -->
      <div class="visibility-control__add-btns">
        <button class="visibility-control__add-btn" type="button" @click="addCondition('AND')">
          + E
        </button>
        <button
          class="visibility-control__add-btn visibility-control__add-btn--or"
          type="button"
          @click="addCondition('OR')"
        >
          + OU
        </button>
      </div>

      <!-- Preview Knockout -->
      <div v-if="knockoutPreview" class="visibility-control__preview">
        <span class="visibility-control__preview-label">Preview KO:</span>
        <code class="visibility-control__preview-code">{{ knockoutPreview }}</code>
      </div>
    </div>

    <!-- Mensagem informativa para "Escondido" -->
    <div v-if="mode === 'hidden'" class="visibility-control__hidden-info">
      Elemento removido do HTML gerado.
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useMappingStore } from '@/stores/mapping'
import { useMultiDocStore } from '@/stores/multiDocStore'

// ─── Types ────────────────────────────────────────────────────────────────────

export type ConditionOperator =
  | 'exists'
  | 'not_exists'
  | 'equals'
  | 'not_equals'
  | 'gt'
  | 'lt'
  | 'contains'

export interface Condition {
  fieldPath: string
  operator: ConditionOperator
  value: string
  logic?: 'AND' | 'OR'
}

export interface VisibilityConfig {
  mode: 'always' | 'conditional' | 'hidden'
  conditions?: Condition[]
}

// ─── Props & Emits ───────────────────────────────────────────────────────────

const props = withDefaults(
  defineProps<{
    modelValue?: VisibilityConfig | null
    nodeLabel?: string
  }>(),
  { modelValue: null, nodeLabel: '' },
)

const emit = defineEmits<{
  'update:modelValue': [value: VisibilityConfig]
}>()

// ─── Computed state ───────────────────────────────────────────────────────────

const mode = computed<'always' | 'conditional' | 'hidden'>(() => {
  return props.modelValue?.mode ?? 'always'
})

const conditions = computed<Condition[]>(() => {
  return props.modelValue?.conditions ?? []
})

// ─── Sync visibility ↔ multiDocStore (Story 14.13) ───────────────────────
watch(mode, (newMode, oldMode) => {
  if (!props.nodeLabel) return
  const multiDocStore = useMultiDocStore()
  if (newMode === 'conditional' && oldMode !== 'conditional') {
    multiDocStore.addDetection({
      id: `vis-${props.nodeLabel}-${Date.now()}`,
      pdfId: '',
      type: 'optional_section',
      description: `Seção "${props.nodeLabel}" marcada como condicional pelo operador`,
      confidence: 1.0,
    })
  }
  if (newMode === 'always' && oldMode === 'conditional') {
    multiDocStore.removeDetectionByLabel(props.nodeLabel)
  }
})

// ─── Field options from mappingStore ────────────────────────────────────────

const mappingStore = useMappingStore()

const fieldOptions = computed(() =>
  mappingStore.fieldNavItems.map((f) => ({ label: f.name, value: f.path })),
)

// ─── Knockout preview generator ──────────────────────────────────────────────

function buildFieldExpr(cond: Condition): string {
  const field = cond.fieldPath || 'campo'
  const val = cond.value
  switch (cond.operator) {
    case 'exists':
      return field
    case 'not_exists':
      return `!${field}`
    case 'equals':
      return `${field}() === '${val}'`
    case 'not_equals':
      return `${field}() !== '${val}'`
    case 'gt':
      return `${field}() > ${val}`
    case 'lt':
      return `${field}() < ${val}`
    case 'contains':
      return `${field}().includes('${val}')`
    default:
      return field
  }
}

const knockoutPreview = computed<string>(() => {
  const conds = conditions.value
  if (conds.length === 0) return ''
  let expr = buildFieldExpr(conds[0]!)
  for (let i = 1; i < conds.length; i++) {
    const cond = conds[i]!
    const logicOp = cond.logic === 'OR' ? ' || ' : ' && '
    expr += logicOp + buildFieldExpr(cond)
  }
  return `<!-- ko if: ${expr} -->`
})

// ─── Actions ─────────────────────────────────────────────────────────────────

function onModeChange(e: Event) {
  const newMode = (e.target as HTMLSelectElement).value as 'always' | 'conditional' | 'hidden'
  const current = props.modelValue ?? { mode: 'always' }
  if (newMode === 'conditional' && (!current.conditions || current.conditions.length === 0)) {
    // Auto-add first empty condition
    emit('update:modelValue', {
      mode: newMode,
      conditions: [{ fieldPath: '', operator: 'exists', value: '' }],
    })
  } else {
    emit('update:modelValue', { ...current, mode: newMode })
  }
}

function updateCondition(idx: number, key: keyof Condition, value: string) {
  const conds = [...conditions.value]
  const cond = {
    ...(conds[idx] ?? { fieldPath: '', operator: 'exists' as ConditionOperator, value: '' }),
  }
  ;(cond as Record<string, unknown>)[key] = value
  conds[idx] = cond
  emit('update:modelValue', { mode: 'conditional', conditions: conds })
}

function removeCondition(idx: number) {
  const conds = conditions.value.filter((_, i) => i !== idx)
  // If first remaining has logic, clear it
  if (conds.length > 0 && conds[0]) {
    conds[0] = { ...conds[0], logic: undefined }
  }
  emit('update:modelValue', { mode: 'conditional', conditions: conds })
}

function addCondition(logic: 'AND' | 'OR') {
  const conds = [...conditions.value]
  conds.push({ fieldPath: '', operator: 'exists', value: '', logic })
  emit('update:modelValue', { mode: 'conditional', conditions: conds })
}
</script>

<style scoped>
.visibility-control {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding: 0.25rem 0;
}

.visibility-control__main {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.visibility-control__label {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  user-select: none;
}

.visibility-control__select {
  width: 100%;
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  color: var(--color-neutral-100, #f3f4f6);
  font-size: 0.8125rem;
  padding: 0.25rem 0.5rem;
  outline: none;
  cursor: pointer;
  transition: border-color 0.15s;
}

.visibility-control__select:focus {
  border-color: var(--color-primary-500, #6366f1);
}

/* Builder */
.visibility-control__builder {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  background: var(--color-neutral-900, #111827);
  border: 1px solid var(--color-neutral-700, #374151);
  border-radius: 0.25rem;
  padding: 0.5rem;
}

.visibility-control__condition-row {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.visibility-control__logic-badge {
  font-size: 0.625rem;
  font-weight: 700;
  padding: 0.0625rem 0.3125rem;
  border-radius: 0.1875rem;
  user-select: none;
  white-space: nowrap;
}

.visibility-control__logic-badge--and {
  background: var(--color-primary-800, #3730a3);
  color: var(--color-primary-200, #c7d2fe);
}

.visibility-control__logic-badge--or {
  background: var(--color-warning-800, #92400e);
  color: var(--color-warning-200, #fde68a);
}

.visibility-control__field-select,
.visibility-control__op-select {
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  color: var(--color-neutral-100, #f3f4f6);
  font-size: 0.75rem;
  padding: 0.1875rem 0.375rem;
  outline: none;
  cursor: pointer;
  flex: 1;
  min-width: 0;
}

.visibility-control__field-select:focus,
.visibility-control__op-select:focus {
  border-color: var(--color-primary-500, #6366f1);
}

.visibility-control__value-input {
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  color: var(--color-neutral-100, #f3f4f6);
  font-size: 0.75rem;
  padding: 0.1875rem 0.375rem;
  outline: none;
  width: 5rem;
  min-width: 0;
  flex-shrink: 0;
}

.visibility-control__value-input:focus {
  border-color: var(--color-primary-500, #6366f1);
}

.visibility-control__value-placeholder {
  width: 5rem;
  flex-shrink: 0;
}

.visibility-control__remove-btn {
  background: transparent;
  border: none;
  color: var(--color-error-400, #f87171);
  font-size: 1rem;
  line-height: 1;
  padding: 0 0.1875rem;
  cursor: pointer;
  flex-shrink: 0;
}

.visibility-control__remove-btn:hover {
  color: var(--color-error-300, #fca5a5);
}

/* Add buttons */
.visibility-control__add-btns {
  display: flex;
  gap: 0.375rem;
}

.visibility-control__add-btn {
  font-size: 0.6875rem;
  padding: 0.1875rem 0.5rem;
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-200, #e5e7eb);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}

.visibility-control__add-btn:hover {
  background: var(--color-neutral-600, #4b5563);
}

.visibility-control__add-btn--or {
  background: var(--color-warning-900, #78350f);
  border-color: var(--color-warning-700, #b45309);
  color: var(--color-warning-200, #fde68a);
}

.visibility-control__add-btn--or:hover {
  background: var(--color-warning-800, #92400e);
}

/* Preview */
.visibility-control__preview {
  display: flex;
  flex-direction: column;
  gap: 0.1875rem;
  margin-top: 0.25rem;
}

.visibility-control__preview-label {
  font-size: 0.625rem;
  color: var(--color-neutral-500, #525252);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.visibility-control__preview-code {
  font-family: 'Fira Mono', 'Consolas', monospace;
  font-size: 0.6875rem;
  color: var(--color-primary-300, #a5b4fc);
  background: var(--color-neutral-950, #030712);
  border: 1px solid var(--color-neutral-700, #374151);
  border-radius: 0.25rem;
  padding: 0.25rem 0.5rem;
  word-break: break-all;
  white-space: pre-wrap;
}

/* Hidden info */
.visibility-control__hidden-info {
  font-size: 0.6875rem;
  color: var(--color-neutral-500, #525252);
  font-style: italic;
  padding: 0.25rem 0;
}
</style>
