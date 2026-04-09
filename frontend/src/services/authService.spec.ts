import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock @/lib/supabase before importing authService
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      signInWithOAuth: vi.fn(),
      signOut: vi.fn(),
      getSession: vi.fn(),
      onAuthStateChange: vi.fn(),
    },
  },
}))

import { signInWithGoogle, signOut, getSession, onAuthStateChange } from './authService'
import { supabase } from '@/lib/supabase'

const mockAuth = supabase.auth as ReturnType<typeof vi.fn> & typeof supabase.auth

describe('authService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('signInWithGoogle', () => {
    it('calls signInWithOAuth with google provider', async () => {
      vi.mocked(mockAuth.signInWithOAuth).mockResolvedValue({ data: {}, error: null } as any)
      await signInWithGoogle()
      expect(mockAuth.signInWithOAuth).toHaveBeenCalledWith({
        provider: 'google',
        options: expect.objectContaining({ redirectTo: expect.stringContaining('/auth/callback') }),
      })
    })

    it('throws when Supabase returns an error', async () => {
      vi.mocked(mockAuth.signInWithOAuth).mockResolvedValue({
        data: {},
        error: { message: 'OAuth failed' },
      } as any)
      await expect(signInWithGoogle()).rejects.toThrow('OAuth failed')
    })
  })

  describe('signOut', () => {
    it('calls supabase.auth.signOut', async () => {
      vi.mocked(mockAuth.signOut).mockResolvedValue({ error: null })
      await signOut()
      expect(mockAuth.signOut).toHaveBeenCalled()
    })

    it('throws when Supabase returns an error', async () => {
      vi.mocked(mockAuth.signOut).mockResolvedValue({
        error: { message: 'Sign out failed' },
      } as any)
      await expect(signOut()).rejects.toThrow('Sign out failed')
    })
  })

  describe('getSession', () => {
    it('returns session when authenticated', async () => {
      const mockSession = { access_token: 'tok', user: { id: '1', email: 'a@b.com' } }
      vi.mocked(mockAuth.getSession).mockResolvedValue({
        data: { session: mockSession },
        error: null,
      } as any)
      const result = await getSession()
      expect(result).toEqual(mockSession)
    })

    it('returns null when no session', async () => {
      vi.mocked(mockAuth.getSession).mockResolvedValue({
        data: { session: null },
        error: null,
      } as any)
      const result = await getSession()
      expect(result).toBeNull()
    })
  })

  describe('onAuthStateChange', () => {
    it('registers callback and returns subscription', () => {
      const mockSubscription = { unsubscribe: vi.fn() }
      vi.mocked(mockAuth.onAuthStateChange).mockReturnValue({
        data: { subscription: mockSubscription },
      } as any)
      const cb = vi.fn()
      const sub = onAuthStateChange(cb)
      expect(mockAuth.onAuthStateChange).toHaveBeenCalledWith(cb)
      expect(sub).toBe(mockSubscription)
    })
  })
})
