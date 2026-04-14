# Epic 41 — Technical Debt Backlog Cleanup

## Objetivo

Resolver os 32 debitos tecnicos deferidos do Brownfield Discovery (Epic 40) que nao foram priorizados na primeira passada. Organizados em 3 waves por impacto e complexidade: quick wins, refatoracao backend/frontend, e melhorias operacionais.

## Fonte

- Assessment: `docs/prd/technical-debt-assessment.md` (secao "Deferidos")
- Epic 40 resolveu 38 debitos; este epic cobre os 32 restantes
- DB-017 excluido (ja resolvido na Story 40.8)
- UX-002 excluido (decisao de produto: desktop-only)
- UX-003 excluido (removido por @ux-design-expert)

## Resumo

| Metrica | Valor |
|---------|-------|
| Total de debitos | 32 |
| Esforco estimado | ~97h |
| Stories | 8 |
| Waves | 3 |

## Waves

### Wave 1: Quick Wins & Code Hygiene (Stories 41.1-41.2, ~13h)

Fixes triviais que podem ser feitos em batch, sem risco de regressao.

| Story | Titulo | Horas | Debitos |
|-------|--------|-------|---------|
| 41.1 | Micro Quick Wins | 7h | SYS-007, SYS-021, DB-010, DB-013, DB-014, REDIS-001, FE-005, FE-007, SEC-002 |
| 41.2 | Code Hygiene & Cleanup | 6h | SYS-005, SYS-009, UX-008, FE-009 |

**Criterio de conclusao:** Zero dead code. Zero console.log em producao. CSS approach unificado.

### Wave 2: Backend & Frontend Refactoring (Stories 41.3-41.6, ~57h)

Refatoracoes mais substanciais que requerem testes cuidadosos.

| Story | Titulo | Horas | Debitos |
|-------|--------|-------|---------|
| 41.3 | Backend Stage Decomposition | 16h | SYS-011 |
| 41.4 | Database & Redis Resilience | 17h | DB-006, DB-011, DB-015, REDIS-002, REDIS-003 |
| 41.5 | Frontend DX & Store Consistency | 8h | FE-004, SYS-008 |
| 41.6 | UX Polish & Accessibility Extras | 8h | UX-004, UX-010, A11Y-004 |

**Criterio de conclusao:** Maior stage file < 500 LOC. Redis com retry/reconnection. Store API padronizada. Skeleton screens no editor.

### Wave 3: Operations & Performance (Stories 41.7-41.8, ~21h)

Melhorias operacionais e de performance que requerem monitoramento previo.

| Story | Titulo | Horas | Debitos |
|-------|--------|-------|---------|
| 41.7 | Operational Improvements | 9h | SYS-017, SYS-018, SYS-019 |
| 41.8 | Performance & Testing Gaps | 12h | PERF-001, PERF-003, TEST-004 |

**Criterio de conclusao:** Health check profundo. API versionada. Tree virtualizada para docs grandes. LoginPage com testes.

## Inventario Completo de Debitos

### Wave 1 — Quick Wins

| ID | Debito | Sev. | Esforco | Story |
|----|--------|------|---------|-------|
| SYS-007 | Dead code/scaffolding (HelloWorld.vue etc.) | LOW | 1h | 41.1 |
| SYS-021 | faker como prod dependency | LOW | 0.5h | 41.1 |
| DB-010 | Indice created_at em jobs | LOW | 0.5h | 41.1 |
| DB-013 | FK templates->jobs | LOW | 1h | 41.1 |
| DB-014 | UPDATE policy storage | LOW | 0.5h | 41.1 |
| REDIS-001 | Prefixo app nas keys Redis | LOW | 0.5h | 41.1 |
| FE-005 | Consolidar ConfidenceBadge duplicado | LOW | 1h | 41.1 |
| FE-007 | Barrel export composables | LOW | 0.5h | 41.1 |
| SEC-002 | DOMPurify upgrade (seguranca transitiva) | MEDIUM | 1h | 41.1 |
| SYS-005 | TMP_BASE duplicado | LOW | 2h | 41.2 |
| SYS-009 | console.log em producao | LOW | 2h | 41.2 |
| UX-008 | Console.log producao (perspectiva UX) | LOW | 0h | 41.2 |
| FE-009 | CSS approach consistencia | LOW | 2h | 41.2 |

### Wave 2 — Refactoring

| ID | Debito | Sev. | Esforco | Story |
|----|--------|------|---------|-------|
| SYS-011 | Stage files monoliticos (backend, maior ~2K LOC) | MEDIUM | 16h | 41.3 |
| DB-006 | Rollback migrations | MEDIUM | 6h | 41.4 |
| DB-011 | Soft-delete para jobs | MEDIUM | 3h | 41.4 |
| DB-015 | Fix recursive storage listing (nao atomico) | MEDIUM | 3h | 41.4 |
| REDIS-002 | Retry + reconnection Redis | MEDIUM | 4h | 41.4 |
| REDIS-003 | scan_iter em all_jobs() | LOW | 1h | 41.4 |
| FE-004 | Padronizar store API (Options vs Composition) | LOW | 4h | 41.5 |
| SYS-008 | Organizacao diretorio componentes | LOW | 4h | 41.5 |
| UX-004 | Skeleton screens editor | MEDIUM | 4h | 41.6 |
| UX-010 | Erros contextuais upload | MEDIUM | 2h | 41.6 |
| A11Y-004 | Alt texts em imagens | MEDIUM | 2h | 41.6 |

### Wave 3 — Operations & Performance

| ID | Debito | Sev. | Esforco | Story |
|----|--------|------|---------|-------|
| SYS-017 | Health check profundo | MEDIUM | 4h | 41.7 |
| SYS-018 | spaCy model mismatch | LOW | 1h | 41.7 |
| SYS-019 | API versioning | MEDIUM | 4h | 41.7 |
| PERF-001 | Tree virtualization (docs 50+ nodes) | MEDIUM | 8h | 41.8 |
| PERF-003 | Monaco bundle optimization | LOW | 2h | 41.8 |
| TEST-004 | LoginPage unit tests | MEDIUM | 2h | 41.8 |

## Exclusoes

| ID | Debito | Razao |
|----|--------|-------|
| DB-017 | Guard save_result() | Ja resolvido na Story 40.8 |
| UX-002 | Responsive/mobile | Decisao de produto: desktop-only |
| UX-003 | Dark mode | Removido por @ux-design-expert |

## Dependencias

- Epic 40 (completo, PRs #66-70 mergeados)
- Story 41.3 depende de mypy configurado (Story 40.3, done)
- Story 41.5 depende de ESLint configurado (Story 40.4, done)
- Story 41.4 depende de Redis async (Story 40.8, done)

## Riscos

| Risco | Probabilidade | Mitigacao |
|-------|--------------|-----------|
| SYS-011 (stage decomposition) quebra pipeline | MEDIA | Testes E2E da Story 40.9 como safety net |
| DB-006 (rollback migrations) falha em producao | BAIXA | Testar em staging primeiro |
| PERF-001 (tree virtualization) degrada UX | BAIXA | Feature flag + benchmark antes/depois |
| FE-004 (store migration) introduz bugs | MEDIA | Migrar 1 store por vez, testar cada |
