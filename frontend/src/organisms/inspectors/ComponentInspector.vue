<template>
  <div class="component-inspector">
    <component :is="activeSubInspector" :node="props.node" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TreeNode } from '@/types/template.types'
import TableInspector from './TableInspector.vue'
import ChartInspector from './ChartInspector.vue'
import ImageInspector from './ImageInspector.vue'
import ContainerInspector from './ContainerInspector.vue'

const props = withDefaults(
  defineProps<{ node?: TreeNode | null }>(),
  { node: null },
)

const subInspectorMap: Record<string, unknown> = {
  table: TableInspector,
  chart: ChartInspector,
  image: ImageInspector,
  container: ContainerInspector,
}

const activeSubInspector = computed(() => {
  const t = props.node?.type ?? ''
  return subInspectorMap[t] ?? ContainerInspector
})
</script>

<style scoped>
.component-inspector {
  display: flex;
  flex-direction: column;
}
</style>
