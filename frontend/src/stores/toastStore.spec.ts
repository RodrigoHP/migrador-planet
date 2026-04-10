import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useToastStore } from './toastStore'

describe('toastStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  it('adds a toast with default type and duration', () => {
    const store = useToastStore()
    const id = store.addToast('Hello')
    expect(store.toasts).toHaveLength(1)
    expect(store.toasts[0].message).toBe('Hello')
    expect(store.toasts[0].type).toBe('info')
    expect(store.toasts[0].duration).toBe(5000)
  })

  it('auto-removes toast after duration', () => {
    const store = useToastStore()
    store.addToast('Temp', 'info', 3000)
    expect(store.toasts).toHaveLength(1)

    vi.advanceTimersByTime(3000)
    expect(store.toasts).toHaveLength(0)
  })

  it('does not auto-remove toast with duration 0', () => {
    const store = useToastStore()
    store.addToast('Persistent', 'warning', 0)
    vi.advanceTimersByTime(10000)
    expect(store.toasts).toHaveLength(1)
  })

  it('removes toast by id', () => {
    const store = useToastStore()
    const id = store.addToast('Test')
    expect(store.toasts).toHaveLength(1)
    store.removeToast(id)
    expect(store.toasts).toHaveLength(0)
  })

  it('clears all toasts', () => {
    const store = useToastStore()
    store.addToast('A')
    store.addToast('B')
    store.addToast('C')
    expect(store.toasts).toHaveLength(3)
    store.clearAll()
    expect(store.toasts).toHaveLength(0)
  })

  it('convenience methods set correct type', () => {
    const store = useToastStore()
    store.info('Info msg')
    store.success('Success msg')
    store.warning('Warning msg')
    store.error('Error msg')

    expect(store.toasts[0].type).toBe('info')
    expect(store.toasts[1].type).toBe('success')
    expect(store.toasts[2].type).toBe('warning')
    expect(store.toasts[3].type).toBe('error')
  })

  it('error convenience uses 8000ms duration by default', () => {
    const store = useToastStore()
    store.error('Oops')
    expect(store.toasts[0].duration).toBe(8000)
  })
})
