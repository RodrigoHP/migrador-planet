import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h, nextTick } from 'vue'
import ErrorBoundary from './ErrorBoundary.vue'

describe('ErrorBoundary', () => {
  it('renders slot content when no error', () => {
    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: '<div class="child">Hello</div>',
      },
    })
    expect(wrapper.find('.child').exists()).toBe(true)
    expect(wrapper.find('.error-boundary').exists()).toBe(false)
  })

  it('renders fallback UI when child component throws', async () => {
    const BrokenChild = defineComponent({
      setup() {
        throw new Error('Test explosion')
      },
      render: () => h('div'),
    })

    // Suppress Vue's error logging in test output
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: () => h(BrokenChild),
      },
    })

    await nextTick()
    expect(wrapper.find('.error-boundary').exists()).toBe(true)
    expect(wrapper.find('.error-boundary__title').text()).toContain('Algo deu errado')
    expect(wrapper.find('.error-boundary__btn').exists()).toBe(true)

    consoleSpy.mockRestore()
  })

  it('shows stack trace in dev mode', async () => {
    const BrokenChild = defineComponent({
      setup() {
        throw new Error('Dev error details')
      },
      render: () => h('div'),
    })

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: () => h(BrokenChild),
      },
    })

    await nextTick()
    // import.meta.env.DEV is true in vitest
    const stackEl = wrapper.find('.error-boundary__stack')
    expect(stackEl.exists()).toBe(true)
    expect(stackEl.text()).toContain('Dev error details')

    consoleSpy.mockRestore()
  })

  it('exposes error and recover via defineExpose', async () => {
    const BrokenChild = defineComponent({
      setup() {
        throw new Error('Exposed error')
      },
      render: () => h('div'),
    })

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: () => h(BrokenChild),
      },
    })

    await nextTick()
    expect(wrapper.vm.error).toBeInstanceOf(Error)
    expect(wrapper.vm.error?.message).toBe('Exposed error')
    expect(typeof wrapper.vm.recover).toBe('function')

    consoleSpy.mockRestore()
  })
})
