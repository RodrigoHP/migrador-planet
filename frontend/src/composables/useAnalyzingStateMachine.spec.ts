import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAnalyzingStateMachine } from './useAnalyzingStateMachine'
import type { RawSSEData } from './useAnalyzingStateMachine'

// Mock apiFetch to prevent real HTTP calls
vi.mock('@/services/apiFetch', () => ({
  apiFetch: vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) })),
}))

describe('useAnalyzingStateMachine', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts in initializing state', () => {
    const sm = useAnalyzingStateMachine()
    expect(sm.pageState.value).toBe('initializing')
  })

  it('transitions to processing on running event', async () => {
    const sm = useAnalyzingStateMachine()
    const event: RawSSEData = { stage: 1, status: 'running' }
    await sm.applyEvent(event)
    expect(sm.pageState.value).toBe('processing')
  })

  it('transitions to error on failed event', async () => {
    const sm = useAnalyzingStateMachine()
    const event: RawSSEData = { stage: 2, status: 'failed', summary: { error: 'Test error' } }
    await sm.applyEvent(event)
    expect(sm.pageState.value).toBe('error')
    expect(sm.errorData.value).not.toBeNull()
    expect(sm.errorData.value!.stage).toBe(2)
  })

  it('transitions to checkpoint on service_failure with checkpoint', async () => {
    const sm = useAnalyzingStateMachine()
    const event: RawSSEData = {
      stage: 1,
      status: 'service_failure',
      checkpoint: {
        type: 'confirm',
        message: 'Layout review needed',
        timeout_seconds: 300,
        timeout_action: 'fallback',
      },
    }
    await sm.applyEvent(event)
    expect(sm.pageState.value).toBe('checkpoint')
    expect(sm.checkpointData.value).not.toBeNull()
    expect(sm.checkpointData.value!.message).toBe('Layout review needed')
  })

  it('transitions to completed on pipeline_completed event', async () => {
    const sm = useAnalyzingStateMachine()
    // First set a stage to running
    await sm.applyEvent({ stage: 1, status: 'running' })
    // Then complete it
    const event: RawSSEData = { event: 'pipeline_completed', stage: 5, status: 'completed' }
    const done = await sm.applyEvent(event)
    expect(done).toBe(true)
    expect(sm.pageState.value).toBe('completed')
  })

  it('updates summary data from events', async () => {
    const sm = useAnalyzingStateMachine()
    await sm.applyEvent({
      stage: 1,
      status: 'completed',
      summary: { pdf_count: 3, page_count: 12 },
    })
    expect(sm.summaryData.value.pdfCount).toBe(3)
    expect(sm.summaryData.value.pageCount).toBe(12)
  })

  it('tracks stepper states correctly', async () => {
    const sm = useAnalyzingStateMachine()
    await sm.applyEvent({ stage: 1, status: 'completed' })
    await sm.applyEvent({ stage: 2, status: 'running' })
    // Stage 1 = done, Stage 2 = active, rest = pending
    expect(sm.stepperStates.value[0]).toBe('done')
    expect(sm.stepperStates.value[1]).toBe('active')
    expect(sm.stepperStates.value[2]).toBe('pending')
  })

  it('computes completed stages list', async () => {
    const sm = useAnalyzingStateMachine()
    await sm.applyEvent({ stage: 1, status: 'running' })
    await sm.applyEvent({ stage: 1, status: 'completed', summary: { layouts_detected: 2 } })
    expect(sm.completedStages.value.length).toBe(1)
    expect(sm.completedStages.value[0].stage).toBe(1)
  })

  it('computes pending stages', async () => {
    const sm = useAnalyzingStateMachine()
    await sm.applyEvent({ stage: 1, status: 'completed' })
    await sm.applyEvent({ stage: 2, status: 'running' })
    // Stages 3, 4, 5 should be pending
    expect(sm.pendingStages.value.length).toBe(3)
  })

  it('resets state correctly', async () => {
    const sm = useAnalyzingStateMachine()
    await sm.applyEvent({ stage: 1, status: 'running' })
    sm.resetState()
    expect(sm.pageState.value).toBe('initializing')
    expect(sm.summaryData.value.pdfCount).toBeNull()
  })

  it('updates sub-step from event', async () => {
    const sm = useAnalyzingStateMachine()
    await sm.applyEvent({ stage: 1, status: 'running', sub_step: '1.3 Normalizacao' })
    expect(sm.v2SubStep.value).toBeTruthy()
  })
})
