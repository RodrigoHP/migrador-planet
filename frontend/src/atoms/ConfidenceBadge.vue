<template>
  <span class="badge" :class="badgeClass">{{ confidence }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  confidence: 'high' | 'medium' | 'low'
}>()

const badgeClass = computed(() => `badge--${props.confidence}`)
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

.badge--high {
  color: #166534;
  background: #dcfce7;
}

.badge--medium {
  color: #854d0e;
  background: #fef9c3;
}

.badge--low {
  color: #991b1b;
  background: #fee2e2;
}
</style>
