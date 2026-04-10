import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BoxModelVisualization from './BoxModelVisualization.vue'
import BoxModelValue from './BoxModelValue.vue'

describe('BoxModelVisualization', () => {
  const defaultProps = {
    margin: { top: 10, right: 20, bottom: 10, left: 20 },
    border: { top: 1, right: 1, bottom: 1, left: 1 },
    padding: { top: 5, right: 10, bottom: 5, left: 10 },
    contentWidth: 200,
    contentHeight: 100,
  }

  it('renders all 4 layers', () => {
    const wrapper = mount(BoxModelVisualization, { props: defaultProps })
    expect(wrapper.find('.box-model__layer--margin').exists()).toBe(true)
    expect(wrapper.find('.box-model__layer--border').exists()).toBe(true)
    expect(wrapper.find('.box-model__layer--padding').exists()).toBe(true)
    expect(wrapper.find('.box-model__layer--content').exists()).toBe(true)
  })

  it('renders content dimensions label', () => {
    const wrapper = mount(BoxModelVisualization, { props: defaultProps })
    expect(wrapper.find('.box-model__content-label').text()).toBe('200 × 100')
  })

  it('renders 12 BoxModelValue components (4 sides × 3 layers)', () => {
    const wrapper = mount(BoxModelVisualization, { props: defaultProps })
    const values = wrapper.findAllComponents(BoxModelValue)
    expect(values).toHaveLength(12)
  })

  it('emits update:margin when a margin value changes', async () => {
    const wrapper = mount(BoxModelVisualization, { props: defaultProps })
    const marginValues = wrapper
      .findAllComponents(BoxModelValue)
      .filter((c) => (c.props('label') as string).startsWith('margin'))
    await marginValues[0]!.vm.$emit('update', 15)
    expect(wrapper.emitted('update:margin')).toBeTruthy()
    expect(wrapper.emitted('update:margin')![0]![0]).toEqual(expect.objectContaining({ top: 15 }))
  })

  it('emits update:padding when a padding value changes', async () => {
    const wrapper = mount(BoxModelVisualization, { props: defaultProps })
    const paddingValues = wrapper
      .findAllComponents(BoxModelValue)
      .filter((c) => (c.props('label') as string).startsWith('padding'))
    await paddingValues[0]!.vm.$emit('update', 8)
    expect(wrapper.emitted('update:padding')).toBeTruthy()
  })

  it('emits update:border when a border value changes', async () => {
    const wrapper = mount(BoxModelVisualization, { props: defaultProps })
    const borderValues = wrapper
      .findAllComponents(BoxModelValue)
      .filter((c) => (c.props('label') as string).startsWith('border'))
    await borderValues[0]!.vm.$emit('update', 2)
    expect(wrapper.emitted('update:border')).toBeTruthy()
  })

  it('renders with default zero props', () => {
    const wrapper = mount(BoxModelVisualization)
    expect(wrapper.find('.box-model__content-label').text()).toBe('0 × 0')
  })

  it('layer labels are visible', () => {
    const wrapper = mount(BoxModelVisualization, { props: defaultProps })
    const labels = wrapper.findAll('.box-model__label')
    expect(labels.length).toBe(3)
    expect(labels.map((l) => l.text())).toEqual(['margin', 'border', 'padding'])
  })
})

describe('BoxModelValue', () => {
  it('renders value as spinbutton', () => {
    const wrapper = mount(BoxModelValue, { props: { label: 'margin top', value: 10 } })
    const span = wrapper.find('[role="spinbutton"]')
    expect(span.exists()).toBe(true)
    expect(span.text()).toBe('10')
    expect(span.attributes('aria-label')).toBe('margin top')
    expect(span.attributes('aria-valuenow')).toBe('10')
    expect(span.attributes('aria-valuemin')).toBe('0')
  })

  it('enters edit mode on click', async () => {
    const wrapper = mount(BoxModelValue, { props: { label: 'margin top', value: 10 } })
    await wrapper.find('[role="spinbutton"]').trigger('click')
    expect(wrapper.find('input').exists()).toBe(true)
  })

  it('emits update on blur with valid number', async () => {
    const wrapper = mount(BoxModelValue, { props: { label: 'margin top', value: 10 } })
    await wrapper.find('[role="spinbutton"]').trigger('click')
    const input = wrapper.find('input')
    await input.setValue('25')
    await input.trigger('blur')
    expect(wrapper.emitted('update')![0]).toEqual([25])
  })

  it('cancels edit on Escape', async () => {
    const wrapper = mount(BoxModelValue, { props: { label: 'margin top', value: 10 } })
    await wrapper.find('[role="spinbutton"]').trigger('click')
    await wrapper.find('input').trigger('keydown.escape')
    expect(wrapper.find('input').exists()).toBe(false)
    expect(wrapper.find('[role="spinbutton"]').text()).toBe('10')
  })

  it('emits update on ArrowUp key', async () => {
    const wrapper = mount(BoxModelValue, { props: { label: 'margin top', value: 10 } })
    await wrapper.find('[role="spinbutton"]').trigger('keydown', { key: 'ArrowUp' })
    expect(wrapper.emitted('update')![0]).toEqual([11])
  })

  it('emits update on Shift+ArrowUp (step 10)', async () => {
    const wrapper = mount(BoxModelValue, { props: { label: 'margin top', value: 10 } })
    await wrapper.find('[role="spinbutton"]').trigger('keydown', { key: 'ArrowUp', shiftKey: true })
    expect(wrapper.emitted('update')![0]).toEqual([20])
  })

  it('does not go below 0 on ArrowDown', async () => {
    const wrapper = mount(BoxModelValue, { props: { label: 'margin top', value: 0 } })
    await wrapper.find('[role="spinbutton"]').trigger('keydown', { key: 'ArrowDown' })
    expect(wrapper.emitted('update')![0]).toEqual([0])
  })
})
