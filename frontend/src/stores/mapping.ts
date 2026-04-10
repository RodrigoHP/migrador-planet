import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
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

export const useMappingStore = defineStore('mapping', () => {
  const fields = ref<FieldMapping[]>([])
  const fieldNavItems = ref<FieldNavItem[]>([])
  const selectedFieldId = ref<string | null>(null)
  const confirmed = ref(false)
  const flatPaths = ref<string[]>([])
  // Story 28.2: XSD fields with no PDF match (from validation_result)
  const xsdOnlyFields = ref<UnmappedXsdField[]>([])

  const selectedField = computed(
    () => fields.value.find((f) => f.id === selectedFieldId.value) ?? null,
  )
  const hasUnresolvedRequired = computed(() =>
    fields.value.some((f) => !f.isManual && f.status === 'not_found'),
  )
  // AC5 — campos agrupados por status (mapped / unmapped / unconfirmed)
  const fieldNavItemsByStatus = computed(
    (): Record<FieldNavStatus, FieldNavItem[]> => ({
      mapped: fieldNavItems.value.filter((f) => f.status === 'mapped'),
      unmapped: fieldNavItems.value.filter((f) => f.status === 'unmapped'),
      unconfirmed: fieldNavItems.value.filter((f) => f.status === 'unconfirmed'),
    }),
  )
  // Story 28.1 — true when XSD flat_paths are available for the BindingEditor
  const hasFlatPaths = computed(() => flatPaths.value.length > 0)
  // Story 28.2 — count of XSD-only fields with no PDF match
  const totalUnmappedXsd = computed(() => xsdOnlyFields.value.length)

  function $reset() {
    fields.value = []
    fieldNavItems.value = []
    selectedFieldId.value = null
    confirmed.value = false
    flatPaths.value = []
    xsdOnlyFields.value = []
  }

  function updateField(payload: Partial<FieldMapping> & { id: string }) {
    const idx = fields.value.findIndex((f) => f.id === payload.id)
    if (idx !== -1) {
      const current = fields.value[idx]
      if (!current) return
      fields.value[idx] = { ...current, ...payload }
    }
  }

  function setFields(newFields: FieldMapping[]) {
    fields.value = newFields
  }

  function setFieldNavItems(items: FieldNavItem[]) {
    fieldNavItems.value = items
  }

  function mapField(nodeId: string, fieldPath: string) {
    const templateStore = useTemplateStore()
    templateStore.updateNodeProperty(nodeId, 'binding', fieldPath)
    const item = fieldNavItems.value.find((i) => i.path === fieldPath)
    if (item) item.status = 'mapped'
    const field = fields.value.find((f) => f.jsonPath === fieldPath)
    if (field) field.status = 'ok'
  }

  function removeBinding(nodeId: string) {
    const templateStore = useTemplateStore()
    const node = templateStore.getNodeById(nodeId)
    if (!node?.binding) return
    const fieldPath = node.binding
    templateStore.updateNodeProperty(nodeId, 'binding', '')
    const item = fieldNavItems.value.find((i) => i.path === fieldPath)
    if (item) item.status = 'unmapped'
    const field = fields.value.find((f) => f.jsonPath === fieldPath)
    if (field) field.status = 'not_found'
  }

  // Story 28.1 — store XSD flat_paths for the BindingEditor dropdown
  function setFlatPaths(paths: string[]) {
    flatPaths.value = paths
  }

  // Story 28.1 — update node.binding via templateStore + sync fieldNavItem status
  function updateNodeBinding(nodeId: string, xsdPath: string | null) {
    const templateStore = useTemplateStore()
    templateStore.updateNodeProperty(nodeId, 'binding', xsdPath ?? '')
    // Sync fieldNavItem status: mapped when path set, unmapped when cleared
    if (xsdPath) {
      const item = fieldNavItems.value.find((i) => i.nodeId === nodeId || i.path === xsdPath)
      if (item) {
        item.status = 'mapped'
        item.binding = xsdPath
        item.nodeId = nodeId
      }
    } else {
      const item = fieldNavItems.value.find((i) => i.nodeId === nodeId)
      if (item) {
        item.status = 'unmapped'
        item.binding = undefined
      }
    }
  }

  // Story 28.1 — remove binding from a node
  function removeNodeBinding(nodeId: string) {
    updateNodeBinding(nodeId, null)
  }

  // Story 28.2 — store XSD fields that have no match in the PDF
  function setUnmappedXsdFields(newFields: UnmappedXsdField[]) {
    xsdOnlyFields.value = newFields
  }

  // Story 28.3 — resolve an ambiguous field: choose an XSD path or leave unmapped
  function resolveAmbiguous(fieldPath: string, chosenPath: string | null) {
    const item = fieldNavItems.value.find((f) => f.path === fieldPath || f.nodeId === fieldPath)
    if (!item) return
    if (chosenPath) {
      item.status = 'mapped'
      item.isAmbiguous = false
      item.binding = chosenPath
      if (item.nodeId) {
        updateNodeBinding(item.nodeId, chosenPath)
      }
    } else {
      item.status = 'unmapped'
      item.isAmbiguous = false
      item.binding = undefined
      if (item.nodeId) {
        removeNodeBinding(item.nodeId)
      }
    }
  }

  function loadPipelineFields(
    entries: FieldMappingEntry[],
    ambiguousFields: AmbiguousField[] = [],
  ) {
    // Map pipeline FieldMappingEntry to legacy FieldMapping shape
    fields.value = entries.map((entry, index) => ({
      id: `pipeline-${index}-${entry.name}`,
      pdfText: entry.name,
      jsonPath: entry.path,
      type: (entry.type as FieldMapping['type']) ?? 'text',
      confidence: mapConfidenceLevel(entry.confidence) as FieldMapping['confidence'],
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
    fieldNavItems.value = entries.map((entry) => {
      const blockId = entry.block_id
      // stage5 embeds candidates directly in each field_mapping entry as [{path, score}].
      // ambiguousMap lookup is used only as fallback; prefer entry.candidates (runtime data).
      const rawCandidates = entry.candidates
      const ambiguous = entry.status === 'ambiguous' ? ambiguousMap.get(entry.name) : undefined
      // Build candidates: use entry.candidates (correct dict format) if available;
      // fallback to ambiguousMap candidates (legacy string[] format) for saved projects.
      const candidates =
        entry.status === 'ambiguous'
          ? rawCandidates?.length
            ? rawCandidates.map((c) => ({
                path: c.path,
                confidence: c.score ?? c.confidence ?? 0,
              }))
            : ambiguous?.candidates?.map((p) => ({
                path: String(p),
                confidence: ambiguous.confidence,
              }))
          : undefined
      // Story 34.1: propagate real confidence score from pipeline
      const confidenceScore = parseConfidenceScore(entry.confidence)
      const confidenceLevel = mapConfidenceLevel(entry.confidence)

      return {
        name: entry.name || entry.path || 'Campo',
        path: entry.path || '',
        type: 'string' as const, // pipeline fields are text by default
        status: mapNavStatus(entry.status),
        binding: entry.binding,
        isOptional: entry.isOptional ?? false,
        isAmbiguous: entry.status === 'ambiguous',
        candidates,
        confidenceLevel: confidenceLevel as 'low' | 'medium' | 'high',
        confidenceScore,
        ...(blockId ? { nodeId: blockId } : {}),
      }
    })
  }

  return {
    fields,
    fieldNavItems,
    selectedFieldId,
    confirmed,
    flatPaths,
    xsdOnlyFields,
    selectedField,
    hasUnresolvedRequired,
    fieldNavItemsByStatus,
    hasFlatPaths,
    totalUnmappedXsd,
    $reset,
    updateField,
    setFields,
    setFieldNavItems,
    mapField,
    removeBinding,
    setFlatPaths,
    updateNodeBinding,
    removeNodeBinding,
    setUnmappedXsdFields,
    resolveAmbiguous,
    loadPipelineFields,
  }
})

function mapStatus(status: FieldMappingEntry['status']): FieldMapping['status'] {
  switch (status) {
    case 'mapped':
      return 'ok'
    case 'ambiguous':
      return 'ambiguous'
    case 'optional':
      return 'optional'
    case 'unmapped':
      return 'not_found'
    default:
      return 'not_found'
  }
}

function mapNavStatus(status: FieldMappingEntry['status']): FieldNavStatus {
  switch (status) {
    case 'mapped':
      return 'mapped'
    case 'ambiguous':
      return 'unconfirmed'
    case 'optional':
      return 'unmapped'
    case 'unmapped':
      return 'unmapped'
    default:
      return 'unmapped'
  }
}

/**
 * Story 34.1 — Map numeric confidence score to category.
 * <40% → low, 40-75% → medium, >75% → high
 */
export function mapConfidenceLevel(
  confidence: number | string | undefined,
): 'low' | 'medium' | 'high' {
  if (confidence === undefined || confidence === null) return 'medium'
  if (typeof confidence === 'string') {
    const lower = confidence.toLowerCase()
    if (lower === 'low' || lower === 'high' || lower === 'medium')
      return lower as 'low' | 'medium' | 'high'
    const parsed = parseFloat(confidence)
    if (!isNaN(parsed)) return mapConfidenceLevel(parsed)
    return 'medium'
  }
  if (confidence < 40) return 'low'
  if (confidence <= 75) return 'medium'
  return 'high'
}

/**
 * Story 34.1 — Parse confidence to numeric score (0-100).
 */
export function parseConfidenceScore(confidence: number | string | undefined): number | undefined {
  if (confidence === undefined || confidence === null) return undefined
  if (typeof confidence === 'number') return confidence
  const parsed = parseFloat(confidence)
  if (!isNaN(parsed)) return parsed
  // Map string categories to representative scores
  switch (confidence.toLowerCase()) {
    case 'low':
      return 20
    case 'medium':
      return 60
    case 'high':
      return 90
    default:
      return undefined
  }
}
