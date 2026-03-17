import { defineStore } from 'pinia'
import type { FieldMapping } from '@/types'
import type { FieldMappingEntry } from '@/types/pipeline.types'
import type { FieldNavItem } from '@/types/field-navigator.types'

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
