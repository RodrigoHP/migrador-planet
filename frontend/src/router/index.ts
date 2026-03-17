import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
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
router.beforeEach(async (to) => {
  // Lazy import store inside guard to avoid circular deps
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
