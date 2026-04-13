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
| 45.3 | CI Tier Separation: GitHub Actions + Medição AC5 | P0 | Ready |

## Critério de Conclusão do Epic

- `make test` (unit) roda em < 2 minutos
- `make test-integration` roda em < 35 minutos
- Nenhum teste sem marker (warning no pyproject)
- CI separado por tier

## Status do Epic

**InProgress** — aguardando 45.3

- Story 45.1: Done — 288 unit tests em 5.5s, markers + Makefile operacionais
- Story 45.2: Done — pytest-xdist -n auto, session fixtures, zero regressões
- Story 45.3: Ready — atualizar ci.yml + medir baseline integration (fecha AC5 da 45.2)
- Meta `make test` (unit) < 2 min: **ATINGIDA** (5.5s)
- Meta `make test-integration` < 35 min: infraestrutura pronta, medição pendente (45.3)
- Meta CI separado por tier: **pendente** (45.3)

## ADR de Referência

Decisão arquitetural documentada por @architect na sessão 2026-04-13.
