<template>
  <div class="editor-layout">
    <header class="editor-layout__header">
      <span class="editor-layout__title">Editor de Template</span>
    </header>
    <main class="editor-layout__main">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
// EditorLayout — shell placeholder for Story 5.1
// Full implementation in Story 5.4
</script>

<style scoped>
.editor-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--color-neutral-50, #f9fafb);
}

.editor-layout__header {
  height: 3rem;
  display: flex;
  align-items: center;
  padding: 0 1.5rem;
  background: var(--color-neutral-900, #111827);
  color: #fff;
}

.editor-layout__title {
  font-size: 0.875rem;
  font-weight: 600;
}

.editor-layout__main {
  flex: 1;
  display: flex;
  overflow: hidden;
}
</style>
