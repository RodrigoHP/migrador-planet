# Pipeline AS-IS — Documentação Completa do Estado Atual

**Versão:** 1.0
**Data:** 2026-03-20
**Autor:** @architect (Aria)
**Propósito:** Documentar com precisão o que cada estágio faz hoje, como faz, o que lê e escreve

---

## 1. Visão Geral

O pipeline converte PDFs do PlanetExpress em HTML templates via **28 estágios** organizados em **8 blocos**. Execução sequencial, orquestrada por `backend/routers/analyze.py`. Estado compartilhado via `context: Dict[str, Any]`.

```
PDF(s) + XSD
    │
    ▼
┌─ Bloco 1: Aquisição ──────────────────────┐
│  Stage 29: XSD Parsing                     │
└────────────────────────────────────────────┘
    │
    ▼
┌─ Bloco 2: PDF Parsing ────────────────────┐
│  Stage 2:  Text Extraction                 │
│  Stage 3:  Text Reconstruction             │
│  Stage 4:  Font Extraction → CSS           │
│  Stage 5:  Image Extraction                │
│  Stage 6:  Grid Detection                  │
│  Stage 2b: Screenshot Generator            │
└────────────────────────────────────────────┘
    │
    ▼
┌─ Bloco 3: Layout Discovery ───────────────┐
│  Stage 7:  Skeleton Builder                │
│  Stage 8:  Page Clustering                 │
│  Stage 9:  Representative Selection        │
│  Stage 10: Fingerprint Generation          │
│  Stage 11: Registry Lookup                 │
└────────────────────────────────────────────┘
    │
    ▼
┌─ Bloco 4: Layout Intelligence ────────────┐
│  Stage 12: Layout Alignment                │
│  Stage 13: Multi-Example Analysis          │
│  Stage 14: Stability Classification        │
│  Stage 15: Variant Detection               │
│  Stage 16: Intelligence Normalization      │
└────────────────────────────────────────────┘
    │
    ▼
┌─ Bloco 5: Tables ─────────────────────────┐
│  Stage 17: Table Detection                 │
│  Stage 18: Table Structuring               │
└────────────────────────────────────────────┘
    │
    ▼
┌─ Bloco 6: Semantic + Vision ──────────────┐
│  Stage 19: Semantic Analysis               │
│  Stage 20: Visual Segmentation             │
│  Stage 21: Visual Interpretation           │
│  Stage 22: Vision Self-Check               │
└────────────────────────────────────────────┘
    │
    ▼
┌─ Bloco 7: Matching ───────────────────────┐
│  Stage 23: Field Matching                  │
│  Stage 24: Format Detection                │
└────────────────────────────────────────────┘
    │
    ▼
┌─ Bloco 8: Validation + Output ────────────┐
│  Stage 25: Confidence Scoring              │
│  Stage 26: Layout Consistency              │
│  Stage 27: Template Draft                  │
│  Stage 28: Pipeline Result                 │
└────────────────────────────────────────────┘
    │
    ▼
  PipelineResult → Frontend Editor
```

---

## 2. Orquestrador

**Arquivo:** `backend/routers/analyze.py`

| Aspecto | Implementação |
|---------|---------------|
| Execução | Sequencial — `for block in pipeline.blocks: for stage in block.stages: await stage.execute(context)` |
| Estado | In-memory dict por `job_id` com TTL 3600s |
| Streaming | SSE com replay buffer — eventos acumulados em `event_log`, clientes reconectam e recebem histórico |
| Progresso | Cada estágio emite evento `{block, stage, stage_name, status, progress_pct, summary}` |
| Erros | Try/except por estágio — falha para pipeline, emite "failed", armazena erro |
| Cancelamento | `cancel_flag: asyncio.Event` checado entre estágios |

---

## 3. Modelos de Dados

### 3.1 ParsedDocument (`backend/models/parsed_document.py`)

```python
ParsedDocument:
  job_id: str
  pdf_index: int              # 0-based
  pdf_name: str
  pages: List[ParsedPage]

ParsedPage:
  page_number: int            # 0-based
  text_blocks: List[TextBlock]
  images: List[ParsedImage]   # Stage 5
  fonts: List[CSSFont]        # Stage 4
  grid_info: GridInfo | None  # Stage 6
  screenshot_path: str | None # Stage 2b

TextBlock:
  text: str
  bbox: (x0, y0, x1, y1)     # PDF points (595×842 A4)
  font_name: str
  font_size: float            # pontos
  page_number: int
  pdf_index: int
  semantic_label: str         # Stage 19: "label"|"value"|"title"|"header"|...

CSSFont:
  font_family: str
  font_size: float
  font_weight: "normal"|"bold"
  font_style: "normal"|"italic"

ParsedImage:
  path: str                   # /tmp/jobs/{job_id}/assets/...
  format: str                 # "png"|"jpeg"
  bbox: (x0, y0, x1, y1)
  page_number: int
  pdf_index: int

GridInfo:
  columns: int
  rows: int
  column_positions: List[float]
  row_positions: List[float]
```

### 3.2 LayoutType (`backend/models/layout_type.py`)

```python
LayoutZones:
  header_top: 0.0
  header_bottom: 0.15        # top 15%
  body_top: 0.15
  body_bottom: 0.90
  footer_top: 0.90           # bottom 10%
  footer_bottom: 1.0

LayoutSkeleton:
  page_number: int
  pdf_index: int
  text_blocks: List[(text, bbox)]
  table_candidates: List[bbox]
  zones: LayoutZones
  grid_info: GridInfo | None
  page_width: 595.0          # A4 default
  page_height: 842.0

  to_feature_vector() → [num_blocks, avg_font_size, table_count, text_density, header_height_ratio]
    # avg_font_size = mean(bbox heights), NOT actual font size
    # text_density = total_text_area / (page_width * page_height)

LayoutFingerprint:
  table_count: float          # average across cluster
  column_count: int
  header_blocks: float        # average across cluster
  body_zone_ratio: float
  footer_present: bool
  fingerprint_hash: str       # SHA-256

LayoutType:
  id: str                     # "layout-0", "layout-1"
  cluster_id: int
  name: str                   # heurístico: "Transações", "Extrato", etc.
  representative_page: {pdf_index, page_number}
  secondary_pages: List[{pdf_index, page_number}]
  page_count: int
  pages: List[{pdf_index, page_number}]
  fingerprint: LayoutFingerprint
  is_reusable: bool           # Stage 11
  template_id: str | None     # Stage 11
```

### 3.3 DetectedTable (`backend/models/detected_table.py`)

```python
DetectedTable:
  table_id: str
  page_number: int
  pdf_index: int
  bbox: (x0, y0, x1, y1)
  headers: List[str]
  rows: List[List[str]]
  column_widths: List[float]
  is_multi_page: bool
  continuation_pages: List[int]
  confidence: float           # 0.0-1.0
  detection_method: str       # "grid_lines"|"alignment"|"pattern"|"combined"
```

### 3.4 FieldTree (`backend/models/field_tree.py`)

```python
FieldNode:
  name: str                   # "cliente", "nome"
  path: str                   # "cliente.nome"
  type: str                   # "string"|"decimal"|"date"|"integer"|"boolean"|"complex"
  required: bool
  is_array: bool              # maxOccurs > 1
  children: List[FieldNode]

FieldTree:
  root_nodes: List[FieldNode]
  flat_paths: List[str]       # ["cliente.nome", "itens[].valor", ...]
```

**XSD Type Map:** 26 XSD types → 6 canonical types (string, decimal, date, integer, boolean, complex)

---

## 4. Estágios — Detalhe Completo

### BLOCO 1: Aquisição

#### Stage 29: XSD Parsing
**Arquivo:** `backend/services/stages/xsd_parser.py` (373 linhas)
**Pergunta:** "Qual a estrutura do schema XSD?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["xsd_path"]` ou procura `schema.xsd` em `context["tmp_base"]` |
| **Escreve** | `context["field_tree"]` ← FieldTree.to_dict() |
| | `context["xsd_parse_error"]` ← str (se falha) |
| **Algoritmo** | lxml recursivo: `xs:element` → `xs:complexType` → `xs:sequence`. Resolve referências globais. Gera `flat_paths` em dot-notation |
| **Wrapper detection** | Se 1 elemento top-level, pula wrapper e promove filhos |
| **Namespaces** | Suporta `http://www.w3.org/2001/XMLSchema` e `http://www.w3.org/1999/XMLSchema` |
| **Erro** | XMLSyntaxError → ValueError com número da linha. OSError → FileNotFoundError |

---

### BLOCO 2: PDF Parsing

> **Nota:** Todos os 6 estágios rodam em TODAS as páginas de TODOS os PDFs.

#### Stage 2: Text Extraction
**Arquivo:** `backend/services/stages/text_extraction.py` (164 linhas)
**Pergunta:** "Que blocos de texto existem em cada página?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["job_id"]`, `context["tmp_base"]` → procura PDFs no disco |
| **Escreve** | `context["parsed_documents"]` ← List[ParsedDocument dicts] |
| **Algoritmo** | PyMuPDF `page.get_text("dict")` → blocks → lines → spans |
| **Extrai** | text, bbox, font_name, font_size por span |
| **Fallback** | Busca recursiva de PDFs se diretório vazio |
| **Limite** | PDFs encriptados → ValueError |

#### Stage 3: Text Reconstruction
**Arquivo:** `backend/services/stages/text_reconstruction.py` (176 linhas)
**Pergunta:** "Como juntar spans fragmentados em palavras/frases?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["parsed_documents"]` |
| **Escreve** | `context["parsed_documents"]` ← atualizado com blocos mesclados |
| **Constantes** | `Y_THRESHOLD = 3.0` pts, `X_SPACING_FACTOR = 1.2` |
| **Algoritmo** | Sort por Y→X. Agrupa em linhas por Y_THRESHOLD. Dentro de cada linha, mescla se: mesma família de fonte E gap < avg_char_width × 1.2. Espaço inserido se gap > avg_w × 0.3 |

#### Stage 4: Font Extraction → CSS
**Arquivo:** `backend/services/stages/font_extraction.py` (138 linhas)
**Pergunta:** "Qual a fonte CSS correspondente a cada fonte PDF?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["parsed_documents"]` |
| **Escreve** | `context["parsed_documents"]` ← atualizado com `fonts: [CSSFont]` por página |
| **FONT_MAP** | 14 entradas: Helvetica→Arial, Times→Times New Roman, Courier→Courier New, Symbol, ZapfDingbats |
| **Algoritmo** | Lookup direto → strip subset prefix (`ABCDEF+Font` → `Font`) → fallback nome original |
| **Bold** | `"bold"` ou `"-bd"` ou `",bold"` no nome |
| **Italic** | `"italic"` ou `"oblique"` ou `"-it"` no nome |

#### Stage 5: Image Extraction
**Arquivo:** `backend/services/stages/image_extraction.py` (175 linhas)
**Pergunta:** "Que imagens existem e onde estão posicionadas?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["job_id"]`, `context["tmp_base"]`, `context["parsed_documents"]` |
| **Escreve** | `context["parsed_documents"]` ← atualizado com `images: [ParsedImage]` por página |
| **Algoritmo** | PyMuPDF `doc.get_page_images()` + `doc.extract_image(xref)`. Bbox via `page.get_image_rects(xref)` |
| **Disco** | Salva em `/tmp/jobs/{job_id}/assets/img_{pdf}_{page}_{idx}.{ext}` |
| **Fallback** | Bbox `(0,0,0,0)` se extração de posição falha |

#### Stage 6: Grid Detection
**Arquivo:** `backend/services/stages/grid_detection.py` (178 linhas)
**Pergunta:** "Que grade de colunas/linhas existe nos blocos de texto?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["parsed_documents"]` |
| **Escreve** | `context["parsed_documents"]` ← atualizado com `grid_info: GridInfo` por página |
| **Constantes** | `MAX_CLUSTERS = 10`, `MIN_BLOCKS_FOR_CLUSTERING = 3` |
| **Algoritmo** | 1. `_optimal_k()`: gap analysis — gaps > median×3 determinam número de clusters. 2. `_cluster_1d()`: KMeans em coordenadas X (colunas) e Y (linhas) separadamente. 3. Fallback sem sklearn: agrupamento por gap |
| **Threshold** | Gap > `max(median_gap × 3, 5.0)` pts |

#### Stage 2b: Screenshot Generator
**Arquivo:** `backend/services/stages/screenshot_generator.py` (186 linhas)
**Pergunta:** "Como renderizar PNGs de cada página para Vision AI?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["job_id"]`, `context["tmp_base"]`, `context["parsed_documents"]` |
| **Escreve** | `context["parsed_documents"]` ← atualizado com `screenshot_path` por página |
| **Constantes** | `DPI = 150`, `MAX_SCREENSHOT_PAGES = 50`, `LARGE_PDF_THRESHOLD = 500` |
| **Algoritmo** | PyMuPDF pixmap com matrix DPI/72. Para PDFs > 500 páginas: amostra distribuída uniformemente (até 50 páginas) |
| **Disco** | `/tmp/jobs/{job_id}/screenshots/page_{pdf}_{page}.png` |

---

### BLOCO 3: Layout Discovery

#### Stage 7: Skeleton Builder
**Arquivo:** `backend/services/stages/skeleton_builder.py` (180 linhas)
**Pergunta:** "Qual o esqueleto estrutural de cada página?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["parsed_documents"]` |
| **Escreve** | `context["_skeleton_objects"]` ← List[LayoutSkeleton] (Python) |
| | `context["skeletons"]` ← serializado |
| **Constantes** | `_DEFAULT_WIDTH = 595.0`, `_DEFAULT_HEIGHT = 842.0`, `_HEADER_BOTTOM = 0.15`, `_FOOTER_TOP = 0.90` |
| **Algoritmo** | 1. Infere dimensões: max(y1) e max(x1) dos blocos, nunca abaixo dos defaults. 2. Converte text_blocks em tuples `(text, bbox)`. 3. Table candidates do grid: se grid tem ≥2 rows E ≥2 cols → bbox `(cols[0], rows[0], cols[-1], rows[-1])`. 4. Zonas fixas: header 0-15%, body 15-90%, footer 90-100% |

#### Stage 8: Page Clustering
**Arquivo:** `backend/services/stages/page_clustering.py` (202 linhas)
**Pergunta:** "Quais páginas têm layout similar?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["_skeleton_objects"]` |
| **Escreve** | `context["cluster_labels"]` ← List[int] (um label por skeleton) |
| **Constantes** | `_LARGE_PDF_THRESHOLD = 500`, `_SAMPLE_SIZE = 50`, `_MIN_CLUSTERS = 2`, `_MAX_CLUSTERS = 8` |
| **Feature vector** | 5-dim: `[num_blocks, avg_font_size, table_count, text_density, header_height_ratio]` |
| **Algoritmo** | 1. StandardScaler nos features. 2. `_best_k()`: testa k ∈ [2, min(8, n)], maximiza silhouette_score. 3. KMeans(k, random_state=42). 4. PDFs > 500 páginas: amostra 50, fit no sample, predict no resto |
| **Fallback** | < 3 páginas → k=1 (todas no mesmo cluster) |

#### Stage 9: Representative Selection
**Arquivo:** `backend/services/stages/representative_selection.py` (244 linhas)
**Pergunta:** "Qual a melhor página representante de cada cluster?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["_skeleton_objects"]`, `context["cluster_labels"]` |
| **Escreve** | `context["_layout_type_objects"]` ← List[LayoutType] (Python) |
| | `context["layout_types"]` ← serializado |
| **Constantes** | `_MAX_SECONDARY = 2` |
| **Algoritmo** | 1. Agrupa skeletons por cluster. 2. Calcula centróide (média de cada dim do feature vector). 3. Primary = skeleton mais próximo do centróide (distância euclidiana), preferindo pdf_index diferente se multi-PDF. 4. Secondary = próximos 2, preferindo PDFs diferentes |
| **Naming** | 7 heurísticas no fingerprint: table_count≥2→"Transações", table_count≥1→"Extrato", header_blocks≥5→"Cabeçalho", etc. Fallback: 8 nomes genéricos |

#### Stage 10: Fingerprint Generation
**Arquivo:** `backend/services/stages/fingerprint_generation.py` (166 linhas)
**Pergunta:** "Qual a assinatura estrutural de cada cluster?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["_layout_type_objects"]` (com `_cluster_skeletons`) |
| **Escreve** | Atualiza `lt.fingerprint` in-place, re-serializa `context["layout_types"]` |
| **Algoritmo** | Médias do cluster: table_count, header_blocks. Column_count do primeiro skeleton com grid. Footer_present se algum bloco tem Y-center ≥ footer_top × page_height. SHA-256 do JSON canônico |

#### Stage 11: Registry Lookup
**Arquivo:** `backend/services/stages/registry_lookup.py` (188 linhas)
**Pergunta:** "Já temos um template salvo para este layout?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["_layout_type_objects"]`, env vars `SUPABASE_URL`/`SUPABASE_KEY` |
| **Escreve** | Atualiza `lt.is_reusable`, `lt.template_id` in-place, re-serializa `context["layout_types"]` |
| **Algoritmo** | Query Supabase `layout_registry` por `fingerprint_hash`. Hit → `is_reusable=True` |
| **Fallback** | Sem Supabase → skip silencioso, emite warning SSE |

---

### BLOCO 4: Layout Intelligence

#### Stage 12: Layout Alignment
**Arquivo:** `backend/services/stages/layout_alignment.py` (162 linhas)
**Pergunta:** "Que offsets de coordenadas existem entre PDFs do mesmo cluster?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["_layout_type_objects"]`, `context["_skeleton_objects"]` |
| **Escreve** | `context["alignment_offsets"]` ← Dict[cluster_id → Dict[pdf_index → (dx, dy)]] |
| | `context["_aligned"]` ← True |
| | `context["intelligence_metadata"]` ← `{single_document, reduced_accuracy}` |
| **Algoritmo** | Mediana do top-left do primeiro bloco por PDF. Ref = min(pdf_indices). Offset = ref − current |
| **Single-doc** | Todos offsets = (0.0, 0.0), `reduced_accuracy=True` |

#### Stage 13: Multi-Example Analysis
**Arquivo:** `backend/services/stages/multi_example_analysis.py` (295 linhas)
**Pergunta:** "O que é label (texto estático) vs value (texto que muda)?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["_layout_type_objects"]`, `context["_skeleton_objects"]`, `context["alignment_offsets"]`, `context["intelligence_metadata"]` |
| **Escreve** | `context["_element_labels"]` ← Dict[cluster_id → List[{bbox_key, text_samples, classification, confidence}]] |
| **Constantes** | `_OVERLAP_THRESHOLD = 0.80` |
| **Multi-PDF** | Agrupa blocos por bbox normalizada (overlap ≥ 80%). Se texto idêntico em todos os PDFs → "label". Se varia → "dynamic". Confidence: "confirmed" |
| **Single-PDF** | Heurísticas: `endswith(":")` → label; regex numérico → dynamic; ≤3 chars uppercase → label; ≤30 chars → label; else dynamic. Confidence: "inferred" |

#### Stage 14: Stability Classification
**Arquivo:** `backend/services/stages/stability_classification.py` (198 linhas)
**Pergunta:** "Quão estável é cada elemento entre documentos?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["_element_labels"]`, `context["_layout_type_objects"]`, `context["_skeleton_objects"]`, `context["intelligence_metadata"]` |
| **Escreve** | `context["_stability_map"]` ← Dict[cluster_id → Dict[bbox_key → {classification, stability_score, doc_count, total_docs}]] |
| **Algoritmo** | `stability_score = doc_count / total_docs`. Se confirmed: doc_count = total_docs. Classification: doc_count < total → "absent"; label → "stable"; dynamic → "variable". Single-doc: "unknown", score=1.0 |

#### Stage 15: Variant Detection
**Arquivo:** `backend/services/stages/variant_detection.py` (260 linhas)
**Pergunta:** "Que campos são opcionais ou condicionais?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["_stability_map"]`, `context["_layout_type_objects"]`, `context["_skeleton_objects"]`, `context["intelligence_metadata"]` |
| **Escreve** | `context["_variants"]` ← Dict[cluster_id → List[{type, elements, presence_pattern}]] |
| | `context["_conditional_sections"]` ← Dict[cluster_id → List[{elements, presence_pattern}]] |
| **Constantes** | `_MIN_SECTION_SIZE = 2`, `_ADJACENCY_Y_THRESHOLD = 30.0` pts |
| **Algoritmo** | Optional fields: elements com classification="absent". Conditional sections: ≥2 absent adjacentes (Y-gap ≤ 30pts). Dynamic tables: se max-min avg_table_count > 0.5 entre PDFs |
| **Single-doc** | Skip — listas vazias |

#### Stage 16: Intelligence Normalization
**Arquivo:** `backend/services/stages/intelligence_normalization.py` (178 linhas)
**Pergunta:** "Como consolidar toda a inteligência em um pacote?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["_layout_type_objects"]`, `context["_element_labels"]`, `context["_stability_map"]`, `context["_variants"]`, `context["_conditional_sections"]`, `context["intelligence_metadata"]` |
| **Escreve** | `context["intelligence"]` ← Dict[cluster_id → {labels[], dynamic_fields[], stability_map, variants[], conditional_sections[], metadata}] |
| | Re-serializa `context["layout_types"]` com `_intelligence` attached |

---

### BLOCO 5: Tables

#### Stage 17: Table Detection
**Arquivo:** `backend/services/stages/table_detection.py` (438 linhas)
**Pergunta:** "Onde estão as tabelas em cada página?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["parsed_documents"]` |
| **Escreve** | `context["tables"]` ← List[DetectedTable dicts] |
| **Constantes** | `TABLE_SCORE_THRESHOLD = 0.5`, `MIN_COLUMNS_FOR_TABLE = 2`, `MIN_ROWS_FOR_TABLE = 2`, `CLUSTER_GAP_THRESHOLD = 15.0` pts, `PATTERN_REPEAT_MIN = 3` |
| **3 evidências** | **Grid score** (0.45): grid.cols≥2 AND rows≥2 → factor min(cols/4,1)×min(rows/6,1). **Alignment score** (0.35): cluster X/Y positions, filtra rows com ≥50% colunas. **Pattern score** (0.20): conta rows com mesma contagem de colunas |
| **Sem grid** | Weights: 0.65×align + 0.35×pattern |
| **Multi-page** | Tabela com y1 > 700pts e próxima página com column_count ±1 → linkada |

#### Stage 18: Table Structuring
**Arquivo:** `backend/services/stages/table_structuring.py` (268 linhas)
**Pergunta:** "Qual a estrutura refinada de cada tabela?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["tables"]`, `context["parsed_documents"]` |
| **Escreve** | `context["tables"]` ← atualizado com headers/rows refinados |
| **Algoritmo** | Re-identifica headers: blocos no top 15% do bbox que são bold ou font > avg×1.1. Cell grid por column bucketing + Y-grouping. Merge multi-page: pula header repetido da continuação |

---

### BLOCO 6: Semantic + Vision

#### Stage 19: Semantic Analysis
**Arquivo:** `backend/services/stages/semantic_analysis.py` (309 linhas)
**Pergunta:** "O que é cada bloco de texto semanticamente?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["parsed_documents"]`, `context["tables"]` |
| **Escreve** | `context["parsed_documents"]` ← atualizado com `semantic_label` em cada TextBlock |
| **Constantes** | `HEADER_ZONE_FRACTION = 0.15`, `FOOTER_ZONE_FRACTION = 0.10`, `DEFAULT_PAGE_HEIGHT = 842.0` |
| **Labels** | `label`, `value`, `title`, `header`, `footer_text`, `page_number`, `table_header`, `table_cell`, `field` |
| **4 prioridades** | 1. **Table context**: centro do bloco dentro de table bbox → `table_header` ou `table_cell`. 2. **Zone**: Y ≤ 15% → `header`; Y ≥ 90% → `footer_text` ou `page_number` (regex). 3. **Formatting**: font > avg×1.2 + bold → `title`. 4. **Content**: `endswith(":")` → `label`; regex numérico → `value`; else → `value` |
| **Default** | Tudo que não match → `"value"` |

#### Stage 20: Visual Segmentation
**Arquivo:** `backend/services/stages/visual_segmentation.py` (295 linhas)
**Pergunta:** "Que regiões visuais a Vision AI identifica?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["layout_types"]`, `context["parsed_documents"]`, `context["job_id"]`, `context["vision_client"]` |
| **Escreve** | `context["visual_analysis"]` ← Dict["{pdf_index}:{page_number}" → {visual_regions, visual_interpretations: [], consistency_score: null}] |
| | `context["vision_unavailable"]` ← bool |
| | `context["_vision_api_calls"]` ← int |
| **Algoritmo** | Screenshot → base64 → GPT-4o via OpenRouter → JSON com regiões: {type, bbox, description} |
| **Valid types** | `header`, `body`, `footer`, `sidebar`, `table_area`, `chart_area`, `image_area`, `form_area` |
| **Scope** | Só 1 página representativa por cluster |

#### Stage 21: Visual Interpretation
**Arquivo:** `backend/services/stages/visual_interpretation.py` (236 linhas)
**Pergunta:** "O que significa cada região visual?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["visual_analysis"]`, `context["parsed_documents"]`, `context["vision_client"]` |
| **Escreve** | `context["visual_analysis"][page_key]["visual_interpretations"]` ← List[{region_type, description, html_suggestion}] |
| **Algoritmo** | Segunda chamada GPT-4o com screenshot + regiões do Stage 20. Retorna interpretações com `html_suggestion` |

#### Stage 22: Vision Self-Check
**Arquivo:** `backend/services/stages/vision_self_check.py` (348 linhas)
**Pergunta:** "A Vision AI concorda com a extração programática?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["visual_analysis"]`, `context["parsed_documents"]`, `context["tables"]`, `context["vision_client"]` |
| **Escreve** | `context["visual_analysis"]` ← atualizado com `consistency_score` (0-100) e `consistency_level` |
| | `context["vision_validation"]` ← {overall_score, page_results, low_confidence_pages} |
| **Constantes** | `CONSISTENT_THRESHOLD = 80`, `PARTIAL_THRESHOLD = 50` |
| **3 dimensões** | Text coverage (0-33): regiões de texto encontradas. Table agreement (0-33): visual vs detectadas. Image agreement (0-34): visual vs extraídas |
| **Retry** | Se score < 50 → re-roda segmentação uma vez, pega o maior score |

---

### BLOCO 7: Matching

#### Stage 23: Field Matching
**Arquivo:** `backend/services/stages/field_matching.py` (445 linhas)
**Pergunta:** "Que campo XSD corresponde a cada valor encontrado no PDF?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["parsed_documents"]`, `context["field_tree"]` (flat_paths), `context["openrouter_client"]` |
| **Escreve** | `context["field_mappings"]` ← List[FieldMappingResult dicts] |
| | `context["ambiguous_fields"]` ← List[str] |
| **Constantes** | `GEMINI_FLASH_MODEL = "google/gemini-2.0-flash-001"`, `AMBIGUITY_THRESHOLD = 0.1`, `ADJACENT_Y_TOLERANCE = 20.0` pts, `ADJACENT_X_MAX_DIFF = 250.0` pts |
| **Adjacência** | Para non-table: label com `semantic_label="label"` à esquerda, `|y_mid_diff| ≤ 20`, `0 ≤ x_dist ≤ 250`. Para table_cell: procura `table_header` acima na mesma coluna |
| **LLM** | Gemini 2.0 Flash via OpenRouter. Prompt com label+value+flat_paths[:80]. JSON response: [{path, score}] |
| **Fallback** | difflib.SequenceMatcher contra todos os flat_paths. Top 5 por ratio |
| **Ambiguidade** | Top-2 scores differ < 0.1 → `is_ambiguous=True` |
| **Structural labels** | Pula: header, footer_text, page_number, title, table_header, label, image |

#### Stage 24: Format Detection
**Arquivo:** `backend/services/stages/format_detection.py` (186 linhas)
**Pergunta:** "Que formato de dado tem cada valor?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["field_mappings"]` |
| **Escreve** | `context["format_functions"]` ← Dict[format_name → js_function_string] |
| | `context["field_mappings"]` ← atualizado com `detected_format` |
| **7 patterns** | `currency_brl`, `date_numeric`, `date_extenso`, `cpf`, `cnpj`, `phone`, `percentage` |
| **Algoritmo** | Regex match no `pdf_text`. Primeiro match ganha. JS functions hardcoded para cada formato |

---

### BLOCO 8: Validation + Output

#### Stage 25: Confidence Scoring
**Arquivo:** `backend/services/stages/confidence_scoring.py` (269 linhas)
**Pergunta:** "Quão confiáveis são os mapeamentos?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["field_mappings"]`, `context["parsed_documents"]`, `context["intelligence"]`, `context["visual_analysis"]`, `context["openrouter_client"]` |
| **Escreve** | `context["confidence_scores"]` ← {factors, global_score, status, ...} |
| **Weights** | layout_stability: 0.25, anchor_detection: 0.25, grid_quality: 0.20, field_variability: 0.15, vision_agreement: 0.15 |
| **5 fatores** | layout_stability: do intelligence (ou 0.5). anchor_detection: % mappings com label_text. grid_quality: cols>1→0.8, else 0.5. field_variability: do intelligence (ou 0.5). vision_agreement: mean(consistency_score/100) (ou 0.5) |
| **LLM opcional** | Claude Sonnet para ajustar global_score |
| **Thresholds** | ≥0.95→"approved", ≥0.80→"review_recommended", <0.80→"human_review_required" |

#### Stage 26: Layout Consistency
**Arquivo:** `backend/services/stages/layout_consistency.py` (222 linhas)
**Pergunta:** "Os mapeamentos são consistentes com o schema e a extração?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["field_mappings"]`, `context["field_tree"]`, `context["parsed_documents"]`, `context["tables"]` |
| **Escreve** | `context["validation_result"]` ← {warnings[], errors[], orphan_count, unmapped_xsd_fields[]} |
| **4 checks** | 1. Value blocks vs mappings count. 2. XSD coverage (unmapped flat_paths). 3. Orphan mappings (path not in field_tree). 4. Table coverage (tabelas detectadas mas sem mapping table_cell) |

#### Stage 27: Template Draft
**Arquivo:** `backend/services/stages/template_draft.py` (477 linhas)
**Pergunta:** "Como gerar o HTML/CSS inicial do template?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | `context["layout_types"]`, `context["field_mappings"]`, `context["field_tree"]`, `context["variants"]` |
| **Escreve** | `context["template_draft"]` ← {html, css, coverage: {fields: {mapped, total}}} |
| **Constantes** | `SCALE_X = 794/595`, `SCALE_Y = 1123/842`, A4 = 794×1123 CSS px |
| **HTML** | `<div class="page page-{name}">` com 3 zonas: header (0-144px), flow (144-1033px), footer (1033-1123px). Cada field → `<span data-bind="text: {xsd_path}">` posicionado absolute |
| **Y-inversion** | `css_top = (page_height - bbox[3]) × SCALE_Y` |
| **Knockout** | Arrays → `<!-- ko foreach -->`, condicionais → `<!-- ko if -->` |
| **Não usa** | `visual_analysis`, `tables` (tabelas não geram `<table>`), `intelligence` |
| **Coverage** | Só `fields: {mapped, total}`. Tables/images/charts = `{mapped: 0, total: 0}` sempre |

#### Stage 28: Pipeline Result
**Arquivo:** `backend/services/stages/pipeline_result.py` (553 linhas)
**Pergunta:** "Como consolidar tudo no resultado final?"

| Aspecto | Detalhe |
|---------|---------|
| **Lê** | Tudo: `parsed_documents`, `layout_types`, `field_mappings`, `confidence_scores`/`confidence_result`, `template_draft`, `format_functions`, `visual_analysis`, `intelligence`, `supabase_client`, `job_id` |
| **Escreve** | `context["result_json"]` ← PipelineResult |
| **Document tree** | FLAT: por página → `TreeNode(type="section")` → filhos diretos com `_LABEL_TO_NODE_TYPE[semantic_label]`. Todas as 100 páginas se tornam nós |
| **Overlay** | Por field_mapping com bbox: calcula `bbox_canvas` (CSS px, Y-inverted) e `bbox_pdf` (pts raw) |
| **Document type** | Heurística de keywords: "boleto", "nota fiscal", "recibo", etc. no texto concatenado |
| **Supabase** | Se client+job_id: UPDATE jobs SET result_json WHERE id=job_id |

---

## 5. Context Keys — Inventário Completo

### Keys públicas (serializam para JSON)

| Key | Tipo | Produtor | Consumidores |
|-----|------|----------|-------------|
| `job_id` | str (UUID) | Router | Todos |
| `tmp_base` | str (path) | Router | 2, 5, 2b |
| `field_tree` | FieldTree dict \| None | Stage 29 | 23, 26, 27 |
| `xsd_parse_error` | str | Stage 29 | — |
| `parsed_documents` | List[ParsedDocument dict] | Stage 2 (atualizado por 3,4,5,6,2b,19) | 7,8,17,18,19,20,23,28 |
| `skeletons` | List[dict] | Stage 7 | — |
| `cluster_labels` | List[int] | Stage 8 | 9 |
| `layout_types` | List[LayoutType dict] | Stage 9 (atualizado por 10,11,16) | 20,27,28 |
| `alignment_offsets` | Dict | Stage 12 | 13 |
| `intelligence_metadata` | Dict | Stage 12 | 13,14,15,16 |
| `intelligence` | Dict | Stage 16 | 25,28 |
| `tables` | List[DetectedTable dict] | Stage 17 (atualizado por 18) | 19,22,26 |
| `visual_analysis` | Dict | Stage 20 (atualizado por 21,22) | 25,28 |
| `vision_unavailable` | bool | Stage 20 | 21 |
| `vision_validation` | Dict | Stage 22 | — |
| `field_mappings` | List[dict] | Stage 23 (atualizado por 24) | 25,26,27,28 |
| `ambiguous_fields` | List[str] | Stage 23 | 28 |
| `field_matching_skipped` | bool | Stage 23 | — |
| `format_functions` | Dict | Stage 24 | 28 |
| `confidence_scores` | Dict | Stage 25 | 28 |
| `validation_result` | Dict | Stage 26 | 28 |
| `template_draft` | Dict | Stage 27 | 28 |
| `result_json` | PipelineResult | Stage 28 | Router |

### Keys internas (prefixo _ — não serializar)

| Key | Tipo | Produtor | Consumidores |
|-----|------|----------|-------------|
| `_skeleton_objects` | List[LayoutSkeleton] | Stage 7 | 8,9,12,13,14,15 |
| `_layout_type_objects` | List[LayoutType] | Stage 9 | 10,11,12,13,14,15,16 |
| `_element_labels` | Dict | Stage 13 | 14,16 |
| `_stability_map` | Dict | Stage 14 | 15,16 |
| `_variants` | Dict | Stage 15 | 16,27 |
| `_conditional_sections` | Dict | Stage 15 | 16 |
| `_aligned` | bool | Stage 12 | — |
| `_vision_api_calls` | int | Stages 20-22 | — |

---

## 6. Frontend — Contrato Esperado

### PipelineResult (`frontend/src/types/pipeline.types.ts`)

```typescript
interface PipelineResult {
  document_structure: DocumentTree
  field_mappings: FieldMappingEntry[]
  confidence_scores: Record<string, ConfidenceFactors>
  coverage: Record<string, CoverageData>
  layout_types: LayoutType[]
  template_draft: { html: string; css: string }
  ambiguous_fields: AmbiguousField[]
  format_functions: FormatFunction[]
  overlay_items?: Record<string, BackendOverlayItem[]>
  document_type?: string
}
```

### TreeNode (`frontend/src/types/template.types.ts`)

```typescript
type NodeType = 'document' | 'header' | 'footer' | 'flow' | 'section' |
                'table' | 'chart' | 'image' | 'container' | 'text' |
                'field' | 'barcode'

interface TreeNode {
  id: string
  type: NodeType
  name: string
  binding?: string
  isOptional?: boolean
  children: TreeNode[]
  properties: NodeProperties    // Record<string, unknown>
  visibility: boolean
}

interface DocumentTree {
  root: TreeNode
}
```

---

## 7. Performance Atual (100 páginas, 2 templates)

| Fase | Páginas processadas | Tempo estimado |
|------|--------------------|---------:|
| Text Extraction (Stage 2) | 100 | ~1s |
| Text Reconstruction (Stage 3) | 100 | ~2s |
| Font Extraction (Stage 4) | 100 | ~1s |
| Image Extraction (Stage 5) | 100 | ~3s |
| Grid Detection (Stage 6) | 100 | ~1s |
| Screenshots (Stage 2b) | 50 (sampled) | ~25s |
| Skeleton → Clustering (7-9) | 100 | ~2s |
| Layout Intelligence (12-16) | All skeletons | ~3s |
| Table Detection (17-18) | 100 | ~5s |
| Semantic Analysis (19) | 100 | ~2s |
| Vision AI (20-22) | 2-4 screenshots | ~30s (API) |
| Field Matching (23) | **100 páginas** | **~15min (LLM)** |
| Format Detection (24) | All mappings | ~1s |
| Confidence + Validation (25-26) | All mappings | ~5s |
| Template Draft (27) | All | ~2s |
| Pipeline Result (28) | All | ~3s |
| **TOTAL** | | **~20 min** |
| **Se filtrasse para 6 representativas** | | **~2-3 min** |

---

## 8. Gaps Identificados

### 8.1 Gaps de Fluxo (dados não chegam onde deveriam)

| Produtor | Output | Deveria alimentar | Alimenta hoje |
|----------|--------|-------------------|---------------|
| Stages 20-22 | `visual_analysis.html_suggestion` | Stage 27 (Template Draft) | **Ninguém** |
| Stage 13 | `_element_labels` (label vs dynamic) | Stage 19 (Semantic Analysis) | **Ninguém** |
| Stage 9 | `layout_types` (representative pages) | Stages 17-23 (filtrar por representativas) | **Ninguém** — todos processam ALL pages |
| Stage 19c | `document_trees` (hierárquico) | Stage 28 (Pipeline Result) | **Não existe** |

### 8.2 Gaps de Abordagem (como está fazendo)

| Estágio | Abordagem Atual | Problema | Alternativa conhecida |
|---------|----------------|----------|----------------------|
| Stage 6 (Grid) | KMeans em coords X/Y | Precisa de k, clusters esféricos | DBSCAN eps=0.02 — sem k, clusters arbitrários |
| Stage 8 (Clustering) | KMeans + silhouette, k∈[2,8] | Assume clusters esféricos, requer range de k | Graph clustering com weighted similarity + NetworkX |
| Stage 8 (Features) | 5-dim feature vector bruto | Sem normalização de conteúdo | Content Abstraction — categorizar texto em DATE/NUMBER/TEXT antes de comparar |
| Stage 8 (Prep) | Sem remoção de ruído | Headers/footers repetitivos inflam similaridade | Header/Footer removal (blocos em >80% páginas) antes de clustering |
| Stage 9 (Selection) | Distância ao centróide | Sensível a outliers | Highest degree no grafo de similaridade |
| Stage 10 (Fingerprint) | Pós-clustering, não influencia | Fingerprint é output, não input | Fingerprint como input da similarity matrix |
| Stage 19 (Semantic) | `endswith(":")` para labels | Muitos labels não terminam com `:` | Usar intelligence._element_labels do Stage 13 |
| Stage 23 (Matching) | Adjacência: label à esquerda | Não detecta label acima do value | Expandir: esquerda + acima + inline |
| Stage 27 (Draft) | Spans flat posicionados | Tabelas viram spans, não `<table>` | Gerar `<table>` real do Stage 17/18 |
| Stage 28 (Tree) | Flat: todos blocos de todas páginas | 100 nós nível 1 para 100 páginas | Hierárquico por layout_type |
| Stage 28 (DocType) | Keywords ("boleto", "nota fiscal") | Frágil, sem cobertura | LLM ou heurísticas expandidas |

### 8.3 Gap Estrutural Principal

**O pipeline processa TODAS as páginas em quase todos os estágios.** O clustering (Stage 8) identifica que 100 páginas = 2 templates, mas nenhum estágio downstream usa essa informação para filtrar. Resultado:

- Stage 23 (Field Matching): ~3000 chamadas LLM em vez de ~60
- Stage 27 (Template Draft): gera HTML para todas as páginas
- Stage 28 (Pipeline Result): document tree com 100 nós flat

---

— Aria, arquitetando o futuro 🏗️
