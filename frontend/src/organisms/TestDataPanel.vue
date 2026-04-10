<template>
  <div class="test-data-panel">
    <!-- Split layout: list (left 30%) | details (right 70%) -->
    <div class="test-data-panel__list">
      <!-- Synthetic Generator Button (AC1) -->
      <div class="test-data-panel__synthetic-bar">
        <div class="test-data-panel__synthetic-wrapper">
          <button
            class="test-data-panel__action-btn test-data-panel__action-btn--primary test-data-panel__synthetic-btn"
            type="button"
            data-testid="generate-synthetic-btn"
            @click="toggleSyntheticDropdown"
          >
            ⚡ Gerar Sintético ▾
          </button>
          <div
            v-if="syntheticDropdownOpen"
            class="test-data-panel__synthetic-dropdown"
            data-testid="synthetic-dropdown"
          >
            <button
              v-for="opt in SYNTHETIC_SIZES"
              :key="opt.value"
              class="test-data-panel__synthetic-option"
              type="button"
              :data-testid="`synthetic-option-${opt.value}`"
              @click="generateSynthetic(opt.value)"
            >
              <span class="test-data-panel__synthetic-option-label">{{ opt.label }}</span>
              <span class="test-data-panel__synthetic-option-desc">{{ opt.description }}</span>
            </button>
          </div>
          <!-- Backdrop to close dropdown -->
          <div
            v-if="syntheticDropdownOpen"
            class="test-data-panel__synthetic-backdrop"
            @click="closeSyntheticDropdown"
          />
        </div>
      </div>

      <DatasetList
        :datasets="store.datasets"
        :active-dataset-id="store.activeDatasetId"
        @select="store.setActiveDataset"
        @delete="onDeleteDataset"
        @upload="onUploadFile"
      />
    </div>

    <div class="test-data-panel__divider" />

    <div class="test-data-panel__details">
      <!-- No dataset selected -->
      <div v-if="!store.activeDataset" class="test-data-panel__empty">
        <span>Selecione ou carregue um dataset</span>
      </div>

      <!-- Dataset details -->
      <div v-else class="test-data-panel__detail-content">
        <div class="test-data-panel__detail-header">
          <span class="test-data-panel__detail-name">{{ store.activeDataset.name }}</span>
          <span
            class="test-data-panel__status-badge"
            :class="`test-data-panel__status-badge--${store.activeDataset.status}`"
            >{{ statusIcon(store.activeDataset.status) }}
            {{ statusLabel(store.activeDataset.status) }}</span
          >
        </div>

        <!-- Stats grid (AC6) -->
        <div class="test-data-panel__stats">
          <div class="test-data-panel__stat">
            <span class="test-data-panel__stat-label">Campos</span>
            <span class="test-data-panel__stat-value">{{
              activeResult?.fieldCount ?? Object.keys(store.activeDataset.fields).length
            }}</span>
          </div>
          <div class="test-data-panel__stat">
            <span class="test-data-panel__stat-label">Loops</span>
            <span class="test-data-panel__stat-value">{{ activeResult?.loopCount ?? 0 }}</span>
          </div>
          <div class="test-data-panel__stat">
            <span class="test-data-panel__stat-label">Tamanho</span>
            <span class="test-data-panel__stat-value">{{
              formatSize(store.activeDataset.size)
            }}</span>
          </div>
          <div class="test-data-panel__stat">
            <span class="test-data-panel__stat-label">Status</span>
            <span class="test-data-panel__stat-value">{{
              statusLabel(store.activeDataset.status)
            }}</span>
          </div>
        </div>

        <!-- Errors & warnings -->
        <div
          v-if="activeResult && activeResult.errors.length > 0"
          class="test-data-panel__messages test-data-panel__messages--error"
        >
          <div class="test-data-panel__messages-title">Erros</div>
          <ul class="test-data-panel__messages-list">
            <li v-for="(err, i) in activeResult.errors" :key="i">{{ err }}</li>
          </ul>
        </div>

        <div
          v-if="activeResult && activeResult.warnings.length > 0"
          class="test-data-panel__messages test-data-panel__messages--warning"
        >
          <div class="test-data-panel__messages-title">Avisos</div>
          <ul class="test-data-panel__messages-list">
            <li v-for="(w, i) in activeResult.warnings" :key="i">{{ w }}</li>
          </ul>
        </div>

        <!-- Action buttons -->
        <div class="test-data-panel__actions">
          <button
            class="test-data-panel__action-btn test-data-panel__action-btn--primary"
            type="button"
            data-testid="apply-to-canvas-btn"
            @click="onApplyToCanvas"
          >
            Aplicar no Canvas
          </button>
          <button
            class="test-data-panel__action-btn"
            type="button"
            data-testid="edit-dataset-btn"
            @click="openEditor"
          >
            Editar Dataset...
          </button>
        </div>
      </div>
    </div>

    <!-- Monaco Editor Modal (AC8) -->
    <Teleport to="body">
      <div
        v-if="editorOpen"
        class="test-data-panel__modal-overlay"
        data-testid="dataset-editor-modal"
        @click.self="closeEditor"
      >
        <div class="test-data-panel__modal">
          <div class="test-data-panel__modal-header">
            <span class="test-data-panel__modal-title"
              >Editar Dataset: {{ store.activeDataset?.name }}</span
            >
            <button
              class="test-data-panel__modal-close"
              type="button"
              aria-label="Fechar editor"
              @click="closeEditor"
            >
              ×
            </button>
          </div>
          <div class="test-data-panel__modal-body">
            <component
              :is="MonacoEditorInner"
              v-if="MonacoEditorInner"
              :content="editorContent"
              language="json"
              @update:content="editorContent = $event"
            />
            <div v-else class="test-data-panel__editor-fallback">
              <textarea
                v-model="editorContent"
                class="test-data-panel__textarea"
                spellcheck="false"
                data-testid="dataset-editor-textarea"
              />
            </div>
          </div>
          <div class="test-data-panel__modal-footer">
            <button class="test-data-panel__action-btn" type="button" @click="closeEditor">
              Cancelar
            </button>
            <button
              class="test-data-panel__action-btn test-data-panel__action-btn--primary"
              type="button"
              data-testid="save-dataset-btn"
              @click="saveEditorContent"
            >
              Salvar e Revalidar
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useTestDataStore } from '@/stores/testDataStore'
import { useMappingStore } from '@/stores/mapping'
import { parseXmlToJson } from '@/stores/testDataStore'
import DatasetList from '@/molecules/DatasetList.vue'
import type { DatasetStatus, XsdFieldDef } from '@/types/test-data.types'
import {
  generateSyntheticData,
  SYNTHETIC_NAMES,
  type SyntheticSize,
} from '@/utils/syntheticGenerator'

// ─── Stores ─────────────────────────────────────────────────────────────────
const store = useTestDataStore()
const mappingStore = useMappingStore()

// ─── Async Monaco (won't fail if not available) ───────────────────────────
// We create a lightweight single-value Monaco wrapper inline for the modal.
// Using null as fallback so tests don't need monaco.
const MonacoEditorInner = null // Fallback: use textarea. Real apps load monaco-editor async.

// ─── Active validation result ─────────────────────────────────────────────
const activeResult = computed(() =>
  store.activeDatasetId ? store.getValidationResult(store.activeDatasetId) : undefined,
)

// ─── Status helpers ──────────────────────────────────────────────────────
function statusIcon(status: DatasetStatus): string {
  switch (status) {
    case 'valid':
      return '✓'
    case 'warning':
      return '⚠'
    case 'invalid':
      return '✕'
    default:
      return '?'
  }
}

function statusLabel(status: DatasetStatus): string {
  switch (status) {
    case 'valid':
      return 'Validado'
    case 'warning':
      return 'Aviso'
    case 'invalid':
      return 'Inválido'
    default:
      return 'Não validado'
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// ─── XSD fields from mappingStore ────────────────────────────────────────
function getXsdFields(): XsdFieldDef[] {
  return mappingStore.fieldNavItems.map((item) => ({
    path: item.path,
    type: item.type === 'array' ? 'array' : item.type === 'string' ? 'string' : 'string',
    required: !item.isOptional,
  }))
}

// ─── Upload handling (AC3 + AC4) ─────────────────────────────────────────
async function onUploadFile(file: File) {
  const raw = await readFileAsText(file)
  let fields: Record<string, unknown>

  if (file.name.endsWith('.xml')) {
    fields = parseXmlToJson(raw)
  } else {
    try {
      const parsed = JSON.parse(raw)
      fields =
        typeof parsed === 'object' && parsed !== null ? (parsed as Record<string, unknown>) : {}
    } catch {
      fields = {}
    }
  }

  const id = `dataset-${Date.now()}`
  const dataset = {
    id,
    name: file.name.replace(/\.(xml|json)$/, ''),
    fields,
    rawContent: file.name.endsWith('.xml') ? JSON.stringify(fields, null, 2) : raw,
    createdAt: new Date().toISOString(),
    size: file.size,
    status: 'unvalidated' as DatasetStatus,
  }

  const added = store.addDataset(dataset)
  if (!added) return

  store.setActiveDataset(id)

  // Auto-validate against XSD (AC3)
  const xsdFields = getXsdFields()
  if (xsdFields.length > 0) {
    store.validateDataset(id, xsdFields)
  }
}

function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve((e.target?.result as string) ?? '')
    reader.onerror = reject
    reader.readAsText(file)
  })
}

// ─── Delete dataset ───────────────────────────────────────────────────────
function onDeleteDataset(id: string) {
  store.removeDataset(id)
}

// ─── Apply to Canvas (AC7) ────────────────────────────────────────────────
function onApplyToCanvas() {
  const iframes = Array.from(
    document.querySelectorAll<HTMLIFrameElement>('[data-testid="html-canvas-iframe"]'),
  )
  store.applyDatasetToCanvas(iframes)
}

// ─── Monaco Editor Modal (AC8) ────────────────────────────────────────────
const editorOpen = ref(false)
const editorContent = ref('')

function openEditor() {
  const dataset = store.activeDataset
  if (!dataset) return
  editorContent.value = dataset.rawContent
  editorOpen.value = true
}

function closeEditor() {
  editorOpen.value = false
}

// ─── Synthetic Data Generation (AC1-AC5) ─────────────────────────────────
const syntheticDropdownOpen = ref(false)

const SYNTHETIC_SIZES: Array<{ value: SyntheticSize; label: string; description: string }> = [
  { value: 'small', label: 'Pequeno', description: '1 linha por array' },
  { value: 'medium', label: 'Médio', description: '10 linhas por array' },
  { value: 'large', label: 'Grande', description: '100+ linhas por array' },
]

function toggleSyntheticDropdown() {
  syntheticDropdownOpen.value = !syntheticDropdownOpen.value
}

function closeSyntheticDropdown() {
  syntheticDropdownOpen.value = false
}

function generateSynthetic(size: SyntheticSize) {
  closeSyntheticDropdown()
  const xsdFields = getXsdFields()
  const fields = generateSyntheticData(xsdFields, size)
  const name = SYNTHETIC_NAMES[size]
  const rawContent = JSON.stringify(fields, null, 2)

  // Remove existing dataset with same name first
  const existing = store.datasets.find((d) => d.name === name)
  if (existing) {
    store.removeDataset(existing.id)
  }

  const id = `synthetic-${size}-${Date.now()}`
  const dataset = {
    id,
    name,
    fields,
    rawContent,
    createdAt: new Date().toISOString(),
    size: new Blob([rawContent]).size,
    status: 'unvalidated' as DatasetStatus,
  }

  store.addDataset(dataset)
  store.setActiveDataset(id)

  // Auto-validate
  if (xsdFields.length > 0) {
    store.validateDataset(id, xsdFields)
  }
}

function saveEditorContent() {
  const dataset = store.activeDataset
  if (!dataset) return

  let fields: Record<string, unknown>
  try {
    const parsed = JSON.parse(editorContent.value)
    fields =
      typeof parsed === 'object' && parsed !== null ? (parsed as Record<string, unknown>) : {}
  } catch {
    // Invalid JSON — still save raw content but keep old fields
    fields = dataset.fields
  }

  store.updateDataset(dataset.id, {
    fields,
    rawContent: editorContent.value,
    size: new Blob([editorContent.value]).size,
    status: 'unvalidated',
  })

  // Re-validate after save
  const xsdFields = getXsdFields()
  if (xsdFields.length > 0) {
    store.validateDataset(dataset.id, xsdFields)
  }

  closeEditor()
}
</script>

<style scoped>
.test-data-panel {
  display: flex;
  height: 100%;
  overflow: hidden;
  background: var(--color-neutral-800, #1f2937);
  color: var(--color-neutral-100, #f3f4f6);
}

/* List: 30% */
.test-data-panel__list {
  width: 30%;
  min-width: 140px;
  flex-shrink: 0;
  overflow: hidden;
  border-right: 1px solid var(--color-neutral-700, #374151);
  display: flex;
  flex-direction: column;
}

.test-data-panel__divider {
  display: none;
}

/* Details: 70% */
.test-data-panel__details {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
}

.test-data-panel__empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8125rem;
  color: var(--color-neutral-500, #525252);
}

/* Detail content */
.test-data-panel__detail-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.test-data-panel__detail-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.test-data-panel__detail-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-neutral-100, #f3f4f6);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.test-data-panel__status-badge {
  flex-shrink: 0;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
}

.test-data-panel__status-badge--valid {
  background: var(--color-success-900, #14532d);
  color: var(--color-success-300, #86efac);
}

.test-data-panel__status-badge--warning {
  background: var(--color-warning-900, #78350f);
  color: var(--color-warning-300, #fcd34d);
}

.test-data-panel__status-badge--invalid {
  background: var(--color-error-900, #7f1d1d);
  color: var(--color-error-300, #fca5a5);
}

.test-data-panel__status-badge--unvalidated {
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-400, #9ca3af);
}

/* Stats grid (AC6) */
.test-data-panel__stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}

.test-data-panel__stat {
  background: var(--color-neutral-900, #111827);
  border: 1px solid var(--color-neutral-700, #374151);
  border-radius: 0.25rem;
  padding: 0.375rem 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.test-data-panel__stat-label {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.test-data-panel__stat-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-neutral-100, #f3f4f6);
}

/* Messages */
.test-data-panel__messages {
  border-radius: 0.25rem;
  padding: 0.5rem;
  font-size: 0.75rem;
}

.test-data-panel__messages--error {
  background: var(--color-error-950, #450a0a);
  border: 1px solid var(--color-error-800, #991b1b);
}

.test-data-panel__messages--warning {
  background: var(--color-warning-950, #431407);
  border: 1px solid var(--color-warning-800, #92400e);
}

.test-data-panel__messages-title {
  font-weight: 600;
  margin-bottom: 0.25rem;
  color: var(--color-neutral-200, #e5e7eb);
}

.test-data-panel__messages--error .test-data-panel__messages-title {
  color: var(--color-error-300, #fca5a5);
}

.test-data-panel__messages--warning .test-data-panel__messages-title {
  color: var(--color-warning-300, #fcd34d);
}

.test-data-panel__messages-list {
  margin: 0;
  padding-left: 1rem;
  color: var(--color-neutral-300, #d1d5db);
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

/* Action buttons */
.test-data-panel__actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.test-data-panel__action-btn {
  padding: 0.375rem 0.75rem;
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-100, #f3f4f6);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.12s;
}

.test-data-panel__action-btn:hover {
  background: var(--color-neutral-600, #4b5563);
}

.test-data-panel__action-btn--primary {
  background: var(--color-primary-700, #1d4ed8);
  border-color: var(--color-primary-600, #2563eb);
  color: #fff;
}

.test-data-panel__action-btn--primary:hover {
  background: var(--color-primary-600, #2563eb);
}

/* Modal overlay */
.test-data-panel__modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.test-data-panel__modal {
  background: var(--color-neutral-900, #111827);
  border: 1px solid var(--color-neutral-700, #374151);
  border-radius: 0.5rem;
  display: flex;
  flex-direction: column;
  width: min(800px, 90vw);
  height: min(600px, 80vh);
  overflow: hidden;
}

.test-data-panel__modal-header {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--color-neutral-700, #374151);
  flex-shrink: 0;
}

.test-data-panel__modal-title {
  flex: 1;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-neutral-100, #f3f4f6);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.test-data-panel__modal-close {
  background: transparent;
  border: none;
  color: var(--color-neutral-400, #9ca3af);
  font-size: 1.25rem;
  line-height: 1;
  cursor: pointer;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  transition: color 0.12s;
  flex-shrink: 0;
}

.test-data-panel__modal-close:hover {
  color: var(--color-neutral-100, #f3f4f6);
}

.test-data-panel__modal-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.test-data-panel__editor-fallback {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.test-data-panel__textarea {
  flex: 1;
  width: 100%;
  resize: none;
  background: var(--color-neutral-950, #030712);
  color: var(--color-neutral-100, #f3f4f6);
  border: none;
  font-family: 'Fira Mono', 'Consolas', monospace;
  font-size: 0.8125rem;
  padding: 0.75rem;
  outline: none;
}

/* Synthetic Generator Bar */
.test-data-panel__synthetic-bar {
  padding: 0.375rem 0.5rem;
  border-bottom: 1px solid var(--color-neutral-700, #374151);
  flex-shrink: 0;
}

.test-data-panel__synthetic-wrapper {
  position: relative;
  display: inline-block;
  width: 100%;
}

.test-data-panel__synthetic-btn {
  width: 100%;
  font-size: 0.75rem;
  padding: 0.3125rem 0.5rem;
}

.test-data-panel__synthetic-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 200;
  background: var(--color-neutral-900, #111827);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.375rem;
  min-width: 160px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  overflow: hidden;
  margin-top: 0.125rem;
}

.test-data-panel__synthetic-backdrop {
  position: fixed;
  inset: 0;
  z-index: 199;
}

.test-data-panel__synthetic-option {
  display: flex;
  flex-direction: column;
  gap: 0.0625rem;
  width: 100%;
  padding: 0.5rem 0.75rem;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background 0.1s;
}

.test-data-panel__synthetic-option:hover {
  background: var(--color-neutral-700, #374151);
}

.test-data-panel__synthetic-option + .test-data-panel__synthetic-option {
  border-top: 1px solid var(--color-neutral-700, #374151);
}

.test-data-panel__synthetic-option-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-neutral-100, #f3f4f6);
}

.test-data-panel__synthetic-option-desc {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
}

.test-data-panel__modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--color-neutral-700, #374151);
  flex-shrink: 0;
}
</style>
