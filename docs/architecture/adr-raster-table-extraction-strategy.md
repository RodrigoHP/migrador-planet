# ADR — Estratégia de Extração de Tabelas Raster

**Data:** 2026-04-13  
**Status:** DECIDIDO  
**Contexto:** Epic 43 — Pipeline Accuracy / Story 43.3 Spike OCR Bake-off

---

## Problema

PDFs Planet Express contêm tabelas embutidas como JPEG raster (ex: boleto Bradesco).  
`page.find_tables()` retorna 0 nesses casos — requer texto vetorial ou ruling lines.  
O template HTML precisa capturar: estrutura (colunas/linhas), conteúdo, font, cores, bordas.

---

## Decisão

**`mistral-ocr-pdf` como extrator primário de estrutura + conteúdo.**  
**PyMuPDF para font/cores de texto.**  
**PIL pixel sampling per-row para background das células.**  
**Nenhum Vision LLM necessário para extração de estilo.**

---

## Descobertas Empíricas que Embasam a Decisão

### 1. Arquitetura do PDF Planet Express

PDFs gerados pelo motor Planet Express têm duas camadas:

- **Camada JPEG** (raster): backgrounds das células, bordas, logos
- **Camada vetorial** (sobreposta): TODO o texto, com font/size/color exatos

PyMuPDF extrai a camada vetorial com precisão absoluta — Arial, 8pt, bold, #000000.  
Não há fill colors vetoriais: backgrounds e bordas estão exclusivamente no JPEG.

### 2. Bake-off de candidatos (43.3) — 7 candidatos testados

| Candidato | Header | Cell F1 | Lat | Custo/call | Estilo |
|-----------|:------:|:-------:|:---:|:----------:|:------:|
| mistral-ocr-pdf | 100% | 0.545 | 1.4s | $0.002 | nenhum (HTML puro) |
| claude-sonnet | 100% | 0.545 | 8.7s | $0.008 | completo (inferido) |
| mistral-vision | 100% | 0.391 | 7.5s | $0.008 | parcial (inferido) |
| gpt4o | 0% | 0.081 | 8.8s | $0.008 | parcial (inferido) |
| gemini-flash | 0% | 0.016 | 4.5s | $0.0003 | parcial (inferido) |
| mistral-ocr (image) | 0% | 0.000 | 1.3s | $0.001 | nenhum |
| azure-doc-intel | 0% | 0.000 | 6.3s | $0.015 | nenhum |

### 3. Estilo "inferido" vs "exato"

Vision LLMs (Claude, GPT-4o, Pixtral) retornam `font_family=Arial, font_size=10px` — mas é **inferência**, não observação. Não há ground truth de fonte validado.

PyMuPDF retorna `Arial_feDefaultFont_Encoding, 8pt, flags=20 (bold)` — **exato, da estrutura do PDF**.

### 4. Mistral OCR response inspecionado

`pages[0]` contém: `markdown, images, tables, hyperlinks, header, footer, dimensions, confidence_scores`.  
**Nenhum campo de font, color ou border.** `document_annotation` ausente no response.  
O HTML das tabelas é estrutural puro — sem CSS inline.

---

## Arquitetura de Extração Decidida

```
PDF
 ├── PyMuPDF.get_text('dict')     → font_family, font_size, font_weight, text_color  [exato, $0]
 ├── PyMuPDF.get_image_bbox()     → posição da tabela na página                       [exato, $0]
 ├── mistral-ocr-pdf              → estrutura HTML (colspan → col_widths_pct)         [$0.002]
 │     └── _parse_html_table()   → headers, rows, col_widths_pct, row_heights_pct
 └── PIL pixel sampling per-row  → header_bg_color, row_bg_colors[], border_color     [$0]
```

### Cobertura de atributos

| Atributo | Fonte | Acurácia |
|----------|-------|----------|
| font_family | PyMuPDF (vetorial) | Exata |
| font_size | PyMuPDF (vetorial) | Exata |
| font_weight (bold) | PyMuPDF flags | Exata |
| text_color | PyMuPDF (vetorial) | Exata |
| col_widths_pct | HTML colspan (mistral-ocr-pdf) | MAE=0.0 (4-col equal) |
| row_heights_pct | Distribuição uniforme | Heurística (suficiente para boletos) |
| header_bg_color | PIL sampling (topo da imagem) | Heurística boa |
| row_bg_colors[] | PIL sampling per-row | Heurística boa |
| border_color | PIL sampling (5th percentile edge) | Heurística boa |
| border_width | Heurístico 1pt | Aproximado |
| Posição (bbox) | PyMuPDF.get_image_bbox() | Exata |

### Custo total por chamada de tabela raster

`$0.002` (apenas mistral-ocr-pdf). Tudo mais é local.

---

## Alternativas Descartadas

**Vision LLM (Claude/GPT-4o) para estilo:**
- Mesmo Cell F1 que mistral-ocr-pdf em conteúdo
- Estilo é inferido, não exato
- 4x mais caro, 6x mais lento
- PyMuPDF já entrega font/color com precisão maior e grátis
- Descartado

**Azure Document Intelligence:**
- Header=0%, Cell F1=0.000
- $0.015/call (7.5x mais caro)
- Descartado

**Gemini Flash:**
- Header=0%, Cell F1=0.016
- Útil como fallback de baixo custo mas inaceitável como primário
- Mantido em avaliação para casos edge

---

## Limitações Conhecidas

1. **Row heights não-uniformes:** se linhas tiverem alturas diferentes, distribuição uniforme erra. Resolvível com detecção de bordas horizontais na imagem (escopo futuro).

2. **Per-cell backgrounds:** pixel sampling atual retorna cores por row, não por célula. Para documentos com células individualmente coloridas, será necessário sampling por bbox de célula — requer col_widths_pct para calcular x boundaries.

3. **Documentos não-Planet Express (scaneados):** camada vetorial pode estar ausente. PyMuPDF não retornaria font/color. Fallback: Vision LLM para estilo ou defaults por tipo de documento.

4. **mistral-ocr-pdf exige PDF completo:** não funciona com PNG crop — `tables[]` fica vazio. Sempre passar o PDF path.

---

## Stories de Implementação Derivadas

- **43.2** (revisão): trocar GPT-4o por `mistral-ocr-pdf` + integrar PyMuPDF font extraction
- **43.5** (nova): PIL pixel sampling per-row para `row_bg_colors[]`
- **43.6** (nova): integrar `col_widths_pct` e `row_heights_pct` no schema de template HTML

---

*Decisão tomada após: Spike 43.3 (bake-off 7 candidatos) + Spike 43.4 (layout extraction) + inspeção direta do response Mistral OCR API + inspeção PyMuPDF na página do boleto.*
