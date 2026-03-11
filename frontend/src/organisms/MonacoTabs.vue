<template>
  <component
    :is="MonacoTabsInner"
    :html="html"
    :css="css"
    :js="js"
    @update:html="$emit('update:html', $event)"
    @update:css="$emit('update:css', $event)"
    @update:js="$emit('update:js', $event)"
  />
</template>

<script setup lang="ts">
import { defineAsyncComponent } from 'vue'

defineProps<{
  html: string
  css: string
  js: string
}>()

defineEmits<{
  'update:html': [value: string]
  'update:css': [value: string]
  'update:js': [value: string]
}>()

const MonacoTabsInner = defineAsyncComponent(() => import('./MonacoTabsInner.vue'))
</script>
