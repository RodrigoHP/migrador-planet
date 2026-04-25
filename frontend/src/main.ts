import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import './assets/main.css'
import App from './App.vue'
import { useToastStore } from './stores/toastStore'
import { useAuthStore } from './stores/authStore'

async function bootstrap() {
  const app = createApp(App)
  const pinia = createPinia()

  app.use(pinia)

  // Initialize auth before the router fires its first navigation guard.
  // getSession() reads from localStorage synchronously (no network call when
  // token is not expired), so this adds ~0ms in practice.
  const authStore = useAuthStore()
  await authStore.initialize()

  app.use(router)

  // Story 40.5 — Global error handler (UX-006 + SYS-012)
  app.config.errorHandler = (err, instance, info) => {
    console.error('[GlobalErrorHandler]', err, '\nComponent:', instance, '\nInfo:', info)

    try {
      const toastStore = useToastStore()
      const message = err instanceof Error ? err.message : String(err)
      toastStore.error(`Erro inesperado: ${message}`)
    } catch {
      // Toast store may not be ready during early bootstrap errors
    }
  }

  app.mount('#app')
}

bootstrap()
