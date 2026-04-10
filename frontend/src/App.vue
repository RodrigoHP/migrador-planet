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
import ErrorBoundary from '@/components/ErrorBoundary.vue'
import ToastContainer from '@/components/ToastContainer.vue'

const authStore = useAuthStore()

onMounted(async () => {
  await authStore.initialize()
})
</script>
