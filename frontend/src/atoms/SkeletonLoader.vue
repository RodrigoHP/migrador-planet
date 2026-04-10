<template>
  <div
    class="skeleton-loader"
    :style="skeletonStyle"
    role="status"
    aria-label="Carregando..."
    aria-busy="true"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    width?: string
    height?: string
    borderRadius?: string
  }>(),
  {
    width: '100%',
    height: '1rem',
    borderRadius: '0.25rem',
  },
)

const skeletonStyle = computed(() => ({
  width: props.width,
  height: props.height,
  borderRadius: props.borderRadius,
}))
</script>

<style scoped>
.skeleton-loader {
  background: linear-gradient(
    90deg,
    var(--color-neutral-700, #374151) 25%,
    var(--color-neutral-600, #4b5563) 50%,
    var(--color-neutral-700, #374151) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.4s ease-in-out infinite;
  display: block;
  flex-shrink: 0;
}

@keyframes skeleton-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
