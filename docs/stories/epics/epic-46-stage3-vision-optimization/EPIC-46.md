# Epic 46 — Stage 3 Vision Optimization: Mistral como Substituto do GPT-4o

## Status: Done

## Objetivo

Eliminar a dependência do GPT-4o Vision no Stage 3.2 usando capacidades já disponíveis no Mistral OCR (`pages[].images` com bbox, `extract_header`, `extract_footer`), reduzindo custo e latência sem perda de qualidade.

## Contexto

No Stage 3.2 (Visual Analysis), o GPT-4o Vision é chamado por página representativa para detectar regiões (`table_area`, `barcode_area`, `image_area`, zonas header/body/footer). O Mistral OCR já é chamado no mesmo stage para extrair conteúdo de tabelas raster (Story 43.2).

Análise arquitetural (2026-04-13) revelou que o Mistral OpenAPI spec (`docs/api-references/mistral-openapi.yaml`) retorna:

| Campo | Struct | Campos |
|-------|--------|--------|
| `pages[].images[]` | `OCRImageObject` | `id`, `top_left_x`, `top_left_y`, `bottom_right_x`, `bottom_right_y`, `image_base64` |
| `pages[].dimensions` | `OCRPageDimensions` | `dpi`, `height`, `width` |
| `pages[].header` | `string \| null` | header da página (requer `extract_header=True`) |
| `pages[].footer` | `string \| null` | footer da página (requer `extract_footer=True`) |
| `pages[].tables[]` | `OCRTableObject` | `id`, `content`, `format` — **sem bbox** |

O bbox das tabelas raster está em `images[]`, não em `tables[]`. O markdown vincula os dois via placeholder (`![img-X.jpeg]` e `[tbl-Y.html]`).

**Hipótese:** A chamada GPT-4o Vision ($0.01/cluster) pode ser eliminada usando:
1. `pages[].images[].top_left_x/y` + `dimensions.dpi` → bbox preciso da tabela raster (substituindo GPT-4o region detection)
2. `extract_header=True` / `extract_footer=True` → zonas header/footer (substituindo GPT-4o zone detection)
3. `pages[].images[]` + PIL heuristic (já implementada na Story 43.8) → barcode vs logo detection

## Custo Atual vs Proposto

| Cenário | GPT-4o Vision | Mistral | Total/cluster |
|---------|:------------:|:-------:|:-------------:|
| Atual | $0.01 | $0.002 (se tabela) | $0.010–0.012 |
| Proposto | $0 | $0.002 (cached, pago uma vez) | ~$0.0001 extra |

**Economia estimada:** ~$0.01/cluster × 7.200 clusters (200 templates × 18 × 2 rep.) = **~$72 total**, com latência reduzida em ~8s/cluster.

## Stories

| Story | Título | Status | Prioridade | Esforço | Dep |
|-------|--------|--------|-----------|---------|-----|
| 46.1 | SPIKE: Validar Mistral `images[]` bbox como substituto do GPT-4o Vision | Done | P0 | 8h | — |
| 46.2 | Eliminar GPT-4o Vision via PyMuPDF + Mistral incondicionalmente | Done | P0 | 8h | 46.1 |

## Critério de Conclusão

- Spike produziu evidência empírica (sim/não) para cada hipótese
- Relatório com métricas de precisão de bbox e qualidade de zona detection
- Recomendação clara: eliminar GPT-4o / manter / hibridizar
- Se resultado positivo: story de implementação criada

## Change Log

| Date | Agent | Action |
|------|-------|--------|
| 2026-04-13 | @architect (Aria) | Epic criado — análise do spec Mistral revela que GPT-4o pode ser redundante |
| 2026-04-13 | @dev (Dex) | Story 46.1 Done — spike concluído. Hipótese images[] FAIL, mas achado PyMuPDF valida eliminação do GPT-4o. Story 46.2 adicionada com caminho alternativo. |
| 2026-04-13 | @dev (Dex) | Story 46.2 Done — GPT-4o eliminado. Mistral incondicionalmente (`pages=[N]`), PyMuPDF bbox exato. 15 unit tests + integração. Custo $0.010→$0.001/cluster. |
