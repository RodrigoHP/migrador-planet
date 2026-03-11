<template>
  <li class="check-item" :class="`check-item--${status}`">
    <span class="check-item__icon" aria-hidden="true">{{ icon }}</span>
    <div>
      <p class="check-item__label">{{ label }}</p>
      <p v-if="note" class="check-item__note">{{ note }}</p>
    </div>
  </li>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  label: string
  status: 'ok' | 'warning' | 'error'
  note?: string
}>()

const icon = computed(() => {
  if (props.status === 'ok') return '✓'
  if (props.status === 'warning') return '!'
  return '✕'
})
</script>

<style scoped>
.check-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.55rem;
  align-items: start;
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.55rem;
  padding: 0.55rem 0.65rem;
}

.check-item__icon {
  width: 1.1rem;
  height: 1.1rem;
  border-radius: 9999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
}

.check-item__label {
  margin: 0;
  font-size: 0.9rem;
}

.check-item__note {
  margin: 0.2rem 0 0;
  font-size: 0.8rem;
  color: var(--color-neutral-700);
}

.check-item--ok .check-item__icon {
  background: #dcfce7;
  color: #166534;
}

.check-item--warning .check-item__icon {
  background: #fef9c3;
  color: #92400e;
}

.check-item--error .check-item__icon {
  background: #fee2e2;
  color: #991b1b;
}
</style>
