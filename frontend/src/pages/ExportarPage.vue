<template>
  <WizardLayout :show-save="true">
    <template #stepper>
      <WizardStepper :current-step="5" />
    </template>

    <section class="export-page">
      <header class="export-page__header">
        <h1>Exportar</h1>
        <p>Valide o pacote final, baixe o ZIP e salve o projeto para retomada.</p>
      </header>

      <section v-if="generation.fidelityScore !== null" class="export-page__fidelity">
        <h2>Fidelidade Final</h2>
        <FidelityScore :score="generation.fidelityScore" />
        <ProgressBar :value="generation.fidelityScore" />
        <p v-if="generation.fidelityComment" class="export-page__fidelity-comment">
          {{ generation.fidelityComment }}
        </p>
      </section>

      <ExportChecklist @update:can-download="canDownload = $event" />

      <div class="export-page__actions">
        <Button variant="ghost" @click="router.push('/geracao')">
          ◀ Voltar à Geração
        </Button>
        <Button
          variant="secondary"
          :disabled="!generation.previewJobId"
          @click="openPreview"
        >
          Abrir Preview
        </Button>
        <Button
          variant="primary"
          :disabled="!canDownload || !generation.previewJobId"
          :loading="isDownloading"
          @click="downloadZip"
        >
          Download ZIP
        </Button>
        <Button variant="ghost" @click="startNewProject">
          Novo Projeto
        </Button>
      </div>

      <p v-if="zipSizeKb !== null" class="export-page__size">
        Tamanho do ZIP: {{ zipSizeKb.toFixed(1) }} KB
      </p>
    </section>
  </WizardLayout>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { openDB } from 'idb'
import { Button, FidelityScore, ProgressBar } from '@/atoms'
import { ExportChecklist, WizardStepper } from '@/organisms'
import { WizardLayout } from '@/templates'
import { useGenerationStore } from '@/stores/generation'
import { useLayoutStore } from '@/stores/layout'
import { useMappingStore } from '@/stores/mapping'
import { useSessionStore } from '@/stores/session'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

const router = useRouter()
const session = useSessionStore()
const mapping = useMappingStore()
const layout = useLayoutStore()
const generation = useGenerationStore()

const canDownload = ref(false)
const isDownloading = ref(false)
const zipSizeKb = ref<number | null>(null)

onMounted(() => {
  session.currentStep = 5
})

function openPreview() {
  if (!generation.previewJobId) return
  window.open(`${API_BASE}/api/preview/${generation.previewJobId}`, '_blank')
}

async function downloadZip() {
  if (!generation.previewJobId) return
  isDownloading.value = true

  try {
    const response = await fetch(`${API_BASE}/api/export/${generation.previewJobId}/zip`)
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

.export-page__fidelity {
  display: grid;
  gap: 0.6rem;
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.75rem;
  padding: 1rem;
  background: #fff;
}

.export-page__fidelity h2 {
  margin: 0;
  font-size: 1rem;
}

.export-page__fidelity-comment {
  margin: 0;
  color: var(--color-neutral-700);
  font-size: 0.875rem;
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
