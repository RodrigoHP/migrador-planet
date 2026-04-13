# Epic 43 — OCR/Vision Bake-off: Extração de Conteúdo Raster

**Data:** 2026-04-13  |  **Budget gasto:** $0.1813 / $5.00

## Sumário Executivo

Bake-off empírico de candidatos para extração de conteúdo raster em PDFs do tipo boleto bancário.
Testado com `Corporate.Boleto.Convenio.pdf` — tabela raster JPEG na página 0.

**Candidatos testados:**
- GPT-4o Vision (`openai/gpt-4o`) via OpenRouter
- Claude Sonnet 4.5 Vision (`anthropic/claude-sonnet-4-5`) via OpenRouter
- Gemini 2.0 Flash Vision (`google/gemini-2.0-flash-001`) via OpenRouter
- Pixtral-large Vision (`mistralai/pixtral-large-2411`) via OpenRouter — **adicionado após revisão**
- Mistral OCR (`mistral-ocr-latest`) via API direta
- Azure Document Intelligence (`prebuilt-layout`) via SDK
- zxing-cpp (barcode decoder, local)

**Candidatos não testados (sem credenciais/instalação):**
- AWS Textract, Google Document AI
- Docling, Marker, pymupdf-layout, Table Transformer (TATR), Deplot
- pyzbar (Windows DLL faltando)

---

## Insight Crítico — Múltiplas Seções na Imagem Raster

A imagem JPEG do boleto (`bbox [27.68, 377.30, 582.92, 718.77]`, 2174×1337px) contém **3 seções de tabela distintas empilhadas verticalmente**:

| Seção | Conteúdo | Ground Truth usado |
|-------|----------|-------------------|
| **A (topo)** | Beneficiário, Agência, Data Emissão, Vencimento, Pagador, Valor | ✅ Seção A é o GT |
| **B (meio)** | Uso do Banco, CIP, Carteira, Espécie Moeda, códigos bancários | ❌ Não é GT |
| **C (baixo)** | Linhas de cálculo: =Valor Documento, -Descontos, =Valor Cobrado | Parcialmente no GT |

---

## Tabela Raster — Métricas Comparativas

Ground truth: `boleto_raster_table_ground_truth.json`
- Colunas GT (Seção A): 4  |  Linhas GT: 9
- Headers: Beneficiário, Agência/Cód. Beneficiário, Data Emissão, Vencimento

| Candidato | Header Acc | Col Acc | Row Acc | Cell F1 | PT Acc | Font | BG Color | Border | Lat p50 | Custo/3runs | Seção vista |
|-----------|:----------:|:-------:|:-------:|:-------:|:------:|:----:|:--------:|:------:|:-------:|:-----------:|:-----------:|
| **azure-doc-intel** | 0.0% | 0.0% | 22.2% | 0.0% | 0.0% | ❌ | ❌ | ❌ | 5889ms | $0.0450 | B (códigos bancários) |
| **gpt4o** | 0.0% | 0.0% | 44.4% | 3.6% | 0.0% | ✅ | ❌ | ❌ | 8981ms | $0.0241 | Misto A+B — esquema diferente |
| **claude-sonnet** | **100.0%** | **100.0%** | 33.3% | **54.5%** | **57.1%** | ✅ | ✅ | ✅ | 9501ms | $0.0341 | A |
| **gemini-flash** | 0.0% | 0.0% | 44.4% | 4.9% | 0.0% | ✅ | ❌ | ❌ | 4654ms | $0.0009 | Parcial A |
| **mistral-ocr** | 0.0% | 0.0% | 33.3% | 0.0% | 0.0% | ❌ | ❌ | ❌ | 1277ms | $0.0030 | B (texto livre + pipe-table) |
| **mistral-vision** ⭐ | **100.0%** | **100.0%** | 33.3% | **54.5%** | **57.1%** | ✅ | ❌ | ✅ | 6770ms | $0.0194 | A |

**Nota sobre `mistral-ocr`:** O endpoint `/v1/ocr` retorna mix de texto livre + pipe-table. O texto livre contém os dados da Seção A, mas sem estrutura de tabela. O pipe-table captura a Seção B. Para extração estruturada use `pixtral-large-2411` via chat completions.

**Nota sobre `gpt4o`:** Retornou 7 colunas tratando "Beneficiário" como label de linha, não como header. Dados presentes mas esquema diferente do GT. Header accuracy = 0.0% porque a métrica é posicional.

---

## Barcode — Métricas Comparativas

Ground truth: `boleto_barcode_ground_truth.json`
- Tipo GT: ITF-14 / Interleaved 2-of-5
- Valor GT: null (JPEG comprimido não decodificável com qualidade de produção)

| Candidato | Type Acc | Value Acc | Lat | Custo |
|-----------|:--------:|:---------:|:---:|:-----:|
| **zxing-cpp** | 0.0% | N/A (GT=null) | 110ms | $0.0000 |
| **gpt4o** | 0.0% | N/A (GT=null) | 3080ms | $0.0013 |
| **claude-sonnet** | 0.0% | N/A (GT=null) | 5164ms | $0.0020 |
| **gemini-flash** | 0.0% | N/A (GT=null) | 3825ms | $0.0002 |
| **mistral-ocr** | 0.0% | N/A (GT=null) | 739ms | $0.0010 |
| **mistral-vision** | 0.0% | N/A (GT=null) | 1961ms | $0.0013 |

**Nota:** O valor da linha digitável já está no texto vetorial do PDF — não precisa extrair do raster.

---

## Recomendação

### Tabela Raster

**Empate técnico: Claude Sonnet 4.5 e Pixtral-large — métricas idênticas.**

Ambos extraíram headers corretos, estrutura de 4 colunas, Cell F1 = 54.5%.

| Critério | Claude Sonnet | Pixtral-large |
|----------|:---:|:---:|
| Header accuracy | 100% | 100% |
| Cell F1 | 54.5% | 54.5% |
| BG Color detectado | ✅ | ❌ |
| Border detectado | ✅ | ✅ |
| Custo/3runs | $0.034 | $0.019 |
| Custo relativo | 1× | **0.57×** |

**Recomendação: Pixtral-large** como primeira opção (~43% mais barato, qualidade equivalente). Claude Sonnet como fallback — detecta BG color que Pixtral não detectou.

**Descartados:**
- `gpt4o` — esquema diferente do GT, Cell F1 baixo
- `gemini-flash` — não capturou headers corretos
- `mistral-ocr` — endpoint OCR inadequado para extração estruturada
- `azure-doc-intel` — captura seção diferente (B); potencial uso complementar

### Barcode

**Recomendação: Não extrair do raster.** O valor está no texto vetorial do PDF. Nenhum candidato decodificou o JPEG comprimido.

---

## Spike Costs

| Run | Custo |
|-----|-------|
| Run inicial (3 Vision LLMs + zxing) | $0.0549 |
| +Azure Doc Intelligence (3 runs) | $0.0485 |
| +Mistral OCR (3 runs) | $0.0082 |
| +Mistral Vision/Pixtral (3 runs) | $0.0697 |
| **Total acumulado** | **$0.1813** |
| Budget máximo | $5.00 |
| Budget restante | $4.8187 |

---

## Raw Outputs

Ver `docs/reports/epic-43-ocr-bakeoff/{candidate}/` para outputs completos por candidato.

---

*Gerado por `backend/scripts/spike_ocr_bakeoff.py` — Story 43.3*
