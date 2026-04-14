# Epic 40 — Technical Debt Resolution

## Objetivo

Resolver os 73 debitos tecnicos identificados no Brownfield Discovery, priorizando seguranca, estabilidade e qualidade. Organizado em 4 waves progressivas: quick wins de seguranca, infraestrutura de qualidade, safety nets + refatoracao, e testes + polish.

## Fonte

- Assessment: `docs/prd/technical-debt-assessment.md`
- QA Gate: APPROVED (8.5/10) por @qa (Quinn)
- Consolidado por @architect (Aria) -- Brownfield Discovery Phase 8

## Resumo

| Metrica | Valor |
|---------|-------|
| Total de debitos unicos | 73 |
| Debitos endererados neste epic | 38 (ativos) |
| Debitos deferidos | 35 (backlog separado) |
| Esforco estimado | ~215h efetivas |
| Stories | 11 |
| Waves | 4 |

## Waves

### Wave 1: Quick Wins + Security Foundation (Stories 40.1-40.2)

Eliminar riscos de seguranca criticos e quick wins de zero risco. Foco em data security chain (RLS, multi-tenancy, service role scoping).

| Story | Titulo | Horas | Debitos |
|-------|--------|-------|---------|
| 40.1 | DB Quick Wins & Security Patches | 4.5h | DB-012, DB-016, SEC-003, DB-004, DB-005, DB-009 |
| 40.2 | Data Security Chain | 24h | DB-002, DB-001, DB-003, SEC-001, SYS-015 |

**Criterio de conclusao:** Zero debitos CRITICAL de seguranca. RLS com owner-based access. Service role scoped.

### Wave 2: Quality Infrastructure (Stories 40.3-40.4)

Estabelecer quality gates automatizados no backend e frontend.

| Story | Titulo | Horas | Debitos |
|-------|--------|-------|---------|
| 40.3 | Python Quality Infrastructure | 8h | SYS-001, SYS-002 |
| 40.4 | Frontend Quality Infrastructure | 16h | SYS-003, SYS-013, SYS-010, SEC-004 |

**Criterio de conclusao:** CI passa lint + typecheck. Pre-commit hooks ativos. `any` count < 20.

### Wave 3: Frontend Safety Net + Core Refactoring (Stories 40.5-40.8)

Estabelecer safety nets antes de refatorar componentes core. Pipeline typed. State unification.

| Story | Titulo | Horas | Debitos |
|-------|--------|-------|---------|
| 40.5 | Frontend Safety Net | 14h | UX-006, SYS-012, UX-007, A11Y-001, UX-001, A11Y-003 |
| 40.6 | Frontend God Objects Decomposition | 18h | FE-003, FE-001, FE-002 |
| 40.7 | Pipeline Typed Context | 12h | SYS-014 |
| 40.8 | Backend Async & State Unification | 17h | DB-008, DB-007, REDIS-004 |

**Criterio de conclusao:** Maior arquivo frontend < 500 LOC. Pipeline context typed. Redis como SSOT.

### Wave 4: Tests, Performance & Polish (Stories 40.9-40.11)

E2E coverage, performance do undo/redo, polish visual e acessibilidade.

| Story | Titulo | Horas | Debitos |
|-------|--------|-------|---------|
| 40.9 | E2E Test Framework | 16h | TEST-001 |
| 40.10 | UX Polish & Accessibility | 9h | UX-005, UX-009, FE-008, A11Y-002 |
| 40.11 | Component Tests & Undo Performance | 24h | TEST-002, TEST-003, PERF-002 |

**Criterio de conclusao:** 4+ E2E smoke tests passando. Undo sem frame drops. Atoms coverage > 50%.

## Debitos Deferidos (nao incluidos neste epic)

35 debitos de baixo impacto ou alto custo/beneficio desfavoravel. Ver secao "Deferidos" no assessment para lista completa. Incluem: responsive/mobile (UX-002), dark mode (UX-003), skeleton screens (UX-004), tree virtualization (PERF-001), Monaco optimization (PERF-003), store API padronization (FE-004), e diversos itens de DX/manutencao.

## Metricas de Sucesso

| Metrica | Baseline Atual | Target |
|---------|---------------|--------|
| Debitos CRITICAL | 6 | 0 |
| Debitos HIGH | 19 | <= 5 |
| RLS coverage | 0% (USING true) | 100% owner-based |
| Backend async compliance | 0% | 100% |
| Frontend test coverage (atoms) | 12% | 50%+ |
| E2E smoke tests | 0 | >= 4 flows |
| `any` count TypeScript | 80 | < 20 |
| Maior arquivo LOC (frontend) | 1,195 | < 500 |
| WCAG AA violations | 2 | 0 |
| Known vulnerabilities (npm) | >= 2 | 0 |
| Security headers | 0/5 | 5/5 |

## Estimativa Total

~215h efetivas (~297h incluindo itens deferidos)

## Dependencias entre Stories

```
40.1 (quick wins) -----> 40.2 (DB-002 desbloqueia DB-001/DB-003)
40.3 (Python lint) ----> 40.7 (SYS-014 depende de SYS-002/mypy)
40.4 (Frontend lint) --> 40.4 interno (SYS-013 depende de SYS-003)
40.5 (safety net) -----> 40.6 (refactor depende de error boundary + guards)
40.7 + 40.8 podem rodar em paralelo
40.9..40.11 independentes entre si
```
