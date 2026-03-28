import { useAuthStore } from '@/stores/authStore'

/**
 * Wrapper around fetch() that injects Authorization: Bearer {token} header
 * when the user is authenticated. Falls back to unauthenticated request
 * for local dev when AUTH_DISABLED=true on backend.
 */
export async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const authStore = useAuthStore()
  const headers = new Headers(options.headers)

  if (authStore.token) {
    headers.set('Authorization', `Bearer ${authStore.token}`)
  }

  return fetch(url, { ...options, headers })
}
