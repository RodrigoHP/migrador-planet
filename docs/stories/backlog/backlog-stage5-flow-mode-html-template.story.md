---
epic: TBD
story: TBD
title: "Stage 5 Flow Mode — geração de HTML knockout template (layout flow)"
status: Draft
executor: "@dev"
quality_gate: "@qa"
quality_gate_tools: [static_analysis, unit_test, manual_review]
depends_on: []
source_rca: "rca-2026-04-11-table-area-silently-ignored"
source_finding: "out_of_scope_gap"
priority: high
---

# Story TBD: Stage 5 Flow Mode — geração de HTML knockout template

## Status
Draft

## Story
**As a** desenvolvedor que usa o pipeline de migração,
**I want** que o Stage 5 produza HTML em modo "flow" (knockout.js + flexbox + HTML tables + JsBarcode),
**so that** o output final do pipeline corresponda ao formato esperado em `docs/exemplos` — com layout relativo, bindings de dados e barcode renderizado via JS, pronto para uso em produção como template do PlanetExpress.

## Contexto

Investigação `rca-2026-04-11-table-area-silently-ignored` (2026-04-11) identificou gap
arquitetural como **out of scope**:

> "Pipeline gera canvas HTML (position:absolute). User quer flow HTML (flexbox + knockout.js +
> JsBarcode) como em docs/exemplos. É gap arquitetural — Stage 5 nunca implementou modo flow.
> Requer nova story: 'Stage 5 Flow Mode — geração de HTML knockout template'."

**Situação atual:** Stage 5 gera exclusivamente HTML canvas com `position: absolute` e
coordenadas em pixels calculadas via `_bbox_to_absolute_style()`. Esse formato serve o
editor visual (drag & drop), mas **não é o formato de template de produção**.

**Formato esperado** (conforme `docs/exemplos/Pdf.Vg.Seguro.Fatura.Vg/Index.html`):
- Layout baseado em **flexbox** e fluxo normal do documento (sem `position: absolute`)
- **Knockout.js 3.4.2** para data bindings (`data-bind`, `ko.applyBindings`)
- **JsBarcode** para renderização de códigos de barras (não CSS/linhas)
- **`<table>`** HTML real para dados tabulares (com `data-bind="foreach: rows"`)
- **`docs/exemplos/Bibliotecas/css/sentico.css`** como folha de estilos base
- Unidades **rem** (não px absolutas)
- Fontes: `SenticoSansDT` (normal, italic, bold) via `@font-face`

**Canvas mode:** Mantido intacto — o editor visual continua usando o formato position:absolute.
O flow mode é um **segundo modo de output** controlado por flag/parâmetro.

**Bibliotecas disponíveis em `docs/exemplos/Bibliotecas/`:**
- `css/sentico.css`, `css/sentico-v2.css`
- `js/knockout-3.4.2.js`, `js/knockout.mapping.js`
- `js/Chart.min.js`, `js/chartjs-plugin-datalabels.min.js`

## Acceptance Criteria

1. **Flag de modo no Stage 5:**
   Stage 5 aceita parâmetro `output_mode: "canvas" | "flow"` (default: `"canvas"` para
   não quebrar comportamento existente). Quando `output_mode="flow"`, o pipeline produz
   HTML flow em vez de canvas HTML.

2. **Estrutura HTML flow gerada:**
   O HTML flow produzido DEVE conter:
   ```html
   <!DOCTYPE html>
   <html>
   <head>
     <meta charset="UTF-8">
     <link rel="stylesheet" href="../Bibliotecas/css/sentico.css">
     <script src="../Bibliotecas/js/knockout-3.4.2.js"></script>
     <script src="../Bibliotecas/js/knockout.mapping.js"></script>
     <script src="../Bibliotecas/js/JsBarcode.all.min.js"></script>
   </head>
   <body>
     <div id="documento" data-bind="with: documento">
       <!-- seções em ordem de fluxo -->
     </div>
     <script>
       var viewModel = ko.mapping.fromJS({ documento: { ... } });
       ko.applyBindings(viewModel);
       JsBarcode("#barcode", viewModel.documento.codBarras(), { ... });
     </script>
   </body>
   </html>
   ```

3. **Seções como blocos flow:**
   Cada seção do tree é renderizada como `<div class="secao">` com `display: flex`
   ou `display: block` conforme o tipo. Labels e values são `<span>` ou `<p>` em
   fluxo normal — sem `top/left` absolutos.

4. **Tabelas como `<table>` HTML:**
   Nodes do tipo `table` no document tree são renderizados como `<table>` com
   `<thead>/<tbody>/<tr>/<td>` reais, com `data-bind="foreach: rows"` no `<tbody>`.
   Não devem aparecer como `<div>` ou spans soltos.

5. **Código de barras via JsBarcode:**
   Nodes do tipo `barcode` são renderizados como:
   ```html
   <svg id="barcode-{id}" data-bind="attr: { 'data-value': codBarras }"></svg>
   ```
   Com inicialização via `JsBarcode("#barcode-{id}", valor, { format: "ITF", ... })`.
   Nenhum barcode deve ser renderizado como imagem ou como coleção de `<div>` finos.

6. **Data bindings knockout:**
   Campos mapeados (com `FieldMappingEntry` no `mapping_by_block`) são renderizados com
   `data-bind="text: {xsd_field_name}"`. Campos sem mapeamento usam o texto estático
   extraído do PDF.

7. **ViewModel gerado:**
   O `<script>` final inclui um `viewModel` com todos os campos mapeados populados com
   o valor extraído do PDF como valor padrão (pré-visualização). Ex:
   ```javascript
   var viewModel = ko.mapping.fromJS({
     documento: {
       cedente: "BRADESCO FINANCIAMENTOS S/A",
       dataVencimento: "15/04/2026",
       valorDocumento: "1.234,56",
       codBarras: "03399.12345 67890.123456 78901.234567 8 12340000123456"
     }
   });
   ```

8. **Canvas mode inalterado:**
   Quando `output_mode="canvas"` (default), o comportamento atual é **idêntico** ao de
   antes desta story. Nenhuma regressão nos testes existentes.

9. **Testes:**
   - `test_stage5_flow_mode.py` (novo arquivo):
     - `test_flow_mode_produces_table_element` — node `table` → `<table>` no HTML
     - `test_flow_mode_produces_jsbarcode_svg` — node `barcode` → `<svg>` com JsBarcode init
     - `test_flow_mode_produces_knockout_bindings` — campos mapeados → `data-bind="text:"`
     - `test_flow_mode_includes_sentico_css` — `<link>` para `sentico.css` presente
     - `test_flow_mode_includes_viewmodel_script` — `ko.applyBindings` presente no output
     - `test_canvas_mode_unaffected` — output canvas mode idêntico ao baseline

## Scope

**IN:**
- `backend/services/stages/stage5_template/html_tree.py` — novo walker `_tree_to_flow_html()`
- `backend/services/stages/stage5_template/html_helpers.py` — helpers flow (tabela, barcode, binding)
- `backend/services/stages/stage5_template/result_assembly.py` — rotear para canvas ou flow conforme flag
- `backend/services/stages/stage5_template/css_generation.py` — gerar CSS complementar flow (se necessário)
- `backend/tests/test_stage5_flow_mode.py` — suite de testes do novo modo (novo arquivo)

**OUT:**
- Não alterar Stage 1, 2, 3, 4 — o flow mode é exclusivamente Stage 5
- Não substituir canvas mode — ambos os modos coexistem
- Não integrar ao frontend nesta story — flag ativado via parâmetro de pipeline apenas
- Não gerar arquivos estáticos de biblioteca (JS/CSS) — referenciar `docs/exemplos/Bibliotecas/` existente
- Não implementar edição de template flow no editor visual — story futura

## Dev Notes

**Ponto de entrada no Stage 5:**
Procurar por onde `_tree_to_html()` é chamado em `result_assembly.py` ou no step 5.5/5.6.
Adicionar branch: se `output_mode == "flow"` → chamar `_tree_to_flow_html()`.

**Estrutura do walker flow:**
```python
def _tree_to_flow_html(
    node: dict[str, Any],
    mapping_by_block: dict[str, FieldMappingEntry],
    field_tree: dict[str, Any] | None,
    layout: LayoutTypeInfo,
    indent: int = 0,
) -> str:
    node_type = node.get("type", "")
    children = node.get("children", [])

    if node_type == "table":
        return _render_flow_table(node)
    elif node_type == "barcode":
        return _render_flow_barcode(node)
    elif node_type in ("field", "label", "value"):
        return _render_flow_field(node, mapping_by_block)
    # ... etc
```

**Referência de formato:** `docs/exemplos/Pdf.Vg.Seguro.Fatura.Vg/Index.html` é o
template de referência primário. Seguir estrutura de seções, classes CSS e padrão
de bindings knockout desse arquivo.

**Deduplicação de IDs de barcode:**
Gerar `id="barcode-{uuid4().hex[:8]}"` para evitar colisão quando múltiplos barcodes
aparecerem na mesma página.

**Campos sem mapeamento:**
Quando `mapping_by_block` não contém a chave do bloco, usar `<span>{texto_estatico}</span>`
sem data-bind — o valor fica hard-coded no HTML (pré-visualização).

## Tasks / Subtasks

- [ ] **Análise do tree builder output**
  - [ ] Mapear todos os `node_type` possíveis emitidos por `_build_tree()` (Stage 3.4)
  - [ ] Documentar quais mapeiam para table, barcode, field, section no modo flow

- [ ] **Walker flow em `html_tree.py`**
  - [ ] Implementar `_tree_to_flow_html()` com handlers por node_type
  - [ ] `_render_flow_table()` → `<table><thead><tbody data-bind="foreach:...">` 
  - [ ] `_render_flow_barcode()` → `<svg id="barcode-X">` + init JsBarcode no script
  - [ ] `_render_flow_field()` → `<span data-bind="text: fieldName">` ou texto estático
  - [ ] `_render_flow_section()` → `<div class="secao">` com flexbox

- [ ] **Geração do ViewModel knockout**
  - [ ] Coletar todos os campos mapeados durante o walk
  - [ ] Serializar como `ko.mapping.fromJS({documento: {...}})` no `<script>` final
  - [ ] Inicializar JsBarcode para cada barcode detectado

- [ ] **Integração em `result_assembly.py`**
  - [ ] Ler `output_mode` do context (default `"canvas"`)
  - [ ] Branch: canvas → `_tree_to_html()` (existente), flow → `_tree_to_flow_html()`
  - [ ] Incluir `<link>` sentico.css e `<script>` knockout/JsBarcode no `<head>` flow

- [ ] **Testes em `test_stage5_flow_mode.py`**
  - [ ] `test_flow_mode_produces_table_element`
  - [ ] `test_flow_mode_produces_jsbarcode_svg`
  - [ ] `test_flow_mode_produces_knockout_bindings`
  - [ ] `test_flow_mode_includes_sentico_css`
  - [ ] `test_flow_mode_includes_viewmodel_script`
  - [ ] `test_canvas_mode_unaffected`

## Testing

```bash
# Testes do novo modo flow
cd backend && python -m pytest tests/test_stage5_flow_mode.py -v

# Garantir que canvas mode não regrediu
cd backend && python -m pytest tests/test_stage5_template_generation.py -v

# Suite completa Stage 5
cd backend && python -m pytest tests/test_stage5_*.py -v
```

**Teste manual (integração):**
1. Rodar pipeline com um PDF de boleto Bradesco + `output_mode="flow"`
2. Abrir o HTML gerado no browser
3. Verificar: tabelas renderizadas como `<table>`, barcode visível via JsBarcode,
   campos com valores do PDF, layout flow sem sobreposições

## Dev Agent Record
### File List
- `backend/services/stages/stage5_template/html_tree.py`
- `backend/services/stages/stage5_template/html_helpers.py`
- `backend/services/stages/stage5_template/result_assembly.py`
- `backend/services/stages/stage5_template/css_generation.py`
- `backend/tests/test_stage5_flow_mode.py`

### Change Log
| Data | Agente | Ação |
|---|---|---|
| 2026-04-11 | @qa (Quinn) | Story criada a partir de gap arquitetural identificado em rca-2026-04-11-table-area-silently-ignored (out_of_scope) |

## QA Results
<!-- @qa preenche durante review -->
