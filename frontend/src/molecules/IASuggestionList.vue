<template>
  <section class="suggestions">
    <h3>Sugestões IA</h3>
    <ul>
      <li v-for="item in suggestions" :key="item.id" class="suggestions__item">
        <div>
          <strong :class="`suggestions__type suggestions__type--${item.type}`">{{ typeLabel(item.type) }}</strong>
          <p>{{ item.message }}</p>
        </div>
        <button
          v-if="item.action"
          type="button"
          class="suggestions__action"
          @click="$emit('action', item)"
        >
          {{ item.action }}
        </button>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import type { IASuggestion } from '@/types'

defineProps<{
  suggestions: IASuggestion[]
}>()

defineEmits<{
  action: [suggestion: IASuggestion]
}>()

function typeLabel(type: IASuggestion['type']) {
  if (type === 'warning') return 'Atenção'
  if (type === 'improvement') return 'Melhoria'
  return 'Info'
}
</script>

<style scoped>
.suggestions {
  display: grid;
  gap: 0.6rem;
}

.suggestions h3 {
  margin: 0;
  font-size: 0.95rem;
}

.suggestions ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.55rem;
}

.suggestions__item {
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.6rem;
  padding: 0.6rem;
  display: grid;
  gap: 0.45rem;
}

.suggestions__item p {
  margin: 0.2rem 0 0;
  color: var(--color-neutral-700);
  font-size: 0.85rem;
}

.suggestions__type {
  font-size: 0.75rem;
}

.suggestions__type--warning {
  color: var(--color-warning-500);
}

.suggestions__type--improvement {
  color: var(--color-success-600);
}

.suggestions__type--info {
  color: var(--color-primary-600);
}

.suggestions__action {
  justify-self: end;
  border: 1px solid var(--color-primary-600);
  background: transparent;
  color: var(--color-primary-600);
  border-radius: 0.4rem;
  padding: 0.25rem 0.5rem;
  cursor: pointer;
}
</style>
