<template>
  <div class="editor-layout" :style="layoutStyle">
    <!-- Toolbar -->
    <header class="editor-layout__toolbar" style="grid-area: toolbar">
      <TopToolbar />
    </header>

    <!-- Left Panel -->
    <aside class="editor-layout__left" style="grid-area: left-panel" :style="{ width: leftPanelWidth + 'px' }">
      <LeftPanel />
    </aside>

    <!-- Resize handle: left | center -->
    <ResizableHandle
      class="editor-layout__handle editor-layout__handle--vertical"
      style="grid-area: left-panel; justify-self: end; z-index: 10"
      direction="horizontal"
      @resize="onLeftResize"
    />

    <!-- Center Panel -->
    <main class="editor-layout__center" style="grid-area: center-panel">
      <CenterPanel />
    </main>

    <!-- Resize handle: center | inspector -->
    <ResizableHandle
      class="editor-layout__handle editor-layout__handle--vertical"
      style="grid-area: inspector; justify-self: start; z-index: 10"
      direction="horizontal"
      @resize="onInspectorResize"
    />

    <!-- Inspector -->
    <aside class="editor-layout__inspector" style="grid-area: inspector" :style="{ width: inspectorWidth + 'px' }">
      <InspectorPanel />
    </aside>

    <!-- MultiDoc Analyzer — AC #1/#2: between center panel and bottom panel -->
    <section
      v-if="multiDocStore.hasMultiplePdfs"
      class="editor-layout__multidoc"
      style="grid-area: multidoc-panel"
    >
      <MultiDocAnalyzer />
    </section>

    <!-- Bottom Panel -->
    <section
      class="editor-layout__bottom"
      style="grid-area: bottom-panel"
      :class="{ 'editor-layout__bottom--collapsed': bottomCollapsed }"
    >
      <div class="editor-layout__bottom-header">
        <button
          class="editor-layout__bottom-toggle"
          type="button"
          :aria-label="bottomCollapsed ? 'Expandir painel inferior' : 'Colapsar painel inferior'"
          @click="toggleBottom"
        >
          <span class="editor-layout__chevron" :class="bottomCollapsed ? 'editor-layout__chevron--up' : 'editor-layout__chevron--down'">
            {{ bottomCollapsed ? '▲' : '▼' }}
          </span>
          <span class="editor-layout__bottom-label">Painel Inferior</span>
        </button>

        <!-- Bottom tabs -->
        <nav v-if="!bottomCollapsed" class="editor-layout__bottom-tabs" role="tablist" aria-label="Abas do painel inferior">
          <button
            v-for="tab in bottomTabs"
            :key="tab.id"
            role="tab"
            type="button"
            :aria-selected="activeBottomTab === tab.id"
            :class="['editor-layout__bottom-tab', activeBottomTab === tab.id && 'editor-layout__bottom-tab--active']"
            @click="activeBottomTab = tab.id"
          >
            {{ tab.label }}
          </button>
        </nav>
      </div>
      <div v-if="!bottomCollapsed" class="editor-layout__bottom-content">
        <template v-if="activeBottomTab === 'test-data'">
          <TestDataPanel class="editor-layout__bottom-fill" />
        </template>
        <template v-else-if="activeBottomTab === 'report'">
          <TestReportPanel class="editor-layout__bottom-fill" />
        </template>
        <template v-else>
          <span class="editor-layout__placeholder-text">{{ activeBottomTabLabel }}</span>
        </template>
      </div>
    </section>

    <!-- Resize handle: main | bottom -->
    <ResizableHandle
      v-if="!bottomCollapsed"
      class="editor-layout__handle editor-layout__handle--horizontal"
      style="grid-area: bottom-panel; align-self: start; z-index: 10"
      direction="vertical"
      @resize="onBottomResize"
    />
  </div>

  <!-- Auto Fix Panel (Teleport modal — AC #1, #3, #4) -->
  <AutoFixPanel />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import TopToolbar from '@/organisms/TopToolbar.vue'
import LeftPanel from '@/organisms/LeftPanel.vue'
import CenterPanel from '@/organisms/CenterPanel.vue'
import ResizableHandle from '@/atoms/ResizableHandle.vue'
import InspectorPanel from '@/organisms/InspectorPanel.vue'
import TestDataPanel from '@/organisms/TestDataPanel.vue'
import TestReportPanel from '@/organisms/TestReportPanel.vue'
import MultiDocAnalyzer from '@/organisms/MultiDocAnalyzer.vue'
import AutoFixPanel from '@/organisms/AutoFixPanel.vue'
import { useTemplateStore } from '@/stores/templateStore'
import { useMultiDocStore } from '@/stores/multiDocStore'

// ─── Template Store (for undo) ────────────────────────────────────────────────
const templateStore = useTemplateStore()

// ─── MultiDoc Store (for conditional MultiDocAnalyzer visibility) ─────────────
const multiDocStore = useMultiDocStore()

// ─── Global Ctrl+Z listener ───────────────────────────────────────────────────
function handleKeyDown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key === 'z' && !event.shiftKey) {
    event.preventDefault()
    templateStore.undoLastAction()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
})

// ─── Panel Sizes ──────────────────────────────────────────────────────────────
const LEFT_MIN = 180
const LEFT_MAX = 400
const LEFT_DEFAULT = 250

const INSPECTOR_MIN = 200
const INSPECTOR_MAX = 450
const INSPECTOR_DEFAULT = 280

const BOTTOM_MIN = 100
const BOTTOM_MAX = 400
const BOTTOM_DEFAULT = 200

const leftPanelWidth = ref(LEFT_DEFAULT)
const inspectorWidth = ref(INSPECTOR_DEFAULT)
const bottomPanelHeight = ref(BOTTOM_DEFAULT)
const bottomCollapsed = ref(false)

// ─── Bottom Tabs ──────────────────────────────────────────────────────────────
type BottomTab = 'test-data' | 'report' | 'console'

const bottomTabs: Array<{ id: BottomTab; label: string }> = [
  { id: 'test-data', label: 'Dados de Teste' },
  { id: 'report', label: 'Report' },
  { id: 'console', label: 'Console' },
]
const activeBottomTab = ref<BottomTab>('test-data')
const activeBottomTabLabel = computed(
  () => bottomTabs.find((t) => t.id === activeBottomTab.value)?.label ?? '',
)

// ─── Layout Style ─────────────────────────────────────────────────────────────
const layoutStyle = computed(() => ({
  '--left-panel-width': `${leftPanelWidth.value}px`,
  '--inspector-width': `${inspectorWidth.value}px`,
  '--bottom-panel-height': bottomCollapsed.value ? '2.5rem' : `${bottomPanelHeight.value}px`,
}))

// ─── Resize Handlers ──────────────────────────────────────────────────────────
function onLeftResize(delta: number) {
  leftPanelWidth.value = Math.min(LEFT_MAX, Math.max(LEFT_MIN, leftPanelWidth.value + delta))
}

function onInspectorResize(delta: number) {
  inspectorWidth.value = Math.min(INSPECTOR_MAX, Math.max(INSPECTOR_MIN, inspectorWidth.value - delta))
}

function onBottomResize(delta: number) {
  bottomPanelHeight.value = Math.min(BOTTOM_MAX, Math.max(BOTTOM_MIN, bottomPanelHeight.value - delta))
}

function toggleBottom() {
  bottomCollapsed.value = !bottomCollapsed.value
}
</script>

<style scoped>
.editor-layout {
  display: grid;
  grid-template-areas:
    "toolbar toolbar toolbar"
    "left-panel center-panel inspector"
    "multidoc-panel multidoc-panel multidoc-panel"
    "bottom-panel bottom-panel bottom-panel";
  grid-template-columns: var(--left-panel-width) 1fr var(--inspector-width);
  grid-template-rows: auto 1fr auto var(--bottom-panel-height);
  height: 100vh;
  min-width: 1200px;
  overflow: hidden;
  background: var(--color-neutral-50, #f9fafb);
}

/* Toolbar */
.editor-layout__toolbar {
  background: var(--color-neutral-900, #111827);
  border-bottom: 1px solid var(--color-neutral-700, #374151);
  overflow: hidden;
}

/* Left Panel */
.editor-layout__left {
  background: var(--color-neutral-800, #1f2937);
  border-right: 1px solid var(--color-neutral-700, #374151);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-width: 180px;
  max-width: 400px;
  position: relative;
}

/* Center Panel */
.editor-layout__center {
  background: var(--color-neutral-100, #f3f4f6);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* Inspector */
.editor-layout__inspector {
  background: var(--color-neutral-800, #1f2937);
  border-left: 1px solid var(--color-neutral-700, #374151);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-width: 200px;
  max-width: 450px;
  position: relative;
}

.editor-layout__inspector-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 0.25rem;
}

/* MultiDoc Analyzer Panel */
.editor-layout__multidoc {
  grid-area: multidoc-panel;
  overflow: hidden;
}

/* Bottom Panel */
.editor-layout__bottom {
  background: var(--color-neutral-800, #1f2937);
  border-top: 1px solid var(--color-neutral-700, #374151);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: height 0.2s ease;
}

.editor-layout__bottom--collapsed {
  overflow: hidden;
}

.editor-layout__bottom-header {
  display: flex;
  align-items: center;
  height: 2.5rem;
  padding: 0 0.5rem 0 1rem;
  border-bottom: 1px solid var(--color-neutral-700, #374151);
  flex-shrink: 0;
  gap: 0.5rem;
}

.editor-layout__bottom-tabs {
  display: flex;
  gap: 0.125rem;
  height: 100%;
  align-items: stretch;
}

.editor-layout__bottom-tab {
  display: flex;
  align-items: center;
  padding: 0 0.75rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-neutral-400, #9ca3af);
  transition: color 0.12s, border-color 0.12s;
  white-space: nowrap;
}

.editor-layout__bottom-tab:hover {
  color: var(--color-neutral-200, #e5e7eb);
}

.editor-layout__bottom-tab--active {
  color: var(--color-primary-400, #60a5fa);
  border-bottom-color: var(--color-primary-400, #60a5fa);
}

.editor-layout__bottom-fill {
  width: 100%;
  height: 100%;
}

.editor-layout__bottom-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-neutral-300, #d1d5db);
  font-size: 0.8125rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  transition: background 0.15s;
}

.editor-layout__bottom-toggle:hover {
  background: var(--color-neutral-700, #374151);
}

.editor-layout__bottom-label {
  font-weight: 500;
}

.editor-layout__chevron {
  font-size: 0.625rem;
}

.editor-layout__bottom-content {
  flex: 1;
  display: flex;
  align-items: stretch;
  overflow: hidden;
}

/* Placeholder text */
.editor-layout__placeholder-text {
  margin: auto;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-neutral-400, #9ca3af);
}

.editor-layout__placeholder-sub {
  font-size: 0.75rem;
  color: var(--color-neutral-500, #6b7280);
}

/* Resize Handles */
.editor-layout__handle {
  position: relative;
}

.editor-layout__handle--vertical {
  width: 4px;
  cursor: col-resize;
}

.editor-layout__handle--horizontal {
  height: 4px;
  cursor: row-resize;
}

/* Responsiveness: panels collapse to icons at threshold */
@media (max-width: 1400px) {
  .editor-layout {
    --left-panel-width: 48px;
  }
  .editor-layout__left {
    min-width: 48px;
  }
}

@media (max-width: 1300px) {
  .editor-layout {
    --inspector-width: 48px;
  }
  .editor-layout__inspector {
    min-width: 48px;
  }
}
</style>
