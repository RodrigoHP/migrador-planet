import { defineStore } from 'pinia'
import { getSession, onAuthStateChange } from '@/services/authService'
import type { User } from '@supabase/supabase-js'

interface AuthState {
  user: User | null
  token: string | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: null,
    token: null,
  }),

  getters: {
    isAuthenticated: (state): boolean => !!state.token,
  },

  actions: {
    setSession(user: User | null, token: string | null) {
      this.user = user
      this.token = token
    },

    clearSession() {
      this.user = null
      this.token = null
    },

    async initialize() {
      // Restore session from localStorage (Supabase persists automatically)
      const session = await getSession()
      if (session) {
        this.setSession(session.user, session.access_token)
      }

      // Listen for auth state changes (login, logout, token refresh)
      onAuthStateChange((event, session) => {
        if (session) {
          this.setSession(session.user, session.access_token)
        } else {
          this.clearSession()
        }
      })
    },
  },
})
