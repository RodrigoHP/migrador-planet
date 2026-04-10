<template>
  <div class="bfl">
    <p v-if="items.length === 0" class="bfl__empty">Nenhum arquivo nesta categoria.</p>

    <ul v-else class="bfl__list" role="list">
      <li
        v-for="item in items"
        :key="item.id"
        class="bfl__item"
        :class="{ 'bfl__item--system': item.system }"
      >
        <div class="bfl__item-info">
          <span class="bfl__item-name" :title="item.name">{{ item.name }}</span>
          <span v-if="item.system" class="bfl__badge-system">Sistema</span>
          <span v-else class="bfl__item-size">{{ formatFileSize(item.size) }}</span>
        </div>

        <button
          v-if="!item.system"
          type="button"
          class="bfl__btn-remove"
          :aria-label="`Remover ${item.name}`"
          :title="`Remover ${item.name}`"
          @click="$emit('remove', item.id, item.name)"
        >
          🗑️
        </button>
      </li>
    </ul>

    <p class="bfl__count">
      {{ countLabel }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BibliotecaFile } from '@/composables/useBibliotecas'
import { formatFileSize } from '@/composables/useBibliotecas'

const props = defineProps<{
  items: BibliotecaFile[]
}>()

defineEmits<{
  remove: [id: string, name: string]
}>()

const countLabel = computed(() => {
  const total = props.items.length
  const system = props.items.filter((i) => i.system).length
  const user = total - system
  if (system > 0) return `${total} arquivo(s) — ${system} do sistema, ${user} adicionado(s)`
  return `${total} arquivo(s)`
})
</script>

<style scoped>
.bfl {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.bfl__empty {
  color: var(--color-neutral-500, #525252);
  font-size: 0.875rem;
  text-align: center;
  padding: 1.5rem 0;
  margin: 0;
}

.bfl__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.bfl__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-neutral-200, #e5e5e5);
  border-radius: 0.5rem;
  background: #fff;
  gap: 0.5rem;
}

.bfl__item--system {
  background: #f8fafc;
}

.bfl__item-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  flex: 1;
}

.bfl__item-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-neutral-800, #262626);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 320px;
}

.bfl__item-size {
  font-size: 0.75rem;
  color: var(--color-neutral-500, #525252);
  flex-shrink: 0;
}

.bfl__badge-system {
  display: inline-flex;
  align-items: center;
  padding: 0.1rem 0.45rem;
  font-size: 0.7rem;
  font-weight: 600;
  background: #eff6ff;
  color: #1d4ed8;
  border-radius: 9999px;
  white-space: nowrap;
  flex-shrink: 0;
}

.bfl__btn-remove {
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

.bfl__btn-remove:hover {
  background: #fee2e2;
  border-color: #fca5a5;
}

.bfl__count {
  font-size: 0.75rem;
  color: var(--color-neutral-400, #a3a3a3);
  margin: 0;
}
</style>
