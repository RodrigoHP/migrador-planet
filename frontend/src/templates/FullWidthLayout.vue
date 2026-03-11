<template>
  <div class="full-width-layout">
    <AppHeader :show-bibliotecas="showBibliotecas" @open-bibliotecas="$emit('open-bibliotecas')">
      <template #stepper>
        <slot name="stepper" />
      </template>
    </AppHeader>

    <main class="full-width-layout__content">
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
.full-width-layout {
  min-height: 100vh;
  background: var(--color-neutral-50);
}

.full-width-layout__content {
  max-width: 860px;
  margin: 0 auto;
  padding: 1.5rem;
}
</style>
