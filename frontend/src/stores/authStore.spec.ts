import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/services/authService', () => ({
  getSession: vi.fn(),
  onAuthStateChange: vi.fn(() => ({ unsubscribe: vi.fn() })),
}))

import { useAuthStore } from './authStore'
import { getSession, onAuthStateChange } from '@/services/authService'

describe('authStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('starts unauthenticated', () => {
    const store = useAuthStore()
    expect(store.isAuthenticated).toBe(false)
    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
  })

  it('setSession marks as authenticated', () => {
    const store = useAuthStore()
    const mockUser = { id: '1', email: 'a@b.com' } as any
    store.setSession(mockUser, 'test-token')
    expect(store.isAuthenticated).toBe(true)
    expect(store.token).toBe('test-token')
    expect(store.user).toStrictEqual(mockUser)
  })

  it('clearSession marks as unauthenticated', () => {
    const store = useAuthStore()
    store.setSession({ id: '1' } as any, 'tok')
    store.clearSession()
    expect(store.isAuthenticated).toBe(false)
    expect(store.token).toBeNull()
  })

  describe('initialize', () => {
    it('restores existing session from Supabase', async () => {
      const mockSession = { access_token: 'restored-tok', user: { id: '1', email: 'a@b.com' } }
      vi.mocked(getSession).mockResolvedValue(mockSession as any)
      vi.mocked(onAuthStateChange).mockReturnValue({ unsubscribe: vi.fn() } as any)

      const store = useAuthStore()
      await store.initialize()

      expect(store.token).toBe('restored-tok')
      expect(store.isAuthenticated).toBe(true)
    })

    it('stays unauthenticated when no session exists', async () => {
      vi.mocked(getSession).mockResolvedValue(null)
      vi.mocked(onAuthStateChange).mockReturnValue({ unsubscribe: vi.fn() } as any)

      const store = useAuthStore()
      await store.initialize()

      expect(store.isAuthenticated).toBe(false)
    })

    it('registers onAuthStateChange listener', async () => {
      vi.mocked(getSession).mockResolvedValue(null)
      vi.mocked(onAuthStateChange).mockReturnValue({ unsubscribe: vi.fn() } as any)

      const store = useAuthStore()
      await store.initialize()

      expect(onAuthStateChange).toHaveBeenCalled()
    })
  })
})
