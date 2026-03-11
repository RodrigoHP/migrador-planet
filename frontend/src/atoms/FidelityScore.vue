<template>
  <div class="fidelity" :class="toneClass">
    <span class="fidelity__label">Fidelidade</span>
    <strong class="fidelity__value">{{ displayedScore }}%</strong>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

const props = defineProps<{
  score: number
}>()

const displayedScore = ref(0)

const toneClass = computed(() => {
  if (props.score >= 80) return 'fidelity--high'
  if (props.score >= 60) return 'fidelity--medium'
  return 'fidelity--low'
})

function animateTo(target: number) {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reducedMotion) {
    displayedScore.value = target
    return
  }

  const startAt = performance.now()
  const duration = 600

  const tick = (now: number) => {
    const elapsed = now - startAt
    const progress = Math.min(elapsed / duration, 1)
    displayedScore.value = Math.round(target * progress)
    if (progress < 1) requestAnimationFrame(tick)
  }

  requestAnimationFrame(tick)
}

onMounted(() => animateTo(props.score))
watch(() => props.score, (next) => animateTo(next))
</script>

<style scoped>
.fidelity {
  display: grid;
  gap: 0.15rem;
  padding: 0.75rem;
  border-radius: 0.65rem;
  border: 1px solid var(--color-neutral-200);
}

.fidelity__label {
  font-size: 0.75rem;
  color: var(--color-neutral-700);
}

.fidelity__value {
  font-size: 1.25rem;
}

.fidelity--high .fidelity__value {
  color: var(--color-success-600);
}

.fidelity--medium .fidelity__value {
  color: var(--color-warning-500);
}

.fidelity--low .fidelity__value {
  color: var(--color-error-600);
}
</style>
