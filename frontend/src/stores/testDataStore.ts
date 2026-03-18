import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { Dataset, ValidationResult, XsdFieldDef, DatasetStatus } from '@/types/test-data.types'

/** Maximum datasets allowed per template (AC9) */
export const MAX_DATASETS = 5

// ─── XSD Validation Helpers ──────────────────────────────────────────────────

/**
 * Flatten a nested object into dot-separated paths.
 * Arrays produce "path[0]", "path[1]", etc. for counting, but are stored
 * under "path" with a count marker.
 */
function flattenKeys(obj: unknown, prefix = ''): Map<string, unknown> {
  const result = new Map<string, unknown>()
  if (obj === null || obj === undefined) return result

  if (Array.isArray(obj)) {
    obj.forEach((item, idx) => {
      const childKeys = flattenKeys(item, `${prefix}[${idx}]`)
      childKeys.forEach((v, k) => result.set(k, v))
    })
    return result
  }

  if (typeof obj === 'object') {
    for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
      const fullPath = prefix ? `${prefix}.${key}` : key
      result.set(fullPath, value)
      if (typeof value === 'object' && value !== null) {
        const childKeys = flattenKeys(value, fullPath)
        childKeys.forEach((v, k) => result.set(k, v))
      }
    }
    return result
  }

  if (prefix) result.set(prefix, obj)
  return result
}

/**
 * Count top-level array fields (loops) in a dataset.
 */
function countLoops(fields: Record<string, unknown>): number {
  return Object.values(fields).filter((v) => Array.isArray(v)).length
}

/**
 * Type compatibility check.
 */
function isTypeCompatible(value: unknown, xsdType: string): boolean {
  if (value === null || value === undefined) return true // absence check handled separately
  switch (xsdType) {
    case 'integer':
      return typeof value === 'number' && Number.isInteger(value)
    case 'decimal':
      return typeof value === 'number'
    case 'boolean':
      return typeof value === 'boolean'
    case 'date':
      if (typeof value !== 'string') return false
      return !isNaN(Date.parse(value))
    case 'string':
    default:
      return true // string is permissive; arrays covered by 'array' check
  }
}

/**
 * Validate a dataset's fields against an array of XSD field definitions.
 * Returns a ValidationResult.
 */
export function validateDatasetAgainstXsd(
  dataset: Dataset,
  xsdFields: XsdFieldDef[],
): ValidationResult {
  const errors: string[] = []
  const warnings: string[] = []
  const flatKeys = flattenKeys(dataset.fields)

  for (const xsdField of xsdFields) {
    const topLevelKey = xsdField.path.split('.')[0] ?? xsdField.path
    // Check existence (use top-level for simple paths)
    const exists =
      topLevelKey in dataset.fields ||
      flatKeys.has(xsdField.path)

    if (!exists) {
      if (xsdField.required) {
        errors.push(`Campo obrigatório ausente: ${xsdField.path}`)
      } else {
        warnings.push(`Campo opcional ausente: ${xsdField.path}`)
      }
      continue
    }

    // Type check (only for leaf fields present in dataset.fields top-level)
    if (xsdField.type !== 'array' && topLevelKey in dataset.fields) {
      const value = dataset.fields[topLevelKey]
      if (!isTypeCompatible(value, xsdField.type)) {
        errors.push(`Tipo incompatível para ${xsdField.path}: esperado ${xsdField.type}`)
      }
    }
  }

  let status: DatasetStatus
  if (errors.length > 0) {
    status = 'invalid'
  } else if (warnings.length > 0) {
    status = 'warning'
  } else {
    status = 'valid'
  }

  return {
    datasetId: dataset.id,
    status,
    fieldCount: Object.keys(dataset.fields).length,
    loopCount: countLoops(dataset.fields),
    errors,
    warnings,
    testedAt: new Date().toISOString(),
  }
}

// ─── XML → JSON parser (simple, no external dependency) ──────────────────────

/**
 * Minimal XML-to-JSON converter that works in-browser.
 * Uses DOMParser if available, otherwise returns empty object.
 */
export function parseXmlToJson(xmlString: string): Record<string, unknown> {
  if (typeof DOMParser === 'undefined') return {}
  try {
    const parser = new DOMParser()
    const doc = parser.parseFromString(xmlString, 'application/xml')
    const errorNode = doc.querySelector('parsererror')
    if (errorNode) return {}
    return xmlNodeToJson(doc.documentElement) as Record<string, unknown>
  } catch {
    return {}
  }
}

function xmlNodeToJson(node: Element): unknown {
  const children = Array.from(node.children)
  if (children.length === 0) {
    // Leaf node
    const text = node.textContent?.trim() ?? ''
    return text
  }

  // Group children by tag name
  const result: Record<string, unknown> = {}
  const tagCounts: Record<string, number> = {}

  for (const child of children) {
    tagCounts[child.tagName] = (tagCounts[child.tagName] ?? 0) + 1
  }

  const tagArrays: Record<string, unknown[]> = {}
  for (const child of children) {
    const tag = child.tagName
    if (tagCounts[tag]! > 1) {
      if (!tagArrays[tag]) tagArrays[tag] = []
      tagArrays[tag]!.push(xmlNodeToJson(child))
    } else {
      result[tag] = xmlNodeToJson(child)
    }
  }

  for (const [tag, arr] of Object.entries(tagArrays)) {
    result[tag] = arr
  }

  return result
}

// ─── Store ───────────────────────────────────────────────────────────────────

export const useTestDataStore = defineStore('testData', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const datasets = ref<Dataset[]>([])
  const activeDatasetId = ref<string | null>(null)
  const validationResults = ref<ValidationResult[]>([])

  // ─── Getters ─────────────────────────────────────────────────────────────
  const activeDataset = computed<Dataset | undefined>(() =>
    datasets.value.find((d) => d.id === activeDatasetId.value),
  )

  const datasetCount = computed(() => datasets.value.length)

  const hasReachedLimit = computed(() => datasets.value.length >= MAX_DATASETS)

  const activeValidationResult = computed<ValidationResult | undefined>(() =>
    validationResults.value.find((r) => r.datasetId === activeDatasetId.value),
  )


  // ─── Actions ─────────────────────────────────────────────────────────────
  function setActiveDataset(id: string) {
    activeDatasetId.value = id
  }

  function addDataset(dataset: Dataset): boolean {
    if (datasets.value.length >= MAX_DATASETS) return false
    datasets.value.push(dataset)
    return true
  }

  function removeDataset(id: string) {
    datasets.value = datasets.value.filter((d) => d.id !== id)
    validationResults.value = validationResults.value.filter((r) => r.datasetId !== id)
    if (activeDatasetId.value === id) {
      activeDatasetId.value = datasets.value[0]?.id ?? null
    }
  }

  function updateDataset(id: string, patch: Partial<Omit<Dataset, 'id'>>) {
    const idx = datasets.value.findIndex((d) => d.id === id)
    if (idx !== -1 && datasets.value[idx]) {
      datasets.value[idx] = { ...datasets.value[idx]!, ...patch }
    }
  }

  function setValidationResult(result: ValidationResult) {
    const idx = validationResults.value.findIndex((r) => r.datasetId === result.datasetId)
    if (idx !== -1) {
      validationResults.value[idx] = result
    } else {
      validationResults.value.push(result)
    }
    // Update dataset status
    updateDataset(result.datasetId, { status: result.status })
  }

  function validateDataset(datasetId: string, xsdFields: XsdFieldDef[]): ValidationResult {
    const dataset = datasets.value.find((d) => d.id === datasetId)
    if (!dataset) {
      throw new Error(`Dataset ${datasetId} not found`)
    }
    const result = validateDatasetAgainstXsd(dataset, xsdFields)
    setValidationResult(result)
    return result
  }

  function getValidationResult(datasetId: string): ValidationResult | undefined {
    return validationResults.value.find((r) => r.datasetId === datasetId)
  }

  /**
   * Apply the active dataset to the Canvas iframe via postMessage.
   * The Canvas is expected to listen for { type: 'apply-test-data', data: {...} }
   */
  function applyDatasetToCanvas(iframeElements: HTMLIFrameElement[]) {
    const dataset = activeDataset.value
    if (!dataset) return
    for (const iframe of iframeElements) {
      iframe.contentWindow?.postMessage(
        { type: 'apply-test-data', data: dataset.fields },
        '*',
      )
    }
  }

  // Legacy placeholder
  function runValidation(_datasetId: string): Promise<void> {
    return Promise.resolve()
  }

  function setValidationResults(results: ValidationResult[]) {
    validationResults.value = results
  }

  return {
    datasets,
    activeDatasetId,
    validationResults,
    activeDataset,
    datasetCount,
    hasReachedLimit,
    activeValidationResult,
    setActiveDataset,
    addDataset,
    removeDataset,
    updateDataset,
    validateDataset,
    getValidationResult,
    setValidationResult,
    applyDatasetToCanvas,
    setValidationResults,
    runValidation,
  }
})
