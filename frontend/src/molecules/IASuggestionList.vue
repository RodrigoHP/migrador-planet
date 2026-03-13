<template>
  <section class="suggestions">
    <h3>Sugestões IA</h3>
    <ul>
      <li
        v-for="item in suggestions"
        :key="item.id"
        class="suggestions__item"
        :class="{
          'suggestions__item--accepted': acceptedIds.has(item.id),
          'suggestions__item--rejected': rejectedIds.has(item.id),
        }"
      >
        <div>
          <strong :class="`suggestions__type suggestions__type--${item.type}`">{{ typeLabel(item.type) }}</strong>
          <p>{{ item.message }}</p>
        </div>
        <div class="suggestions__item-actions">
          <button
            v-if="item.action"
            type="button"
            class="suggestions__action"
            :disabled="acceptedIds.has(item.id) || rejectedIds.has(item.id)"
            @click="$emit('action', item)"
          >
            {{ item.action }}
          </button>
          <button
            type="button"
            class="suggestions__btn suggestions__btn--accept"
            :disabled="acceptedIds.has(item.id) || rejectedIds.has(item.id)"
            @click="accept(item)"
          >
            ✅ Aceitar
          </button>
          <button
            type="button"
            class="suggestions__btn suggestions__btn--reject"
            :disabled="acceptedIds.has(item.id) || rejectedIds.has(item.id)"
            @click="reject(item)"
          >
            ↩ Rejeitar
          </button>
        </div>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { IASuggestion } from '@/types'

defineProps<{
  suggestions: IASuggestion[]
}>()

const emit = defineEmits<{
  action: [suggestion: IASuggestion]
  'suggestion-accepted': [suggestion: IASuggestion]
  'suggestion-rejected': [suggestion: IASuggestion]
}>()

const acceptedIds = ref(new Set<string>())
const rejectedIds = ref(new Set<string>())

function typeLabel(type: IASuggestion['type']) {
  if (type === 'warning') return 'Atenção'
  if (type === 'improvement') return 'Melhoria'
  return 'Info'
}

function accept(item: IASuggestion) {
  acceptedIds.value = new Set([...acceptedIds.value, item.id])
  emit('suggestion-accepted', item)
  if (item.action) {
    emit('action', item)
  }
}

function reject(item: IASuggestion) {
  rejectedIds.value = new Set([...rejectedIds.value, item.id])
  emit('suggestion-rejected', item)
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
  transition: opacity 200ms ease;
}

.suggestions__item--accepted {
  border-color: var(--color-success-600);
  background: #f0fdf4;
}

.suggestions__item--rejected {
  opacity: 0.4;
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

.suggestions__item-actions {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.suggestions__action,
.suggestions__btn {
  border-radius: 0.4rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.8rem;
  cursor: pointer;
  transition: opacity 150ms ease;
}

.suggestions__action:disabled,
.suggestions__btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.suggestions__action {
  border: 1px solid var(--color-primary-600);
  background: transparent;
  color: var(--color-primary-600);
}

.suggestions__btn--accept {
  border: 1px solid var(--color-success-600);
  background: transparent;
  color: var(--color-success-600);
}

.suggestions__btn--reject {
  border: 1px solid var(--color-neutral-400);
  background: transparent;
  color: var(--color-neutral-600);
}
</style>
