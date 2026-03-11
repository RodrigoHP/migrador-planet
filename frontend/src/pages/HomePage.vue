<template>
  <section class="home">
    <div class="home__card">
      <h1>Migrador Planetexpress</h1>
      <p>PDF + XSD + Dados para HTML/Knockout.js</p>
      <div class="home__actions">
        <Button variant="primary" @click="startNew">Novo Projeto</Button>
        <Button variant="secondary" :loading="isOpening" @click="openProject">
          Abrir Projeto (.json)
        </Button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button } from '@/atoms'
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
.home {
  min-height: 100vh;
  background: var(--color-neutral-50);
  display: grid;
  place-items: center;
  padding: 1.25rem;
}

.home__card {
  width: min(560px, 100%);
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.85rem;
  padding: 1.25rem;
  background: #fff;
  display: grid;
  gap: 0.75rem;
}

.home__card h1 {
  margin: 0;
}

.home__card p {
  margin: 0;
  color: var(--color-neutral-700);
}

.home__actions {
  display: flex;
  gap: 0.55rem;
}
</style>
