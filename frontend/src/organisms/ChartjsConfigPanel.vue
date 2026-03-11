<template>
  <component
    :is="ChartjsConfigPanelInner"
    :initial-config="initialConfig"
    @save="$emit('save', $event)"
  />
</template>

<script setup lang="ts">
import { defineAsyncComponent } from 'vue'
import type { ChartjsConfig } from '@/types'

defineProps<{
  initialConfig: ChartjsConfig
}>()

defineEmits<{
  save: [config: ChartjsConfig]
}>()

const ChartjsConfigPanelInner = defineAsyncComponent(
  () => import('./ChartjsConfigPanelInner.vue'),
)
</script>
