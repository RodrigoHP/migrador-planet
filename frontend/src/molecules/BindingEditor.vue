<template>
  <!-- Estado: XSD não disponível -->
  <div
    v-if="!hasPaths"
    class="binding-editor binding-editor--disabled"
    role="combobox"
    aria-expanded="false"
    aria-label="Binding XSD"
    :title="'XSD não disponível — carregue um XSD para ativar'"
  >
    <span class="binding-editor__badge binding-editor__badge--none">⚪</span>
    <span class="binding-editor__value">XSD não disponível</span>
  </div>

  <!-- Estado: sem binding ou com binding -->
  <div v-else class="binding-editor" :class="boundClass">
    <div
      class="binding-editor__trigger"
      role="combobox"
      :aria-expanded="isOpen"
      aria-autocomplete="list"
      aria-label="Binding XSD"
      @click="openDropdown"
      @keydown.enter.prevent="openDropdown"
      @keydown.space.prevent="openDropdown"
      tabindex="0"
    >
      <span class="binding-editor__badge" :class="badgeClass">{{ badgeChar }}</span>
      <span class="binding-editor__value">{{ displayValue }}</span>
      <span class="binding-editor__chevron">▾</span>
    </div>
    <button
      v-if="modelValue"
      class="binding-editor__remove"
      title="Remover binding"
      @click.stop="removeBinding"
      @keydown.enter.prevent="removeBinding"
    >✕</button>
  </div>

  <!-- Dropdown via Teleport -->
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="binding-dropdown"
      :style="dropdownStyle"
      @keydown.escape="closeDropdown"
      @keydown.up.prevent="navigateList(-1)"
      @keydown.down.prevent="navigateList(1)"
      @keydown.enter.prevent="selectHighlighted"
    >
      <div class="binding-dropdown__search">
        <span class="binding-dropdown__search-icon">🔍</span>
        <input
          ref="searchInput"
          v-model="search"
          class="binding-dropdown__input"
          placeholder="Buscar XSD path..."
          aria-autocomplete="list"
          aria-label="Buscar campo XSD"
          @input="onSearchInput"
        />
      </div>
      <ul class="binding-dropdown__list" role="listbox">
        <li
          v-if="filteredPaths.length === 0"
          class="binding-dropdown__empty"
          role="option"
          aria-selected="false"
        >
          Nenhum resultado
        </li>
        <li
          v-for="(path, idx) in filteredPaths"
          :key="path"
          class="binding-dropdown__item"
          :class="{
            'binding-dropdown__item--selected': path === modelValue,
            'binding-dropdown__item--highlighted': idx === highlightedIndex,
          }"
          role="option"
          :aria-selected="path === modelValue"
          @click="selectPath(path)"
          @mouseenter="highlightedIndex = idx"
        >
          {{ path }}
        </li>
      </ul>
    </div>
    <!-- Overlay to close on outside click -->
    <div v-if="isOpen" class="binding-dropdown__backdrop" @click="closeDropdown" />
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'

interface Props {
  modelValue: string | null
  flatPaths: string[] | null
  status?: 'mapped' | 'unmapped' | 'unconfirmed'
}

interface Emits {
  'update:modelValue': [path: string | null]
}

const props = withDefaults(defineProps<Props>(), {
  status: 'unmapped',
  flatPaths: null,
})

const emit = defineEmits<Emits>()

const isOpen = ref(false)
const search = ref('')
const highlightedIndex = ref(0)
const searchInput = ref<HTMLInputElement | null>(null)
const triggerEl = ref<HTMLElement | null>(null)
const dropdownStyle = ref<Record<string, string>>({})

const hasPaths = computed(() => Array.isArray(props.flatPaths) && props.flatPaths.length > 0)

const filteredPaths = computed(() => {
  const paths = props.flatPaths ?? []
  if (!search.value) return paths
  const q = search.value.toLowerCase()
  return paths.filter((p) => p.toLowerCase().includes(q))
})

const displayValue = computed(() => {
  if (!props.modelValue) return 'Sem vínculo XSD'
  const max = 22
  return props.modelValue.length > max ? props.modelValue.slice(0, max) + '…' : props.modelValue
})

const badgeChar = computed(() => {
  if (!props.modelValue) return '🟥'
  if (props.status === 'mapped') return '🟩'
  if (props.status === 'unconfirmed') return '🟨'
  return '🟥'
})

const badgeClass = computed(() => {
  if (!props.modelValue) return 'binding-editor__badge--unmapped'
  if (props.status === 'mapped') return 'binding-editor__badge--mapped'
  if (props.status === 'unconfirmed') return 'binding-editor__badge--unconfirmed'
  return 'binding-editor__badge--unmapped'
})

const boundClass = computed(() => {
  if (!props.modelValue) return 'binding-editor--empty'
  return 'binding-editor--bound'
})

function openDropdown() {
  isOpen.value = true
  search.value = ''
  highlightedIndex.value = 0
  nextTick(() => {
    searchInput.value?.focus()
    positionDropdown()
  })
}

function positionDropdown() {
  // Position below the trigger element; fallback to fixed center
  const trigger = document.querySelector('.binding-editor__trigger')
  if (trigger) {
    const rect = trigger.getBoundingClientRect()
    dropdownStyle.value = {
      position: 'fixed',
      top: `${rect.bottom + 4}px`,
      left: `${rect.left}px`,
      width: `${Math.max(rect.width, 240)}px`,
      zIndex: '9999',
    }
  } else {
    dropdownStyle.value = {
      position: 'fixed',
      top: '50%',
      left: '50%',
      transform: 'translate(-50%, -50%)',
      width: '280px',
      zIndex: '9999',
    }
  }
}

function closeDropdown() {
  isOpen.value = false
  search.value = ''
}

function selectPath(path: string) {
  emit('update:modelValue', path)
  closeDropdown()
}

function removeBinding() {
  emit('update:modelValue', null)
}

function onSearchInput() {
  highlightedIndex.value = 0
}

function navigateList(dir: 1 | -1) {
  const len = filteredPaths.value.length
  if (len === 0) return
  highlightedIndex.value = (highlightedIndex.value + dir + len) % len
}

function selectHighlighted() {
  const path = filteredPaths.value[highlightedIndex.value]
  if (path) selectPath(path)
}

defineExpose({ search, filteredPaths, selectPath })
</script>

<style scoped>
.binding-editor {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 28px;
}

.binding-editor--disabled {
  opacity: 0.5;
  cursor: not-allowed;
  padding: 4px 8px;
  border-radius: 4px;
  background: var(--color-neutral-800, #1f2937);
  font-size: 0.75rem;
  color: var(--color-neutral-400, #9ca3af);
}

.binding-editor__trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  padding: 4px 8px;
  border-radius: 4px;
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  cursor: pointer;
  font-size: 0.75rem;
  color: var(--color-neutral-100, #f3f4f6);
  transition: border-color 0.15s;
  overflow: hidden;
}

.binding-editor__trigger:hover,
.binding-editor__trigger:focus {
  border-color: var(--color-primary-400, #60a5fa);
  outline: none;
}

.binding-editor__badge {
  font-size: 10px;
  flex-shrink: 0;
}

.binding-editor__value {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.binding-editor--empty .binding-editor__value {
  color: var(--color-neutral-400, #9ca3af);
  font-style: italic;
}

.binding-editor__chevron {
  font-size: 10px;
  color: var(--color-neutral-400, #9ca3af);
  flex-shrink: 0;
}

.binding-editor__remove {
  background: none;
  border: none;
  color: var(--color-red-500, #ef4444);
  cursor: pointer;
  font-size: 12px;
  padding: 2px 4px;
  border-radius: 3px;
  line-height: 1;
  transition: background 0.15s;
  flex-shrink: 0;
}

.binding-editor__remove:hover {
  background: rgba(239, 68, 68, 0.15);
}

/* Dropdown */
.binding-dropdown {
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 6px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  overflow: hidden;
  max-height: 280px;
  display: flex;
  flex-direction: column;
}

.binding-dropdown__search {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--color-neutral-600, #4b5563);
}

.binding-dropdown__search-icon {
  font-size: 12px;
  flex-shrink: 0;
}

.binding-dropdown__input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  font-size: 0.75rem;
  color: var(--color-neutral-100, #f3f4f6);
  caret-color: var(--color-primary-400, #60a5fa);
}

.binding-dropdown__input::placeholder {
  color: var(--color-neutral-400, #9ca3af);
}

.binding-dropdown__list {
  list-style: none;
  margin: 0;
  padding: 4px 0;
  overflow-y: auto;
  flex: 1;
}

.binding-dropdown__item {
  padding: 6px 12px;
  font-size: 0.75rem;
  color: var(--color-neutral-300, #d1d5db);
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: background 0.1s;
}

.binding-dropdown__item:hover,
.binding-dropdown__item--highlighted {
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-100, #f3f4f6);
}

.binding-dropdown__item--selected {
  color: var(--color-primary-200, #bfdbfe);
  background: var(--color-primary-900, #1e3a5f);
}

.binding-dropdown__empty {
  padding: 10px 12px;
  font-size: 0.75rem;
  color: var(--color-neutral-400, #9ca3af);
  font-style: italic;
}

.binding-dropdown__backdrop {
  position: fixed;
  inset: 0;
  z-index: 9998;
}
</style>
