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
  </div>
</template>

<script setup lang="ts">
import { useLayoutStore } from '@/stores/layout'

const layoutStore = useLayoutStore()

function onSelectChange(event: Event) {
  const target = event.target as HTMLSelectElement
  layoutStore.setActiveLayout(target.value)
}
</script>

<style scoped>
.layout-selector {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
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
</style>
