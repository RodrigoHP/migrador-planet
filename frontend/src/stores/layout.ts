import { defineStore } from 'pinia'
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
  // Epic-6 extensions
  layoutTypes: LayoutType[]
  activeLayoutId: string | null
  // Story 12.9: per-layout transient state
  layoutStates: Record<string, LayoutState>
  // Canvas scroll target — set by setActiveLayout(), cleared by canvas after scroll
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

export const useLayoutStore = defineStore('layout', {
  state: (): LayoutStore => ({
    pageSize: 'A4',
    marginTop: 20,
    marginBottom: 20,
    marginLeft: 20,
    marginRight: 20,
    baseFontFamily: 'Inter',
    baseFontSize: 14,
    primaryColor: '#2563EB',
    lineHeight: 1.5,
    bibliotecasVersions: {},
    confirmed: false,
    layoutTypes: [],
    activeLayoutId: null,
    layoutStates: {},
    pendingScrollToLayout: null,
  }),
  getters: {
    activeLayout: (state): LayoutType | undefined =>
      state.layoutTypes.find((lt) => lt.id === state.activeLayoutId),
  },
  actions: {
    async hydrateFromIdb() {
      const db = await getDb()
      const persisted = await db.get('project', 'layout') as LayoutPersistedState | undefined
      if (!persisted) return
      this.$patch(persisted as unknown as Parameters<typeof this.$patch>[0])
    },
    async persistToIdb() {
      const db = await getDb()
      const payload: LayoutPersistedState = {
        pageSize: this.pageSize,
        marginTop: this.marginTop,
        marginBottom: this.marginBottom,
        marginLeft: this.marginLeft,
        marginRight: this.marginRight,
        baseFontFamily: this.baseFontFamily,
        baseFontSize: this.baseFontSize,
        primaryColor: this.primaryColor,
        lineHeight: this.lineHeight,
        bibliotecasVersions: this.bibliotecasVersions,
        confirmed: this.confirmed,
        layoutTypes: this.layoutTypes,
        activeLayoutId: this.activeLayoutId,
        layoutStates: this.layoutStates,
      }
      await db.put('project', payload, 'layout')
    },
    loadLayoutTypes(types: LayoutType[]) {
      this.layoutTypes = types
      if (types.length > 0 && !this.activeLayoutId) {
        this.activeLayoutId = types[0]?.id ?? null
      }
    },
    renameLayout(id: string, newName: string) {
      const layout = this.layoutTypes.find((lt) => lt.id === id)
      if (layout) {
        layout.name = newName.trim() || layout.name
        this.persistToIdb()
      }
    },
    setActiveLayout(id: string) {
      if (this.activeLayoutId === id) return

      const editorStore = useEditorStore()
      const mappingStore = useMappingStore()
      const inspectorStore = useInspectorStore()

      // 1. Preserve current layout's unsaved state back into the array
      const currentId = this.activeLayoutId
      const currentLayout = this.layoutTypes.find((lt) => lt.id === currentId)
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
        this.layoutStates[currentId] = {
          selectedNodeId: inspectorStore.selectedNode?.id ?? null,
          zoomLevel: editorStore.zoomLevel,
          selectedFieldId: mappingStore.selectedFieldId,
        }
      }

      // 2. Switch active layout
      this.activeLayoutId = id

      // 3. Load new layout state into stores
      const newLayout = this.layoutTypes.find((lt) => lt.id === id)
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
        const saved = this.layoutStates[id]
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
          // First access: reset inspector to Page level
          inspectorStore.clearSelection()
        }
      }

      // 5. Signal canvas to scroll to this layout's section
      this.pendingScrollToLayout = id
    },

    clearScrollTarget() {
      this.pendingScrollToLayout = null
    },

    // Sync activeLayoutId from canvas scroll (no DOM side-effects — avoids loop)
    syncActiveLayoutFromScroll(id: string) {
      if (this.activeLayoutId === id) return
      this.activeLayoutId = id
      const newLayout = this.layoutTypes.find((lt) => lt.id === id)
      if (newLayout) {
        const templateStore = useTemplateStore()
        const confidenceStore = useConfidenceStore()
        const coverageStore = useCoverageStore()
        if (newLayout.documentTree) templateStore.loadTree(newLayout.documentTree)
        if (newLayout.confidence) confidenceStore.updateForLayout(id, newLayout.confidence)
        if (newLayout.coverage) coverageStore.updateForLayout(id, newLayout.coverage)
      }
    },
  },
})
