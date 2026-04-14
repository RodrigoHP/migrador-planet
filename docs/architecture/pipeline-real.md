# Pipeline Migrador Planet — Arquitetura Atual

**Versão:** 1.0
**Data:** 2026-04-13
**Status:** `current` — reflete o código em `backend/services/` hoje
**Dono:** `@architect` — atualiza a cada story que modifica stages
**Fonte:** `backend/services/stages/` — não os docs antigos
**Atualizar quando:** story modifica qualquer `backend/services/stages/stage*/`
**Última validação:** 2026-04-13 (Epic 46 — Vision Optimization concluído)

> Para contratos de dados entre stages (tipos Pydantic), ver `pipeline-contracts.md`.

---

## Princípios de Design

| Princípio | Descrição |
|-----------|-----------|
| **Light-Scan-First** | Descubra o que é diferente ANTES de extrair a fundo. Scan leve de todas as páginas → clustering → extração profunda só das representativas |
| **Representative-First** | Após clustering, todos os stages de análise operam apenas sobre páginas representativas — nunca sobre todas as páginas |
| **Contracts-Over-Convention** | Cada stage documenta explicitamente o que lê e escreve no context (ver `pipeline-contracts.md`) |
| **Visual-Integrated** | Saídas de Vision AI (Mistral OCR) alimentam o document tree e o template draft |
| **Layout-Scoped** | Resultados downstream são indexados por `layout_type_id` — cada cluster tem seu próprio output |
| **Fail-Graceful** | Cada stage produz output válido mesmo quando dependências opcionais falham |

---

## Visão Geral — 5 Stages

```
PDFs + XSD
    │
    ▼
┌── Stage 1: Layout Clustering ─────────────────────────────┐
│  Agrupa páginas com layout idêntico (3 camadas de defesa)  │
│  Saída: clusters[] + página representativa por cluster     │
└────────────────────────────────────────────────────────────┘
    │
    ▼
┌── Stage 2: Deep Extraction ───────────────────────────────┐
│  Extrai conteúdo COMPLETO das páginas representativas      │
│  Texto + fontes + imagens + tabelas vetoriais + screenshot │
└────────────────────────────────────────────────────────────┘
    │
    ▼
┌── Stage 3: Structural Analysis ───────────────────────────┐
│  3.1 Multi-Example Analysis (CPU, paralelo)                │
│  3.2 Visual Analysis — Mistral OCR + PyMuPDF (async, paralelo) │
│  3.3 Semantic Classification (sync, depende de 3.1+3.2)    │
│  3.4 Hierarchy Builder (sync, depende de 3.3)              │
│  Saída: document_trees[] com seções, barcodes, imagens     │
└────────────────────────────────────────────────────────────┘
    │
    ▼
┌── Stage 4: Field Mapping ─────────────────────────────────┐
│  XSD parsing → seção/XSD matching → Gemini Flash (LLM)    │
│  Saída: field_mappings[] com xsd_field_path por campo      │
└────────────────────────────────────────────────────────────┘
    │
    ▼
┌── Stage 5: Template Generation ───────────────────────────┐
│  Document tree → HTML + CSS (sem LLM)                      │
│  Barcodes, imagens, tabelas, campos dinâmicos              │
│  Saída: template_draft {html, css}, confidence_score       │
└────────────────────────────────────────────────────────────┘
    │
    ▼
  PipelineResult → Frontend Editor
```

---

## Stage 1 — Layout Clustering

**Arquivo:** `stage1_layout_clustering.py` + `stage1_clustering/`
**LLM:** nenhum
**Ferramentas:** PyMuPDF (fitz), scikit-learn, KMeans

### O que faz

Recebe todos os PDFs do job e agrupa páginas com layout idêntico. Retorna um cluster por layout distinto, com uma página representativa por cluster.

### 3 camadas de defesa

| Camada | Steps | Objetivo |
|--------|-------|---------|
| Prevention | 1.1–1.9 | Garantir dados de entrada válidos, normalizados |
| Detection | 1.10–1.13 | Detectar outliers, páginas em branco, anomalias |
| Correction | 1.14–1.15 | Corrigir clusters ruins (merge, split) |
| Validation | 1.16 | Homogeneity check — valida representatividade |

### Saída no context

```python
context["clusters"]          # list[dict] — um por layout distinto
context["_raw_text_blocks"]  # dict[page_key, list[block]] — dados crus
```

---

## Stage 2 — Deep Extraction

**Arquivo:** `stage2_deep_extraction.py` + `stage2_extraction/`
**LLM:** nenhum
**Ferramentas:** PyMuPDF, pdfplumber, PIL

### O que faz

Opera **só nas páginas representativas** de cada cluster. Extrai dados completos para análise posterior.

| Sub-step | O que extrai | Ferramenta |
|----------|-------------|------------|
| 2.0 | Texto completo + bbox + font_size + flags | PyMuPDF `get_text('dict')` |
| Fontes | font_family, font_weight → CSS | PyMuPDF + FONT_MAP |
| Imagens | crops PNG de imagens embutidas | PyMuPDF `get_images()` |
| Tabelas | estrutura vetorial (ruling lines) | pdfplumber `find_tables()` |
| Screenshot | PNG da página inteira a 150 DPI | PyMuPDF `get_pixmap()` |
| Drawn elements | linhas, retângulos desenhados | PyMuPDF `get_drawings()` |

### Saída no context

```python
context["enriched_documents"]  # list[dict] — um por PDF
# Cada página representativa contém:
page = {
    "text_blocks": [...],       # blocos com bbox, texto, font
    "fonts": [...],             # fontes detectadas
    "images": [...],            # imagens (logos, etc.)
    "tables": [...],            # tabelas vetoriais (se houver)
    "drawn_elements": [...],    # linhas/retângulos
    "screenshot_path": "...",   # path do PNG 150 DPI
    "width": 595.0,
    "height": 842.0,
}
```

---

## Stage 3 — Structural Analysis

**Arquivo:** `stage3_structural_analysis.py` + `stage3_structural/`
**LLM:** Mistral OCR (tabelas raster + detecção de zonas) — GPT-4o eliminado no Epic 46.2

### Execução

```
3.1 Multi-Example Analysis  ─┐  paralelo (asyncio.gather)
3.2 Visual Analysis          ─┘
        │
        ▼
3.3 Semantic Classification   (sync — depende de 3.1 + 3.2)
        │
        ▼
3.4 Hierarchy Builder         (sync — depende de 3.3)
```

### 3.1 — Multi-Example Analysis

**Ferramenta:** PyMuPDF + scikit-learn + spaCy pt_core_news_sm (opcional)

Analisa blocos de texto entre múltiplos PDFs do mesmo cluster para determinar quais campos são fixos vs dinâmicos:
- Blocos com texto idêntico em todos os PDFs → `static` ou `label`
- Blocos com texto diferente entre PDFs → `dynamic`
- `_DYNAMIC_PATTERNS` (regexes com peso) garante que datas, CPF, CNPJ, R$, CEP sejam `dynamic` mesmo sendo curtos (fix 43.1)

### 3.2 — Visual Analysis

**Epic 46.2 (2026-04-13): GPT-4o Vision completamente eliminado.** Mistral OCR chamado incondicionalmente + PyMuPDF para bbox.

```
_run_3_2(context)
    │
    ├── PyMuPDF.get_image_bbox()       → bbox de todas as imagens raster da página  [$0]
    │   (filtrado: área ≥ 5000 pt², ordenado por área desc)
    │
    ├── _extract_raster_table_mistral(pdf_path, page_index)
    │       POST https://api.mistral.ai/v1/ocr
    │       pages=[page_index]          ← só a página representativa
    │       extract_header=True
    │       extract_footer=True
    │       Cache key: f"{pdf_path}:{page_index}"
    │       Custo: $0.001/chamada
    │       → (extracted_table, cost, zones)
    │           zones = {header, footer, ...}
    │           footer "#" → None (sentinel Mistral)
    │
    └── _build_regions_from_mistral(extracted_table, zones, page_width, page_height)
            → regions[] compatível com formato legado
            → consistency_notes contém "Mistral"
```

Regiões produzidas:

| type | Fonte | Precisão |
|------|-------|----------|
| `table_area` | bbox via PyMuPDF `get_image_bbox()` | ~0 pt² erro |
| `header` | `pages[N].header` do Mistral OCR | texto exato |
| `footer` | `pages[N].footer` do Mistral OCR | texto exato |
| `body` | remainder (height sem header/footer) | geométrico |

**Fallback** (se `MISTRAL_API_KEY` ausente): zonas por threshold geométrico (~75% qualidade) + warning explícito.

**Por que PyMuPDF para bbox e não `images[]` do Mistral?**

Spike 46.1 revelou que `pages[N].images[]` do Mistral contém **apenas imagens que o Mistral não consegue OCR** (logos, fotos opacas). Tabelas raster aparecem em `tables[]` — sem bbox. PyMuPDF `get_image_bbox()` retorna erro ~0 pts vs ~122 pts do GPT-4o.

#### 3.2b — Extração de Tabelas Raster (Mistral OCR)

Acionado incondicionalmente quando há imagem raster na página (não mais gateado por GPT-4o):

```
_extract_raster_table_mistral(pdf_path, page_index)
    │
    ├── PDF completo → base64 → POST https://api.mistral.ai/v1/ocr
    │   model: "mistral-ocr-latest", table_format: "html"
    │   pages=[page_index]  ← por página representativa (não PDF inteiro)
    │   Custo: $0.001/chamada
    │   Cache key: f"{pdf_path}:{page_index}"
    │
    ├── pages[page_index].tables[0].content → HTML
    ├── _parse_html_table_mistral(html) → headers[], rows[][], col_widths_pct[]
    │
    ├── PyMuPDF no bbox → font_family, font_size, font_weight, text_color [exato, $0]
    └── PIL per-row sampling → header_bg_color, row_bg_colors[], border_color [$0]
```

**Por que Mistral e não GPT-4o/Claude para tabelas?**

| Candidato | Header acc. | Cell F1 | Custo | Latência |
|-----------|:-----------:|:-------:|:-----:|:--------:|
| mistral-ocr-pdf | 100% | 0.545 | $0.002 | 1.4s |
| claude-sonnet | 100% | 0.545 | $0.008 | 8.7s |
| GPT-4o | 0% | 0.081 | $0.008 | 8.8s |

GPT-4o falha em tabelas de boleto (extrai seção errada). Mistral = mesma qualidade que Claude, 4× mais barato, 6× mais rápido.

#### 3.2c — Classificação de image_area (Heurística PIL)

Quando GPT-4o detecta `image_area` (genérico):

```
_classify_image_area_heuristic(bbox, screenshot_path)
    │
    ├── crop PIL do screenshot 150 DPI
    ├── aspect_ratio = w / h
    ├── pct_bw = % pixels pretos (<50) + brancos (>200)
    └── unique_colors (sample 1000px)
         │
         ├── aspect > 3.0 AND pct_bw > 85% → "barcode"
         ├── pct_bw > 70% AND unique_colors < 20 → "barcode"
         └── else → "logo"
```

**Por que não usar LLM aqui?**

| Candidato | Accuracy | Custo | Latência |
|-----------|:--------:|:-----:|:--------:|
| Heurística PIL | 3/3 (100%) | $0 | 4ms |
| GPT-4o Vision | 2/3 (66.7%) | $0.02 | 1.4s |
| Gemini Flash | ERROR no barcode | $0.0003 | 1.9s |

GPT-4o classificou barcode como "logo" no caso mais crítico. Gemini retornou erro. Heurística $0 supera ambos no domínio Planet Express.

Fallback: se screenshot indisponível ou PIL falhar → `"logo"` (preserve_as_image_crop — nunca perde dado).

### 3.3 — Semantic Classification

**Ferramenta:** regex + spaCy (opcional)

Classifica cada bloco de texto como `label`, `dynamic` ou `static` usando:
- `position_classifications` do 3.1 (fixo vs dinâmico entre PDFs)
- `visual_analysis_result` do 3.2 (contexto de região visual)
- Regras de posição e formato

### 3.4 — Hierarchy Builder

**Ferramenta:** PyMuPDF (zonas) + PIL (screenshot)

Constrói o document tree hierárquico. Para cada cluster:

1. Zonas → visual regions (Mistral OCR header/footer + PyMuPDF bbox) ou threshold geométrico
2. Seções → drawn lines (PyMuPDF) ou gap analysis
3. Elementos visuais → `_assign_visual_elements_to_sections`

Roteamento de elementos visuais (pós-Epic 43):

| region.type | Handler | Destino no section |
|-------------|---------|-------------------|
| `chart_area` | direto | `section["charts"]` |
| `barcode_area` | direto | `section["barcodes"]` |
| `svg_area` | direto | `section["svgs"]` |
| `table_area` | `extracted_table` (Mistral) ou fallback texto | `section["tables"]` |
| `image_area` | heurística PIL → barcode ou logo | `section["barcodes"]` ou `section["images"]` |
| outros | **descartado** | — |

### Saída no context

```python
context["document_trees"]          # list[dict] — tree por cluster
context["block_classifications"]   # dict — label/dynamic/static por bloco
context["visual_analysis"]         # dict — regiões (Mistral + PyMuPDF) por page_key
```

---

## Stage 4 — Field Mapping

**Arquivo:** `stage4_field_mapping.py` + `stage4_mapping/`
**LLM:** Gemini Flash (`google/gemini-2.0-flash-001`) via OpenRouter

### Sub-steps

| Step | O que faz | LLM? |
|------|-----------|------|
| 4.1 | XSD parsing — extrai campos, tipos, obrigatoriedade | Não (lxml) |
| 4.3 | Format pre-detection — regex para datas, CPF, CNPJ antes do LLM | Não |
| 4.4 | Section/XSD matching — heurística de similaridade por seção | Não |
| 4.5 | Batch field matching — Gemini Flash, 1 chamada por layout | **Sim** |

### 4.5 — Batch LLM (Gemini Flash)

Gemini recebe em batch todos os campos `dynamic` de um layout + paths XSD candidatos (pré-filtrados por seção), e retorna o mapeamento `campo → xsd_field_path`.

**Por que Gemini Flash e não GPT-4o?**
- Campo de texto estruturado (não visual) — não precisa de Vision
- Gemini Flash: mais barato ($0.0003/call) e suficientemente preciso para matching textual

### Saída no context

```python
context["field_mappings"]  # list[FieldMappingEntry] — campo + xsd_field_path + confidence
context["field_tree"]      # XSD tree estruturado
```

---

## Stage 5 — Template Generation

**Arquivo:** `stage5_template_generation.py` + `stage5_template/`
**LLM:** nenhum

### O que faz

Transforma o document tree + field mappings em HTML + CSS final. Sem nenhuma chamada LLM — é renderização determinística.

### Sub-steps

| Step | O que faz |
|------|-----------|
| 5.1 | Tree-driven HTML — percorre document_tree, gera HTML por nó |
| 5.2 | CSS generation — fontes, cores, layout |
| 5.3 | Coverage calculation — fields 60% + tables 25% + images 15% |
| Result | Monta template_draft + confidence_score + variation_matrix |

### Elementos renderizados

| Tipo | HTML gerado |
|------|------------|
| Texto label | `<span class="label">` |
| Campo dinâmico | `<span data-field="xsd_path">` |
| Barcode | SVG placeholder + `data-barcode="true"` |
| Imagem/logo | `<img>` crop preservado |
| Tabela vetorial | `<table>` com estrutura extraída |
| Tabela raster | `<table>` com col_widths%, row_bg_colors[], fontes PyMuPDF |

### Saída no context

```python
context["result_json"] = {
    "template_draft": {"html": "...", "css": "..."},
    "confidence_score": 85,
    "field_mappings": [...],
    "layout_types": [...],
}
```

---

## LLMs Utilizados — Resumo

| Stage | LLM | Modelo | Via | Custo aprox. | Propósito |
|-------|-----|--------|-----|:------------:|-----------|
| Stage 3.2 | Mistral OCR | `mistral-ocr-latest` | Mistral API | $0.001/página repr. | Detecção de zonas (header/footer) + extração de tabelas raster |
| Stage 4.5 | Gemini Flash | `google/gemini-2.0-flash-001` | OpenRouter | ~$0.001/layout | Mapeamento campo → XSD |

**Sem LLM:** Stage 1, Stage 2, Stage 5, heurística PIL (image_area), PyMuPDF font/color/bbox.

> **Epic 46.2 (2026-04-13):** GPT-4o Vision removido do Stage 3.2. Era usado para detecção de regiões (~$0.01/cluster). Substituído por PyMuPDF (`get_image_bbox`) para bbox e Mistral OCR incondicionalmente para zonas.

---

## Variáveis de Ambiente Relevantes

| Variável | Efeito se ausente |
|----------|------------------|
| `OPENROUTER_API_KEY` | Stage 4.5 Gemini desabilitado → field mapping sem LLM |
| `MISTRAL_API_KEY` | Stage 3.2 em fallback geométrico (~75% qualidade) + tabelas raster não extraídas |

> `VISION_AI_ENABLED` foi **removido** no Epic 46.2 — não tem mais efeito. O fallback do Stage 3.2 é controlado exclusivamente por `MISTRAL_API_KEY`.

---

## Custo por Template (estimativa, 1 PDF de 1 página)

| Componente | Custo |
|-----------|:-----:|
| ~~GPT-4o Vision (eliminado Epic 46.2)~~ | ~~$0.010~~ |
| Mistral OCR (detecção + tabela raster) | $0.001 |
| Gemini Flash (field mapping) | ~$0.001 |
| PyMuPDF + PIL (tudo mais) | $0 |
| **Total** | **~$0.002** |

Para 200 templates: **~$0.40** (era ~$2.40 antes do Epic 46.2)

---

## Arquivos Principais

```
backend/services/
├── pipeline_orchestrator_v2.py       # orquestrador — chama os 5 stages em sequência
├── openrouter_client.py              # cliente OpenAI-compat (GPT-4o + Gemini via OpenRouter)
└── stages/
    ├── stage1_layout_clustering.py   # entry point Stage 1
    ├── stage1_clustering/            # algoritmos de clustering, validação
    ├── stage2_deep_extraction.py     # entry point Stage 2
    ├── stage2_extraction/            # text, media, font extraction
    ├── stage3_structural_analysis.py # entry point Stage 3
    ├── stage3_structural/
    │   ├── multi_example_analysis.py # 3.1 — fixo vs dinâmico
    │   ├── visual_analysis.py        # 3.2 — Mistral OCR + PyMuPDF bbox + PIL (GPT-4o eliminado)
    │   ├── classification.py         # 3.3 — label/dynamic/static
    │   ├── section_utils.py          # 3.4 — zonas, seções, image_area handler
    │   ├── tree_builder.py           # 3.4 — document tree
    │   ├── constants.py              # _DYNAMIC_PATTERNS
    │   └── semantic_utils.py         # XSD binding utils
    ├── stage4_field_mapping.py       # entry point Stage 4
    ├── stage4_mapping/
    │   ├── section_matching.py       # 4.4+4.5 — Gemini Flash
    │   ├── xsd_integration.py        # 4.1 — XSD parsing
    │   └── constants.py              # GEMINI_FLASH_MODEL
    ├── stage5_template_generation.py # entry point Stage 5
    └── stage5_template/
        ├── html_tree.py              # 5.1 — tree → HTML
        ├── css_generation.py         # 5.2 — CSS
        ├── html_helpers.py           # barcode, tabela, campo helpers
        └── coverage_overlay.py       # 5.3 — confidence score
```

---

## Referências

- `docs/architecture/adr-raster-table-extraction-strategy.md` — decisão Mistral vs Vision LLM para tabelas
- `docs/reports/epic-43-ocr-bakeoff/image-classification-report.md` — spike heurística PIL vs LLMs
- `docs/stories/epics/epic-43-pipeline-accuracy/EPIC-43.md` — todas as correções do Epic 43

> **Nota sobre docs antigos:** `pipeline-architecture-v2.md` e `pipeline-redesign-v3.md` descrevem
> uma proposta de 28 estágios que não foi implementada. Ignorar para entender o sistema atual.
