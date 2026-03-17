<template>
  <div class="home-page">
    <AppHeader :show-bibliotecas="true" @open-bibliotecas="isBibliotecasOpen = true" />

    <main class="home">
      <div class="home__cards">
        <div class="home-card">
          <div class="home-card__icon">➕</div>
          <h2>Novo Projeto</h2>
          <p>Iniciar migração de um novo documento PDF</p>
          <Button variant="primary" @click="startNew">Começar →</Button>
        </div>

        <div class="home-card">
          <div class="home-card__icon">📂</div>
          <h2>Abrir Projeto</h2>
          <p>Retomar projeto salvo (.json)</p>
          <Button variant="secondary" :loading="isOpening" @click="openProject">
            Carregar arquivo
          </Button>
        </div>
      </div>
    </main>

    <BibliotecasModal :open="isBibliotecasOpen" @close="isBibliotecasOpen = false" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button } from '@/atoms'
import { AppHeader, BibliotecasModal } from '@/organisms'
import { useProject } from '@/composables/useProject'
import { useGenerationStore } from '@/stores/generation'
import { useLayoutStore } from '@/stores/layout'
import { useMappingStore } from '@/stores/mapping'
import { useSessionStore } from '@/stores/session'

const router = useRouter()
const { load } = useProject()
const session = useSessionStore()
const mapping = useMappingStore()
const layout = useLayoutStore()
const generation = useGenerationStore()

const isOpening = ref(false)
const isBibliotecasOpen = ref(false)

function startNew() {
  session.$reset()
  mapping.$reset()
  layout.$reset()
  generation.$reset()
  router.push('/upload')
}

async function openProject() {
  isOpening.value = true
  try {
    await load()
  } finally {
    isOpening.value = false
  }
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: var(--color-neutral-50);
  display: flex;
  flex-direction: column;
}

.home {
  flex: 1;
  display: grid;
  place-items: center;
  padding: 1.25rem;
}

.home__cards {
  display: flex;
  gap: 1.25rem;
  flex-wrap: wrap;
  justify-content: center;
}

.home-card {
  width: min(320px, 100%);
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.85rem;
  padding: 1.5rem;
  background: #fff;
  display: grid;
  gap: 0.75rem;
  text-align: center;
}

.home-card__icon {
  font-size: 2rem;
}

.home-card h2 {
  margin: 0;
  font-size: 1.1rem;
}

.home-card p {
  margin: 0;
  color: var(--color-neutral-600);
  font-size: 0.875rem;
}
</style>
