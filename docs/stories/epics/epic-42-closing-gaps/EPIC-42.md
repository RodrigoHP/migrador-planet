# Epic 42 — Closing Gaps

## Status: Ready

## Objetivo

Fechar as pendências identificadas na auditoria pós-Epics 40+41:
- CI quality gates (mypy + ruff + TypeScript no pipeline)
- RCA e fix das 3 falhas de barcode pré-existentes
- Canvas SVG inline sync (AC3 deferido da Story 41.10)
- **Migração Pydantic completa A→B** — 309 `dict[str, Any]` em 29 arquivos → modelos tipados

## Contexto

Epics 40 e 41 cobriram os 73 débitos do Brownfield Discovery. Esta auditoria pós-execução identificou os itens pendentes abaixo, incluindo a migração Pydantic completa que não foi executada nos epics anteriores por risco/esforço.

A migração Pydantic (42.4–42.9) é a maior iniciativa do epic: transforma o pipeline de 5 stages de `dict[str, Any]` para modelos Pydantic tipados, fechando o contrato com o frontend via OpenAPI codegen. Dependências críticas: 42.1 → 42.2 → 42.4 → 42.5 → 42.6 → 42.7 → 42.8, com 42.3 e 42.9 independentes.

## Stories

| Story | Título | Prioridade | Esforço | Dep |
|-------|--------|-----------|---------|-----|
| 42.1 | CI Quality Gates — mypy + ruff no GitHub Actions | P0 | 3h | — |
| 42.2 | RCA + Fix — 3 falhas barcode pré-existentes | P0 | 5h | — |
| 42.3 | Canvas SVG Inline Sync (41.10 AC3) | P1 | 10h | — |
| 42.4 | Stage 1+2 Pydantic Migration | P1 | 8h | 42.1, 42.2 |
| 42.5 | Stage 3 Pydantic Migration (Structural Analysis) | P1 | 16h | 42.4 |
| 42.6 | Stage 4+5 Pydantic Migration | P1 | 14h | 42.5 |
| 42.7 | Pydantic Contract Tightening (extra="forbid" + mypy zero) | P1 | 8h | 42.6 |
| 42.8 | Frontend TypeScript Alignment + OpenAPI Codegen | P1 | 7h | 42.7 |
| 42.9 | Frontend CI TypeScript Gate | P1 | 2h | paralelo c/ 42.8 |

**Total estimado:** ~73h

## Critério de Conclusão

- CI bloqueia PRs com erros mypy/ruff/TypeScript/ESLint
- Zero falhas barcode no suite de testes
- Canvas reflete svgInlineContent quando svgInline: true
- 100% pipeline stages com modelos Pydantic (zero `dict[str, Any]` em produção)
- `extra="forbid"` em todos os 16 modelos de `pipeline_context.py`
- `response_model` declarado no endpoint `/api/v1/analyze/{job_id}/result`
- `tsc --noEmit` sem erros — tipos frontend alinhados com backend
- OpenAPI codegen configurado no CI (ou fix manual documentado)

## Change Log

| Date | Agent | Action |
|------|-------|--------|
| 2026-04-10 | @pm | Epic criado a partir de auditoria pós-Epics 40+41 |
| 2026-04-10 | @architect | Stories 42.4-42.9 adicionadas — plano completo migração Pydantic A→B |

## Débitos Técnicos Identificados Pós-Epic

| ID | Arquivo | Descrição | Prioridade |
|----|---------|-----------|-----------|
| DT-42-1 | `tests/schemas/contract_3_2.json` vs `models/pipeline_context.py::FontInfo` | Schema espera `font_family/font_size/font_weight/font_style`; modelo produz `name/css_family/size/is_bold/is_italic`. 5 testes em `test_stage1_stage2_integration.py` falhando desde Epic 13. | P1 |
| DT-42-2 | `services/stages/stage5_template/coverage_overlay.py` | RCA Fix 2 parcialmente aplicado — `_generate_anchors` agora prefere `xsd_path`, mas `label_text` ainda não é o campo primário conforme fix_requirements original. | P2 |
| DT-42-3 | `models/pipeline_context.py::PipelineResult` | `field_mappings/document_structure/confidence_scores` usam `list[dict[str, Any]]` — gera `{ [key: string]: unknown }[]` no TypeScript (Story 42.13 AC3/AC4 adiados). | P2 |
| DT-42-4 | `backend/=1.20.0` | Arquivo órfão de `pip install =1.20.0` (typo). Deletar. | P3 |
