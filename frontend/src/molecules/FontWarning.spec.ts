import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import FontWarning from './FontWarning.vue'

describe('FontWarning', () => {
  // ── Visibility ──────────────────────────────────────────────────────────────

  it('is visible when status is not_found', () => {
    const wrapper = mount(FontWarning, {
      props: {
        detectedFont: 'CustomFont',
        fallbackFont: 'Arial',
        status: 'not_found',
      },
    })
    expect(wrapper.find('.font-warning').exists()).toBe(true)
  })

  it('is NOT visible when status is found', () => {
    const wrapper = mount(FontWarning, {
      props: {
        detectedFont: 'Arial',
        fallbackFont: 'Arial',
        status: 'found',
      },
    })
    expect(wrapper.find('.font-warning').exists()).toBe(false)
  })

  it('is NOT visible when status is fallback', () => {
    const wrapper = mount(FontWarning, {
      props: {
        detectedFont: 'Helvetica',
        fallbackFont: 'Arial',
        status: 'fallback',
      },
    })
    expect(wrapper.find('.font-warning').exists()).toBe(false)
  })

  // ── Content ─────────────────────────────────────────────────────────────────

  it('shows the detected font name', () => {
    const wrapper = mount(FontWarning, {
      props: {
        detectedFont: 'MySpecialFont',
        fallbackFont: 'sans-serif',
        status: 'not_found',
      },
    })
    expect(wrapper.text()).toContain('MySpecialFont')
  })

  it('shows the fallback font name', () => {
    const wrapper = mount(FontWarning, {
      props: {
        detectedFont: 'MySpecialFont',
        fallbackFont: 'Roboto',
        status: 'not_found',
      },
    })
    expect(wrapper.text()).toContain('Roboto')
  })

  it('shows the upload button', () => {
    const wrapper = mount(FontWarning, {
      props: {
        detectedFont: 'X',
        fallbackFont: 'Y',
        status: 'not_found',
      },
    })
    const btn = wrapper.find('.font-warning__btn')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toContain('Upload')
  })

  // ── Upload event ─────────────────────────────────────────────────────────────

  it('emits upload event with file when file is selected', async () => {
    const wrapper = mount(FontWarning, {
      props: {
        detectedFont: 'X',
        fallbackFont: 'Y',
        status: 'not_found',
      },
    })

    const fileInput = wrapper.find<HTMLInputElement>('.font-warning__file-input')
    expect(fileInput.exists()).toBe(true)

    const file = new File(['dummy'], 'test.ttf', { type: 'font/ttf' })

    // Simulate file input change by creating a mock FileList
    const mockFileList = {
      0: file,
      length: 1,
      item: (index: number) => (index === 0 ? file : null),
    } as unknown as FileList

    Object.defineProperty(fileInput.element, 'files', {
      value: mockFileList,
      configurable: true,
    })

    await fileInput.trigger('change')

    expect(wrapper.emitted('upload')).toBeTruthy()
    expect((wrapper.emitted('upload')![0] as unknown[])[0]).toBe(file)
  })

  it('file input accepts font formats', () => {
    const wrapper = mount(FontWarning, {
      props: {
        detectedFont: 'X',
        fallbackFont: 'Y',
        status: 'not_found',
      },
    })
    const fileInput = wrapper.find<HTMLInputElement>('.font-warning__file-input')
    const accept = fileInput.element.accept
    expect(accept).toContain('.ttf')
    expect(accept).toContain('.otf')
    expect(accept).toContain('.woff')
    expect(accept).toContain('.woff2')
  })
})
