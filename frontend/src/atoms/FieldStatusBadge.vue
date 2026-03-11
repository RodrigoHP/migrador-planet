<template>
  <span class="badge" :class="badgeClass">{{ status }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: 'ok' | 'ambiguous' | 'not_found' | 'optional'
}>()

const badgeClass = computed(() => `badge--${props.status}`)
</script>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  padding: 0.125rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
}

.badge--ok {
  color: #166534;
  background: #dcfce7;
}

.badge--ambiguous {
  color: #854d0e;
  background: #fef9c3;
}

.badge--not_found {
  color: #991b1b;
  background: #fee2e2;
}

.badge--optional {
  color: #404040;
  background: #e5e5e5;
}
</style>
