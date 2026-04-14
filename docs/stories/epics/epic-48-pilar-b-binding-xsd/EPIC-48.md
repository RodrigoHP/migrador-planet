# Epic 48 — Pilar B: Binding XSD — Validação Multi-Sample

## Status: Ready

## Objetivo

Validar e completar o binding de campos detectados para XSD com input multi-sample (3+ PDFs do mesmo template). Ao final deste epic, o Pilar B deve ser declarado **completo** ou ter um backlog de gaps explícito com estimativa de esforço de correção.

## Contexto

O Epic 47 validou que o Pilar A (Detecção Estrutural) funciona corretamente para todos os tipos de documento Planet Express — em modo single-PDF. Mas o workflow real exige **3+ PDFs do mesmo template** para que o pipeline possa:

1. **Stage 1** — Agrupar as páginas de instâncias idênticas em um único cluster
2. **Stage 3.1** — Comparar blocos entre instâncias para distinguir `dynamic` (muda entre instâncias) vs `static`/`label` (igual em todas)
3. **Stage 4** — Mapear campos `dynamic` para paths XSD via Gemini Flash

Nenhum destes três stages foi validado com multi-sample real. O pipeline foi desenvolvido assumindo este cenário, mas **nunca testado com 3+ instâncias do mesmo template**.

**Gaps aceitos no Epic 47 que este epic resolve:**

| Gap | Ação no Epic 48 |
|-----|----------------|
| Multi-sample clustering não validado | 48.4 — SPIKE com Railway API |
| Crash PDFs misturados (defensive) | 48.2 — fix Stage 1 guard |
| Infra Railway degradada | 48.1 — DevOps fix |

**Pré-requisito (não story — responsabilidade do usuário):**
- Adquirir **3+ PDFs do mesmo template** para pelo menos 2 tipos de documento (ex.: 3 boletos Corporate de meses diferentes, 3 relatórios PosicaoConsolidada de datas diferentes)

## Stories

| Story | Título | Status | Prioridade | Esforço | Dep |
|-------|--------|--------|-----------|---------|-----|
| 48.1 | DevOps: Corrigir Railway — pt_core_news_sm + Redis + MISTRAL_API_KEY | Ready | P0 | 2h | — |
| 48.2 | Defensive: Corrigir crash Stage 1 com PDFs de templates misturados | Ready | P1 | 2h | — |
| 48.3 | SPIKE: Ground truth multi-sample — comparar blocos entre instâncias do mesmo template | Ready | P0 | 4h | — |
| 48.4 | SPIKE: Validar Stage 1 clustering + Stage 3.1 dynamic/static com input multi-sample | Ready | P0 | 6h | 48.1 + 48.3 |
| 48.5 | SPIKE: Validar Stage 4 XSD binding accuracy com resultado multi-sample | Ready | P0 | 4h | 48.4 |
| 48.6 | Consolidação: declarar Pilar B completo ou abrir backlog de gaps | Ready | P0 | 2h | 48.4 + 48.5 |

**Total estimado:** ~20h

**Paralelismo possível:** 48.1 e 48.2 e 48.3 podem rodar em paralelo (sem dependências entre si).

## Método de Validação

Para cada tipo de documento (com 3+ instâncias do mesmo template):

1. Subir 3+ PDFs via API Railway (POST `/api/analyze` com múltiplos arquivos)
2. Capturar output JSON do job
3. Verificar Stage 1: número de clusters = número de layouts distintos do template (não = número de PDFs)
4. Verificar Stage 3.1: campos que mudam entre instâncias marcados `likely_dynamic`; campos fixos marcados `label`/`static`
5. Verificar Stage 4: `field_mappings[]` com `xsd_field_path` preenchido por campo `dynamic`
6. Calcular accuracy: (campos dynamic mapeados corretamente) / (total campos dynamic ground truth)

## Critério de Conclusão do Epic

- Railway infrastructure funcional: spaCy `pt_core_news_sm`, Redis configurado, MISTRAL_API_KEY ativo
- Crash defensivo corrigido: pipeline não falha quando PDFs misturados submetidos
- Multi-sample clustering validado: 3 instâncias de boleto Corporate → 1 cluster (não 3)
- Stage 3.1 validado: campos `valor_boleto`, `data_vencimento` marcados `dynamic`; `banco_nome`, labels fixos marcados `label`/`static`
- Stage 4 validado: mapeamento campo → XSD path com accuracy ≥ 80%
- Story 48.6 produz decisão formal: **PILAR B COMPLETO** ou **GAPS DOCUMENTADOS**

## Arquivos Relevantes

- `backend/services/stages/stage1_clustering/` — Stage 1 (clustering multi-PDF)
- `backend/services/stages/stage3_structural/multi_example_analysis.py` — Stage 3.1 (dynamic vs static)
- `backend/services/stages/stage4_mapping/` — Stage 4 (XSD binding via Gemini Flash)
- `backend/tests/fixtures/samples/` — fixtures de PDFs reais (gitignored)
- `docs/reports/epic-47/pipeline-single-pdf-results.json` — baseline single-PDF para comparação

## Change Log

| Date | Agent | Action |
|------|-------|--------|
| 2026-04-14 | @pm | Epic criado — 6 stories baseadas nos gaps aceitos do Epic 47. Foco: validar pipeline multi-sample end-to-end (Stage 1 clustering + Stage 3.1 dynamic/static + Stage 4 XSD binding) |
