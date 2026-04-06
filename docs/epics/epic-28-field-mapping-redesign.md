# Epic 28 — Field Mapping Panel Redesign

**Status:** Ready for Story Creation
**Prioridade:** Alta
**Origem:** RCA investigation 2026-04-01 (@qa Quinn) → handoff para @pm

---

## Epic Goal

Redesenhar o painel de mapeamento de campos do editor para que o operador consiga **visualizar, entender e corrigir associações campo↔XSD em um único lugar**, sem precisar navegar entre abas separadas ou usar mecanismos de drag&drop não-descobríveis.

---

## Contexto do Sistema Existente

**Tecnologia:** Vue 3 + Pinia + TypeScript (frontend), FastAPI (backend)

**Estado atual (evidências de código):**

| Componente | Localização | Problema |
|-----------|-------------|---------|
| `LeftPanel.vue` | `src/organisms/LeftPanel.vue:46-47` | 2 abas separadas: "Estrutura" + "Campos" — operações de re-mapeamento exigem alternar entre elas |
| `FieldNavigator.vue` | `src/organisms/FieldNavigator.vue` | Lista campos do PDF com raw text como nome (`4.978,54`, `000`) — sem semântica |
| `ElementInspector.vue` | `src/organisms/inspectors/ElementInspector.vue:142` | Campo "Binding" é read-only — não editável |
| `StructureTree.vue` | `src/organisms/StructureTree.vue:337` | `removeBinding` só acessível via context-menu na aba Estrutura |
| `FieldNavItem.vue` | `src/molecules/FieldNavItem.vue:81` | `emit('open-ambiguous')` disparado mas sem handler — modal nunca abre |
| `session.ts` | `src/stores/session.ts:178` | `validation_result.unmapped_xsd_fields` descartado — campos XSD obrigatórios sem match são invisíveis |

**Bug já corrigido nesta sessão:**
- `session.ts:reconcileFieldBindings()` adicionado — click campo → inspector agora funciona
- `FieldNavigator.vue:onSelectField()` — fallback por `field.path` adicionado

---

## Problema do Usuário

O operador precisa realizar **5 passos em 2 abas diferentes** para corrigir um mapeamento errado:
1. Ver campo errado na aba **Campos**
2. Trocar para aba **Estrutura**
3. Clicar direito → "Remover binding"
4. Voltar para aba **Campos**
5. Arrastar campo correto sobre o nó

Além disso, o operador **não sabe quais campos XSD ainda faltam** no template — `unmapped_xsd_fields` existe no backend mas nunca chega à UI.

---

## Stories

### Story 28.1 — Binding Editor no Inspector
**Executor:** `@dev` | **Quality Gate:** `@qa`

Substituir o campo "Binding" read-only no `ElementInspector` por um **dropdown editável** com:
- Busca/autocomplete nos `flat_paths` do XSD (`field_tree`)
- Badge de status inline (🟩🟥🟨)
- Botão "Remover binding" acessível direto no Inspector
- Sem necessidade de trocar de aba para corrigir

**Arquivos afetados:**
- `frontend/src/organisms/inspectors/ElementInspector.vue`
- `frontend/src/stores/mapping.ts` (expor `flat_paths` do field_tree)
- `frontend/src/stores/session.ts` (persistir `field_tree.flat_paths`)

**AC principais:**
- AC1: Campo "Binding" no Inspector tem dropdown com todos os XSD paths disponíveis
- AC2: Selecionar um path atualiza `node.binding` e reflete em FieldNavigator status
- AC3: Botão "✕ Remover binding" aparece quando binding está definido
- AC4: Busca por substring funciona (ex: "venc" encontra "data.vencimento")

---

### Story 28.2 — Campos XSD Visíveis + Nomes Semânticos
**Executor:** `@dev` | **Quality Gate:** `@qa`

Dois problemas de visibilidade corrigidos juntos:

**2a — Surfaçar unmapped_xsd_fields:**
- `session.ts` passa `validation_result.unmapped_xsd_fields` para `mappingStore`
- `loadPipelineFields` inclui esses campos na lista com `status='unmapped'` e badge especial (🔴 XSD-only)
- Contagem no header atualizada: `25 de 55 PDF + 8 XSD obrigatórios sem match`

**2b — Nomes semânticos:**
- Quando `xsd_field_path` existe, usar o último segmento como nome preferencial
  - Ex: `data.vencimento` → exibe "Vencimento" em vez de `30/03/2026`
- Raw PDF text fica como tooltip/subtítulo

**Arquivos afetados:**
- `frontend/src/stores/session.ts`
- `frontend/src/stores/mapping.ts`
- `frontend/src/types/pipeline.types.ts` (adicionar `unmapped_xsd_fields` no contrato)
- `frontend/src/organisms/FieldNavigator.vue`
- `frontend/src/molecules/FieldNavItem.vue`

**AC principais:**
- AC1: Campos XSD sem match aparecem na lista com badge 🔴 "XSD obrigatório"
- AC2: Campos com XSD path exibem nome semântico como título principal
- AC3: Raw PDF text visível como subtítulo/tooltip no item
- AC4: Header mostra contagem separada: `X PDF + Y XSD obrigatórios`

---

### Story 28.3 — Modal de Resolução de Ambiguidade
**Executor:** `@dev` | **Quality Gate:** `@qa`

Implementar o handler do evento `open-ambiguous` no `FieldNavigator` para abrir modal de resolução:
- Lista os candidatos XSD com score de confiança
- Permite selecionar o correto
- Confirma e atualiza binding + status 🟨→🟩

**Arquivos afetados:**
- `frontend/src/organisms/FieldNavigator.vue` (handler @open-ambiguous)
- `frontend/src/molecules/AmbiguousFieldModal.vue` (novo componente)
- `frontend/src/stores/mapping.ts` (action resolveAmbiguous)
- `frontend/src/types/field-navigator.types.ts` (candidates já tipado)

**AC principais:**
- AC1: Clicar em campo 🟨 abre modal listando candidatos com score (%)
- AC2: Selecionar candidato atualiza `node.binding` e muda status para 🟩
- AC3: Modal tem opção "Nenhum dos anteriores — deixar sem mapeamento"
- AC4: Após resolução, contagem `X de Y` é atualizada

---

### Story 28.6 — StructureTree: separar click de toggle + inspector routing correto
**Executor:** `@dev` | **Quality Gate:** `@qa`

**Bug crítico encontrado:** `StructureTreeNode.handleClick()` faz select E toggle simultaneamente, causando a percepção de que "clicar não muda o inspector". Além disso, `header`/`footer`/`flow` mapeiam para `PageInspector` que exibe campos vazios — segunda causa de "inspector não muda".

**Arquivos afetados:**
- `frontend/src/molecules/StructureTreeNode.vue` — remover `emit('toggle')` de `handleClick`
- `frontend/src/stores/inspectorStore.ts` — corrigir LEVEL_MAP para header/footer/flow
- `frontend/src/organisms/inspectors/StructuralNodeInfo.vue` — novo inspector minimalista

**AC principais:**
- AC1: Clicar no nome/área de um nó seleciona sem expandir/colapsar
- AC2: O ícone ▶/▼ continua controlando expand/collapse (comportamento atual preservado)
- AC3: Clicar em header/footer/flow mostra inspector com info básica do nó (não PageInspector)
- AC4: O inspector title e conteúdo mudam visivelmente ao clicar qualquer nó

---

### Story 28.7 — StructureTree: badge de status de binding nos nós
**Executor:** `@dev` | **Quality Gate:** `@qa`

Nós `text`/`field` não têm indicação visual de status de binding (mapeado/não mapeado/ambíguo). O texto `→ {{data.vencimento}}` está em cinza sem cor — não há distinção entre um nó bem mapeado e um com problema.

**Arquivos afetados:**
- `frontend/src/molecules/StructureTreeNode.vue` — adicionar badge 🟩🟥🟨 para nós text/field
- `frontend/src/organisms/StructureTree.vue` — passar `fieldNavItems` para colorir nós

**AC principais:**
- AC1: Nós `text`/`field` com binding mapeado mostram badge 🟩
- AC2: Nós `text`/`field` com binding ambíguo mostram 🟨
- AC3: Nós `text`/`field` sem binding mostram 🟥 discretamente
- AC4: Hover no badge mostra tooltip com o XSD path completo
- AC5: Nós container/section mostram mini barra de cobertura (X/Y filhos mapeados)

---

### Story 28.4 — Drag de Campo para o Canvas
**Executor:** `@dev` | **Quality Gate:** `@qa`

Descoberta durante elaboração do interaction spec: o canvas (HTMLCanvas.vue) não aceita drops de campo — apenas a aba Estrutura aceita. Isso torna o drag intuitivo (arrastar sobre o elemento visual) silenciosamente ineficaz.

**Arquivos afetados:**
- `frontend/src/organisms/HTMLCanvas.vue` (adicionar handlers `@dragover` + `@drop`)
- `frontend/src/organisms/CanvasSelectionOverlay.vue` (estilo "drop target" ativo)

**AC principais:**
- AC1: Arrastar campo sobre elemento no canvas mostra highlight "drop aqui" (outline azul)
- AC2: Soltar vincula o binding (igual ao drop na StructureTree)
- AC3: SE binding existente: mesmo dialog de confirmação da StructureTree
- AC4: Arrastar sobre área sem elemento: cursor `no-drop`, sem ação

---

## Sequência de Implementação

```
28.1 (Inspector binding editável)    ← pivô — bridge entre as duas abas
  ↓
28.6 (StructureTree click bug fix)   ← desbloqueador: faz a aba Estrutura funcionar
  ↓
28.2 (Campos: nomes + XSD visíveis)  ← melhora aba Campos
  ↓
28.7 (StructureTree badges status)   ← integra visualmente 28.1 + 28.2 na árvore
  ↓
28.3 (Modal de ambiguidade)          ← fecha fluxo aba Campos
  ↓
28.4 (Drag campo → canvas)           ← alternativa visual (pode ser paralelo a 28.3)
```

28.1 + 28.6 = MVP mínimo para ambas as abas funcionarem de verdade.

> **Nota:** Story 28.5 (auto-expand StructureTree ao selecionar via Campos) foi **removida** após UX audit.
> Aba Campos e aba Estrutura ocupam o mesmo painel — nunca co-existem na tela. Auto-expand de uma
> aba invisível não oferece valor ao operador. Ver `frontend/docs/epic-28-ux-audit.md`.

28.1 pode ir para produção antes das outras.

---

## Compatibilidade e Riscos

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| `StructureTree` drag-drop existente continua funcionando | Médio | 28.1-28.3 não tocam StructureTree — só adicionam |
| `flat_paths` do XSD pode ser null (XSD não fornecido) | Alto | Dropdown disabled com tooltip "XSD não disponível" |
| Contagem de campos muda com 28.2 — surpresa para usuário | Baixo | Badge visual diferenciado para XSD-only |
| Drop no canvas pode colidir com seleção por click | Médio | `dragover.prevent` só ativa se `drag-type === 'field'` |
| Auto-expand pode ser distrator se usuário está na aba Campos | Baixo | Expand só ocorre na aba Estrutura — não muda aba ativa |

**Rollback:** Todas as stories são aditivas. Reverter qualquer uma não quebra as demais.

---

## Definition of Done (Epic)

- [ ] Operador corrige binding errado em 1 ação no Inspector (sem trocar de aba)
- [ ] Campos XSD obrigatórios sem match visíveis na lista
- [ ] Campos com ambiguidade resolvíveis via modal
- [ ] Nomes semânticos substituem raw PDF text
- [ ] Testes unitários em todos os novos componentes
- [ ] Sem regressão nas funcionalidades existentes (drag, structure tree, coverage)

---

## Handoff para @sm

"Desenvolver stories detalhadas para o Epic 28 — Field Mapping Panel Redesign.

Sistema existente: Vue 3 + Pinia + TypeScript. Editor de templates HTML gerados de PDFs do Planet Express.

Integration points:
- `LeftPanel.vue` — container das abas Estrutura/Campos
- `mappingStore` (Pinia) — estado central dos mapeamentos
- `templateStore` — árvore de nós do template
- `session.ts:reconcileFieldBindings()` — já conecta field_mappings ↔ tree nodes (implementado)
- `ElementInspector.vue` — inspector do nó selecionado
- `field_tree.flat_paths` — lista todos os XSD paths disponíveis (backend)

Padrões existentes a seguir:
- Componentes em `src/organisms/` e `src/molecules/`
- Pinia stores com actions explícitas
- Testes Vitest + Vue Test Utils em `*.spec.ts` colocados ao lado do componente

Stories já sequenciadas: 28.1 → 28.2 → 28.3. Backlog original em `docs/stories/backlog/backlog-field-mapping-panel-redesign.story.md`."
