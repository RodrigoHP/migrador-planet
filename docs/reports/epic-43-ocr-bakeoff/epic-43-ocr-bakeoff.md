# Epic 43 — OCR/Vision Bake-off: Extração de Conteúdo Raster

**Data:** 2026-04-13  |  **Budget gasto:** $0.1116 / $5.00

## Sumário Executivo

Bake-off empírico de candidatos para extração de conteúdo raster em PDFs do tipo boleto bancário.
Testado com `Corporate.Boleto.Convenio.pdf` — tabela raster JPEG na página 0.

**Candidatos via OpenRouter (credenciais disponíveis):**
- GPT-4o Vision (`openai/gpt-4o`)
- Claude Sonnet 4.5 Vision (`anthropic/claude-sonnet-4-5`)
- Gemini 2.0 Flash Vision (`google/gemini-2.0-flash-001`)
- Pixtral Large Vision (`mistralai/pixtral-large-2411`) via OpenRouter — alias `mistral-vision`

**Candidatos via Mistral API direta:**
- Mistral OCR image (`mistral-ocr-latest`, input: PNG crop) — alias `mistral-ocr`
- Mistral OCR PDF (`mistral-ocr-latest`, input: PDF completo + `table_format="html"`) — alias `mistral-ocr-pdf`

**Candidatos locais (free):**
- zxing-cpp (barcode decoder)

**Candidatos nao testados (sem credenciais/instalacao):**
- Azure Document Intelligence (testado, encoding quebrado — sem metricas validas)
- AWS Textract, Google Document AI
- Docling, Marker, pymupdf-layout, Table Transformer (TATR), Deplot
- pyzbar (Windows DLL faltando)

---

## Tabela Raster — Metricas Comparativas

Ground truth: `boleto_raster_table_ground_truth.json`
- Colunas GT: 4  |  Linhas GT: 9
- Headers: Beneficiario, Agencia/Cod. Beneficiario, Data Emissao, Vencimento

| Candidato | n | Header Acc | Col Acc | Row Acc | Cell F1 | PT Acc | Font | Border | Lat p50 | Custo/3runs |
|-----------|:-:|:----------:|:-------:|:-------:|:-------:|:------:|:----:|:------:|:-------:|:-----------:|
| **mistral-ocr-pdf** | 3 | **100%** | **100%** | 33.3% | **0.545** | 57% | - | - | **1376ms** | **$0.0060** |
| **claude-sonnet** | 2 | **100%** | **100%** | 33.3% | **0.545** | 57% | OK | OK | 8733ms | $0.0158 |
| mistral-vision | 2 | 100% | 50% | 27.8% | 0.391 | 50% | OK | OK | 7516ms | $0.0151 |
| gpt4o | 3 | 0% | 33% | **81.5%** | 0.081 | 0% | OK | OK | 8793ms | $0.0241 |
| gemini-flash | 3 | 0% | 0% | 37.0% | 0.016 | 0% | OK | - | 4491ms | $0.0009 |
| mistral-ocr (image) | 3 | 0% | 0% | 33.3% | 0.000 | 0% | - | - | 1311ms | $0.0030 |
| azure-doc-intel | 3 | 0% | 0% | 22.2% | 0.000 | 0% | - | - | 6267ms | $0.0450 |

> **Nota sobre Row Acc:** GT tem 9 linhas (schema completo do boleto). Todos os candidatos top extraem apenas a Secao A (Beneficiario/Pagador = 3 linhas). Row Acc de 33% = 3/9 linhas — comportamento correto para o target da Secao A.

> **Nota sobre GPT-4o:** Row Acc de 81.5% indica que o GPT-4o ve mais linhas do boleto (Secao B/C tambem), mas sem match de headers — schema interpretado de forma diferente do GT.

---

## Barcode — Metricas Comparativas

Ground truth: `boleto_barcode_ground_truth.json`
- Tipo GT: ITF-14 / Interleaved 2-of-5
- Valor GT: null (JPEG comprimido nao decodificavel com qualidade de producao)

| Candidato | Type Acc | Value Acc | Lat | Custo |
|-----------|:--------:|:---------:|:---:|:-----:|
| **zxing-cpp** | 0.0% | N/A (GT=null) | ~50ms | $0.0000 |

---

## Insights Tecnicos

### 1. Mistral OCR: PDF mode >> image mode

`mistral-ocr-latest` com PDF completo e `table_format="html"` retorna `pages[0].tables[]` com HTML estruturado (colspan/rowspan). O mesmo endpoint com PNG crop retorna markdown sem estrutura de tabela util.

**Conclusao:** Ao usar Mistral OCR, sempre passar o PDF completo. O crop de imagem perde a vantagem estrutural do endpoint.

### 2. pixtral-large via direct API tem rate limit severo

`pixtral-large-2411` via `api.mistral.ai` retorna 429 apos 1 chamada. Solucao: rotear via OpenRouter (`mistralai/pixtral-large-2411`). Custo ligeiramente maior mas sem throttling.

### 3. mistral-ocr-pdf = melhor custo-beneficio

Empate com Claude Sonnet em Cell F1 e Header accuracy, mas:
- **4x mais barato** ($0.002/run vs $0.0079/run)
- **6x mais rapido** (1376ms vs 8733ms)
- Limitacao: nao detecta font/border (output e HTML sem CSS inline)

### 4. Claude Sonnet e o unico que detecta estilo visual

Font family, font size, text color, border color — apenas Claude Sonnet retorna esses campos de forma consistente. Relevante para o Pilar A (fidelidade visual do template).

### 5. Boleto tem estrutura multi-secao no raster

A imagem JPEG contem 3 secoes de tabela:
- **Secao A:** Beneficiario/Pagador (4 colunas) — alvo do GT
- **Secao B:** Codigos bancarios/linha digitavel (9 colunas)
- **Secao C:** Calculos (Descontos, Mora, Valor Cobrado)

GPT-4o captura todas as secoes (Row Acc 81.5%) mas sem alignment de headers. Candidatos de topo focam corretamente na Secao A.

---

## Recomendacao

### Tabela Raster

**Primario: `mistral-ocr-pdf`**
- Melhor custo-beneficio: Cell F1=0.545, Header=100%, $0.002/run, ~1.4s
- Usar com PDF completo + `table_format="html"`
- Implementar seletor de secao por keywords GT

**Fallback / quando estilo e necessario: `claude-sonnet-4-5` via OpenRouter**
- Mesmo Cell F1, mas detecta font + border — necessario para fidelidade visual de template
- 4x mais caro, 6x mais lento — usar apenas quando atributos de estilo sao requeridos

**Descartar:** `mistral-ocr` (image mode), `azure-doc-intel`, `gemini-flash` para esta tarefa.

**Manter em avaliacao:** `gpt4o` — high row recall pode ser util para extracao de multiplas secoes, mas requer prompt engineering para alinhamento de schema.

### Barcode

**zxing-cpp**: Nao conseguiu decodificar o JPEG comprimido. Alternativa: usar Vision LLM para identificar tipo + descrever; o valor real da linha digitavel e derivado do PDF vetorial (nao necessario extrair do raster).

---

## Spike Costs

| Run | Custo |
|-----|-------|
| Total acumulado | $0.1116 |
| Budget maximo | $5.00 |
| Budget restante | $4.8884 |

---

## Raw Outputs

Ver `docs/reports/epic-43-ocr-bakeoff/{candidate}/` para outputs completos por candidato.

---

*Gerado por `backend/scripts/spike_ocr_bakeoff.py` — Story 43.3*
