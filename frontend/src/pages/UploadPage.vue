<template>
  <WizardLayout>
    <template #stepper>
      <WizardStepper :current-step="1" />
    </template>

    <section class="upload">
      <header class="upload__header">
        <h1>Upload de arquivos</h1>
        <p>Selecione PDF, XSD e dados para iniciar a analise.</p>
      </header>

      <div class="upload__grid">
        <FileDropzone v-model="pdfSelected" label="Arquivo PDF" accept="application/pdf,.pdf" />
        <FileDropzone v-model="xsdSelected" label="Arquivo XSD" accept="text/xml,.xsd" />
        <FileDropzone v-model="dataSelected" label="Arquivo de Dados (JSON/XML)" accept="application/json,text/xml,.json,.xml" />
      </div>

      <CrossValidationBadge
        v-if="allFilesSelected"
        :status="session.crossValidation.status"
        :divergences="session.crossValidation.divergences"
      />

      <div v-if="recoverableWarning" class="upload__warning" role="status">
        {{ recoverableWarning }}
      </div>

      <div v-if="session.error" class="upload__error" role="alert">
        <p>{{ session.error }}</p>
        <Button variant="danger" size="sm" @click="resetToInitial">Tentar novamente</Button>
      </div>

      <div v-if="session.isProcessing" class="upload__progress">
        <ProgressLabel :text="session.processingStep || 'Processando...'" />
        <ProgressBar :value="session.processingPct" :animated="true" />
      </div>

      <div class="upload__actions">
        <Button
          variant="primary"
          size="lg"
          :loading="session.isProcessing"
          :disabled="isAnalyzeDisabled"
          @click="startAnalysis"
        >
          Analisar
        </Button>
      </div>
    </section>
  </WizardLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Button, CrossValidationBadge, ProgressBar, ProgressLabel } from '@/atoms'
import { FileDropzone } from '@/molecules'
import { WizardStepper } from '@/organisms'
import { WizardLayout } from '@/templates'
import { useSessionStore } from '@/stores/session'
import { useSSE } from '@/composables/useSSE'
import type { ExtractionResult } from '@/types'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

const router = useRouter()
const session = useSessionStore()

const pdfSelected = ref<File | null>(null)
const xsdSelected = ref<File | null>(null)
const dataSelected = ref<File | null>(null)
const recoverableWarning = ref<string | null>(null)

const allFilesSelected = computed(() => !!pdfSelected.value && !!xsdSelected.value && !!dataSelected.value)
const isAnalyzeDisabled = computed(() => !allFilesSelected.value || session.isProcessing)

const jobIdRef = computed(() => session.jobId)
useSSE(jobIdRef, {
  onDone: (event) => {
    const extraction = event.extraction ?? session.extraction
    if (!extraction) {
      session.isProcessing = false
      session.setError('Extracao final nao retornou dados validos.')
      return
    }
    session.extraction = extraction
    session.isProcessing = false
    session.currentStep = 2
    router.push('/campos')
  },
  onError: (event) => {
    session.isProcessing = false
    session.setError(event.error ?? 'Falha durante o processamento SSE.')
  },
  onWarning: (message) => {
    recoverableWarning.value = message
  },
})

onMounted(() => {
  session.currentStep = 1
})

watch([pdfSelected, xsdSelected, dataSelected], ([pdf, xsd, data]) => {
  if (!pdf || !xsd || !data) {
    session.crossValidation = { status: null, divergences: [] }
    return
  }

  const divergences: string[] = []
  if (pdf.size === 0) divergences.push('PDF vazio.')
  if (!xsd.name.toLowerCase().endsWith('.xsd')) divergences.push('Arquivo XSD invalido.')
  if (!/\.(json|xml)$/i.test(data.name)) divergences.push('Arquivo de dados deve ser JSON ou XML.')

  session.crossValidation = {
    status: divergences.length > 0 ? 'divergence' : 'ok',
    divergences,
  }
})

function extractWarningMessage(payload: unknown): string | null {
  if (!payload || typeof payload !== 'object') return null
  const p = payload as Record<string, unknown>
  if (typeof p.warning === 'string' && p.warning.trim()) return p.warning
  if (Array.isArray(p.warnings) && p.warnings.length > 0) {
    const first = p.warnings[0]
    if (typeof first === 'string') return first
  }
  return null
}

async function toPdfFile(file: File) {
  return {
    name: file.name,
    pages: 0,
    sizeKB: Math.round(file.size / 1024),
    bytes: await file.arrayBuffer(),
  }
}

async function toXsdFile(file: File) {
  const bytes = await file.arrayBuffer()
  const text = new TextDecoder().decode(bytes)
  const fieldCount = (text.match(/<xs:element\b/g) ?? []).length
  const optionalCount = (text.match(/minOccurs="0"/g) ?? []).length
  return {
    name: file.name,
    fieldCount,
    optionalCount,
    bytes,
  }
}

async function toDataFile(file: File) {
  const bytes = await file.arrayBuffer()
  const text = new TextDecoder().decode(bytes)
  let fieldCount = 0
  try {
    const json = JSON.parse(text)
    if (json && typeof json === 'object' && !Array.isArray(json)) {
      fieldCount = Object.keys(json).length
    }
  } catch {
    fieldCount = 0
  }
  return {
    name: file.name,
    fieldCount,
    bytes,
  }
}

async function uploadFile(path: string, file: File) {
  const formData = new FormData()
  formData.append('file', file, file.name)
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    body: formData,
  })

  let payload: unknown = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  return { response, payload }
}

async function requestExtraction(): Promise<string> {
  const response = await fetch(`${API_BASE}/extract`, { method: 'POST' })
  if (!response.ok) {
    throw new Error('Falha ao iniciar extracao no backend.')
  }
  const payload = await response.json() as { jobId?: string; extraction?: ExtractionResult }
  if (!payload.jobId) {
    throw new Error('Resposta invalida do backend: jobId ausente.')
  }
  if (payload.extraction) {
    session.extraction = payload.extraction
  }
  return payload.jobId
}

async function startAnalysis() {
  if (!pdfSelected.value || !xsdSelected.value || !dataSelected.value) return

  recoverableWarning.value = null
  session.setError(null)
  session.extraction = null
  session.isProcessing = true
  session.processingPct = 0
  session.processingStep = 'Preparando arquivos...'

  try {
    session.pdfFile = await toPdfFile(pdfSelected.value)
    session.xsdFile = await toXsdFile(xsdSelected.value)
    session.dataFile = await toDataFile(dataSelected.value)

    session.processingStep = 'Enviando PDF...'
    const pdfUpload = await uploadFile('/upload/pdf', pdfSelected.value)
    if (!pdfUpload.response.ok) {
      throw new Error('Erro fatal ao enviar PDF.')
    }

    session.processingStep = 'Enviando XSD...'
    const xsdUpload = await uploadFile('/upload/xsd', xsdSelected.value)
    if (!xsdUpload.response.ok) {
      throw new Error('Erro fatal ao enviar XSD.')
    }

    const xsdWarning = extractWarningMessage(xsdUpload.payload)
    if (xsdWarning) {
      recoverableWarning.value = xsdWarning
      session.crossValidation = {
        status: 'divergence',
        divergences: [xsdWarning],
      }
    }

    session.processingStep = 'Enviando dados...'
    const dataUpload = await uploadFile('/upload/data', dataSelected.value)
    if (!dataUpload.response.ok) {
      throw new Error('Erro fatal ao enviar arquivo de dados.')
    }

    session.processingStep = 'Iniciando extracao...'
    session.jobId = await requestExtraction()
    session.processingPct = 5
  } catch (error: any) {
    session.isProcessing = false
    session.jobId = null
    session.setError(error?.message ?? 'Erro inesperado durante a analise.')
  }
}

function resetToInitial() {
  session.resetProcessing()
  session.extraction = null
  session.crossValidation = { status: null, divergences: [] }
  pdfSelected.value = null
  xsdSelected.value = null
  dataSelected.value = null
  recoverableWarning.value = null
}
</script>

<style scoped>
.upload {
  display: grid;
  gap: 1rem;
}

.upload__header h1 {
  margin: 0 0 0.25rem;
  color: var(--color-neutral-900);
}

.upload__header p {
  margin: 0;
  color: var(--color-neutral-700);
}

.upload__grid {
  display: grid;
  gap: 0.75rem;
}

.upload__warning {
  border: 1px solid #fde68a;
  background: #fefce8;
  color: #854d0e;
  border-radius: 0.75rem;
  padding: 0.75rem 0.875rem;
}

.upload__error {
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #991b1b;
  border-radius: 0.75rem;
  padding: 0.75rem 0.875rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.upload__error p {
  margin: 0;
}

.upload__progress {
  display: grid;
  gap: 0.5rem;
}

.upload__actions {
  display: flex;
  justify-content: flex-end;
}
</style>
