import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import './assets/main.css'
import App from './App.vue'
import { useToastStore } from './stores/toastStore'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Story 40.5 — Global error handler (UX-006 + SYS-012)
// Catches errors that escape component boundaries
app.config.errorHandler = (err, instance, info) => {
  console.error('[GlobalErrorHandler]', err, '\nComponent:', instance, '\nInfo:', info)

  // Dispatch to toast store for user-visible feedback
  try {
    const toastStore = useToastStore()
    const message = err instanceof Error ? err.message : String(err)
    toastStore.error(`Erro inesperado: ${message}`)
  } catch {
    // Toast store may not be ready during early bootstrap errors
  }
}

app.mount('#app')
