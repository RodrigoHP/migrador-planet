import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { openDB } from 'idb'
import type { LayoutType } from '@/types/pipeline.types'
import { useTemplateStore } from './templateStore'
import { useConfidenceStore } from './confidenceStore'
import { useCoverageStore } from './coverageStore'
import { useInspectorStore } from './inspectorStore'
import { useEditorStore } from './editorStore'
import { useMappingStore } from './mapping'

// Per-layout transient state preserved across layout switches (Story 12.9)
export interface LayoutState {
  selectedNodeId: string | null
  zoomLevel: number
  selectedFieldId: string | null
}

export interface LayoutStore {
  pageSize: 'A4' | 'Letter' | 'A3'
  marginTop: number
  marginBottom: number
  marginLeft: number
  marginRight: number
  baseFontFamily: string
  baseFontSize: number
  primaryColor: string
  lineHeight: number
  bibliotecasVersions: Record<string, string>
  confirmed: boolean
  layoutTypes: LayoutType[]
  activeLayoutId: string | null
  layoutStates: Record<string, LayoutState>
  pendingScrollToLayout: string | null
}

type LayoutPersistedState = Omit<LayoutStore, 'pendingScrollToLayout'>

let dbPromise: ReturnType<typeof openDB> | null = null

function getDb() {
  if (!dbPromise) {
    dbPromise = openDB('migrador', 1, {
      upgrade(db) {
        if (!db.objectStoreNames.contains('project')) {
          db.createObjectStore('project')
        }
      },
    })
  }
  return dbPromise
}

export const useLayoutStore = defineStore('layout', () => {
  const pageSize = ref<'A4' | 'Letter' | 'A3'>('A4')
  const marginTop = ref(20)
  const marginBottom = ref(20)
  const marginLeft = ref(20)
  const marginRight = ref(20)
  const baseFontFamily = ref('Inter')
  const baseFontSize = ref(14)
  const primaryColor = ref('#2563EB')
  const lineHeight = ref(1.5)
  const bibliotecasVersions = ref<Record<string, string>>({})
  const confirmed = ref(false)
  const layoutTypes = ref<LayoutType[]>([])
  const activeLayoutId = ref<string | null>(null)
  const layoutStates = ref<Record<string, LayoutState>>({})
  const pendingScrollToLayout = ref<string | null>(null)

  const activeLayout = computed((): LayoutType | undefined =>
    layoutTypes.value.find((lt) => lt.id === activeLayoutId.value),
  )

  function $reset() {
    pageSize.value = 'A4'
    marginTop.value = 20
    marginBottom.value = 20
    marginLeft.value = 20
    marginRight.value = 20
    baseFontFamily.value = 'Inter'
    baseFontSize.value = 14
    primaryColor.value = '#2563EB'
    lineHeight.value = 1.5
    bibliotecasVersions.value = {}
    confirmed.value = false
    layoutTypes.value = []
    activeLayoutId.value = null
    layoutStates.value = {}
    pendingScrollToLayout.value = null
  }

  async function hydrateFromIdb() {
    const db = await getDb()
    const persisted = (await db.get('project', 'layout')) as LayoutPersistedState | undefined
    if (!persisted) return
    pageSize.value = persisted.pageSize ?? pageSize.value
    marginTop.value = persisted.marginTop ?? marginTop.value
    marginBottom.value = persisted.marginBottom ?? marginBottom.value
    marginLeft.value = persisted.marginLeft ?? marginLeft.value
    marginRight.value = persisted.marginRight ?? marginRight.value
    baseFontFamily.value = persisted.baseFontFamily ?? baseFontFamily.value
    baseFontSize.value = persisted.baseFontSize ?? baseFontSize.value
    primaryColor.value = persisted.primaryColor ?? primaryColor.value
    lineHeight.value = persisted.lineHeight ?? lineHeight.value
    bibliotecasVersions.value = persisted.bibliotecasVersions ?? bibliotecasVersions.value
    confirmed.value = persisted.confirmed ?? confirmed.value
    layoutTypes.value = persisted.layoutTypes ?? layoutTypes.value
    activeLayoutId.value = persisted.activeLayoutId ?? activeLayoutId.value
    layoutStates.value = persisted.layoutStates ?? layoutStates.value
  }

  async function persistToIdb() {
    const db = await getDb()
    const payload: LayoutPersistedState = {
      pageSize: pageSize.value,
      marginTop: marginTop.value,
      marginBottom: marginBottom.value,
      marginLeft: marginLeft.value,
      marginRight: marginRight.value,
      baseFontFamily: baseFontFamily.value,
      baseFontSize: baseFontSize.value,
      primaryColor: primaryColor.value,
      lineHeight: lineHeight.value,
      bibliotecasVersions: bibliotecasVersions.value,
      confirmed: confirmed.value,
      layoutTypes: layoutTypes.value,
      activeLayoutId: activeLayoutId.value,
      layoutStates: layoutStates.value,
    }
    await db.put('project', payload, 'layout')
  }

  function loadLayoutTypes(types: LayoutType[]) {
    layoutTypes.value = types
    if (types.length > 0 && !activeLayoutId.value) {
      activeLayoutId.value = types[0]?.id ?? null
    }
  }

  function renameLayout(id: string, newName: string) {
    const layout = layoutTypes.value.find((lt) => lt.id === id)
    if (layout) {
      layout.name = newName.trim() || layout.name
      persistToIdb()
    }
  }

  function setActiveLayout(id: string) {
    if (activeLayoutId.value === id) return

    const editorStore = useEditorStore()
    const mappingStore = useMappingStore()
    const inspectorStore = useInspectorStore()

    // 1. Preserve current layout state
    const currentId = activeLayoutId.value
    const currentLayout = layoutTypes.value.find((lt) => lt.id === currentId)
    if (currentLayout && currentId) {
      const templateStore = useTemplateStore()
      const confidenceStore = useConfidenceStore()
      const coverageStore = useCoverageStore()
      if (templateStore.documentTree !== null) {
        currentLayout.documentTree = JSON.parse(JSON.stringify(templateStore.documentTree))
      }
      const currentConfidence = confidenceStore.getForLayout(currentId)
      if (currentConfidence) {
        currentLayout.confidence = currentConfidence
      }
      const currentCoverage = coverageStore.getForLayout(currentId)
      if (currentCoverage) {
        currentLayout.coverage = currentCoverage
      }
      // Save transient UI state (Story 12.9)
      layoutStates.value[currentId] = {
        selectedNodeId: inspectorStore.selectedNode?.id ?? null,
        zoomLevel: editorStore.zoomLevel,
        selectedFieldId: mappingStore.selectedFieldId,
      }
    }

    // 2. Switch active layout
    activeLayoutId.value = id

    // 3. Load new layout state into stores
    const newLayout = layoutTypes.value.find((lt) => lt.id === id)
    if (newLayout) {
      const templateStore = useTemplateStore()
      const confidenceStore = useConfidenceStore()
      const coverageStore = useCoverageStore()

      if (newLayout.documentTree) {
        templateStore.loadTree(newLayout.documentTree)
      }
      if (newLayout.confidence) {
        confidenceStore.updateForLayout(id, newLayout.confidence)
      }
      if (newLayout.coverage) {
        coverageStore.updateForLayout(id, newLayout.coverage)
      }

      // 4. Restore transient UI state if previously saved (Story 12.9), else defaults
      const saved = layoutStates.value[id]
      if (saved) {
        editorStore.setZoom(saved.zoomLevel)
        if (saved.selectedNodeId) {
          const node = templateStore.getNodeById(saved.selectedNodeId)
          if (node) inspectorStore.selectNode(node)
          else inspectorStore.clearSelection()
        } else {
          inspectorStore.clearSelection()
        }
        if (saved.selectedFieldId) {
          mappingStore.selectedFieldId = saved.selectedFieldId
        }
      } else {
        inspectorStore.clearSelection()
      }
    }

    // 5. Signal canvas to scroll to this layout section
    pendingScrollToLayout.value = id
  }

  function clearScrollTarget() {
    pendingScrollToLayout.value = null
  }

  // Sync activeLayoutId from canvas scroll (no DOM side-effects — avoids loop)
  function syncActiveLayoutFromScroll(id: string) {
    if (activeLayoutId.value === id) return
    activeLayoutId.value = id
    const newLayout = layoutTypes.value.find((lt) => lt.id === id)
    if (newLayout) {
      const templateStore = useTemplateStore()
      const confidenceStore = useConfidenceStore()
      const coverageStore = useCoverageStore()
      if (newLayout.documentTree) templateStore.loadTree(newLayout.documentTree)
      if (newLayout.confidence) confidenceStore.updateForLayout(id, newLayout.confidence)
      if (newLayout.coverage) coverageStore.updateForLayout(id, newLayout.coverage)
    }
  }

  return {
    pageSize,
    marginTop,
    marginBottom,
    marginLeft,
    marginRight,
    baseFontFamily,
    baseFontSize,
    primaryColor,
    lineHeight,
    bibliotecasVersions,
    confirmed,
    layoutTypes,
    activeLayoutId,
    layoutStates,
    pendingScrollToLayout,
    activeLayout,
    $reset,
    hydrateFromIdb,
    persistToIdb,
    loadLayoutTypes,
    renameLayout,
    setActiveLayout,
    clearScrollTarget,
    syncActiveLayoutFromScroll,
  }
})
