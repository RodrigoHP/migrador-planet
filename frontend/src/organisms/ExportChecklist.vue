<template>
  <section class="export-checklist">
    <h2>Validações do ZIP</h2>
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
import { useLayoutStore } from '@/stores/layout'

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
const layout = useLayoutStore()

const items = ref<ChecklistStateItem[]>([])

const allCriticalPassed = computed(() =>
  items.value.filter((item) => item.critical).every((item) => item.status !== 'error'),
)

function runChecks() {
  const hasBundledJsPath = (generation.html ?? '').includes('./js/')
  const hasLibraries = Object.keys(layout.bibliotecasVersions).length > 0

  items.value = [
    {
      id: 'html',
      label: 'index.html gerado',
      status: generation.html ? 'ok' : 'error',
      critical: true,
    },
    {
      id: 'css',
      label: 'style.css gerado',
      status: generation.css ? 'ok' : 'error',
      critical: true,
    },
    {
      id: 'js',
      label: 'base.js gerado',
      status: generation.js ? 'ok' : 'error',
      critical: true,
    },
    {
      id: 'job',
      label: 'Preview Job ID disponível',
      status: generation.previewJobId ? 'ok' : 'error',
      critical: true,
    },
    {
      id: 'libs',
      label: 'Bibliotecas selecionadas',
      status: hasLibraries ? 'ok' : 'warning',
      critical: false,
      note: hasLibraries ? undefined : 'Nenhuma versão foi selecionada explicitamente.',
    },
    {
      id: 'paths',
      label: 'Referência relativa de bibliotecas (./js/...)',
      status: hasBundledJsPath ? 'ok' : 'warning',
      critical: false,
      note: hasBundledJsPath ? undefined : 'Não foi encontrada referência ./js/ no HTML atual.',
    },
  ]

  emit('update:canDownload', allCriticalPassed.value)
}

onMounted(runChecks)

watch(
  () => [
    generation.html,
    generation.css,
    generation.js,
    generation.previewJobId,
    generation.monacoEdits,
    layout.bibliotecasVersions,
  ],
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
