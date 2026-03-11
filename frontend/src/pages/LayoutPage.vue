<template>
  <WizardLayout :show-bibliotecas="true" @open-bibliotecas="isBibliotecasOpen = true">
    <template #stepper>
      <WizardStepper :current-step="3" />
    </template>

    <section class="layout">
      <article class="layout__controls">
        <header class="layout__header">
          <h1>Layout</h1>
          <p>Configure margens, tipografia e cor primária do template.</p>
        </header>

        <LayoutControls :model-value="layoutState" @update:model-value="onLayoutUpdate" />

        <div class="layout__actions">
          <Button variant="primary" @click="confirmLayout">Confirmar Layout</Button>
        </div>
      </article>

      <article class="layout__preview">
        <LayoutPreview :layout="layoutState" />
      </article>
    </section>
  </WizardLayout>

  <BibliotecasModal :open="isBibliotecasOpen" @close="isBibliotecasOpen = false" />
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { watchDebounced } from '@vueuse/core'
import { useRouter } from 'vue-router'
import { Button } from '@/atoms'
import { BibliotecasModal, LayoutControls, LayoutPreview, WizardStepper } from '@/organisms'
import { WizardLayout } from '@/templates'
import { useLayoutStore } from '@/stores/layout'
import { useSessionStore } from '@/stores/session'
import type { LayoutStore } from '@/stores/layout'

const router = useRouter()
const session = useSessionStore()
const layout = useLayoutStore()

const isBibliotecasOpen = ref(false)
const hasHydrated = ref(false)

const layoutState = computed<LayoutStore>(() => ({
  pageSize: layout.pageSize,
  marginTop: layout.marginTop,
  marginBottom: layout.marginBottom,
  marginLeft: layout.marginLeft,
  marginRight: layout.marginRight,
  baseFontFamily: layout.baseFontFamily,
  baseFontSize: layout.baseFontSize,
  primaryColor: layout.primaryColor,
  lineHeight: layout.lineHeight,
  bibliotecasVersions: layout.bibliotecasVersions,
  confirmed: layout.confirmed,
}))

watchDebounced(
  () => layout.$state,
  async () => {
    if (!hasHydrated.value) return
    await layout.persistToIdb()
  },
  { debounce: 500, deep: true },
)

onMounted(async () => {
  session.currentStep = 3
  await layout.hydrateFromIdb()
  hasHydrated.value = true
})

function onLayoutUpdate(value: Partial<LayoutStore>) {
  layout.$patch(value)
}

async function confirmLayout() {
  layout.confirmed = true
  await layout.persistToIdb()
  router.push('/geracao')
}
</script>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 40% 60%;
  gap: 1rem;
}

.layout__controls {
  display: grid;
  align-content: start;
  gap: 1rem;
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.75rem;
  background: #fff;
  padding: 1rem;
}

.layout__header h1 {
  margin: 0 0 0.35rem;
}

.layout__header p {
  margin: 0;
  color: var(--color-neutral-700);
}

.layout__preview {
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.75rem;
  background: #fff;
  padding: 1rem;
}

.layout__actions {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 1024px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
