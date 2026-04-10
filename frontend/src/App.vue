<template>
  <ErrorBoundary>
    <RouterView />
  </ErrorBoundary>
  <ToastContainer />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import ErrorBoundary from '@/organisms/ErrorBoundary.vue'
import ToastContainer from '@/organisms/ToastContainer.vue'

const authStore = useAuthStore()

onMounted(async () => {
  await authStore.initialize()
})
</script>
