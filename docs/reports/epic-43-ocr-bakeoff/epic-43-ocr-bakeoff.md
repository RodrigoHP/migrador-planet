# Epic 43 — OCR/Vision Bake-off: Extração de Conteúdo Raster

**Data:** 2026-04-13  |  **Budget gasto:** $0.0170 / $5.00

## Sumário Executivo

Bake-off empírico de candidatos para extração de conteúdo raster em PDFs do tipo boleto bancário.
Testado com `Corporate.Boleto.Convenio.pdf` — tabela raster JPEG na página 0.

**Candidatos via OpenRouter (credenciais disponíveis):**
- GPT-4o Vision (`openai/gpt-4o`)
- Claude Sonnet 4.5 Vision (`anthropic/claude-sonnet-4-5`)
- Gemini 2.0 Flash Vision (`google/gemini-2.0-flash-001`)

**Candidatos locais (free):**
- zxing-cpp (barcode decoder)

**Candidatos nao testados (sem credenciais/instalacao):**
- Azure Document Intelligence, AWS Textract, Google Document AI
- Docling, Marker, pymupdf-layout, Table Transformer (TATR), Deplot
- pyzbar (Windows DLL faltando)

---

## Tabela Raster — Métricas Comparativas

Ground truth: `boleto_raster_table_ground_truth.json`
- Colunas GT: 4  |  Linhas GT: 9
- Headers: Beneficiário, Agência/Cód. Beneficiário, Data Emissão, Vencimento

| Candidato | Header Acc | Col Acc | Row Acc | Cell F1 | PT Acc | Font | BG Color | Border | Lat p50 | Custo/3runs |
|-----------|:----------:|:-------:|:-------:|:-------:|:------:|:----:|:--------:|:------:|:-------:|:-----------:|
| **azure-doc-intel** | 0.0% | 0.0% | 22.2% | 0.0% | 0.0% | ❌ | ❌ | ❌ | 7098ms | $0.0150 |
| **mistral-ocr-pdf** | 100.0% | 100.0% | 33.3% | 54.5% | 57.1% | ❌ | ❌ | ❌ | 1205ms | $0.0020 |

## Barcode — Métricas Comparativas

Ground truth: `boleto_barcode_ground_truth.json`
- Tipo GT: ITF-14 / Interleaved 2-of-5
- Valor GT: null (JPEG comprimido não decodificável com qualidade de produção)

| Candidato | Type Acc | Value Acc | Lat | Custo |
|-----------|:--------:|:---------:|:---:|:-----:|
| **zxing-cpp** | 0.0% | N/A (GT=null) | 5ms | $0.0000 |

---

## Recomendação

### Tabela Raster

_Baseada nos resultados do bake-off acima._

### Barcode

**zxing-cpp**: Não conseguiu decodificar o JPEG comprimido. Alternativa: usar Vision LLM para identificar tipo + descrever; o valor real da linha digitável é derivado do PDF vetorial (não necessário extrair do raster).

---

## Spike Costs

| Run | Custo |
|-----|-------|
| Total acumulado | $0.0170 |
| Budget máximo | $5.00 |
| Budget restante | $4.9830 |

---

## Raw Outputs

Ver `docs/reports/epic-43-ocr-bakeoff/{candidate}/` para outputs completos por candidato.

---

*Gerado por `backend/scripts/spike_ocr_bakeoff.py` — Story 43.3*