<template>
  <div class="wizard-layout">
    <AppHeader :show-bibliotecas="showBibliotecas" @open-bibliotecas="$emit('open-bibliotecas')">
      <template #stepper>
        <slot name="stepper" />
      </template>
    </AppHeader>

    <main class="wizard-layout__content">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { AppHeader } from '@/organisms'

withDefaults(
  defineProps<{
    showBibliotecas?: boolean
  }>(),
  { showBibliotecas: false },
)

defineEmits<{
  'open-bibliotecas': []
}>()
</script>

<style scoped>
.wizard-layout {
  min-height: 100vh;
  background: var(--color-neutral-50);
}

.wizard-layout__content {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1.5rem;
}
</style>
