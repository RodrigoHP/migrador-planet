import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getSession, onAuthStateChange } from '@/services/authService'
import type { User } from '@supabase/supabase-js'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)

  const isAuthenticated = computed(() => !!token.value)

  function setSession(u: User | null, t: string | null) {
    user.value = u
    token.value = t
  }

  function clearSession() {
    user.value = null
    token.value = null
  }

  async function initialize() {
    // Restore session from localStorage (Supabase persists automatically)
    const session = await getSession()
    if (session) {
      setSession(session.user, session.access_token)
    }

    // Listen for auth state changes (login, logout, token refresh)
    onAuthStateChange((event, session) => {
      if (session) {
        setSession(session.user, session.access_token)
      } else {
        clearSession()
      }
    })
  }

  return { user, token, isAuthenticated, setSession, clearSession, initialize }
})
