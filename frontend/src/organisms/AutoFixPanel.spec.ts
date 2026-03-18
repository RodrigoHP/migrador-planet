import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import AutoFixPanel from './AutoFixPanel.vue'
import { useAutoFixStore } from '@/stores/autoFixStore'
import type { FixSuggestion } from '@/stores/autoFixStore'

// Mock idb to avoid IndexedDB errors in test environment
vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      get: vi.fn(() => Promise.resolve(undefined)),
      put: vi.fn(() => Promise.resolve()),
    }),
  ),
}))

function makeSuggestion(overrides: Partial<FixSuggestion> = {}): FixSuggestion {
  return {
    id: 'fix-001',
    type: 'spacing',
    description: 'Espaçamento inconsistente',
    element_id: 'node-1',
    current_value: '8px',
    suggested_value: '16px',
    confidence: 85,
    ...overrides,
  }
}

describe('AutoFixPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('does not render when isOpen is false', () => {
    const wrapper = mount(AutoFixPanel, { attachTo: document.body })
    const store = useAutoFixStore()
    store.isOpen = false
    expect(document.querySelector('[data-testid="auto-fix-panel"]')).toBeNull()
    wrapper.unmount()
  })

  it('renders when isOpen is true', async () => {
    const store = useAutoFixStore()
    store.isOpen = true
    const wrapper = mount(AutoFixPanel, { attachTo: document.body })
    await wrapper.vm.$nextTick()
    expect(document.querySelector('[data-testid="auto-fix-panel"]')).not.toBeNull()
    wrapper.unmount()
  })

  it('shows loading state when isRunning is true', async () => {
    const store = useAutoFixStore()
    store.isOpen = true
    store.isRunning = true
    const wrapper = mount(AutoFixPanel, { attachTo: document.body })
    await wrapper.vm.$nextTick()
    expect(document.querySelector('[data-testid="auto-fix-loading"]')).not.toBeNull()
    wrapper.unmount()
  })

  it('shows error state when error is set', async () => {
    const store = useAutoFixStore()
    store.isOpen = true
    store.isRunning = false
    store.error = 'Algo deu errado'
    const wrapper = mount(AutoFixPanel, { attachTo: document.body })
    await wrapper.vm.$nextTick()
    expect(document.querySelector('[data-testid="auto-fix-error"]')).not.toBeNull()
    wrapper.unmount()
  })

  it('shows empty state when suggestions are empty and not running', async () => {
    const store = useAutoFixStore()
    store.isOpen = true
    store.isRunning = false
    store.suggestions = []
    const wrapper = mount(AutoFixPanel, { attachTo: document.body })
    await wrapper.vm.$nextTick()
    expect(document.querySelector('[data-testid="auto-fix-empty"]')).not.toBeNull()
    wrapper.unmount()
  })

  it('shows action buttons when suggestion is active', async () => {
    const store = useAutoFixStore()
    store.isOpen = true
    store.isRunning = false
    store.suggestions = [makeSuggestion()]
    store.currentIndex = 0
    const wrapper = mount(AutoFixPanel, { attachTo: document.body })
    await wrapper.vm.$nextTick()
    expect(document.querySelector('[data-testid="auto-fix-actions"]')).not.toBeNull()
    wrapper.unmount()
  })

  it('shows accept, reject, skip buttons', async () => {
    const store = useAutoFixStore()
    store.isOpen = true
    store.isRunning = false
    store.suggestions = [makeSuggestion()]
    store.currentIndex = 0
    const wrapper = mount(AutoFixPanel, { attachTo: document.body })
    await wrapper.vm.$nextTick()
    expect(document.querySelector('[data-testid="btn-accept"]')).not.toBeNull()
    expect(document.querySelector('[data-testid="btn-reject"]')).not.toBeNull()
    expect(document.querySelector('[data-testid="btn-skip"]')).not.toBeNull()
    wrapper.unmount()
  })

  it('shows summary when finished', async () => {
    const store = useAutoFixStore()
    store.isOpen = true
    store.isRunning = false
    store.suggestions = [makeSuggestion()]
    store.currentIndex = 1 // past end = finished
    const wrapper = mount(AutoFixPanel, { attachTo: document.body })
    await wrapper.vm.$nextTick()
    expect(document.querySelector('[data-testid="auto-fix-summary"]')).not.toBeNull()
    wrapper.unmount()
  })

  it('shows progress when suggestion is active', async () => {
    const store = useAutoFixStore()
    store.isOpen = true
    store.isRunning = false
    store.suggestions = [makeSuggestion(), makeSuggestion({ id: 'fix-002' })]
    store.currentIndex = 0
    const wrapper = mount(AutoFixPanel, { attachTo: document.body })
    await wrapper.vm.$nextTick()
    expect(document.querySelector('[data-testid="auto-fix-progress"]')).not.toBeNull()
    wrapper.unmount()
  })

  it('calls acceptCurrent when accept button is clicked', async () => {
    const store = useAutoFixStore()
    store.isOpen = true
    store.isRunning = false
    store.suggestions = [makeSuggestion()]
    store.currentIndex = 0
    const spy = vi.spyOn(store, 'acceptCurrent')
    const wrapper = mount(AutoFixPanel, { attachTo: document.body })
    await wrapper.vm.$nextTick()
    const btn = document.querySelector('[data-testid="btn-accept"]') as HTMLButtonElement
    btn?.click()
    expect(spy).toHaveBeenCalledOnce()
    wrapper.unmount()
  })

  it('calls rejectCurrent when reject button is clicked', async () => {
    const store = useAutoFixStore()
    store.isOpen = true
    store.isRunning = false
    store.suggestions = [makeSuggestion()]
    store.currentIndex = 0
    const spy = vi.spyOn(store, 'rejectCurrent')
    const wrapper = mount(AutoFixPanel, { attachTo: document.body })
    await wrapper.vm.$nextTick()
    const btn = document.querySelector('[data-testid="btn-reject"]') as HTMLButtonElement
    btn?.click()
    expect(spy).toHaveBeenCalledOnce()
    wrapper.unmount()
  })

  it('calls skipCurrent when skip button is clicked', async () => {
    const store = useAutoFixStore()
    store.isOpen = true
    store.isRunning = false
    store.suggestions = [makeSuggestion()]
    store.currentIndex = 0
    const spy = vi.spyOn(store, 'skipCurrent')
    const wrapper = mount(AutoFixPanel, { attachTo: document.body })
    await wrapper.vm.$nextTick()
    const btn = document.querySelector('[data-testid="btn-skip"]') as HTMLButtonElement
    btn?.click()
    expect(spy).toHaveBeenCalledOnce()
    wrapper.unmount()
  })
})
