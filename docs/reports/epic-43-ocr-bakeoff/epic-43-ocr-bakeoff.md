# Epic 43 — OCR/Vision Bake-off: Extracao de Conteudo Raster

**Data:** 2026-04-13  |  **Budget gasto:** $0.0549 / $5.00  |  **Story:** 43.3

---

## Sumario Executivo

Bake-off empirico de candidatos para extracao de conteudo raster em PDFs do tipo boleto bancario.

**Arquivo testado:** `Corporate.Boleto.Convenio.pdf`  
**Regiao testada:** Tabela raster JPEG na pagina 0, bbox `[27.68, 377.30, 582.92, 718.77]`  
**Crop:** `boleto_raster_table_crop.png` (1111x684 px a 2x)  
**Barcode:** `boleto_barcode_crop.png` (478x126 px a 2x)

**Veredicto: Claude Sonnet 4.5 e o vencedor para extracao de tabela raster.**

---

## Candidatos Testados

| # | Candidato | Status | Motivo |
|---|-----------|--------|--------|
| 1 | GPT-4o Vision (via OpenRouter) | TESTADO | OPENROUTER_API_KEY disponivel |
| 2 | Claude Sonnet 4.5 Vision (via OpenRouter) | TESTADO | OPENROUTER_API_KEY disponivel |
| 3 | Gemini 2.0 Flash Vision (via OpenRouter) | TESTADO | OPENROUTER_API_KEY disponivel |
| 4 | zxing-cpp (local) | TESTADO | Instalado localmente |
| 5 | Azure Document Intelligence | SKIPPED | Sem credenciais |
| 6 | AWS Textract | SKIPPED | Sem credenciais |
| 7 | Google Document AI | SKIPPED | Sem credenciais |
| 8 | Docling (IBM) | SKIPPED | Nao instalado |
| 9 | Marker | SKIPPED | Nao instalado |
| 10 | pymupdf-layout | SKIPPED | Nao disponivel |
| 11 | pyzbar | SKIPPED | DLL libzbar ausente no Windows |
| 12 | Table Transformer (TATR) | SKIPPED | Requer GPU/HuggingFace |
| 13 | Deplot | SKIPPED | Requer GPU/HuggingFace |

---

## Tabela Raster - Resultados

**Ground truth:** `boleto_raster_table_ground_truth.json`
- Colunas: 4 (Beneficiario, Agencia/Cod. Beneficiario, Data Emissao, Vencimento)
- Linhas: 9 (dados do beneficiario + pagador + 6 linhas de calculo de valor)

| Candidato | Header Acc | Col Acc | Row Acc | Cell F1 | PT Acc | Font | BG Color | Border | Lat p50 | Custo/3runs |
|-----------|:----------:|:-------:|:-------:|:-------:|:------:|:----:|:--------:|:------:|:-------:|:-----------:|
| **claude-sonnet** | **100%** | **100%** | 33% | **54.5%** | 57.1% | OK | **OK** | OK | ~2s | $0.035 |
| gpt4o | 0% | 0% | 11% | 0% | 0% | OK | -- | OK | ~3s | $0.016 |
| gemini-flash | 0% | 0% | 11% | 0% | 0% | OK | -- | OK | <1s | $0.001 |

### Analise Detalhada

**Claude Sonnet 4.5 (VENCEDOR):**
- Identificou corretamente os 4 headers: `["Beneficiario", "Agencia/Cod. Beneficiario", "Data Emissao", "Vencimento"]`
- Extraiu 3 linhas de dados (beneficiario, labels pagador, dados pagador)
- Nao extraiu as 6 linhas de calculo abaixo (=Valor do Documento, -Descontos, etc.)
- **Unico candidato que detectou cor de fundo** (`cell_bg_color: "#FFFFFF"`)
- Pequena diferenca: "Numero do Documento" vs GT "Numero de Documento" (artigo diferente -- sem impacto pratico)
- Custo: ~$0.012/run (3 runs = $0.035 total)

**GPT-4o:**
- Interpretou a tabela com 12 colunas e 1 linha de dados -- estrutura completamente diferente do GT
- Headers identificados: `["Data do Documento", "Numero do Documento", "Especie do Documento", "Aceite", ...]`
- Esta interpretacao reflete a secao de calculo do boleto como header em vez de dados
- Inconsistente entre runs (viu diferentes layouts nas 3 tentativas)
- Custo: ~$0.005/run

**Gemini 2.0 Flash:**
- Interpretou com 6 colunas (mesclou algumas colunas)
- Estrutura diferente do GT
- Mais barato ($0.001/3 runs) mas impreciso para esta tarefa
- Opcao de fallback de baixo custo se precisao nao e critica

### Conclusao Tabela Raster

Claude Sonnet 4.5 e a escolha correta para extracao de tabela raster. Os resultados mostram:
1. **Header accuracy perfeita (100%)** -- identifica as colunas corretamente
2. **Col count perfeito (4 colunas)** -- estrutura correta
3. **Unico a detectar BG color** -- relevante para fidelidade visual
4. **Row accuracy limitada (33%)** -- perde as linhas de calculo (=Valor, -Desconto, etc.)
   - Isso nao e necessariamente um problema: as linhas de calculo sao fixas no template e podem ser hardcoded pelo Stage 5 (reconstrucao)

---

## Barcode - Resultados

**Ground truth:** `boleto_barcode_ground_truth.json`
- Tipo GT: `itf-14` (Interleaved 2-of-5 / FEBRABAN padrao boleto)
- Valor GT: `null` (JPEG comprimido nao decodificavel)

| Candidato | Tipo identificado | Type Acc | Value Acc | Latencia | Custo |
|-----------|:-----------------:|:--------:|:---------:|:--------:|:-----:|
| zxing-cpp | (nao decodificado) | -- | -- | <1ms | $0 |
| gpt4o | "other" | 0% | N/A (GT=null) | ~2s | $0.001 |
| claude-sonnet | "other" | 0% | N/A (GT=null) | ~1s | $0.002 |
| gemini-flash | "other" | 0% | N/A (GT=null) | <1s | <$0.001 |

### Analise Barcode

**zxing-cpp:** Nao conseguiu decodificar o JPEG comprimido. A qualidade de imagem (comprimida na geracao do PDF) nao e suficiente para decodificacao automatica.

**Vision LLMs:** Todos identificaram como tipo "other" em vez de "itf-14". Esperado -- LLMs nao sao especializados em classificar simbologias de barcode com precisao.

**Conclusao Barcode:**
- **Recomendacao primaria:** Para boletos, o codigo de barras vetorial ja esta disponivel no PDF como texto. Nao e necessario extrair do raster.
- **Fallback:** zxing-cpp com imagem de alta resolucao (sem compressao JPEG) se necessario
- A imagem raster do barcode no boleto e estatica (fixo) -- o template pode preserva-la como imagem crop

---

## Recomendacao Final

### Por Tipo de Conteudo Raster

| Tipo | Recomendacao | Candidato | Justificativa |
|------|:------------:|-----------|---------------|
| Tabela raster | **Claude Sonnet 4.5** | `anthropic/claude-sonnet-4-5` via OpenRouter | 100% header accuracy, unico a detectar cores, consistente |
| Barcode | **PyMuPDF (vetor)** | `page.get_text()` | O valor da linha digitavel ja esta no PDF como texto vetorial |
| Barcode (fallback) | **zxing-cpp** | Alta res + sem JPEG | Funciona se imagem de boa qualidade |
| Grafico | **Claude Sonnet 4.5** | `anthropic/claude-sonnet-4-5` | Nao testado (sem PDF com grafico) -- padrao similar a tabela |
| Imagem generica | **Preservar como crop** | -- | Logos e imagens nao precisam extracao -- preservar PNG como elemento |

### Configuracao Recomendada para Story 43.2

```python
# Story 43.2: Raster table fallback via Vision
RASTER_TABLE_MODEL = "anthropic/claude-sonnet-4-5"  # via OpenRouter

# Prompt canonico validado neste spike
RASTER_TABLE_PROMPT = """Extract the table from this image. Return ONLY valid JSON:
{
  "headers": ["col1", "col2", ...],
  "rows": [["val1", "val2", ...], ...],
  "style": {
    "font_family": "Arial",
    "font_size_px": 10,
    "font_weight": "normal",
    "header_bg_color": "#RRGGBB or null",
    "cell_bg_color": "#RRGGBB or null",
    "text_color": "#RRGGBB",
    "border_color": "#RRGGBB or null",
    "border_width_px": 1
  }
}
Rules:
- Preserve Portuguese text exactly (c, a, a, e, o, u)
- Use "" for empty cells, null for undetectable style
- Include ALL rows including calculation/summary rows
- Colors in hex (#RRGGBB format)"""
```

**Nota:** Story 43.2 foi implementada com `openai/gpt-4o` como modelo padrao. Com base neste spike, recomenda-se migrar para `anthropic/claude-sonnet-4-5` em producao para melhor accuracy.

---

## Spike Costs

| Item | Custo |
|------|-------|
| GPT-4o -- 3 runs tabela + 1 run barcode | $0.0169 |
| Claude Sonnet -- 3 runs tabela + 1 run barcode | $0.0368 |
| Gemini Flash -- 3 runs tabela + 1 run barcode | $0.0012 |
| zxing-cpp | $0.00 |
| **Total gasto** | **$0.0549** |
| Budget disponivel | $5.00 |
| Budget restante | $4.9451 |

---

## Raw Outputs

Ver `docs/reports/epic-43-ocr-bakeoff/{candidate}/` para outputs completos:
- `table_run{1,2,3}.json` -- output bruto por run
- `table_result.json` -- resultado agregado com metricas
- `barcode_run1.json` -- output barcode
- `barcode_result.json` -- resultado barcode com metricas

---

## Limitacoes

1. **Azure/AWS/Google nao testados** -- candidatos cloud com maior capacidade nao puderam ser avaliados
2. **Row recall baixo** -- nenhum modelo extraiu as linhas de calculo de forma consistente
3. **Barcode nao decodificavel** -- compressao JPEG impossibilita decodificacao automatica
4. **Grafico nao testado** -- sem PDF com grafico no conjunto de referencia

---

*Gerado por `backend/scripts/spike_ocr_bakeoff.py` -- Story 43.3 | Agent: Dex (claude-sonnet-4-6)*
