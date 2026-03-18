<template>
  <component :is="MonacoTabsInner" />
</template>

<script setup lang="ts">
import { defineAsyncComponent } from 'vue'

const MonacoTabsInner = defineAsyncComponent(() => import('./MonacoTabsInner.vue'))
</script>
