/**
 * HTMLCanvas — Story 29.2 (AC7)
 *
 * Tests that canvas re-render is triggered after:
 * - updateNodeProperty (text property) → patchNodeText
 * - moveElement (called by endDrag) → patchNodeGeometry
 * - resizeElement (called by endResize) → patchNodeGeometry
 *
 * These tests exercise the store integration layer (ADR-029, Opção C).
 * The watcher in HTMLCanvas.vue fires automatically when generationStore.templateDraft
 * receives a new object reference — that Vue reactivity mechanism is tested implicitly
 * by asserting templateDraft is updated.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useGenerationStore } from '@/stores/generation'
import { useTemplateStore } from '@/stores/templateStore'
import type { DocumentTree } from '@/types/template.types'

// ─── Test fixture helpers ─────────────────────────────────────────────────────

const SAMPLE_HTML = `<div data-layout-type="flow"><span data-node-id="node-label-1" data-type="label" style="position:absolute;left:10px;top:20px;width:100px;height:30px">Cedente</span></div>`

function buildTree(nodeId: string): DocumentTree {
  return {
    root: {
      id: 'root-1',
      type: 'document',
      name: 'Documento',
      binding: '',
      isOptional: false,
      visibility: true,
      properties: {},
      children: [
        {
          id: nodeId,
          type: 'label',
          name: 'Cedente',
          binding: '',
          isOptional: false,
          visibility: true,
          properties: { x: 10, y: 20, width: 100, height: 30, text: 'Cedente' },
          children: [],
        },
      ],
    },
  }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('HTMLCanvas — re-render via canvas patch (Story 29.2 AC7)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('AC7a: re-render após updateNodeProperty(text)', () => {
    it('atualiza templateDraft.html quando operador edita propriedade text', () => {
      const genStore = useGenerationStore()
      const tplStore = useTemplateStore()

      genStore.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })
      tplStore.loadTree(buildTree('node-label-1'))

      const refAntes = genStore.templateDraft

      tplStore.updateNodeProperty('node-label-1', 'text', 'Nome Atualizado')

      // templateDraft foi substituído (nova referência) → watcher do canvas dispara
      expect(genStore.templateDraft).not.toBe(refAntes)
      expect(genStore.templateDraft?.html).toContain('Nome Atualizado')
    })

    it('mutationVersion é incrementado após updateNodeProperty', () => {
      const tplStore = useTemplateStore()
      const genStore = useGenerationStore()
      genStore.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })
      tplStore.loadTree(buildTree('node-label-1'))

      const versionAntes = tplStore.mutationVersion

      tplStore.updateNodeProperty('node-label-1', 'text', 'Novo Texto')

      expect(tplStore.mutationVersion).toBe(versionAntes + 1)
    })

    it('não chama patchNodeText para propriedades não-text', () => {
      const genStore = useGenerationStore()
      const tplStore = useTemplateStore()

      genStore.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })
      tplStore.loadTree(buildTree('node-label-1'))

      const refAntes = genStore.templateDraft

      tplStore.updateNodeProperty('node-label-1', 'binding', 'novo.binding')

      // HTML não deve ter sido alterado por patchNodeText
      expect(genStore.templateDraft?.html).toBe(refAntes?.html)
    })
  })

  describe('AC7b: re-render após endDrag (moveElement)', () => {
    it('atualiza templateDraft.html quando operador arrasta elemento', () => {
      const genStore = useGenerationStore()
      const tplStore = useTemplateStore()

      genStore.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })
      tplStore.loadTree(buildTree('node-label-1'))

      const refAntes = genStore.templateDraft

      // endDrag chama templateStore.moveElement(id, dx, dy)
      tplStore.moveElement('node-label-1', 30, 40)

      // templateDraft foi substituído → watcher do canvas dispara
      expect(genStore.templateDraft).not.toBe(refAntes)
      expect(genStore.templateDraft?.html).toContain('left:40px')  // 10 + 30
      expect(genStore.templateDraft?.html).toContain('top:60px')   // 20 + 40
    })

    it('mutationVersion é incrementado após moveElement', () => {
      const tplStore = useTemplateStore()
      const genStore = useGenerationStore()
      genStore.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })
      tplStore.loadTree(buildTree('node-label-1'))

      const versionAntes = tplStore.mutationVersion

      tplStore.moveElement('node-label-1', 5, 5)

      expect(tplStore.mutationVersion).toBe(versionAntes + 1)
    })

    it('preserva posição correta após múltiplos drags sequenciais', () => {
      const genStore = useGenerationStore()
      const tplStore = useTemplateStore()

      genStore.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })
      tplStore.loadTree(buildTree('node-label-1'))

      tplStore.moveElement('node-label-1', 10, 0)  // x: 10→20
      tplStore.moveElement('node-label-1', 10, 0)  // x: 20→30

      expect(genStore.templateDraft?.html).toContain('left:30px')
    })
  })

  describe('AC7c: re-render após endResize (resizeElement)', () => {
    it('atualiza templateDraft.html quando operador redimensiona elemento', () => {
      const genStore = useGenerationStore()
      const tplStore = useTemplateStore()

      genStore.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })
      tplStore.loadTree(buildTree('node-label-1'))

      const refAntes = genStore.templateDraft

      tplStore.resizeElement('node-label-1', 250, 60)

      expect(genStore.templateDraft).not.toBe(refAntes)
      expect(genStore.templateDraft?.html).toContain('width:250px')
      expect(genStore.templateDraft?.html).toContain('height:60px')
    })

    it('mutationVersion é incrementado após resizeElement', () => {
      const tplStore = useTemplateStore()
      const genStore = useGenerationStore()
      genStore.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })
      tplStore.loadTree(buildTree('node-label-1'))

      const versionAntes = tplStore.mutationVersion

      tplStore.resizeElement('node-label-1', 150, 50)

      expect(tplStore.mutationVersion).toBe(versionAntes + 1)
    })
  })

  describe('Sem templateDraft carregado — sem erro', () => {
    it('moveElement não quebra quando templateDraft é null', () => {
      const tplStore = useTemplateStore()
      tplStore.loadTree(buildTree('node-label-1'))

      // generationStore.templateDraft é null — não deve lançar exceção
      expect(() => tplStore.moveElement('node-label-1', 10, 10)).not.toThrow()
    })

    it('updateNodeProperty(text) não quebra quando templateDraft é null', () => {
      const tplStore = useTemplateStore()
      tplStore.loadTree(buildTree('node-label-1'))

      expect(() => tplStore.updateNodeProperty('node-label-1', 'text', 'Novo')).not.toThrow()
    })
  })
})
