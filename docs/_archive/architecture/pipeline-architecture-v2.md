# Arquitetura do Pipeline v2.0 — Redesign Completo

**Versão:** 2.0
**Data:** 2026-03-20
**Autor:** @architect (Aria)
**Status:** `reference` — design planejado (28 estágios nunca implementados). Para o pipeline real, ver `pipeline-real.md`
**Origem:** Gap analysis do @analyst (Atlas) + revisão completa de todos os 28 estágios

---

## Change Log

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0 | 2026-03-10 | Pipeline original — 28 estágios, 8 blocos |
| 2.0 | 2026-03-20 | Redesign — corrige 7 gaps críticos, introduz Representative Filter, reestrutura blocos 6-8 |
| 2.1 | 2026-03-20 | Light Scan First — split Bloco 2 em Light Scan (todas as páginas) + Deep Extraction (só representativas). Princípio: descobrir o que é diferente ANTES de extrair a fundo |
| 2.2 | 2026-04-13 | **Epic 43 — Pipeline Accuracy:** Stage 3 corrigido (17%→≥80% mapping). (1) Fix semantic misclassification — `_DYNAMIC_PATTERNS` para blocos VALUE curtos. (2) Tabela raster — Mistral OCR + PyMuPDF font/color + PIL per-row sampling. (3) image_area handler — heurística PIL barcode/logo, `image_area` não mais descartada. Ver detalhes: `pipeline-stage3-epic43.md` |
| 2.3 | 2026-04-13 | **Epic 46.2 — GPT-4o Vision eliminado do Stage 3.2:** Mistral OCR chamado incondicionalmente por página representativa (`pages=[page_index]`). PyMuPDF (`get_image_bbox`) fornece bbox exato de imagens raster ($0). Custo Stage 3.2: $0.010–0.012/cluster → $0.001/cluster. Fallback threshold-based ativado por `MISTRAL_API_KEY` ausente (não mais `VISION_AI_ENABLED`). |

---

## 1. Problema

O pipeline v1 detecta layout types (templates) via clustering mas **nenhum estágio downstream usa essa informação**. Resultado: para um PDF de 100 páginas com 2 templates reais, o pipeline processa 100 páginas em vez de ~6, faz ~3000 chamadas LLM em vez de ~60, e gera output com duplicatas.

Além disso, 3 estágios de Vision AI (20-22) gastam API mas seu output é **ignorado** pelo template draft e pelo resultado final.

---

## 2. Princípios de Design

| Princípio | Descrição |
|-----------|-----------|
| **Light-Scan-First** | Descubra o que é diferente ANTES de extrair a fundo. Scan leve de todas as páginas → clustering → extração profunda só das representativas |
| **Representative-First** | Após clustering, todos os estágios de análise operam apenas sobre páginas representativas |
| **Contracts-Over-Convention** | Cada estágio documenta explicitamente o que lê e escreve no context |
| **Visual-Integrated** | Saídas de Vision AI alimentam o template draft e o document tree |
| **Layout-Scoped** | Resultados downstream são indexados por layout_type_id |
| **Fail-Graceful** | Cada estágio produz output válido mesmo quando dependências opcionais falham |

---

## 3. Pipeline v2.1 — Visão Geral

### Filosofia: Light Scan First

> "Não extraia tudo de 100 páginas para depois descobrir que só tem 2 templates.
> Descubra o que é diferente PRIMEIRO. Depois extraia a fundo só o que importa."

O pipeline v1 fazia:
```
Extrair TUDO (100 páginas) → Clustering → Trabalhar com tudo
```

O pipeline v2.1 faz:
```
Scan leve (100 páginas) → Clustering → Filtrar representativas → Extrair a fundo (6 páginas)
```

### Diagrama Completo

```
PDF(s) + XSD
    │
    ▼
┌─ BLOCO 1: Aquisição (2 estágios) ─────────────────────┐
│  Stage 1: Upload & Storage                              │
│  Stage 1b: XSD Parsing                                  │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─ BLOCO 2a: Light Scan — TODAS as páginas ─────────────┐
│  (rápido — só PyMuPDF nativo, sem reconstrução,        │
│   sem imagens, sem screenshots)                         │
│                                                         │
│  Stage 2: Text Extraction (texto + bbox + font_size)    │
│  Stage 6: Grid Detection (colunas/linhas)               │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─ BLOCO 3: Layout Discovery ───────────────────────────┐
│  Stage 7: Skeleton Builder                              │
│  Stage 8: Page Clustering (KMeans)                      │
│  Stage 9: Representative Selection                      │
└─────────────────────────────────────────────────────────┘
    │
    ▼
══════════════════════════════════════════════════════════
  ★ REPRESENTATIVE FILTER (NOVO — Stage 9.5)
  Filtra parsed_documents para manter apenas as páginas
  representativas + secundárias de cada cluster.
    context["representative_documents"] ← filtrado (~6 páginas)
    context["all_parsed_documents"]     ← backup (100 páginas)
══════════════════════════════════════════════════════════
    │
    ▼
┌─ BLOCO 2b: Deep Extraction — SÓ representativas ─────┐
│  (caro — reconstrução, fontes CSS, imagens, PNGs)      │
│                                                         │
│  Stage 3: Text Reconstruction  ← SÓ representativas    │
│  Stage 4: Font Extraction → CSS ← SÓ representativas   │
│  Stage 5: Image Extraction     ← SÓ representativas    │
│  Stage 2b: Screenshot Generator ← SÓ representativas   │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─ BLOCO 4: Layout Intelligence (5 estágios) ───────────┐
│  Stage 10: Fingerprint Generation                       │
│  Stage 11: Registry Lookup                              │
│  Stage 12: Layout Alignment                             │
│  Stage 13: Multi-Example Analysis                       │
│  Stage 14: Stability Classification                     │
│  Stage 15: Variant Detection                            │
│  Stage 16: Intelligence Normalization                   │
│  (já opera sobre layout_type_objects — sem mudança)     │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─ BLOCO 5: Tables — SÓ representativas ────────────────┐
│  Stage 17: Table Detection                              │
│  Stage 18: Table Structuring                            │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─ BLOCO 6: Análise Semântica — SÓ representativas ─────┐
│  Stage 19: Semantic Analysis                            │
│  Stage 19b: Document Type Detection (NOVO)              │
│  Stage 19c: Hierarchy Builder (NOVO)                    │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─ BLOCO 7: Vision AI — OPCIONAL, SÓ representativas ───┐
│  Stage 20: Visual Segmentation                          │
│  Stage 21: Visual Interpretation                        │
│  Stage 22: Vision Self-Check                            │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─ BLOCO 8: Matching — SÓ representativas ──────────────┐
│  Stage 23: Field Matching                               │
│  Stage 24: Format Detection                             │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─ BLOCO 9: Validação & Output ─────────────────────────┐
│  Stage 25: Confidence Scoring                           │
│  Stage 26: Layout Consistency                           │
│  Stage 27: Template Draft       ← REESCRITO            │
│  Stage 28: Pipeline Result      ← REESCRITO            │
└─────────────────────────────────────────────────────────┘
    │
    ▼
  PipelineResult → Frontend Editor
```

---

## 4. Mudanças vs. Pipeline v1

| Mudança | Tipo | Justificativa |
|---------|------|---------------|
| **Bloco 2 split em 2a + 2b** | **REESTRUTURADO** | Light Scan (todas) antes de clustering; Deep Extraction (representativas) depois. Princípio: descubra o que é diferente ANTES de extrair a fundo |
| Stage 9.5: Representative Filter | **NOVO** | Filtra parsed_documents para representative pages — separa os dois mundos |
| Stages 3, 4, 5, 2b movidos para Bloco 2b | **MOVIDOS** | Executam DEPOIS do clustering, só nas ~6 páginas representativas em vez de 100 |
| Stage 19b: Document Type Detection | **NOVO** | Detecção dedicada usando LLM + heurísticas (substitui keyword matching do Stage 28) |
| Stage 19c: Hierarchy Builder | **NOVO** | Agrupa blocos flat em estrutura hierárquica (seções, tabelas, containers) |
| Stage 27: Template Draft | **REESCRITO** | Integra visual_interpretations, gera tabelas reais, coverage multidimensional |
| Stage 28: Pipeline Result | **REESCRITO** | Document tree hierárquico, resultados por layout_type, coverage completo |
| Stages 17-19, 23: filtro | **MODIFICADO** | Operam sobre `representative_documents` em vez de `parsed_documents` |

### Por que o Bloco 2 foi dividido

O clustering (Stage 8) precisa de apenas **2 dados** por página:
- **Texto + bbox** → `num_blocks`, `avg_font_size`, `text_density` (Stage 2 — PyMuPDF nativo, ~0.5s para 100 páginas)
- **Grid info** → `table_count` (Stage 6 — clustering de coordenadas, ~0.3s para 100 páginas)

O clustering **NÃO precisa** de:
- Text Reconstruction (Stage 3) — merging de spans fragmentados, O(n²)
- Font → CSS (Stage 4) — mapeamento de fontes para CSS families
- Image Extraction (Stage 5) — renderiza e salva imagens no disco
- Screenshots (Stage 2b) — renderiza PNGs a 150 DPI

Esses 4 estágios são os mais caros do Bloco 2 e agora rodam DEPOIS do filtro, em ~6 páginas em vez de 100.

---

## 5. Contratos por Estágio

### BLOCO 1 — Aquisição

#### Stage 1: Upload & Storage

| Campo | Valor |
|-------|-------|
| **Lê** | HTTP request (multipart: PDFs, XSD, data files) |
| **Escreve** | `context["job_id"]` ← UUID v4 |
| | `context["tmp_base"]` ← Path base |
| | Disco: `/tmp/jobs/{job_id}/input.pdf`, `input_2.pdf`, ... |
| | Disco: `/tmp/jobs/{job_id}/schema.xsd` (se presente) |
| **Garante** | Pelo menos 1 PDF existe no disco |

#### Stage 1b: XSD Parsing (atual Stage 29)

| Campo | Valor |
|-------|-------|
| **Lê** | `context["job_id"]`, `context["tmp_base"]` → procura `schema.xsd` |
| **Escreve** | `context["field_tree"]` ← `{ root_nodes: [...], flat_paths: string[] }` |
| | `context["xsd_path"]` ← caminho do arquivo |
| **Garante** | Se XSD não existe → `field_tree = None` (não falha) |
| **Contrato de saída** | `flat_paths` contém todos os caminhos XSD em notação dot (ex: `cliente.nome`, `itens[].valor`) |

---

### BLOCO 2a — Light Scan (TODAS as páginas)

> Objetivo: extrair o mínimo necessário para clustering. Rápido (~1-2s para 100 páginas).

#### Stage 2: Text Extraction

| Campo | Valor |
|-------|-------|
| **Lê** | `context["job_id"]`, `context["tmp_base"]` |
| **Escreve** | `context["parsed_documents"]` ← `List[ParsedDocumentDict]` |
| **ParsedDocumentDict** | `{ job_id, pdf_index, pdf_name, pages: [ParsedPageDict] }` |
| **ParsedPageDict** | `{ page_number, width, height, text_blocks: [TextBlockDict] }` |
| **TextBlockDict** | `{ text, bbox: [x0,y0,x1,y1], font_name, font_size, page_number, pdf_index, id }` |
| **Garante** | Cada TextBlock tem `bbox` válido (4 floats) e `id` único |
| **Nota** | Sem mudança de código — PyMuPDF é rápido. Output é "leve" (sem images, sem fonts CSS, sem screenshots) |

#### Stage 6: Grid Detection

| Campo | Valor |
|-------|-------|
| **Lê** | `context["parsed_documents"]` |
| **Escreve** | `context["parsed_documents"]` ← atualizado com `grid_info` por página |
| **GridInfo** | `{ column_count, row_count, column_positions: float[], row_positions: float[] }` |
| **Nota** | Precisa rodar antes do clustering pois `table_count` é feature do KMeans |

---

### BLOCO 2b — Deep Extraction (SÓ representativas)

> Objetivo: enriquecer apenas as ~6 páginas representativas com dados caros.
> Roda DEPOIS do Representative Filter (Stage 9.5).

#### Stage 3: Text Reconstruction

| Campo | Valor |
|-------|-------|
| **Lê** | `context["representative_documents"]` ← **MUDOU** |
| **Escreve** | `context["representative_documents"]` ← atualizado (blocos fragmentados mesclados) |
| **Garante** | Blocos adjacentes com mesma fonte e Y-próximo são mesclados em um único bloco |

#### Stage 4: Font Extraction → CSS

| Campo | Valor |
|-------|-------|
| **Lê** | `context["representative_documents"]` ← **MUDOU** |
| **Escreve** | `context["representative_documents"]` ← atualizado com `fonts: [CSSFont]` por página |
| **CSSFont** | `{ family, size, weight, style, original_name }` |

#### Stage 5: Image Extraction

| Campo | Valor |
|-------|-------|
| **Lê** | `context["job_id"]`, `context["tmp_base"]`, `context["representative_documents"]` ← **MUDOU** |
| **Escreve** | `context["representative_documents"]` ← atualizado com `images: [ParsedImage]` por página |
| | Disco: `/tmp/jobs/{job_id}/assets/img_*.png` (só ~6 páginas) |
| **ParsedImage** | `{ path, bbox: [x0,y0,x1,y1], width, height, page_number, pdf_index }` |

#### Stage 2b: Screenshot Generator

| Campo | Valor |
|-------|-------|
| **Lê** | `context["job_id"]`, `context["tmp_base"]`, `context["representative_documents"]` ← **MUDOU** |
| **Escreve** | `context["representative_documents"]` ← atualizado com `screenshot_path` por página |
| | Disco: `/tmp/jobs/{job_id}/screenshots/page_{pdf}_{page}.png` (só ~6 páginas) |
| **Garante** | Renderiza APENAS as páginas representativas (não precisa de sampling) |

---

### BLOCO 3 — Layout Discovery

#### Stage 7: Skeleton Builder

| Campo | Valor |
|-------|-------|
| **Lê** | `context["parsed_documents"]` |
| **Escreve** | `context["skeletons"]` ← `List[LayoutSkeletonDict]` |
| | `context["_skeleton_objects"]` ← `List[LayoutSkeleton]` (Python objects) |
| **LayoutSkeletonDict** | `{ page_number, pdf_index, text_blocks, table_candidates, zones, grid_info, page_width, page_height }` |
| **Feature vector** | `[num_blocks, avg_font_size, table_count, text_density, header_height_ratio]` |

#### Stage 8: Page Clustering

| Campo | Valor |
|-------|-------|
| **Lê** | `context["_skeleton_objects"]` |
| **Escreve** | `context["cluster_labels"]` ← `List[int]` (um label por skeleton) |
| **Algoritmo** | KMeans com silhouette score, k ∈ [2, min(8, n_pages)] |
| **Garante** | PDFs > 500 páginas → amostra ~50 para fitting, predict no resto |

#### Stage 9: Representative Selection

| Campo | Valor |
|-------|-------|
| **Lê** | `context["_skeleton_objects"]`, `context["cluster_labels"]` |
| **Escreve** | `context["layout_types"]` ← `List[LayoutTypeDict]` |
| | `context["_layout_type_objects"]` ← `List[LayoutType]` |
| **LayoutTypeDict** | `{ id, cluster_id, name, representative_page: {pdf_index, page_number}, page_count, pages: [{pdf_index, page_number}] }` |
| **Garante** | 1 representative_page por cluster + até 2 secundárias |

#### ★ Stage 9.5: Representative Filter (NOVO)

| Campo | Valor |
|-------|-------|
| **Lê** | `context["parsed_documents"]`, `context["layout_types"]` |
| **Escreve** | `context["representative_documents"]` ← `List[ParsedDocumentDict]` (filtrado) |
| | `context["all_parsed_documents"]` ← backup do `parsed_documents` original |
| **Lógica** | Para cada layout_type, coleta representative_page + secondary_pages. Cria um parsed_documents reduzido contendo APENAS essas páginas (tipicamente 2-6 páginas no total). |
| **Garante** | `representative_documents` contém no mínimo 1 página por layout_type |
| **Impacto** | Todos os estágios a partir daqui que lêem `parsed_documents` passam a ler `representative_documents` |

#### Stage 10: Fingerprint Generation

| Campo | Valor |
|-------|-------|
| **Lê** | `context["_layout_type_objects"]` |
| **Escreve** | `context["layout_types"]` ← atualizado com `fingerprint` e `fingerprint_hash` |
| **Fingerprint** | `{ table_count, column_count, header_blocks, body_zone_ratio, footer_present }` |

#### Stage 11: Registry Lookup

| Campo | Valor |
|-------|-------|
| **Lê** | `context["_layout_type_objects"]` (fingerprint_hash) |
| **Escreve** | `context["layout_types"]` ← atualizado com `is_reusable`, `template_id` |
| **Dependência** | Supabase (opcional — não bloqueia se indisponível) |

---

### BLOCO 4 — Layout Intelligence

> **Nota:** Estágios 12-16 já operam sobre `_layout_type_objects` e `_skeleton_objects`.
> Não precisam de mudança — já são layout-scoped.

#### Stage 12: Layout Alignment

| Campo | Valor |
|-------|-------|
| **Lê** | `context["_layout_type_objects"]`, `context["_skeleton_objects"]` |
| **Escreve** | `context["alignment_offsets"]` ← `Dict[cluster_id → Dict[pdf_index → (dx, dy)]]` |
| | `context["intelligence_metadata"]` ← `{ single_document: bool }` |

#### Stage 13: Multi-Example Analysis

| Campo | Valor |
|-------|-------|
| **Lê** | `context["_layout_type_objects"]`, `context["_skeleton_objects"]`, `context["alignment_offsets"]` |
| **Escreve** | `context["_element_labels"]` ← `Dict[cluster_id → List[{bbox_key, text_samples, classification, confidence}]]` |
| **classification** | `"label"` (texto estático) \| `"dynamic"` (texto que varia entre PDFs) |

#### Stage 14: Stability Classification

| Campo | Valor |
|-------|-------|
| **Lê** | `context["_element_labels"]`, `context["_layout_type_objects"]`, `context["intelligence_metadata"]` |
| **Escreve** | `context["_stability_map"]` ← `Dict[cluster_id → Dict[bbox_key → {classification, stability_score, doc_count}]]` |
| **classification** | `"stable"` \| `"variable"` \| `"absent"` \| `"unknown"` |

#### Stage 15: Variant Detection

| Campo | Valor |
|-------|-------|
| **Lê** | `context["_stability_map"]`, `context["_element_labels"]`, `context["_layout_type_objects"]` |
| **Escreve** | `context["_variants"]` ← `Dict[cluster_id → List[{type, elements, presence_pattern}]]` |
| | `context["_conditional_sections"]` ← `Dict[cluster_id → List[section]]` |
| **variant.type** | `"optional_field"` \| `"conditional_section"` \| `"dynamic_table"` |

#### Stage 16: Intelligence Normalization

| Campo | Valor |
|-------|-------|
| **Lê** | Todos os outputs dos Stages 12-15 |
| **Escreve** | `context["intelligence"]` ← `Dict[cluster_id → {labels, dynamic_fields, stability_map, variants, conditional_sections, metadata}]` |
| | `context["layout_types"]` ← re-serializado com intelligence metadata |

---

### BLOCO 5 — Tables

#### Stage 17: Table Detection (MODIFICADO)

| Campo | Valor |
|-------|-------|
| **Lê** | `context["representative_documents"]` ← **MUDOU** (era parsed_documents) |
| **Escreve** | `context["tables"]` ← `List[DetectedTableDict]` |
| **DetectedTableDict** | `{ page_number, pdf_index, bbox, headers, rows, columns, table_id, is_multi_page }` |

#### Stage 18: Table Structuring

| Campo | Valor |
|-------|-------|
| **Lê** | `context["tables"]`, `context["representative_documents"]` ← **MUDOU** |
| **Escreve** | `context["tables"]` ← atualizado com headers/rows refinados |

---

### BLOCO 6 — Análise Semântica + Tipo

#### Stage 19: Semantic Analysis (MODIFICADO)

| Campo | Valor |
|-------|-------|
| **Lê** | `context["representative_documents"]` ← **MUDOU** (era parsed_documents) |
| | `context["tables"]` |
| **Escreve** | `context["representative_documents"]` ← atualizado com `semantic_label` em cada TextBlock |
| **Labels** | `label`, `value`, `title`, `header`, `footer_text`, `page_number`, `table_header`, `table_cell`, `field` |
| **Lógica** | Sem mudança na classificação. Apenas opera sobre documentos filtrados. |

#### ★ Stage 19b: Document Type Detection (NOVO)

| Campo | Valor |
|-------|-------|
| **Lê** | `context["representative_documents"]` (texto completo) |
| | `context["visual_analysis"]` (opcional, se Vision rodou antes) |
| **Escreve** | `context["document_type"]` ← `string` (ex: `"boleto-bancario"`, `"nota-fiscal"`, `"recibo"`, `"contrato"`, `"extrato"`, `"documento-geral"`) |
| | `context["document_type_confidence"]` ← `float` (0.0-1.0) |
| **Lógica** | 1. Tenta LLM (enviar texto dos primeiros 2 blocos de cada página representativa). 2. Se sem API key, usa heurísticas expandidas (keywords + layout features: tem tabela? tem código de barras? tem assinatura?). 3. Resultado é atômico — um tipo por documento. |
| **Contrato** | Sempre produz um `document_type` válido (fallback: `"documento-geral"`) |

#### ★ Stage 19c: Hierarchy Builder (NOVO)

| Campo | Valor |
|-------|-------|
| **Lê** | `context["representative_documents"]` (com semantic_label) |
| | `context["tables"]` |
| | `context["layout_types"]` |
| **Escreve** | `context["document_trees"]` ← `Dict[layout_type_id → HierarchicalTree]` |
| **HierarchicalTree** | Estrutura hierárquica onde: |
| | - Nó raiz `type: "document"` |
| | - Filhos: `type: "page"` (1 por página representativa do layout) |
| | - Dentro de page: `type: "header"`, `type: "flow"`, `type: "footer"` (zonas) |
| | - Dentro de zona: `type: "section"` (agrupamento por proximidade Y) |
| | - Dentro de section: `type: "field"`, `type: "text"`, `type: "table"`, `type: "image"` |
| **Lógica** | 1. Particiona blocos por zona (header 15%, footer 10%, flow resto). 2. Dentro de cada zona, agrupa blocos adjacentes (Y-gap > 20px = nova seção). 3. Para tabelas detectadas: cria nó `table` com filhos `table_header` e `table_row`. 4. Para imagens: cria nó `image`. 5. Cada nó preserva `bbox`, `semantic_label`, `properties`. |
| **Contrato** | Output é um `Dict[layout_type_id → TreeNode]` — cada layout type tem sua própria árvore. O editor recebe árvores separadas por template, não uma lista flat de 100 páginas. |

---

### BLOCO 7 — Vision AI (Opcional)

> **Nota:** Estágios 20-22 permanecem sem mudança interna.
> A integração dos seus outputs acontece nos Stages 27 e 28.

#### Stage 20: Visual Segmentation

| Campo | Valor |
|-------|-------|
| **Lê** | `context["layout_types"]`, `context["representative_documents"]`, `context["job_id"]` |
| **Escreve** | `context["visual_analysis"]` ← `Dict[page_key → { visual_regions, visual_interpretations: [], consistency_score: null }]` |
| **Dependência** | OpenRouter API (GPT-4o). Se indisponível → `context["vision_unavailable"] = True` |

#### Stage 21: Visual Interpretation

| Campo | Valor |
|-------|-------|
| **Lê** | `context["visual_analysis"]`, `context["representative_documents"]` |
| **Escreve** | `context["visual_analysis"][page_key]["visual_interpretations"]` ← `List[{ region_type, description, html_suggestion }]` |

#### Stage 22: Vision Self-Check

| Campo | Valor |
|-------|-------|
| **Lê** | `context["visual_analysis"]`, `context["representative_documents"]`, `context["tables"]` |
| **Escreve** | `context["visual_analysis"]` ← atualizado com `consistency_score`, `consistency_level` por página |
| | `context["vision_validation"]` ← `{ overall_score, page_results, low_confidence_pages }` |

---

### BLOCO 8 — Matching

#### Stage 23: Field Matching (MODIFICADO)

| Campo | Valor |
|-------|-------|
| **Lê** | `context["representative_documents"]` ← **MUDOU** (era parsed_documents) |
| | `context["field_tree"]` |
| **Escreve** | `context["field_mappings"]` ← `List[FieldMappingDict]` |
| | `context["ambiguous_fields"]` ← `List[string]` |
| **FieldMappingDict** | `{ pdf_text, label_text, xsd_field_path, confidence, is_ambiguous, candidates, page_number, pdf_index, bbox, name, path, type, status, isOptional, layout_type_id }` |
| **Mudança** | Cada mapping agora inclui `layout_type_id` indicando a qual template pertence |
| **Impacto** | Para 100 páginas / 2 templates: processa ~6 páginas representativas → ~60 chamadas LLM em vez de ~3000 |

#### Stage 24: Format Detection

| Campo | Valor |
|-------|-------|
| **Lê** | `context["field_mappings"]` |
| **Escreve** | `context["field_mappings"]` ← atualizado com `detected_format` |
| | `context["format_functions"]` ← `Dict[format_name → js_function_string]` |
| **Sem mudança** | Já opera sobre field_mappings (que agora são reduzidos) |

---

### BLOCO 9 — Validação & Output

#### Stage 25: Confidence Scoring

| Campo | Valor |
|-------|-------|
| **Lê** | `context["field_mappings"]`, `context["representative_documents"]`, `context["intelligence"]`, `context["visual_analysis"]` |
| **Escreve** | `context["confidence_scores"]` ← `Dict[layout_type_id → ConfidenceFactors]` |
| **Mudança** | Já lê `visual_analysis` para `vision_agreement`. Agora indexa por `layout_type_id` em vez de struct flat. |

#### Stage 26: Layout Consistency

| Campo | Valor |
|-------|-------|
| **Lê** | `context["field_mappings"]`, `context["field_tree"]`, `context["representative_documents"]`, `context["tables"]` |
| **Escreve** | `context["validation_result"]` ← `{ warnings, errors, orphan_count, unmapped_xsd_fields }` |
| **Sem mudança** | Lógica de validação permanece igual |

#### Stage 27: Template Draft (REESCRITO)

| Campo | Valor |
|-------|-------|
| **Lê** | `context["layout_types"]` |
| | `context["field_mappings"]` (agora com `layout_type_id`) |
| | `context["field_tree"]` |
| | `context["document_trees"]` ← **NOVO** (do Stage 19c) |
| | `context["visual_analysis"]` ← **NOVO** (html_suggestion do Stage 21) |
| | `context["tables"]` ← **NOVO** (para gerar `<table>` real) |
| | `context["_variants"]` (condicionais do Stage 15) |
| **Escreve** | `context["template_draft"]` ← `Dict[layout_type_id → { html, css }]` |
| | `context["coverage"]` ← `Dict[layout_type_id → CoverageData]` |

**Mudanças no Template Draft:**

| Aspecto | v1 (atual) | v2 (novo) |
|---------|------------|-----------|
| HTML structure | `<span>` flat posicionados | Hierárquico: page > zones > sections > elements |
| Tables | Ignoradas (blocos soltos) | `<table>` real com `<thead>`, `<tbody>`, `<!-- ko foreach -->` |
| Visual AI | Não usado | `html_suggestion` das interpretations é incorporado como fallback |
| Coverage | Só fields | Fields + Tables + Images + Charts |
| Output | Um HTML para todos | Um `{html, css}` **por layout_type** |
| Condicionais | `<!-- ko if -->` vazio | Condicionais reais dos variants |

**CoverageData v2:**
```typescript
interface CoverageData {
  fields: { mapped: number; total: number }
  tables: { mapped: number; total: number }    // <— NOVO: contabiliza tabelas
  images: { mapped: number; total: number }    // <— NOVO: contabiliza imagens
  charts: { mapped: number; total: number }    // <— futuro
  percentage: number                            // weighted average
}
```

**Lógica de coverage:**
- `fields.total` = `field_tree.flat_paths.length` (do XSD)
- `fields.mapped` = field_mappings com `xsd_field_path` preenchido
- `tables.total` = número de tabelas detectadas no layout
- `tables.mapped` = tabelas com pelo menos 1 célula mapeada ao XSD
- `images.total` = imagens extraídas no layout
- `images.mapped` = imagens com binding ou referência

#### Stage 28: Pipeline Result (REESCRITO)

| Campo | Valor |
|-------|-------|
| **Lê** | Todos os outputs dos estágios anteriores |
| **Escreve** | `context["result_json"]` ← `PipelineResult` (contrato final) |

**PipelineResult v2:**
```typescript
interface PipelineResult {
  // --- MANTIDOS (mesma interface, dados melhores) ---
  field_mappings: FieldMappingEntry[]          // agora com layout_type_id
  confidence_scores: Record<string, ConfidenceFactors>  // por layout_type_id
  layout_types: LayoutType[]
  ambiguous_fields: AmbiguousField[]
  format_functions: FormatFunction[]
  overlay_items: Record<string, BackendOverlayItem[]>   // por layout_type_id

  // --- MODIFICADOS ---
  document_structure: {
    pages: SimplifiedPage[]                     // resumo das páginas
    layout_types: LayoutType[]
    root: TreeNode                              // <— MUDOU: hierárquico por layout
    trees_by_layout: Record<string, TreeNode>   // <— NOVO: árvore por layout
  }
  template_draft: Record<string, { html: string; css: string }>  // <— MUDOU: por layout_type_id
  coverage: Record<string, CoverageData>        // <— MUDOU: multidimensional
  document_type: string                         // <— MUDOU: do Stage 19b (confiável)
  document_type_confidence: number              // <— NOVO

  // --- NOVOS ---
  visual_analysis?: Record<string, VisualPageAnalysis>  // <— NOVO: exposto ao frontend
  intelligence?: Record<string, IntelligenceData>       // <— NOVO: exposto ao frontend
}
```

---

## 6. Fluxo de Dados — Diagrama de Dependências

```
                    ┌──────────┐
                    │  Upload  │
                    │ Stage 1  │
                    └────┬─────┘
                         │ job_id, PDFs on disk
                    ┌────▼─────┐
                    │   XSD    │
                    │ Stage 1b │
                    └────┬─────┘
                         │ field_tree (flat_paths)
                    ┌────▼─────┐
                    │ LIGHT    │  ← TODAS as páginas (rápido)
                    │ SCAN     │
                    │  2 + 6   │  Text + bbox + grid
                    └────┬─────┘
                         │ parsed_documents (100 páginas, dados leves)
                    ┌────▼─────┐
                    │ Cluster  │
                    │  7-8-9   │  Skeleton → KMeans → Representatives
                    └────┬─────┘
                         │ layout_types + cluster_labels
               ┌─────────▼──────────┐
               │  ★ REP FILTER 9.5  │
               │  100 → ~6 páginas  │
               └─────────┬──────────┘
                         │ representative_documents (~6 páginas)
                    ┌────▼─────┐
                    │ DEEP     │  ← SÓ representativas
                    │ EXTRACT  │
                    │ 3,4,5,2b │  Reconstruct + Fonts + Images + Screenshots
                    └────┬─────┘
                         │ representative_documents (enriquecidos)
          ┌──────────────┼───────────────┐
          │              │               │
     ┌────▼────┐   ┌────▼────┐    ┌─────▼─────┐
     │ Layout  │   │ Tables  │    │ Semantic  │
     │ Intel   │   │  17-18  │    │  19,19b   │
     │ 10-16   │   └────┬────┘    │  19c      │
     └────┬────┘        │        └─────┬─────┘
          │         tables        semantic_label
          │              │        document_type
     intelligence        │        document_trees
          │              │               │
          │    ┌─────────▼───────────────▼──────┐
          │    │         Vision AI (opcional)    │
          │    │         20-21-22               │
          │    └─────────┬─────────────────────┘
          │              │ visual_analysis
          │              │
     ┌────▼──────────────▼────┐
     │     Field Matching     │
     │        23-24           │
     └────────────┬───────────┘
                  │ field_mappings (por layout_type)
     ┌────────────▼───────────┐
     │    Validation & Output │
     │       25-26-27-28      │
     └────────────┬───────────┘
                  │
                  ▼
            PipelineResult
```

---

## 7. Impacto de Performance

| Métrica | Pipeline v1 (100 páginas) | Pipeline v2.1 (100 páginas) |
|---------|--------------------------|--------------------------|
| Light Scan (text+bbox+grid) | 100 páginas | 100 páginas (rápido: ~1s) |
| Deep Extraction (reconstruct, fonts, images, screenshots) | **100 páginas** | **~6 páginas** |
| Semantic Analysis | 100 páginas | ~6 páginas |
| Table Detection | 100 páginas | ~6 páginas |
| Chamadas LLM (Field Matching) | **~3000** | **~60** |
| Chamadas Vision AI | ~2-4 | ~2-4 (sem mudança) |
| Tempo total estimado | ~15-30 min | **~2-4 min** |
| Custo API estimado | ~$3-5 | **~$0.30-0.50** |

### Por que Light Scan é rápido

PyMuPDF (`fitz`) é escrito em C. `page.get_text("dict")` para 100 páginas A4 leva ~0.5-1s.
Grid Detection (Stage 6) é clustering de coordenadas — ~0.3s para 100 páginas.
**Total do Light Scan: ~1-2 segundos para 100 páginas.**

O custo real está na Deep Extraction:
- Screenshot rendering (150 DPI): ~0.5s por página
- Image extraction: ~0.3s por página
- Text Reconstruction (O(n²) span merging): ~0.2s por página

Com 100 páginas = ~100s. Com 6 representativas = ~6s.

---

## 8. Ordem de Implementação Recomendada

| Prioridade | Mudança | Justificativa |
|------------|---------|---------------|
| **P0** | Stage 9.5 (Representative Filter) | O corte central: sem ele, nada muda |
| **P0** | Bloco 2 split (mover Stages 3,4,5,2b para depois do filtro) | Light Scan First — sem extrair tudo antes de saber o que é diferente |
| **P0** | Stages 3,4,5,2b,17,18,19,23 mod (ler representative_documents) | Acompanha P0 — todas as leituras de parsed_documents precisam mudar |
| **P1** | Stage 19c (Hierarchy Builder) | Resolve document tree flat — impacta UX do editor |
| **P1** | Stage 27 rewrite (Template Draft) | Integra visual, tabelas reais, coverage multidimensional |
| **P1** | Stage 28 rewrite (Pipeline Result) | Adequa o contrato final ao novo formato |
| **P2** | Stage 19b (Document Type Detection) | Melhora qualidade da detecção de tipo |
| **P3** | Coverage multidimensional | Contabiliza tables/images/charts |

---

## 9. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Representative Filter perde informação relevante | Média | Alto | Manter `all_parsed_documents` no context; secondary representatives cobrem variações |
| Hierarchy Builder cria agrupamentos incorretos | Média | Médio | Thresholds configuráveis; visual_interpretations como validação cruzada |
| Template Draft v2 quebra frontend existente | Alta | Alto | Manter backward-compatible: se frontend recebe `template_draft` como Dict, usa primeiro layout; migrar frontend em paralelo |
| Document Type Detection consome API extra | Baixa | Baixo | Fallback heurístico funciona sem API |

---

## 10. Compatibilidade Frontend

O `PipelineResult` v2 é **backward-compatible** com extensões:

| Campo | v1 (atual) | v2 (novo) | Frontend Impact |
|-------|------------|-----------|-----------------|
| `template_draft` | `{html, css}` | `Record<layoutId, {html, css}>` | Frontend precisa ler primeiro layout como fallback, depois migrar para multi-layout |
| `document_structure.root` | TreeNode flat | TreeNode hierárquico | Frontend já espera TreeNode — estrutura interna muda mas interface é a mesma |
| `document_structure.trees_by_layout` | Não existe | `Record<layoutId, TreeNode>` | Novo campo — frontend ignora até ser implementado |
| `coverage` | `{fields: {mapped, total}}` | `{fields, tables, images, charts, percentage}` | Frontend lê `fields` como antes; novos campos são additive |
| `visual_analysis` | Não exposto | `Record<pageKey, VisualPageAnalysis>` | Novo campo — frontend ignora até ser implementado |

---

— Aria, arquitetando o futuro 🏗️
