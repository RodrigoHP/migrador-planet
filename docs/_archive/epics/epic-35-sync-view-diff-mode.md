# Epic 35 — Sync View & Diff Mode Completo

**Prioridade:** P2
**Fase:** 3
**Estimativa:** 8 stories (originalmente 9 — 35.7 removida por já estar implementada)
**Dependências:** Epic 32 (fidelidade visual), Epic 34 (coverage accuracy)
**Objetivo:** Comparação PDF↔Canvas funcional com âncoras, seleção sincronizada, diff com tipo `moved`, e Analisador Multi-Documento com Matriz Campos×PDFs.

---

## Contexto

SyncView tem âncoras hardcoded [], seleção sincronizada não funcional, ignora Layout Type ativo. DiffViewer nunca gera tipo `moved`, painel de inferências ausente, highlights usam coordenadas erradas. MultiDocAnalyzer mostra Layout Types × PDFs em vez de Campos × PDFs.

> **Nota QA (2026-04-07):** Story 35.7 (ocultar MultiDocAnalyzer com 1 PDF) **removida** — `EditorLayout.vue:41` já tem `v-if="multiDocStore.hasMultiplePdfs"`.

---

## Stories

### 35.1 — Âncoras de layout no SyncView + seleção sincronizada
**Gap:** C15, C16
**Escopo:** Backend (pipeline output) + Frontend (`SyncView.vue`, `useSync.ts`)
**AC:**
- [ ] Pipeline retorna `anchors[]` por Layout Type com `{id, label, bbox_canvas, bbox_pdf}`
- [ ] `SyncView.vue` substitui `anchors = []` por consumo de dados reais do store
- [ ] `LayoutAnchor` renderizado em ambos os painéis com linha conectora visual
- [ ] Clique em elemento no painel Canvas → destaca bounding box correspondente no painel PDF
- [ ] `syncSelection` conectado a cliques nos iframes via `postMessage`

### 35.2 — SyncView usa página representativa do Layout Type ativo
**Gap:** I25
**Escopo:** Frontend (`SyncView.vue`)
**AC:**
- [ ] Ao carregar PDF, usa `layoutStore.activeLayout.representativePages[0]`
- [ ] Ao trocar Layout Type, navega para página representativa correspondente
- [ ] PDF exibido corresponde ao layout selecionado na toolbar

### 35.3 — Tipo `moved` (amarelo) no Diff
**Gap:** C13
**Escopo:** Frontend (`diffStore.ts`)
**AC:**
- [ ] `computeDiff()` compara bounding boxes entre documentos
- [ ] Elemento presente em ambos com diferença de posição > 5px → classificado como `moved`
- [ ] Highlight 🟨 amarelo aplicado no DiffViewer para elementos `moved`
- [ ] Resumo no painel mostra contagem por tipo (identical, moved, added, removed)

### 35.4 — Painel de inferências no DiffViewer
**Gap:** C14
**Escopo:** Frontend (`DiffViewer.vue`)
**AC:**
- [ ] Seção "Resultado" abaixo dos painéis lado-a-lado
- [ ] Lista `diffStore.inferences` com descrição, tipo e confiança
- [ ] Botão Confirmar → `diffStore.confirmInference(id)` → aplica no templateStore
- [ ] Botão Rejeitar → `diffStore.rejectInference(id)` → remove da lista
- [ ] Contagem de inferências pendentes visível no header

### 35.5 — Highlights do Diff usam coordenadas PDF
**Gap:** I24
**Escopo:** Frontend (`diffStore.ts`, `DiffViewer.vue`)
**AC:**
- [ ] `DiffHighlight` no painel PDF usa `bbox_pdf` (coordenadas do PDF original)
- [ ] `DiffHighlight` no painel Canvas usa `bbox_canvas` (coordenadas do template)
- [ ] Highlights se sobrepõem corretamente aos elementos nos respectivos painéis

### 35.6 — Matriz Variação Campos × PDFs
**Gap:** C12
**Escopo:** Backend (`stage5_template_generation.py`) + Frontend (`MultiDocAnalyzer.vue`)
**QA Note:** `VariationMatrix` type precisa de `fieldIds` (ou repurpose `layoutIds`). Backend `block_classifications` deve ser source das rows.
**AC:**
- [ ] `VariationMatrix` type estendido com `fieldIds: string[]` (ou repurpose `layoutIds`)
- [ ] `_step_5_5_variation_matrix` usa `block_classifications` como source das rows — emite linhas por campo (não por Layout Type)
- [ ] Colunas = PDFs, linhas = campos com ✔/✖ por célula
- [ ] Frontend renderiza campo como label de linha (não layoutId)
- [ ] Campos com padrão misto (✔ em alguns) classificados como opcionais

### ~~35.7~~ — REMOVIDA (já implementada)
> `EditorLayout.vue:41` já tem `v-if="multiDocStore.hasMultiplePdfs"`.

### 35.8 — Agrupamento de campos adjacentes em seção opcional
**Gap:** I22
**Escopo:** Backend + Frontend
**AC:**
- [ ] `_step_5_5_variation_matrix` agrupa blocos com mesmo `present_in_pdfs` quando adjacentes
- [ ] Detection tipo `optional_section` com lista de blocos agrupados
- [ ] Frontend exibe como uma única inferência "Seção opcional: [campo1, campo2, ...]"
- [ ] Confirmar → aplica `<!-- ko if -->` wrapper na seção inteira

### 35.9 — Detecção de `dynamic_table`
**Gap:** I23
**Escopo:** Backend + Frontend
**AC:**
- [ ] Pipeline detecta tabelas cujo número de linhas varia entre PDFs
- [ ] Detection tipo `dynamic_table` com range (min, max) de linhas
- [ ] Frontend exibe inferência "Tabela dinâmica: N-M linhas"
- [ ] Confirmar → configura `foreach` e paginação na tabela
