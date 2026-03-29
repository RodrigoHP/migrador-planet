import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'
import ElementInspector from './ElementInspector.vue'
import type { TreeNode } from '@/types/template.types'

// ─── Mocks ────────────────────────────────────────────────────────────────────

vi.mock('@/composables/useFontCascade', () => ({
  useFontCascade: () => ({
    fontStatus: ref('not_found'),
    suggestedAlternative: ref(null),
    suggestions: ref([]),
    isLoading: ref(false),
    resolveFontCascade: vi.fn().mockResolvedValue({ fontStatus: 'not_found', suggestedAlternative: null, suggestions: [] }),
  }),
}))

vi.mock('@/composables/useBibliotecas', () => ({
  useBibliotecas: () => ({
    files: ref([]),
    isLoading: ref(false),
    error: ref(null),
    loadFiles: vi.fn(),
    addFile: vi.fn(),
    removeFile: vi.fn(),
    getByCategory: vi.fn().mockReturnValue([]),
    isFileReferenced: vi.fn().mockReturnValue(false),
  }),
}))

vi.mock('@/stores/templateStore', () => ({
  useTemplateStore: () => ({
    updateNodeProperty: vi.fn(),
    flatNodes: new Map(),
  }),
}))

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeNode(overrides: Partial<TreeNode> & { type?: string } = {}): TreeNode {
  return {
    id: 'node-el-1',
    type: 'field',
    name: 'Campo',
    binding: '',
    isOptional: false,
    children: [],
    properties: {},
    visibility: true,
    ...overrides,
  } as TreeNode
}

// ─── isTableCell detection tests (Story 14.14) ────────────────────────────────

describe('ElementInspector — isTableCell detection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('does NOT show Vertical Align for a regular field node', () => {
    const wrapper = mount(ElementInspector, {
      props: { node: makeNode({ type: 'field' }) },
    })
    expect(wrapper.text()).not.toContain('Alinhamento Vertical')
    wrapper.unmount()
  })

  it('does NOT show Vertical Align for a text node without is_table_cell', () => {
    const wrapper = mount(ElementInspector, {
      props: { node: makeNode({ type: 'text' }) },
    })
    expect(wrapper.text()).not.toContain('Alinhamento Vertical')
    wrapper.unmount()
  })

  it('shows Vertical Align when properties.is_table_cell is true', () => {
    const wrapper = mount(ElementInspector, {
      props: {
        node: makeNode({ type: 'field', properties: { is_table_cell: true } }),
      },
    })
    expect(wrapper.text()).toContain('Alinhamento Vertical')
    wrapper.unmount()
  })

  it('shows Vertical Align when node.type is "table-cell"', () => {
    const wrapper = mount(ElementInspector, {
      props: { node: makeNode({ type: 'table-cell' as TreeNode['type'] }) },
    })
    expect(wrapper.text()).toContain('Alinhamento Vertical')
    wrapper.unmount()
  })

  it('shows Vertical Align when node.type contains "cell" (e.g. future variant)', () => {
    const wrapper = mount(ElementInspector, {
      props: { node: makeNode({ type: 'header-cell' as TreeNode['type'] }) },
    })
    expect(wrapper.text()).toContain('Alinhamento Vertical')
    wrapper.unmount()
  })

  it('does NOT show Vertical Align when is_table_cell is false', () => {
    const wrapper = mount(ElementInspector, {
      props: {
        node: makeNode({ type: 'field', properties: { is_table_cell: false } }),
      },
    })
    expect(wrapper.text()).not.toContain('Alinhamento Vertical')
    wrapper.unmount()
  })

  it('does NOT show Vertical Align when node is null', () => {
    const wrapper = mount(ElementInspector, {
      props: { node: null },
    })
    expect(wrapper.text()).not.toContain('Alinhamento Vertical')
    wrapper.unmount()
  })
})
