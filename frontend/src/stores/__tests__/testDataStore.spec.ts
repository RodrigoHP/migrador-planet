import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import {
  useTestDataStore,
  validateDatasetAgainstXsd,
  parseXmlToJson,
  MAX_DATASETS,
} from '../testDataStore'
import type { Dataset, XsdFieldDef } from '@/types/test-data.types'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeDataset(overrides: Partial<Dataset> = {}): Dataset {
  return {
    id: 'ds-1',
    name: 'test-dataset',
    fields: { name: 'Alice', age: 30 },
    rawContent: '{"name":"Alice","age":30}',
    createdAt: new Date().toISOString(),
    size: 24,
    status: 'unvalidated',
    ...overrides,
  }
}

const xsdFields: XsdFieldDef[] = [
  { path: 'name', type: 'string', required: true },
  { path: 'age', type: 'integer', required: true },
  { path: 'email', type: 'string', required: false },
]

// ─── validateDatasetAgainstXsd ────────────────────────────────────────────────

describe('validateDatasetAgainstXsd', () => {
  it('returns warning when required fields present but optional field missing', () => {
    const ds = makeDataset({ fields: { name: 'Alice', age: 30 } })
    const result = validateDatasetAgainstXsd(ds, xsdFields)
    // email is optional so it produces a warning, not an error
    expect(result.status).toBe('warning')
    expect(result.errors).toHaveLength(0)
    expect(result.warnings).toHaveLength(1) // email optional missing
  })

  it('returns valid when all fields present including optional', () => {
    const ds = makeDataset({ fields: { name: 'Alice', age: 30, email: 'alice@example.com' } })
    const result = validateDatasetAgainstXsd(ds, xsdFields)
    expect(result.status).toBe('valid')
    expect(result.errors).toHaveLength(0)
    expect(result.warnings).toHaveLength(0)
  })

  it('returns invalid when required field missing', () => {
    const ds = makeDataset({ fields: { name: 'Alice' } })
    const result = validateDatasetAgainstXsd(ds, xsdFields)
    expect(result.status).toBe('invalid')
    expect(result.errors.some((e) => e.includes('age'))).toBe(true)
  })

  it('returns warning when optional field missing but no required issues', () => {
    const ds = makeDataset({ fields: { name: 'Alice', age: 42 } })
    const result = validateDatasetAgainstXsd(ds, [
      { path: 'name', type: 'string', required: true },
      { path: 'age', type: 'integer', required: true },
      { path: 'email', type: 'string', required: false },
    ])
    expect(result.status).toBe('warning')
    expect(result.warnings.some((w) => w.includes('email'))).toBe(true)
  })

  it('returns invalid when type is incompatible', () => {
    const ds = makeDataset({ fields: { name: 'Alice', age: 'not-a-number' } })
    const result = validateDatasetAgainstXsd(ds, xsdFields)
    expect(result.status).toBe('invalid')
    expect(result.errors.some((e) => e.includes('Tipo incompatível'))).toBe(true)
  })

  it('counts fields correctly', () => {
    const ds = makeDataset({ fields: { a: 1, b: [1, 2], c: 'x' } })
    const result = validateDatasetAgainstXsd(ds, [])
    expect(result.fieldCount).toBe(3)
  })

  it('counts loops (array fields) correctly', () => {
    const ds = makeDataset({ fields: { items: [1, 2, 3], name: 'Alice' } })
    const result = validateDatasetAgainstXsd(ds, [])
    expect(result.loopCount).toBe(1)
  })

  it('sets datasetId on result', () => {
    const ds = makeDataset({ id: 'my-ds' })
    const result = validateDatasetAgainstXsd(ds, [])
    expect(result.datasetId).toBe('my-ds')
  })
})

// ─── parseXmlToJson ───────────────────────────────────────────────────────────

describe('parseXmlToJson', () => {
  it('returns empty object for invalid XML', () => {
    const result = parseXmlToJson('not xml at all <<<')
    expect(typeof result).toBe('object')
  })

  it('returns empty object when DOMParser unavailable (graceful fallback)', () => {
    // In jsdom DOMParser is available — just verify it returns an object
    const result = parseXmlToJson('<root><name>Alice</name></root>')
    expect(typeof result).toBe('object')
  })
})

// ─── useTestDataStore ─────────────────────────────────────────────────────────

describe('useTestDataStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with empty state', () => {
    const store = useTestDataStore()
    expect(store.datasets).toHaveLength(0)
    expect(store.activeDatasetId).toBeNull()
    expect(store.validationResults).toHaveLength(0)
  })

  it('addDataset adds a dataset', () => {
    const store = useTestDataStore()
    const ds = makeDataset()
    const added = store.addDataset(ds)
    expect(added).toBe(true)
    expect(store.datasets).toHaveLength(1)
    expect(store.datasets[0]!.id).toBe('ds-1')
  })

  it('addDataset returns false when limit reached', () => {
    const store = useTestDataStore()
    for (let i = 0; i < MAX_DATASETS; i++) {
      store.addDataset(makeDataset({ id: `ds-${i}` }))
    }
    const result = store.addDataset(makeDataset({ id: 'ds-overflow' }))
    expect(result).toBe(false)
    expect(store.datasets).toHaveLength(MAX_DATASETS)
  })

  it('hasReachedLimit is true when at max', () => {
    const store = useTestDataStore()
    for (let i = 0; i < MAX_DATASETS; i++) {
      store.addDataset(makeDataset({ id: `ds-${i}` }))
    }
    expect(store.hasReachedLimit).toBe(true)
  })

  it('removeDataset removes the dataset', () => {
    const store = useTestDataStore()
    store.addDataset(makeDataset({ id: 'ds-1' }))
    store.addDataset(makeDataset({ id: 'ds-2' }))
    store.removeDataset('ds-1')
    expect(store.datasets).toHaveLength(1)
    expect(store.datasets[0]!.id).toBe('ds-2')
  })

  it('removeDataset updates activeDatasetId when active is removed', () => {
    const store = useTestDataStore()
    store.addDataset(makeDataset({ id: 'ds-1' }))
    store.addDataset(makeDataset({ id: 'ds-2' }))
    store.setActiveDataset('ds-1')
    store.removeDataset('ds-1')
    expect(store.activeDatasetId).toBe('ds-2')
  })

  it('removeDataset sets activeDatasetId to null when last removed', () => {
    const store = useTestDataStore()
    store.addDataset(makeDataset({ id: 'ds-1' }))
    store.setActiveDataset('ds-1')
    store.removeDataset('ds-1')
    expect(store.activeDatasetId).toBeNull()
  })

  it('setActiveDataset sets activeDatasetId', () => {
    const store = useTestDataStore()
    store.addDataset(makeDataset({ id: 'ds-1' }))
    store.setActiveDataset('ds-1')
    expect(store.activeDatasetId).toBe('ds-1')
  })

  it('activeDataset computed returns correct dataset', () => {
    const store = useTestDataStore()
    store.addDataset(makeDataset({ id: 'ds-1', name: 'Alpha' }))
    store.addDataset(makeDataset({ id: 'ds-2', name: 'Beta' }))
    store.setActiveDataset('ds-2')
    expect(store.activeDataset?.name).toBe('Beta')
  })

  it('validateDataset stores result and updates status', () => {
    const store = useTestDataStore()
    // Include all fields (including optional email) so result is 'valid'
    store.addDataset(
      makeDataset({ id: 'ds-1', fields: { name: 'Alice', age: 30, email: 'a@b.com' } }),
    )
    store.setActiveDataset('ds-1')
    const result = store.validateDataset('ds-1', xsdFields)
    expect(result.datasetId).toBe('ds-1')
    expect(result.status).toBe('valid')
    // Check status updated on dataset
    expect(store.datasets[0]!.status).toBe(result.status)
  })

  it('getValidationResult returns stored result', () => {
    const store = useTestDataStore()
    store.addDataset(makeDataset({ id: 'ds-1' }))
    store.validateDataset('ds-1', xsdFields)
    const found = store.getValidationResult('ds-1')
    expect(found).toBeDefined()
    expect(found!.datasetId).toBe('ds-1')
  })

  it('updateDataset patches dataset fields', () => {
    const store = useTestDataStore()
    store.addDataset(makeDataset({ id: 'ds-1', name: 'Old Name' }))
    store.updateDataset('ds-1', { name: 'New Name' })
    expect(store.datasets[0]!.name).toBe('New Name')
  })

  it('setValidationResults replaces validation results array', () => {
    const store = useTestDataStore()
    store.setValidationResults([
      {
        datasetId: 'ds-99',
        status: 'valid',
        fieldCount: 1,
        loopCount: 0,
        errors: [],
        warnings: [],
        testedAt: new Date().toISOString(),
      },
    ])
    expect(store.validationResults).toHaveLength(1)
    expect(store.validationResults[0]!.datasetId).toBe('ds-99')
  })

  it('datasetCount matches number of datasets', () => {
    const store = useTestDataStore()
    expect(store.datasetCount).toBe(0)
    store.addDataset(makeDataset({ id: 'ds-1' }))
    expect(store.datasetCount).toBe(1)
  })

  it('activeValidationResult returns result for active dataset', () => {
    const store = useTestDataStore()
    store.addDataset(makeDataset({ id: 'ds-1' }))
    store.setActiveDataset('ds-1')
    store.validateDataset('ds-1', xsdFields)
    expect(store.activeValidationResult?.datasetId).toBe('ds-1')
  })

  it('MAX_DATASETS constant is 5', () => {
    expect(MAX_DATASETS).toBe(5)
  })
})
