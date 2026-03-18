<template>
  <div class="top-toolbar">
    <!-- Left section: template name + badges + layout selector -->
    <div class="top-toolbar__left">
      <!-- Template name -->
      <span class="top-toolbar__template-name">
        {{ sessionStore.template_name ?? 'Sem template' }}
      </span>

      <span class="top-toolbar__separator" aria-hidden="true">│</span>

      <!-- Confidence badge + popover -->
      <div class="top-toolbar__badge-wrapper" ref="confidenceWrapperRef">
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
      <div class="top-toolbar__badge-wrapper" ref="coverageWrapperRef">
        <CoverageBadge
          :percentage="coveragePct"
          @click="onCoverageBadgeClick"
        />
        <CoveragePopover
          :visible="showCoveragePopover"
          @close="showCoveragePopover = false"
        />
      </div>

      <!-- Layout selector (hidden when only 1 layout) -->
      <span
        v-if="layoutStore.layoutTypes.length > 1"
        class="top-toolbar__separator"
        aria-hidden="true"
      >│</span>
      <LayoutSelector />
    </div>

    <!-- Right section: toggle buttons + action buttons -->
    <div class="top-toolbar__right">
      <!-- Toggle buttons -->
      <div class="top-toolbar__toggles" role="group" aria-label="Ferramentas">
        <ToggleButton
          icon="🗺️"
          label="Cobertura"
          :active="editorStore.coverageMode"
          @click="editorStore.toggleCoverage()"
        />
        <ToggleButton
          icon="🔀"
          label="Diff"
          :active="editorStore.diffMode"
          @click="editorStore.toggleDiff()"
        />
        <ToggleButton
          icon="🧲"
          label="Snap"
          :active="editorStore.snapEnabled"
          @click="editorStore.toggleSnap()"
        />
        <ToggleButton
          icon="🔧"
          label="Auto Fix"
          :active="editorStore.autoFixEnabled"
          @click="editorStore.toggleAutoFix()"
        />
      </div>

      <span class="top-toolbar__separator" aria-hidden="true">│</span>

      <!-- Action buttons -->
      <div class="top-toolbar__actions">
        <button
          type="button"
          class="top-toolbar__action-btn"
          aria-label="Salvar"
          @click="onSave"
        >
          💾 Salvar
        </button>
        <button
          type="button"
          class="top-toolbar__action-btn top-toolbar__action-btn--export"
          :disabled="isExporting"
          aria-label="Exportar"
          @click="onExport"
        >
          📦 {{ isExporting ? 'Exportando…' : 'Exportar' }}
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
        <input
          v-model="includeTestData"
          type="checkbox"
          class="top-toolbar__modal-checkbox"
        />
        Incluir datasets de teste
      </label>
      <div class="top-toolbar__modal-actions">
        <button
          type="button"
          class="top-toolbar__action-btn"
          @click="showExportModal = false"
        >
          Cancelar
        </button>
        <button
          type="button"
          class="top-toolbar__action-btn top-toolbar__action-btn--export"
          @click="runExport(includeTestData)"
        >
          📦 Exportar ZIP
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useConfidenceStore } from '@/stores/confidenceStore'
import { useCoverageStore } from '@/stores/coverageStore'
import { useLayoutStore } from '@/stores/layout'
import { useEditorStore } from '@/stores/editorStore'
import { useTemplateStore } from '@/stores/templateStore'
import { useMappingStore } from '@/stores/mapping'
import { useTestDataStore } from '@/stores/testDataStore'
import { useExport, downloadJson } from '@/composables/useExport'
import type { SavedProjectV2 } from '@/types'
import ConfidenceBadgeMetric from '@/molecules/ConfidenceBadgeMetric.vue'
import CoverageBadge from '@/molecules/CoverageBadge.vue'
import LayoutSelector from '@/molecules/LayoutSelector.vue'
import ToggleButton from '@/atoms/ToggleButton.vue'
import ConfidencePopover from '@/organisms/ConfidencePopover.vue'
import CoveragePopover from '@/organisms/CoveragePopover.vue'

const sessionStore = useSessionStore()
const confidenceStore = useConfidenceStore()
const coverageStore = useCoverageStore()
const layoutStore = useLayoutStore()
const editorStore = useEditorStore()
const templateStore = useTemplateStore()
const mappingStore = useMappingStore()
const testDataStore = useTestDataStore()

const coveragePct = computed(() => coverageStore.activeLayoutCoverage?.percentage)
const hasDatasets = computed(() => testDataStore.datasets.length > 0)

// ─── Export composable ──────────────────────────────────────────────────────
const { exportZip, isExporting } = useExport()

// ─── Export options modal state ────────────────────────────────────────────
const showExportModal = ref(false)
const includeTestData = ref(false)

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

// ─── Save action (AC4, AC5) ─────────────────────────────────────────────────
function onSave() {
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
  const fieldMappings: import('@/types/pipeline.types').FieldMappingEntry[] = mappingStore.fields.map(
    (f) => ({
      name: f.pdfText,
      path: f.jsonPath,
      type: f.type,
      status: (() => {
        switch (f.status) {
          case 'ok': return 'mapped' as const
          case 'ambiguous': return 'ambiguous' as const
          case 'optional': return 'optional' as const
          default: return 'unmapped' as const
        }
      })(),
      isOptional: f.status === 'optional',
    }),
  )

  const savedProject: SavedProjectV2 = {
    version: '2.0',
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
  }

  const templateName = sessionStore.template_name ?? 'projeto'
  downloadJson(savedProject, `${templateName}.projeto.json`)
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
  await exportZip({ includeTestData: withTestData })
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
</style>
