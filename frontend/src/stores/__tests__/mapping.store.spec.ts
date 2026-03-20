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
import type { FieldMappingEntry } from '@/types/pipeline.types'

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
})
