<template>
  <FullWidthLayout>
    <template #stepper>
      <WizardStepper :current-step="5" />
    </template>

    <section class="export-page">
      <header class="export-page__header">
        <h1>Exportar</h1>
        <p>Valide o pacote final, baixe o ZIP e salve o projeto para retomada.</p>
      </header>

      <ExportChecklist @update:can-download="canDownload = $event" />

      <div class="export-page__actions">
        <Button
          variant="primary"
          :disabled="!canDownload || !generation.previewJobId"
          :loading="isDownloading"
          @click="downloadZip"
        >
          Download ZIP
        </Button>
        <Button variant="secondary" :loading="isSavingProject" @click="saveProject">
          Salvar Projeto (.json)
        </Button>
        <Button variant="ghost" @click="startNewProject">
          Novo Projeto
        </Button>
      </div>

      <p v-if="zipSizeKb !== null" class="export-page__size">
        Tamanho do ZIP: {{ zipSizeKb.toFixed(1) }} KB
      </p>
    </section>
  </FullWidthLayout>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { openDB } from 'idb'
import { Button } from '@/atoms'
import { ExportChecklist, WizardStepper } from '@/organisms'
import { FullWidthLayout } from '@/templates'
import { useGenerationStore } from '@/stores/generation'
import { useLayoutStore } from '@/stores/layout'
import { useMappingStore } from '@/stores/mapping'
import { useSessionStore } from '@/stores/session'
import { useProject } from '@/composables/useProject'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

const router = useRouter()
const session = useSessionStore()
const mapping = useMappingStore()
const layout = useLayoutStore()
const generation = useGenerationStore()
const { save } = useProject()

const canDownload = ref(false)
const isDownloading = ref(false)
const isSavingProject = ref(false)
const zipSizeKb = ref<number | null>(null)

onMounted(() => {
  session.currentStep = 5
})

async function downloadZip() {
  if (!generation.previewJobId) return
  isDownloading.value = true

  try {
    const response = await fetch(`${API_BASE}/export/${generation.previewJobId}/zip`)
    if (!response.ok) {
      throw new Error('Falha ao baixar ZIP.')
    }

    const blob = await response.blob()
    zipSizeKb.value = blob.size / 1024

    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `template-${generation.previewJobId}.zip`
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } finally {
    isDownloading.value = false
  }
}

async function saveProject() {
  isSavingProject.value = true
  try {
    await save()
  } finally {
    isSavingProject.value = false
  }
}

async function startNewProject() {
  const confirmed = window.confirm('Iniciar novo projeto? O progresso atual será perdido.')
  if (!confirmed) return

  session.$reset()
  mapping.$reset()
  layout.$reset()
  generation.$reset()

  const db = await openDB('migrador', 1)
  await db.delete('project', 'current')
  await db.delete('project', 'layout')

  router.push('/')
}
</script>

<style scoped>
.export-page {
  display: grid;
  gap: 1rem;
}

.export-page__header h1 {
  margin: 0 0 0.3rem;
}

.export-page__header p {
  margin: 0;
  color: var(--color-neutral-700);
}

.export-page__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.export-page__size {
  margin: 0;
  color: var(--color-neutral-700);
  font-size: 0.9rem;
}
</style>
