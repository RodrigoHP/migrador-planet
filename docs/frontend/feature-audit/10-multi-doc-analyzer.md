# Auditoria: Analisador Multi-Documento

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

### FR40 — Analisador Multi-Documento (`docs/prd-v3.md` linha 132)
- Exibido quando múltiplos PDFs enviados (oculto com 1 PDF)
- Lista de PDFs (base/variação)
- Matriz de Variação: campo × documento → ✔/✖
- Detecção automática:
  - ✔ em todos → campo obrigatório
  - ✔ em alguns → campo opcional (gera `<!-- ko if: campo -->`)
  - Campos adjacentes com mesmo padrão de presença → seção opcional (agrupados automaticamente com `<!-- ko if -->`)
  - ✔ em apenas 1 → seção condicional
  - Linhas variáveis em tabelas → layout dinâmico (foreach com contagem variável)
- Campos detectados como opcionais pela Matriz de Variação pré-preenchidos como Condicional no Inspetor

### UX Spec — Seção 6 (`docs/ideias/ux/template_editor_main_screen_spec.md` linha 259)
- Lista de documentos com status (base/variação)
- Matriz de Variação com colunas Doc1..DocN e linhas com campo + ✔/✖ por coluna
- Detecções automáticas: campos opcionais, seções condicionais, variações de layout
- Binding condicional `<!-- ko if: campo -->` gerado automaticamente

### Wireframe (`docs/wireframes/wireframes-mid-fi.md` linha 1279)
- Seção colapsável "Analisador Multi-Documento"
- Contador de PDFs no título
- Matriz de Variação com header Campo + D1..DN e linhas com ✔/✖
- Seção "Inferências Automáticas" com cards confirmáveis/rejeitáveis
- Detecção de seção opcional quando campos adjacentes têm mesmo padrão (ex: telefone + email ambos ✖✔✖✔ → agrupados em seção "contato")

---

## Frontend — Status de Implementação

### MultiDocAnalyzer.vue (`frontend/src/organisms/MultiDocAnalyzer.vue`)
**Implementado:**
- Componente colapsável com toggle (→/↓) e contador de PDFs no título
- Seção "Documentos" com lista de PDFs mostrando role (base/variação) e nome
- Seção "Matriz de Variação" com grid dinâmico (colunas = 1 + N PDFs) usando `VariationRow`
- Seção "Inferências Automáticas" com lista de `DetectionCard` com handlers `confirm`/`reject`
- Oculta a matriz quando `matrixRows.length === 0`
- Mensagem "Nenhuma inferência disponível" quando detections vazia

**Gap — Variation Matrix:**
- Os rows da matriz usam `matrix.layoutIds` como identificadores de campo — são IDs de Layout Type, não nomes de campos do XSD. A matriz exibida mostra Layout Types × PDFs, não campos × PDFs como planejado. Isso é uma interpretação divergente do spec que prevê "campo × documento".

**Gap — Componente não oculto com 1 PDF:**
- O componente é renderizado mesmo com 1 PDF; `multiDocStore.hasMultiplePdfs` existe na store mas não é usado como guard no componente ou no layout pai para ocultar o analisador.

### multiDocStore.ts (`frontend/src/stores/multiDocStore.ts`)
**Implementado:**
- `pdfList: PdfDocument[]` — lista de PDFs com `role: 'base' | 'variation'`
- `variationMatrix: VariationMatrix | null` — estrutura `{layoutIds, variationIds, cells}`
- `detections: Detection[]` — tipos: `required`, `optional_field`, `conditional_section`, `dynamic_table`
- `confirmedDetections: Set<string>`
- `hasMultiplePdfs` computed (booleano)
- `populateFromPipeline(pipelineResult)` — preenche pdfList, matrix e detections de uma vez
- `confirmDetection(id)` — atualiza `templateStore` (visibility, koIf, foreach) baseado no tipo
- `rejectDetection(id)` — remove detection
- `analyzeVariations()` — gera detections localmente a partir da `variationMatrix` sem chamar backend
- `addDetection` / `removeDetectionByLabel` — bidirectional sync com Inspetor (Story 14.13)

**Gap — Detecção de seção opcional por adjacência:**
- `analyzeVariations()` classifica campos individualmente como `optional_field` ou `conditional_section`; não há lógica para detectar e agrupar campos **adjacentes com mesmo padrão de presença** em uma seção opcional. A detecção de "seção contato = telefone + email (mesmo padrão ✖✔✖✔)" não está implementada.

**Gap — Detecção de `dynamic_table`:**
- `analyzeVariations()` não gera detections do tipo `dynamic_table` — apenas `required`, `optional_field` e `conditional_section`. Tabelas com linhas variáveis não são inferidas.

---

## Backend — Status de Implementação

### `_step_5_5_variation_matrix` (`backend/services/stages/stage5_template_generation.py`, linhas 1067–1160)
**Implementado:**
- Constrói `pdfList` a partir dos clusters (PDF base = o com maior cobertura de clusters)
- Constrói `cells: layoutId × pdfId → bool` — presença do layout em cada PDF
- Gera `detections` a partir de `block_classifications` (presente em `intelligence[layout_id]`)
- Cada detection tem: `id`, `pdfId`, `type` (`optional_field` ou `conditional_section`), `description`, `confidence`, `nodeBinding`
- Retorna `{pdfs, matrix, detections}`

**Gap — Estrutura da matriz:**
- A matriz gerada usa `layoutIds` (IDs de Layout Type) como linhas, não campos do XSD. O spec (FR40 e wireframe) prevê linhas = campos detectados × colunas = PDFs. A matriz atual é Layout Types × PDFs, o que representa presença de layouts nos documentos, não presença de campos.

**Gap — `block_classifications` alimenta detections:**
- `block_classifications` vem de `intelligence[layout_id].get("block_classifications", {})` (Stage 3). Se `intelligence` estiver vazio ou não tiver `block_classifications` para um layout, `detections` será vazio. Não há fallback.

**Gap — Adjacência e seções opcionais agrupadas:**
- `_step_5_5_variation_matrix` não implementa agrupamento de campos adjacentes com mesmo padrão. Cada bloco é classificado individualmente.

**Gap — `dynamic_table` ausente:**
- Não há geração de detections do tipo `dynamic_table` (tabelas com contagem variável de linhas) — apenas `optional_field` e `conditional_section`.

### Stage 3 — `block_classifications` (`backend/services/stages/stage3_structural_analysis.py`)
**Implementado:**
- `block_classifications` gerado com campos `variant` (`required` / `optional` / `conditional`) e `present_in_pdfs`
- Alimenta `_step_5_5_variation_matrix` via `intelligence`

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Matriz de Variação exibe Layout Types × PDFs, não Campos × PDFs como especificado | 🔴 Crítico | Frontend + Backend | `MultiDocAnalyzer.vue:120-124` / FR40 / wireframe linha 1281 |
| 2 | Componente não é ocultado quando apenas 1 PDF está presente | 🟡 Importante | Frontend | `MultiDocAnalyzer.vue` / FR40 — "Seção oculta quando apenas 1 PDF" |
| 3 | Agrupamento de campos adjacentes com mesmo padrão em seção opcional não implementado | 🟡 Importante | Frontend + Backend | `multiDocStore.analyzeVariations()` / FR40 linha 135 |
| 4 | Detecção de `dynamic_table` (tabelas com linhas variáveis) ausente | 🟡 Importante | Frontend + Backend | `multiDocStore.analyzeVariations()` / FR40 linha 137 |
| 5 | `block_classifications` pode estar vazio — sem fallback para detections | 🟡 Importante | Backend | `_step_5_5_variation_matrix:1141-1142` |
| 6 | Nenhuma indicação visual de status por documento (ex: ✓ validado, ✕ erro) além do ✔ genérico | 🟢 Menor | Frontend | `MultiDocAnalyzer.vue:39` / wireframe linha 1280 |

---

## Backlog Gerado

1. **[Backend + Frontend] Corrigir estrutura da Matriz de Variação para Campos × PDFs** — `_step_5_5_variation_matrix` deve emitir linhas por campo detectado (não por Layout Type); `MultiDocAnalyzer.vue` deve renderizar campo como label de linha.
2. **[Frontend] Ocultar analisador com 1 PDF** — usar `multiDocStore.hasMultiplePdfs` como `v-if` no componente pai ou no próprio `MultiDocAnalyzer`.
3. **[Backend + Frontend] Implementar detecção de seção opcional por adjacência** — agrupar blocos com mesmo padrão de presença `present_in_pdfs` quando são adjacentes no layout; emitir detection `optional_section` com lista de blocos agrupados.
4. **[Backend + Frontend] Implementar detecção de `dynamic_table`** — detectar tabelas cujo número de linhas varia entre PDFs; emitir detection `dynamic_table` com range `(min, max)` de linhas.
5. **[Backend] Adicionar fallback robusto quando `block_classifications` está vazio** — logar aviso e retornar detections vazias de forma explícita, não silenciosa.

---

## Status Geral

🟡 Parcial — A infraestrutura do analisador existe (componente, store, backend), mas a Matriz de Variação exibe Layout Types × PDFs em vez de Campos × PDFs como previsto no spec. A detecção de seções opcionais por adjacência e de `dynamic_table` não foi implementada. O componente também não é ocultado corretamente com 1 PDF.
