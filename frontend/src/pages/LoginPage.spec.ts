import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LoginPage from './LoginPage.vue'
import * as authService from '@/services/authService'

// ─── Mock authService ─────────────────────────────────────────────────────────
// vi.mock is hoisted, so use vi.fn() inline; access the mock via the imported module
vi.mock('@/services/authService', () => ({
  signInWithGoogle: vi.fn(),
}))

// Typed reference for convenience
const mockSignInWithGoogle = authService.signInWithGoogle as ReturnType<typeof vi.fn>

// ─── Helper ───────────────────────────────────────────────────────────────────

function mountLogin() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const wrapper = mount(LoginPage, {
    global: { plugins: [pinia] },
  })
  return { wrapper }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ── Rendering ──────────────────────────────────────────────────────────────

  it('renders the page title and subtitle', () => {
    const { wrapper } = mountLogin()
    expect(wrapper.text()).toContain('migrador-planet')
    expect(wrapper.text()).toContain('Engenharia reversa de PDFs para HTML')
  })

  it('renders the OAuth (Google) login button', () => {
    const { wrapper } = mountLogin()
    const btn = wrapper.find('button.login__btn')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toContain('Entrar com Google')
  })

  it('button is enabled by default (not in loading state)', () => {
    const { wrapper } = mountLogin()
    const btn = wrapper.find('button.login__btn')
    expect(btn.attributes('disabled')).toBeUndefined()
  })

  // ── OAuth redirect / signInWithGoogle ─────────────────────────────────────

  it('calls signInWithGoogle when OAuth button is clicked', async () => {
    mockSignInWithGoogle.mockResolvedValue(undefined)
    const { wrapper } = mountLogin()

    await wrapper.find('button.login__btn').trigger('click')
    await flushPromises()

    expect(mockSignInWithGoogle).toHaveBeenCalledOnce()
  })

  it('shows loading text while authentication is in progress', async () => {
    // Never-resolving promise to freeze the loading state
    mockSignInWithGoogle.mockReturnValue(new Promise(() => {}))
    const { wrapper } = mountLogin()

    await wrapper.find('button.login__btn').trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('button.login__btn').text()).toContain('Redirecionando...')
    expect(wrapper.find('button.login__btn').attributes('disabled')).toBeDefined()
  })

  // ── Error handling ─────────────────────────────────────────────────────────

  it('displays error message when signInWithGoogle throws', async () => {
    mockSignInWithGoogle.mockRejectedValue(new Error('Auth failed'))
    const { wrapper } = mountLogin()

    await wrapper.find('button.login__btn').trigger('click')
    await flushPromises()

    expect(wrapper.find('.login__error').exists()).toBe(true)
    expect(wrapper.find('.login__error').text()).toBe('Auth failed')
  })

  it('displays generic error for non-Error throws', async () => {
    mockSignInWithGoogle.mockRejectedValue('network error')
    const { wrapper } = mountLogin()

    await wrapper.find('button.login__btn').trigger('click')
    await flushPromises()

    expect(wrapper.find('.login__error').text()).toBe('Erro ao autenticar.')
  })

  it('re-enables the button after an error', async () => {
    mockSignInWithGoogle.mockRejectedValue(new Error('fail'))
    const { wrapper } = mountLogin()

    await wrapper.find('button.login__btn').trigger('click')
    await flushPromises()

    expect(wrapper.find('button.login__btn').attributes('disabled')).toBeUndefined()
  })

  it('does not show error element when there is no error', () => {
    const { wrapper } = mountLogin()
    expect(wrapper.find('.login__error').exists()).toBe(false)
  })

  // ── Google SVG icon ────────────────────────────────────────────────────────

  it('renders the Google SVG icon inside the button', () => {
    const { wrapper } = mountLogin()
    const svg = wrapper.find('button.login__btn svg.login__google-icon')
    expect(svg.exists()).toBe(true)
  })
})
