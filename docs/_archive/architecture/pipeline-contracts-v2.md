# Pipeline Contracts v2.0 — Contratos de Dados Entre Estágios

**Versão:** 2.0
**Data:** 2026-03-20
**Autor:** @architect (Aria)
**Complementa:** `pipeline-architecture-v2.md`

---

## Propósito

Este documento define os **contratos formais de dados** entre cada estágio do pipeline. Cada contrato especifica:
- O **tipo exato** dos dados escritos no context
- As **garantias** que o estágio produtor oferece
- As **expectativas** que o estágio consumidor pode assumir

---

## 1. Context Keys — Inventário Completo

### Keys primárias (interface estável — frontend pode ler)

| Key | Tipo | Produtor | Consumidores |
|-----|------|----------|-------------|
| `job_id` | `str` (UUID v4) | Upload Router | Todos |
| `tmp_base` | `str` (path) | Upload Router | 2, 5, 2b |
| `field_tree` | `FieldTreeDict \| None` | Stage 1b | 23, 26, 27 |
| `parsed_documents` | `List[ParsedDocumentDict]` | Stage 2 (atualizado por 3,4,5,6,2b) | 7, 8, 9.5 |
| `representative_documents` | `List[ParsedDocumentDict]` | Stage 9.5 | 17, 18, 19, 19b, 19c, 20, 21, 22, 23 |
| `all_parsed_documents` | `List[ParsedDocumentDict]` | Stage 9.5 | Backup (não usado em runtime normal) |
| `layout_types` | `List[LayoutTypeDict]` | Stage 9 (atualizado por 10, 11, 16) | 9.5, 12-16, 20, 27, 28 |
| `tables` | `List[DetectedTableDict]` | Stage 17 (atualizado por 18) | 19, 19c, 22, 26, 27 |
| `intelligence` | `Dict[cluster_id, IntelligenceDict]` | Stage 16 | 25, 28 |
| `visual_analysis` | `Dict[page_key, VisualPageAnalysis]` | Stage 20 (atualizado por 21, 22) | 19b, 25, 27, 28 |
| `document_type` | `str` | Stage 19b | 28 |
| `document_type_confidence` | `float` | Stage 19b | 28 |
| `document_trees` | `Dict[layout_type_id, TreeNode]` | Stage 19c | 27, 28 |
| `field_mappings` | `List[FieldMappingDict]` | Stage 23 (atualizado por 24) | 25, 26, 27, 28 |
| `ambiguous_fields` | `List[str]` | Stage 23 | 28 |
| `format_functions` | `Dict[name, js_string]` | Stage 24 | 28 |
| `confidence_scores` | `Dict` | Stage 25 | 28 |
| `validation_result` | `Dict` | Stage 26 | 28 |
| `template_draft` | `Dict[layout_type_id, {html, css}]` | Stage 27 | 28 |
| `coverage` | `Dict[layout_type_id, CoverageData]` | Stage 27 | 28 |
| `result_json` | `PipelineResult` | Stage 28 | analyze.py (retorna ao frontend) |

### Keys internas (prefixo _ — uso entre estágios Python, não serializar)

| Key | Tipo | Produtor | Consumidores |
|-----|------|----------|-------------|
| `_skeleton_objects` | `List[LayoutSkeleton]` | Stage 7 | 8, 9, 12-15 |
| `_layout_type_objects` | `List[LayoutType]` | Stage 9 | 10, 11, 12-16 |
| `_element_labels` | `Dict` | Stage 13 | 14, 16 |
| `_stability_map` | `Dict` | Stage 14 | 15, 16 |
| `_variants` | `Dict` | Stage 15 | 16, 27 |
| `_conditional_sections` | `Dict` | Stage 15 | 16 |
| `_aligned` | `bool` | Stage 12 | — |
| `_vision_api_calls` | `int` | Stages 20-22 | — |

---

## 2. Type Definitions — Contratos Tipados

### ParsedDocumentDict

```python
{
    "job_id": str,              # UUID v4
    "pdf_index": int,           # 0-based index do PDF no job
    "pdf_name": str,            # nome do arquivo original
    "pages": [ParsedPageDict]
}
```

### ParsedPageDict

```python
{
    "page_number": int,         # 0-based
    "width": float,             # pontos PDF (595.0 para A4)
    "height": float,            # pontos PDF (842.0 para A4)
    "text_blocks": [TextBlockDict],
    "images": [ParsedImageDict],        # Stage 5
    "fonts": [CSSFontDict],             # Stage 4
    "grid_info": GridInfoDict | None,   # Stage 6
    "screenshot_path": str | None       # Stage 2b
}
```

### TextBlockDict

```python
{
    "id": str,                  # UUID único por bloco
    "text": str,                # texto extraído
    "bbox": [float, float, float, float],  # [x0, y0, x1, y1] em pontos PDF
    "font_name": str,           # nome da fonte original
    "font_size": float,         # tamanho em pontos
    "page_number": int,         # 0-based
    "pdf_index": int,           # 0-based
    "semantic_label": str | None  # Stage 19: "label"|"value"|"title"|"header"|"footer_text"|"page_number"|"table_header"|"table_cell"|"field"
}
```

### FieldTreeDict

```python
{
    "root_nodes": [FieldNodeDict],
    "flat_paths": [str]          # ex: ["cliente.nome", "cliente.cpf", "itens[].descricao"]
}
```

### FieldNodeDict

```python
{
    "name": str,
    "path": str,                # dot-notation path completo
    "type": str,                # "string"|"decimal"|"date"|"integer"|...
    "is_array": bool,           # maxOccurs > 1
    "required": bool,           # minOccurs > 0
    "children": [FieldNodeDict]
}
```

### LayoutTypeDict

```python
{
    "id": str,                           # "layout-0", "layout-1", ...
    "cluster_id": int,                   # cluster label do KMeans
    "name": str,                         # heurístico: "Transações", "Extrato", etc.
    "representative_page": {
        "pdf_index": int,
        "page_number": int
    },
    "secondary_pages": [{"pdf_index": int, "page_number": int}],
    "page_count": int,                   # número total de páginas no cluster
    "pages": [{"pdf_index": int, "page_number": int}],
    "fingerprint": LayoutFingerprintDict,
    "fingerprint_hash": str,             # SHA-256
    "is_reusable": bool,                 # Stage 11 — encontrado no registry
    "template_id": str | None            # Stage 11 — ID do template reutilizável
}
```

### DetectedTableDict

```python
{
    "table_id": str,             # identificador único
    "page_number": int,
    "pdf_index": int,
    "bbox": [float, float, float, float],  # [x0, y0, x1, y1]
    "headers": [str],            # textos do header
    "rows": [[str]],             # conteúdo das linhas
    "columns": int,              # número de colunas
    "is_multi_page": bool        # tabela continua na próxima página
}
```

### FieldMappingDict (v2 — com layout_type_id)

```python
{
    # --- Identificação ---
    "block_id": str | None,      # ID do TextBlock de origem
    "layout_type_id": str,       # ★ NOVO: "layout-0", "layout-1", ...

    # --- Conteúdo extraído ---
    "pdf_text": str,             # texto do valor no PDF
    "label_text": str,           # texto do label adjacente
    "bbox": [float, float, float, float] | None,  # bbox do valor

    # --- Matching ---
    "xsd_field_path": str,       # caminho XSD mapeado (vazio se não mapeado)
    "confidence": float,         # 0.0-1.0
    "is_ambiguous": bool,
    "candidates": [{"path": str, "score": float}],

    # --- Metadata ---
    "page_number": int,
    "pdf_index": int,
    "is_table_cell": bool,       # Stage 19 classificou como table_cell
    "from_table": bool,          # pertence a tabela detectada

    # --- Frontend-compatible aliases ---
    "name": str,                 # = label_text || pdf_text
    "path": str,                 # = xsd_field_path
    "type": str,                 # "text" (default)
    "status": str,               # "mapped"|"unmapped"|"ambiguous"|"optional"
    "isOptional": bool,

    # --- Stage 24 enrichment ---
    "detected_format": str | None,  # "currency_brl"|"date_numeric"|"cpf"|...
    "font_name": str | None,
    "font_size": float | None
}
```

### TreeNode (v2 — hierárquico)

```python
{
    "id": str,                   # único dentro da árvore
    "type": str,                 # "document"|"page"|"header"|"flow"|"footer"|"section"|"table"|"field"|"text"|"image"|"barcode"|"chart"|"container"
    "name": str,                 # display name
    "binding": str | None,       # XSD path (se mapeado)
    "isOptional": bool,
    "children": [TreeNode],
    "properties": {
        # --- Comuns ---
        "semantic_label": str | None,
        "text": str | None,
        "x": float | None,      # CSS pixels (não PDF points)
        "y": float | None,
        "width": float | None,
        "height": float | None,

        # --- Font (quando aplicável) ---
        "font_family": str | None,
        "font_size": float | None,

        # --- Page-level ---
        "page_number": int | None,
        "pdf_name": str | None,

        # --- Table-level ---
        "headers": [str] | None,
        "column_count": int | None,
        "row_count": int | None,

        # --- Image-level ---
        "image_path": str | None,
        "image_width": int | None,
        "image_height": int | None
    },
    "visibility": bool
}
```

### CoverageData (v2 — multidimensional)

```python
{
    "fields": {
        "mapped": int,
        "total": int
    },
    "tables": {
        "mapped": int,          # tabelas com ≥1 célula mapeada
        "total": int            # tabelas detectadas
    },
    "images": {
        "mapped": int,          # imagens com binding
        "total": int            # imagens extraídas
    },
    "charts": {
        "mapped": int,          # futuro
        "total": int            # futuro
    },
    "percentage": int           # weighted: fields*0.6 + tables*0.25 + images*0.15
}
```

### ConfidenceFactors

```python
{
    "layout_stability": float,   # 0.0-1.0 — elementos estáveis vs. variáveis
    "anchor_detection": float,   # 0.0-1.0 — % de fields com label adjacente
    "grid_quality": float,       # 0.0-1.0 — qualidade da grade detectada
    "field_variability": float,  # 0.0-1.0 — consistência dos campos dinâmicos
    "vision_agreement": float,   # 0.0-1.0 — concordância com Visual AI
    "overall": int               # 0-100 — weighted average
}
```

### PipelineResult (v2 — contrato final)

```python
{
    "document_structure": {
        "pages": [SimplifiedPageDict],          # resumo por página
        "layout_types": [LayoutTypeDict],
        "root": TreeNode,                       # árvore do primeiro layout (backward compat)
        "trees_by_layout": {                    # ★ NOVO
            "layout-0": TreeNode,
            "layout-1": TreeNode
        }
    },
    "field_mappings": [FieldMappingDict],        # agora com layout_type_id
    "confidence_scores": {                       # indexado por layout_type_id
        "layout-0": ConfidenceFactors,
        "layout-1": ConfidenceFactors
    },
    "coverage": {                                # indexado por layout_type_id
        "layout-0": CoverageData,
        "layout-1": CoverageData
    },
    "layout_types": [LayoutTypeDict],
    "template_draft": {                          # ★ MUDOU: por layout
        "layout-0": {"html": str, "css": str},
        "layout-1": {"html": str, "css": str}
    },
    "ambiguous_fields": [AmbiguousFieldDict],
    "format_functions": {name: js_function_string},
    "overlay_items": {                           # indexado por layout_type_id
        "layout-0": [BackendOverlayItemDict],
        "layout-1": [BackendOverlayItemDict]
    },
    "document_type": str,                        # ★ MUDOU: do Stage 19b
    "document_type_confidence": float,           # ★ NOVO

    # --- NOVOS (opcionais, frontend usa quando disponível) ---
    "visual_analysis": {                         # ★ NOVO
        "0:0": VisualPageAnalysis,
        "0:3": VisualPageAnalysis
    } | None,
    "intelligence": {                            # ★ NOVO
        "0": IntelligenceDict,
        "1": IntelligenceDict
    } | None
}
```

---

## 3. Regras de Compatibilidade

### Breaking Changes (frontend PRECISA adaptar)

| Campo | Antes | Depois | Migração |
|-------|-------|--------|----------|
| `template_draft` | `{html, css}` | `Record<layoutId, {html, css}>` | Frontend checa se é Dict ou Record; se Dict com keys `html`/`css`, usa como está; se Record com layout IDs, usa o active layout |

### Non-Breaking Additions (frontend pode ignorar)

| Campo | Tipo | Default se ausente |
|-------|------|--------------------|
| `document_structure.trees_by_layout` | Record | Não existe → usa `root` |
| `document_type_confidence` | float | `1.0` (assume confiança total) |
| `visual_analysis` | Record | `null` → sem dados visuais |
| `intelligence` | Record | `null` → sem dados de inteligência |
| `coverage.*.tables` | `{mapped, total}` | `{mapped: 0, total: 0}` |
| `coverage.*.images` | `{mapped, total}` | `{mapped: 0, total: 0}` |
| `field_mappings[].layout_type_id` | string | `"global"` → sem filtro |

---

## 4. Validação de Contratos

Cada estágio DEVE validar suas entradas antes de processar:

```python
# Padrão para cada stage executor
async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    # 1. Ler inputs com defaults seguros
    docs = context.get("representative_documents") or context.get("parsed_documents") or []

    # 2. Early return se input essencial ausente
    if not docs:
        context["<output_key>"] = <empty_default>
        return {"status": "skipped", "reason": "no input documents"}

    # 3. Processar
    ...

    # 4. Escrever output com tipo garantido
    context["<output_key>"] = result  # NUNCA None para keys primárias

    # 5. Retornar summary para SSE
    return {"status": "completed", "summary": {...}}
```

---

## 5. Diagrama de Migração — v1 → v2.1

```
FASE 1: Light Scan First (P0)
  ├── Stage 9.5  (Representative Filter)    — ~50 linhas Python (NOVO)
  ├── Pipeline orchestrator (analyze.py)    — reordenar execução dos blocos:
  │     Bloco 2a (Stages 2, 6)  → Bloco 3 (7-9) → Filter 9.5 → Bloco 2b (3,4,5,2b)
  ├── register_all.py                       — nova função register_bloco2b()
  └── Stages 3,4,5,2b                       — trocar parsed_documents → representative_documents (1 linha cada)

FASE 2: Downstream Filter (P0)
  ├── Stage 17   (Table Detection)          — trocar parsed_documents → representative_documents (1 linha)
  ├── Stage 18   (Table Structuring)        — trocar para representative_documents (1 linha)
  ├── Stage 19   (Semantic Analysis)        — trocar para representative_documents (1 linha)
  └── Stage 23   (Field Matching)           — trocar + add layout_type_id (2 linhas)

FASE 3: Novos estágios (P1-P2)
  ├── Stage 19b  (Document Type Detection)  — ~100 linhas Python (NOVO)
  └── Stage 19c  (Hierarchy Builder)        — ~150 linhas Python (NOVO)

FASE 4: Reescrita de output (P1)
  ├── Stage 27   (Template Draft)           — ~200 linhas (nova lógica de geração)
  └── Stage 28   (Pipeline Result)          — ~100 linhas (novo formato de saída)

FASE 5: Frontend (paralelo)
  ├── pipeline.types.ts                     — novas interfaces
  ├── session.ts / templateStore.ts         — consumir trees_by_layout
  └── coverageStore.ts                      — consumir coverage multidimensional
```

---

— Aria, arquitetando o futuro 🏗️
