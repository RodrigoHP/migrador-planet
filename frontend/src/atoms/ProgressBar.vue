<template>
  <div class="progress" role="progressbar" :aria-valuenow="safeValue" aria-valuemin="0" aria-valuemax="100">
    <div class="progress__inner" :class="{ 'progress__inner--animated': animated }" :style="{ width: `${safeValue}%` }" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    value: number
    animated?: boolean
  }>(),
  { animated: true },
)

const safeValue = computed(() => Math.max(0, Math.min(100, Math.round(props.value))))
</script>

<style scoped>
.progress {
  width: 100%;
  height: 0.625rem;
  border-radius: 9999px;
  background: var(--color-neutral-200);
  overflow: hidden;
}

.progress__inner {
  height: 100%;
  background: var(--color-primary-600);
  transition: width 300ms linear;
}

.progress__inner--animated {
  background-image: linear-gradient(
    45deg,
    rgba(255, 255, 255, 0.2) 25%,
    transparent 25%,
    transparent 50%,
    rgba(255, 255, 255, 0.2) 50%,
    rgba(255, 255, 255, 0.2) 75%,
    transparent 75%,
    transparent
  );
  background-size: 1rem 1rem;
  animation: move 1s linear infinite;
}

@keyframes move {
  to {
    background-position: 1rem 0;
  }
}
</style>
