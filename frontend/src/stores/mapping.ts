import { defineStore } from 'pinia'
import type { FieldMapping } from '@/types'
import type { FieldMappingEntry } from '@/types/pipeline.types'
import type { FieldNavItem } from '@/types/field-navigator.types'
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
