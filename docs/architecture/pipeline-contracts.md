# Pipeline Contracts — Contratos de Dados Entre Stages

**Versão:** 3.0
**Data:** 2026-04-13
**Status:** `current` — derivado de `backend/models/pipeline_context.py`
**Dono:** `@architect` — regenerar manualmente ao alterar o modelo
**Fonte:** `backend/models/pipeline_context.py` — PipelineContext TypedDict + Stage*Output models (fonte de verdade)
**Atualizar quando:** qualquer alteração em `backend/models/pipeline_context.py` ou adição de context key em um stage
**Última validação:** 2026-04-13 (Epic 46 — Vision Optimization concluído)

> Este doc é derivado do código, não o contrário. Em caso de conflito, o código prevalece.

---

## Visão Geral do Fluxo

```
[Input] pdf_documents + xsd_path + job_id
    │
    ▼
Stage 1 → clusters, _raw_text_blocks
    │
    ▼
Stage 2 → enriched_documents, extraction_warnings
    │
    ▼
Stage 3 → document_trees, intelligence, visual_analysis, label_value_pairs, layout_types
    │
    ▼
Stage 4 → field_tree, field_mappings, format_functions, confidence_scores,
          validation_result, ambiguous_fields, block_classifications_confirmed
    │
    ▼
Stage 5 → result_json, stage_5_result
              └── PipelineResult (resposta final da API)
```

---

## Input do Pipeline

Keys injetadas pelo router antes do Stage 1:

| Context Key | Tipo | Descrição |
|-------------|------|-----------|
| `pdf_documents` | `list[{id, path, name}]` | PDFs a processar |
| `xsd_path` | `str` | Caminho para o XSD de mapeamento |
| `job_id` | `str` (UUID v4) | ID do job de análise |
| `_storage` | Storage | Instância de storage (Supabase) |
| `_job` | `dict` | Metadata do job |

---

## Stage 1 — Layout Clustering

**Módulo:** `stage1_layout_clustering.py` + `stage1_clustering/`

**Lê do context:** `pdf_documents`, `job_id`

**Escreve no context:**

| Context Key | Tipo Pydantic | Descrição |
|-------------|---------------|-----------|
| `clusters` | `list[Cluster]` | Grupos de páginas com layout idêntico |
| `_raw_text_blocks` | `dict[str, list[dict]]` | Blocos de texto brutos por página (interno) |

**Modelo `Cluster`:**
```python
class Cluster(BaseModel):
    cluster_id: str
    pages: list[PageReference]           # {pdf_id, page_index}
    representative_page: PageReference   # página usada para extração
    page_count: int
    confidence: ClusterConfidence | float
```

**Garantia:** todo cluster tem exatamente uma `representative_page`. Stages downstream operam **apenas** sobre páginas representativas.

---

## Stage 2 — Deep Extraction

**Módulo:** `stage2_deep_extraction.py` + `stage2_extraction/`

**Lê do context:** `clusters`, `pdf_documents`, `_storage`

**Escreve no context:**

| Context Key | Tipo Pydantic | Descrição |
|-------------|---------------|-----------|
| `enriched_documents` | `list[EnrichedDocument]` | Documentos com páginas extraídas |
| `extraction_warnings` | `list[dict]` | Avisos de extração (não-bloqueantes) |

**Modelo `EnrichedDocument`:**
```python
class EnrichedDocument(BaseModel):
    pdf_id: str
    pdf_name: str
    pages: list[EnrichedPage]

class EnrichedPage(BaseModel):
    page_index: int
    cluster_id: str
    is_representative: bool
    width: float
    height: float
    text_blocks: list[TextBlock]    # texto + bbox + font + cor
    images: list[ImageInfo]         # imagens raster com bbox
    fonts: list[FontInfo]           # fontes usadas na página
    grid_info: dict | None          # colunas/linhas detectadas
    screenshot_path: str | None     # screenshot para Mistral OCR
    tables: list[dict]              # tabelas vetoriais (rich cells)
    drawn_elements: list[dict] | None  # elementos desenhados (linhas, retângulos)
```

**Garantia:** `enriched_documents` contém apenas páginas representativas (`is_representative=True`). Páginas não-representativas NÃO são extraídas.

---

## Stage 3 — Structural Analysis

**Módulo:** `stage3_structural_analysis.py` + `stage3_structural/`

**Lê do context:** `clusters`, `enriched_documents`, `_storage`, `job_id`

**Escreve no context:**

| Context Key | Tipo Pydantic | Descrição |
|-------------|---------------|-----------|
| `document_trees` | `dict[str, dict]` | Árvore estrutural por cluster_id |
| `intelligence` | `dict[str, ClusterIntelligence]` | Classificação de blocos por cluster |
| `visual_analysis` | `dict[str, Any]` | Análise visual via Mistral OCR |
| `label_value_pairs` | `dict[str, Any]` | Pares label→value detectados |
| `layout_types` | `list[LayoutTypeInfo]` | Tipos de layout identificados |

**Modelo `ClusterIntelligence`:**
```python
class ClusterIntelligence(BaseModel):
    block_classifications: dict[str, dict]  # block_id → BlockClassification
    labels: list[str]
    dynamic_fields: list[str]
    optional_fields: list[str]
    conditional_fields: list[str]
    classification_quality: dict
```

**Modelo `BlockClassification`:**
```python
class BlockClassification(BaseModel):
    semantic: str      # "label"|"dynamic"|"semi_dynamic"|"likely_dynamic"|"static"|"header"|"footer_text"
    stability: str     # "stable"|"variable"|"rare"|"unknown"
    variant: str       # "required"|"optional"|"conditional"
    presence_ratio: float
    pdf_coverage: float
    confidence: float
    field_pair: str | None
    smart_signals: list[str] | None
    present_in_pdfs: list[str] | None
```

**Modelo `LayoutTypeInfo`:**
```python
class LayoutTypeInfo(BaseModel):
    id: str
    cluster_id: str
    name: str
    page_width_pts: float   # padrão: 595.0 (A4)
    page_height_pts: float  # padrão: 842.0 (A4)
    page_count: int
```

---

## Stage 4 — Field Mapping

**Módulo:** `stage4_field_mapping.py` + `stage4_mapping/`

**Lê do context:** `document_trees`, `intelligence`, `label_value_pairs`, `layout_types`, `enriched_documents`, `clusters`, `xsd_path`

**Escreve no context:**

| Context Key | Tipo Pydantic | Descrição |
|-------------|---------------|-----------|
| `field_tree` | `dict | None` | Árvore XSD de campos disponíveis |
| `field_mappings` | `list[FieldMappingEntry]` | Mapeamentos bloco → campo XSD |
| `format_functions` | `dict[str, str]` | Funções de formato por campo |
| `confidence_scores` | `dict[str, ConfidenceScoreEntry]` | Scores por layout (0.0–1.0) |
| `validation_result` | `ValidationResult` | Resultado de validação de consistência |
| `ambiguous_fields` | `list[dict]` | Campos com mapeamento ambíguo |
| `block_classifications_confirmed` | `dict[str, Any]` | Classificações confirmadas pelo mapeamento |

**Modelo `FieldMappingEntry`** (alinhado com `pipeline.types.ts` no frontend):
```python
class FieldMappingEntry(BaseModel):
    block_id: str
    layout_type_id: str
    pdf_text: str
    label_text: str
    bbox: list[float] | None
    page_number: int
    pdf_id: str
    xsd_field_path: str
    xsd_type: str | None
    confidence: float
    is_ambiguous: bool
    detected_format: str | None
    semantic_confirmed: str | None
    is_table_cell: bool
    # Frontend interface fields
    name: str
    path: str
    type: str        # "text" (default)
    status: str      # "unmapped" (default)
    isOptional: bool
```

**Modelo `ValidationResult`:**
```python
class ValidationResult(BaseModel):
    warnings: list[dict]
    errors: list[dict]
    orphans: list[str]          # blocos sem mapeamento
    unmapped_required: list[str]  # campos XSD required sem mapeamento
```

---

## Stage 5 — Template Generation

**Módulo:** `stage5_template_generation.py` + `stage5_template/`

**Lê do context:**
```
document_trees, intelligence, visual_analysis, enriched_documents,
field_mappings, field_tree, layout_types, clusters, confidence_scores,
validation_result, block_classifications_confirmed, format_functions,
pdf_documents, _storage, job_id
```

**Escreve no context:**

| Context Key | Tipo Pydantic | Descrição |
|-------------|---------------|-----------|
| `result_json` | `PipelineResult` | Resultado final da API |
| `stage_5_result` | `Stage5Result` | Sumário do Stage 5 |

**Modelo `PipelineResult`** (resposta do endpoint `GET /api/v1/analyze/{job_id}/result`):
```python
class PipelineResult(BaseModel):
    layout_types: list[dict]
    field_mappings: list[FieldMappingEntry]
    document_structure: DocumentStructure
    confidence_scores: dict[str, NormalizedConfidenceScore]  # 0–100 int (normalizado)
    coverage: dict
    template_draft: dict
    document_type: str
    document_type_confidence: float
    ambiguous_fields: list[dict]
    format_functions: dict[str, str]
    overlay_items: dict
    visual_analysis: dict | None
    intelligence: dict | None
    validation_result: dict | None
    block_classifications_confirmed: dict | None
    multi_doc: dict            # {pdfs, matrix, detections}
    page_config: dict
    anchors: dict
```

**Nota:** `confidence_scores` no result_json usa `NormalizedConfidenceScore` (0–100 int), diferente de `ConfidenceScoreEntry` no context (0.0–1.0 float). Stage 5 normaliza antes de montar o resultado.

---

## Context Keys — Inventário Completo

| Key | Produzido por | Consumido por | Tipo |
|-----|---------------|---------------|------|
| `pdf_documents` | Input | Stage 2, Stage 5 | `list[dict]` |
| `xsd_path` | Input | Stage 4 | `str` |
| `job_id` | Input | Stage 1, Stage 3, Stage 5 | `str` |
| `_storage` | Input | Stage 2, Stage 5 | Storage |
| `clusters` | Stage 1 | Stage 2, Stage 3, Stage 4, Stage 5 | `list[Cluster]` |
| `_raw_text_blocks` | Stage 1 | (interno) | `dict` |
| `enriched_documents` | Stage 2 | Stage 3, Stage 4, Stage 5 | `list[EnrichedDocument]` |
| `extraction_warnings` | Stage 2 | (log) | `list[dict]` |
| `document_trees` | Stage 3 | Stage 4, Stage 5 | `dict[str, dict]` |
| `intelligence` | Stage 3 | Stage 4, Stage 5 | `dict[str, ClusterIntelligence]` |
| `visual_analysis` | Stage 3 | Stage 5 | `dict` |
| `label_value_pairs` | Stage 3 | Stage 4 | `dict` |
| `layout_types` | Stage 3 | Stage 4, Stage 5 | `list[LayoutTypeInfo]` |
| `field_tree` | Stage 4 | Stage 5 | `dict | None` |
| `field_mappings` | Stage 4 | Stage 5 | `list[FieldMappingEntry]` |
| `format_functions` | Stage 4 | Stage 5 | `dict[str, str]` |
| `confidence_scores` | Stage 4 | Stage 5 | `dict[str, ConfidenceScoreEntry]` |
| `validation_result` | Stage 4 | Stage 5 | `ValidationResult` |
| `ambiguous_fields` | Stage 4 | Stage 5 | `list[dict]` |
| `block_classifications_confirmed` | Stage 4 | Stage 5 | `dict` |
| `result_json` | Stage 5 | API Response | `PipelineResult` |

---

## Nota sobre Pydantic v2

Todos os modelos usam Pydantic v2 (`model_validate()` / `model_dump()`). `dict` raw é anti-pattern — usar modelos tipados para novas context keys.

Referência: `backend/models/pipeline_context.py`
