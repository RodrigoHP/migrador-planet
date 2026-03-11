<template>
  <div class="app-shell">
    <AppHeader :show-bibliotecas="true" @open-bibliotecas="onOpenBibliotecas">
      <template #stepper>
        <div class="stepper-placeholder">Wizard steps</div>
      </template>
    </AppHeader>

    <main class="app-content">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import { AppHeader } from '@/organisms'

function onOpenBibliotecas() {
  // Placeholder for story 1.4 modal wiring.
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: var(--color-neutral-50);
}

.app-content {
  padding: 1.5rem;
}

.stepper-placeholder {
  font-size: 0.875rem;
  color: var(--color-neutral-500);
}
</style>
