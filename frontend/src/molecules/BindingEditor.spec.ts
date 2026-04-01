import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BindingEditor from './BindingEditor.vue'

const FLAT_PATHS = [
  'data.vencimento',
  'data.valor',
  'data.competencia',
  'cliente.nome',
  'cliente.documento',
  'endereco.cep',
]

function mountComponent(props: ConstructorParameters<typeof BindingEditor>[0] = {}) {
  return mount(BindingEditor, {
    props: {
      modelValue: null,
      flatPaths: FLAT_PATHS,
      ...props,
    },
    global: {
      stubs: {
        Teleport: true,
      },
    },
  })
}

describe('BindingEditor', () => {
  it('exibe [Vincular →] placeholder quando binding é null e paths disponíveis', () => {
    const wrapper = mountComponent({ modelValue: null, flatPaths: FLAT_PATHS })
    // Trigger shows empty state styling and placeholder text
    expect(wrapper.find('.binding-editor--empty').exists()).toBe(true)
    expect(wrapper.text()).toContain('Sem vínculo XSD')
  })

  it('exibe binding atual com badge quando binding está definido', () => {
    const wrapper = mountComponent({
      modelValue: 'data.vencimento',
      flatPaths: FLAT_PATHS,
      status: 'mapped',
    })
    expect(wrapper.find('.binding-editor--bound').exists()).toBe(true)
    expect(wrapper.text()).toContain('data.vencimento')
    expect(wrapper.text()).toContain('🟩')
  })

  it('aparece disabled quando flatPaths está vazio', () => {
    const wrapper = mountComponent({ modelValue: null, flatPaths: [] })
    expect(wrapper.find('.binding-editor--disabled').exists()).toBe(true)
    expect(wrapper.text()).toContain('XSD não disponível')
  })

  it('aparece disabled quando flatPaths é null', () => {
    const wrapper = mountComponent({ modelValue: null, flatPaths: null })
    expect(wrapper.find('.binding-editor--disabled').exists()).toBe(true)
  })

  it('emite update:modelValue ao selecionar um path via selectPath', async () => {
    const wrapper = mountComponent({ modelValue: null, flatPaths: FLAT_PATHS })
    // Access the internal selectPath via component expose (or trigger via vm)
    const vm = wrapper.vm as unknown as { selectPath: (p: string) => void; filteredPaths: string[] }
    vm.selectPath('data.valor')
    await wrapper.vm.$nextTick()
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect(emitted![0]).toEqual(['data.valor'])
  })

  it('emite update:modelValue com null ao clicar em remover binding', async () => {
    const wrapper = mountComponent({
      modelValue: 'data.vencimento',
      flatPaths: FLAT_PATHS,
      status: 'mapped',
    })
    const removeBtn = wrapper.find('.binding-editor__remove')
    expect(removeBtn.exists()).toBe(true)
    await removeBtn.trigger('click')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect(emitted![0]).toEqual([null])
  })

  it('filtra paths por substring na busca (case-insensitive)', async () => {
    const wrapper = mountComponent({ modelValue: null, flatPaths: FLAT_PATHS })
    // search and filteredPaths are exposed via defineExpose — set directly on vm
    const vm = wrapper.vm as unknown as { search: string; filteredPaths: string[] }
    vm.search = 'venc'
    await wrapper.vm.$nextTick()
    expect(vm.filteredPaths).toContain('data.vencimento')
    expect(vm.filteredPaths).not.toContain('data.valor')
    expect(vm.filteredPaths).not.toContain('cliente.nome')
  })

  it('mantém filteredPaths com todos os paths quando search está vazio', () => {
    const wrapper = mountComponent({ modelValue: null, flatPaths: FLAT_PATHS })
    const vm = wrapper.vm as unknown as { search: string; filteredPaths: string[] }
    // search is '' by default — filteredPaths should return all
    expect(vm.filteredPaths.length).toBe(FLAT_PATHS.length)
  })

  it('não exibe botão de remover quando binding é null', () => {
    const wrapper = mountComponent({ modelValue: null, flatPaths: FLAT_PATHS })
    expect(wrapper.find('.binding-editor__remove').exists()).toBe(false)
  })
})
