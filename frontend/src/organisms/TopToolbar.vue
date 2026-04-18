<template>
  <div class="top-toolbar">
    <!-- Left section: template name + badges + layout selector -->
    <div class="top-toolbar__left">
      <!-- Template name / document type badge -->
      <span
        class="top-toolbar__template-name"
        :title="
          templateStore.documentType ? `Tipo detectado: ${templateStore.documentType}` : undefined
        "
      >
        {{ sessionStore.template_name ?? formatDocType(templateStore.documentType) }}
      </span>

      <span class="top-toolbar__separator" aria-hidden="true">│</span>

      <!-- Confidence badge + popover -->
      <div ref="confidenceWrapperRef" class="top-toolbar__badge-wrapper">
        <ConfidenceBadgeMetric
          :percentage="confidenceStore.overallForActiveLayout"
          @click="onConfidenceBadgeClick"
        />
        <ConfidencePopover
          :visible="showConfidencePopover"
          @close="showConfidencePopover = false"
        />
      </div>

      <span class="top-toolbar__separator" aria-hidden="true">│</span>

      <!-- Coverage badge + popover -->
      <div ref="coverageWrapperRef" class="top-toolbar__badge-wrapper">
        <CoverageBadge
          :percentage="coveragePct"
          :breakdown="coverageBreakdown"
          @click="onCoverageBadgeClick"
        />
        <CoveragePopover :visible="showCoveragePopover" @close="showCoveragePopover = false" />
      </div>

      <!-- Layout selector (hidden when only 1 layout) -->
      <span
        v-if="layoutStore.layoutTypes.length > 1"
        class="top-toolbar__separator"
        aria-hidden="true"
        >│</span
      >
      <LayoutSelector />
    </div>

    <!-- Right section: toggle buttons + action buttons -->
    <div class="top-toolbar__right">
      <!-- Toggle buttons -->
      <div class="top-toolbar__toggles" role="group" aria-label="Ferramentas">
        <ToggleButton
          :icon="MapIcon"
          label="Cobertura"
          :active="editorStore.coverageMode"
          @click="editorStore.toggleCoverage()"
        />
        <ToggleButton
          :icon="ArrowLeftRight"
          label="Diff"
          :active="diffStore.isActive"
          @click="onToggleDiff()"
        />
        <ToggleButton
          :icon="Magnet"
          label="Snap"
          :active="editorStore.snapEnabled"
          @click="editorStore.toggleSnap()"
        />
        <ToggleButton
          :icon="Ruler"
          label="Guias"
          :active="editorStore.showGuides"
          @click="editorStore.toggleGuides()"
        />
        <button
          type="button"
          class="top-toolbar__autofix-btn"
          :disabled="autoFixStore.isLimitReached || autoFixStore.isRunning"
          :title="
            autoFixStore.isLimitReached ? 'Limite de Auto Fix atingido nesta sessão' : 'Auto Fix IA'
          "
          data-testid="btn-auto-fix"
          @click="autoFixStore.runAutoFix()"
        >
          <Wrench :size="14" :stroke-width="2" /> Auto Fix
        </button>
      </div>

      <span class="top-toolbar__separator" aria-hidden="true">│</span>

      <!-- Action buttons -->
      <div class="top-toolbar__actions">
        <button
          type="button"
          class="top-toolbar__action-btn"
          aria-label="Abrir projeto"
          @click="onOpen"
        >
          <FolderOpen :size="14" :stroke-width="2" /> Abrir
        </button>
        <button type="button" class="top-toolbar__action-btn" aria-label="Salvar" @click="onSave">
          <Save :size="14" :stroke-width="2" /> Salvar
        </button>
        <button
          type="button"
          class="top-toolbar__action-btn top-toolbar__action-btn--export"
          :disabled="isExporting"
          aria-label="Exportar"
          @click="onExport"
        >
          <Loader2 v-if="isExporting" :size="14" :stroke-width="2" class="top-toolbar__spinner" />
          <Package v-else :size="14" :stroke-width="2" />
          {{ isExporting ? 'Exportando…' : 'Exportar' }}
        </button>
      </div>
    </div>
  </div>

  <!-- AC3: Export options modal (shown only when datasets exist) -->
  <div
    v-if="showExportModal"
    class="top-toolbar__modal-backdrop"
    role="dialog"
    aria-modal="true"
    aria-labelledby="export-modal-title"
  >
    <div class="top-toolbar__modal">
      <h3 id="export-modal-title" class="top-toolbar__modal-title">Exportar Template</h3>
      <label class="top-toolbar__modal-option">
        <input v-model="includeTestData" type="checkbox" class="top-toolbar__modal-checkbox" />
        Incluir datasets de teste
      </label>
      <div class="top-toolbar__modal-actions">
        <button type="button" class="top-toolbar__action-btn" @click="showExportModal = false">
          Cancelar
        </button>
        <button
          type="button"
          class="top-toolbar__action-btn top-toolbar__action-btn--export"
          @click="runExport(includeTestData)"
        >
          <Package :size="14" :stroke-width="2" /> Exportar ZIP
        </button>
      </div>
    </div>
  </div>

  <!-- AC11: Pre-export validation modal -->
  <ExportValidationModal
    :visible="showValidationModal"
    :blocking-errors="validationBlockingErrors"
    :warnings="validationWarnings"
    @confirm="onValidationConfirm"
    @cancel="onValidationCancel"
  />
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useConfidenceStore } from '@/stores/confidenceStore'
import { useCoverageStore } from '@/stores/coverageStore'
import { useLayoutStore } from '@/stores/layout'
import { useEditorStore } from '@/stores/editorStore'
import { useTemplateStore } from '@/stores/templateStore'
import { useAutoFixStore } from '@/stores/autoFixStore'
import { useMappingStore } from '@/stores/mapping'
import { useDiffStore } from '@/stores/diffStore'
import { useTestDataStore } from '@/stores/testDataStore'
import JSZip from 'jszip'
import { useCodeStore } from '@/stores/codeStore'
import { useExport, downloadJson, downloadBlob } from '@/composables/useExport'
import type { SavedProjectV2 } from '@/types'
import {
  collectAssetsFromTree,
  buildAssetReferences,
  restoreAssetsIntoTree,
} from '@/utils/zipAssetUtils'
import type { PreExportError } from '@/composables/usePreExportValidation'
import {
  Map as MapIcon,
  ArrowLeftRight,
  Magnet,
  Ruler,
  Wrench,
  FolderOpen,
  Save,
  Package,
  Loader2,
} from 'lucide-vue-next'
import ConfidenceBadgeMetric from '@/molecules/ConfidenceBadgeMetric.vue'
import CoverageBadge from '@/molecules/CoverageBadge.vue'
import LayoutSelector from '@/molecules/LayoutSelector.vue'
import ToggleButton from '@/atoms/ToggleButton.vue'
import ConfidencePopover from '@/organisms/ConfidencePopover.vue'
import CoveragePopover from '@/organisms/CoveragePopover.vue'
import ExportValidationModal from '@/molecules/ExportValidationModal.vue'

const sessionStore = useSessionStore()
const confidenceStore = useConfidenceStore()
const coverageStore = useCoverageStore()
const layoutStore = useLayoutStore()
const editorStore = useEditorStore()
const templateStore = useTemplateStore()
const mappingStore = useMappingStore()
const testDataStore = useTestDataStore()
const codeStore = useCodeStore()
const autoFixStore = useAutoFixStore()
const diffStore = useDiffStore()

const DOC_TYPE_LABELS: Record<string, string> = {
  'boleto-bancario': 'Boleto Bancário',
  'nota-fiscal': 'Nota Fiscal',
  recibo: 'Recibo',
  'documento-geral': 'Documento Geral',
}

function formatDocType(type: string | null): string {
  if (!type) return 'Sem template'
  return DOC_TYPE_LABELS[type] ?? type
}

function onToggleDiff() {
  diffStore.toggleDiffMode()
  // Keep editorStore in sync for save/restore purposes
  editorStore.diffMode = diffStore.isActive
}

const coveragePct = computed(() => coverageStore.activeLayoutCoverage?.percentage)
const coverageBreakdown = computed(() => coverageStore.activeLayoutCoverage)
const hasDatasets = computed(() => testDataStore.datasets.length > 0)

// ─── Export composable ──────────────────────────────────────────────────────
const { exportZip, isExporting, lastValidation } = useExport()

// ─── Export options modal state ────────────────────────────────────────────
const showExportModal = ref(false)
const includeTestData = ref(false)

// ─── Validation modal state (AC11) ─────────────────────────────────────────
const showValidationModal = ref(false)
const validationBlockingErrors = ref<PreExportError[]>([])
const validationWarnings = ref<PreExportError[]>([])
/** Stored export options to use when user confirms despite warnings */
let pendingExportOptions: { withTestData: boolean } | null = null

// ─── Popover state ─────────────────────────────────────────────────────────
const showConfidencePopover = ref(false)
const showCoveragePopover = ref(false)

function onConfidenceBadgeClick() {
  showCoveragePopover.value = false
  showConfidencePopover.value = !showConfidencePopover.value
}

function onCoverageBadgeClick() {
  showConfidencePopover.value = false
  showCoveragePopover.value = !showCoveragePopover.value
}

// ─── Open action (Story 36.4: accepts .json legacy and .zip v3.0) ──────────
const fileInput = ref<HTMLInputElement | null>(null)

async function onOpen() {
  // Create a hidden file input to select .json or .zip
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json,.zip'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) return

    try {
      if (file.name.endsWith('.zip')) {
        // Story 36.4: Open .zip format
        const zip = await JSZip.loadAsync(file)
        const projectJsonFile = zip.file('project.json')
        if (!projectJsonFile) {
          alert('ZIP invalido: project.json nao encontrado')
          return
        }
        const jsonStr = await projectJsonFile.async('string')
        const data = JSON.parse(jsonStr) as import('@/types').SavedProjectV2

        // Story 36.6: Read asset files from assets/ folder before loading project
        const assetFiles = new Map<string, Uint8Array>()
        const assetsPrefix = 'assets/'
        const assetEntries = zip.file(new RegExp(`^${assetsPrefix}.+`))
        for (const entry of assetEntries) {
          const filename = entry.name.replace(assetsPrefix, '')
          if (filename && filename !== '.gitkeep') {
            const bytes = await entry.async('uint8array')
            assetFiles.set(filename, bytes)
          }
        }

        await sessionStore.loadFromSavedProject(data)

        // Story 36.6: Restore data URIs into tree image nodes after load
        if (assetFiles.size > 0 && templateStore.documentTree) {
          restoreAssetsIntoTree(templateStore.documentTree, assetFiles, data.assetReferences)
        }
      } else {
        // Legacy .json format
        const text = await file.text()
        const data = JSON.parse(text) as import('@/types').SavedProjectV2
        await sessionStore.loadFromSavedProject(data)
      }
    } catch (err) {
      alert(`Erro ao abrir projeto: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      // Story 36.7 Fix 1: Remove ephemeral input element to prevent DOM leak
      input.remove()
    }
  }
  input.click()
}

// ─── Save action (AC4, AC5) ─────────────────────────────────────────────────
async function onSave() {
  // Build confidence map (Record<string, ConfidenceFactors>)
  const confidenceRecord: Record<string, import('@/types/confidence.types').ConfidenceFactors> = {}
  for (const [layoutId, factors] of confidenceStore.confidenceByLayout.entries()) {
    confidenceRecord[layoutId] = factors
  }

  // Build coverage map
  const coverageRecord: Record<string, import('@/types/coverage.types').CoverageData> = {}
  for (const [layoutId, cov] of coverageStore.coverageByLayout.entries()) {
    coverageRecord[layoutId] = cov
  }

  // Serialize fieldMappings as FieldMappingEntry[] from mappingStore.fields
  const fieldMappings: import('@/types/pipeline.types').FieldMappingEntry[] =
    mappingStore.fields.map((f) => ({
      name: f.pdfText,
      path: f.jsonPath,
      type: f.type,
      status: (() => {
        switch (f.status) {
          case 'ok':
            return 'mapped' as const
          case 'ambiguous':
            return 'ambiguous' as const
          case 'optional':
            return 'optional' as const
          default:
            return 'unmapped' as const
        }
      })(),
      isOptional: f.status === 'optional',
    }))

  const savedProject: SavedProjectV2 = {
    version: '2.1',
    savedAt: new Date().toISOString(),
    templateName: sessionStore.template_name,
    documentTree: templateStore.documentTree,
    fieldMappings,
    editorState: {
      activeCenterTab: editorStore.activeCenterTab,
      activeLeftTab: editorStore.activeLeftTab,
      zoomLevel: editorStore.zoomLevel,
      selectedElementId: editorStore.selectedElementId,
      activeSidebarTab: editorStore.activeSidebarTab,
      pdfZoom: editorStore.pdfZoom,
      toggles: {
        coverageMode: editorStore.coverageMode,
        diffMode: editorStore.diffMode,
        snapEnabled: editorStore.snapEnabled,
        autoFixEnabled: editorStore.autoFixEnabled,
        showGuides: editorStore.showGuides,
      },
    },
    layoutTypes: layoutStore.layoutTypes,
    activeLayoutId: layoutStore.activeLayoutId,
    confidence: confidenceRecord,
    coverage: coverageRecord,
    // Story 36.3: include code files, test datasets, XSD paths, asset refs
    codeFiles: {
      html: codeStore.fileContents.html,
      css: codeStore.fileContents.css,
      js: codeStore.fileContents.js,
    },
    testDatasets: testDataStore.datasets.length > 0 ? [...testDataStore.datasets] : undefined,
    xsdFlatPaths: mappingStore.flatPaths.length > 0 ? [...mappingStore.flatPaths] : undefined,
    assetReferences: undefined, // Populated below when assets exist (Story 36.6)
  }

  // Story 36.6: Collect real assets from document tree image nodes
  const collectedAssets = collectAssetsFromTree(templateStore.documentTree)
  savedProject.assetReferences = buildAssetReferences(collectedAssets)

  const templateName = sessionStore.template_name ?? 'projeto'

  // Story 36.4: Save as .zip with project.json + assets/
  const zip = new JSZip()
  zip.file('project.json', JSON.stringify(savedProject, null, 2))

  // Story 36.6: Write real asset binaries into assets/ folder
  const assetsFolder = zip.folder('assets')!
  if (collectedAssets.length > 0) {
    for (const asset of collectedAssets) {
      assetsFolder.file(asset.filename, asset.data)
    }
  } else {
    assetsFolder.file('.gitkeep', '')
  }

  const blob = await zip.generateAsync({ type: 'blob' })
  downloadBlob(blob, `${templateName}.projeto.zip`)
}

// ─── Export action (AC1–AC3, AC8) ──────────────────────────────────────────
function onExport() {
  if (hasDatasets.value) {
    // AC3: show modal so user can choose whether to include datasets
    showExportModal.value = true
    includeTestData.value = false
  } else {
    runExport(false)
  }
}

async function runExport(withTestData: boolean) {
  showExportModal.value = false
  const result = await exportZip({ includeTestData: withTestData })

  if (result.success) return

  if (result.blockingErrors && result.blockingErrors.length > 0) {
    // AC7: Show validation modal with blocking errors
    validationBlockingErrors.value = lastValidation.value?.errors ?? []
    validationWarnings.value = lastValidation.value?.warnings ?? []
    showValidationModal.value = true
    return
  }

  if (result.hasWarnings) {
    // AC8: Show validation modal with warnings only — user can proceed
    validationBlockingErrors.value = []
    validationWarnings.value = lastValidation.value?.warnings ?? []
    pendingExportOptions = { withTestData }
    showValidationModal.value = true
  }
}

/** User confirmed export despite warnings */
async function onValidationConfirm() {
  showValidationModal.value = false
  if (pendingExportOptions !== null) {
    await exportZip({
      includeTestData: pendingExportOptions.withTestData,
      skipWarnings: true,
    })
    pendingExportOptions = null
  }
}

/** User cancelled — close modal */
function onValidationCancel() {
  showValidationModal.value = false
  pendingExportOptions = null
}
</script>

<style scoped>
.top-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 3.25rem;
  padding: 0 1rem;
  background: var(--color-neutral-900, #111827);
  color: var(--color-neutral-100, #f3f4f6);
  gap: 0.75rem;
  overflow: hidden;
}

.top-toolbar__left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
  overflow: hidden;
}

.top-toolbar__right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
}

.top-toolbar__template-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-neutral-100, #f3f4f6);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.top-toolbar__separator {
  color: var(--color-neutral-600, #4b5563);
  font-size: 0.875rem;
  flex-shrink: 0;
}

.top-toolbar__badge-wrapper {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.top-toolbar__toggles {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.top-toolbar__actions {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.top-toolbar__action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.3125rem 0.75rem;
  background: var(--color-neutral-700, #374151);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.375rem;
  cursor: pointer;
  color: var(--color-neutral-100, #f3f4f6);
  font-size: 0.8125rem;
  font-weight: 500;
  white-space: nowrap;
  transition: background 0.15s;
}

.top-toolbar__action-btn:hover {
  background: var(--color-neutral-600, #4b5563);
}

.top-toolbar__action-btn--export {
  background: var(--color-primary-700, #1d4ed8);
  border-color: var(--color-primary-600, #2563eb);
}

.top-toolbar__action-btn--export:hover {
  background: var(--color-primary-600, #2563eb);
}

.top-toolbar__modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.top-toolbar__modal {
  background: var(--color-neutral-900, #111827);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.5rem;
  padding: 1.5rem;
  min-width: 20rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  color: var(--color-neutral-100, #f3f4f6);
}

.top-toolbar__modal-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.top-toolbar__modal-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  cursor: pointer;
}

.top-toolbar__modal-checkbox {
  cursor: pointer;
}

.top-toolbar__modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.top-toolbar__spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.top-toolbar__autofix-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.625rem;
  border-radius: 0.375rem;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--color-neutral-600, #4b5563);
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-100, #f3f4f6);
  transition:
    background 0.15s,
    opacity 0.15s;
}

.top-toolbar__autofix-btn:hover:not(:disabled) {
  background: var(--color-neutral-600, #4b5563);
}

.top-toolbar__autofix-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
