# Auditoria: Tabelas + Loops/Foreach

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**FR11** (`docs/prd-v3.md`, linha 186): Classificação automática de elementos como fixos ou dinâmicos usando padrões visuais repetidos e campos declarados como array no XSD. Elementos dinâmicos recebem `<!-- ko foreach -->`, paginação (FR12), replicação header/footer (FR13), reposicionamento (FR15).

**FR12** (seção Loops e Tabelas): Tabelas quebram por linhas com `<thead>` replicado. Operador configura parâmetros via Inspetor de Componente nível 3 — Tabela.

**`flow_layout_editor_spec.md`**: Modelo de Flow Layout com HEADER / CONTENT FLOW / FOOTER; tabelas com `foreach` automático no CONTENT FLOW; Inspector mostra "Data Source: movimentos" e "Pagination: enabled".

**`docs/prd-v3.md` linha 418 (restrições MVP)**: Loops aninhados e tabelas com `colspan`/`rowspan` não suportados — requerem ajuste manual.

**`docs/prd-v3.md` linha 411 (bibliotecas)**: `knockout-3.4.2.js` e `knockout.mapping.js` em `../Bibliotecas/js/`.

---

## Frontend — Status de Implementação

**Componentes existentes:**

- `/home/user/migrador-planet/frontend/src/stores/foreachGeneration.ts` (Story 9.5): `classifyNode()` classifica nó como `dynamic` (array) ou `fixed` por: (1) propriedade `isArray=true`; (2) padrão de nome do binding (`Items$`, `List$`, `Array$`, `Rows?$`, `Entries$`, `Records?$`, `Lines?$`); (3) tabela com múltiplos filhos do tipo section/container/field. `generateForeachBlock()` gera `<!-- ko foreach: field -->...<!-- /ko -->`. `generateTableForeach()` gera `<table><thead>...<tbody><!-- ko foreach -->`. `detectArrayFields()` varre árvore e retorna todos os nós dinâmicos.
- `/home/user/migrador-planet/frontend/src/organisms/inspectors/TableInspector.vue` (Stories 9.5, 14.4, 14.12): seção Geral (Nome, Fonte de Dados/binding), seção Colunas (campo, largura, alinhamento, drag&drop para reordenar, adicionar/remover), seção Paginação (checkbox "Quebrar entre páginas", checkbox "Repetir cabeçalho", input "Mínimo de linhas por página"), seção Linhas (altura, padding, border collapse), seção Posição (Âncora — read-only, Manter Junto — read-only), seção Visibilidade (VisibilityControl + camada + bloqueio). `TableCellEditor` integrado para editar células individuais.
- `/home/user/migrador-planet/frontend/src/composables/table-pagination.ts` (Story 9.5): `splitTableRows()`, `buildTablePages()` com `repeatHeader` e `minRowsPerPage`.

**O que funciona:**
- Detecção automática de nós dinâmicos via `classifyNode()` e `detectArrayFields()`.
- Geração de `<!-- ko foreach: campo -->...<!-- /ko -->` via `generateForeachBlock()`.
- Geração de `<table>` real com `<thead>` estático e `<tbody><!-- ko foreach -->` via `generateTableForeach()` — tabelas usam `<table>` real, não divs.
- TableInspector: binding/fonte de dados, colunas editáveis (campo, largura, alinhamento), paginação configurável (page_break, repeat_header, min_rows).
- TableCellEditor: edita propriedades individuais de células (Story 14.4).
- Drag & drop de colunas no inspector (Story 14.12).
- Table pagination via `table-pagination.ts` com chunks por altura e repetição de header.

**O que falta:**
- "Manter Junto" e "Âncora" no TableInspector são `InspectorField` (read-only) — não há controle editável para `keep_together`. O operador não consegue ativar via UI.
- Header row configurável (primeira linha = header estático): a spec menciona configurar qual linha é header; o TableInspector mostra "Repetir cabeçalho" (boolean) mas não há seleção de qual linha da tabela é o `<thead>`.
- Nested tables: explicitamente fora do escopo MVP (`docs/prd-v3.md` linha 418), porém não há mensagem de aviso/bloqueio no Inspector para tabelas aninhadas detectadas.
- Colspan/rowspan: fora do MVP, sem aviso no Inspector.
- Table continuation multi-página (TableIntelligenceModule do architecture-v5): não identificado — a lógica de `table-pagination.ts` existe no composable mas não há evidência de integração com o Canvas para visualizar continuação de tabela entre páginas.

---

## Backend — Status de Implementação

**Stage 3** (`stage3_structural_analysis.py`):
- Detecção de tabelas via `_assign_tables_to_sections()` (linha 1267): distribui tabelas detectadas no Stage 2 para as seções por sobreposição de posição Y.
- Estrutura da árvore: nós `"type": "header_row"` com células, nós de data row. Headers extraídos como `List[List[Dict]]` (linhas 1529–1537).
- Charts e barcodes detectados via Vision AI (GPT-4o) via `chat_with_vision()` (stage3, linhas 443–568), convertidos em nós `"type": "chart"` e `"type": "barcode"` com bbox, chart_type, barcode_format, confidence.
- Tabelas com múltiplas colunas detectadas corretamente pelo Stage 2 (alimentado via PyMuPDF).

**Stage 5** (`stage5_template_generation.py`):
- `_generate_table_html()` (linhas 527–605): gera `<table class="data-table">` real com `<thead>` (static header rows), `<tbody><!-- ko foreach: xsd_array_path -->`, células com `data-bind="text: fieldName"`. Usa `xsd_array_path` do nó como campo do foreach.
- Nomes de campos derivados de `xsd_field_path` via `mapping_by_block`.
- **Limitação identificada**: a função gera apenas 1 `<tr>` de dados no corpo (template do foreach); não há suporte a múltiplas colunas de dados com estrutura diferenciada por célula além do campo simples `data-bind="text: campo"`.

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | "Manter Junto" e "Âncora" no TableInspector são read-only — operador não pode ativar keep_together via UI | 🟡 Importante | Frontend | FR12, `05_keep_together_blocks.md` |
| 2 | Header row configurável (seleção de qual linha é `<thead>`) não implementado — apenas toggle "Repetir cabeçalho" | 🟡 Importante | Frontend | FR12, `flow_layout_editor_spec.md` |
| 3 | Integração table-pagination.ts com Canvas não verificada — continuação visual de tabela entre páginas não confirmada | 🟡 Importante | Frontend | FR12, `04_table_pagination.md` |
| 4 | `_generate_table_html()` gera apenas 1 `<tr>` template no foreach; colspan/rowspan não suportados | 🟢 Menor | Backend (stage5) | FR12, `docs/prd-v3.md` linha 418 |
| 5 | Nested tables: sem aviso visual no Inspector quando tabela aninhada detectada | 🟢 Menor | Frontend | `docs/prd-v3.md` linha 418 |
| 6 | classifyNode() usa apenas padrões de nome (`Items`, `List`, etc.) — tabelas com bindings de nomes atípicos não são detectadas como dinâmicas automaticamente | 🟢 Menor | Frontend | FR11 |

---

## Backlog Gerado

1. **Keep-together editável no TableInspector**: Trocar `InspectorField` por `InspectorCheckbox` para "Manter Junto"; integrar ao `calculatePageBreaks()` para honrar a flag.
2. **Seleção de header row**: Adicionar controle no TableInspector para marcar qual linha é o `<thead>` (ex: radio "primeira linha é cabeçalho estático"). Refletir na geração do HTML.
3. **Integração visual table-pagination no Canvas**: Confirmar que o Canvas renderiza continuação de tabela entre páginas com header repetido; criar story para validação visual.
4. **Aviso de nested table/colspan no Inspector**: Exibir banner de aviso quando tabela aninhada ou colspan/rowspan detectado no nó, orientando o operador ao ajuste manual.
5. **classifyNode() com fallback manual**: Adicionar campo "Forçar como array" no Inspector de nó para casos em que o nome do binding não segue os padrões automáticos.

---

## Status Geral

🟡 Parcial — A geração de `<table>` real com `<!-- ko foreach -->` está implementada tanto no frontend (foreachGeneration.ts) quanto no backend (stage5 `_generate_table_html`). O TableInspector cobre a maioria das configurações necessárias. Os gaps principais são: keep-together não editável via UI, ausência de seleção de header row, e a integração visual da table continuation no Canvas não confirmada.
