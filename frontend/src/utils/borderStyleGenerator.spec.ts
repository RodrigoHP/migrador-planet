import { describe, it, expect } from 'vitest'
import { generateNodeBorderCss, generateNodeTextCss, generateAllBorderOverrides } from './borderStyleGenerator'

describe('generateNodeBorderCss', () => {
  it('returns empty string for node with no border properties', () => {
    expect(generateNodeBorderCss('n1', {})).toBe('')
  })

  it('generates CSS for a single border side', () => {
    const css = generateNodeBorderCss('n1', {
      border_top_width: 2,
      border_top_style: 'solid',
      border_top_color: '#ff0000',
    })
    expect(css).toContain('[data-node-id="n1"]')
    expect(css).toContain('border-top: 2px solid #ff0000')
  })

  it('generates CSS for all four sides', () => {
    const props = {
      border_top_width: 1, border_top_style: 'solid', border_top_color: '#000',
      border_right_width: 2, border_right_style: 'dashed', border_right_color: '#111',
      border_bottom_width: 3, border_bottom_style: 'dotted', border_bottom_color: '#222',
      border_left_width: 4, border_left_style: 'double', border_left_color: '#333',
    }
    const css = generateNodeBorderCss('n2', props)
    expect(css).toContain('border-top: 1px solid #000')
    expect(css).toContain('border-right: 2px dashed #111')
    expect(css).toContain('border-bottom: 3px dotted #222')
    expect(css).toContain('border-left: 4px double #333')
  })

  it('outputs border: none for sides with width 0', () => {
    const css = generateNodeBorderCss('n3', {
      border_top_width: 0,
      border_top_style: 'none',
    })
    expect(css).toContain('border-top: none')
  })

  it('generates border-radius when corners are set', () => {
    const css = generateNodeBorderCss('n4', {
      border_top_width: 1, border_top_style: 'solid', border_top_color: '#000',
      border_radius_top_left: 5,
      border_radius_top_right: 10,
      border_radius_bottom_right: 0,
      border_radius_bottom_left: 0,
    })
    expect(css).toContain('border-radius: 5px 10px 0 0')
  })

  it('defaults color to #000000 when not provided', () => {
    const css = generateNodeBorderCss('n5', {
      border_top_width: 1,
      border_top_style: 'solid',
    })
    expect(css).toContain('border-top: 1px solid #000000')
  })
})

describe('generateNodeTextCss', () => {
  it('returns empty string for node with no text properties', () => {
    expect(generateNodeTextCss('n1', {})).toBe('')
  })

  it('generates CSS for text-align right', () => {
    const css = generateNodeTextCss('n1', { text_align: 'right' })
    expect(css).toContain('[data-node-id="n1"]')
    expect(css).toContain('text-align: right')
  })

  it('skips default values (none, normal, left)', () => {
    const css = generateNodeTextCss('n1', {
      text_align: 'left',
      text_decoration: 'none',
      font_style: 'normal',
    })
    expect(css).toBe('')
  })

  it('generates multiple text properties', () => {
    const css = generateNodeTextCss('n1', {
      text_align: 'center',
      text_transform: 'uppercase',
      font_style: 'italic',
    })
    expect(css).toContain('text-align: center')
    expect(css).toContain('text-transform: uppercase')
    expect(css).toContain('font-style: italic')
  })

  it('handles text-decoration with multiple values', () => {
    const css = generateNodeTextCss('n1', { text_decoration: 'underline line-through' })
    expect(css).toContain('text-decoration: underline line-through')
  })
})

describe('table cell overrides', () => {
  it('generates border-collapse: separate when border_collapse is false', () => {
    const map = new Map<string, { properties: Record<string, unknown> }>()
    map.set('t1', { properties: { border_collapse: false } })
    const css = generateAllBorderOverrides(map)
    expect(css).toContain('border-collapse: separate')
  })

  it('generates cell border CSS from cells property', () => {
    const map = new Map<string, { properties: Record<string, unknown> }>()
    map.set('t1', {
      properties: {
        cells: {
          '0-1': {
            border: {
              top: { width: 2, style: 'solid', color: '#000' },
              right: { width: 0, style: 'none', color: '#000' },
              bottom: { width: 0, style: 'none', color: '#000' },
              left: { width: 0, style: 'none', color: '#000' },
              radius: { topLeft: 0, topRight: 0, bottomRight: 0, bottomLeft: 0 },
            },
            backgroundColor: '#f0f0f0',
          },
        },
      },
    })
    const css = generateAllBorderOverrides(map)
    expect(css).toContain('tr:nth-child(1) td:nth-child(2)')
    expect(css).toContain('border-top: 2px solid #000')
    expect(css).toContain('background-color: #f0f0f0')
  })

  it('generates cell padding CSS', () => {
    const map = new Map<string, { properties: Record<string, unknown> }>()
    map.set('t1', {
      properties: {
        cells: {
          '1-0': { padding: { top: 4, right: 8, bottom: 4, left: 8 } },
        },
      },
    })
    const css = generateAllBorderOverrides(map)
    expect(css).toContain('padding: 4px 8px 4px 8px')
  })
})

describe('generateAllBorderOverrides', () => {
  it('returns empty string when no nodes have borders', () => {
    const map = new Map<string, { properties: Record<string, unknown> }>()
    map.set('a', { properties: { font_size: 12 } })
    expect(generateAllBorderOverrides(map)).toBe('')
  })

  it('generates overrides for multiple nodes', () => {
    const map = new Map<string, { properties: Record<string, unknown> }>()
    map.set('a', { properties: { border_top_width: 1, border_top_style: 'solid', border_top_color: '#000' } })
    map.set('b', { properties: { border_bottom_width: 2, border_bottom_style: 'dashed', border_bottom_color: '#f00' } })
    const css = generateAllBorderOverrides(map)
    expect(css).toContain('[data-node-id="a"]')
    expect(css).toContain('[data-node-id="b"]')
    expect(css).toContain('Inspector overrides')
  })

  it('does not throw when a node has undefined properties (backend bbox-less nodes)', () => {
    const map = new Map<string, { properties: Record<string, unknown> }>()
    // Simula nó sem properties (vindo do backend sem bbox)
    map.set('no-props', { properties: undefined as unknown as Record<string, unknown> })
    map.set('with-props', { properties: { border_top_width: 1, border_top_style: 'solid', border_top_color: '#000' } })
    expect(() => generateAllBorderOverrides(map)).not.toThrow()
    const css = generateAllBorderOverrides(map)
    expect(css).toContain('[data-node-id="with-props"]')
  })
})
