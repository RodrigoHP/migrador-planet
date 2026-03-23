import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import StepCircle from './StepCircle.vue'
import AnalyzingStepper from './AnalyzingStepper.vue'
import InitializingState from './InitializingState.vue'
import AnalyzingDetailCard from './AnalyzingDetailCard.vue'
import CompletedStageAccordion from './CompletedStageAccordion.vue'
import CheckpointCard from './CheckpointCard.vue'
import ErrorCard from './ErrorCard.vue'
import CompletedSummary from './CompletedSummary.vue'
import { PIPELINE_V2_STAGES, TOTAL_V2_STAGES } from '@/pages/analyzingPageConstantsV2'
import type {
  StepCircleState,
  CompletedStageSummary,
  CheckpointData,
  ErrorData,
  CompletedSummaryData,
} from '@/pages/analyzingPageConstantsV2'

// ─── StepCircle ───────────────────────────────────────────────────────────────

describe('StepCircle', () => {
  it.each<[StepCircleState, string]>([
    ['done', 'step-circle--done'],
    ['active', 'step-circle--active'],
    ['pending', 'step-circle--pending'],
    ['error', 'step-circle--error'],
    ['warning', 'step-circle--warning'],
  ])('renders state %s with class %s', (state, expectedClass) => {
    const wrapper = mount(StepCircle, { props: { state, stageNumber: 1 } })
    expect(wrapper.classes()).toContain(expectedClass)
  })

  it('shows spinner for active state', () => {
    const wrapper = mount(StepCircle, { props: { state: 'active' as StepCircleState, stageNumber: 2 } })
    expect(wrapper.find('.step-circle__spinner').exists()).toBe(true)
  })

  it('shows checkmark for done state', () => {
    const wrapper = mount(StepCircle, { props: { state: 'done' as StepCircleState, stageNumber: 1 } })
    expect(wrapper.text()).toContain('\u2713')
  })

  it('shows stage number for pending state', () => {
    const wrapper = mount(StepCircle, { props: { state: 'pending' as StepCircleState, stageNumber: 3 } })
    expect(wrapper.find('.step-circle__number').text()).toBe('3')
  })

  it('sets aria-label appropriately', () => {
    const wrapper = mount(StepCircle, { props: { state: 'active' as StepCircleState, stageNumber: 1 } })
    expect(wrapper.attributes('aria-label')).toBe('Em andamento')
  })
})

// ─── AnalyzingStepper ─────────────────────────────────────────────────────────

describe('AnalyzingStepper', () => {
  const defaultStates: StepCircleState[] = ['done', 'done', 'active', 'pending', 'pending']

  it('renders role="list" on the stepper container', () => {
    const wrapper = mount(AnalyzingStepper, {
      props: { stages: PIPELINE_V2_STAGES, stepStates: defaultStates, stageTimes: {} },
    })
    expect(wrapper.find('[role="list"]').exists()).toBe(true)
  })

  it('renders 5 listitems', () => {
    const wrapper = mount(AnalyzingStepper, {
      props: { stages: PIPELINE_V2_STAGES, stepStates: defaultStates, stageTimes: {} },
    })
    expect(wrapper.findAll('[role="listitem"]')).toHaveLength(5)
  })

  it('sets aria-current="step" on active stage', () => {
    const wrapper = mount(AnalyzingStepper, {
      props: { stages: PIPELINE_V2_STAGES, stepStates: defaultStates, stageTimes: {} },
    })
    const items = wrapper.findAll('[role="listitem"]')
    expect(items[2].attributes('aria-current')).toBe('step')
    expect(items[0].attributes('aria-current')).toBeUndefined()
  })

  it('renders stage names in PT-BR', () => {
    const wrapper = mount(AnalyzingStepper, {
      props: { stages: PIPELINE_V2_STAGES, stepStates: defaultStates, stageTimes: {} },
    })
    expect(wrapper.text()).toContain('Agrupamento de Layouts')
    expect(wrapper.text()).toContain('Extração Profunda')
    expect(wrapper.text()).toContain('Análise Estrutural')
    expect(wrapper.text()).toContain('Mapeamento de Campos')
    expect(wrapper.text()).toContain('Geração do Template')
  })

  it('shows elapsed time for completed stages', () => {
    const wrapper = mount(AnalyzingStepper, {
      props: {
        stages: PIPELINE_V2_STAGES,
        stepStates: defaultStates,
        stageTimes: { 1: 12, 2: 18 },
      },
    })
    expect(wrapper.text()).toContain('12s')
    expect(wrapper.text()).toContain('18s')
  })

  it('renders connector lines between steps (4 connectors for 5 steps)', () => {
    const wrapper = mount(AnalyzingStepper, {
      props: { stages: PIPELINE_V2_STAGES, stepStates: defaultStates, stageTimes: {} },
    })
    expect(wrapper.findAll('.stepper__connector')).toHaveLength(4)
  })
})

// ─── InitializingState ────────────────────────────────────────────────────────

describe('InitializingState', () => {
  it('renders shimmer animation bar', () => {
    const wrapper = mount(InitializingState, { props: { pdfCount: 3 } })
    expect(wrapper.find('.progress-shimmer').exists()).toBe(true)
  })

  it('shows PDF count', () => {
    const wrapper = mount(InitializingState, { props: { pdfCount: 5 } })
    expect(wrapper.text()).toContain('5')
  })

  it('shows dashes for pending metrics', () => {
    const wrapper = mount(InitializingState, { props: { pdfCount: null } })
    const values = wrapper.findAll('.info-card__value--pending')
    expect(values.length).toBeGreaterThanOrEqual(2) // pages and layouts
  })
})

// ─── AnalyzingDetailCard ──────────────────────────────────────────────────────

describe('AnalyzingDetailCard', () => {
  const defaultProps = {
    stageNumber: 3,
    totalStages: 5,
    stageName: 'Análise Estrutural',
    stageDescription: 'Identificando elementos...',
    subStep: '3.3 Classificando blocos',
    progressPct: 0.6,
    subStepPill: 'Sub-etapa 3.3',
    estimatedTimeLabel: '~25s restantes',
  }

  it('shows stage label "ESTÁGIO X DE 5"', () => {
    const wrapper = mount(AnalyzingDetailCard, { props: defaultProps })
    expect(wrapper.text().toUpperCase()).toContain('ESTÁGIO 3 DE 5')
  })

  it('renders pulsating blue dot', () => {
    const wrapper = mount(AnalyzingDetailCard, { props: defaultProps })
    expect(wrapper.find('.detail-card__pulse--blue').exists()).toBe(true)
  })

  it('renders progressbar with correct aria attributes', () => {
    const wrapper = mount(AnalyzingDetailCard, { props: defaultProps })
    const bar = wrapper.find('[role="progressbar"]')
    expect(bar.exists()).toBe(true)
    expect(bar.attributes('aria-valuenow')).toBe('60')
    expect(bar.attributes('aria-valuemin')).toBe('0')
    expect(bar.attributes('aria-valuemax')).toBe('100')
  })

  it('shows sub-step pill', () => {
    const wrapper = mount(AnalyzingDetailCard, { props: defaultProps })
    expect(wrapper.text()).toContain('Sub-etapa 3.3')
  })

  it('shows estimated time', () => {
    const wrapper = mount(AnalyzingDetailCard, { props: defaultProps })
    expect(wrapper.text()).toContain('~25s restantes')
  })

  it('renders contextual metrics when provided', () => {
    const metrics = [
      { value: 45, label: 'Blocos' },
      { value: 12, label: 'Labels' },
    ]
    const wrapper = mount(AnalyzingDetailCard, { props: { ...defaultProps, metrics } })
    expect(wrapper.text()).toContain('45')
    expect(wrapper.text()).toContain('Blocos')
    expect(wrapper.text()).toContain('12')
    expect(wrapper.text()).toContain('Labels')
  })
})

// ─── CompletedStageAccordion ──────────────────────────────────────────────────

describe('CompletedStageAccordion', () => {
  const stages: CompletedStageSummary[] = [
    { stage: 1, name: 'Agrupamento de Layouts', shortSummary: '2 layouts', elapsedSeconds: 12, details: ['2 layouts encontrados', '120 páginas'] },
    { stage: 2, name: 'Extração Profunda', shortSummary: '342 textos', elapsedSeconds: 18, details: ['342 blocos de texto'] },
  ]

  it('renders all completed stages', () => {
    const wrapper = mount(CompletedStageAccordion, { props: { stages, label: 'Concluídos' } })
    expect(wrapper.findAll('[role="button"]')).toHaveLength(2)
  })

  it('has aria-expanded="false" by default', () => {
    const wrapper = mount(CompletedStageAccordion, { props: { stages } })
    const btns = wrapper.findAll('[role="button"]')
    expect(btns[0].attributes('aria-expanded')).toBe('false')
  })

  it('expands on click and sets aria-expanded="true"', async () => {
    const wrapper = mount(CompletedStageAccordion, { props: { stages } })
    const btn = wrapper.findAll('[role="button"]')[0]
    await btn.trigger('click')
    expect(btn.attributes('aria-expanded')).toBe('true')
    expect(wrapper.text()).toContain('2 layouts encontrados')
  })

  it('collapses on second click', async () => {
    const wrapper = mount(CompletedStageAccordion, { props: { stages } })
    const btn = wrapper.findAll('[role="button"]')[0]
    await btn.trigger('click')
    await btn.trigger('click')
    expect(btn.attributes('aria-expanded')).toBe('false')
  })

  it('expands on Enter key', async () => {
    const wrapper = mount(CompletedStageAccordion, { props: { stages } })
    const btn = wrapper.findAll('[role="button"]')[0]
    await btn.trigger('keydown', { key: 'Enter' })
    expect(btn.attributes('aria-expanded')).toBe('true')
  })

  it('expands on Space key', async () => {
    const wrapper = mount(CompletedStageAccordion, { props: { stages } })
    const btn = wrapper.findAll('[role="button"]')[0]
    await btn.trigger('keydown', { key: ' ' })
    expect(btn.attributes('aria-expanded')).toBe('true')
  })

  it('has tabindex="0" for keyboard navigation', () => {
    const wrapper = mount(CompletedStageAccordion, { props: { stages } })
    const btns = wrapper.findAll('[role="button"]')
    expect(btns[0].attributes('tabindex')).toBe('0')
  })

  it('shows elapsed time', () => {
    const wrapper = mount(CompletedStageAccordion, { props: { stages } })
    expect(wrapper.text()).toContain('12s')
    expect(wrapper.text()).toContain('18s')
  })
})

// ─── CheckpointCard ───────────────────────────────────────────────────────────

describe('CheckpointCard', () => {
  const checkpoint: CheckpointData = {
    stage: 1,
    stageName: 'Agrupamento de Layouts',
    message: 'A confiança está em 62%.',
    confidence: 62,
    layouts: [
      { id: 'a', label: 'Layout A', pageCount: 80 },
      { id: 'b', label: 'Layout B', pageCount: 35, similar: true },
    ],
    suggestion: { text: 'Unir Layout B e C', resultLayouts: 2, resultConfidence: 89 },
    timeoutSeconds: 300,
    timeoutAction: 'confirm',
  }

  it('has role="alert"', () => {
    const wrapper = mount(CheckpointCard, { props: { checkpoint, visible: true } })
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
  })

  it('shows stage name in title', () => {
    const wrapper = mount(CheckpointCard, { props: { checkpoint, visible: true } })
    expect(wrapper.text()).toContain('Agrupamento de Layouts')
  })

  it('renders layout thumbnails with role="button"', () => {
    const wrapper = mount(CheckpointCard, { props: { checkpoint, visible: true } })
    const thumbs = wrapper.findAll('[role="button"]')
    expect(thumbs.length).toBeGreaterThanOrEqual(2)
  })

  it('shows suggestion card', () => {
    const wrapper = mount(CheckpointCard, { props: { checkpoint, visible: true } })
    expect(wrapper.text()).toContain('Sugestão do sistema')
    expect(wrapper.text()).toContain('Unir Layout B e C')
  })

  it('shows countdown timer with aria-live="polite"', () => {
    const wrapper = mount(CheckpointCard, { props: { checkpoint, visible: true } })
    const timer = wrapper.find('[aria-live="polite"]')
    expect(timer.exists()).toBe(true)
    expect(timer.text()).toContain('5:00') // 300 seconds
  })

  it('emits "decide" with action on button click', async () => {
    const wrapper = mount(CheckpointCard, { props: { checkpoint, visible: true } })
    const buttons = wrapper.findAll('button')
    // First button = Aceitar sugestão -> 'confirm'
    await buttons[0].trigger('click')
    expect(wrapper.emitted('decide')).toBeTruthy()
    expect(wrapper.emitted('decide')![0]).toEqual(['confirm'])
  })

  it('emits "skip" on third button click', async () => {
    const wrapper = mount(CheckpointCard, { props: { checkpoint, visible: true } })
    const buttons = wrapper.findAll('button')
    await buttons[2].trigger('click')
    expect(wrapper.emitted('decide')![0]).toEqual(['skip'])
  })
})

// ─── ErrorCard ────────────────────────────────────────────────────────────────

describe('ErrorCard', () => {
  const error: ErrorData = {
    stage: 3,
    stageName: 'Análise Estrutural',
    service: 'GPT-4o',
    errorMessage: 'Serviço de visão não respondeu após 2 tentativas.',
    retriesAttempted: 1,
  }

  it('has role="alert"', () => {
    const wrapper = mount(ErrorCard, { props: { error } })
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
  })

  it('shows "O que aconteceu?" section', () => {
    const wrapper = mount(ErrorCard, { props: { error } })
    expect(wrapper.text()).toContain('O que aconteceu?')
    expect(wrapper.text()).toContain('Serviço de visão não respondeu')
  })

  it('renders 3 action buttons (retry, fallback, abort)', () => {
    const wrapper = mount(ErrorCard, { props: { error } })
    const btns = wrapper.findAll('.error-btn')
    expect(btns).toHaveLength(3)
  })

  it('emits "decide" with "retry" on first button', async () => {
    const wrapper = mount(ErrorCard, { props: { error } })
    await wrapper.findAll('.error-btn')[0].trigger('click')
    expect(wrapper.emitted('decide')![0]).toEqual(['retry'])
  })

  it('emits "decide" with "fallback" on second button', async () => {
    const wrapper = mount(ErrorCard, { props: { error } })
    await wrapper.findAll('.error-btn')[1].trigger('click')
    expect(wrapper.emitted('decide')![0]).toEqual(['fallback'])
  })

  it('emits "decide" with "abort" on third button', async () => {
    const wrapper = mount(ErrorCard, { props: { error } })
    await wrapper.findAll('.error-btn')[2].trigger('click')
    expect(wrapper.emitted('decide')![0]).toEqual(['abort'])
  })

  it('shows stage name and failure label', () => {
    const wrapper = mount(ErrorCard, { props: { error } })
    expect(wrapper.text()).toContain('Análise Estrutural — Falha')
    expect(wrapper.text().toUpperCase()).toContain('FALHA NO ESTÁGIO 3')
  })

  it('shows "Continuar sem GPT-4o" in fallback button', () => {
    const wrapper = mount(ErrorCard, { props: { error } })
    expect(wrapper.text()).toContain('Continuar sem GPT-4o')
  })
})

// ─── CompletedSummary ─────────────────────────────────────────────────────────

describe('CompletedSummary', () => {
  const summary: CompletedSummaryData = {
    totalTimeSeconds: 83,
    layoutCount: 2,
    pageCount: 120,
    fieldsMapped: 67,
    coverageTotal: 92,
    coverageBreakdown: [
      { label: 'Campos', pct: 95 },
      { label: 'Tabelas', pct: 85 },
    ],
    warnings: ['<strong>2 campos ambíguos</strong> para revisão.'],
  }

  it('shows "Análise concluída!" title', () => {
    const wrapper = mount(CompletedSummary, { props: { summary } })
    expect(wrapper.text()).toContain('Análise concluída!')
  })

  it('shows 4-metric grid', () => {
    const wrapper = mount(CompletedSummary, { props: { summary } })
    expect(wrapper.findAll('.summary-stat')).toHaveLength(4)
  })

  it('shows coverage total and breakdown', () => {
    const wrapper = mount(CompletedSummary, { props: { summary } })
    expect(wrapper.text()).toContain('92%')
    expect(wrapper.text()).toContain('Campos')
    expect(wrapper.text()).toContain('95%')
    expect(wrapper.text()).toContain('Tabelas')
    expect(wrapper.text()).toContain('85%')
  })

  it('shows warnings section', () => {
    const wrapper = mount(CompletedSummary, { props: { summary } })
    expect(wrapper.find('.summary-warnings').exists()).toBe(true)
  })

  it('renders "Abrir no Editor" button', () => {
    const wrapper = mount(CompletedSummary, { props: { summary } })
    const btn = wrapper.find('.btn-editor')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toContain('Abrir no Editor')
  })

  it('emits "open-editor" on button click', async () => {
    const wrapper = mount(CompletedSummary, { props: { summary } })
    await wrapper.find('.btn-editor').trigger('click')
    expect(wrapper.emitted('open-editor')).toBeTruthy()
  })

  it('formats total time correctly (1 min 23 seg)', () => {
    const wrapper = mount(CompletedSummary, { props: { summary } })
    expect(wrapper.text()).toContain('1 min 23 seg')
  })
})

// ─── SSE v1 Backward Compatibility (constants) ───────────────────────────────

describe('Pipeline V2 Constants', () => {
  it('has exactly 5 stages', () => {
    expect(PIPELINE_V2_STAGES).toHaveLength(5)
    expect(TOTAL_V2_STAGES).toBe(5)
  })

  it('stages have PT-BR names', () => {
    const names = PIPELINE_V2_STAGES.map((s) => s.name)
    expect(names).toEqual([
      'Agrupamento de Layouts',
      'Extração Profunda',
      'Análise Estrutural',
      'Mapeamento de Campos',
      'Geração do Template',
    ])
  })

  it('stages have English names for SSE matching', () => {
    const names = PIPELINE_V2_STAGES.map((s) => s.nameEn)
    expect(names).toEqual([
      'Layout Clustering',
      'Deep Extraction',
      'Structural Analysis',
      'Field Mapping',
      'Template Generation',
    ])
  })
})
