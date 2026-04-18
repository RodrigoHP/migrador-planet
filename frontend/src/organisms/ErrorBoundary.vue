<template>
  <slot v-if="!hasError" />
  <div v-else class="error-boundary">
    <p>Ocorreu um erro inesperado.</p>
    <button @click="reset">Tentar novamente</button>
  </div>
</template>

<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'

const hasError = ref(false)

onErrorCaptured(() => {
  hasError.value = true
  return false
})

function reset() {
  hasError.value = false
}
</script>
