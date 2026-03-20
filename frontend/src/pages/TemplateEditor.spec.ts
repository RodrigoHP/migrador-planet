import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import TemplateEditor from './TemplateEditor.vue'

// Mock EditorLayout to isolate page-level tests
vi.mock('@/layouts/EditorLayout.vue', () => ({
  default: { template: '<div class="editor-layout-mock" data-testid="editor-layout" />' },
}))

describe('TemplateEditor (Story 11.3)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('monta sem erros', () => {
    expect(() => mount(TemplateEditor)).not.toThrow()
  })

  it('renderiza EditorLayout como componente raiz', () => {
    const wrapper = mount(TemplateEditor)
    expect(wrapper.find('[data-testid="editor-layout"]').exists()).toBe(true)
  })

  it('não renderiza conteúdo stub antigo (h1 "Editor de Template")', () => {
    const wrapper = mount(TemplateEditor)
    expect(wrapper.find('h1').exists()).toBe(false)
  })

  it('não tem div.template-editor desnecessária', () => {
    const wrapper = mount(TemplateEditor)
    expect(wrapper.find('.template-editor').exists()).toBe(false)
  })
})
