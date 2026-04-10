<template>
  <div class="field-nav-group">
    <!-- Group header -->
    <button class="field-nav-group__header" type="button" :aria-expanded="isOpen" @click="toggle">
      <span class="field-nav-group__badge" aria-hidden="true">{{ badge }}</span>
      <span class="field-nav-group__label">{{ label }}</span>
      <span class="field-nav-group__count">({{ count }})</span>
      <span class="field-nav-group__chevron" aria-hidden="true">
        {{ isOpen ? '▼' : '▶' }}
      </span>
    </button>

    <!-- Items slot -->
    <div v-if="isOpen" class="field-nav-group__items">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  label: string
  badge: string
  count: number
  startOpen?: boolean
}

const props = withDefaults(defineProps<Props>(), { startOpen: true })

const isOpen = ref(props.startOpen)

function toggle() {
  isOpen.value = !isOpen.value
}
</script>

<style scoped>
.field-nav-group {
  border-bottom: 1px solid var(--color-neutral-750, #2d3748);
}

.field-nav-group__header {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  width: 100%;
  padding: 0.375rem 0.75rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-neutral-200, #e5e7eb);
  text-align: left;
  transition: background-color 0.1s;
}

.field-nav-group__header:hover {
  background-color: var(--color-neutral-750, #2d3748);
}

.field-nav-group__badge {
  font-size: 0.75rem;
  flex-shrink: 0;
}

.field-nav-group__label {
  flex: 1;
}

.field-nav-group__count {
  font-size: 0.6875rem;
  font-weight: 400;
  color: var(--color-neutral-500, #6b7280);
}

.field-nav-group__chevron {
  font-size: 0.5rem;
  color: var(--color-neutral-500, #6b7280);
}

.field-nav-group__items {
  padding-bottom: 0.25rem;
}
</style>
