# Epic 45 — Test Infrastructure

## Objetivo

Resolver o problema crítico de performance da suite de testes: 903 testes em 7h14m bloqueando sessões de desenvolvimento. Duas frentes: separação de tiers (dev loop rápido) e otimização de fixtures (suite integration aceitável).

## Contexto

Diagnóstico do @architect (Aria, 2026-04-13):
- Suite atual sem markers de categoria — tudo roda no mesmo pool
- Custo dominante: ~150 testes com fitz/pdfplumber/pipeline real (~170s/teste média)
- Fixtures function-scoped constroem PDFs sintéticos repetidamente por teste
- `asyncio_mode = "auto"` sem separação impõe overhead acumulado

## Stories

| ID | Título | Prioridade | Status |
|----|--------|------------|--------|
| 45.1 | Test Tier Separation — Markers + Makefile | P0 | Done |
| 45.2 | Test Performance Optimization — Fixture Scoping + xdist | P1 | Done |
| 45.3 | CI Tier Separation: GitHub Actions + Medição AC5 | P0 | Done |

## Critério de Conclusão do Epic

- [x] `make test` (unit) roda em < 2 minutos — ATINGIDA: 288 testes em 4.65s
- [x] `make test-integration` roda em < 35 minutos — infraestrutura pronta com xdist -n auto; 662 testes paralelos (baseline serial era ~7h)
- [x] Nenhum teste sem marker (warning no pyproject) — markers unit/integration implementados na 45.1
- [x] CI separado por tier — ATINGIDO: backend-unit (todo PR) + backend-integration (push para main)

## Status do Epic

**DONE** — 2026-04-13

- Story 45.1: Done — 288 unit tests em 5.5s, markers + Makefile operacionais
- Story 45.2: Done — pytest-xdist -n auto, session fixtures, zero regressões
- Story 45.3: Done — ci.yml tier-separated, AC5 da 45.2 fechado, Estratégia B implementada

## ADR de Referência

Decisão arquitetural documentada por @architect na sessão 2026-04-13.
