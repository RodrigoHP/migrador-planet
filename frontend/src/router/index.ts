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
    path: '/campos',
    name: 'campos',
    component: () => import('@/pages/CamposPage.vue'),
  },
  {
    path: '/layout',
    name: 'layout',
    component: () => import('@/pages/LayoutPage.vue'),
  },
  {
    path: '/geracao',
    name: 'geracao',
    component: () => import('@/pages/GeracaoPage.vue'),
  },
  {
    path: '/exportar',
    name: 'exportar',
    component: () => import('@/pages/ExportarPage.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation guards
router.beforeEach(async (to) => {
  // Lazy import stores inside guard to avoid circular deps
  const { useSessionStore } = await import('@/stores/session')
  const { useMappingStore } = await import('@/stores/mapping')
  const { useLayoutStore } = await import('@/stores/layout')
  const { useGenerationStore } = await import('@/stores/generation')

  const session = useSessionStore()
  const mapping = useMappingStore()
  const layout = useLayoutStore()
  const generation = useGenerationStore()

  if (to.name === 'campos' && session.extraction === null) {
    return { name: 'upload' }
  }
  if (to.name === 'layout' && !mapping.confirmed) {
    return { name: 'campos' }
  }
  if (to.name === 'geracao' && !layout.confirmed) {
    return { name: 'layout' }
  }
  if (to.name === 'exportar' && generation.html === null) {
    return { name: 'geracao' }
  }
})

export default router
