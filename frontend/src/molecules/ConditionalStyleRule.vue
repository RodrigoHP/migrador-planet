<template>
  <div class="csr">
    <!-- SE: [campo] [operador] [valor] -->
    <div class="csr__condition">
      <span class="csr__label-se">SE</span>
      <!-- Field selector -->
      <select
        class="csr__select"
        :value="modelValue.fieldPath"
        @change="update('fieldPath', ($event.target as HTMLSelectElement).value)"
      >
        <option value="" disabled>Campo</option>
        <option v-for="field in fieldNavItems" :key="field.path" :value="field.path">
          {{ field.path }}
        </option>
      </select>

      <!-- Operator -->
      <select
        class="csr__select csr__select--op"
        :value="modelValue.operator"
        @change="update('operator', ($event.target as HTMLSelectElement).value)"
      >
        <option value="" disabled>Op</option>
        <option v-for="op in OPERATORS" :key="op.value" :value="op.value">{{ op.label }}</option>
      </select>

      <!-- Value (hidden for notEmpty/empty operators) -->
      <input
        v-if="!isUnaryOperator"
        class="csr__input"
        type="text"
        :value="modelValue.value"
        placeholder="valor"
        @input="update('value', ($event.target as HTMLInputElement).value)"
      />
    </div>

    <!-- ENTÃO: [propriedade] = [valor] -->
    <div class="csr__consequence">
      <span class="csr__label-then">ENTÃO</span>
      <!-- Property -->
      <select
        class="csr__select"
        :value="modelValue.property"
        @change="
          update('property', ($event.target as HTMLSelectElement).value as StyleRule['property'])
        "
      >
        <option value="" disabled>Prop</option>
        <option v-for="prop in PROPERTIES" :key="prop.value" :value="prop.value">
          {{ prop.label }}
        </option>
      </select>
      <span class="csr__eq">=</span>

      <!-- Property value: color picker for color/background, dropdown for visibility, text for image -->
      <template
        v-if="
          modelValue.property === 'color' ||
          modelValue.property === 'background' ||
          modelValue.property === 'border-color'
        "
      >
        <input
          class="csr__color"
          type="color"
          :value="modelValue.propertyValue || '#000000'"
          @input="update('propertyValue', ($event.target as HTMLInputElement).value)"
        />
        <span class="csr__color-hex">{{ modelValue.propertyValue || '—' }}</span>
      </template>
      <template v-else-if="modelValue.property === 'visibility'">
        <select
          class="csr__select"
          :value="modelValue.propertyValue"
          @change="update('propertyValue', ($event.target as HTMLSelectElement).value)"
        >
          <option value="hidden">Oculto</option>
          <option value="visible">Visível</option>
        </select>
      </template>
      <template v-else-if="modelValue.property === 'font-weight'">
        <select
          class="csr__select"
          :value="modelValue.propertyValue || 'normal'"
          @change="update('propertyValue', ($event.target as HTMLSelectElement).value)"
        >
          <option value="normal">Normal</option>
          <option value="bold">Bold</option>
          <option value="lighter">Lighter</option>
          <option value="bolder">Bolder</option>
        </select>
      </template>
      <template v-else-if="modelValue.property === 'text-decoration'">
        <select
          class="csr__select"
          :value="modelValue.propertyValue || 'none'"
          @change="update('propertyValue', ($event.target as HTMLSelectElement).value)"
        >
          <option value="none">Nenhum</option>
          <option value="underline">Sublinhado</option>
          <option value="line-through">Tachado</option>
          <option value="overline">Sobre-linha</option>
        </select>
      </template>
      <template v-else-if="modelValue.property === 'opacity'">
        <input
          class="csr__input"
          type="number"
          min="0"
          max="1"
          step="0.1"
          :value="modelValue.propertyValue || '1'"
          @input="update('propertyValue', ($event.target as HTMLInputElement).value)"
        />
      </template>
      <template v-else>
        <input
          class="csr__input"
          type="text"
          :value="modelValue.propertyValue"
          placeholder="url"
          @input="update('propertyValue', ($event.target as HTMLInputElement).value)"
        />
      </template>
    </div>

    <!-- Preview strip (Story 38.2) -->
    <div v-if="showPreview" class="csr__preview" :style="previewStyle">
      <template v-if="modelValue.property === 'image'">
        <img
          class="csr__preview-img"
          :src="modelValue.propertyValue"
          alt="Pré-visualização da imagem selecionada"
          @error="($event.target as HTMLImageElement).style.display = 'none'"
        />
      </template>
      <template v-else> Abc 123 </template>
    </div>

    <!-- Remove button -->
    <button class="csr__remove" type="button" title="Remover regra" @click="emit('remove')">
      ✕
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useMappingStore } from '@/stores/mapping'
import type { StyleRule } from '@/utils/formatStringGenerator'

const props = defineProps<{
  modelValue: StyleRule
}>()

const emit = defineEmits<{
  'update:modelValue': [value: StyleRule]
  remove: []
}>()

const mappingStore = useMappingStore()
const fieldNavItems = computed(() => mappingStore.fieldNavItems)

const OPERATORS = [
  { value: '===', label: '=' },
  { value: '!==', label: '≠' },
  { value: '>', label: '>' },
  { value: '>=', label: '≥' },
  { value: '<', label: '<' },
  { value: '<=', label: '≤' },
  { value: 'contains', label: 'contém' },
  { value: 'notEmpty', label: 'não vazio' },
  { value: 'empty', label: 'vazio' },
] as const

const PROPERTIES = [
  { value: 'color', label: 'Cor do texto' },
  { value: 'background', label: 'Cor de fundo' },
  { value: 'image', label: 'Imagem' },
  { value: 'visibility', label: 'Visibilidade' },
  { value: 'border-color', label: 'Cor da borda' },
  { value: 'font-weight', label: 'Peso da fonte' },
  { value: 'text-decoration', label: 'Decoração de texto' },
  { value: 'opacity', label: 'Opacidade' },
] as const

const isUnaryOperator = computed(
  () => props.modelValue.operator === 'notEmpty' || props.modelValue.operator === 'empty',
)

// Story 38.2: Preview strip showing the visual effect of the rule
const showPreview = computed(() => {
  return !!props.modelValue.property && !!props.modelValue.propertyValue
})

const previewStyle = computed<Record<string, string>>(() => {
  const pv = props.modelValue.propertyValue
  if (!pv) return {}
  switch (props.modelValue.property) {
    case 'color':
      return { color: pv }
    case 'background':
      return { backgroundColor: pv, color: '#fff' }
    case 'visibility':
      return { opacity: pv === 'hidden' ? '0.3' : '1' }
    case 'border-color':
      return { borderColor: pv, borderWidth: '2px', borderStyle: 'solid' }
    case 'font-weight':
      return { fontWeight: pv }
    case 'text-decoration':
      return { textDecoration: pv }
    case 'opacity':
      return { opacity: pv }
    default:
      return {}
  }
})

function update<K extends keyof StyleRule>(key: K, value: StyleRule[K]) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}
</script>

<style scoped>
.csr {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  background: var(--color-neutral-850, #18212f);
  border: 1px solid var(--color-neutral-700, #374151);
  border-radius: 0.375rem;
  padding: 0.5rem 0.625rem;
  position: relative;
}

.csr__condition,
.csr__consequence {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.csr__label-se,
.csr__label-then,
.csr__eq {
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  flex-shrink: 0;
}

.csr__select {
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  color: var(--color-neutral-100, #f3f4f6);
  font-size: 0.75rem;
  padding: 0.125rem 0.25rem;
  outline: none;
  cursor: pointer;
  max-width: 8rem;
}

.csr__select--op {
  max-width: 5rem;
}

.csr__input {
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  color: var(--color-neutral-100, #f3f4f6);
  font-size: 0.75rem;
  padding: 0.125rem 0.375rem;
  outline: none;
  width: 5rem;
  min-width: 3rem;
}

.csr__color {
  width: 1.75rem;
  height: 1.25rem;
  padding: 0;
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  background: none;
  cursor: pointer;
  flex-shrink: 0;
}

.csr__color-hex {
  font-size: 0.6875rem;
  color: var(--color-neutral-300, #d1d5db);
  font-family: monospace;
}

.csr__remove {
  position: absolute;
  top: 0.375rem;
  right: 0.375rem;
  background: none;
  border: none;
  color: var(--color-neutral-500, #525252);
  cursor: pointer;
  font-size: 0.75rem;
  padding: 0.125rem 0.25rem;
  border-radius: 0.125rem;
  line-height: 1;
}

.csr__remove:hover {
  color: var(--color-error-400, #f87171);
  background: rgba(239, 68, 68, 0.1);
}

/* Story 38.2: Preview strip */
.csr__preview {
  background: var(--color-neutral-900, #111827);
  border: 1px dashed var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  color: var(--color-neutral-200, #e5e7eb);
  text-align: center;
  min-height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.csr__preview-img {
  max-height: 1.5rem;
  max-width: 4rem;
  object-fit: contain;
}
</style>
