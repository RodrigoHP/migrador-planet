<template>
  <!-- EditorLayout orquestra o layout 3-pane completo:
       - Painel esquerdo: LeftPanel (tabs: estrutura + campos + arquivos)
       - Centro: CenterPanel (tabs: canvas + pdf + código + sync)
       - Direita: InspectorPanel (inspector reativo ao nó selecionado)
       - Inferior: TestDataPanel / TestReportPanel
       - Toolbar: TopToolbar com controles e toggles
       Store de editor (editorStore) controla activeCenterTab, activeLeftTab e
       estado de seleção. Todos os stores são hidratados em session.loadFromPipelineResult()
       antes da navegação para /editor, conforme guard em router/index.ts.
  -->
  <EditorLayout />
</template>

<script setup lang="ts">
import { watch, onMounted, onUnmounted } from 'vue'
import EditorLayout from '@/layouts/EditorLayout.vue'
import { useTemplateStore } from '@/stores/templateStore'
import { setGlobalDirty, globalDirtyFlag } from '@/composables/useUnsavedChanges'

// TemplateEditor — página /editor
// Orquestra o layout 3-pane via EditorLayout (Story 11.3)
// Os organismos (LeftPanel, CenterPanel, InspectorPanel) são compostos dentro
// do EditorLayout; os stores são populados pelo session.loadFromPipelineResult().

// Story 40.5 — UX-007: Track unsaved changes via templateStore.mutationVersion
const templateStore = useTemplateStore()
let initialMutationVersion = templateStore.mutationVersion

watch(
  () => templateStore.mutationVersion,
  (version) => {
    setGlobalDirty(version !== initialMutationVersion)
  },
)

function onBeforeUnload(e: BeforeUnloadEvent) {
  if (globalDirtyFlag.value) {
    e.preventDefault()
    e.returnValue = 'Voce tem alteracoes nao salvas. Deseja sair?'
  }
}

onMounted(() => {
  window.addEventListener('beforeunload', onBeforeUnload)
})

onUnmounted(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
  setGlobalDirty(false)
})
</script>
