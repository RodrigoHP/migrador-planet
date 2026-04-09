<template>
  <div v-show="layoutStore.layoutTypes.length > 1" class="layout-selector">
    <label class="layout-selector__label" for="layout-type-select">Layout</label>
    <select
      id="layout-type-select"
      class="layout-selector__select"
      :value="layoutStore.activeLayoutId ?? ''"
      @change="onSelectChange"
    >
      <option
        v-for="lt in layoutStore.layoutTypes"
        :key="lt.id"
        :value="lt.id"
      >
        {{ lt.name }} ({{ lt.pageCount }} pgs em {{ lt.docCount }} docs)
      </option>
    </select>
    <button
      class="layout-selector__rename-btn"
      title="Renomear layout"
      type="button"
      @click="startRename"
    >
      ✏️
    </button>
    <div v-if="isRenaming" class="layout-selector__rename-overlay">
      <input
        ref="renameInputRef"
        v-model="renameDraft"
        class="layout-selector__rename-input"
        @keydown.enter="confirmRename"
        @keydown.escape="cancelRename"
        @blur="confirmRename"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useLayoutStore } from '@/stores/layout'

const layoutStore = useLayoutStore()

const isRenaming = ref(false)
const renameDraft = ref('')
const renameInputRef = ref<HTMLInputElement | null>(null)

function onSelectChange(event: Event) {
  const target = event.target as HTMLSelectElement
  layoutStore.setActiveLayout(target.value)
}

function startRename() {
  const active = layoutStore.activeLayout
  if (!active) return
  renameDraft.value = active.name
  isRenaming.value = true
  nextTick(() => {
    renameInputRef.value?.focus()
    renameInputRef.value?.select()
  })
}

function confirmRename() {
  if (!isRenaming.value) return
  const activeId = layoutStore.activeLayoutId
  if (activeId && renameDraft.value.trim()) {
    layoutStore.renameLayout(activeId, renameDraft.value)
  }
  isRenaming.value = false
}

function cancelRename() {
  isRenaming.value = false
}
</script>

<style scoped>
.layout-selector {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  position: relative;
}

.layout-selector__label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-neutral-400, #9ca3af);
  white-space: nowrap;
}

.layout-selector__select {
  padding: 0.25rem 1.5rem 0.25rem 0.5rem;
  background: var(--color-neutral-700, #374151);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.375rem;
  color: var(--color-neutral-100, #f3f4f6);
  font-size: 0.8125rem;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' fill='none'%3E%3Cpath d='M0 0l5 6 5-6H0z' fill='%239ca3af'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.5rem center;
}

.layout-selector__select:focus {
  outline: 2px solid var(--color-primary-500, #3b82f6);
  outline-offset: 1px;
}

.layout-selector__rename-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.75rem;
  padding: 0.125rem;
  opacity: 0.6;
  transition: opacity 0.15s;
}

.layout-selector__rename-btn:hover {
  opacity: 1;
}

.layout-selector__rename-overlay {
  position: absolute;
  top: 0;
  left: 3rem;
  z-index: 10;
}

.layout-selector__rename-input {
  padding: 0.25rem 0.5rem;
  background: var(--color-neutral-800, #1f2937);
  border: 2px solid var(--color-primary-500, #3b82f6);
  border-radius: 0.375rem;
  color: var(--color-neutral-100, #f3f4f6);
  font-size: 0.8125rem;
  width: 12rem;
}
</style>
