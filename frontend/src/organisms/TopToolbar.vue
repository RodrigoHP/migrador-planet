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
          aria-label="Exportar"
          @click="onExport"
        >
          📦 Exportar
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

const coveragePct = computed(() => coverageStore.activeLayoutCoverage?.percentage)

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

function onSave() {
  // Functional in Epic 8
  console.log('[TopToolbar] save placeholder')
}

function onExport() {
  // Functional in Epic 8
  console.log('[TopToolbar] export placeholder')
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
</style>
