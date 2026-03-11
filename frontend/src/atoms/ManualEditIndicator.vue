<template>
  <span v-if="visible" class="manual-indicator" title="Editado manualmente" aria-label="Editado manualmente">
    <PenLine :size="14" />
  </span>
</template>

<script setup lang="ts">
import { PenLine } from 'lucide-vue-next'

defineProps<{
  visible: boolean
}>()
</script>

<style scoped>
.manual-indicator {
  display: inline-flex;
  align-items: center;
  color: var(--color-primary-600);
}
</style>
