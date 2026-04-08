/**
 * Tests for Story 12.3 — Campos: popular fieldNavItems no mapping store
 *
 * Covers:
 * - AC1: loadPipelineFields() populates fieldNavItems (not just fields[])
 * - AC2: Status mapping — mapped→mapped, ambiguous→unconfirmed, unmapped→unmapped
 * - AC3: Counters — mappedCount and totalCount derived from fieldNavItems
 * - AC5: fieldNavItemsByStatus getter groups by status
 * - AC7: Test coverage for loadPipelineFields() populating fieldNavItems
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useMappingStore } from '../mapping'
import { mapConfidenceLevel, parseConfidenceScore } from '../mapping'
import type { AmbiguousField, FieldMappingEntry } from '@/types/pipeline.types'

// ─── Fixtures ────────────────────────────────────────────────────────────────

function makeEntry(
  overrides: Partial<FieldMappingEntry> = {},
): FieldMappingEntry {
  return {
    name: 'Campo Teste',
    path: 'boleto.campo',
    type: 'text',
    status: 'mapped',
    isOptional: false,
    ...overrides,
  }
}

// ─── Setup ───────────────────────────────────────────────────────────────────

describe('mappingStore — loadPipelineFields (Story 12.3)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // ── AC1 ──────────────────────────────────────────────────────────────────

  it('AC1: populates fieldNavItems after loadPipelineFields', () => {
    const store = useMappingStore()
    expect(store.fieldNavItems).toHaveLength(0)

    store.loadPipelineFields([
      makeEntry({ name: 'Beneficiário', path: 'boleto.beneficiario', status: 'mapped' }),
      makeEntry({ name: 'Valor', path: 'boleto.valor', status: 'unmapped' }),
    ])

    expect(store.fieldNavItems).toHaveLength(2)
  })

  it('AC1: fieldNavItems has correct name and path', () => {
    const store = useMappingStore()

    store.loadPipelineFields([
      makeEntry({ name: 'Pagador', path: 'boleto.pagador.nome', status: 'mapped' }),
    ])

    const item = store.fieldNavItems[0]!
    expect(item.name).toBe('Pagador')
    expect(item.path).toBe('boleto.pagador.nome')
  })

  it('AC1: empty entries results in empty fieldNavItems', () => {
    const store = useMappingStore()
    store.loadPipelineFields([])
    expect(store.fieldNavItems).toHaveLength(0)
  })

  // ── AC2: Status mapping ───────────────────────────────────────────────────

  it('AC2: mapped status → fieldNavItem status = "mapped"', () => {
    const store = useMappingStore()
    store.loadPipelineFields([makeEntry({ status: 'mapped' })])
    expect(store.fieldNavItems[0]!.status).toBe('mapped')
  })

  it('AC2: unmapped status → fieldNavItem status = "unmapped"', () => {
    const store = useMappingStore()
    store.loadPipelineFields([makeEntry({ status: 'unmapped' })])
    expect(store.fieldNavItems[0]!.status).toBe('unmapped')
  })

  it('AC2: ambiguous status → fieldNavItem status = "unconfirmed"', () => {
    const store = useMappingStore()
    store.loadPipelineFields([makeEntry({ status: 'ambiguous' })])
    expect(store.fieldNavItems[0]!.status).toBe('unconfirmed')
    expect(store.fieldNavItems[0]!.isAmbiguous).toBe(true)
  })

  it('AC2: optional status → fieldNavItem status = "unmapped"', () => {
    const store = useMappingStore()
    store.loadPipelineFields([makeEntry({ status: 'optional' })])
    expect(store.fieldNavItems[0]!.status).toBe('unmapped')
  })

  // ── AC3: Counters via fieldNavItems ───────────────────────────────────────

  it('AC3: mappedCount computed from fieldNavItems with mixed statuses', () => {
    const store = useMappingStore()
    store.loadPipelineFields([
      makeEntry({ name: 'A', path: 'a', status: 'mapped' }),
      makeEntry({ name: 'B', path: 'b', status: 'mapped' }),
      makeEntry({ name: 'C', path: 'c', status: 'unmapped' }),
      makeEntry({ name: 'D', path: 'd', status: 'ambiguous' }),
    ])

    const mappedCount = store.fieldNavItems.filter((f) => f.status === 'mapped').length
    const totalCount = store.fieldNavItems.length
    expect(mappedCount).toBe(2)
    expect(totalCount).toBe(4)
  })

  // ── AC5: fieldNavItemsByStatus getter ─────────────────────────────────────

  it('AC5: fieldNavItemsByStatus groups items by status', () => {
    const store = useMappingStore()
    store.loadPipelineFields([
      makeEntry({ name: 'A', path: 'a', status: 'mapped' }),
      makeEntry({ name: 'B', path: 'b', status: 'mapped' }),
      makeEntry({ name: 'C', path: 'c', status: 'unmapped' }),
      makeEntry({ name: 'D', path: 'd', status: 'ambiguous' }),
    ])

    const byStatus = store.fieldNavItemsByStatus
    expect(byStatus.mapped).toHaveLength(2)
    expect(byStatus.unmapped).toHaveLength(1)
    expect(byStatus.unconfirmed).toHaveLength(1)
  })

  it('AC5: fieldNavItemsByStatus returns empty arrays when store is empty', () => {
    const store = useMappingStore()
    const byStatus = store.fieldNavItemsByStatus
    expect(byStatus.mapped).toHaveLength(0)
    expect(byStatus.unmapped).toHaveLength(0)
    expect(byStatus.unconfirmed).toHaveLength(0)
  })

  // ── Type defaults ─────────────────────────────────────────────────────────

  it('type defaults to "string" for pipeline field entries', () => {
    const store = useMappingStore()
    store.loadPipelineFields([makeEntry()])
    expect(store.fieldNavItems[0]!.type).toBe('string')
  })

  // ── isOptional propagated ─────────────────────────────────────────────────

  it('isOptional is propagated from entry', () => {
    const store = useMappingStore()
    store.loadPipelineFields([makeEntry({ isOptional: true })])
    expect(store.fieldNavItems[0]!.isOptional).toBe(true)
  })

  // ── Fallback name when entry name is empty ────────────────────────────────

  it('uses path as fallback name when entry name is empty', () => {
    const store = useMappingStore()
    store.loadPipelineFields([makeEntry({ name: '', path: 'boleto.valor' })])
    expect(store.fieldNavItems[0]!.name).toBe('boleto.valor')
  })

  it('uses "Campo" as fallback when both name and path are empty', () => {
    const store = useMappingStore()
    store.loadPipelineFields([makeEntry({ name: '', path: '' })])
    expect(store.fieldNavItems[0]!.name).toBe('Campo')
  })

  // ── Bug fix: candidates populated from ambiguous_fields (Story 28.3) ────────

  it('populates candidates from ambiguous_fields when status is ambiguous', () => {
    const store = useMappingStore()
    const ambiguousFields: AmbiguousField[] = [
      { name: 'NOME', candidates: ['BOLETO.SACADO.NOME', 'BOLETO.BENEFICIARIO.NOME'], confidence: 0.72 },
    ]
    store.loadPipelineFields(
      [makeEntry({ name: 'NOME', path: '', status: 'ambiguous' })],
      ambiguousFields,
    )
    const item = store.fieldNavItems[0]!
    expect(item.isAmbiguous).toBe(true)
    expect(item.candidates).toHaveLength(2)
    expect(item.candidates![0]!.path).toBe('BOLETO.SACADO.NOME')
    expect(item.candidates![0]!.confidence).toBe(0.72)
  })

  it('leaves candidates undefined for non-ambiguous fields even when ambiguousFields is provided', () => {
    const store = useMappingStore()
    const ambiguousFields: AmbiguousField[] = [
      { name: 'NOME', candidates: ['BOLETO.SACADO.NOME'], confidence: 0.8 },
    ]
    store.loadPipelineFields(
      [makeEntry({ name: 'NOME', path: 'boleto.nome', status: 'mapped' })],
      ambiguousFields,
    )
    expect(store.fieldNavItems[0]!.candidates).toBeUndefined()
  })

  it('leaves candidates undefined for ambiguous field not in ambiguous_fields list', () => {
    const store = useMappingStore()
    store.loadPipelineFields(
      [makeEntry({ name: 'NR_BANCO', path: '', status: 'ambiguous' })],
      [],
    )
    expect(store.fieldNavItems[0]!.candidates).toBeUndefined()
  })

  it('backward compat: calling without ambiguousFields leaves candidates undefined', () => {
    const store = useMappingStore()
    store.loadPipelineFields([makeEntry({ status: 'ambiguous' })])
    expect(store.fieldNavItems[0]!.candidates).toBeUndefined()
  })

  // ── Reload clears previous state ──────────────────────────────────────────

  it('calling loadPipelineFields twice replaces previous fieldNavItems', () => {
    const store = useMappingStore()
    store.loadPipelineFields([makeEntry({ name: 'First', path: 'first' })])
    expect(store.fieldNavItems).toHaveLength(1)

    store.loadPipelineFields([
      makeEntry({ name: 'Second', path: 'second' }),
      makeEntry({ name: 'Third', path: 'third' }),
    ])
    expect(store.fieldNavItems).toHaveLength(2)
    expect(store.fieldNavItems[0]!.name).toBe('Second')
  })

  // ── Bug fix: stage5 ambiguous_fields format — candidates as [{path, score}] dicts ─
  // stage5_template_generation.py embeds full field_mapping entries in ambiguous_fields,
  // with candidates as [{path: string, score: number}]. The frontend must extract them
  // correctly — not treat dict objects as path strings (which broke semanticLabel in modal).

  it('extracts candidates from entry.candidates (stage5 dict format) when available', () => {
    const store = useMappingStore()
    // Simulate stage5 format: entry has candidates as [{path, score}]
    const entryWithCandidates = {
      ...makeEntry({ name: 'ENDERECO', path: 'BOLETO.SACADO.ENDERECO', status: 'ambiguous' }),
      candidates: [
        { path: 'BOLETO.SACADO.ENDERECO', score: 0.78 },
        { path: 'BOLETO.SACADO.LOGRADOURO', score: 0.61 },
      ],
      block_id: 'blk-001',
    } as unknown as FieldMappingEntry

    store.loadPipelineFields([entryWithCandidates], [])
    const item = store.fieldNavItems[0]!
    expect(item.isAmbiguous).toBe(true)
    // candidates must have string paths (not objects)
    expect(typeof item.candidates![0]!.path).toBe('string')
    expect(item.candidates![0]!.path).toBe('BOLETO.SACADO.ENDERECO')
    expect(item.candidates![0]!.confidence).toBeCloseTo(0.78)
    expect(item.candidates![1]!.path).toBe('BOLETO.SACADO.LOGRADOURO')
  })

  it('falls back to ambiguous_fields string candidates when entry.candidates is absent', () => {
    // Simulates saved project / legacy format without entry.candidates
    const store = useMappingStore()
    const ambiguousFields: AmbiguousField[] = [
      { name: 'NOME', candidates: ['BOLETO.SACADO.NOME', 'BOLETO.BENEFICIARIO.NOME'], confidence: 0.70 },
    ]
    store.loadPipelineFields(
      [makeEntry({ name: 'NOME', path: '', status: 'ambiguous' })],
      ambiguousFields,
    )
    const item = store.fieldNavItems[0]!
    expect(item.candidates).toHaveLength(2)
    expect(item.candidates![0]!.path).toBe('BOLETO.SACADO.NOME')
    expect(item.candidates![0]!.confidence).toBe(0.70)
  })

  // ── Story 34.1: Confidence propagation ─────────────────────────────────────

  it('34.1: propagates numeric confidence score to fieldNavItem', () => {
    const store = useMappingStore()
    store.loadPipelineFields([makeEntry({ confidence: 85 })])
    const item = store.fieldNavItems[0]!
    expect(item.confidenceScore).toBe(85)
    expect(item.confidenceLevel).toBe('high')
  })

  it('34.1: propagates string confidence to fieldNavItem', () => {
    const store = useMappingStore()
    store.loadPipelineFields([makeEntry({ confidence: 'low' })])
    const item = store.fieldNavItems[0]!
    expect(item.confidenceLevel).toBe('low')
  })

  it('34.1: defaults to medium when confidence is undefined', () => {
    const store = useMappingStore()
    store.loadPipelineFields([makeEntry()])
    const item = store.fieldNavItems[0]!
    expect(item.confidenceLevel).toBe('medium')
  })

  it('34.1: maps numeric confidence to legacy fields.confidence', () => {
    const store = useMappingStore()
    store.loadPipelineFields([makeEntry({ confidence: 30 })])
    const field = store.fields[0]!
    expect(field.confidence).toBe('low')
  })
})

// ── Story 34.1: mapConfidenceLevel and parseConfidenceScore helpers ────────

describe('mapConfidenceLevel (Story 34.1)', () => {
  it('maps <40 to low', () => {
    expect(mapConfidenceLevel(20)).toBe('low')
    expect(mapConfidenceLevel(0)).toBe('low')
    expect(mapConfidenceLevel(39)).toBe('low')
  })

  it('maps 40-75 to medium', () => {
    expect(mapConfidenceLevel(40)).toBe('medium')
    expect(mapConfidenceLevel(60)).toBe('medium')
    expect(mapConfidenceLevel(75)).toBe('medium')
  })

  it('maps >75 to high', () => {
    expect(mapConfidenceLevel(76)).toBe('high')
    expect(mapConfidenceLevel(100)).toBe('high')
  })

  it('handles string values', () => {
    expect(mapConfidenceLevel('low')).toBe('low')
    expect(mapConfidenceLevel('medium')).toBe('medium')
    expect(mapConfidenceLevel('high')).toBe('high')
    expect(mapConfidenceLevel('HIGH')).toBe('high')
  })

  it('handles numeric strings', () => {
    expect(mapConfidenceLevel('85')).toBe('high')
    expect(mapConfidenceLevel('30')).toBe('low')
  })

  it('defaults to medium for undefined', () => {
    expect(mapConfidenceLevel(undefined)).toBe('medium')
  })
})

describe('parseConfidenceScore (Story 34.1)', () => {
  it('returns numeric value as-is', () => {
    expect(parseConfidenceScore(85)).toBe(85)
  })

  it('parses numeric strings', () => {
    expect(parseConfidenceScore('72')).toBe(72)
  })

  it('maps string categories to representative scores', () => {
    expect(parseConfidenceScore('low')).toBe(20)
    expect(parseConfidenceScore('medium')).toBe(60)
    expect(parseConfidenceScore('high')).toBe(90)
  })

  it('returns undefined for undefined input', () => {
    expect(parseConfidenceScore(undefined)).toBeUndefined()
  })
})
