# Technical Debt Assessment -- FINAL

**Projeto:** Migrador Planet Express (PDF-to-HTML Template Migration Tool)
**Data:** 2026-04-09
**Versao:** 1.0 (Final)
**Consolidado por:** @architect (Aria) -- Brownfield Discovery Phase 8
**Aprovado por:** @qa (Quinn) -- Gate APPROVED 8.5/10

---

## Executive Summary

| Metrica | Valor |
|---------|-------|
| **Total de debitos unicos** | 73 |
| **CRITICAL** | 6 |
| **HIGH** | 19 |
| **MEDIUM** | 25 |
| **LOW** | 23 |
| **Esforco total estimado** | ~297h |
| **Esforco efetivo (excluindo deferidos)** | ~215h |
| **Duplicatas removidas** | 4 (SYS-022=PERF-002, SYS-020=TEST-001, SYS-006=FE-003, FE-006 incluso em SYS-007) |
| **Debitos adicionados por especialistas** | 10 (DB-015..017, REDIS-004, UX-006..010, SEC-004) |
| **Cross-cutting patterns** | 8 (CC-001..CC-008) |

**Distribuicao por area:**

| Area | Debitos | CRITICAL | HIGH | MEDIUM | LOW |
|------|---------|----------|------|--------|-----|
| Sistema (SYS-*) | 19 | 4 | 3 | 8 | 5 |
| Database (DB-*) | 17 | 2 | 6 | 4 | 3 |
| Redis (REDIS-*) | 4 | 0 | 0 | 2 | 2 |
| Frontend (FE-*) | 8 | 0 | 3 | 1 | 4 |
| UX (UX-*) | 10 | 0 | 2 | 3 | 5 |
| Acessibilidade (A11Y-*) | 4 | 0 | 1 | 2 | 1 |
| Seguranca (SEC-*) | 4 | 0 | 3 | 1 | 0 |
| Performance (PERF-*) | 3 | 0 | 0 | 2 | 1 |
| Testes (TEST-*) | 4 | 0 | 1 | 2 | 1 |

**Topologia de risco:** Os debitos CRITICAL concentram-se em infraestrutura de codigo (vendored deps, sem linting, pipeline untyped). A cadeia de seguranca DB-001 + DB-002 + DB-003 (agora HIGH apos ajuste de @data-engineer) representa o maior risco de seguranca da aplicacao. O frontend carece de safety nets (sem error boundary, sem confirmacao de saida, sem E2E) amplificando o risco de qualquer refatoracao.

**Ajustes de severidade aplicados:**

| ID | DRAFT | Final | Especialista | Justificativa |
|----|-------|-------|-------------|---------------|
| DB-003 | CRITICAL | HIGH | @data-engineer | Service role eh necessario para storage; risco eh uso indiscriminado, nao a key em si |
| DB-006 | HIGH | MEDIUM | @data-engineer | Schema simples (3 tabelas), rollback manual viavel |
| DB-010 | MEDIUM | LOW | @data-engineer | Volume insuficiente (<1K rows) para justificar indice |
| FE-004 | MEDIUM | LOW | @ux-design-expert | Zero impacto UX, puro DX debt |
| SYS-012 | MEDIUM | HIGH | @qa | Mesmo problema que UX-006; tela branca eh impacto direto no usuario |

---

## 1. Inventario Completo de Debitos

### 1.1 Sistema (validado por @architect) -- 19 debitos

#### CRITICAL (4)

| ID | Debito | Impacto | Esforco |
|----|--------|---------|---------|
| SYS-001 | **Vendored dependencies (32MB)** -- `backend/vendor/` contem openai, pydantic, httpx vendorados. Patches de seguranca nao aplicados automaticamente. `conftest.py` adiciona vendor ao `sys.path`. | Seguranca, tamanho do repo | 4h |
| SYS-002 | **Sem linter/formatter Python** -- Sem `pyproject.toml`, `ruff.toml`, `mypy.ini`. Sem type checking apesar de type hints extensivos. | Qualidade, consistencia | 4h |
| SYS-003 | **Sem ESLint/Prettier (Frontend)** -- Sem configuracao de linting/formatting. `vue-tsc --noEmit` eh o unico quality gate. | Qualidade, consistencia | 4h |
| SYS-014 | **Pipeline context untyped (`Dict[str, Any]`)** -- 123 ocorrencias em 20 arquivos. Contratos entre stages documentados em markdown mas nao enforced pelo type system. | Type safety, debugging | 12h |

#### HIGH (3)

| ID | Debito | Impacto | Esforco |
|----|--------|---------|---------|
| SYS-004 | **Dual job state management** -- `_pipeline_jobs` (in-memory) + `job_store` (Redis) + Supabase. Split-brain em crash. `recover_running_jobs()` existe mas NAO eh chamado no lifespan. | Consistencia, confiabilidade | 8h |
| SYS-012 | **Sem error boundary/global error handler** -- Nenhum `app.config.errorHandler` em `main.ts`. Erros nao capturados = tela em branco. Sentry DSN no `.env.example` mas nao usado. **Severidade elevada de MEDIUM para HIGH por recomendacao de @qa (alinhamento com UX-006).** | UX, error recovery | 4h |
| SYS-015 | **Sem security headers** -- CORS overly permissive (`allow_methods=["*"]`). Sem CSP, X-Frame-Options, HSTS. | Seguranca (OWASP A05) | 4h |

#### MEDIUM (7)

| ID | Debito | Impacto | Esforco |
|----|--------|---------|---------|
| SYS-005 | **`TMP_BASE` duplicado em 3 arquivos** | Manutencao | 2h |
| SYS-008 | **Organizacao de componentes inconsistente** -- `components/` ao lado de atoms/molecules/organisms | DX, discoverability | 4h |
| SYS-010 | **80 ocorrencias de `any` em TypeScript** -- 28 arquivos incluindo producao | Type safety | 6h |
| SYS-011 | **Stage files monoliticos** -- stage3 (2,048 LOC), stage5 (2,008 LOC), stage1 (1,403 LOC) | Manutencao, testabilidade | 16h |
| SYS-013 | **Sem pre-commit hooks** -- Sem `.husky/` ou `.pre-commit-config.yaml` | Quality enforcement | 2h |
| SYS-016 | **Supabase project ref hardcoded no CI** | Portabilidade, seguranca | 1h |
| SYS-018 | **spaCy model mismatch** -- Instala `pt_core_news_sm`, tenta carregar `pt_core_news_lg` | Acuracia NLP | 1h |

#### LOW (5)

| ID | Debito | Impacto | Esforco |
|----|--------|---------|---------|
| SYS-007 | **Dead code e scaffolding** -- `HelloWorld.vue`, `backend/_deprecated/` (223 LOC), `vue.svg`, `@faker-js/faker` como prod dep. **Inclui FE-006 (duplicata removida).** | Limpeza | 1h |
| SYS-009 | **`console.log/warn/error` em producao** -- 10 chamadas em 6 arquivos | Observabilidade | 2h |
| SYS-017 | **Health check superficial** -- `/api/health` sem checar Redis, Supabase ou disco | Observabilidade | 4h |
| SYS-019 | **Sem API versioning** -- Rotas em `/api/` sem prefixo de versao, sem OpenAPI | Evolucao da API | 4h |
| SYS-021 | **`@faker-js/faker` como dep de producao** | Bundle size | 0.5h |

---

### 1.2 Database (validado por @data-engineer) -- 17 debitos

#### CRITICAL (2)

| ID | Debito | Impacto | Esforco |
|----|--------|---------|---------|
| DB-001 | **RLS policies com `USING (true)`** -- Todas as 3 tabelas e storage buckets. Qualquer usuario autenticado le/modifica/deleta dados de outro. | Seguranca: exposicao completa de dados | 8h |
| DB-002 | **Sem multi-tenancy / `user_id`** -- Nenhuma tabela tem `user_id`. Bloqueia DB-001 e DB-003. Requer migration + backfill + application code + testes. | Seguranca, compliance | 12h |

#### HIGH (6)

| ID | Debito | Impacto | Esforco |
|----|--------|---------|---------|
| DB-003 | **Service role key -- uso indiscriminado** -- Backend usa service role para TODAS as operacoes. **Rebaixado de CRITICAL por @data-engineer:** service role eh necessario para storage (upload, download, signed URLs); o debito eh usa-la para queries de tabela sem necessidade. Solucao: dois clientes Supabase (admin para storage, user para queries). | Seguranca: key leak = acesso irrestrito | 4h |
| DB-004 | **`jobs.updated_at` sem trigger** -- Trigger existe para `templates` mas nao para `jobs`. Copy-paste do pattern existente. | Integridade de dados | 1h |
| DB-005 | **`jobs.status` sem CHECK constraint** -- Aceita qualquer texto. Valores validos: `pending`, `running`, `completed`, `failed`, `cancelled`. | Integridade de dados | 1h |
| DB-007 | **Supabase SDK sincrono em contexto async** -- `supabase-py` v2 eh sincrono. Todas as chamadas bloqueiam event loop. Solucao recomendada por @data-engineer: `asyncio.to_thread()`. | Performance: throughput limitado | 6h |
| DB-008 | **Dual state stores (3 lugares)** -- Job state em in-memory + Redis + Supabase sem garantia transacional. Agravado por DB-016 (recover nao chamado) e DB-017 (save_result sem guard). | Confiabilidade | 8h |
| DB-016 | **`recover_running_jobs()` nao eh chamado no lifespan** -- Funcao existe em `job_store.py:195-217` mas NUNCA eh chamada. Jobs `running` permanecem em estado fantasma apos restart. **Adicionado por @data-engineer.** | Confiabilidade | 0.5h |

#### MEDIUM (4)

| ID | Debito | Impacto | Esforco |
|----|--------|---------|---------|
| DB-006 | **Sem rollback migrations** -- Apenas arquivos "up". **Rebaixado de HIGH por @data-engineer:** com 4 migration files e schema simples, risco operacional eh baixo. | Operacoes | 6h |
| DB-009 | **Buckets nao criados nas migrations** -- SQL de criacao comentado em `20260322000003`. | Operacoes | 1h |
| DB-011 | **Cleanup de storage nao atomico** -- `delete_job()` falha parcial = arquivos orfaos. Bug adicional: lista apenas top-level, subdiretorios nao sao removidos (ver DB-015). | Integridade de dados | 4h |
| DB-012 | **Sem safeguard `AUTH_DISABLED` em producao** -- `_AUTH_DISABLED` lido sem check de environment em `middleware/auth.py:33`. | Seguranca: bypass acidental | 0.5h |
| DB-015 | **`delete_job()` nao lista subdiretorios no storage** -- `list(f"jobs/{job_id}")` retorna apenas raiz; arquivos em `pdfs/`, `screenshots/`, `thumbnails/`, `assets/` nao sao removidos. **Adicionado por @data-engineer.** | Integridade de dados | 2h |

#### LOW (3)

| ID | Debito | Impacto | Esforco |
|----|--------|---------|---------|
| DB-010 | **Sem indice `created_at` em `jobs`** -- **Rebaixado de MEDIUM por @data-engineer:** volume atual (dezenas/centenas de jobs) torna sequential scan aceitavel. Indice so se justifica com >10K rows. | Performance futura | 0.5h |
| DB-013 | **`templates` sem FK para `jobs`** -- Por design, templates sao independentes. FK opcional. | Traceability | 1h |
| DB-014 | **Sem UPDATE policy em `storage.objects`** -- Impacto minimo; backend usa service role. | Menor | 0.5h |
| DB-017 | **`save_result()` faz upsert sem condicao de status** -- Pode sobrescrever `cancelled`/`failed` para `completed`. **Adicionado por @data-engineer.** | Integridade de dados | 1h |

---

### 1.3 Redis (validado por @data-engineer) -- 4 debitos

| ID | Debito | Severidade | Impacto | Esforco |
|----|--------|-----------|---------|---------|
| REDIS-001 | Sem prefixo de app nas keys (`job:{id}` sem namespace) | LOW | Colisao se Redis compartilhado | 0.5h |
| REDIS-002 | Sem reconnection / circuit breaker -- fallback para InMemory so no startup | MEDIUM | Confiabilidade | 4h |
| REDIS-003 | `all_jobs()` usa `scan_iter` -- full keyspace scan | LOW | Performance (aceitavel com TTL 1h) | 1h |
| REDIS-004 | **Redis client sincrono em contexto async** -- `redis.from_url()` em vez de `redis.asyncio.from_url()`. Mesmo pattern que DB-007. **Adicionado por @data-engineer.** | MEDIUM | Performance | 3h |

---

### 1.4 Frontend (validado por @ux-design-expert) -- 8 debitos

| ID | Debito | Severidade | Impacto UX | Esforco |
|----|--------|-----------|------------|---------|
| FE-001 | **AnalyzingPage.vue (1,195 LOC)** -- Stepper, state machine, checkpoint, cancellation, reconnection misturados. Decompor em composable `useAnalyzingStateMachine()` + sub-componentes por estado. | HIGH | MEDIO -- bugs no stepper impactam confianca | 8h |
| FE-002 | **HTMLCanvas.vue (913 LOC)** -- Rendering, zoom, scroll, keyboard, drag/drop, iframe management misturados. Extrair para composables: `useCanvasZoom`, `useCanvasDrag`, `useCanvasIframe`, `useCanvasKeyboard`. | HIGH | ALTO -- canvas eh 90% do tempo do usuario | 6h |
| FE-003 | **session.ts (534 LOC)** -- `loadFromPipelineResult()` ~150 linhas orquestrando 10+ stores. **Primario; SYS-006 removido como duplicata.** | HIGH | MEDIO -- bugs de carregamento degradam editor | 4h |
| FE-004 | **Mixed store API styles** -- 8 Composition, 9 Options. **Rebaixado de MEDIUM para LOW por @ux-design-expert:** zero impacto UX, puro DX. Migrar por oportunidade. | LOW | NENHUM | 4h |
| FE-005 | ConfidenceBadge duplicado em atoms/ e molecules/ | LOW | BAIXO | 1h |
| FE-007 | Sem barrel export para composables | LOW | NENHUM | 0.5h |
| FE-008 | **Design tokens duplicados** -- Cores em `main.css @theme` E `tailwind.config.ts`. Risco de drift visual. | MEDIUM | MEDIO | 2h |
| FE-009 | CSS approach inconsistente (Tailwind utilities vs BEM scoped) | LOW | BAIXO | 2h |

---

### 1.5 UX (validado por @ux-design-expert) -- 10 debitos

| ID | Debito | Severidade | Impacto UX | Esforco |
|----|--------|-----------|------------|---------|
| UX-001 | **Sem toast/notification store global** -- Toasts via `defineExpose`, impossivel disparar de stores/services. | MEDIUM | ALTO | 3h |
| UX-002 | Sem responsive/mobile -- editor desktop-only by design | LOW | BAIXO | 16h+ |
| UX-003 | Sem dark mode -- **removido do catalogo ativo por @ux-design-expert** (custo alto, confunde percepcao de cores em editor PDF). Mantido como registro. | LOW | BAIXO | 16h+ |
| UX-004 | Sem skeleton screens no editor | LOW | MEDIO | 4h |
| UX-005 | **Emoji icons no toolbar** -- Emojis literais renderizam diferente entre OS. Substituir por lucide-vue-next (Map, ArrowLeftRight, Magnet, Ruler). | MEDIUM | ALTO | 2h |
| UX-006 | **Sem error boundary global** -- `app.config.errorHandler` ausente. Erro nao capturado = tela em branco sem feedback. Cross-ref SYS-012 (mesmo problema, perspectiva backend/frontend). **Adicionado por @ux-design-expert.** | HIGH | ALTO | 4h |
| UX-007 | **Sem confirmacao de saida com alteracoes pendentes** -- Sem `beforeunload` handler ou rota guard. Editor complexo sem "unsaved changes" dialog. **Adicionado por @ux-design-expert.** | HIGH | ALTO | 2h |
| UX-008 | **Console.log em producao** -- Poluicao de console expoe internals. Cross-ref SYS-009. **Adicionado por @ux-design-expert.** | LOW | BAIXO | 2h |
| UX-009 | **Sem indicador de loading em export** -- Click no TopToolbar sem feedback de progresso ate download completo. **Adicionado por @ux-design-expert.** | MEDIUM | MEDIO | 2h |
| UX-010 | **Mensagens de erro genericas em upload** -- Erros de validacao de arquivo sem tipo esperado, tamanho maximo ou acao sugerida. **Adicionado por @ux-design-expert.** | LOW | BAIXO | 2h |

---

### 1.6 Acessibilidade (validado por @ux-design-expert) -- 4 debitos

| ID | Debito | Severidade | Impacto | Esforco |
|----|--------|-----------|---------|---------|
| A11Y-001 | **Sem focus trap em modais** -- 4 modais permitem Tab escapar. Violacao WCAG 2.1 SC 2.4.3. Fix: `useFocusTrap` do `@vueuse/core` (ja instalado). | HIGH | ALTO | 4h |
| A11Y-002 | **Sem focus indicators customizados** -- Defaults do browser inconsistentes em fundos escuros. Recomendacao: `outline: 2px solid var(--color-primary-600)` + offset. | MEDIUM | MEDIO | 3h |
| A11Y-003 | **Contraste Neutral-500 (#737373)** -- 4.48:1 vs 4.5:1 exigido (WCAG AA). Substituir por Neutral-600 (#525252, 7.1:1). | MEDIUM | MEDIO | 1h |
| A11Y-004 | Alt texts ausentes em PDF viewer e canvas iframe placeholders | LOW | BAIXO | 2h |

---

### 1.7 Seguranca (consolidado) -- 4 debitos

| ID | Debito | Severidade | OWASP | Esforco |
|----|--------|-----------|-------|---------|
| SEC-001 | **v-html XSS em BibliotecaComponentList** -- `v-html="item.previewHtml"` sem sanitizacao. Fix: DOMPurify com allowlist (conforme @ux-design-expert). | HIGH | A03:2021 Injection | 2h |
| SEC-002 | dompurify vulneravel (transitiva via monaco-editor, <=3.3.1) | MEDIUM | A06:2021 Vulnerable Components | 1h |
| SEC-003 | **Vite vulneravel** -- path traversal em dev server. `npm audit fix` resolve. | HIGH | A06:2021 Vulnerable Components | 0.5h |
| SEC-004 | **Sem audit logging de operacoes privilegiadas** -- Nenhum logging de eventos de seguranca (login, access denied, service role ops). Gap OWASP A09. **Adicionado por recomendacao de @qa.** | HIGH | A09:2021 Logging/Monitoring | 4h |

---

### 1.8 Performance -- 3 debitos

| ID | Debito | Severidade | Impacto | Esforco |
|----|--------|-----------|---------|---------|
| PERF-001 | **Sem virtualizacao de tree** -- StructureTree renderiza todos os nodes. Docs tipicos: 20-80 nodes, max ~200. Deprioritizar; monitorar com `performance.mark` antes de implementar. | MEDIUM | Performance | 8h |
| PERF-002 | **JSON.stringify undo snapshots** -- Arvore completa serializada a cada mutacao. Frame drops perceptiveis em docs 50+ elementos. **Primario; SYS-022 removido como duplicata.** Solucao: command pattern com deltas ou Immer. | MEDIUM | Performance, UX | 6h |
| PERF-003 | Monaco editor bundle size (~3MB compressed) | LOW | Initial load | 2h |

---

### 1.9 Testes -- 4 debitos

| ID | Debito | Severidade | Impacto | Esforco |
|----|--------|-----------|---------|---------|
| TEST-001 | **Sem framework E2E** -- Flow critico sem cobertura browser-level. **Primario; SYS-020 removido como duplicata.** | HIGH | Quality assurance | 16h |
| TEST-002 | Atoms 88% sem testes (2 de 16 com specs) | MEDIUM | Risco de regressao | 6h |
| TEST-003 | Molecules ~55% sem testes (30 de 55 sem specs) | MEDIUM | Risco de regressao | 12h |
| TEST-004 | LoginPage sem testes (OAuth redirect simples) | LOW | Risco de regressao | 2h |

---

## 2. Cross-Cutting Debts

Debitos que atravessam multiplas areas e requerem coordenacao entre especialistas.

### CC-001: Split-Brain State Management

**Debitos envolvidos:** SYS-004, DB-008, DB-016, DB-017, REDIS-002
**Areas:** Sistema + Database + Redis
**Severidade composta:** CRITICAL

O estado de jobs vive em 3 locais (in-memory, Redis, Supabase) sem garantia transacional. Agravado por: `recover_running_jobs()` nunca eh chamado (DB-016), `save_result()` pode sobrescrever cancelamentos (DB-017), e Redis nao tem reconnection (REDIS-002).

**Decisao arquitetural (validada por @data-engineer):** Redis como source of truth primario com write-behind para Supabase. In-memory reduzido a cache de leitura. Mitigacao imediata: chamar `recover_running_jobs()` no lifespan (0.5h) + guard em `save_result()` (1h).

### CC-002: Seguranca de Dados End-to-End

**Debitos envolvidos:** DB-001, DB-002, DB-003, DB-012, SYS-015, SEC-004
**Areas:** Database + Sistema + Seguranca
**Severidade composta:** CRITICAL

Cadeia: RLS blanket (DB-001) + sem user_id (DB-002) + service key para tudo (DB-003) + AUTH_DISABLED sem safeguard (DB-012) + sem security headers (SYS-015) + sem audit logging (SEC-004).

**Ordem de resolucao (validada por @data-engineer):** DB-012 (0.5h) -> DB-002 (12h) -> DB-001 + DB-003 em paralelo (8h) -> SEC-004 (4h) -> SYS-015 (4h).

### CC-003: Quality Enforcement Pipeline

**Debitos envolvidos:** SYS-002, SYS-003, SYS-013, SYS-010
**Areas:** Sistema (backend + frontend)
**Severidade composta:** HIGH

Sem linting (Python e JS), sem pre-commit hooks, 80 `any` em TypeScript. Uma unica iniciativa: ruff + mypy, eslint + prettier, husky + lint-staged.

### CC-004: Oversized Components / God Objects

**Debitos envolvidos:** SYS-011, FE-001, FE-002, FE-003
**Areas:** Sistema (backend stages) + Frontend (Vue + stores)
**Severidade composta:** HIGH

Padrao recorrente: stage3 (2,048 LOC), AnalyzingPage (1,195 LOC), HTMLCanvas (913 LOC), session.ts (534 LOC). Decomposicao guiada por responsabilidade unica.

### CC-005: Undo/Redo Performance

**Debitos envolvidos:** PERF-002
**Areas:** Frontend
**Severidade composta:** MEDIUM

JSON.stringify da arvore completa a cada mutacao. Frame drops em docs 50+ elementos, limite artificial de 20 snapshots. Fix: command pattern com deltas ou structural sharing via Immer.

### CC-006: E2E / Integration Test Gap

**Debitos envolvidos:** TEST-001
**Areas:** Sistema + Frontend
**Severidade composta:** HIGH

Ausencia total de testes E2E. Flow Upload -> Analyze -> Edit -> Export sem cobertura browser-level. Fix: Playwright com smoke tests.

### CC-007: Silent Failure Pattern (identificado por @qa)

**Debitos envolvidos:** DB-015, DB-016, DB-017, SYS-009, SYS-017
**Areas:** Database + Sistema
**Severidade composta:** HIGH

Multiplos pontos do sistema falham silenciosamente: storage cleanup nao deleta subdiretorios sem lancar erro (DB-015), recovery de jobs existe mas nao eh chamada (DB-016), resultados sobrescrevem cancelamentos sem warning (DB-017), logs via console.log sem logger estruturado (SYS-009), health check nao verifica dependencias (SYS-017).

### CC-008: Frontend Safety Net Gap (identificado por @qa)

**Debitos envolvidos:** TEST-001, UX-006, UX-007, SYS-012
**Areas:** Frontend + UX + Testes
**Severidade composta:** HIGH

O frontend nao tem nenhuma camada de protecao: sem error boundary (UX-006/SYS-012), sem confirmacao de saida (UX-007), sem testes E2E (TEST-001). Qualquer refatoracao de componentes core tem risco amplificado. **Recomendacao de @qa:** implementar UX-006 + UX-007 ANTES das refatoracoes de FE-001, FE-002, FE-003.

---

## 3. Security Consolidated View

### Debitos de Seguranca Consolidados (todas as areas)

| Prioridade | ID | Debito | Severidade | OWASP Top 10 |
|-----------|-----|--------|-----------|-------------|
| 1 | DB-001 | RLS `USING (true)` -- acesso blanket | CRITICAL | A01 Broken Access Control |
| 2 | DB-002 | Sem multi-tenancy / user_id | CRITICAL | A01 Broken Access Control |
| 3 | SYS-001 | Vendored dependencies -- patches nao aplicados | CRITICAL | A06 Vulnerable Components |
| 4 | DB-003 | Service role key -- uso indiscriminado | HIGH | A01 Broken Access Control |
| 5 | SEC-001 | v-html XSS em BibliotecaComponentList | HIGH | A03 Injection |
| 6 | SYS-015 | Sem security headers (CORS *, sem CSP, sem HSTS) | HIGH | A05 Security Misconfiguration |
| 7 | SEC-003 | Vite vulneravel (path traversal, dev-only) | HIGH | A06 Vulnerable Components |
| 8 | SEC-004 | Sem audit logging de operacoes privilegiadas | HIGH | A09 Logging/Monitoring |
| 9 | DB-012 | Sem safeguard AUTH_DISABLED em producao | MEDIUM | A07 Auth Failures |
| 10 | SEC-002 | dompurify vulneravel (transitiva) | MEDIUM | A06 Vulnerable Components |
| 11 | SYS-016 | Supabase ref hardcoded no CI | MEDIUM | A05 Security Misconfiguration |

### OWASP Top 10 Coverage

| OWASP Category | Status | Debitos |
|---------------|--------|---------|
| A01 Broken Access Control | COBERTO | DB-001, DB-002, DB-003 |
| A02 Cryptographic Failures | PARCIAL | JWT via Supabase (adequado); sem analise de dados em transito/repouso |
| A03 Injection | COBERTO | SEC-001 (XSS). SQL injection mitigado pelo SDK Supabase |
| A04 Insecure Design | N/A | Aplicacao interna, threat model simplificado |
| A05 Security Misconfiguration | COBERTO | SYS-015, SYS-016 |
| A06 Vulnerable Components | COBERTO | SYS-001, SEC-002, SEC-003 |
| A07 Auth Failures | COBERTO | DB-012 |
| A08 Software/Data Integrity | PARCIAL | Sem verificacao de integridade de templates gerados |
| A09 Logging/Monitoring | COBERTO (novo) | SEC-004 |
| A10 SSRF | N/A | Backend nao faz requests baseados em input do usuario |

**Nota sobre rate limiting:** `main.py` importa `slowapi` (presente em requirements.txt). Provavelmente ja implementado -- verificar cobertura de endpoints.

---

## 4. Gaps Adicionais (identificados por @qa)

### GAP-1: CI/CD Pipeline Debts

O CI (`ci.yml`) nao foi analisado sistematicamente. Itens potenciais:
- Sem lint/typecheck enforcement no CI (relacionado a SYS-002/SYS-003)
- Sem deployment rollback strategy documentada
- Sem smoke test pos-deploy
- SYS-016 (Supabase ref hardcoded) eh o unico debito CI catalogado

**Acao:** Apos resolver SYS-002 e SYS-003, adicionar lint + typecheck + test como CI gates. Considerar smoke test pos-deploy como extensao de TEST-001.

### GAP-2: Logging/Observabilidade Estruturada

SYS-009 e SYS-017 tocam no tema, mas faltam:
- Structured logging no backend (sem correlation IDs entre requests)
- Metricas de pipeline (tempo por stage, taxa de sucesso/falha)
- Alerting para falhas silenciosas (CC-007)

**Acao:** Incorporar na Wave 3 como iniciativa de observabilidade (~8h). Priorizar correlation IDs e metricas basicas de pipeline.

### GAP-3: Dependency Supply Chain

SYS-001, SEC-002, SEC-003 cobrem vulnerabilidades especificas, mas faltam:
- Analise sistematica de `npm audit` / `pip audit`
- Politica de atualizacao (Renovate/Dependabot ausente)
- Verificacao de licencas

**Acao:** Quick win -- habilitar Dependabot no GitHub (~30min). Incluir `npm audit` e `pip audit` no CI.

### GAP-4: Documentacao Tecnica

Nao ha debitos catalogados para:
- ADRs (Architecture Decision Records)
- Documentacao de API (OpenAPI/Swagger)
- Onboarding guide para novos desenvolvedores

**Acao:** Nao bloqueante. Adicionar OpenAPI export como extensao de SYS-019. ADRs e onboarding como backlog separado.

### GAP-5: Error Recovery / Resilience Patterns

REDIS-002, DB-016, SYS-004 cobrem cenarios especificos, mas faltam:
- Retry policies para OpenRouter (GPT-4o Vision) -- pipeline stage 3
- Circuit breaker para Supabase
- Graceful degradation quando recursos opcionais falham

**Acao:** Verificar se `openrouter_client.py` ja tem retry. Se sim, GAP parcialmente mitigado. Incluir resilience review na Wave 3.

---

## 5. Matriz de Priorizacao Final

Consolidada a partir das recomendacoes de @data-engineer, @ux-design-expert e @qa.

### Tier 1: CRITICAL + HIGH Security (28.5h)

| # | ID | Debito | Sev | Horas | Bloqueado por |
|---|-----|--------|-----|-------|---------------|
| 1 | DB-012 | Safeguard AUTH_DISABLED producao | M | 0.5h | -- |
| 2 | DB-016 | Chamar recover_running_jobs() no lifespan | H | 0.5h | -- |
| 3 | SEC-003 | Vite patch | H | 0.5h | -- |
| 4 | DB-004 | Trigger updated_at em jobs | H | 1h | -- |
| 5 | DB-005 | CHECK constraint jobs.status | H | 1h | -- |
| 6 | DB-009 | Bucket creation nas migrations | M | 1h | -- |
| 7 | SEC-001 | v-html XSS (DOMPurify) | H | 2h | -- |
| 8 | DB-002 | Adicionar user_id a todas as tabelas | C | 12h | -- |
| 9 | DB-001 | Reescrever RLS policies com owner filter | C | 4h | DB-002 |
| 10 | DB-003 | Separar service role de queries (2 clientes) | H | 4h | DB-002 |
| 11 | SYS-015 | Security headers (CSP, HSTS, X-Frame) | H | 4h | -- |

### Tier 2: Quality Infrastructure (24h)

| # | ID | Debito | Sev | Horas | Bloqueado por |
|---|-----|--------|-----|-------|---------------|
| 12 | SYS-001 | Remover vendored deps, usar requirements.txt | C | 4h | -- |
| 13 | SYS-002 | Configurar ruff + mypy (Python) | C | 4h | -- |
| 14 | SYS-003 | Configurar eslint + prettier (Frontend) | C | 4h | -- |
| 15 | SYS-013 | Pre-commit hooks (husky + lint-staged) | M | 2h | SYS-002, SYS-003 |
| 16 | SYS-010 | Reduzir 80 `any` em TypeScript | M | 6h | SYS-003 |
| 17 | SEC-004 | Audit logging de operacoes privilegiadas | H | 4h | -- |

### Tier 3: Frontend Safety Net (14h)

| # | ID | Debito | Sev | Horas | Bloqueado por |
|---|-----|--------|-----|-------|---------------|
| 18 | UX-006 | Error boundary global | H | 4h | -- |
| 19 | SYS-012 | app.config.errorHandler (implementar junto UX-006) | H | 0h | UX-006 |
| 20 | UX-007 | Unsaved changes guard (beforeunload + router) | H | 2h | -- |
| 21 | A11Y-001 | Focus trap em modais (useFocusTrap) | H | 4h | -- |
| 22 | UX-001 | Toast store global (Pinia) | M | 3h | -- |
| 23 | A11Y-003 | Neutral-500 -> Neutral-600 contraste | M | 1h | -- |

### Tier 4: Core Refactoring (46h)

| # | ID | Debito | Sev | Horas | Bloqueado por |
|---|-----|--------|-----|-------|---------------|
| 24 | FE-003 | session.ts refactor | H | 4h | Tier 3 (safety net) |
| 25 | FE-001 | AnalyzingPage decomposicao | H | 8h | FE-003 |
| 26 | FE-002 | HTMLCanvas decomposicao | H | 6h | Tier 3 |
| 27 | SYS-014 | Pipeline context typed (Pydantic models) | C | 12h | SYS-002 |
| 28 | DB-008 | State store unification (Redis SSOT) | H | 8h | CC-001 decision |
| 29 | DB-007 | asyncio.to_thread para Supabase SDK | H | 6h | -- |
| 30 | REDIS-004 | Migrar para redis.asyncio | M | 3h | -- |

### Tier 5: UX Polish + Testes (47h)

| # | ID | Debito | Sev | Horas | Bloqueado por |
|---|-----|--------|-----|-------|---------------|
| 31 | UX-005 | Emoji -> lucide icons | M | 2h | -- |
| 32 | UX-009 | Loading indicator export | M | 2h | -- |
| 33 | FE-008 | Unificar design tokens | M | 2h | -- |
| 34 | A11Y-002 | Focus indicators customizados | M | 3h | -- |
| 35 | PERF-002 | Undo/redo command pattern | M | 6h | -- |
| 36 | TEST-001 | E2E framework (Playwright) + smoke tests | H | 16h | -- |
| 37 | TEST-002 | Testes atoms prioritarios (Button, ProgressBar, ColorPicker, ConfidenceBadge) | M | 6h | -- |
| 38 | TEST-003 | Testes molecules prioritarios (InspectorField, BindingEditor, ContextMenu) | M | 12h | -- |

### Deferidos (nao agendar)

| ID | Debito | Horas | Razao |
|----|--------|-------|-------|
| UX-002 | Responsive/mobile | 16h+ | Desktop-only product decision |
| UX-003 | Dark mode | 16h+ | Removido por @ux-design-expert -- confunde percepcao de cores |
| UX-004 | Skeleton screens editor | 4h | Editor carrega apos pipeline completo |
| PERF-001 | Tree virtualization | 8h | Monitorar primeiro; docs tipicos 20-80 nodes |
| PERF-003 | Monaco bundle optimization | 2h | Ja chunked separadamente |
| FE-004 | Padronizar store API | 4h | Migrar por oportunidade |
| FE-007 | Barrel export composables | 0.5h | DX trivial |
| FE-009 | CSS approach consistencia | 2h | Cosmetics |
| FE-005 | Consolidar ConfidenceBadge | 1h | Fazer por oportunidade |
| SYS-007 | Dead code/scaffolding | 1h | Quick win por oportunidade |
| SYS-009 | console.log em producao | 2h | Cross-ref UX-008 |
| SYS-005 | TMP_BASE duplicado | 2h | Manutencao menor |
| SYS-008 | Organizacao componentes | 4h | DX |
| SYS-011 | Stage files monoliticos | 16h | Alto esforco, baixo risco imediato |
| SYS-017 | Health check profundo | 4h | Melhoria operacional |
| SYS-018 | spaCy model mismatch | 1h | Funcional com fallback |
| SYS-019 | API versioning | 4h | Evolucao futura |
| SYS-021 | faker como prod dep | 0.5h | Trivial |
| DB-006 | Rollback migrations | 6h | Schema simples, rollback manual viavel |
| DB-010 | Indice created_at | 0.5h | Volume insuficiente |
| DB-011+DB-015 | Soft-delete + fix recursive listing | 6h | Fazer juntos quando priorizado |
| DB-013 | FK templates->jobs | 1h | Nice-to-have |
| DB-014 | UPDATE policy storage | 0.5h | Impacto zero |
| DB-017 | Guard save_result() | 1h | Fazer com DB-008 |
| REDIS-001 | Prefixo app nas keys | 0.5h | Trivial |
| REDIS-002 | Retry + reconnection | 4h | Fazer com DB-008 |
| REDIS-003 | scan_iter em all_jobs() | 1h | TTL limita keyspace |
| SEC-002 | dompurify upgrade | 1h | Seguranca transitiva |
| UX-008 | Console.log producao | 2h | Polimento |
| UX-010 | Erros contextuais upload | 2h | Nice-to-have |
| A11Y-004 | Alt texts | 2h | Baixo impacto |
| TEST-004 | LoginPage tests | 2h | OAuth redirect simples |

---

## 6. Plano de Resolucao

### Wave 1: Quick Wins + Security Foundation (0-2 sprints, ~28.5h)

**Objetivo:** Eliminar riscos de seguranca criticos e quick wins de zero risco.

| Sprint | IDs | Foco | Horas |
|--------|-----|------|-------|
| 1A | DB-012, DB-016, SEC-003, DB-004, DB-005, DB-009 | Quick wins DB + patch Vite | 4.5h |
| 1B | DB-002, DB-001, DB-003, SEC-001, SYS-015 | Security chain (DB-002 primeiro) | 24h |

**Criterio de conclusao:** Zero debitos CRITICAL de seguranca. RLS com owner-based access. Service role scoped.

### Wave 2: Quality Infrastructure (1 sprint, ~24h)

**Objetivo:** Estabelecer quality gates automatizados.

| IDs | Foco | Horas |
|-----|------|-------|
| SYS-001, SYS-002, SYS-003, SYS-013, SYS-010, SEC-004 | Vendored deps, linters, pre-commit, audit logging | 24h |

**Criterio de conclusao:** CI passa lint + typecheck. Pre-commit hooks ativos. `any` count < 20.

### Wave 3: Frontend Safety Net + Core Refactoring (2-3 sprints, ~60h)

**Objetivo:** Estabelecer safety nets antes de refatorar componentes core.

| Sprint | IDs | Foco | Horas |
|--------|-----|------|-------|
| 3A | UX-006, UX-007, A11Y-001, UX-001, A11Y-003 | Error boundary, unsaved guard, focus trap, toasts | 14h |
| 3B | FE-003, FE-001, FE-002 | Decomposicao de God Objects frontend | 18h |
| 3C | SYS-014, DB-008, DB-007, REDIS-004 | Pipeline typed, state unification, async | 29h |

**Criterio de conclusao:** Maior arquivo frontend < 500 LOC. Pipeline context typed. Redis como SSOT.

### Wave 4: Performance, Testes e Polish (2 sprints, ~47h)

**Objetivo:** E2E coverage, performance do undo/redo, polish visual.

| Sprint | IDs | Foco | Horas |
|--------|-----|------|-------|
| 4A | TEST-001, UX-005, UX-009, FE-008, A11Y-002 | E2E framework, icons, tokens, a11y | 29h |
| 4B | PERF-002, TEST-002, TEST-003 | Undo performance, testes de componentes | 24h |

**Criterio de conclusao:** 4+ E2E smoke tests passando. Undo sem frame drops. Atoms coverage > 50%.

---

## 7. Dependencias entre Debitos

### Grafo de Dependencias (atualizado com adicoes dos especialistas)

```
                    DB-002 (user_id) [CRITICAL]
                   /       \
                  v         v
             DB-001       DB-003
            (RLS fix)   (scoped creds)
             [CRITICAL]   [HIGH]

        SYS-002 (ruff)     SYS-003 (eslint)
         [CRITICAL]         [CRITICAL]
           |                    |
           v                    v
        SYS-014            SYS-010
      (typed context)     (fix any)
           \                /
            v              v
            SYS-013 (pre-commit hooks)

        UX-006 + UX-007 (safety nets) [HIGH]
              |
              v  (SHOULD PRECEDE)
        FE-003 (session.ts refactor) [HIGH]
              |
              v
          FE-001 (AnalyzingPage) [HIGH]

        Decisao CC-001 (single source of truth)
              |
              v
          DB-008 + REDIS-002

        DB-011 --RELATED--> DB-015 (fix conjunto)
        DB-008 --AGGRAVATED BY--> DB-016, DB-017
        DB-007 --PARALLEL WITH--> REDIS-004 (mesmo pattern)
        UX-006 --CROSS-REF--> SYS-012 (mesmo debito, perspectivas diferentes)
        UX-008 --CROSS-REF--> SYS-009 (mesmo tema)
```

### Duplicatas Consolidadas (removidas do inventario)

| Removido | Mantido | Justificativa |
|----------|---------|---------------|
| SYS-022 | PERF-002 | Mesma issue (JSON.stringify undo). PERF-002 mais especifico |
| SYS-020 | TEST-001 | Mesma issue (sem E2E). TEST-001 mais especifico |
| SYS-006 | FE-003 | Mesma issue (session.ts God Object). FE-003 mais especifico |
| FE-006 | SYS-007 | HelloWorld.vue incluso em SYS-007 (dead code geral) |

### Cross-References (debitos relacionados, nao duplicatas)

| Debito A | Debito B | Relacao |
|----------|----------|---------|
| SYS-012 | UX-006 | Mesmo problema (error boundary), perspectiva backend vs UX |
| SYS-009 | UX-008 | Mesmo tema (console.log em producao) |
| DB-011 | DB-015 | DB-015 agrava DB-011 (cleanup incompleto + nao atomico) |
| DB-007 | REDIS-004 | Mesmo pattern (sync client em async context) |

---

## 8. Riscos e Mitigacoes

### Riscos de Regressao Durante Resolucao

| Fix | Risco | Probabilidade | Mitigacao |
|-----|-------|--------------|-----------|
| DB-002 (add user_id) | Backend INSERTs falham sem user_id | ALTA | Nullable primeiro, enforcement gradual (@data-engineer) |
| DB-001 (RLS rewrite) | Queries legitimas bloqueadas | MEDIA | Testar com roles `anon` e `authenticated` separadamente |
| FE-003 (session.ts) | Editor abre com dados incompletos | ALTA | Testes de integracao ANTES de refatorar. Maior risco do catalogo |
| FE-001 (AnalyzingPage) | State transitions quebram em edge cases | MEDIA | Testes unitarios para state machine ANTES de decompor |
| FE-002 (HTMLCanvas) | Drag/zoom/scroll quebram | MEDIA | Testes manuais + snapshot tests |
| DB-008 (state unification) | Jobs perdem status durante transicao | ALTA | Feature flag + dual-write temporario |
| SYS-014 (typed context) | Tipagem incorreta causa erros downstream | MEDIA | Rodar pipeline com PDFs de referencia antes/depois |
| SEC-001 (DOMPurify) | Sanitizacao remove HTML legitimo | MEDIA | Allowlist explicita (ALLOWED_TAGS conforme @ux-design-expert) |

### Riscos Cruzados (identificados por @qa)

| Risco | Severidade | Mitigacao |
|-------|-----------|-----------|
| Fix de DB-002 quebra backend code | HIGH | Nullable com enforcement gradual |
| Fix de DB-001 pode bloquear pipeline se service role nao separado | HIGH | Ordem: DB-002 -> DB-001 + DB-003 em paralelo |
| Refactor de session.ts sem E2E safety net | MEDIUM | Criar testes de integracao leves (Vitest + happy-dom) |
| Unificacao de state stores pode perder dados | HIGH | Feature flag + dual-write |
| Linters geram centenas de warnings | LOW | `--fix` no bootstrap + regras incrementais |

---

## 9. Criterios de Sucesso

| Metrica | Baseline Atual | Target Pos-Resolucao | Como Medir |
|---------|---------------|---------------------|-----------|
| Debitos CRITICAL | 6 | 0 | Catalogo atualizado |
| Debitos HIGH | 19 | <= 5 (apos Waves 1-3) | Catalogo atualizado |
| RLS coverage | 0% (USING true) | 100% owner-based | SQL audit |
| Backend async compliance | 0% (sync SDK) | 100% (asyncio.to_thread) | Code grep sync calls em async |
| Frontend test coverage (atoms) | 12% (2/16) | 50%+ (8/16) | Vitest coverage |
| E2E smoke tests | 0 | >= 4 flows | Playwright count |
| `any` count em TypeScript | 80 | < 20 | grep count |
| Maior arquivo LOC (frontend) | 1,195 (AnalyzingPage) | < 500 | wc -l |
| Maior arquivo LOC (backend) | 2,048 (stage3) | < 1,000 (stretch) | wc -l |
| WCAG AA violations | 2 (focus trap + contraste) | 0 | Axe/Lighthouse |
| Known vulnerabilities (npm) | >= 2 (Vite + dompurify) | 0 | npm audit |
| Security headers | 0/5 (CSP, HSTS, X-Frame, X-Content-Type, CORS scoped) | 5/5 | Response header check |
| Audit logging | Ausente | Operacoes privilegiadas logadas | Log review |

---

## 10. Testes Requeridos Pos-Resolucao

### Apos Wave 1 (Security + Quick Wins)

- [ ] `jobs` table rejects invalid status values (DB-005)
- [ ] `jobs.updated_at` auto-updates on modification (DB-004)
- [ ] `recover_running_jobs()` called during server startup (DB-016)
- [ ] `AUTH_DISABLED=true` raises error when `ENVIRONMENT=production` (DB-012)
- [ ] Storage buckets exist after running all migrations (DB-009)
- [ ] User A cannot read/modify/delete User B's jobs (DB-001 + DB-002)
- [ ] Anon key queries respect RLS policies (DB-003)
- [ ] Service role used ONLY for storage operations (DB-003)
- [ ] `v-html` content sanitized through DOMPurify (SEC-001)
- [ ] Security headers present in all responses (SYS-015)

### Apos Wave 2 (Quality Infrastructure)

- [ ] CI pipeline includes lint + typecheck gates
- [ ] Pre-commit hooks block commits with lint errors
- [ ] `any` count < 20 in TypeScript
- [ ] Security audit events logged for privileged operations (SEC-004)

### Apos Wave 3 (Safety Net + Refactoring)

- [ ] Error boundary catches and displays unhandled errors (UX-006)
- [ ] Unsaved changes dialog appears on navigate away (UX-007)
- [ ] Focus trap prevents Tab from escaping modal (A11Y-001)
- [ ] Toast triggered from any Pinia store (UX-001)
- [ ] AnalyzingPage transitions through all 5 states correctly (FE-001)
- [ ] HTMLCanvas zoom, scroll, drag-drop work after decomposition (FE-002)
- [ ] `loadFromPipelineResult` loads all data correctly (FE-003)
- [ ] Server crash mid-pipeline does not lose job result (CC-001/DB-008)
- [ ] Redis disconnect does not crash server (REDIS-002)
- [ ] Concurrent pipeline runs do not block each other (DB-007)
- [ ] `save_result()` does not overwrite cancelled job status (DB-017)

### Apos Wave 4 (Testes + Polish)

- [ ] E2E Smoke: Upload PDF -> Pipeline completes -> Editor loads -> Export ZIP
- [ ] E2E Smoke: Login flow (OAuth redirect + callback)
- [ ] E2E Smoke: Field mapping panel interaction
- [ ] E2E Smoke: Inspector panel edits reflect in canvas
- [ ] Undo/redo works for all mutation types without frame drops (PERF-002)

---

## 11. Decisoes Arquiteturais Incorporadas

Decisoes tomadas durante o processo de revisao, validadas pelos especialistas:

| Decisao | Especialista | Referencia |
|---------|-------------|-----------|
| Redis como SSOT para job state, Supabase como persistencia final (write-behind) | @data-engineer | CC-001, DB-008 |
| `user_id` nullable com enforcement gradual (zero downtime) | @data-engineer | DB-002 |
| Dois clientes Supabase: admin (storage) + user (queries com JWT) | @data-engineer | DB-003 |
| `asyncio.to_thread()` em vez de httpx direto contra PostgREST | @data-engineer | DB-007 |
| Soft-delete para jobs (em vez de Edge Functions) | @data-engineer | DB-011 |
| Retry simples com health check para Redis (nao circuit breaker completo) | @data-engineer | REDIS-002 |
| Composable `useAnalyzingStateMachine()` + sub-componentes por estado | @ux-design-expert | FE-001 |
| Composables para canvas: useCanvasZoom, useCanvasDrag, useCanvasIframe | @ux-design-expert | FE-002 |
| DOMPurify (nao iframe sandboxed) para v-html sanitization | @ux-design-expert | SEC-001 |
| useFocusTrap do @vueuse/core (nao vue-focus-lock) | @ux-design-expert | A11Y-001 |
| Neutral-600 (#525252) para substituir Neutral-500 | @ux-design-expert | A11Y-003 |
| Dark mode removido do catalogo (nao eh debito para editor PDF) | @ux-design-expert | UX-003 |
| Safety nets (UX-006, UX-007) ANTES de refatoracoes de componentes | @qa | CC-008 |

---

## Controle de Versoes

| Versao | Data | Autor | Mudanca |
|--------|------|-------|---------|
| DRAFT v1.0 | 2026-04-09 | @architect (Aria) | Consolidacao inicial -- Phase 4 |
| Review DB v1.0 | 2026-04-09 | @data-engineer (Dara) | Validacao + 4 debitos adicionados -- Phase 5 |
| Review UX v1.0 | 2026-04-09 | @ux-design-expert (Uma) | Validacao + 5 debitos adicionados -- Phase 6 |
| QA Gate v1.0 | 2026-04-09 | @qa (Quinn) | APPROVED 8.5/10 + 2 CCs + 1 debito -- Phase 7 |
| **FINAL v1.0** | **2026-04-09** | **@architect (Aria)** | **Consolidacao final -- Phase 8** |
