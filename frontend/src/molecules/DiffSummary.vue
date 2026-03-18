<template>
  <div class="diff-summary">
    <h3 class="diff-summary__title">Resumo de Inferências</h3>

    <div v-if="diffStore.inferences.length === 0" class="diff-summary__empty">
      Nenhuma inferência encontrada. Selecione dois documentos para comparar.
    </div>

    <ul v-else class="diff-summary__list" role="list">
      <li
        v-for="inference in diffStore.inferences"
        :key="inference.id"
        class="diff-summary__item"
      >
        <div class="diff-summary__item-info">
          <span
            class="diff-summary__badge"
            :class="`diff-summary__badge--${inference.type}`"
          >
            {{ badgeLabel(inference.type) }}
          </span>
          <span class="diff-summary__description">{{ inference.description }}</span>
          <span class="diff-summary__confidence">
            {{ Math.round(inference.confidence * 100) }}%
          </span>
        </div>
        <div class="diff-summary__actions">
          <button
            type="button"
            class="diff-summary__btn diff-summary__btn--confirm"
            :data-testid="`confirm-${inference.id}`"
            @click="diffStore.confirmInference(inference.id)"
          >
            Confirmar
          </button>
          <button
            type="button"
            class="diff-summary__btn diff-summary__btn--reject"
            :data-testid="`reject-${inference.id}`"
            @click="diffStore.rejectInference(inference.id)"
          >
            Rejeitar
          </button>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { useDiffStore } from '@/stores/diffStore'

const diffStore = useDiffStore()

function badgeLabel(type: string): string {
  const labels: Record<string, string> = {
    identical: '= Idêntico',
    moved: '↕ Movido',
    added: '+ Adicionado',
    removed: '− Removido',
  }
  return labels[type] ?? type
}
</script>

<style scoped>
.diff-summary {
  background: var(--color-neutral-50, #f9fafb);
  border-top: 1px solid var(--color-neutral-200, #e5e7eb);
  padding: 0.75rem 1rem;
  overflow-y: auto;
  max-height: 200px;
  flex-shrink: 0;
}

.diff-summary__title {
  margin: 0 0 0.5rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-neutral-700, #374151);
}

.diff-summary__empty {
  font-size: 0.8125rem;
  color: var(--color-neutral-400, #9ca3af);
  text-align: center;
  padding: 0.5rem 0;
}

.diff-summary__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.diff-summary__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.375rem 0.5rem;
  background: #fff;
  border: 1px solid var(--color-neutral-200, #e5e7eb);
  border-radius: 0.375rem;
}

.diff-summary__item-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  flex: 1;
}

.diff-summary__badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.6875rem;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}

.diff-summary__badge--identical {
  background: rgba(34, 197, 94, 0.15);
  color: #15803d;
}

.diff-summary__badge--moved {
  background: rgba(234, 179, 8, 0.15);
  color: #92400e;
}

.diff-summary__badge--added {
  background: rgba(239, 68, 68, 0.15);
  color: #b91c1c;
}

.diff-summary__badge--removed {
  background: rgba(239, 68, 68, 0.15);
  color: #b91c1c;
}

.diff-summary__description {
  font-size: 0.8125rem;
  color: var(--color-neutral-700, #374151);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.diff-summary__confidence {
  font-size: 0.75rem;
  color: var(--color-neutral-400, #9ca3af);
  white-space: nowrap;
  flex-shrink: 0;
}

.diff-summary__actions {
  display: flex;
  gap: 0.25rem;
  flex-shrink: 0;
}

.diff-summary__btn {
  padding: 0.1875rem 0.625rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background 0.15s;
}

.diff-summary__btn--confirm {
  background: rgba(34, 197, 94, 0.1);
  border-color: rgba(34, 197, 94, 0.4);
  color: #15803d;
}

.diff-summary__btn--confirm:hover {
  background: rgba(34, 197, 94, 0.2);
}

.diff-summary__btn--reject {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.4);
  color: #b91c1c;
}

.diff-summary__btn--reject:hover {
  background: rgba(239, 68, 68, 0.2);
}
</style>
