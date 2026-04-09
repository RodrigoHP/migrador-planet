import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ImageReplacePreview from './ImageReplacePreview.vue'

// Mock URL.createObjectURL / revokeObjectURL
const createObjectURLMock = vi.fn(() => 'blob:mock-preview-url')
const revokeObjectURLMock = vi.fn()

beforeEach(() => {
  vi.stubGlobal('URL', {
    createObjectURL: createObjectURLMock,
    revokeObjectURL: revokeObjectURLMock,
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

function makeFile(name = 'new.png', type = 'image/png'): File {
  return new File(['content'], name, { type })
}

describe('ImageReplacePreview', () => {
  it('renders both "Atual" and "Nova" labels', () => {
    const wrapper = mount(ImageReplacePreview, {
      props: {
        currentImageUrl: 'http://example.com/old.png',
        newImageFile: makeFile(),
      },
    })
    expect(wrapper.text()).toContain('Atual')
    expect(wrapper.text()).toContain('Nova')
  })

  it('displays current image when currentImageUrl is provided', () => {
    const wrapper = mount(ImageReplacePreview, {
      props: {
        currentImageUrl: 'http://example.com/old.png',
        newImageFile: makeFile(),
      },
    })
    const imgs = wrapper.findAll('img')
    expect(imgs.some((img) => img.attributes('src') === 'http://example.com/old.png')).toBe(true)
  })

  it('creates object URL for new file preview', () => {
    mount(ImageReplacePreview, {
      props: {
        currentImageUrl: 'http://example.com/old.png',
        newImageFile: makeFile(),
      },
    })
    expect(createObjectURLMock).toHaveBeenCalled()
  })

  it('displays current dimensions when provided', () => {
    const wrapper = mount(ImageReplacePreview, {
      props: {
        currentImageUrl: 'http://example.com/old.png',
        newImageFile: makeFile(),
        currentDimensions: { width: 800, height: 600 },
      },
    })
    expect(wrapper.text()).toContain('800 × 600 px')
  })

  it('displays new dimensions when provided', () => {
    const wrapper = mount(ImageReplacePreview, {
      props: {
        currentImageUrl: 'http://example.com/old.png',
        newImageFile: makeFile(),
        newDimensions: { width: 400, height: 300 },
      },
    })
    expect(wrapper.text()).toContain('400 × 300 px')
  })

  it('emits "confirm" when confirm button is clicked', async () => {
    const wrapper = mount(ImageReplacePreview, {
      props: {
        currentImageUrl: 'http://example.com/old.png',
        newImageFile: makeFile(),
      },
    })
    const confirmBtn = wrapper.find('button:first-of-type')
    await confirmBtn.trigger('click')
    expect(wrapper.emitted('confirm')).toBeTruthy()
    expect(wrapper.emitted('confirm')).toHaveLength(1)
  })

  it('emits "cancel" when cancel button is clicked', async () => {
    const wrapper = mount(ImageReplacePreview, {
      props: {
        currentImageUrl: 'http://example.com/old.png',
        newImageFile: makeFile(),
      },
    })
    const cancelBtn = wrapper.find('button:last-of-type')
    await cancelBtn.trigger('click')
    expect(wrapper.emitted('cancel')).toBeTruthy()
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })

  it('shows dash when currentImageUrl is empty', () => {
    const wrapper = mount(ImageReplacePreview, {
      props: {
        currentImageUrl: '',
        newImageFile: makeFile(),
      },
    })
    // Should show placeholder div instead of img
    const currentImgs = wrapper
      .findAll('img')
      .filter((img) => img.attributes('alt') === 'Imagem atual')
    expect(currentImgs).toHaveLength(0)
  })
})
