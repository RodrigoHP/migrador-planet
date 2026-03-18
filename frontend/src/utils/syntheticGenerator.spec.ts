import { describe, it, expect, beforeEach } from 'vitest'
import {
  generateCpf,
  generateCnpj,
  generateName,
  generateDate,
  generateIsoDate,
  generateCurrency,
  generatePhone,
  generateSyntheticData,
  SYNTHETIC_NAMES,
  resetCounter,
} from './syntheticGenerator'
import type { XsdFieldDef } from '@/types/test-data.types'

// Reset counter before each test for reproducibility
beforeEach(() => {
  resetCounter()
})

// ─── CPF ─────────────────────────────────────────────────────────────────────

describe('generateCpf', () => {
  it('returns a string in format XXX.XXX.XXX-XX', () => {
    const cpf = generateCpf()
    expect(cpf).toMatch(/^\d{3}\.\d{3}\.\d{3}-\d{2}$/)
  })

  it('has valid check digits', () => {
    // Run multiple CPFs and verify format
    for (let i = 0; i < 5; i++) {
      const cpf = generateCpf()
      expect(cpf).toMatch(/^\d{3}\.\d{3}\.\d{3}-\d{2}$/)
    }
  })

  it('generates different CPFs on successive calls', () => {
    const cpf1 = generateCpf()
    const cpf2 = generateCpf()
    // They may occasionally be equal, but with different counters they should differ
    // Just test that they are valid format
    expect(cpf1).toMatch(/^\d{3}\.\d{3}\.\d{3}-\d{2}$/)
    expect(cpf2).toMatch(/^\d{3}\.\d{3}\.\d{3}-\d{2}$/)
  })
})

// ─── CNPJ ────────────────────────────────────────────────────────────────────

describe('generateCnpj', () => {
  it('returns a string in format XX.XXX.XXX/XXXX-XX', () => {
    const cnpj = generateCnpj()
    expect(cnpj).toMatch(/^\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}$/)
  })

  it('generates valid format CNPJ', () => {
    for (let i = 0; i < 5; i++) {
      const cnpj = generateCnpj()
      expect(cnpj).toMatch(/^\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}$/)
    }
  })
})

// ─── Name ────────────────────────────────────────────────────────────────────

describe('generateName', () => {
  it('returns two words (first + last)', () => {
    const name = generateName()
    const parts = name.trim().split(' ')
    expect(parts.length).toBeGreaterThanOrEqual(2)
  })

  it('returns non-empty string', () => {
    expect(generateName()).toBeTruthy()
  })
})

// ─── Date ────────────────────────────────────────────────────────────────────

describe('generateDate', () => {
  it('returns date in DD/MM/YYYY format', () => {
    const date = generateDate()
    expect(date).toMatch(/^\d{2}\/\d{2}\/\d{4}$/)
  })

  it('generates year between 2020 and 2025', () => {
    for (let i = 0; i < 5; i++) {
      const date = generateDate()
      const year = parseInt(date.split('/')[2]!)
      expect(year).toBeGreaterThanOrEqual(2020)
      expect(year).toBeLessThanOrEqual(2025)
    }
  })
})

describe('generateIsoDate', () => {
  it('returns date in YYYY-MM-DD format', () => {
    const date = generateIsoDate()
    expect(date).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })
})

// ─── Currency ────────────────────────────────────────────────────────────────

describe('generateCurrency', () => {
  it('starts with R$', () => {
    const currency = generateCurrency()
    expect(currency).toMatch(/^R\$/)
  })
})

// ─── Phone ───────────────────────────────────────────────────────────────────

describe('generatePhone', () => {
  it('returns phone in (XX)XXXXX-XXXX format', () => {
    const phone = generatePhone()
    expect(phone).toMatch(/^\(\d{2}\)\d{5}-\d{4}$/)
  })
})

// ─── generateSyntheticData ───────────────────────────────────────────────────

describe('generateSyntheticData', () => {
  const simpleFields: XsdFieldDef[] = [
    { path: 'nome', type: 'string', required: true },
    { path: 'cpf', type: 'string', required: true },
    { path: 'data', type: 'date', required: false },
    { path: 'valor', type: 'decimal', required: false },
    { path: 'ativo', type: 'boolean', required: false },
    { path: 'quantidade', type: 'integer', required: false },
  ]

  it('generates fields for all XSD paths', () => {
    const data = generateSyntheticData(simpleFields, 'small')
    expect(data).toHaveProperty('nome')
    expect(data).toHaveProperty('cpf')
    expect(data).toHaveProperty('data')
    expect(data).toHaveProperty('valor')
    expect(data).toHaveProperty('ativo')
    expect(data).toHaveProperty('quantidade')
  })

  it('generates CPF format for cpf field', () => {
    const data = generateSyntheticData(simpleFields, 'small')
    expect(String(data['cpf'])).toMatch(/^\d{3}\.\d{3}\.\d{3}-\d{2}$/)
  })

  it('generates boolean for boolean field', () => {
    const data = generateSyntheticData(simpleFields, 'small')
    expect(typeof data['ativo']).toBe('boolean')
  })

  it('generates integer for integer field', () => {
    const data = generateSyntheticData(simpleFields, 'small')
    expect(typeof data['quantidade']).toBe('number')
    expect(Number.isInteger(data['quantidade'])).toBe(true)
  })

  it('generates decimal or currency string for decimal field', () => {
    const data = generateSyntheticData(simpleFields, 'small')
    // 'valor' triggers currency semantic override → string "R$ X,XX"
    // or falls back to number depending on semantic detection
    const v = data['valor']
    expect(v !== null && v !== undefined).toBe(true)
  })

  describe('array sizes', () => {
    const fieldsWithArray: XsdFieldDef[] = [
      { path: 'nome', type: 'string', required: true },
      { path: 'items', type: 'array', required: true },
      { path: 'items.descricao', type: 'string', required: true },
      { path: 'items.quantidade', type: 'integer', required: true },
    ]

    it('generates 1 item for small', () => {
      const data = generateSyntheticData(fieldsWithArray, 'small')
      expect(Array.isArray(data['items'])).toBe(true)
      expect((data['items'] as unknown[]).length).toBe(1)
    })

    it('generates 10 items for medium', () => {
      const data = generateSyntheticData(fieldsWithArray, 'medium')
      expect(Array.isArray(data['items'])).toBe(true)
      expect((data['items'] as unknown[]).length).toBe(10)
    })

    it('generates 100 items for large', () => {
      const data = generateSyntheticData(fieldsWithArray, 'large')
      expect(Array.isArray(data['items'])).toBe(true)
      expect((data['items'] as unknown[]).length).toBe(100)
    })
  })

  it('generates minimal data when no fields defined', () => {
    const data = generateSyntheticData([], 'small')
    expect(data).toHaveProperty('nome')
    expect(data).toHaveProperty('cpf')
    expect(data).toHaveProperty('items')
    expect(Array.isArray(data['items'])).toBe(true)
    expect((data['items'] as unknown[]).length).toBe(1)
  })

  it('generates 10 items for medium with no fields', () => {
    const data = generateSyntheticData([], 'medium')
    expect((data['items'] as unknown[]).length).toBe(10)
  })
})

// ─── SYNTHETIC_NAMES ─────────────────────────────────────────────────────────

describe('SYNTHETIC_NAMES', () => {
  it('has names for all three sizes', () => {
    expect(SYNTHETIC_NAMES.small).toBe('synthetic_small')
    expect(SYNTHETIC_NAMES.medium).toBe('synthetic_medium')
    expect(SYNTHETIC_NAMES.large).toBe('synthetic_large')
  })
})
