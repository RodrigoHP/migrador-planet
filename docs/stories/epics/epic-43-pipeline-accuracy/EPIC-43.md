# Epic 43 — Pipeline Accuracy: Boleto First-PDF Fix

## Status: Ready

## Objetivo

Corrigir as duas causas-raiz identificadas empiricamente que impedem o pipeline de processar o primeiro PDF (boleto bancário Corporate.Boleto.Convenio.pdf). Com estas correções, a taxa de mapeamento deve saltar de 17% → >80% em Layout A.

## Contexto

Diagnóstico empírico executado em 2026-04-12 contra job `f6fd4a39-...` no Supabase (PDF: Corporate.Boleto.Convenio.pdf). Baseline medido:

| Métrica | Layout A | Layout B |
|---------|----------|----------|
| Campos XSD mapeados | 8/48 (17%) | 3/48 (6%) |
| Campos obrigatórios XSD unmapped | 33/38 (87%) | — |
| Tabelas extraídas | 0/1 (0%) | 0/1 (0%) |
| Confidence score | 45/100 | 41/100 |
| anchor_detection | 51 | 25 |

### Causa Raiz #1 — Stage 3.3 Misclassification (87% unmapped)

O heurístico `≤30 chars → semantic: "label"` em Stage 3.1/3.3 classifica incorretamente blocos de VALUE como labels:

| Block ID | Texto | Classificação atual | Correta |
|----------|-------|-------------------|---------|
| c9d9361d | "RUA PARAIBUNA 456" | label | dynamic |
| 74f23df4 | "30/03/2026" | label | dynamic |
| 1c8cb3b1 | "237" | label | dynamic |
| 22672f57 | "005" | label | dynamic |
| c5632f41 | "8600" | label | dynamic |
| dc96bdf2 | "000" | label | dynamic |

Stage 3.3 cria o par `{label: "RUA PARAIBUNA 456", value: "SAO JOSE DOS CAMPOS - SP"}` com `source: "stage_3"`. O Gemini recebe este par e mapeia para `BOLETO.INSTRUCOES.INSTRUCAO` (array sem penalidade de colisão) em vez de `BOLETO.SACADO.CIDADE` / `BOLETO.SACADO.ENDERECO`.

### Causa Raiz #2 — Tabela Raster sem Fallback (0% tabelas)

A tabela de parcelas do boleto é um JPEG 2174×1337 pixels embutido no PDF. `page.find_tables()` retorna 0 (requer texto vetorial ou ruling lines). Não existe fallback Vision API quando `table_area` é detectado pela análise visual.

## Stories

| Story | Título | Status | Prioridade | Esforço | Dep |
|-------|--------|--------|-----------|---------|-----|
| 43.1 | Fix Stage 3 Semantic Classification — guardar VALUE blocks como dynamic | InReview | P0 | 8h | — |
| 43.3 | SPIKE: Bake-off Empírico de OCR/Vision para Tabela Raster | InReview | P0 | 16h | — |
| 43.4 | SPIKE: Layout Extraction (col_widths, colors) via HTML colspan + PIL | InReview | P0 | 4h | 43.3 |
| 43.2 | Fix Raster Table Extraction — trocar GPT-4o por mistral-ocr-pdf (decisão 43.3) | InReview | P0 | 10h | 43.3 |
| 43.5 | PIL Pixel Sampling Per-Row para row_bg_colors[] | Draft | P1 | 4h | 43.4 |
| 43.6 | Integrar Layout Schema completo no pipeline (font PyMuPDF + mistral + PIL) | Draft | P1 | 8h | 43.2, 43.5 |
| 43.7 | SPIKE: Estratégia de Handling para image_area no Pipeline | Draft | P1 | 4h | 43.3 |

**Total estimado:** ~54h

**Decisão arquitetural:** `mistral-ocr-pdf` como extrator primário de estrutura ($0.002/call). Font/color via PyMuPDF (vetorial, exato, grátis). Backgrounds via PIL per-row sampling (grátis). Nenhum Vision LLM necessário para estilo. Ver `docs/architecture/adr-raster-table-extraction-strategy.md`.

## Critério de Conclusão

- Taxa de mapeamento Layout A: ≥80% (de 17%)
- Campos obrigatórios XSD mapeados: ≥30/38 (de 5/38)
- Tabelas extraídas: 1/1 (de 0/1) para boleto com JPEG table
- Suite de testes passa sem regressões
- Baseline re-medido contra job Supabase após deploy

## Arquivos Principais Afetados

- `backend/services/stages/stage3_structural/multi_example_analysis.py` — heurístico `≤30 chars`
- `backend/services/stages/stage3_structural/classification.py` — classificação semântica
- `backend/services/stages/stage2_extraction/grid_table_extraction.py` — `_detect_tables` / fallback Vision
- `backend/tests/test_pipeline_orchestrator_v2.py` — testes de integração

## Change Log

| Date | Agent | Action |
|------|-------|--------|
| 2026-04-12 | @sm | Epic criado — diagnóstico empírico job f6fd4a39 baseline 17% mapping |
| 2026-04-13 | @dev (Dex) | Decisão arquitetural fechada: mistral-ocr-pdf primário, PyMuPDF para font/color, PIL per-row para backgrounds. Nenhum Vision LLM para estilo. ADR documentado. Stories 43.5 e 43.6 criadas. |
| 2026-04-13 | @aios-master (Orion) | Story 43.7 criada — spike para avaliar estratégia de image_area (Option B no-LLM vs A-Gemini); gap documentado: section_utils.py linha 469 descarta image_area silenciosamente. |
