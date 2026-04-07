# Auditoria: Modo Diff

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

### FR41 — Modo Diff (`docs/prd-v3.md` linha 142)
- Toggle na toolbar (Modo Diff)
- Compara páginas representativas do mesmo Layout Type entre documentos lado a lado
- Destaque automático: 🟩 verde (igual), 🟨 amarelo (diferente posição), 🟥 vermelho (novo/ausente)
- Resumo de inferências: campos opcionais, seções condicionais, variações de layout
- Operador pode confirmar ou rejeitar inferências

### Wireframe — Modo Diff ATIVO (`docs/wireframes/wireframes-mid-fi.md` linha 1447)
- Layout lado a lado: Doc A (esquerda) | Doc B (direita)
- Seletor "Comparar: [DocX ▼] vs [DocY ▼]" na toolbar do diff
- Highlights por elemento com ícones 🟩/🟨/🟥
- Painel inferior "Resultado" com lista de inferências: telefone → campo opcional, movimentos → linhas variáveis, mudança de layout
- Operador pode confirmar/rejeitar cada inferência
- Seletor de Layout Type na toolbar principal filtra quais páginas representativas são comparáveis
- Toggle Modo Diff na toolbar principal (ao lado de Cobertura e Snap)

---

## Frontend — Status de Implementação

### DiffViewer.vue (`frontend/src/organisms/DiffViewer.vue`)
**Implementado:**
- Split view lado a lado: Painel A (esquerda) + Painel B (direita)
- Renderização real de PDFs em `<canvas>` via PDF.js com loading state, error state e empty state
- Navegação por página independente para cada painel (◀/▶ com contador)
- `DocumentSelector` na toolbar para selecionar Doc A e Doc B
- Highlights via componente `DiffHighlight` com `boundsA`/`boundsB` por item
- `diffStore.diffData` filtrado em `highlightsA` e `highlightsB` para cada painel

**Gaps identificados:**
- Nenhum painel de "Resultado / Inferências" visível no DiffViewer — `diffStore.inferences` existe na store mas não é renderizado no componente (sem seção de inferências confirmar/rejeitar dentro do DiffViewer)
- Os highlights usam `bounds` derivados de `node.properties.x/y/width/height` — esses valores são coordenadas do template Canvas, não coordenadas no PDF. Para o painel PDF as coordenadas não correspondem à posição real no documento original.
- Não há filtragem por Layout Type ativo dentro do DiffViewer — todos os nós do `templateStore` são usados, independente do layout selecionado na toolbar

### diffStore.ts (`frontend/src/stores/diffStore.ts`)
**Implementado:**
- `isActive: boolean` — estado do toggle
- `documentA` / `documentB` — IDs dos documentos selecionados
- `diffData: DiffItem[]` — lista de itens com `diffType: 'identical' | 'moved' | 'added' | 'removed'`
- `inferences: DiffInference[]` — derivadas dos itens non-identical
- `toggleDiffMode()`, `setDocuments(docA, docB)`, `computeDiff()`
- `computeDiff()` usa `variationMatrix` (quando disponível) para classificar presença de cada layoutId em cada documento; fallback para todos os nós como `identical`
- `confirmInference(id)` delega para `multiDocStore.confirmDetection`
- `rejectInference(id)` delega para `multiDocStore.rejectDetection`
- `highlightsByType` computed agrupando por tipo

**Gaps:**
- `computeDiff()` usa `matrix.layoutIds` (Layout Types) como elementos do diff, não coordenadas reais de elementos no PDF — a comparação é semântica, não espacial/visual. Elementos marcados como `moved` nunca ocorrem porque `boundsA === boundsB` (mesmas coordenadas do template).
- Tipo `moved` (🟨 amarelo = diferente posição) nunca é gerado — `computeDiff()` só classifica `identical`, `added`, `removed`; não compara posições entre documentos.
- Inferences derivadas dos diffItems, mas sem UI no DiffViewer para confirmação.

### TopToolbar.vue (`frontend/src/organisms/TopToolbar.vue`)
**Implementado:**
- Toggle Diff (🔀) presente na toolbar: `@click="onToggleDiff()"` → `diffStore.toggleDiffMode()` + `editorStore.diffMode = diffStore.isActive`
- Estado visual do toggle reflete `diffStore.isActive`

**Gap:**
- A toolbar não exibe qual aba/view é ativada quando Diff Mode é ligado — não há lógica que alterne automaticamente para a aba/painel DiffViewer ao ativar o toggle.

---

## Backend — Status de Implementação

Não há endpoint ou stage dedicado ao Modo Diff. O DiffViewer opera inteiramente no frontend usando:
1. PDFs carregados em memória (`sessionStore.uploadedPdfs`)
2. `variationMatrix` gerada pelo `_step_5_5_variation_matrix` (Stage 5.5)
3. Nós do `templateStore` para posições de elementos

**Consequência:** O diff visual depende de coordenadas do template (não do PDF), tornando os highlights posicionalmente incorretos no painel PDF.

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Tipo `moved` (🟨 diferente posição) nunca gerado — `computeDiff()` não compara posições entre documentos | 🔴 Crítico | Frontend / diffStore.ts | FR41 — destaque automático amarelo / wireframe linha 1464 |
| 2 | Painel de inferências (Resultado) ausente no DiffViewer — `inferences` existe na store mas sem UI | 🔴 Crítico | Frontend / DiffViewer.vue | FR41 — "resumo de inferências" / wireframe linha 1469 |
| 3 | Highlights usam coordenadas do template Canvas, não coordenadas PDF — sobreposições incorretas no painel PDF | 🟡 Importante | Frontend / diffStore.computeDiff | FR41 — destaque visual correto |
| 4 | Nenhum botão confirmar/rejeitar inferências dentro do DiffViewer | 🟡 Importante | Frontend / DiffViewer.vue | FR41 — "operador pode confirmar/rejeitar" |
| 5 | Filtragem por Layout Type ausente no DiffViewer — compara todos os nós sem considerar layout ativo | 🟡 Importante | Frontend / diffStore.computeDiff | Wireframe linha 1480 — seletor de Layout Type |
| 6 | Toggle Diff não navega automaticamente para aba/view de comparação | 🟢 Menor | Frontend / TopToolbar.vue | Wireframe linha 1441 |
| 7 | Sincronização com coverageStore ausente — campos opcionais identificados pelo diff não são destacados em amarelo no coverage overlay | 🟢 Menor | Frontend / diffStore | Ponto de verificação da auditoria |

---

## Backlog Gerado

1. **[Frontend] Implementar painel de inferências no DiffViewer** — adicionar seção "Resultado" abaixo dos painéis laterais exibindo `diffStore.inferences` com botões Confirmar/Rejeitar por item.
2. **[Frontend] Implementar detecção de `moved` (🟨)** — em `computeDiff()`, quando elemento presente em ambos os documentos, comparar coordenadas de bounding box (ex: `bbox_pdf`) e classificar como `moved` se diferença > threshold (ex: 5px).
3. **[Frontend] Corrigir coordenadas dos highlights** — `DiffHighlight` no painel PDF deve usar coordenadas do PDF (`bbox_pdf` do overlay data), não as coordenadas do template Canvas.
4. **[Frontend] Filtrar diff por Layout Type ativo** — `computeDiff()` deve considerar apenas os nós do layout selecionado na toolbar; ignorar nós de outros layouts.
5. **[Frontend] Ao ativar toggle Diff, navegar automaticamente para view de comparação** — `onToggleDiff()` na TopToolbar deve alternar para a aba central ou view que exibe o DiffViewer.
6. **[Frontend] Sincronizar Modo Diff com coverageStore** — campos marcados como `added`/`removed` pelo diff devem atualizar o status no `coverageStore` para refletir campos opcionais.

---

## Status Geral

🟡 Parcial — O DiffViewer renderiza PDFs reais lado a lado e o toggle de Diff Mode está presente na toolbar. Porém, as funcionalidades centrais da spec estão incompletas: o tipo `moved` (🟨) nunca é gerado, o painel de inferências para confirmação/rejeição está ausente no componente, e os highlights usam coordenadas do Canvas em vez do PDF.
