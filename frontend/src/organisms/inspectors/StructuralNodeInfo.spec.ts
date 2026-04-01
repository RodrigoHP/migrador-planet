import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StructuralNodeInfo from './StructuralNodeInfo.vue'
import type { TreeNode } from '@/types/template.types'

const textChild1: TreeNode = {
  id: 'child-1',
  type: 'text',
  name: 'Text1',
  binding: 'data.vencimento',
  children: [],
  properties: {},
  visibility: true,
}

const textChild2: TreeNode = {
  id: 'child-2',
  type: 'text',
  name: 'Text2',
  binding: undefined,
  children: [],
  properties: {},
  visibility: true,
}

const fieldChild: TreeNode = {
  id: 'child-3',
  type: 'field',
  name: 'Field1',
  binding: 'data.valor',
  children: [],
  properties: {},
  visibility: true,
}

const headerNode: TreeNode = {
  id: 'header-1',
  type: 'header',
  name: 'Cabeçalho Principal',
  children: [textChild1, textChild2, fieldChild],
  properties: {},
  visibility: true,
}

const footerNode: TreeNode = {
  id: 'footer-1',
  type: 'footer',
  name: 'Rodapé',
  children: [textChild1],
  properties: {},
  visibility: true,
}

const flowNode: TreeNode = {
  id: 'flow-1',
  type: 'flow',
  name: 'Fluxo Principal',
  children: [],
  properties: {},
  visibility: true,
}

describe('StructuralNodeInfo — Story 28.6', () => {
  it('renderiza tipo humanizado "Cabeçalho" para nó header', () => {
    const wrapper = mount(StructuralNodeInfo, { props: { node: headerNode } })
    expect(wrapper.text()).toContain('Cabeçalho')
  })

  it('renderiza tipo humanizado "Rodapé" para nó footer', () => {
    const wrapper = mount(StructuralNodeInfo, { props: { node: footerNode } })
    expect(wrapper.text()).toContain('Rodapé')
  })

  it('renderiza tipo humanizado "Fluxo" para nó flow', () => {
    const wrapper = mount(StructuralNodeInfo, { props: { node: flowNode } })
    expect(wrapper.text()).toContain('Fluxo')
  })

  it('mostra contagem de filhos diretos correta', () => {
    const wrapper = mount(StructuralNodeInfo, { props: { node: headerNode } })
    expect(wrapper.text()).toContain('3 elementos')
  })

  it('conta corretamente os filhos com binding vs bindáveis', () => {
    // headerNode: 3 bindable (text1+text2+field), 2 bound (text1+field)
    const wrapper = mount(StructuralNodeInfo, { props: { node: headerNode } })
    // "2 de 3 bindáveis" pattern
    expect(wrapper.text()).toContain('2')
    expect(wrapper.text()).toContain('3')
    expect(wrapper.text()).toContain('bindáveis')
  })

  it('mostra hint sobre propriedades no nó Documento', () => {
    const wrapper = mount(StructuralNodeInfo, { props: { node: headerNode } })
    expect(wrapper.text()).toContain('Propriedades de layout são configuradas no nó Documento')
  })

  it('renderiza sem erros quando node é null', () => {
    const wrapper = mount(StructuralNodeInfo, { props: { node: null } })
    expect(wrapper.find('.structural-node-info').exists()).toBe(true)
  })
})
