<template>
  <span
    class="confidence-badge"
    :class="badgeClass"
    :title="tooltip"
    data-testid="confidence-badge"
  >{{ formatted }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{ score?: number }>(),
  { score: 0 },
)

const formatted = computed(() => {
  if (props.score == null || isNaN(props.score)) return '—'
  return props.score.toFixed(2)
})

const badgeClass = computed(() => {
  if (props.score == null || isNaN(props.score)) return 'confidence-badge--unknown'
  if (props.score > 0.8) return 'confidence-badge--high'
  if (props.score >= 0.5) return 'confidence-badge--medium'
  return 'confidence-badge--low'
})

const tooltip = computed(() => {
  if (props.score == null || isNaN(props.score)) return 'Confiança desconhecida'
  if (props.score > 0.8) return 'Alta confiança — sugestão segura'
  if (props.score >= 0.5) return 'Média confiança — requer revisão'
  return 'Baixa confiança — revisar com cuidado'
})
</script>

<style scoped>
.confidence-badge {
  display: inline-flex;
  align-items: center;
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.125rem 0.375rem;
  border-radius: 9999px;
  line-height: 1.25;
  font-family: monospace;
}

.confidence-badge--high {
  background: rgba(16, 185, 129, 0.15);
  color: #6ee7b7;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.confidence-badge--medium {
  background: rgba(245, 158, 11, 0.15);
  color: #fcd34d;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.confidence-badge--low {
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.confidence-badge--unknown {
  background: rgba(107, 114, 128, 0.15);
  color: #9ca3af;
  border: 1px solid rgba(107, 114, 128, 0.3);
}
</style>
