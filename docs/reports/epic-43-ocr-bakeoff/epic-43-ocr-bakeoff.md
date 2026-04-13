# Epic 43 — OCR/Vision Bake-off: Extração de Conteúdo Raster

**Data:** 2026-04-13  |  **Budget gasto:** $0.1116 / $5.00

## Sumário Executivo

Bake-off empírico de candidatos para extração de conteúdo raster em PDFs do tipo boleto bancário.
Testado com `Corporate.Boleto.Convenio.pdf` — tabela raster JPEG na página 0.

**Candidatos via OpenRouter (credenciais disponíveis):**
- GPT-4o Vision (`openai/gpt-4o`)
- Claude Sonnet 4.5 Vision (`anthropic/claude-sonnet-4-5`)
- Gemini 2.0 Flash Vision (`google/gemini-2.0-flash-001`)

**Candidatos locais (free):**
- zxing-cpp (barcode decoder)

**Candidato via API direta:**
- Mistral OCR (`mistral-ocr-latest`) — endpoint dedicado OCR, retorna Markdown

**Candidato via SDK Azure:**
- Azure Document Intelligence (`prebuilt-layout`) — endpoint `docditeste.cognitiveservices.azure.com`

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

**Consequência das métricas:**
- **Claude Sonnet** → focou na Seção A → 100% header accuracy vs GT
- **Azure Doc Intel** → focou na Seção B → 0% header accuracy vs GT, mas correto sobre o que viu
- **GPT-4o / Gemini** → misturaram seções → métricas intermediárias
- **Mistral OCR** → extraiu somente Seção B em markdown → 0% vs GT da Seção A

Nenhum candidato extraiu as 3 seções de forma estruturada e completa em uma única chamada.

---

## Tabela Raster — Métricas Comparativas

Ground truth: `boleto_raster_table_ground_truth.json`
- Colunas GT (Seção A): 4  |  Linhas GT: 9
- Headers: Beneficiário, Agência/Cód. Beneficiário, Data Emissão, Vencimento

| Candidato | Header Acc | Col Acc | Row Acc | Cell F1 | PT Acc | Font | BG Color | Border | Lat p50 | Custo/3runs | Seção vista |
|-----------|:----------:|:-------:|:-------:|:-------:|:------:|:----:|:--------:|:------:|:-------:|:-----------:|:-----------:|
| **azure-doc-intel** | 0.0% | 0.0% | 22.2% | 0.0% | 0.0% | ❌ | ❌ | ❌ | 5889ms | $0.0450 | B (códigos bancários) |
| **gpt4o** | 0.0% | 0.0% | 44.4% | 3.6% | 0.0% | ✅ | ❌ | ❌ | 8981ms | $0.0241 | Misto A+B |
| **claude-sonnet** | **100.0%** | **100.0%** | 33.3% | **54.5%** | **57.1%** | ✅ | ✅ | ✅ | 9501ms | $0.0341 | A (beneficiário/pagador) |
| **gemini-flash** | 0.0% | 0.0% | 44.4% | 4.9% | 0.0% | ✅ | ❌ | ❌ | 4654ms | $0.0009 | Misto |
| **mistral-ocr** | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | ❌ | ❌ | ❌ | 1180ms | $0.0030 | B (markdown) |

**Legenda:** Header Acc = % headers GT reconhecidos | Col Acc = % colunas corretas | Cell F1 = média F1 por célula posição-matched | PT Acc = % valores em português com acentuação correta

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
| **mistral-ocr** | 0.0% | N/A (GT=null) | 1030ms | $0.0010 |

**Nota:** O valor da linha digitável (código de barras ITF-14) **não precisa ser extraído do raster** — o pipeline já captura esse valor do texto vetorial do PDF. O barcode como elemento visual é tratado como imagem estática para preservar no template.

---

## Recomendação

### Tabela Raster

**Vencedor: Claude Sonnet 4.5 Vision**

Único candidato a reconhecer corretamente os headers da Seção A (100% header accuracy), detectar font, background color e border. Cell F1 de 54.5% reflete que Claude capturou estrutura e layout corretos, mas não extraiu todas as linhas de cálculo da Seção C.

**Justificativa:**
- Header accuracy 100% vs GT — critério #1 do Decision Framework (≥95%)
- Detecção de estilo: font ✅, BG color ✅, border ✅ — único candidato completo
- Portuguese accuracy 57.1% — melhor entre todos (outros: 0%)
- Custo razoável: $0.011/run para uso one-time em ~200 templates

**Limitação conhecida:** Claude (como todos os candidatos) não extrai as 3 seções da imagem em uma única chamada estruturada. Para cobertura total da imagem, seria necessário uma segunda chamada focando nas Seções B e C.

**Fallback: Gemini 2.0 Flash Vision**

Se custo for constraint crítico: Gemini a $0.0003/run vs $0.011/run do Claude. Porém: header accuracy 0%, não detecta estilo. Usar apenas como fallback de custo com degradação de qualidade aceita.

**Azure Doc Intelligence — papel complementar:**

Azure extrai a Seção B (códigos bancários) com estrutura correta. Em workflows onde todas as 3 seções precisam ser cobertas, Azure + Claude em calls separadas podem ser combinados.

### Barcode

**Recomendação: Não extrair do raster.**

O valor da linha digitável já está disponível como texto vetorial no PDF (capturado pelo pipeline). O barcode como elemento visual é estático — preservar como image crop no template. nenhum candidato conseguiu decodificar o JPEG comprimido do boleto de produção.

Se decodificação for necessária no futuro: usar versão vetorial do barcode (se disponível no PDF) ou biblioteca especializada com imagem de qualidade (>300 DPI, sem compressão JPEG).

---

## Spike Costs

| Run | Custo |
|-----|-------|
| Run inicial (3 Vision LLMs + zxing) | $0.0549 |
| +Azure Doc Intelligence (3 runs) | $0.0485 |
| +Mistral OCR (3 runs) | $0.0082 |
| **Total acumulado** | **$0.1116** |
| Budget máximo | $5.00 |
| Budget restante | $4.8884 |

---

## Raw Outputs

Ver `docs/reports/epic-43-ocr-bakeoff/{candidate}/` para outputs completos por candidato.

Candidatos com raw outputs disponíveis:
- `azure-doc-intel/` — tables extraídas em JSON
- `gpt4o/` — respostas JSON estruturadas
- `claude-sonnet/` — respostas JSON estruturadas
- `gemini-flash/` — respostas JSON estruturadas
- `mistral-ocr/` — markdown retornado + parsed JSON
- `zxing-cpp/` — resultado de decodificação

---

*Gerado por `backend/scripts/spike_ocr_bakeoff.py` — Story 43.3*
