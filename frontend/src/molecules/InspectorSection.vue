<template>
  <div class="inspector-section">
    <button
      v-if="collapsible"
      class="inspector-section__header inspector-section__header--btn"
      type="button"
      :aria-expanded="!collapsed"
      @click="collapsed = !collapsed"
    >
      <span class="inspector-section__title">{{ title }}</span>
      <span
        class="inspector-section__chevron"
        :class="
          collapsed ? 'inspector-section__chevron--closed' : 'inspector-section__chevron--open'
        "
      >
        ▾
      </span>
    </button>
    <div v-else class="inspector-section__header">
      <span class="inspector-section__title">{{ title }}</span>
    </div>
    <div v-if="!collapsed" class="inspector-section__body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = withDefaults(
  defineProps<{
    title: string
    collapsible?: boolean
  }>(),
  { collapsible: false },
)

const collapsed = ref(false)
</script>

<style scoped>
.inspector-section {
  border-bottom: 1px solid var(--color-neutral-700, #374151);
}

.inspector-section:last-child {
  border-bottom: none;
}

.inspector-section__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
}

.inspector-section__header--btn {
  width: 100%;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
}

.inspector-section__header--btn:hover {
  background: var(--color-neutral-700, #374151);
}

.inspector-section__title {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-neutral-300, #d1d5db);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.inspector-section__chevron {
  font-size: 0.875rem;
  color: var(--color-neutral-400, #9ca3af);
  transition: transform 0.15s;
}

.inspector-section__chevron--closed {
  transform: rotate(-90deg);
}

.inspector-section__chevron--open {
  transform: rotate(0deg);
}

.inspector-section__body {
  padding: 0.25rem 0.75rem 0.625rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
</style>
