import { defineStore } from 'pinia'
import type { FieldMapping } from '@/types'
import type { FieldMappingEntry } from '@/types/pipeline.types'
import type { FieldNavItem, FieldNavStatus } from '@/types/field-navigator.types'
import { useTemplateStore } from './templateStore'

export interface MappingStoreState {
  fields: FieldMapping[]
  fieldNavItems: FieldNavItem[]
  selectedFieldId: string | null
  confirmed: boolean
}

export const useMappingStore = defineStore('mapping', {
  state: (): MappingStoreState => ({
    fields: [],
    fieldNavItems: [],
    selectedFieldId: null,
    confirmed: false,
  }),
  getters: {
    selectedField: (state) =>
      state.fields.find((f) => f.id === state.selectedFieldId) ?? null,
    hasUnresolvedRequired: (state) =>
      state.fields.some((f) => !f.isManual && f.status === 'not_found'),
    // AC5 — campos agrupados por status (mapped / unmapped / unconfirmed)
    fieldNavItemsByStatus: (state): Record<FieldNavStatus, FieldNavItem[]> => ({
      mapped: state.fieldNavItems.filter((f) => f.status === 'mapped'),
      unmapped: state.fieldNavItems.filter((f) => f.status === 'unmapped'),
      unconfirmed: state.fieldNavItems.filter((f) => f.status === 'unconfirmed'),
    }),
  },
  actions: {
    updateField(payload: Partial<FieldMapping> & { id: string }) {
      const idx = this.fields.findIndex((f) => f.id === payload.id)
      if (idx !== -1) {
        const current = this.fields[idx]
        if (!current) return
        this.fields[idx] = { ...current, ...payload }
      }
    },
    setFields(fields: FieldMapping[]) {
      this.fields = fields
    },
    setFieldNavItems(items: FieldNavItem[]) {
      this.fieldNavItems = items
    },
    mapField(nodeId: string, fieldPath: string) {
      const templateStore = useTemplateStore()
      templateStore.updateNodeProperty(nodeId, 'binding', fieldPath)
      const item = this.fieldNavItems.find((i) => i.path === fieldPath)
      if (item) item.status = 'mapped'
      const field = this.fields.find((f) => f.jsonPath === fieldPath)
      if (field) field.status = 'ok'
    },
    removeBinding(nodeId: string) {
      const templateStore = useTemplateStore()
      const node = templateStore.getNodeById(nodeId)
      if (!node?.binding) return
      const fieldPath = node.binding
      templateStore.updateNodeProperty(nodeId, 'binding', '')
      const item = this.fieldNavItems.find((i) => i.path === fieldPath)
      if (item) item.status = 'unmapped'
      const field = this.fields.find((f) => f.jsonPath === fieldPath)
      if (field) field.status = 'not_found'
    },
    loadPipelineFields(entries: FieldMappingEntry[]) {
      // Map pipeline FieldMappingEntry to legacy FieldMapping shape
      this.fields = entries.map((entry, index) => ({
        id: `pipeline-${index}-${entry.name}`,
        pdfText: entry.name,
        jsonPath: entry.path,
        type: (entry.type as FieldMapping['type']) ?? 'text',
        confidence: 'medium' as FieldMapping['confidence'],
        status: mapStatus(entry.status),
        isManual: false,
        candidates: undefined,
        pageRef: undefined,
        boundingBox: undefined,
      }))

      // AC1 — Populate fieldNavItems so FieldNavigator.vue renders the fields list.
      // Before Story 12.3 this was never populated — fieldNavItems stayed empty
      // regardless of how many fields the pipeline extracted.
      this.fieldNavItems = entries.map((entry) => ({
        name: entry.name || entry.path || 'Campo',
        path: entry.path || '',
        type: 'string' as const,  // pipeline fields are text by default
        status: mapNavStatus(entry.status),
        binding: entry.binding,
        isOptional: entry.isOptional ?? false,
        isAmbiguous: entry.status === 'ambiguous',
      }))
    },
  },
})

function mapStatus(status: FieldMappingEntry['status']): FieldMapping['status'] {
  switch (status) {
    case 'mapped': return 'ok'
    case 'ambiguous': return 'ambiguous'
    case 'optional': return 'optional'
    case 'unmapped': return 'not_found'
    default: return 'not_found'
  }
}

function mapNavStatus(status: FieldMappingEntry['status']): FieldNavStatus {
  switch (status) {
    case 'mapped': return 'mapped'
    case 'ambiguous': return 'unconfirmed'
    case 'optional': return 'unmapped'
    case 'unmapped': return 'unmapped'
    default: return 'unmapped'
  }
}
