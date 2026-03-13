<template>
  <WizardLayout :show-save="true">
    <template #stepper>
      <WizardStepper :current-step="4" />
    </template>

    <section class="generation">
      <aside class="generation__left">
        <header class="generation__header">
          <h1>Geração</h1>
          <p>Revise e ajuste o código antes de exportar.</p>
        </header>

        <div v-if="isGenerating" class="generation__progress">
          <ProgressLabel :text="session.processingStep || 'Gerando artefatos...'" />
          <ProgressBar :value="session.processingPct" :animated="true" />
        </div>

        <template v-else>
          <FidelityScore v-if="fidelityScore !== null" :score="fidelityScore" />
          <p v-if="generation.fidelityComment" class="generation__comment">
            {{ generation.fidelityComment }}
          </p>

          <div v-if="generation.isFidelityLow" class="generation__warning" role="status">
            Fidelidade abaixo de 70%. Revise o resultado antes de exportar.
          </div>

        </template>

        <div v-if="!isGenerating && fidelityScore !== null" class="generation__improve">
          <Button
            variant="ghost"
            :disabled="!suggestions.length"
            @click="showSuggestions = !showSuggestions"
          >
            ✨ Melhorar com IA
          </Button>
        </div>

        <IASuggestionList
          v-if="showSuggestions && suggestions.length > 0"
          :suggestions="suggestions"
          @action="handleSuggestionAction"
          @suggestion-accepted="handleSuggestionAction"
        />

        <div class="generation__actions">
          <Button variant="ghost" @click="showAjustarLayoutModal = true">
            ◀ Ajustar Layout
          </Button>
          <Button variant="secondary" :disabled="!generation.previewJobId" @click="openPreview">
            Abrir Preview
          </Button>
          <Button variant="ghost" :loading="isGenerating" @click="generate(true)">
            Regenerar com edições
          </Button>
          <Button variant="primary" :disabled="!generation.html" @click="goToExport">
            Próximo
          </Button>
        </div>

        <div v-if="generation.previewExpired" class="generation__preview-expired">
          Preview expirado. Gere novamente para atualizar.
          <button type="button" @click="generate(false)">Regenerar Preview</button>
        </div>
      </aside>

      <section class="generation__right">
        <RightPanelToggle v-model="generation.rightPanel" />

        <div v-if="isGenerating" class="generation__processing-placeholder">
          Aguardando conclusão da geração para abrir editor/preview...
        </div>

        <div v-else>
          <article v-if="generation.rightPanel === 'html-preview'" class="generation__preview-panel">
            <iframe
              class="generation__iframe"
              title="HTML preview local"
              :srcdoc="previewDoc"
            />
          </article>

          <MonacoTabs
            v-else-if="generation.rightPanel === 'monaco'"
            :html="effectiveHtml"
            :css="effectiveCss"
            :js="effectiveJs"
            @update:html="(value) => (generation.monacoEdits.html = value)"
            @update:css="(value) => (generation.monacoEdits.css = value)"
            @update:js="(value) => (generation.monacoEdits.js = value)"
          />

          <article v-else-if="generation.rightPanel === 'wysiwyg'" class="generation__wysiwyg">
            <p>Modo WYSIWYG será integrado em iteração futura.</p>
          </article>

          <ChartjsConfigPanel
            v-else
            :initial-config="activeChartConfig"
            @save="saveChartConfig"
          />
        </div>
      </section>
    </section>
  </WizardLayout>

  <!-- Modal: Ajustar Layout -->
  <div v-if="showAjustarLayoutModal" class="modal-overlay" @click.self="showAjustarLayoutModal = false">
    <div class="modal" role="dialog" aria-modal="true">
      <p>O HTML será regenerado ao avançar. Edições feitas nesta tela serão perdidas.</p>
      <div class="modal__actions">
        <Button variant="ghost" @click="showAjustarLayoutModal = false">Cancelar</Button>
        <Button variant="secondary" @click="router.push('/layout')">Voltar ao Layout</Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, FidelityScore, ProgressBar, ProgressLabel } from '@/atoms'
import { IASuggestionList, RightPanelToggle } from '@/molecules'
import { ChartjsConfigPanel, MonacoTabs, WizardStepper } from '@/organisms'
import { WizardLayout } from '@/templates'
import { useSSE } from '@/composables/useSSE'
import { useGenerationStore } from '@/stores/generation'
import { useLayoutStore } from '@/stores/layout'
import { useMappingStore } from '@/stores/mapping'
import { useSessionStore } from '@/stores/session'
import type { ChartjsConfig, IASuggestion } from '@/types'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

const router = useRouter()
const session = useSessionStore()
const layout = useLayoutStore()
const mapping = useMappingStore()
const generation = useGenerationStore()

const isGenerating = ref(false)
const previewTimer = ref<number | null>(null)
const showAjustarLayoutModal = ref(false)
const showSuggestions = ref(false)

const sseJobId = computed(() => generation.previewJobId)
useSSE(sseJobId, {
  onDone: async () => {
    const jobId = generation.previewJobId
    if (jobId) {
      try {
        const resultRes = await fetch(`${API_BASE}/api/result/${jobId}`)
        if (resultRes.ok) {
          const data = await resultRes.json() as Record<string, unknown>
          applyGenerationPayload(data)
        }
      } catch {
        // fallback: leave existing state
      }
    }
    isGenerating.value = false
    session.isProcessing = false
  },
  onError: (event) => {
    isGenerating.value = false
    session.isProcessing = false
    session.setError(event.error ?? 'Falha na geração.')
  },
})

const defaultSuggestion: IASuggestion[] = [
  {
    id: 'sug-1',
    type: 'improvement',
    message: 'Avalie padronizar espaçamento de seções para melhorar leitura.',
    action: 'Abrir Monaco',
  },
]

const suggestions = computed(() => generation.iaSuggestions ?? defaultSuggestion)
const fidelityScore = computed(() => generation.fidelityScore)

const effectiveHtml = computed(() => generation.monacoEdits.html ?? generation.html ?? '<main></main>')
const effectiveCss = computed(() => generation.monacoEdits.css ?? generation.css ?? 'body { font-family: Inter, sans-serif; }')
const effectiveJs = computed(() => generation.monacoEdits.js ?? generation.js ?? 'console.log("preview ready");')

const previewDoc = computed(() =>
  `<!doctype html><html><head><meta charset="utf-8"/><style>${effectiveCss.value}</style></head><body>${effectiveHtml.value}<script>${effectiveJs.value}<\/script></body></html>`,
)

const activeChartConfig = computed<ChartjsConfig>(() => {
  const selectedId = generation.activeChartId ?? 'default-chart'
  return generation.chartConfigs[selectedId] ?? {
    id: selectedId,
    chartType: 'bar',
    dataField: 'valor',
    labelField: 'categoria',
    colors: ['#2563EB', '#16A34A', '#EAB308'],
    title: 'Distribuição',
  }
})

onMounted(() => {
  session.currentStep = 4
  generate(false)
})

onBeforeUnmount(() => {
  if (previewTimer.value) window.clearTimeout(previewTimer.value)
})

async function generate(includeEdits: boolean) {
  isGenerating.value = true
  session.isProcessing = true
  session.setError(null)
  session.processingStep = 'Iniciando geração...'
  session.processingPct = 5
  generation.previewExpired = false

  const payload = {
    mappingFields: mapping.fields,
    layoutConfig: layout.$state,
    monacoEdits: includeEdits ? generation.monacoEdits : {},
  }

  try {
    const res = await fetch(`${API_BASE}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (!res.ok) {
      throw new Error('Falha ao disparar geração.')
    }

    const data = await res.json() as Record<string, unknown>
    const jobId = typeof data.jobId === 'string' ? data.jobId : null
    generation.previewJobId = jobId
    armPreviewExpiration()

    if (!jobId) {
      isGenerating.value = false
      session.isProcessing = false
    } else {
      session.processingStep = 'Aguardando SSE de geração...'
      session.processingPct = 15
    }
  } catch (error: any) {
    isGenerating.value = false
    session.isProcessing = false
    session.setError(error?.message ?? 'Erro inesperado na geração.')
  }
}

function applyGenerationPayload(payload: unknown) {
  if (!payload || typeof payload !== 'object') return
  const data = payload as Record<string, unknown>

  const html = pickString(data, ['html', 'indexHtml'])
  const css = pickString(data, ['css', 'styleCss'])
  const js = pickString(data, ['js', 'baseJs'])
  const fidelityScoreValue = pickNumber(data, ['fidelityScore', 'score'])
  const fidelityComment = pickString(data, ['fidelityComment', 'comment'])
  const suggestionsValue = data.iaSuggestions

  if (html) generation.html = html
  if (css) generation.css = css
  if (js) generation.js = js
  if (fidelityScoreValue !== null) generation.fidelityScore = fidelityScoreValue
  if (fidelityComment) generation.fidelityComment = fidelityComment

  if (Array.isArray(suggestionsValue)) {
    generation.iaSuggestions = suggestionsValue as IASuggestion[]
  }

  if (!generation.html) generation.html = '<main><h1>Template Gerado</h1></main>'
  if (!generation.css) generation.css = 'main { padding: 16px; color: #171717; }'
  if (!generation.js) generation.js = 'console.log("template generated");'
  if (generation.fidelityScore === null) generation.fidelityScore = 82
  if (!generation.iaSuggestions) generation.iaSuggestions = defaultSuggestion
}

function pickString(data: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = data[key]
    if (typeof value === 'string') return value
  }
  return null
}

function pickNumber(data: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = data[key]
    if (typeof value === 'number') return value
  }
  return null
}

function armPreviewExpiration() {
  if (previewTimer.value) window.clearTimeout(previewTimer.value)
  previewTimer.value = window.setTimeout(() => {
    generation.previewExpired = true
  }, 600_000)
}

function openPreview() {
  if (!generation.previewJobId) return
  window.open(`${API_BASE}/api/preview/${generation.previewJobId}`, '_blank')
}

function saveChartConfig(config: ChartjsConfig) {
  generation.chartConfigs = { ...generation.chartConfigs, [config.id]: config }
  generation.activeChartId = config.id
}

function handleSuggestionAction(suggestion: IASuggestion) {
  if (!suggestion.action) return
  generation.rightPanel = 'monaco'
}

function goToExport() {
  router.push('/exportar')
}
</script>

<style scoped>
.generation {
  display: grid;
  grid-template-columns: 35% 65%;
  gap: 1rem;
}

.generation__left,
.generation__right {
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.75rem;
  padding: 1rem;
  background: #fff;
}

.generation__left {
  display: grid;
  align-content: start;
  gap: 0.9rem;
}

.generation__header h1 {
  margin: 0 0 0.3rem;
}

.generation__header p {
  margin: 0;
  color: var(--color-neutral-700);
}

.generation__progress {
  display: grid;
  gap: 0.5rem;
}

.generation__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.generation__preview-expired {
  border: 1px solid #fde68a;
  background: #fefce8;
  color: #854d0e;
  padding: 0.6rem;
  border-radius: 0.55rem;
  font-size: 0.85rem;
  display: grid;
  gap: 0.4rem;
}

.generation__preview-expired button {
  justify-self: start;
  border: 1px solid var(--color-warning-500);
  background: #fff;
  color: #854d0e;
  border-radius: 0.4rem;
  padding: 0.3rem 0.5rem;
  cursor: pointer;
}

.generation__warning {
  border: 1px solid #fde68a;
  background: #fffbeb;
  color: #92400e;
  border-radius: 0.55rem;
  padding: 0.55rem 0.65rem;
  font-size: 0.85rem;
}

.generation__comment {
  margin: 0;
  color: var(--color-neutral-700);
  font-size: 0.88rem;
}

.generation__right {
  display: grid;
  align-content: start;
  gap: 0.8rem;
}

.generation__processing-placeholder {
  border: 1px dashed var(--color-neutral-200);
  border-radius: 0.65rem;
  padding: 1rem;
  color: var(--color-neutral-700);
}

.generation__preview-panel {
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.65rem;
  overflow: hidden;
}

.generation__iframe {
  width: 100%;
  min-height: 520px;
  border: 0;
  background: #fff;
}

.generation__wysiwyg {
  border: 1px dashed var(--color-neutral-200);
  border-radius: 0.65rem;
  padding: 1rem;
  color: var(--color-neutral-700);
}

@media (max-width: 1024px) {
  .generation {
    grid-template-columns: 1fr;
  }
}

.generation__improve {
  display: flex;
  justify-content: flex-start;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: #fff;
  border-radius: 0.75rem;
  padding: 1.25rem;
  max-width: 420px;
  width: 90%;
  display: grid;
  gap: 1rem;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}

.modal p {
  margin: 0;
  color: var(--color-neutral-800);
}

.modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
