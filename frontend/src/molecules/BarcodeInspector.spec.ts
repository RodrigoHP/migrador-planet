import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import BarcodeInspector, { BARCODE_FORMATS } from './BarcodeInspector.vue'
import type { TreeNode } from '@/types/template.types'

function makeNode(overrides: Partial<TreeNode['properties']> = {}): TreeNode {
  return {
    id: 'barcode-test-1',
    type: 'barcode',
    name: 'Test Barcode',
    children: [],
    properties: {
      barcodeFormat: 'CODE128',
      barcodeField: 'codigoItem',
      barcodeLineWidth: 2,
      barcodeHeight: 60,
      barcodeDisplayValue: true,
      ...overrides,
    },
    visibility: true,
  }
}

describe('BarcodeInspector', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // ── Constants ───────────────────────────────────────────────────────────────

  describe('BARCODE_FORMATS', () => {
    it('contains CODE128', () => {
      expect(BARCODE_FORMATS.some((f) => f.value === 'CODE128')).toBe(true)
    })

    it('contains EAN13', () => {
      expect(BARCODE_FORMATS.some((f) => f.value === 'EAN13')).toBe(true)
    })

    it('contains all required formats', () => {
      const values = BARCODE_FORMATS.map((f) => f.value)
      expect(values).toContain('CODE128')
      expect(values).toContain('CODE39')
      expect(values).toContain('EAN13')
      expect(values).toContain('EAN8')
      expect(values).toContain('UPC')
      expect(values).toContain('ITF')
      expect(values).toContain('MSI')
    })
  })

  // ── Rendering ───────────────────────────────────────────────────────────────

  it('renders without errors', () => {
    const wrapper = mount(BarcodeInspector, {
      props: { node: makeNode() },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('renders format dropdown', () => {
    const wrapper = mount(BarcodeInspector, {
      props: { node: makeNode() },
    })
    // Find the first select element (format selector)
    const selects = wrapper.findAll('select')
    expect(selects.length).toBeGreaterThanOrEqual(1)
  })

  it('renders with no node (null)', () => {
    const wrapper = mount(BarcodeInspector, {
      props: { node: null },
    })
    expect(wrapper.exists()).toBe(true)
  })

  // ── Format selection ────────────────────────────────────────────────────────

  it('displays all format options in the select', () => {
    const wrapper = mount(BarcodeInspector, {
      props: { node: makeNode() },
    })
    const selects = wrapper.findAll('select')
    const formatSelect = selects[0]
    const options = formatSelect?.findAll('option') ?? []
    const optionValues = options.map((o) => (o.element as HTMLOptionElement).value)

    expect(optionValues).toContain('CODE128')
    expect(optionValues).toContain('EAN13')
    expect(optionValues).toContain('MSI')
  })

  it('shows current format from node property', () => {
    const wrapper = mount(BarcodeInspector, {
      props: { node: makeNode({ barcodeFormat: 'EAN13' }) },
    })
    const selects = wrapper.findAll('select')
    const formatSelect = selects[0]!
    expect((formatSelect.element as HTMLSelectElement).value).toBe('EAN13')
  })

  // ── Generated code ──────────────────────────────────────────────────────────

  it('generated code contains the div barcode tag', () => {
    const wrapper = mount(BarcodeInspector, {
      props: { node: makeNode({ barcodeField: 'itemCode' }) },
    })
    const pre = wrapper.find('pre')
    expect(pre.exists()).toBe(true)
    expect(pre.text()).toContain('<div')
    expect(pre.text()).toContain('data-type="barcode"')
  })

  it('generated code contains JsBarcode call', () => {
    const wrapper = mount(BarcodeInspector, {
      props: { node: makeNode({ barcodeField: 'myField', barcodeFormat: 'CODE39' }) },
    })
    const pre = wrapper.find('pre')
    expect(pre.text()).toContain('JsBarcode')
    expect(pre.text()).toContain('CODE39')
    expect(pre.text()).toContain('myField')
  })

  it('generated code includes ko.unwrap for KnockoutJS binding', () => {
    const wrapper = mount(BarcodeInspector, {
      props: { node: makeNode({ barcodeField: 'barField' }) },
    })
    const pre = wrapper.find('pre')
    expect(pre.text()).toContain('ko.unwrap')
  })

  // ── Preview ─────────────────────────────────────────────────────────────────

  it('renders preview bars', () => {
    const wrapper = mount(BarcodeInspector, {
      props: { node: makeNode() },
    })
    const bars = wrapper.findAll('.barcode-inspector__bar')
    expect(bars.length).toBeGreaterThan(0)
  })
})
