<template>
  <ErrorBoundary>
    <RouterView />
  </ErrorBoundary>
  <ToastContainer />
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import ErrorBoundary from '@/organisms/ErrorBoundary.vue'
import ToastContainer from '@/organisms/ToastContainer.vue'
</script>
