# Stage 3 — Structural Analysis: Arquitetura Pós-Epic 43

**Versão:** 1.0 (pós-Epic 43 — Pipeline Accuracy)
**Data:** 2026-04-13
**Status:** `current` — Stage 3 pós-Epic 43/46
**Dono:** `@architect` — atualiza quando story modifica Stage 3
**Fonte:** `backend/services/stages/stage3_structural/` — código real do stage
**Baseline antes:** mapeamento 17% Layout A, 0% tabelas raster, image_area descartada
**Baseline depois:** estrutura corrigida, tabelas raster extraídas, image_area roteada
**Atualizar quando:** story modifica `backend/services/stages/stage3_structural/`
**Última validação:** 2026-04-13 (Epic 46 — GPT-4o eliminado, Mistral incondicional)

---

## 1. Visão Geral do Stage 3

Stage 3 ("Structural Analysis") é o estágio central do pipeline. Recebe páginas representativas de cada cluster e produz o **document tree** — a estrutura hierárquica que alimenta o Stage 4 (field mapping) e o Stage 5 (template generation).

```
Stage 2 (Deep Extraction)
    └── enriched_documents, clusters, raw_text_blocks, screenshots
         │
         ▼
    ┌─ STAGE 3 ─────────────────────────────────────────────┐
    │                                                        │
    │  3.1 Multi-Example Analysis (parallel)  ←── CPU-bound  │
    │  3.2 Visual Analysis        (parallel)  ←── async/LLM  │
    │       │                                                │
    │       ▼ (await ambos)                                  │
    │  3.3 Semantic Classification            ←── sync       │
    │       │                                                │
    │       ▼                                                │
    │  3.4 Hierarchy Builder                  ←── sync       │
    │       │                                                │
    └───────┼────────────────────────────────────────────────┘
            │
            ▼
    document_trees → Stage 4
```

---

## 2. Sub-step 3.1 — Multi-Example Analysis

**Arquivo:** `multi_example_analysis.py`
**Fix:** Story 43.1

### Problema corrigido (43.1)

A heurística `≤30 chars → semantic: "label"` classificava blocos de VALUE como labels. Endereços, datas e valores curtos eram marcados como labels — o Stage 3.3 então criava pares `{label: "RUA PARAIBUNA 456", value: "SAO JOSE DOS CAMPOS"}` incorretos, levando o Stage 4 a mapear para campos errados.

### Solução

`_DYNAMIC_PATTERNS` (em `constants.py`) — conjunto de regexes com peso que identificam valores dinâmicos independente do tamanho do texto:

```python
_DYNAMIC_PATTERNS = [
    (r"\d{2}/\d{2}/\d{4}", "date", 0.9),           # dd/mm/aaaa
    (r"R\$\s*\d", "currency", 0.9),                 # R$ 1.234,56
    (r"\d{5}-?\d{3}", "cep", 0.85),                 # CEP
    (r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", "cnpj", 0.95),
    # ... outros patterns
]
```

Blocos que batem em qualquer pattern são classificados como `dynamic` antes da heurística de comprimento.

---

## 3. Sub-step 3.2 — Visual Analysis

**Arquivo:** `visual_analysis.py`
**Fix:** Stories 43.2, 43.3, 43.4, 43.5, 43.6, **46.2**

> **Epic 46.2 (2026-04-13):** GPT-4o Vision eliminado completamente. Mistral OCR chamado incondicionalmente por página representativa. PyMuPDF fornece bbox exato de imagens raster. Zero chamadas a Vision LLMs.

### 3.2a — Arquitetura Atual (pós-Epic 46.2)

Mistral é chamado **incondicionalmente** para cada página representativa, com `pages=[page_index]` para processar apenas a página relevante:

```
_run_3_2(clusters, enriched_documents, context, emit_progress)
     │
     ├── SE MISTRAL_API_KEY ausente → _fallback_visual_analysis()
     │   └── zonas threshold (top 10%=header, bottom 10%=footer) — ~75% qualidade
     │
     └── SE MISTRAL_API_KEY presente:
         │
         ├── _extract_raster_table_mistral(pdf_path, page_index, key, cache)
         │   │
         │   ├── Mistral OCR API (pages=[page_index], extract_header=True, extract_footer=True)
         │   │   └── retorna pages[0]: {tables[], header, footer, images[]}
         │   │
         │   ├── SE tables[] vazio → None (tabela vetorial — pdfplumber processa)
         │   │
         │   ├── _get_raster_image_bboxes_pymupdf(pdf_path, page_index)
         │   │   └── page.get_images() + page.get_image_bbox(img) → bbox exato [pts]
         │   │       Filtra < 100×50 pts (logos/barcodes pequenos)
         │   │
         │   ├── _parse_html_table_mistral(html) → headers[], rows[][], col_widths_pct[]
         │   │
         │   └── retorna (table_dict, cost_usd, zones)
         │       zones = {header: str|None, footer: str|None}
         │       footer "#" → None (sentinel Mistral para ausente)
         │
         ├── _build_regions_from_mistral(table, zones, page_w, page_h)
         │   └── produz dict idêntico ao formato GPT-4o (retrocompatível com section_utils)
         │       regiões: header? + table_area? + body + footer?
         │
         └── SE table_dict presente → _enrich_raster_table_style(table, page_data, screenshot)
             ├── PyMuPDF get_text('dict') → font_family, font_size, font_weight, text_color
             └── PIL pixel sampling per-row → header_bg_color, row_bg_colors[], border_color
```

### 3.2b — Por que GPT-4o foi eliminado (Spike 46.1)

A spike 46.1 revelou que a hipótese original estava parcialmente errada:

| Hipótese | Resultado |
|----------|-----------|
| `images[]` popula bbox de tabelas raster | **FAIL** — Mistral só coloca em `images[]` o que NÃO consegue OCR. Tabelas/barcodes vão para `tables[]` sem bbox |
| `images[]` popula logos/fotos | **PASS** — `DirfInformaFinanceiro.pdf` confirmou: logos em `images[]` com bbox |
| PyMuPDF como alternativa para bbox | **PASS** — `get_image_bbox()` retorna bbox exato (erro ~0 pts vs ~122 pts do GPT-4o) |
| `extract_header/footer` substitui zone detection GPT-4o | **PASS** — zones retornadas com qualidade suficiente |

**Caminho implementado:** PyMuPDF para bbox (não `images[]`), Mistral incondicional para conteúdo + zonas.

### 3.2c — Custo por cluster (pós-46.2)

| Item | Antes (Epic 43) | Depois (Epic 46.2) |
|------|:--------------:|:-----------------:|
| GPT-4o Vision (region detection) | $0.010 | **$0** |
| Mistral OCR (se tabela raster) | $0.002 | $0.001* |
| PyMuPDF bbox | $0 | $0 |
| PIL sampling | $0 | $0 |
| **Total/cluster** | **$0.010–0.012** | **$0.001** |

*`pages=[page_index]` envia só 1 página → 1 page processed → $0.001.

**Economia: ~$0.01/cluster × ~7.200 clusters = ~$72 total + redução de ~8s de latência por cluster.**

### 3.2d — Layout Schema (Story 43.6, inalterado)

Após extração, cada tabela raster recebe o schema de layout completo:

```python
table["style"] = {
    "font_family": "Arial",           # PyMuPDF
    "font_size": 8.0,                 # PyMuPDF
    "font_weight": "bold",            # PyMuPDF flags
    "text_color": "#000000",          # PyMuPDF
    "col_widths_pct": [25, 25, 25, 25], # HTML colspan (mistral)
    "row_heights_pct": [10, 10, ...], # distribuição uniforme
    "header_bg_color": "#1a3a6b",     # PIL sampling
    "row_bg_colors": ["#ffffff", "#f0f0f0", ...], # PIL per-row
    "border_color": "#cccccc",        # PIL edge sampling
    "border_width": 1,                # heurístico
}
```

### 3.2c — Layout Schema (Story 43.6)

Após extração, cada tabela raster recebe o schema de layout completo:

```python
table["style"] = {
    "font_family": "Arial",           # PyMuPDF
    "font_size": 8.0,                 # PyMuPDF
    "font_weight": "bold",            # PyMuPDF flags
    "text_color": "#000000",          # PyMuPDF
    "col_widths_pct": [25, 25, 25, 25], # HTML colspan (mistral)
    "row_heights_pct": [10, 10, ...], # distribuição uniforme
    "header_bg_color": "#1a3a6b",     # PIL sampling
    "row_bg_colors": ["#ffffff", "#f0f0f0", ...], # PIL per-row
    "border_color": "#cccccc",        # PIL edge sampling
    "border_width": 1,                # heurístico
}
```

---

## 4. Sub-step 3.3 — Semantic Classification

**Arquivo:** `classification.py`
**Fix:** Story 43.1 (patterns), contextualizado por 3.1 e 3.2

Usa `position_classifications` (3.1) e `visual_analysis_result` (3.2) para classificar cada bloco:

- `label` — texto fixo (rótulo de campo)
- `dynamic` — valor que muda entre instâncias
- `static` — texto fixo não-label (título, instrução)

O field mapping do Stage 4 depende dessa classificação para saber o que é XSD-mappable.

---

## 5. Sub-step 3.4 — Hierarchy Builder

**Arquivo:** `tree_builder.py`, `section_utils.py`
**Fix:** Stories 43.2, 43.7, 43.8

Constrói o document tree hierárquico. Para cada cluster representativo:

```
1. Determinar zonas (visual regions → zonas; ou threshold → zonas)
2. Dividir zonas em seções (drawn lines → split; ou gap analysis → split)
3. Atribuir elementos visuais às seções
4. Construir tree
```

### Atribuição de elementos visuais (Step 3 — pós-Epic 43)

**Função:** `_assign_visual_elements_to_sections(zones, visual_analysis, page_key, screenshot_path)`

| `region.type` | Handler | Destino |
|---------------|---------|---------|
| `chart_area` | direto | `section["charts"]` |
| `barcode_area` | direto | `section["barcodes"]` |
| `svg_area` | direto | `section["svgs"]` |
| `table_area` | `_build_visual_table_from_blocks` ou `extracted_table` | `section["tables"]` |
| `image_area` | **`_classify_image_area_heuristic`** (NOVO — 43.8) | `section["barcodes"]` ou `section["images"]` |
| outros | descartado | — |

#### Heurística PIL para image_area (43.7 + 43.8)

Antes da 43.8, `image_area` era silenciosamente descartada (section_utils.py:469). Agora:

```
visual_analysis detecta region.type = "image_area"
         │
         ▼
_classify_image_area_heuristic(bbox, screenshot_path)
         │
         ├── crop a região do screenshot (150 DPI)
         ├── aspect_ratio = width / height
         ├── pct_bw = % pixels pretos (<50) + brancos (>200)
         └── unique_colors (sample de 1000 px)
                  │
                  ├── aspect > 3.0 AND pct_bw > 85% → "barcode"
                  ├── pct_bw > 70% AND unique_colors < 20 → "barcode"
                  └── else → "logo"
                           │
           ┌───────────────┴────────────────┐
           ▼                                ▼
     "barcode"                           "logo"
  section["barcodes"]              section["images"]
  source="image_area_refined"      render_strategy=
                                   "preserve_as_image_crop"
```

**Resultados da spike 43.7 (dados reais):**

| Candidato | Accuracy | Custo | Latência p50 |
|-----------|:--------:|:-----:|:------------:|
| Heurística PIL | **3/3 (100%)** | **$0** | **4ms** |
| GPT-4o Vision | 2/3 (66.7%) | $0.02/call | 1409ms |
| Gemini Flash | 2/2 (100% válidos) | $0.0003/call | 1886ms |

GPT-4o falhou no caso mais crítico: classificou barcode como "logo". Gemini retornou ERROR no barcode (imagem pequena). Heurística PIL acertou os 3 casos incluindo o edge case (logo com aspect ratio 3.21 → corretamente logo, não barcode).

**Fallback seguro:** se screenshot não disponível ou PIL falhar → `"logo"` (preserve_as_image_crop — nunca perde dado).

---

## 6. Fluxo Completo — Tabelas e Imagens no Stage 3

```
PDF raster (JPEG com tabela embutida)
    │
    Stage 2 → screenshot (150 DPI) + enriched_documents
    │
    Stage 3.2 (GPT-4o Vision)
    │   └── detecta region: {type: "table_area", bbox: [...]}
    │
    Stage 3.2 (_extract_raster_table_mistral)
    │   ├── Mistral OCR → HTML → headers[], rows[][], col_widths_pct[]
    │   ├── PyMuPDF → font_family, font_size, font_weight, text_color
    │   └── PIL per-row → header_bg_color, row_bg_colors[], border_color
    │
    Stage 3.4 (_assign_visual_elements_to_sections)
    │   └── region.extracted_table → section["tables"]
    │
    Stage 4 (Field Mapping)
    │   └── table cells → XSD field candidates
    │
    Stage 5 (Template Generation)
        └── table → <table> HTML com layout schema completo

PDF com barcode/logo detectado como image_area
    │
    Stage 3.2 (GPT-4o Vision)
    │   └── detecta region: {type: "image_area", bbox: [...]}
    │
    Stage 3.4 (_classify_image_area_heuristic)
    │   ├── aspect > 3.0 AND pct_bw > 85% → barcode
    │   │       └── section["barcodes"] → Stage 5: zxing-cpp decode
    │   └── else → logo
    │               └── section["images"] → Stage 5: preserve_as_image_crop
```

---

## 7. Custo por Cluster (pós-Epic 43)

| Componente | Custo | Quando |
|-----------|:-----:|--------|
| GPT-4o Vision (detecção de regiões) | ~$0.01 | sempre |
| Mistral OCR (extração tabela raster) | $0.002 | só se tem tabela raster |
| PyMuPDF (font/color) | $0 | sempre |
| PIL (sampling + heurística image_area) | $0 | sempre |
| **Total sem tabela raster** | ~$0.01 | boleto simples |
| **Total com tabela raster** | ~$0.012 | boleto com JPEG table |

---

## 8. Arquivos Modificados (Epic 43)

| Arquivo | Mudança |
|---------|---------|
| `stage3_structural/multi_example_analysis.py` | `_DYNAMIC_PATTERNS` — regexes para classificar blocos curtos como dynamic (43.1) |
| `stage3_structural/constants.py` | `_DYNAMIC_PATTERNS` — 20+ regexes com peso para datas, CPF, CNPJ, CEP, R$, etc. |
| `stage3_structural/visual_analysis.py` | `_extract_raster_table_mistral` — Mistral OCR para tabelas raster (43.2) |
| `stage3_structural/visual_analysis.py` | `sample_table_colors` — PIL per-row sampling (43.5) |
| `stage3_structural/visual_analysis.py` | `_enrich_raster_table_style` — schema completo font+color (43.6) |
| `stage3_structural/section_utils.py` | `_classify_image_area_heuristic` — heurística PIL barcode/logo (43.8) |
| `stage3_structural/section_utils.py` | `_assign_visual_elements_to_sections` — `image_area` incluída, parâmetro `screenshot_path` (43.8) |
| `stage3_structural/tree_builder.py` | passa `screenshot_path` para `_assign_visual_elements_to_sections` (43.8) |

---

## 9. Limitações Conhecidas (Backlog)

| Limitação | Impacto | Story |
|-----------|---------|-------|
| Row heights não-uniformes | PIL sampling por row usa distribuição uniforme — erro se linhas têm alturas diferentes | Futuro |
| Per-cell background | Só per-row atualmente; células individualmente coloridas precisam de sampling por célula | Futuro |
| image_area ground truth pequeno | Spike 43.7 testou 3 samples; charts ausentes no domínio Planet Express | Aceitável |
| Gemini como fallback de image_area | Gemini falhou no caso barcode — não usar como fallback de LLM | Documentado |

---

## 10. Referências

- `docs/architecture/adr-raster-table-extraction-strategy.md` — decisão Mistral vs Vision LLM
- `docs/reports/epic-43-ocr-bakeoff/image-classification-report.md` — spike 43.7 heurística PIL
- `docs/stories/epics/epic-43-pipeline-accuracy/EPIC-43.md` — todas as stories
