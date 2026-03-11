<template>
  <section class="split">
    <aside class="split__left">
      <slot name="left" />
    </aside>
    <section class="split__center">
      <slot name="center" />
    </section>
    <aside class="split__right">
      <slot name="right" />
    </aside>
  </section>
</template>

<style scoped>
.split {
  display: grid;
  grid-template-columns: minmax(280px, 5fr) minmax(280px, 3fr) minmax(280px, 2fr);
  gap: 0.75rem;
  min-height: calc(100vh - 120px);
}

.split__left,
.split__center,
.split__right {
  min-width: 280px;
  background: #fff;
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.75rem;
  padding: 0.875rem;
  overflow: auto;
}

@media (max-width: 1280px) {
  .split {
    grid-template-columns: 1fr;
  }
}
</style>
