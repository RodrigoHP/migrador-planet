import { describe, it, expect } from 'vitest'
import { hexToRgba, parseRgba, parseColor, isValidColor } from './colorUtils'

describe('hexToRgba', () => {
  it('converts hex + 100% to rgba with alpha 1.00', () => {
    expect(hexToRgba('#336699', 100)).toBe('rgba(51, 102, 153, 1.00)')
  })

  it('converts hex + 80% to rgba with alpha 0.80', () => {
    expect(hexToRgba('#336699', 80)).toBe('rgba(51, 102, 153, 0.80)')
  })

  it('converts hex + 0% to rgba with alpha 0.00', () => {
    expect(hexToRgba('#ff0000', 0)).toBe('rgba(255, 0, 0, 0.00)')
  })

  it('clamps opacity to 0-100', () => {
    expect(hexToRgba('#000000', 150)).toBe('rgba(0, 0, 0, 1.00)')
    expect(hexToRgba('#000000', -10)).toBe('rgba(0, 0, 0, 0.00)')
  })
})

describe('parseRgba', () => {
  it('parses rgba string', () => {
    expect(parseRgba('rgba(51, 102, 153, 0.80)')).toEqual({ hex: '#336699', opacity: 80 })
  })

  it('parses rgb string (no alpha)', () => {
    expect(parseRgba('rgb(255, 0, 0)')).toEqual({ hex: '#ff0000', opacity: 100 })
  })

  it('returns null for invalid string', () => {
    expect(parseRgba('notacolor')).toBeNull()
  })
})

describe('parseColor', () => {
  it('parses hex color', () => {
    expect(parseColor('#ff0000')).toEqual({ hex: '#ff0000', opacity: 100 })
  })

  it('parses shorthand hex', () => {
    expect(parseColor('#f00')).toEqual({ hex: '#ff0000', opacity: 100 })
  })

  it('parses rgba', () => {
    expect(parseColor('rgba(0, 0, 0, 0.5)')).toEqual({ hex: '#000000', opacity: 50 })
  })

  it('returns null for transparent', () => {
    expect(parseColor('transparent')).toBeNull()
  })

  it('returns null for inherit', () => {
    expect(parseColor('inherit')).toBeNull()
  })

  it('returns null for empty string', () => {
    expect(parseColor('')).toBeNull()
  })
})

describe('isValidColor', () => {
  it('validates hex colors', () => {
    expect(isValidColor('#ff0000')).toBe(true)
    expect(isValidColor('#f00')).toBe(true)
  })

  it('validates transparent and inherit', () => {
    expect(isValidColor('transparent')).toBe(true)
    expect(isValidColor('inherit')).toBe(true)
  })

  it('validates rgba', () => {
    expect(isValidColor('rgba(0, 0, 0, 0.5)')).toBe(true)
  })

  it('rejects invalid strings', () => {
    expect(isValidColor('notacolor')).toBe(false)
    expect(isValidColor('')).toBe(false)
  })
})
