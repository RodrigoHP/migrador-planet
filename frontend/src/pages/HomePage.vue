<template>
  <FullWidthLayout :show-bibliotecas="true" @open-bibliotecas="isBibliotecasOpen = true">
    <div class="flex items-center justify-center min-h-[calc(100vh-56px)]">
      <div class="w-full max-w-2xl px-4">
        <h1 class="text-2xl font-bold text-center text-neutral-800 mb-8">
          Migrador Planetexpress
        </h1>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Card Novo Template -->
          <div class="border border-neutral-200 rounded-lg p-6 bg-white flex flex-col gap-4 text-center">
            <div class="text-4xl">➕</div>
            <h2 class="text-lg font-semibold text-neutral-900 m-0">Novo Template</h2>
            <p class="text-sm text-neutral-600 flex-1 m-0">
              Iniciar migração de um novo documento PDF
            </p>
            <Button variant="primary" class="w-full" @click="startNew">Começar →</Button>
          </div>

          <!-- Card Abrir Projeto -->
          <div class="border border-neutral-200 rounded-lg p-6 bg-white flex flex-col gap-4 text-center">
            <div class="text-4xl">📂</div>
            <h2 class="text-lg font-semibold text-neutral-900 m-0">Abrir Projeto</h2>
            <p class="text-sm text-neutral-600 flex-1 m-0">
              Retomar projeto salvo (.json)
            </p>
            <Button variant="secondary" class="w-full" :loading="isOpening" @click="triggerFilePicker">
              Carregar arquivo
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- Hidden file input for project loading -->
    <input
      ref="fileInput"
      type="file"
      accept=".json"
      class="hidden"
      @change="onFileSelected"
    />
  </FullWidthLayout>

  <BibliotecasModal :open="isBibliotecasOpen" @close="isBibliotecasOpen = false" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button } from '@/atoms'
import { BibliotecasModal } from '@/organisms'
import { FullWidthLayout } from '@/templates'
import { useSessionStore } from '@/stores/session'
import { useMappingStore } from '@/stores/mapping'
import { useLayoutStore } from '@/stores/layout'
import { useGenerationStore } from '@/stores/generation'

const router = useRouter()
const session = useSessionStore()
const mapping = useMappingStore()
const layout = useLayoutStore()
const generation = useGenerationStore()

const isOpening = ref(false)
const isBibliotecasOpen = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

function startNew() {
  session.$reset()
  mapping.$reset()
  layout.$reset()
  generation.$reset()
  router.push('/upload')
}

function triggerFilePicker() {
  fileInput.value?.click()
}

async function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  isOpening.value = true
  try {
    const text = await file.text()
    const data = JSON.parse(text)
    // Basic validation — full state restoration comes in Epic 8
    if (!data || typeof data !== 'object') {
      throw new Error('Formato inválido')
    }
    // Mark analysis as completed so the /editor guard passes
    session.$reset()
    session.$patch({ analysisCompleted: true })
    router.push('/editor')
  } catch {
    session.setError('Arquivo de projeto inválido ou corrompido.')
  } finally {
    isOpening.value = false
    // Reset file input so same file can be selected again if needed
    input.value = ''
  }
}
</script>
