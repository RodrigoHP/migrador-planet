import { useSessionStore } from '@/stores/session'
import { useMappingStore } from '@/stores/mapping'
import { useLayoutStore } from '@/stores/layout'
import { useGenerationStore } from '@/stores/generation'
import { useRouter } from 'vue-router'
import { ref } from 'vue'
import { openDB } from 'idb'
import type { ProjectFile } from '@/types'

const STEP_TO_ROUTE: Record<number, string> = {
  0: '/',
  1: '/upload',
  2: '/campos',
  3: '/layout',
  4: '/geracao',
  5: '/exportar',
}

let dbPromise: ReturnType<typeof openDB> | null = null

function getDb() {
  if (!dbPromise) {
    dbPromise = openDB('migrador', 1, {
      upgrade(db) {
        if (!db.objectStoreNames.contains('project')) {
          db.createObjectStore('project')
        }
      },
    })
  }
  return dbPromise
}

export function useProject() {
  const session = useSessionStore()
  const mapping = useMappingStore()
  const layout = useLayoutStore()
  const generation = useGenerationStore()
  const router = useRouter()
  const currentProjectName = ref<string | null>(null)

  async function save() {
    const data: ProjectFile = {
      version: '1.0',
      savedAt: new Date().toISOString(),
      currentStep: session.currentStep,
      session: {
        currentStep: session.currentStep,
        jobId: session.jobId,
        processingStep: session.processingStep,
        processingPct: session.processingPct,
        error: session.error,
        crossValidation: session.crossValidation,
        extraction: session.extraction,
      },
      mapping: {
        fields: mapping.fields,
        confirmed: mapping.confirmed,
      },
      layout: {
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
      },
      generation: {
        html: generation.html,
        css: generation.css,
        js: generation.js,
        previewJobId: generation.previewJobId,
        previewExpired: generation.previewExpired,
        rightPanel: generation.rightPanel,
        activeChartId: generation.activeChartId,
        monacoEdits: generation.monacoEdits,
        chartConfigs: generation.chartConfigs,
      },
    }

    const json = JSON.stringify(data, null, 2)
    const db = await getDb()
    await db.put('project', data, 'current')

    if ('showSaveFilePicker' in window) {
      try {
        const handle = await (window as any).showSaveFilePicker({
          suggestedName: 'projeto.json',
          types: [{ description: 'Projeto JSON', accept: { 'application/json': ['.json'] } }],
        })
        const writable = await handle.createWritable()
        await writable.write(json)
        await writable.close()
        currentProjectName.value = handle.name ?? 'projeto.json'
      } catch (e: any) {
        if (e.name !== 'AbortError') throw e
      }
    } else {
      // Fallback: download via <a>
      const blob = new Blob([json], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'projeto.json'
      a.click()
      currentProjectName.value = a.download
      setTimeout(() => URL.revokeObjectURL(url), 60_000)
    }
  }

  async function load() {
    let file: File | null = null

    if ('showOpenFilePicker' in window) {
      try {
        const [handle] = await (window as any).showOpenFilePicker({
          types: [{ description: 'Projeto JSON', accept: { 'application/json': ['.json'] } }],
        })
        file = await handle.getFile()
      } catch (e: any) {
        if (e.name === 'AbortError') return
        throw e
      }
    } else {
      file = await new Promise<File | null>((resolve) => {
        const input = document.createElement('input')
        input.type = 'file'
        input.accept = '.json'
        input.onchange = () => resolve(input.files?.[0] ?? null)
        input.click()
      })
    }

    if (!file) return
    currentProjectName.value = file.name

    const text = await file.text()
    const data: ProjectFile = JSON.parse(text)

    session.$patch({
      currentStep: data.session.currentStep as 0 | 1 | 2 | 3 | 4 | 5,
      jobId: data.session.jobId,
      processingStep: data.session.processingStep,
      processingPct: data.session.processingPct,
      error: data.session.error,
      crossValidation: data.session.crossValidation,
      extraction: data.session.extraction,
    })

    mapping.$patch({
      fields: data.mapping.fields,
      confirmed: data.mapping.confirmed,
    })

    layout.$patch(data.layout)

    generation.$patch({
      html: data.generation.html,
      css: data.generation.css,
      js: data.generation.js,
      previewJobId: data.generation.previewJobId,
      previewExpired: data.generation.previewExpired,
      rightPanel: data.generation.rightPanel,
      activeChartId: data.generation.activeChartId,
      monacoEdits: data.generation.monacoEdits,
      chartConfigs: data.generation.chartConfigs,
    })

    const route = STEP_TO_ROUTE[data.currentStep] ?? '/'
    router.push(route)
  }

  return { save, load, currentProjectName }
}
