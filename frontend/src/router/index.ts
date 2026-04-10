import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { globalDirtyFlag } from '@/composables/useUnsavedChanges'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/pages/LoginPage.vue'),
    meta: { public: true },
  },
  {
    path: '/auth/callback',
    name: 'auth-callback',
    component: () => import('@/pages/AuthCallback.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    name: 'home',
    component: () => import('@/pages/HomePage.vue'),
  },
  {
    path: '/upload',
    name: 'upload',
    component: () => import('@/pages/UploadPage.vue'),
  },
  {
    path: '/analyzing',
    name: 'analyzing',
    component: () => import('@/pages/AnalyzingPage.vue'),
  },
  {
    path: '/editor',
    name: 'editor',
    component: () => import('@/pages/TemplateEditor.vue'),
  },
  { path: '/:pathMatch(.*)*', name: 'not-found', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation guards
router.beforeEach(async (to, from) => {
  // Story 40.5 — UX-007: Warn on unsaved changes before navigation
  if (globalDirtyFlag.value && from.name === 'editor' && to.name !== 'editor') {
    const confirmed = window.confirm('Voce tem alteracoes nao salvas. Deseja sair sem salvar?')
    if (!confirmed) return false
  }
  // Auth guard — redirect to /login if not authenticated
  if (!to.meta.public) {
    const { useAuthStore } = await import('@/stores/authStore')
    const auth = useAuthStore()
    if (!auth.isAuthenticated) {
      return { name: 'login' }
    }
  }

  // Session guards — protect analyzing/editor by app state
  const { useSessionStore } = await import('@/stores/session')
  const session = useSessionStore()

  if (to.name === 'analyzing' && !session.jobId) {
    return { name: 'upload' }
  }

  if (to.name === 'editor' && session.analysisCompleted !== true) {
    return { name: 'home' }
  }
})

export default router
