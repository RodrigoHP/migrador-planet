import { describe, it, expect } from 'vitest'
import {
  parseFormatFields,
  generateFormatComputed,
  generateStyleBindings,
  type StyleRule,
} from './formatStringGenerator'

describe('parseFormatFields', () => {
  it('extracts single field', () => {
    expect(parseFormatFields('{Logradouro}')).toEqual(['Logradouro'])
  })

  it('extracts multiple fields', () => {
    expect(parseFormatFields('{Logradouro}, {Numero} - {Bairro}')).toEqual([
      'Logradouro',
      'Numero',
      'Bairro',
    ])
  })

  it('ignores escaped braces \\{', () => {
    expect(parseFormatFields('\\{literal\\} {Field}')).toEqual(['Field'])
  })

  it('returns empty for empty string', () => {
    expect(parseFormatFields('')).toEqual([])
  })

  it('returns empty for plain text without braces', () => {
    expect(parseFormatFields('hello world')).toEqual([])
  })
})

describe('generateFormatComputed', () => {
  it('generates computed for single field', () => {
    const result = generateFormatComputed('{Logradouro}')
    expect(result).toBe('ko.computed(function() { return data.Logradouro(); })')
  })

  it('generates computed with concatenation for multiple fields', () => {
    const result = generateFormatComputed('{Logradouro}, {Numero}')
    expect(result).toBe(
      'ko.computed(function() { return data.Logradouro() + ", " + data.Numero(); })',
    )
  })

  it('generates computed combining literal and field', () => {
    const result = generateFormatComputed('Rua: {Logradouro}')
    expect(result).toBe('ko.computed(function() { return "Rua: " + data.Logradouro(); })')
  })

  it('handles escaped \\{ as literal', () => {
    const result = generateFormatComputed('\\{literal\\}')
    expect(result).toBe('ko.computed(function() { return "{literal}"; })')
  })

  it('returns empty string for empty input', () => {
    expect(generateFormatComputed('')).toBe('')
    expect(generateFormatComputed('   ')).toBe('')
  })

  it('handles multiple fields with separators', () => {
    const result = generateFormatComputed('{Logradouro}, {Numero} - {Bairro}')
    expect(result).toBe(
      'ko.computed(function() { return data.Logradouro() + ", " + data.Numero() + " - " + data.Bairro(); })',
    )
  })
})

describe('generateStyleBindings', () => {
  it('returns empty string for empty rules', () => {
    expect(generateStyleBindings([])).toBe('')
  })

  it('generates color style binding', () => {
    const rules: StyleRule[] = [
      {
        fieldPath: 'Status',
        operator: '===',
        value: 'active',
        property: 'color',
        propertyValue: '#00ff00',
      },
    ]
    const result = generateStyleBindings(rules)
    expect(result).toBe(
      `data-bind="style: { color: data.Status() === \"active\" ? \"#00ff00\" : '' }"`,
    )
  })

  it('generates visibility style binding', () => {
    const rules: StyleRule[] = [
      {
        fieldPath: 'IsVisible',
        operator: 'notEmpty',
        value: '',
        property: 'visibility',
        propertyValue: 'hidden',
      },
    ]
    const result = generateStyleBindings(rules)
    expect(result).toContain('visibility:')
    expect(result).toContain('data.IsVisible()')
  })

  it('generates background color style binding', () => {
    const rules: StyleRule[] = [
      {
        fieldPath: 'Score',
        operator: '>',
        value: '100',
        property: 'background',
        propertyValue: '#ff0000',
      },
    ]
    const result = generateStyleBindings(rules)
    expect(result).toContain('background:')
    expect(result).toContain('data.Score() > 100')
  })

  it('filters rules with empty fieldPath', () => {
    const rules: StyleRule[] = [
      {
        fieldPath: '',
        operator: '===',
        value: 'x',
        property: 'color',
        propertyValue: '#fff',
      },
    ]
    expect(generateStyleBindings(rules)).toBe('')
  })

  it('combines multiple rules for different properties', () => {
    const rules: StyleRule[] = [
      {
        fieldPath: 'A',
        operator: '===',
        value: '1',
        property: 'color',
        propertyValue: '#fff',
      },
      {
        fieldPath: 'B',
        operator: '===',
        value: '2',
        property: 'background',
        propertyValue: '#000',
      },
    ]
    const result = generateStyleBindings(rules)
    expect(result).toContain('color:')
    expect(result).toContain('background:')
  })
})
