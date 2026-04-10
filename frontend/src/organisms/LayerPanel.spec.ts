import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import LayerPanel from './LayerPanel.vue'
import { useTemplateStore } from '@/stores/templateStore'
import { useEditorStore } from '@/stores/editorStore'
import type { DocumentTree } from '@/types/template.types'

function makeTree(): DocumentTree {
  return {
    root: {
      id: 'root',
      type: 'page',
      name: 'Root',
      children: [
        {
          id: 'a',
          type: 'field',
          name: 'Field A',
          children: [],
          properties: { zIndex: 10 },
          visibility: true,
        },
        {
          id: 'b',
          type: 'field',
          name: 'Field B',
          children: [],
          properties: { zIndex: 20 },
          visibility: true,
        },
      ],
      properties: {},
      visibility: true,
    },
  }
}

describe('LayerPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const templateStore = useTemplateStore()
    templateStore.loadTree(makeTree())
  })

  it('renders layer items', () => {
    const w = mount(LayerPanel)
    const items = w.findAll('.layer-panel__item')
    expect(items.length).toBeGreaterThanOrEqual(2)
  })

  it('has role=listbox', () => {
    const w = mount(LayerPanel)
    expect(w.find('[role="listbox"]').exists()).toBe(true)
  })

  it('items have role=option', () => {
    const w = mount(LayerPanel)
    const options = w.findAll('[role="option"]')
    expect(options.length).toBeGreaterThanOrEqual(2)
  })

  it('clicking item selects it in editorStore', async () => {
    const editorStore = useEditorStore()
    const w = mount(LayerPanel)
    const items = w.findAll('.layer-panel__item')
    await items[0].trigger('click')
    expect(editorStore.selectedElementId).toBeTruthy()
  })

  it('has aria-live region', () => {
    const w = mount(LayerPanel)
    expect(w.find('[aria-live="polite"]').exists()).toBe(true)
  })

  it('toolbar buttons are disabled when no selection', () => {
    const w = mount(LayerPanel)
    const buttons = w.findAll('.layer-panel__toolbar button')
    // First 4 are layer order buttons, should be disabled
    expect(buttons[0].attributes('disabled')).toBeDefined()
  })

  it('group button disabled when multiSelection < 2', () => {
    const w = mount(LayerPanel)
    const buttons = w.findAll('.layer-panel__toolbar button')
    // Group button (index 4, after separator)
    const groupBtn = buttons.find((b) => b.attributes('title') === 'Group')
    expect(groupBtn?.attributes('disabled')).toBeDefined()
  })
})
