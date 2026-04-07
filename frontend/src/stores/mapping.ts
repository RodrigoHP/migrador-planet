import { defineStore } from 'pinia'
import type { FieldMapping } from '@/types'
import type { AmbiguousField, FieldMappingEntry, UnmappedXsdField } from '@/types/pipeline.types'
import type { FieldNavItem, FieldNavStatus } from '@/types/field-navigator.types'
import { useTemplateStore } from './templateStore'

export interface MappingStoreState {
  fields: FieldMapping[]
  fieldNavItems: FieldNavItem[]
  selectedFieldId: string | null
  confirmed: boolean
  flatPaths: string[]
  // Story 28.2: XSD fields with no PDF match (from validation_result)
  xsdOnlyFields: UnmappedXsdField[]
}

export const useMappingStore = defineStore('mapping', {
  state: (): MappingStoreState => ({
    fields: [],
    fieldNavItems: [],
    selectedFieldId: null,
    confirmed: false,
    flatPaths: [],
    xsdOnlyFields: [],
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
    // Story 28.1 — true when XSD flat_paths are available for the BindingEditor
    hasFlatPaths: (state) => state.flatPaths.length > 0,
    // Story 28.2 — count of XSD-only fields with no PDF match
    totalUnmappedXsd: (state) => state.xsdOnlyFields.length,
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
    // Story 28.1 — store XSD flat_paths for the BindingEditor dropdown
    setFlatPaths(paths: string[]) {
      this.flatPaths = paths
    },

    // Story 28.1 — update node.binding via templateStore + sync fieldNavItem status
    updateNodeBinding(nodeId: string, xsdPath: string | null) {
      const templateStore = useTemplateStore()
      templateStore.updateNodeProperty(nodeId, 'binding', xsdPath ?? '')
      // Sync fieldNavItem status: mapped when path set, unmapped when cleared
      if (xsdPath) {
        const item = this.fieldNavItems.find((i) => i.nodeId === nodeId || i.path === xsdPath)
        if (item) {
          item.status = 'mapped'
          item.binding = xsdPath
          item.nodeId = nodeId
        }
      } else {
        const item = this.fieldNavItems.find((i) => i.nodeId === nodeId)
        if (item) {
          item.status = 'unmapped'
          item.binding = undefined
        }
      }
    },

    // Story 28.1 — remove binding from a node
    removeNodeBinding(nodeId: string) {
      this.updateNodeBinding(nodeId, null)
    },

    // Story 28.2 — store XSD fields that have no match in the PDF
    setUnmappedXsdFields(fields: UnmappedXsdField[]) {
      this.xsdOnlyFields = fields
    },

    // Story 28.3 — resolve an ambiguous field: choose an XSD path or leave unmapped
    resolveAmbiguous(fieldPath: string, chosenPath: string | null) {
      const item = this.fieldNavItems.find((f) => f.path === fieldPath || f.nodeId === fieldPath)
      if (!item) return
      if (chosenPath) {
        item.status = 'mapped'
        item.isAmbiguous = false
        item.binding = chosenPath
        if (item.nodeId) {
          this.updateNodeBinding(item.nodeId, chosenPath)
        }
      } else {
        item.status = 'unmapped'
        item.isAmbiguous = false
        item.binding = undefined
        if (item.nodeId) {
          this.removeNodeBinding(item.nodeId)
        }
      }
    },

    loadPipelineFields(entries: FieldMappingEntry[], ambiguousFields: AmbiguousField[] = []) {
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

      // Build lookup: field name → AmbiguousField (for candidate population)
      const ambiguousMap = new Map<string, AmbiguousField>()
      for (const af of ambiguousFields) {
        ambiguousMap.set(af.name, af)
      }

      // AC1 — Populate fieldNavItems so FieldNavigator.vue renders the fields list.
      // Before Story 12.3 this was never populated — fieldNavItems stayed empty
      // regardless of how many fields the pipeline extracted.
      // Pre-populate nodeId from block_id (raw pipeline data has this field even
      // though FieldMappingEntry type doesn't declare it). Since the backend sets
      // node.id = block_id, this lets onSelectField navigate to the node for ALL
      // fields (mapped AND unmapped), enabling "Vincular →" to open the Inspector.
      this.fieldNavItems = entries.map((entry) => {
        const blockId = (entry as unknown as Record<string, unknown>)['block_id'] as string | undefined
        // stage5 embeds candidates directly in each field_mapping entry as [{path, score}].
        // ambiguousMap lookup is used only as fallback; prefer entry.candidates (runtime data).
        const entryAny = entry as unknown as Record<string, unknown>
        const rawCandidates = entryAny['candidates'] as Array<{ path: string; score?: number; confidence?: number }> | undefined
        const ambiguous = entry.status === 'ambiguous' ? ambiguousMap.get(entry.name) : undefined
        // Build candidates: use entry.candidates (correct dict format) if available;
        // fallback to ambiguousMap candidates (legacy string[] format) for saved projects.
        const candidates = entry.status === 'ambiguous'
          ? rawCandidates?.length
            ? rawCandidates.map((c) => ({ path: c.path, confidence: c.score ?? c.confidence ?? 0 }))
            : ambiguous?.candidates?.map((p) => ({ path: String(p), confidence: ambiguous.confidence }))
          : undefined
        return {
          name: entry.name || entry.path || 'Campo',
          path: entry.path || '',
          type: 'string' as const,  // pipeline fields are text by default
          status: mapNavStatus(entry.status),
          binding: entry.binding,
          isOptional: entry.isOptional ?? false,
          isAmbiguous: entry.status === 'ambiguous',
          candidates,
          ...(blockId ? { nodeId: blockId } : {}),
        }
      })
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
