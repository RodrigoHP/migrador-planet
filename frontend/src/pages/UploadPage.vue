<template>
  <FullWidthLayout>
    <section class="upload">
      <!-- Header + Voltar -->
      <div class="upload__topbar">
        <button class="upload__back" type="button" @click="router.push('/')">← Voltar</button>
        <h1 class="upload__title">Upload de Arquivos</h1>
      </div>

      <!-- Campo nome do template (AC: 3) -->
      <div class="upload__field">
        <label class="upload__label" for="template-name">Nome do Template</label>
        <input
          id="template-name"
          v-model="templateName"
          class="upload__input"
          type="text"
          placeholder="Ex: Extrato Bancário, Nota Fiscal..."
        />
      </div>

      <!-- Erros de validação de tamanho -->
      <div v-if="sizeErrors.length" class="upload__size-errors">
        <p v-for="(err, i) in sizeErrors" :key="i" class="upload__size-error">{{ err }}</p>
      </div>

      <!-- Dropzones (AC: 1) -->
      <div class="upload__grid">

        <!-- Dropzone PDFs: múltiplos (AC: 1) -->
        <div
          class="dropzone"
          :class="{ 'dropzone--drag': isDraggingPdf }"
          @dragenter.prevent="isDraggingPdf = true"
          @dragover.prevent="isDraggingPdf = true"
          @dragleave.prevent="isDraggingPdf = false"
          @drop.prevent="onDropPdf"
        >
          <p class="dropzone__label">📄 PDFs do documento</p>
          <p v-if="pdfFiles.length === 1" class="dropzone__file">
            {{ pdfFiles[0]?.name }} ({{ formatSize(pdfFiles[0]?.size ?? 0) }})
          </p>
          <p v-else-if="pdfFiles.length > 1" class="dropzone__file">
            {{ pdfFiles.length }} PDFs selecionados
          </p>
          <p v-else class="dropzone__hint">Arraste PDFs aqui ou selecione manualmente</p>
          <div class="dropzone__actions">
            <button class="dropzone__button" type="button" @click="pdfInputRef?.click()">
              Selecionar PDFs
            </button>
          </div>
          <input
            ref="pdfInputRef"
            class="dropzone__input"
            type="file"
            accept=".pdf"
            multiple
            @change="onPdfInputChange"
          />
        </div>

        <!-- Dropzone XSD: único (AC: 1) -->
        <div
          class="dropzone"
          :class="{ 'dropzone--drag': isDraggingXsd }"
          @dragenter.prevent="isDraggingXsd = true"
          @dragover.prevent="isDraggingXsd = true"
          @dragleave.prevent="isDraggingXsd = false"
          @drop.prevent="onDropXsd"
        >
          <p class="dropzone__label">📋 Schema XSD</p>
          <p v-if="xsdFile" class="dropzone__file">
            {{ xsdFile.name }} ({{ formatSize(xsdFile.size) }})
          </p>
          <p v-else class="dropzone__hint">Arraste o XSD aqui ou selecione manualmente</p>
          <div class="dropzone__actions">
            <button class="dropzone__button" type="button" @click="xsdInputRef?.click()">
              Selecionar XSD
            </button>
            <button v-if="xsdFile" class="dropzone__clear" type="button" @click="xsdFile = null">
              Limpar
            </button>
          </div>
          <input
            ref="xsdInputRef"
            class="dropzone__input"
            type="file"
            accept=".xsd"
            @change="onXsdInputChange"
          />
        </div>

        <!-- Dropzone Data: único, opcional (AC: 1) -->
        <div
          class="dropzone"
          :class="{ 'dropzone--drag': isDraggingData }"
          @dragenter.prevent="isDraggingData = true"
          @dragover.prevent="isDraggingData = true"
          @dragleave.prevent="isDraggingData = false"
          @drop.prevent="onDropData"
        >
          <p class="dropzone__label">📊 Dados (opcional)</p>
          <p v-if="dataFile" class="dropzone__file">
            {{ dataFile.name }} ({{ formatSize(dataFile.size) }})
          </p>
          <p v-else class="dropzone__hint">Arraste XML/JSON aqui ou selecione manualmente</p>
          <div class="dropzone__actions">
            <button class="dropzone__button" type="button" @click="dataInputRef?.click()">
              Selecionar Dados
            </button>
            <button v-if="dataFile" class="dropzone__clear" type="button" @click="dataFile = null">
              Limpar
            </button>
          </div>
          <input
            ref="dataInputRef"
            class="dropzone__input"
            type="file"
            accept=".xml,.json"
            @change="onDataInputChange"
          />
        </div>
      </div>

      <!-- Lista de PDFs com remoção e contagem (AC: 2) -->
      <div v-if="pdfFiles.length" class="upload__pdf-list">
        <p class="upload__pdf-count">📊 {{ pdfFiles.length }} PDF{{ pdfFiles.length > 1 ? 's' : '' }} (recomendado: 3-5)</p>
        <ul class="upload__pdf-items">
          <li v-for="(file, index) in pdfFiles" :key="index" class="upload__pdf-item">
            <span class="upload__pdf-name">{{ file.name }} ({{ formatSize(file.size) }})</span>
            <button class="upload__pdf-remove" type="button" @click="removePdf(index)">🗑️</button>
          </li>
        </ul>
      </div>

      <!-- Hints contextuais (AC: 4-7) -->
      <div v-if="currentHint" class="upload__hint" role="status">
        {{ currentHint }}
      </div>

      <!-- Progresso de upload (AC: 12) -->
      <div v-if="isUploading" class="upload__progress">
        <p class="upload__progress-label">Enviando arquivos... {{ uploadProgress }}%</p>
        <ProgressBar :value="uploadProgress" :animated="true" />
      </div>

      <!-- Erro de upload -->
      <div v-if="uploadError" class="upload__error" role="alert">
        <p>{{ uploadError }}</p>
        <button class="upload__retry-btn" type="button" @click="uploadError = null">Fechar</button>
      </div>

      <!-- Ações -->
      <div class="upload__actions">
        <button
          class="upload__submit"
          type="button"
          :disabled="isAnalyzeDisabled"
          @click="startAnalysis"
        >
          Iniciar Análise
        </button>
      </div>
    </section>
  </FullWidthLayout>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ProgressBar } from '@/atoms'
import { FullWidthLayout } from '@/templates'
import { useSessionStore } from '@/stores/session'

const PDF_MAX_BYTES = 50 * 1024 * 1024  // 50 MB
const OTHER_MAX_BYTES = 10 * 1024 * 1024 // 10 MB

const router = useRouter()
const session = useSessionStore()

// --- State ---
const templateName = ref('')
const pdfFiles = ref<File[]>([])
const xsdFile = ref<File | null>(null)
const dataFile = ref<File | null>(null)
const sizeErrors = ref<string[]>([])
const isUploading = ref(false)
const uploadProgress = ref(0)
const uploadError = ref<string | null>(null)

// Drag state
const isDraggingPdf = ref(false)
const isDraggingXsd = ref(false)
const isDraggingData = ref(false)

// Input refs
const pdfInputRef = ref<HTMLInputElement | null>(null)
const xsdInputRef = ref<HTMLInputElement | null>(null)
const dataInputRef = ref<HTMLInputElement | null>(null)

// --- Computed (AC: 4-7) ---
const hasPdf = computed(() => pdfFiles.value.length > 0)
const hasXsd = computed(() => xsdFile.value !== null)
const hasData = computed(() => dataFile.value !== null)
const pdfCount = computed(() => pdfFiles.value.length)

const isAnalyzeDisabled = computed(() => !hasPdf.value || !hasXsd.value || isUploading.value)

const currentHint = computed<string | null>(() => {
  // AC 4: sem arquivos
  if (!hasPdf.value && !hasXsd.value) {
    return 'Envie ao menos 1 PDF + XSD para continuar'
  }
  // AC 5: só 1 PDF (com XSD)
  if (pdfCount.value === 1 && hasXsd.value && !hasData.value) {
    return '💡 Adicionar mais PDFs melhora a detecção de variações'
  }
  // AC 7: PDF + dados sem XSD
  if (hasPdf.value && hasData.value && !hasXsd.value) {
    return '💡 Adicionar o XSD permite validar campos obrigatórios'
  }
  // AC 6: PDF + XSD sem dados
  if (hasPdf.value && hasXsd.value && !hasData.value) {
    return '💡 Adicionar dados reais melhora a detecção de tipos e formatos'
  }
  return null
})

// --- Helpers ---
function formatSize(size: number): string {
  if (size >= 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`
  return `${(size / 1024).toFixed(1)} KB`
}

function validatePdfSize(files: File[]): { valid: File[]; errors: string[] } {
  const valid: File[] = []
  const errors: string[] = []
  for (const file of files) {
    if (file.size > PDF_MAX_BYTES) {
      errors.push(`Arquivo '${file.name}' excede o tamanho máximo de 50MB`)
    } else {
      valid.push(file)
    }
  }
  return { valid, errors }
}

function validateOtherSize(file: File): string | null {
  if (file.size > OTHER_MAX_BYTES) {
    return `Arquivo '${file.name}' excede o tamanho máximo de 10MB`
  }
  return null
}

// --- PDF handlers ---
function addPdfFiles(files: FileList | null) {
  if (!files || files.length === 0) return
  const arr = Array.from(files)
  const { valid, errors } = validatePdfSize(arr)
  // Reset size errors before each new batch so stale errors don't accumulate
  sizeErrors.value = errors
  // Deduplicate by name
  const existingNames = new Set(pdfFiles.value.map((f) => f.name))
  for (const f of valid) {
    if (!existingNames.has(f.name)) {
      pdfFiles.value.push(f)
      existingNames.add(f.name)
    }
  }
  // Reset input so the same files can be re-selected
  if (pdfInputRef.value) pdfInputRef.value.value = ''
}

function removePdf(index: number) {
  pdfFiles.value.splice(index, 1)
}

function onPdfInputChange(event: Event) {
  const target = event.target as HTMLInputElement
  addPdfFiles(target.files)
}

function onDropPdf(event: DragEvent) {
  isDraggingPdf.value = false
  addPdfFiles(event.dataTransfer?.files ?? null)
}

// --- XSD handlers ---
function setXsdFile(file: File | null) {
  if (!file) {
    xsdFile.value = null
    return
  }
  const err = validateOtherSize(file)
  if (err) {
    sizeErrors.value = [...sizeErrors.value.filter((e) => !e.includes(file.name)), err]
    return
  }
  sizeErrors.value = sizeErrors.value.filter((e) => !e.includes(file.name))
  xsdFile.value = file
}

function onXsdInputChange(event: Event) {
  const target = event.target as HTMLInputElement
  setXsdFile(target.files?.[0] ?? null)
  if (xsdInputRef.value) xsdInputRef.value.value = ''
}

function onDropXsd(event: DragEvent) {
  isDraggingXsd.value = false
  setXsdFile(event.dataTransfer?.files?.[0] ?? null)
}

// --- Data handlers ---
function setDataFile(file: File | null) {
  if (!file) {
    dataFile.value = null
    return
  }
  const err = validateOtherSize(file)
  if (err) {
    sizeErrors.value = [...sizeErrors.value.filter((e) => !e.includes(file.name)), err]
    return
  }
  sizeErrors.value = sizeErrors.value.filter((e) => !e.includes(file.name))
  dataFile.value = file
}

function onDataInputChange(event: Event) {
  const target = event.target as HTMLInputElement
  setDataFile(target.files?.[0] ?? null)
  if (dataInputRef.value) dataInputRef.value.value = ''
}

function onDropData(event: DragEvent) {
  isDraggingData.value = false
  setDataFile(event.dataTransfer?.files?.[0] ?? null)
}

// --- Upload (AC: 9, 12) ---
const API_BASE = import.meta.env.VITE_API_URL ?? ''

async function startAnalysis() {
  if (!hasPdf.value || !hasXsd.value) return

  sizeErrors.value = []
  uploadError.value = null
  isUploading.value = true
  uploadProgress.value = 0
  session.uploadedPdfs = []

  const formData = new FormData()
  for (const pdf of pdfFiles.value) {
    formData.append('pdfs[]', pdf, pdf.name)
  }
  formData.append('xsd', xsdFile.value!, xsdFile.value!.name)
  if (dataFile.value) {
    formData.append('data', dataFile.value, dataFile.value.name)
  }
  formData.append('template_name', templateName.value)

  return new Promise<void>((resolve) => {
    const xhr = new XMLHttpRequest()

    xhr.upload.onprogress = (event: ProgressEvent) => {
      if (event.lengthComputable) {
        uploadProgress.value = Math.round((event.loaded / event.total) * 100)
      }
    }

    xhr.onload = () => {
      isUploading.value = false
      if (xhr.status >= 200 && xhr.status < 300) {
        const responseText = xhr.responseText
        const filesToProcess = [...pdfFiles.value]
        const handleSuccess = async () => {
          try {
            const response = JSON.parse(responseText) as { job_id: string }
            session.jobId = response.job_id
            const pdfs = await Promise.all(
              filesToProcess.map(async (pdf) => ({
                name: pdf.name,
                pages: 0,
                sizeKB: Math.round(pdf.size / 1024),
                bytes: await pdf.arrayBuffer(),
              }))
            )
            session.uploadedPdfs = pdfs
            // AC2 — Persist bytes to IndexedDB so PDF tab survives page refresh (Story 12.4)
            const { savePdfBytes } = await import('@/utils/pdfStorage')
            await Promise.all(
              pdfs.map((pdf, i) =>
                savePdfBytes(response.job_id, i, new Uint8Array(pdf.bytes as ArrayBuffer))
              )
            )
            router.push('/analyzing')
          } catch {
            uploadError.value = 'Resposta inválida do servidor.'
          }
          resolve()
        }
        handleSuccess()
      } else {
        uploadError.value = `Erro ao enviar arquivos: ${xhr.status} ${xhr.statusText}`
        resolve()
      }
    }

    xhr.onerror = () => {
      isUploading.value = false
      uploadError.value = 'Falha de conexão ao enviar arquivos.'
      resolve()
    }

    xhr.open('POST', `${API_BASE}/api/upload`)
    xhr.send(formData)
  })
}
</script>

<style scoped>
.upload {
  display: grid;
  gap: 1rem;
}

.upload__topbar {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.upload__back {
  border: 1px solid var(--color-neutral-200);
  background: #fff;
  color: var(--color-neutral-700);
  border-radius: 0.5rem;
  padding: 0.4rem 0.75rem;
  font-size: 0.875rem;
  cursor: pointer;
  white-space: nowrap;
}

.upload__back:hover {
  background: var(--color-neutral-100);
}

.upload__title {
  margin: 0;
  color: var(--color-neutral-900);
  font-size: 1.25rem;
}

.upload__field {
  display: grid;
  gap: 0.375rem;
}

.upload__label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-neutral-800);
}

.upload__input {
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.5rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  color: var(--color-neutral-900);
  background: #fff;
  width: 100%;
  box-sizing: border-box;
}

.upload__input:focus {
  outline: 2px solid var(--color-primary-600);
  outline-offset: 1px;
}

.upload__size-errors {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 0.65rem;
  padding: 0.65rem 0.875rem;
}

.upload__size-error {
  margin: 0;
  font-size: 0.875rem;
  color: #991b1b;
}

.upload__size-error + .upload__size-error {
  margin-top: 0.25rem;
}

.upload__grid {
  display: grid;
  gap: 0.75rem;
}

/* Dropzone styles (inline — FileDropzone only supports single file) */
.dropzone {
  border: 2px dashed var(--color-neutral-200);
  border-radius: 0.75rem;
  padding: 1rem;
  background: #fff;
}

.dropzone--drag {
  border-color: var(--color-primary-600);
  background: #eff6ff;
}

.dropzone__label {
  margin: 0;
  font-weight: 600;
  color: var(--color-neutral-900);
}

.dropzone__hint,
.dropzone__file {
  margin: 0.5rem 0;
  color: var(--color-neutral-700);
  font-size: 0.875rem;
}

.dropzone__actions {
  display: flex;
  gap: 0.5rem;
}

.dropzone__button,
.dropzone__clear {
  border: 1px solid var(--color-neutral-200);
  background: #fff;
  color: var(--color-neutral-900);
  border-radius: 0.5rem;
  padding: 0.4rem 0.75rem;
  font-size: 0.875rem;
  cursor: pointer;
}

.dropzone__button:hover,
.dropzone__clear:hover {
  background: var(--color-neutral-100);
}

.dropzone__input {
  display: none;
}

/* PDF list (AC: 2) */
.upload__pdf-list {
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.75rem;
  padding: 0.75rem 0.875rem;
  background: var(--color-neutral-50);
}

.upload__pdf-count {
  margin: 0 0 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-neutral-800);
}

.upload__pdf-items {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.35rem;
}

.upload__pdf-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.upload__pdf-name {
  font-size: 0.875rem;
  color: var(--color-neutral-700);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload__pdf-remove {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 1rem;
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
  flex-shrink: 0;
}

.upload__pdf-remove:hover {
  background: #fef2f2;
}

/* Hint (AC: 4-7) */
.upload__hint {
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  color: #1e40af;
  border-radius: 0.65rem;
  padding: 0.65rem 0.875rem;
  font-size: 0.875rem;
}

/* Progress (AC: 12) */
.upload__progress {
  display: grid;
  gap: 0.375rem;
}

.upload__progress-label {
  margin: 0;
  font-size: 0.875rem;
  color: var(--color-neutral-700);
}

/* Error */
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
  font-size: 0.875rem;
}

.upload__retry-btn {
  border: 1px solid #fecaca;
  background: #fff;
  color: #991b1b;
  border-radius: 0.5rem;
  padding: 0.3rem 0.6rem;
  font-size: 0.8rem;
  cursor: pointer;
  flex-shrink: 0;
}

/* Actions */
.upload__actions {
  display: flex;
  justify-content: flex-end;
}

.upload__submit {
  background: var(--color-primary-600);
  color: #fff;
  border: none;
  border-radius: 0.5rem;
  padding: 0.625rem 1.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 200ms;
}

.upload__submit:hover:not(:disabled) {
  background: var(--color-primary-700, #1d4ed8);
}

.upload__submit:disabled {
  background: var(--color-neutral-300);
  color: var(--color-neutral-500);
  cursor: not-allowed;
}
</style>
