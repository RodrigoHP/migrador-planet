# Epic 33 — Inspector Loop Completo

**Prioridade:** P1
**Fase:** 2
**Estimativa:** 9 stories (originalmente 10 — 33.9 removida por já estar implementada)
**Dependências:** Epic 32 (data-node-id nos elementos)
**Objetivo:** Operador edita qualquer propriedade via Inspector e vê o resultado imediatamente no Canvas. Todos os níveis do Inspector funcionam corretamente.

---

## Contexto

O Inspector Hierárquico tem 4 níveis implementados, mas Header/Footer/Flow são roteados incorretamente, posição/tamanho são read-only, bulk updates não disparam re-render, e vários controles faltam (tipo de campo, keep-together, layer visibility/lock).

> **Nota QA (2026-04-07):** Story 33.9 (FontWarning) **removida** — já integrada em `ElementInspector.vue:43-49` com `useFontCascade` e upload funcional.

---

## Stories

### 33.1 — Corrigir roteamento Header/Footer/Flow → SectionInspector
**Gap:** C7
**Escopo:** Frontend (`inspectorStore.ts`)
**QA Note:** Story 28.6 mudou o roteamento de `'page'` → `'structural'` (StructuralNodeInfo). Isso corrigiu o bug original (PageInspector errado) mas StructuralNodeInfo é read-only — o operador não consegue editar altura, padding, repetição, visibilidade. SectionInspector já existe e já tem todas essas funcionalidades incluindo "Repetir em cada página" integrado ao Layout Engine.
**AC:**
- [ ] `LEVEL_MAP` em `inspectorStore.ts`: mudar `header/footer/flow` de `'structural'` → `'section'`
- [ ] Selecionar Header na árvore abre SectionInspector com altura, padding, repetição, visibilidade
- [ ] Selecionar Footer na árvore abre SectionInspector
- [ ] Selecionar Flow na árvore abre SectionInspector
- [ ] StructuralNodeInfo.vue mantido para nós sem inspector dedicado (container genérico, etc.)
- [ ] Verificar que SectionInspector funciona corretamente com nós do tipo header/footer/flow (propriedades compatíveis)

### 33.2 — Posição X/Y e tamanho W/H editáveis no ElementInspector
**Gap:** C8
**Escopo:** Frontend (`ElementInspector.vue`)
**AC:**
- [ ] Campos X, Y, Largura, Altura são inputs editáveis (não read-only)
- [ ] Editar valor → `templateStore.updateNodeProperty()` + `patchNodeGeometry()`
- [ ] Canvas re-renderiza na posição/tamanho novos
- [ ] Validação: valores numéricos positivos, limites da página

### 33.3 — `updateNodeProperties()` dispara patch e re-render
**Gap:** I6
**Escopo:** Frontend (`templateStore.ts`)
**AC:**
- [ ] `updateNodeProperties()` (bulk) chama patch correspondente para cada propriedade alterada
- [ ] `mutationVersion` incrementado após bulk update
- [ ] Canvas re-renderiza após edição bulk via Inspector
- [ ] Teste: editar múltiplas propriedades no Inspector → todas refletem no Canvas

### 33.4 — Implementar `patchNodeStyle()` em generation.ts
**Gap:** I8
**Escopo:** Frontend (`generation.ts`)
**AC:**
- [ ] `patchNodeStyle(nodeId, property, value)` atualiza atributo `style` inline no HTML via DOMParser
- [ ] Suporta: font-size, font-weight, font-style, color, background-color
- [ ] `templateStore.updateNodeProperty()` chama `patchNodeStyle()` para propriedades tipográficas
- [ ] Canvas reflete mudanças de estilo em tempo real

### 33.5 — Re-render Canvas após mudança de visibility
**Gap:** C23
**Escopo:** Frontend (`templateStore.ts`, `generation.ts`)
**QA Note:** VisibilityControl emite `VisibilityConfig` **objeto** (não boolean). A condição `typeof value === 'boolean'` em `updateNodeProperty` nunca faz match para visibility. AC deve usar `value.mode`.
**AC:**
- [ ] Corrigir `updateNodeProperty`: detectar `VisibilityConfig` via `value.mode` (não `typeof value === 'boolean'`)
- [ ] Mudar visibilidade (sempre/condicional/escondido) no VisibilityControl dispara `patchNodeVisibility()`
- [ ] Canvas aplica `display:none` ou `<!-- ko if -->` corretamente
- [ ] Elemento some/aparece no Canvas conforme a visibilidade selecionada

### 33.6 — Tipo de campo selecionável no ElementInspector
**Gap:** I16
**Escopo:** Frontend (`ElementInspector.vue`)
**AC:**
- [ ] Badge read-only substituído por dropdown/select
- [ ] Opções: Texto, Número, Moeda (BRL), Data, CPF, CNPJ, Percentual, Telefone, Personalizado
- [ ] Seleção atualiza `templateStore.updateNodeProperty(id, 'fieldType', value)`
- [ ] Tipo influencia formatação no FormatStringEditor

### 33.7 — Keep-together editável no TableInspector
**Gap:** I29
**Escopo:** Frontend (`TableInspector.vue`)
**AC:**
- [ ] Campo "Manter Junto" é checkbox editável (não read-only)
- [ ] Valor persiste em `node.properties.keepTogether`
- [ ] `calculatePageBreaks()` em `usePagination.ts` honra flag keepTogether
- [ ] Bloco com keepTogether=true move inteiro para próxima página quando não cabe

### 33.8 — Seleção de header row no TableInspector
**Gap:** I30
**Escopo:** Frontend (`TableInspector.vue`)
**AC:**
- [ ] Controle para marcar qual(is) linha(s) compõem o `<thead>` estático
- [ ] Padrão: primeira linha = header
- [ ] Alteração reflete na geração do HTML (`_generate_table_html`)
- [ ] "Repetir cabeçalho" funciona com a linha selecionada

### ~~33.9~~ — REMOVIDA (já implementada)
> FontWarning já integrado em `ElementInspector.vue:43-49` com `useFontCascade` e upload funcional via IndexedDB/Bibliotecas.

### 33.10 — LayerPanel: toggle visibilidade + lock/unlock
**Gap:** I34
**Escopo:** Frontend (`LayerPanel.vue`)
**AC:**
- [ ] Ícone 👁 por camada que alterna visibilidade (visible/hidden)
- [ ] Ícone 🔒 por camada que alterna lock (locked impede drag/resize/select no Canvas)
- [ ] Estado locked/visible persiste no `templateStore` como propriedades do nó
- [ ] Canvas respeita locked: elemento não é arrastável nem redimensionável
- [ ] Canvas respeita hidden: elemento não é renderizado no iframe
