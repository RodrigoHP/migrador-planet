<template>
  <div class="toast-container" aria-live="polite" aria-atomic="false" />
</template>

<script setup lang="ts"></script>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  pointer-events: none;
}
</style>
