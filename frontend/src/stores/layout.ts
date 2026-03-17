import { defineStore } from 'pinia'
import { openDB } from 'idb'
import type { LayoutType } from '@/types/pipeline.types'

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
}

type LayoutPersistedState = Omit<LayoutStore, never>

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
      this.$patch(persisted)
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
      }
      await db.put('project', payload, 'layout')
    },
    loadLayoutTypes(types: LayoutType[]) {
      this.layoutTypes = types
      if (types.length > 0 && !this.activeLayoutId) {
        this.activeLayoutId = types[0]?.id ?? null
      }
    },
    setActiveLayout(id: string) {
      this.activeLayoutId = id
    },
  },
})
