import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AlignmentToolbar from './AlignmentToolbar.vue'

const baseProps = {
  visible: true,
  position: { x: 100, y: 200 },
  selectedCount: 3,
}

describe('AlignmentToolbar', () => {
  it('renders when visible=true', () => {
    const w = mount(AlignmentToolbar, { props: baseProps })
    expect(w.find('.alignment-toolbar').exists()).toBe(true)
  })

  it('does not render when visible=false', () => {
    const w = mount(AlignmentToolbar, { props: { ...baseProps, visible: false } })
    expect(w.find('.alignment-toolbar').exists()).toBe(false)
  })

  it('renders 8 buttons', () => {
    const w = mount(AlignmentToolbar, { props: baseProps })
    expect(w.findAll('.alignment-toolbar__btn')).toHaveLength(8)
  })

  it('has role=toolbar and aria-label', () => {
    const w = mount(AlignmentToolbar, { props: baseProps })
    const toolbar = w.find('.alignment-toolbar')
    expect(toolbar.attributes('role')).toBe('toolbar')
    expect(toolbar.attributes('aria-label')).toBe('Ferramentas de alinhamento')
  })

  it('distribute buttons disabled when selectedCount < 3', () => {
    const w = mount(AlignmentToolbar, { props: { ...baseProps, selectedCount: 2 } })
    const btns = w.findAll('.alignment-toolbar__btn')
    // last 2 buttons are distribute
    expect(btns[6].attributes('aria-disabled')).toBe('true')
    expect(btns[7].attributes('aria-disabled')).toBe('true')
    // first 6 are not disabled
    expect(btns[0].attributes('aria-disabled')).toBeUndefined()
  })

  it('emits align on button click', async () => {
    const w = mount(AlignmentToolbar, { props: baseProps })
    await w.findAll('.alignment-toolbar__btn')[0].trigger('click')
    expect(w.emitted('align')![0]).toEqual(['left'])
  })

  it('emits distribute on distribute button click', async () => {
    const w = mount(AlignmentToolbar, { props: baseProps })
    await w.findAll('.alignment-toolbar__btn')[6].trigger('click')
    expect(w.emitted('distribute')![0]).toEqual(['distribute-h'])
  })
})
