# Epic 42 — Closing Gaps

## Status: Ready

## Objetivo

Fechar as pendências identificadas na auditoria pós-Epics 40+41:
- CI quality gates (mypy + ruff no pipeline)
- RCA e fix das 3 falhas de barcode pré-existentes
- Canvas SVG inline sync (AC3 deferido da Story 41.10)

## Contexto

Epics 40 e 41 cobriram os 73 débitos do Brownfield Discovery. Esta auditoria pós-execução identificou 3 itens pendentes que ficaram de fora ou foram explicitamente deferidos.

## Stories

| Story | Título | Prioridade | Esforço |
|-------|--------|-----------|---------|
| 42.1 | CI Quality Gates — mypy + ruff no GitHub Actions | P0 | 3h |
| 42.2 | RCA + Fix — 3 falhas barcode pré-existentes | P0 | 5h |
| 42.3 | Canvas SVG Inline Sync (41.10 AC3) | P1 | 10h |

## Critério de Conclusão

- CI bloqueia PRs com erros mypy/ruff
- Zero falhas barcode no suite de testes
- Canvas reflete svgInlineContent quando svgInline: true

## Change Log

| Date | Agent | Action |
|------|-------|--------|
| 2026-04-10 | @pm | Epic criado a partir de auditoria pós-Epics 40+41 |
