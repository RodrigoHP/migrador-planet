<template>
  <section class="export-checklist">
    <h2>Resumo do Pacote</h2>
    <ul>
      <ChecklistItem
        v-for="item in items"
        :key="item.id"
        :label="item.label"
        :status="item.status"
        :note="item.note"
      />
    </ul>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ChecklistItem } from '@/atoms'
import { useGenerationStore } from '@/stores/generation'

type ItemStatus = 'ok' | 'warning' | 'error'
interface ChecklistStateItem {
  id: string
  label: string
  status: ItemStatus
  critical: boolean
  note?: string
}

const emit = defineEmits<{
  'update:canDownload': [value: boolean]
}>()

const generation = useGenerationStore()

const items = ref<ChecklistStateItem[]>([])

const allCriticalPassed = computed(() =>
  items.value.filter((item) => item.critical).every((item) => item.status !== 'error'),
)

function runChecks() {
  items.value = [
    {
      id: 'html',
      label: 'Template HTML gerado',
      status: generation.html ? 'ok' : 'error',
      critical: true,
    },
    {
      id: 'css',
      label: 'Estilos CSS gerados',
      status: generation.css ? 'ok' : 'error',
      critical: true,
    },
    {
      id: 'js',
      label: 'Script JS gerado',
      status: generation.js ? 'ok' : 'error',
      critical: true,
    },
  ]

  emit('update:canDownload', allCriticalPassed.value)
}

onMounted(runChecks)

watch(
  () => [generation.html, generation.css, generation.js, generation.monacoEdits],
  runChecks,
  { deep: true },
)
</script>

<style scoped>
.export-checklist {
  display: grid;
  gap: 0.7rem;
}

.export-checklist h2 {
  margin: 0;
  font-size: 1rem;
}

.export-checklist ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.55rem;
}
</style>
