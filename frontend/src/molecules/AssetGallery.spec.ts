import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import AssetGallery from './AssetGallery.vue'
import type { AssetInfo } from '@/services/assetService'

// Mock assetService
vi.mock('@/services/assetService', () => ({
  listAssets: vi.fn(),
}))

import { listAssets } from '@/services/assetService'
const listAssetsMock = vi.mocked(listAssets)

const sampleAssets: AssetInfo[] = [
  {
    filename: 'logo.png',
    path: 'assets/logo.png',
    size: 24576,
    thumbnailUrl: '/api/templates/t1/assets/logo.png/thumbnail',
  },
  {
    filename: 'banner.jpg',
    path: 'assets/banner.jpg',
    size: 1048576,
    thumbnailUrl: '/api/templates/t1/assets/banner.jpg/thumbnail',
  },
]

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('AssetGallery', () => {
  it('renders thumbnails and file names after loading', async () => {
    listAssetsMock.mockResolvedValueOnce(sampleAssets)

    const wrapper = mount(AssetGallery, {
      props: { templateId: 't1' },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('logo.png')
    expect(wrapper.text()).toContain('banner.jpg')
  })

  it('shows file sizes formatted correctly', async () => {
    listAssetsMock.mockResolvedValueOnce(sampleAssets)

    const wrapper = mount(AssetGallery, {
      props: { templateId: 't1' },
    })
    await flushPromises()

    // 24576 bytes = 24 KB
    expect(wrapper.text()).toContain('24 KB')
    // 1048576 bytes = 1.0 MB
    expect(wrapper.text()).toContain('1.0 MB')
  })

  it('shows empty state when no assets', async () => {
    listAssetsMock.mockResolvedValueOnce([])

    const wrapper = mount(AssetGallery, {
      props: { templateId: 't1' },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Nenhum asset no projeto')
  })

  it('shows error message on load failure', async () => {
    listAssetsMock.mockRejectedValueOnce(new Error('Erro de rede'))

    const wrapper = mount(AssetGallery, {
      props: { templateId: 't1' },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Erro de rede')
  })

  it('emits "select" with asset info when item is clicked', async () => {
    listAssetsMock.mockResolvedValueOnce(sampleAssets)

    const wrapper = mount(AssetGallery, {
      props: { templateId: 't1' },
    })
    await flushPromises()

    const buttons = wrapper.findAll('button')
    expect(buttons.length).toBeGreaterThan(0)
    await buttons[0]!.trigger('click')

    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')![0]).toEqual([sampleAssets[0]])
  })

  it('calls listAssets with the correct templateId', async () => {
    listAssetsMock.mockResolvedValueOnce([])

    mount(AssetGallery, {
      props: { templateId: 'my-template' },
    })
    await flushPromises()

    expect(listAssetsMock).toHaveBeenCalledWith('my-template')
  })

  it('exposes loadAssets method that reloads the list', async () => {
    listAssetsMock.mockResolvedValue([])

    const wrapper = mount(AssetGallery, {
      props: { templateId: 't1' },
    })
    await flushPromises()

    expect(listAssetsMock).toHaveBeenCalledTimes(1)

    // Call exposed method
    await (wrapper.vm as { loadAssets: () => Promise<void> }).loadAssets()
    await flushPromises()

    expect(listAssetsMock).toHaveBeenCalledTimes(2)
  })
})
