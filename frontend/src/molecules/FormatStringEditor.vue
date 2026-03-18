<template>
  <div class="fse">
    <label class="fse__label">Format String</label>

    <!-- Editable input -->
    <div class="fse__input-wrap">
      <input
        ref="inputRef"
        class="fse__input"
        type="text"
        :value="modelValue"
        placeholder='ex: "{Logradouro}, {Numero} - {Bairro}"'
        autocomplete="off"
        @input="onInput"
        @keydown="onKeyDown"
        @blur="closeDropdown"
      />
    </div>

    <!-- Autocomplete dropdown -->
    <ul
      v-if="showDropdown && filteredFields.length"
      class="fse__dropdown"
      role="listbox"
    >
      <li
        v-for="(field, idx) in filteredFields"
        :key="field.path"
        class="fse__dropdown-item"
        :class="{ 'fse__dropdown-item--active': idx === activeIndex }"
        role="option"
        :aria-selected="idx === activeIndex"
        @mousedown.prevent="selectField(field.path)"
      >
        <span class="fse__dropdown-path">{{ field.path }}</span>
        <span class="fse__dropdown-name">{{ field.name }}</span>
      </li>
    </ul>

    <!-- Highlighted preview of the format string -->
    <div class="fse__highlight" aria-hidden="true">
      <span
        v-for="(segment, idx) in highlightedSegments"
        :key="idx"
        :class="segment.cls"
        :title="segment.tooltip"
      >{{ segment.text }}</span>
    </div>

    <!-- Live preview -->
    <div v-if="previewText !== null" class="fse__preview">
      <span class="fse__preview-label">Preview:</span>
      <span class="fse__preview-value">{{ previewText }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useMappingStore } from '@/stores/mapping'

const props = withDefaults(
  defineProps<{
    modelValue: string
    testData?: Record<string, string>
  }>(),
  {
    modelValue: '',
    testData: () => ({}),
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const mappingStore = useMappingStore()
const inputRef = ref<HTMLInputElement | null>(null)

// ─── Dropdown state ────────────────────────────────────────────────────────
const showDropdown = ref(false)
const dropdownQuery = ref('')
const activeIndex = ref(0)
/** Cursor position where `{` was typed (start of the incomplete token) */
const tokenStart = ref(-1)

const filteredFields = computed(() => {
  const q = dropdownQuery.value.toLowerCase()
  return mappingStore.fieldNavItems
    .filter((f) => !q || f.path.toLowerCase().includes(q) || f.name.toLowerCase().includes(q))
    .slice(0, 20)
})

function closeDropdown() {
  showDropdown.value = false
  tokenStart.value = -1
}

// ─── Input handling ────────────────────────────────────────────────────────
function onInput(e: Event) {
  const target = e.target as HTMLInputElement
  const value = target.value
  emit('update:modelValue', value)

  // Check if cursor is inside an open `{` token (not escaped)
  const cursor = target.selectionStart ?? value.length
  const beforeCursor = value.slice(0, cursor)

  // Find the last unescaped `{` before cursor
  const lastOpenBrace = findLastUnescapedBrace(beforeCursor)

  if (lastOpenBrace !== -1) {
    // Check there's no closing `}` between lastOpenBrace and cursor
    const afterBrace = beforeCursor.slice(lastOpenBrace + 1)
    if (!afterBrace.includes('}')) {
      tokenStart.value = lastOpenBrace
      dropdownQuery.value = afterBrace
      activeIndex.value = 0
      showDropdown.value = true
      return
    }
  }

  closeDropdown()
}

function onKeyDown(e: KeyboardEvent) {
  if (!showDropdown.value) return

  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeIndex.value = Math.min(activeIndex.value + 1, filteredFields.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIndex.value = Math.max(activeIndex.value - 1, 0)
  } else if (e.key === 'Enter' || e.key === 'Tab') {
    const field = filteredFields.value[activeIndex.value]
    if (field) {
      e.preventDefault()
      selectField(field.path)
    }
  } else if (e.key === 'Escape') {
    closeDropdown()
  }
}

function selectField(path: string) {
  const input = inputRef.value
  if (!input || tokenStart.value === -1) return

  const value = props.modelValue
  const cursor = input.selectionStart ?? value.length

  // Replace from tokenStart to cursor with {path}
  const newValue = value.slice(0, tokenStart.value) + `{${path}}` + value.slice(cursor)
  emit('update:modelValue', newValue)

  closeDropdown()
  nextTick(() => {
    if (input) {
      const newCursor = tokenStart.value + path.length + 2 // +2 for { and }
      input.setSelectionRange(newCursor, newCursor)
      input.focus()
    }
  })
}

// ─── Field parsing ─────────────────────────────────────────────────────────
/** Public getter: extract all field paths from the format string */
const parsedFields = computed<string[]>(() => {
  const fields: string[] = []
  const regex = /(?<!\\)\{([^}]+)\}/g
  let match: RegExpExecArray | null
  while ((match = regex.exec(props.modelValue)) !== null) {
    if (match[1] !== undefined) fields.push(match[1])
  }
  return fields
})

defineExpose({ parsedFields })

// ─── Highlight segments ────────────────────────────────────────────────────
interface Segment {
  text: string
  cls: string
  tooltip: string
}

const knownPaths = computed(() => new Set(mappingStore.fieldNavItems.map((f) => f.path)))

const highlightedSegments = computed<Segment[]>(() => {
  const raw = props.modelValue
  if (!raw) return []

  const segments: Segment[] = []
  let i = 0

  while (i < raw.length) {
    if (raw[i] === '\\' && i + 1 < raw.length && (raw[i + 1] === '{' || raw[i + 1] === '}')) {
      // Escaped brace literal
      segments.push({ text: raw[i + 1]!, cls: 'fse__hl-literal', tooltip: '' })
      i += 2
    } else if (raw[i] === '{') {
      const end = raw.indexOf('}', i + 1)
      if (end === -1) {
        // Unclosed — treat as literal
        segments.push({ text: raw.slice(i), cls: '', tooltip: '' })
        break
      }
      const fieldPath = raw.slice(i + 1, end)
      const isValid = knownPaths.value.has(fieldPath)
      segments.push({
        text: `{${fieldPath}}`,
        cls: isValid ? 'fse__hl-valid' : 'fse__hl-invalid',
        tooltip: isValid ? '' : 'Campo não encontrado no XSD',
      })
      i = end + 1
    } else {
      // Accumulate literal text
      let literal = ''
      while (
        i < raw.length &&
        !(raw[i] === '{') &&
        !(raw[i] === '\\' && i + 1 < raw.length && (raw[i + 1] === '{' || raw[i + 1] === '}'))
      ) {
        literal += raw[i]
        i++
      }
      if (literal) segments.push({ text: literal, cls: '', tooltip: '' })
    }
  }

  return segments
})

// ─── Preview ───────────────────────────────────────────────────────────────
const defaultTestData: Record<string, string> = {
  Logradouro: 'Rua A',
  Numero: '123',
  Bairro: 'Centro',
  Cidade: 'São Paulo',
  Estado: 'SP',
  CEP: '01001-000',
}

const previewText = computed<string | null>(() => {
  const raw = props.modelValue
  if (!raw) return null

  const data = Object.keys(props.testData).length > 0 ? props.testData : defaultTestData
  let result = ''
  let i = 0

  while (i < raw.length) {
    if (raw[i] === '\\' && i + 1 < raw.length && (raw[i + 1] === '{' || raw[i + 1] === '}')) {
      result += raw[i + 1]
      i += 2
    } else if (raw[i] === '{') {
      const end = raw.indexOf('}', i + 1)
      if (end === -1) {
        result += raw.slice(i)
        break
      }
      const fieldPath = raw.slice(i + 1, end)
      result += data[fieldPath] ?? `{${fieldPath}}`
      i = end + 1
    } else {
      result += raw[i]
      i++
    }
  }

  return result
})

// ─── Helpers ───────────────────────────────────────────────────────────────
function findLastUnescapedBrace(str: string): number {
  for (let i = str.length - 1; i >= 0; i--) {
    if (str[i] === '{') {
      // Check if escaped
      let backslashCount = 0
      let j = i - 1
      while (j >= 0 && str[j] === '\\') {
        backslashCount++
        j--
      }
      if (backslashCount % 2 === 0) return i
    }
  }
  return -1
}
</script>

<style scoped>
.fse {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.25rem 0;
  position: relative;
}

.fse__label {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  user-select: none;
}

.fse__input-wrap {
  position: relative;
}

.fse__input {
  width: 100%;
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  color: var(--color-neutral-100, #f3f4f6);
  font-size: 0.8125rem;
  padding: 0.25rem 0.5rem;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
  font-family: monospace;
}

.fse__input:focus {
  border-color: var(--color-primary-500, #6366f1);
}

/* Autocomplete dropdown */
.fse__dropdown {
  position: absolute;
  top: calc(100% + 0.125rem);
  left: 0;
  right: 0;
  z-index: 50;
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  list-style: none;
  margin: 0;
  padding: 0.25rem 0;
  max-height: 10rem;
  overflow-y: auto;
}

.fse__dropdown-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.25rem 0.5rem;
  cursor: pointer;
  gap: 0.5rem;
  font-size: 0.75rem;
}

.fse__dropdown-item:hover,
.fse__dropdown-item--active {
  background: var(--color-primary-700, #4338ca);
}

.fse__dropdown-path {
  color: var(--color-primary-300, #a5b4fc);
  font-family: monospace;
  font-size: 0.75rem;
}

.fse__dropdown-name {
  color: var(--color-neutral-400, #9ca3af);
  font-size: 0.6875rem;
  flex-shrink: 0;
}

/* Highlight preview */
.fse__highlight {
  font-size: 0.75rem;
  font-family: monospace;
  background: var(--color-neutral-900, #111827);
  border: 1px solid var(--color-neutral-700, #374151);
  border-radius: 0.25rem;
  padding: 0.25rem 0.5rem;
  min-height: 1.5rem;
  word-break: break-all;
  white-space: pre-wrap;
  line-height: 1.4;
}

.fse__hl-valid {
  color: var(--color-primary-400, #818cf8);
  background: rgba(99, 102, 241, 0.12);
  border-radius: 0.125rem;
  padding: 0 0.125rem;
}

.fse__hl-invalid {
  color: var(--color-error-400, #f87171);
  background: rgba(239, 68, 68, 0.12);
  border-radius: 0.125rem;
  padding: 0 0.125rem;
  text-decoration: underline wavy var(--color-error-500, #ef4444);
  cursor: help;
}

.fse__hl-literal {
  color: var(--color-neutral-300, #d1d5db);
  opacity: 0.75;
}

/* Live preview */
.fse__preview {
  display: flex;
  align-items: flex-start;
  gap: 0.375rem;
  font-size: 0.75rem;
  padding: 0.25rem 0;
}

.fse__preview-label {
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  font-size: 0.6875rem;
  flex-shrink: 0;
}

.fse__preview-value {
  color: var(--color-neutral-100, #f3f4f6);
  font-family: monospace;
  word-break: break-all;
}
</style>
