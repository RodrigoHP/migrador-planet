import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { CenterTab, LeftTab } from '@/types/editor.types'

export const useEditorStore = defineStore('editor', () => {
  // ─── Center & Left Tabs ──────────────────────────────────────────────────
  const activeCenterTab = ref<CenterTab>('canvas')
  const activeLeftTab = ref<LeftTab>('structure')
  const activeSidebarTab = ref<string>('properties')

  // ─── Zoom ────────────────────────────────────────────────────────────────
  const zoomLevel = ref<number>(100)
  const pdfZoom = ref<number>(100)

  // ─── Selection ───────────────────────────────────────────────────────────
  const selectedElementId = ref<string | null>(null)

  // ─── Toggles ─────────────────────────────────────────────────────────────
  const coverageMode = ref<boolean>(false)
  const diffMode = ref<boolean>(false)
  const snapEnabled = ref<boolean>(false)
  const autoFixEnabled = ref<boolean>(false)
  const showGuides = ref<boolean>(false)

  // ─── Actions ─────────────────────────────────────────────────────────────
  function setActiveCenterTab(tab: CenterTab) {
    activeCenterTab.value = tab
  }

  function setActiveLeftTab(tab: LeftTab) {
    activeLeftTab.value = tab
  }

  function setActiveSidebarTab(tab: string) {
    activeSidebarTab.value = tab
  }

  function setZoom(level: number) {
    zoomLevel.value = level
  }

  function setPdfZoom(level: number) {
    pdfZoom.value = level
  }

  function selectElement(id: string | null) {
    selectedElementId.value = id
  }

  function toggleCoverage() {
    coverageMode.value = !coverageMode.value
  }

  function toggleDiff() {
    diffMode.value = !diffMode.value
  }

  function toggleSnap() {
    snapEnabled.value = !snapEnabled.value
  }

  function toggleAutoFix() {
    autoFixEnabled.value = !autoFixEnabled.value
  }

  function toggleGuides() {
    showGuides.value = !showGuides.value
  }

  return {
    activeCenterTab,
    activeLeftTab,
    activeSidebarTab,
    zoomLevel,
    pdfZoom,
    selectedElementId,
    coverageMode,
    diffMode,
    snapEnabled,
    autoFixEnabled,
    showGuides,
    setActiveCenterTab,
    setActiveLeftTab,
    setActiveSidebarTab,
    setZoom,
    setPdfZoom,
    selectElement,
    toggleCoverage,
    toggleDiff,
    toggleSnap,
    toggleAutoFix,
    toggleGuides,
  }
})
