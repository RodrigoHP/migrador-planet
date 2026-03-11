<template>
  <div class="cross-badge" :class="badgeClass">
    <strong>{{ title }}</strong>
    <ul v-if="status === 'divergence' && divergences.length" class="cross-badge__list">
      <li v-for="item in divergences" :key="item">{{ item }}</li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: 'ok' | 'divergence' | null
  divergences: string[]
}>()

const title = computed(() => {
  if (props.status === 'ok') return 'Arquivos compatíveis'
  if (props.status === 'divergence') return 'Divergências encontradas'
  return 'Aguardando validação'
})

const badgeClass = computed(() => {
  if (props.status === 'ok') return 'cross-badge--ok'
  if (props.status === 'divergence') return 'cross-badge--divergence'
  return 'cross-badge--neutral'
})
</script>

<style scoped>
.cross-badge {
  border-radius: 0.75rem;
  padding: 0.75rem 0.875rem;
  border: 1px solid transparent;
}

.cross-badge--ok {
  color: #166534;
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.cross-badge--divergence {
  color: #854d0e;
  background: #fefce8;
  border-color: #fde68a;
}

.cross-badge--neutral {
  color: var(--color-neutral-700);
  background: var(--color-neutral-100);
  border-color: var(--color-neutral-200);
}

.cross-badge__list {
  margin: 0.5rem 0 0;
  padding-left: 1.1rem;
}
</style>
