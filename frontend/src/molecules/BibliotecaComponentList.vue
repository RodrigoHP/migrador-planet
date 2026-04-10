<template>
  <div class="bcl">
    <p v-if="items.length === 0" class="bcl__empty">Nenhum componente salvo.</p>

    <ul v-else class="bcl__list" role="list">
      <li v-for="item in items" :key="item.id" class="bcl__item">
        <!-- Preview thumbnail -->
        <!-- SEC-001: Sanitize HTML to prevent XSS -->
        <div class="bcl__preview" v-html="sanitizeHtml(item.previewHtml)" />

        <div class="bcl__info">
          <span class="bcl__name" :title="item.name">{{ item.name }}</span>
          <span class="bcl__meta"
            >{{ item.nodeCount }} nó(s) · {{ formatDate(item.createdAt) }}</span
          >
        </div>

        <div class="bcl__actions">
          <button
            type="button"
            class="bcl__btn-insert"
            :aria-label="`Inserir ${item.name}`"
            :title="`Inserir ${item.name}`"
            @click="$emit('insert', item)"
          >
            ➕
          </button>
          <button
            type="button"
            class="bcl__btn-remove"
            :aria-label="`Remover ${item.name}`"
            :title="`Remover ${item.name}`"
            @click="$emit('remove', item.id, item.name)"
          >
            🗑️
          </button>
        </div>
      </li>
    </ul>

    <p class="bcl__count">{{ items.length }} componente(s)</p>
  </div>
</template>

<script setup lang="ts">
import type { BibliotecaComponent } from '@/composables/useBibliotecas'
import { sanitizeHtml } from '@/utils/htmlSanitizer'

defineProps<{
  items: BibliotecaComponent[]
}>()

defineEmits<{
  insert: [component: BibliotecaComponent]
  remove: [id: string, name: string]
}>()

function formatDate(ts: number): string {
  return new Date(ts).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
  })
}
</script>

<style scoped>
.bcl {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.bcl__empty {
  color: var(--color-neutral-500, #525252);
  font-size: 0.875rem;
  text-align: center;
  padding: 1.5rem 0;
  margin: 0;
}

.bcl__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.bcl__item {
  display: flex;
  align-items: center;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-neutral-200, #e5e5e5);
  border-radius: 0.5rem;
  background: #fff;
  gap: 0.75rem;
}

.bcl__preview {
  flex-shrink: 0;
  width: 80px;
  height: 48px;
  overflow: hidden;
  border: 1px solid var(--color-neutral-200, #e5e5e5);
  border-radius: 0.25rem;
  background: #fafafa;
  font-size: 8px;
  padding: 2px;
}

.bcl__info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
  flex: 1;
}

.bcl__name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-neutral-800, #262626);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 280px;
}

.bcl__meta {
  font-size: 0.75rem;
  color: var(--color-neutral-500, #525252);
}

.bcl__actions {
  display: flex;
  gap: 0.25rem;
  flex-shrink: 0;
}

.bcl__btn-insert,
.bcl__btn-remove {
  flex-shrink: 0;
  padding: 0.25rem 0.375rem;
  font-size: 1rem;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 0.375rem;
  cursor: pointer;
  transition:
    background-color 150ms ease,
    border-color 150ms ease;
  line-height: 1;
}

.bcl__btn-insert:hover {
  background: #eff6ff;
  border-color: #93c5fd;
}

.bcl__btn-remove:hover {
  background: #fee2e2;
  border-color: #fca5a5;
}

.bcl__count {
  font-size: 0.75rem;
  color: var(--color-neutral-400, #a3a3a3);
  margin: 0;
}
</style>
