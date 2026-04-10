<template>
  <div class="callback">
    <p v-if="error" class="callback__error">{{ error }}</p>
    <p v-else class="callback__msg">Autenticando...</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { supabase } from '@/lib/supabase'
import { useAuthStore } from '@/stores/authStore'

const router = useRouter()
const authStore = useAuthStore()
const error = ref<string | null>(null)

onMounted(async () => {
  // Supabase automatically exchanges the code in the URL for a session
  const { data, error: err } = await supabase.auth.getSession()
  if (err || !data.session) {
    error.value = err?.message ?? 'Falha na autenticação. Tente novamente.'
    return
  }
  authStore.setSession(data.session.user, data.session.access_token)
  router.replace('/')
})
</script>

<style scoped>
.callback {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.callback__msg {
  color: var(--color-neutral-500, #525252);
}

.callback__error {
  color: var(--color-red-600, #dc2626);
}
</style>
