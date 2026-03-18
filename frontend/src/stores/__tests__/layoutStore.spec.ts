import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useLayoutStore } from '../layout'
import { useTemplateStore } from '../templateStore'
import { useConfidenceStore } from '../confidenceStore'
import { useCoverageStore } from '../coverageStore'
import { useInspectorStore } from '../inspectorStore'
import type { LayoutType } from '@/types/pipeline.types'
import type { DocumentTree, TreeNode } from '@/types/template.types'
import type { ConfidenceFactors } from '@/types/confidence.types'
import type { CoverageData } from '@/types/coverage.types'

vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      get: vi.fn(() => Promise.resolve(undefined)),
      put: vi.fn(() => Promise.resolve()),
    }),
  ),
}))

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const rootNode: TreeNode = {
  id: 'root-1',
  type: 'document',
  name: 'Doc',
  children: [],
  properties: {},
  visibility: true,
}

const documentTree1: DocumentTree = {
  root: { ...rootNode, id: 'root-lt1' },
}

const documentTree2: DocumentTree = {
  root: { ...rootNode, id: 'root-lt2' },
}

const confidence1: ConfidenceFactors = {
  layout_stability: 98,
  anchor_detection: 97,
  grid_quality: 95,
  field_variability: 94,
  vision_agreement: 99,
  overall: 96,
}

const confidence2: ConfidenceFactors = {
  layout_stability: 80,
  anchor_detection: 78,
  grid_quality: 82,
  field_variability: 79,
  vision_agreement: 85,
  overall: 81,
}

const coverage1: CoverageData = {
  fields: { mapped: 18, total: 20 },
  tables: { mapped: 3, total: 3 },
  images: { mapped: 2, total: 2 },
  charts: { mapped: 1, total: 1 },
  percentage: 96,
}

const coverage2: CoverageData = {
  fields: { mapped: 10, total: 20 },
  tables: { mapped: 2, total: 3 },
  images: { mapped: 1, total: 2 },
  charts: { mapped: 0, total: 1 },
  percentage: 65,
}

const lt1: LayoutType = {
  id: 'lt-1',
  name: 'Transações',
  pageCount: 285,
  docCount: 3,
  representativePages: [1],
  documentTree: documentTree1,
  confidence: confidence1,
  coverage: coverage1,
}

const lt2: LayoutType = {
  id: 'lt-2',
  name: 'Resumo',
  pageCount: 10,
  docCount: 1,
  representativePages: [1],
  documentTree: documentTree2,
  confidence: confidence2,
  coverage: coverage2,
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('layoutStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('initial state', () => {
    it('initializes with empty layoutTypes and null activeLayoutId', () => {
      const store = useLayoutStore()
      expect(store.layoutTypes).toHaveLength(0)
      expect(store.activeLayoutId).toBeNull()
    })

    it('activeLayout getter returns undefined when no active layout', () => {
      const store = useLayoutStore()
      expect(store.activeLayout).toBeUndefined()
    })
  })

  describe('loadLayoutTypes', () => {
    it('loads layout types and sets first as active', () => {
      const store = useLayoutStore()
      store.loadLayoutTypes([lt1, lt2])
      expect(store.layoutTypes).toHaveLength(2)
      expect(store.activeLayoutId).toBe('lt-1')
    })

    it('does not change activeLayoutId if already set', () => {
      const store = useLayoutStore()
      store.activeLayoutId = 'lt-2'
      store.loadLayoutTypes([lt1, lt2])
      expect(store.activeLayoutId).toBe('lt-2')
    })

    it('activeLayout getter returns correct layout after load', () => {
      const store = useLayoutStore()
      store.loadLayoutTypes([lt1, lt2])
      expect(store.activeLayout?.name).toBe('Transações')
    })
  })

  describe('setActiveLayout', () => {
    it('updates activeLayoutId to new layout', () => {
      const store = useLayoutStore()
      store.loadLayoutTypes([lt1, lt2])
      store.setActiveLayout('lt-2')
      expect(store.activeLayoutId).toBe('lt-2')
    })

    it('does nothing when switching to already-active layout', () => {
      const store = useLayoutStore()
      store.loadLayoutTypes([lt1, lt2])
      store.activeLayoutId = 'lt-1'
      const templateStore = useTemplateStore()
      const loadTreeSpy = vi.spyOn(templateStore, 'loadTree')
      store.setActiveLayout('lt-1')
      expect(loadTreeSpy).not.toHaveBeenCalled()
    })

    it('loads new layout documentTree into templateStore', () => {
      const store = useLayoutStore()
      store.loadLayoutTypes([lt1, lt2])
      const templateStore = useTemplateStore()
      store.setActiveLayout('lt-2')
      expect(templateStore.documentTree?.root.id).toBe('root-lt2')
    })

    it('loads new layout confidence into confidenceStore', () => {
      const store = useLayoutStore()
      store.loadLayoutTypes([lt1, lt2])
      store.setActiveLayout('lt-2')
      const confidenceStore = useConfidenceStore()
      const conf = confidenceStore.getForLayout('lt-2')
      expect(conf?.overall).toBe(81)
    })

    it('loads new layout coverage into coverageStore', () => {
      const store = useLayoutStore()
      store.loadLayoutTypes([lt1, lt2])
      store.setActiveLayout('lt-2')
      const coverageStore = useCoverageStore()
      const cov = coverageStore.getForLayout('lt-2')
      expect(cov?.percentage).toBe(65)
    })

    it('resets inspectorStore selectedNode to null', () => {
      const store = useLayoutStore()
      store.loadLayoutTypes([lt1, lt2])
      const inspectorStore = useInspectorStore()
      inspectorStore.selectNode(rootNode)
      expect(inspectorStore.selectedNode).not.toBeNull()
      store.setActiveLayout('lt-2')
      expect(inspectorStore.selectedNode).toBeNull()
    })

    it('resets inspector level to page after layout switch', () => {
      const store = useLayoutStore()
      store.loadLayoutTypes([lt1, lt2])
      const inspectorStore = useInspectorStore()
      inspectorStore.selectNode({ ...rootNode, type: 'table' })
      store.setActiveLayout('lt-2')
      expect(inspectorStore.level).toBe('page')
    })

    it('preserves current layout state back into array on switch', () => {
      const store = useLayoutStore()
      store.loadLayoutTypes([lt1, lt2])

      // Load a tree into templateStore for lt-1
      const templateStore = useTemplateStore()
      const modifiedTree: DocumentTree = {
        root: { ...rootNode, id: 'root-modified' },
      }
      templateStore.loadTree(modifiedTree)

      // Switch away from lt-1
      store.setActiveLayout('lt-2')

      // lt-1 should have captured the modified tree
      const savedLt1 = store.layoutTypes.find((lt) => lt.id === 'lt-1')
      expect(savedLt1?.documentTree?.root.id).toBe('root-modified')
    })

    it('activeLayout getter reflects new active layout after switch', () => {
      const store = useLayoutStore()
      store.loadLayoutTypes([lt1, lt2])
      store.setActiveLayout('lt-2')
      expect(store.activeLayout?.name).toBe('Resumo')
    })
  })
})
