---
origin: epic-29
created: 2026-04-07
status: backlog
priority_order:
  - 30.1 (validação real auto-mapping)
  - 30.2 (converter para tabela)
  - 30.3 (parser HTML completo para árvore)
  - 30.4 (patchNodeStyle propriedades não-visuais)
  - 30.5 (console warnings backend em tempo real)
  - 30.6 (context menu PDF Reference panel)
  - 30.7 (atalhos de teclado context menu)
  - 30.8 (exportação log de warnings)
---

# Backlog — Itens fora de escopo do Epic 29

Todos os itens abaixo foram explicitamente excluídos (scope_out) das stories do Epic 29
por serem MVP ou por dependerem de outras entregas. Este documento serve como insumo
para o Epic 30 ou sprints de refinamento.

---

## 30.1 — Validar auto-mapping no Boleto Bancário (AC5 story 29.4)

**Origem:** Story 29.4 — AC5 marcado como `N/A para testes unitários`

**Problema:** Os nomes semânticos foram implementados (`_extract_semantic_name`,
`_infer_section_name`), mas o AC5 — "auto-mapping resulta em > 10/66 campos mapeados"
— nunca foi verificado com dados reais do Boleto Bancário.

**O que fazer:**
1. Processar o Boleto Bancário pelo pipeline com as mudanças da story 29.4
2. Abrir o editor e verificar quantos campos são auto-mapeados na árvore
3. Se < 10/66, investigar gargalo (nomes não extraídos corretamente? XSD path mismatch?)
4. Ajustar `_extract_semantic_name` ou a lógica de auto-binding conforme necessário

**Critério de aceite:** > 10/66 campos mapeados automaticamente após processamento.

**Complexidade:** S (se apenas validação) | M (se precisar corrigir lógica de auto-binding)

---

## 30.2 — Converter para Tabela via context menu

**Origem:** Story 29.6 scope_out — "Converter para Tabela com implementação completa"

**Problema:** O item "Converter para Tabela" no context menu existe e fecha o menu,
mas não faz nada (`handleCtxConvertTable` apenas chama `closeContextMenu()`).

**O que fazer:**
1. Definir o que "converter para tabela" significa — criar nó filho `table` a partir de
   `section` ou `flow`? Converter um grupo de `field`/`label` em estrutura de tabela?
2. Implementar a conversão em `templateStore.convertToTable(nodeId)`
3. Conectar ao `handleCtxConvertTable` em `HTMLCanvas.vue`
4. Adicionar HTML mínimo de tabela em `_generateMinimalNodeHtml` em `generation.ts`
5. Testes

**Arquivo relevante:** `frontend/src/organisms/HTMLCanvas.vue:handleCtxConvertTable`

**Complexidade:** M-L (depende da definição funcional)

---

## 30.3 — Parser HTML completo para reconstrução de árvore (Code Editor)

**Origem:** Story 29.3 scope_out — "Parser completo de HTML para reconstrução de árvore"

**Problema:** O `codeStore.syncHtmlToTree()` atual usa DOMParser para extrair apenas
`textContent` e `data-field` de cada nó. Não reconstrói nós novos, não remove nós
deletados do HTML, não sincroniza posição/tamanho (propriedades CSS `left`/`top`/`width`/`height`).

**O que fazer:**
1. Expandir `syncHtmlToTree` para detectar adição/remoção de `data-node-id` no HTML editado
2. Para nós adicionados no HTML: criar nó correspondente no templateStore
3. Para nós removidos do HTML: chamar `templateStore.removeNode`
4. Para nós com posição CSS alterada no HTML: chamar `templateStore.moveElement`/`resizeElement`

**Risco:** Loop code→tree→code — o `_isSyncing` guard já existe mas precisará cobrir os novos casos.

**Arquivo relevante:** `frontend/src/stores/codeStore.ts:syncHtmlToTree`

**Complexidade:** L

---

## 30.4 — patchNodeStyle para propriedades não-visuais

**Origem:** Story 29.7 scope_out — "patchNodeStyle para binding, visibility, formatString, styleRules"

**Problema:** `updateNodeProperty` dispara `mutationVersion++` e `patchNodeText`/`patchNodeGeometry`
para propriedades visuais. Mas propriedades como `binding`, `visibility`, `formatString` e
`styleRules` ainda não têm patch dedicado — a árvore muda mas o HTML do canvas não reflete
imediatamente (ex: visibility=false deveria ocultar o elemento no canvas).

**O que fazer:**
1. Implementar `patchNodeVisibility(nodeId, visible)` em `generation.ts` — adiciona/remove
   `style="display:none"` no elemento
2. Garantir que `updateNodeProperty('visibility', false)` chame `patchNodeVisibility`
3. Para `styleRules` — CSS injection via `borderOverrideCss` já existe; avaliar se precisa de patch separado
4. `binding` e `formatString` são metadados sem impacto visual imediato — documentar decisão

**Arquivo relevante:** `frontend/src/stores/generation.ts`, `frontend/src/stores/templateStore.ts`

**Complexidade:** S-M

---

## 30.5 — Console Panel: warnings de backend em tempo real

**Origem:** Story 29.5 scope_out — "Warnings de backend em tempo real"

**Problema:** O `ConsolePanel.vue` só exibe warnings locais (campos não mapeados via
`templateStore.flatNodes`). Warnings gerados pelo backend durante o processamento do PDF
(ex: "tabela com estrutura ambígua", "página com baixa confiança de extração") não chegam
ao painel.

**O que fazer:**
1. Verificar se o backend já retorna warnings/confidence scores na resposta do pipeline
2. Criar/usar `confidenceStore` para armazenar warnings do backend
3. Expandir `ConsolePanel.vue` para exibir warnings do `confidenceStore` além dos locais
4. Adicionar categorias: `table_inconsistent`, `low_confidence`, `missing_binding`

**Arquivo relevante:** `frontend/src/organisms/ConsolePanel.vue`,
`frontend/src/stores/confidenceStore.ts`

**Complexidade:** M

---

## 30.6 — Context menu no PDF Reference panel

**Origem:** Story 29.6 scope_out — "Context menu no PDF Reference panel"

**Problema:** O PDF Reference panel (visualização do PDF original) não tem context menu.
O operador não consegue clicar direito em uma região do PDF para mapeá-la ou marcá-la.

**O que fazer:**
1. Verificar estrutura do PDF Reference panel — usa iframe? canvas? overlay?
2. Adicionar handler `contextmenu` no overlay do PDF Reference
3. Reutilizar `CanvasContextMenu.vue` com opções relevantes para o contexto do PDF
   (ex: "Mapear esta região", "Criar campo aqui")

**Complexidade:** M (depende da estrutura atual do PDF Reference panel)

---

## 30.7 — Atalhos de teclado para ações do context menu

**Origem:** Story 29.6 scope_out — "Atalhos de teclado para as ações do menu"

**Problema:** As ações do context menu (Mapear Campo, Remover, Marcar Estático) só estão
acessíveis via clique direito. Não há atalhos de teclado (ex: `Del` para remover elemento
selecionado, `M` para mapear campo).

**O que fazer:**
1. Registrar handlers no `useCanvasKeyboard` composable para as ações do context menu
2. `Delete`/`Backspace` → `templateStore.removeNode(selectedElementId)`
3. Documentar atalhos no `CanvasContextMenu.vue` (hint de tecla ao lado do label)

**Arquivo relevante:** `frontend/src/composables/useCanvasKeyboard.ts`,
`frontend/src/molecules/CanvasContextMenu.vue`

**Complexidade:** S

---

## 30.8 — Exportação e filtragem do log de warnings

**Origem:** Story 29.5 scope_out — "Exportação do log de warnings" e "filtragem"

**Problema:** O `ConsolePanel.vue` exibe todos os warnings mas não permite:
- Filtrar por categoria (não mapeado / tabela inconsistente / baixa confiança)
- Exportar para CSV/JSON para análise externa
- Marcar warnings como "aceitos" (dismissed)

**O que fazer:**
1. Adicionar barra de filtro por categoria acima da lista de warnings
2. Botão "Exportar" → gera JSON ou CSV com a lista atual
3. Swipe/botão "Ignorar" por warning individual — salva em `localStorage` para não reaparecer

**Arquivo relevante:** `frontend/src/organisms/ConsolePanel.vue`

**Complexidade:** S

---

## Resumo de prioridade sugerida

| ID | Título | Complexidade | Impacto | Prioridade |
|----|--------|-------------|---------|-----------|
| 30.1 | Validar auto-mapping Boleto | S-M | Alto (valida entrega 29.4) | 🔴 Alta |
| 30.2 | Converter para Tabela | M-L | Médio (fluxo do operador) | 🟡 Média |
| 30.7 | Atalhos de teclado | S | Baixo (UX improvement) | 🟢 Baixa |
| 30.4 | patchNodeStyle visibility | S-M | Médio (canvas fidelidade) | 🟡 Média |
| 30.3 | Parser HTML completo | L | Baixo (MVP sync suficiente) | 🟢 Baixa |
| 30.5 | Warnings backend tempo real | M | Médio (observabilidade) | 🟡 Média |
| 30.6 | Context menu PDF Reference | M | Baixo (nice-to-have) | 🟢 Baixa |
| 30.8 | Exportação log warnings | S | Baixo (nice-to-have) | 🟢 Baixa |
