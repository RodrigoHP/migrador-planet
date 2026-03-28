<template>
  <div class="login">
    <div class="login__card">
      <h1 class="login__title">migrador-planet</h1>
      <p class="login__subtitle">Engenharia reversa de PDFs para HTML</p>

      <button class="login__btn" :disabled="loading" @click="handleLogin">
        <svg class="login__google-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
        </svg>
        {{ loading ? 'Redirecionando...' : 'Entrar com Google' }}
      </button>

      <p v-if="error" class="login__error">{{ error }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { signInWithGoogle } from '@/services/authService'

const loading = ref(false)
const error = ref<string | null>(null)

async function handleLogin() {
  loading.value = true
  error.value = null
  try {
    await signInWithGoogle()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao autenticar.'
    loading.value = false
  }
}
</script>

<style scoped>
.login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-neutral-50, #f9fafb);
}

.login__card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2.5rem 2rem;
  background: white;
  border: 1px solid var(--color-neutral-200, #e5e7eb);
  border-radius: 0.75rem;
  width: 100%;
  max-width: 360px;
}

.login__title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-neutral-900, #111827);
}

.login__subtitle {
  font-size: 0.875rem;
  color: var(--color-neutral-500, #6b7280);
  text-align: center;
  margin-bottom: 0.5rem;
}

.login__btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.625rem 1rem;
  background: white;
  border: 1px solid var(--color-neutral-300, #d1d5db);
  border-radius: 0.5rem;
  font-size: 0.9375rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.login__btn:hover:not(:disabled) {
  background: var(--color-neutral-50, #f9fafb);
}

.login__btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login__google-icon {
  width: 1.25rem;
  height: 1.25rem;
  flex-shrink: 0;
}

.login__error {
  font-size: 0.8125rem;
  color: var(--color-red-600, #dc2626);
}
</style>
