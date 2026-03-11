import { defineStore } from 'pinia'
import type { FieldMapping } from '@/types'

export interface MappingStore {
  fields: FieldMapping[]
  selectedFieldId: string | null
  confirmed: boolean
}

export const useMappingStore = defineStore('mapping', {
  state: (): MappingStore => ({
    fields: [],
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
  },
})
