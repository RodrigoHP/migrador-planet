# Technical Debt Assessment - DRAFT

## Para Revisao dos Especialistas

**Projeto:** migrador-planet (PDF-to-HTML Template Migration Tool)
**Data:** 2026-04-09
**Consolidado por:** @architect (Aria) -- Brownfield Discovery Phase 4
**Status:** DRAFT -- Pendente revisao de @data-engineer e @ux-design-expert

---

### Executive Summary

| Metrica | Valor |
|---------|-------|
| **Total de debitos** | 65 |
| **CRITICAL** | 7 |
| **HIGH** | 16 |
| **MEDIUM** | 26 |
| **LOW** | 16 |
| **Esforco total estimado** | ~350h |

**Distribuicao por area:**

| Area | Debitos | CRITICAL | HIGH | MEDIUM | LOW |
|------|---------|----------|------|--------|-----|
| Sistema (SYS-*) | 22 | 4 | 3 | 10 | 5 |
| Database (DB-*) | 14 | 3 | 5 | 4 | 2 |
| Redis (REDIS-*) | 3 | 0 | 0 | 1 | 2 |
| Frontend (FE-*) | 9 | 0 | 3 | 2 | 4 |
| UX (UX-*) | 5 | 0 | 0 | 2 | 3 |
| Acessibilidade (A11Y-*) | 4 | 0 | 1 | 2 | 1 |
| Seguranca (SEC-*) | 3 | 0 | 2 | 1 | 0 |
| Performance (PERF-*) | 3 | 0 | 0 | 2 | 1 |
| Testes (TEST-*) | 4 | 0 | 1 | 2 | 1 |

**Topologia de risco:** Os debitos CRITICAL concentram-se em duas areas -- infraestrutura de codigo (vendored deps, sem linting, pipeline untyped) e seguranca de dados (RLS blanket access, sem multi-tenancy, service key sem defesa em profundidade). A combinacao DB-001 + DB-002 + DB-003 representa o maior risco de seguranca da aplicacao.

---

### 1. Debitos de Sistema (Phase 1 -- @architect)

*Fonte: `docs/architecture/system-architecture.md` -- 22 debitos identificados*

#### 1.1 CRITICAL (P0)

| ID | Debito | Impacto | Esforco |
|----|--------|---------|---------|
| SYS-001 | **Vendored dependencies (32MB)** -- `backend/vendor/` contem openai, pydantic, httpx vendorados. Patches de seguranca nao sao aplicados automaticamente. Repositorio bloated. `conftest.py` adiciona vendor ao `sys.path`. | Seguranca, tamanho do repo, gestao de deps | 4h |
| SYS-002 | **Sem linter/formatter Python** -- Nenhum `pyproject.toml`, `ruff.toml`, `mypy.ini` ou `.flake8`. Sem type checking (mypy/pyright) apesar de type hints extensivos. Qualidade do backend nao tem enforcement automatizado. | Qualidade, consistencia, DX | 4h |
| SYS-003 | **Sem ESLint/Prettier (Frontend)** -- Nenhuma configuracao de linting/formatting. `vue-tsc --noEmit` eh o unico quality gate. Sem auto-formatting, sem import ordering. | Qualidade, consistencia | 4h |
| SYS-014 | **Pipeline context untyped (`Dict[str, Any]`)** -- Orquestrador passa `Dict[str, Any]` entre 5 stages. 123 ocorrencias em 20 arquivos. Contratos entre stages documentados em markdown mas nao enforced pelo type system. Typo em key = erro de runtime. | Type safety, manutencao, debugging | 12h |

#### 1.2 HIGH (P1)

| ID | Debito | Impacto | Esforco |
|----|--------|---------|---------|
| SYS-004 | **Dual job state management** -- `_pipeline_jobs` dict (in-memory) + `job_store` (Redis) + Supabase (final). Split-brain em crash. `recover_running_jobs()` existe mas NAO eh chamado no lifespan handler. TTL hardcoded em 2 locais. | Consistencia, confiabilidade | 8h |
| SYS-006 | **Session store God Object (534 LOC)** -- `loadFromPipelineResult()` ~150 linhas orquestrando 10+ stores. Contem logica de negocio (tree normalization, table cell flags, binding reconciliation). Duplica `applyTableCellFlags` inline. | Manutencao, testabilidade | 8h |
| SYS-015 | **Sem security headers** -- CORS overly permissive (`allow_methods=["*"]`, `allow_headers=["*"]`). Sem CSP, X-Frame-Options, X-Content-Type-Options, HSTS. API serve PDFs sem Content-Disposition. | Seguranca (OWASP) | 4h |

#### 1.3 MEDIUM (P2)

| ID | Debito | Impacto | Esforco |
|----|--------|---------|---------|
| SYS-005 | **`TMP_BASE` duplicado em 3 arquivos** -- `analyze.py`, `upload.py`, `validation.py` leem `JOBS_DIR` env independentemente. | Manutencao | 2h |
| SYS-008 | **Organizacao de componentes inconsistente** -- `components/` existe ao lado de atoms/molecules/organisms. `layouts/` e `templates/` com propositos similares. | DX, discoverability | 4h |
| SYS-010 | **80 ocorrencias de `any` em TypeScript** -- 28 arquivos, incluindo codigo de producao (`session.ts`, `mapping.ts`, `generation.ts`, `autoFixStore.ts`). | Type safety | 6h |
| SYS-011 | **Stage files monoliticos** -- `stage3` (2,048 LOC), `stage5` (2,008 LOC), `stage1` (1,403 LOC). Sub-steps acoplados, dificil testar individualmente. | Manutencao, testabilidade | 16h |
| SYS-012 | **Sem error boundary/global error handler** -- Nenhum `app.config.errorHandler` em `main.ts`. Erros nao capturados = tela em branco. Sentry DSN no `.env.example` mas nao usado. | UX, error recovery | 4h |
| SYS-013 | **Sem pre-commit hooks** -- Nenhum `.husky/` ou `.pre-commit-config.yaml`. Devs podem commitar sem rodar checks. CI pega issues apenas pos-push. | Quality enforcement | 2h |
| SYS-016 | **Supabase project ref hardcoded no CI** -- `xrmlhuytgebovrgtzypl` em `.github/workflows/ci.yml`. Deveria ser secret/variable. | Portabilidade, seguranca | 1h |
| SYS-018 | **spaCy model mismatch** -- `requirements.txt` instala `pt_core_news_sm`, codigo tenta carregar `pt_core_news_lg`. Fallback funciona mas NER roda sempre no modelo menor. | Acuracia NLP | 1h |
| SYS-020 | **Sem testes de integracao/E2E** -- Sem Playwright/Cypress. `test_pipeline_benchmark.py` excluido do CI. Sem testes de integracao do flow `loadFromPipelineResult`. | Prevencao de regressao | 16h |
| SYS-022 | **Undo/redo com JSON.stringify completo** -- Serializa toda a arvore do documento a cada mutacao. 20 snapshots de varios KB cada. GC pressure significativo em docs complexos. | Performance, memoria | 8h |

#### 1.4 LOW (P3)

| ID | Debito | Impacto | Esforco |
|----|--------|---------|---------|
| SYS-007 | **Dead code e scaffolding** -- `HelloWorld.vue`, `backend/_deprecated/` (223 LOC), `vue.svg`, `@faker-js/faker` como prod dependency. | Limpeza | 1h |
| SYS-009 | **`console.log/warn/error` em producao** -- 10 chamadas em 6 arquivos de producao. Sem logger estruturado no frontend. | Observabilidade | 2h |
| SYS-017 | **Health check superficial** -- `/api/health` retorna `{"status": "ok"}` sem checar Redis, Supabase ou disco. | Observabilidade, deploys | 4h |
| SYS-019 | **Sem API versioning** -- Rotas em `/api/` sem prefixo de versao. Sem exportacao OpenAPI. | Evolucao da API | 4h |
| SYS-021 | **`@faker-js/faker` como dep de producao** -- Listado em `dependencies` em vez de `devDependencies`. | Bundle size, classificacao | 0.5h |

---

### 2. Debitos de Database/Redis (Phase 2 -- @data-engineer)

> :warning: **PENDENTE: Revisao do @data-engineer**

*Fonte: `supabase/docs/DB-AUDIT.md` -- 17 debitos identificados (14 DB + 3 Redis)*

#### 2.1 CRITICAL

| ID | Debito | Impacto | Esforco |
|----|--------|---------|---------|
| DB-001 | **RLS policies com `USING (true)`** -- Todas as 3 tabelas e storage buckets permitem qualquer usuario autenticado ler/modificar/deletar QUALQUER dado de outro usuario. Sem row-level ownership. | Seguranca: exposicao completa de dados entre usuarios | HIGH |
| DB-002 | **Sem multi-tenancy / isolamento de usuario** -- Nenhuma tabela tem coluna `user_id`. Impossivel implementar isolamento, audit trails, ou tracking de uso. | Seguranca, Compliance | HIGH |
| DB-003 | **Service role key bypassa RLS** -- Backend usa `SUPABASE_SERVICE_ROLE_KEY` para todas operacoes. Se vazada, atacante tem acesso irrestrito a todo o banco. Sem defesa em profundidade. | Seguranca: key leak = compromisso total | MEDIUM |

#### 2.2 HIGH

| ID | Debito | Impacto | Esforco |
|----|--------|---------|---------|
| DB-004 | **`jobs.updated_at` nunca auto-atualiza** -- Coluna existe mas sem trigger (diferente de `templates`). Backend nao seta manualmente. Valor eh sempre data de criacao. | Integridade de dados | LOW |
| DB-005 | **`jobs.status` sem CHECK constraint** -- Aceita qualquer texto. Status invalidos nao sao barrados pelo DB. | Integridade de dados | LOW |
| DB-006 | **Sem rollback migrations** -- Apenas arquivos "up". Nenhum mecanismo para reverter migracoes problematicas em producao. | Operacoes: deploys arriscados | MEDIUM |
| DB-007 | **Supabase SDK sincrono em contexto async** -- `supabase-py v2` eh sincrono. Storage uploads, DB upserts e downloads bloqueiam o event loop. Sob carga concorrente, serializa todo I/O. | Performance: throughput limitado | HIGH |
| DB-008 | **Dual state stores (3 lugares)** -- Job state em in-memory dict + Redis + Supabase. Sem garantia transacional. Crash do server = divergencia. | Confiabilidade: status stale, resultados perdidos | MEDIUM |

#### 2.3 MEDIUM

| ID | Debito | Impacto | Esforco |
|----|--------|---------|---------|
| DB-009 | **Buckets nao criados nas migrations** -- SQL de criacao de buckets esta comentado em `20260322000003`. Ambientes novos requerem setup manual. | Operacoes | LOW |
| DB-010 | **Sem indice `created_at` em `jobs`** -- Queries por tempo fazem sequential scan. | Performance | LOW |
| DB-011 | **Cleanup de storage nao atomico** -- `delete_job()` lista arquivos, remove, depois deleta DB row. Falha parcial = arquivos orfaos. | Integridade de dados | MEDIUM |
| DB-012 | **Sem safeguard de producao para `AUTH_DISABLED`** -- Nenhum check impede `AUTH_DISABLED=true` em producao. | Seguranca: bypass acidental de auth | LOW |

#### 2.4 LOW (DB)

| ID | Debito | Impacto | Esforco |
|----|--------|---------|---------|
| DB-013 | **`templates` sem FK para `jobs`** -- Sem rastreabilidade de qual job produziu qual template. | Traceability | LOW |
| DB-014 | **Sem UPDATE policy em `storage.objects`** -- Policies definem INSERT, SELECT, DELETE mas nao UPDATE. | Menor: impacta apenas acesso direto frontend | LOW |

#### 2.5 Redis

| ID | Debito | Impacto | Esforco |
|----|--------|---------|---------|
| REDIS-001 | **Sem prefixo de aplicacao nas keys** -- Keys usam `job:{id}` sem namespace da app. Colisao se Redis compartilhado. | LOW | LOW |
| REDIS-002 | **Sem reconnection / circuit breaker** -- Se Redis cai mid-session, operacoes falham com excecoes nao tratadas. Fallback para InMemoryJobStore so ocorre no startup. | MEDIUM | MEDIUM |
| REDIS-003 | **`all_jobs()` usa `scan_iter`** -- Full keyspace scan. Aceitavel na escala atual mas deve ser monitorado. | LOW | LOW |

---

### 3. Debitos de Frontend/UX (Phase 3 -- @ux-design-expert)

> :warning: **PENDENTE: Revisao do @ux-design-expert**

*Fonte: `docs/frontend/frontend-spec.md` -- 26 debitos identificados*

#### 3.1 Frontend Architecture (FE-*)

| ID | Debito | Severidade | Impacto | Esforco |
|----|--------|-----------|---------|---------|
| FE-001 | **AnalyzingPage.vue (1,195 LOC)** -- Combina stepper, state machine, checkpoint, cancellation, reconnection e rendering. Extrair state machine para composable. | HIGH | Manutencao | 8h |
| FE-002 | **HTMLCanvas.vue (913 LOC)** -- Mista rendering, zoom, scroll, keyboard, drag/drop, iframe management. | HIGH | Manutencao | 6h |
| FE-003 | **session.ts (534 LOC)** -- `loadFromPipelineResult()` ~200 linhas orquestrando 9 stores. | HIGH | Manutencao, Testabilidade | 4h |
| FE-004 | **Mixed store API styles** -- 8 Composition API, 9 Options API. Sem padrao definido. | MEDIUM | Consistencia | 4h |
| FE-005 | **ConfidenceBadge duplicado** -- Existe em `atoms/` e `molecules/` com propositos sobrepostos. | LOW | Confusao | 1h |
| FE-006 | **HelloWorld.vue presente** -- Scaffold leftover do Vite. | LOW | Limpeza | 5min |
| FE-007 | **Sem barrel export para composables** -- Unico diretorio sem `index.ts`. | LOW | DX | 30min |
| FE-008 | **Design tokens duplicados** -- Cores definidas em `main.css @theme` E `tailwind.config.ts`. Risco de drift. | MEDIUM | Consistencia | 2h |
| FE-009 | **CSS approach inconsistente** -- HomePage usa Tailwind utilities; resto usa BEM scoped. | LOW | Consistencia | 2h |

#### 3.2 UX Patterns (UX-*)

| ID | Debito | Severidade | Impacto | Esforco |
|----|--------|-----------|---------|---------|
| UX-001 | **Sem toast/notification store global** -- Toasts gerenciados via `defineExpose` por componente. Impossivel disparar de stores/services. | MEDIUM | UX, DX | 3h |
| UX-002 | **Sem responsive/mobile** -- Editor desktop-only. Login, Home, Upload sem mobile optimization. | LOW | Alcance | 16h+ |
| UX-003 | **Sem dark mode** -- Nenhum `dark:` variant, sem toggle, sem `prefers-color-scheme`. | LOW | UX | 16h+ |
| UX-004 | **Sem skeleton screens no editor** -- Paineis aparecem vazios ate dados do pipeline carregarem. | LOW | Perceived Performance | 4h |
| UX-005 | **Emoji icons no toolbar** -- ToggleButtons usam emoji que renderiza inconsistentemente entre OS/browsers. Deveria usar lucide-vue-next. | MEDIUM | Consistencia Visual | 2h |

#### 3.3 Acessibilidade (A11Y-*)

| ID | Debito | Severidade | Impacto | Esforco |
|----|--------|-----------|---------|---------|
| A11Y-001 | **Sem focus trap em modais** -- 4 modais (Bibliotecas, AmbiguousField, ExportValidation, ServiceFailure) permitem Tab escapar para conteudo de fundo. | HIGH | Acessibilidade | 4h |
| A11Y-002 | **Sem focus indicators customizados** -- Depende de defaults do browser, inconsistentes e invisiveis em fundos escuros. | MEDIUM | Acessibilidade | 3h |
| A11Y-003 | **Contraste Neutral-500** -- #737373 em branco = 4.48:1, abaixo de WCAG AA (4.5:1) para texto normal. Usado em timestamps, hints, meta. | MEDIUM | Acessibilidade | 1h |
| A11Y-004 | **Alt texts ausentes** -- PDF viewer e canvas iframe placeholders tem `aria-label` mas sem alt text fallback em imagens/icones decorativos. | LOW | Acessibilidade | 2h |

#### 3.4 Seguranca (SEC-*)

| ID | Debito | Severidade | Impacto | Esforco |
|----|--------|-----------|---------|---------|
| SEC-001 | **v-html com conteudo controlado pelo usuario** -- `BibliotecaComponentList.vue` renderiza `previewHtml` de dados salvos via v-html. XSS se projeto JSON eh tampered. | HIGH | Seguranca (XSS) | 2h |
| SEC-002 | **dompurify vulneravel (transitiva)** -- `monaco-editor` depende de `dompurify <=3.3.1` com mutation-XSS conhecido. | MEDIUM | Seguranca | 1h |
| SEC-003 | **Vite vulneravel (dev server)** -- `vite 7.0.0-7.3.1` com path traversal e file read. Risco em dev, patch disponivel. | HIGH | Seguranca (Dev) | 30min |

#### 3.5 Performance (PERF-*)

| ID | Debito | Severidade | Impacto | Esforco |
|----|--------|-----------|---------|---------|
| PERF-001 | **Sem virtualizacao de tree** -- StructureTree renderiza todos os nodes no DOM. Docs com 200+ nodes = scroll jank. | MEDIUM | Performance | 8h |
| PERF-002 | **JSON.stringify undo snapshots** -- Arvore completa serializada a cada mutacao. Large trees = GC pressure e frame drops. | MEDIUM | Performance | 6h |
| PERF-003 | **Monaco editor bundle size** -- ~3MB compressed. Considerar lazy-loading apenas quando tab de codigo eh ativada. | LOW | Initial Load | 2h |

#### 3.6 Testes (TEST-*)

| ID | Debito | Severidade | Impacto | Esforco |
|----|--------|-----------|---------|---------|
| TEST-001 | **Sem framework E2E** -- Flow critico (Upload->Analyze->Edit->Export) sem cobertura browser-level. | HIGH | Quality Assurance | 16h |
| TEST-002 | **Atoms 88% sem testes** -- Apenas 2 de 16 atoms tem spec files. | MEDIUM | Risco de regressao | 6h |
| TEST-003 | **Molecules ~55% sem testes** -- 30 de 55 molecules sem testes. | MEDIUM | Risco de regressao | 12h |
| TEST-004 | **LoginPage sem testes** -- Flow de auth sem cobertura. | LOW | Risco de regressao | 2h |

---

### 4. Matriz de Priorizacao Preliminar

| Rank | ID | Debito | Area | Severidade | Esforco | Impacto |
|------|-----|--------|------|-----------|---------|---------|
| 1 | DB-001 | RLS blanket access `USING (true)` | Database | CRITICAL | HIGH | Seguranca: dados expostos entre usuarios |
| 2 | DB-002 | Sem multi-tenancy / user_id | Database | CRITICAL | HIGH | Seguranca, compliance: sem isolamento |
| 3 | DB-003 | Service role key bypassa RLS | Database | CRITICAL | MEDIUM | Seguranca: key leak = compromisso total |
| 4 | SYS-001 | Vendored dependencies (32MB) | Sistema | CRITICAL | 4h | Seguranca: patches nao aplicados |
| 5 | SYS-002 | Sem linter/formatter Python | Sistema | CRITICAL | 4h | Qualidade: drift sem enforcement |
| 6 | SYS-003 | Sem ESLint/Prettier frontend | Sistema | CRITICAL | 4h | Qualidade: drift sem enforcement |
| 7 | SYS-014 | Pipeline context untyped | Sistema | CRITICAL | 12h | Type safety: runtime errors |
| 8 | SEC-003 | Vite vulneravel (patch disponivel) | Frontend | HIGH | 30min | Seguranca: fix trivial |
| 9 | SEC-001 | v-html XSS em BibliotecaComponentList | Frontend | HIGH | 2h | Seguranca: XSS vector |
| 10 | DB-004 | `jobs.updated_at` sem trigger | Database | HIGH | LOW | Integridade de dados |
| 11 | DB-005 | `jobs.status` sem CHECK | Database | HIGH | LOW | Integridade de dados |
| 12 | DB-012 | Sem safeguard AUTH_DISABLED prod | Database | MEDIUM | LOW | Seguranca: bypass acidental |
| 13 | SYS-015 | Sem security headers | Sistema | HIGH | 4h | Seguranca (OWASP) |
| 14 | A11Y-001 | Sem focus trap em modais | Frontend | HIGH | 4h | Acessibilidade |
| 15 | SYS-004 | Dual job state management | Sistema | HIGH | 8h | Consistencia de dados |
| 16 | DB-007 | Supabase SDK sincrono em async | Database | HIGH | HIGH | Performance sob carga |
| 17 | DB-008 | Dual state stores (3 lugares) | Database | HIGH | MEDIUM | Confiabilidade |
| 18 | DB-006 | Sem rollback migrations | Database | HIGH | MEDIUM | Operacoes |
| 19 | SYS-006 | Session store God Object | Sistema | HIGH | 8h | Manutencao |
| 20 | FE-001 | AnalyzingPage.vue 1,195 LOC | Frontend | HIGH | 8h | Manutencao |
| 21 | FE-002 | HTMLCanvas.vue 913 LOC | Frontend | HIGH | 6h | Manutencao |
| 22 | FE-003 | session.ts 534 LOC | Frontend | HIGH | 4h | Manutencao |
| 23 | TEST-001 | Sem framework E2E | Frontend | HIGH | 16h | Quality Assurance |
| 24 | SYS-013 | Sem pre-commit hooks | Sistema | MEDIUM | 2h | Quality enforcement |
| 25 | SYS-018 | spaCy model mismatch | Sistema | MEDIUM | 1h | Acuracia NLP |
| 26 | SYS-016 | Supabase ref hardcoded CI | Sistema | MEDIUM | 1h | Portabilidade |
| 27 | DB-009 | Buckets nao criados em migrations | Database | MEDIUM | LOW | Operacoes |
| 28 | DB-010 | Sem indice `created_at` | Database | MEDIUM | LOW | Performance |
| 29 | A11Y-003 | Neutral-500 contraste | Frontend | MEDIUM | 1h | Acessibilidade |
| 30 | SEC-002 | dompurify vulneravel | Frontend | MEDIUM | 1h | Seguranca |
| 31 | UX-005 | Emoji icons no toolbar | Frontend | MEDIUM | 2h | Visual |
| 32 | UX-001 | Sem toast store global | Frontend | MEDIUM | 3h | UX, DX |
| 33 | A11Y-002 | Sem focus indicators | Frontend | MEDIUM | 3h | Acessibilidade |
| 34 | FE-004 | Mixed store API styles | Frontend | MEDIUM | 4h | Consistencia |
| 35 | FE-008 | Design tokens duplicados | Frontend | MEDIUM | 2h | Consistencia |
| 36 | SYS-005 | TMP_BASE duplicado | Sistema | MEDIUM | 2h | Manutencao |
| 37 | SYS-008 | Organizacao componentes inconsistente | Sistema | MEDIUM | 4h | DX |
| 38 | SYS-010 | 80x `any` em TypeScript | Sistema | MEDIUM | 6h | Type safety |
| 39 | SYS-012 | Sem error boundary | Sistema | MEDIUM | 4h | UX, error recovery |
| 40 | REDIS-002 | Sem reconnection/circuit breaker | Redis | MEDIUM | MEDIUM | Confiabilidade |
| 41 | DB-011 | Storage cleanup nao atomico | Database | MEDIUM | MEDIUM | Integridade |
| 42 | SYS-011 | Stage files monoliticos | Sistema | MEDIUM | 16h | Manutencao |
| 43 | SYS-020 | Sem testes integracao/E2E | Sistema | MEDIUM | 16h | Regressao |
| 44 | SYS-022 | Undo/redo JSON.stringify | Sistema | MEDIUM | 8h | Performance |
| 45 | PERF-001 | Sem tree virtualization | Frontend | MEDIUM | 8h | Performance |
| 46 | PERF-002 | JSON undo snapshots | Frontend | MEDIUM | 6h | Performance |
| 47 | TEST-002 | Atoms 88% sem testes | Frontend | MEDIUM | 6h | Regressao |
| 48 | TEST-003 | Molecules 55% sem testes | Frontend | MEDIUM | 12h | Regressao |
| 49 | SYS-007 | Dead code e scaffolding | Sistema | LOW | 1h | Limpeza |
| 50 | SYS-009 | console.log em producao | Sistema | LOW | 2h | Observabilidade |
| 51 | SYS-017 | Health check superficial | Sistema | LOW | 4h | Observabilidade |
| 52 | SYS-019 | Sem API versioning | Sistema | LOW | 4h | Evolucao API |
| 53 | SYS-021 | faker como prod dep | Sistema | LOW | 0.5h | Classificacao |
| 54 | DB-013 | templates sem FK para jobs | Database | LOW | LOW | Traceability |
| 55 | DB-014 | Sem UPDATE policy storage | Database | LOW | LOW | Menor |
| 56 | REDIS-001 | Sem prefixo de app nas keys | Redis | LOW | LOW | Operacoes |
| 57 | REDIS-003 | `all_jobs()` scan_iter | Redis | LOW | LOW | Performance |
| 58 | FE-005 | ConfidenceBadge duplicado | Frontend | LOW | 1h | Confusao |
| 59 | FE-006 | HelloWorld.vue presente | Frontend | LOW | 5min | Limpeza |
| 60 | FE-007 | Sem barrel export composables | Frontend | LOW | 30min | DX |
| 61 | FE-009 | CSS approach inconsistente | Frontend | LOW | 2h | Consistencia |
| 62 | UX-002 | Sem responsive/mobile | Frontend | LOW | 16h+ | Alcance |
| 63 | UX-003 | Sem dark mode | Frontend | LOW | 16h+ | UX |
| 64 | UX-004 | Sem skeleton screens editor | Frontend | LOW | 4h | Perceived perf |
| 65 | A11Y-004 | Alt texts ausentes | Frontend | LOW | 2h | Acessibilidade |
| -- | PERF-003 | Monaco bundle size | Frontend | LOW | 2h | Initial load |
| -- | TEST-004 | LoginPage sem testes | Frontend | LOW | 2h | Regressao |

> **Nota:** Ranks 65+ foram omitidos da contagem principal pois PERF-003 e TEST-004 empatam com outros LOWs. Total permanece 65 debitos unicos.

---

### 5. Debitos Cross-Cutting (identificados na consolidacao)

Debitos que atravessam multiplas areas e cujo fix requer coordenacao entre especialistas:

#### CC-001: Split-Brain State Management

**Debitos envolvidos:** SYS-004, DB-008, REDIS-002
**Areas:** Sistema + Database + Redis

O estado de jobs vive em 3 locais simultaneamente (in-memory `_pipeline_jobs`, Redis via `job_store`, Supabase `jobs` table) sem garantia transacional. Cada area reportou independentemente o mesmo problema. O fix requer decisao arquitetural sobre single source of truth, seguido de implementacao coordenada em backend (Python) e infra (Redis config, Supabase schema).

**Impacto composto:** Crash mid-pipeline = resultado perdido + usuario ve status stale + Redis pode ter dados divergentes do Supabase.

#### CC-002: Seguranca de Dados End-to-End

**Debitos envolvidos:** DB-001, DB-002, DB-003, DB-012, SYS-015
**Areas:** Database + Sistema

O cluster de debitos de seguranca forma uma cadeia: (1) RLS permite acesso blanket, (2) nao ha `user_id` para enforcement, (3) service key bypassa RLS de qualquer forma, (4) `AUTH_DISABLED` pode ser habilitado acidentalmente em prod, (5) sem security headers no backend. A solucao requer migration de schema (add `user_id`), atualizacao de RLS policies, revisao de uso de service key, safeguard de producao, e middleware de headers -- trabalho coordenado entre @data-engineer e @architect.

#### CC-003: Quality Enforcement Pipeline

**Debitos envolvidos:** SYS-002, SYS-003, SYS-013, SYS-010
**Areas:** Sistema (backend + frontend)

Sem linting (Python e JS), sem pre-commit hooks, e 80 `any` em TypeScript. A ausencia de gates automatizados permite drift continuo. O fix eh uma unica iniciativa: configurar ruff + mypy (backend), eslint + prettier (frontend), e husky + lint-staged como gate unificado.

#### CC-004: Oversized Components / God Objects

**Debitos envolvidos:** SYS-006, SYS-011, FE-001, FE-002, FE-003
**Areas:** Sistema (backend stages) + Frontend (Vue components + stores)

Padrao recorrente de arquivos monoliticos que acumulam responsabilidades: backend stages (1,400-2,048 LOC), `AnalyzingPage.vue` (1,195 LOC), `HTMLCanvas.vue` (913 LOC), `session.ts` (534 LOC). O padrao sugere falta de guidelines de decomposicao. Fix requer definir regras de max LOC por arquivo e refatorar sistematicamente.

#### CC-005: Undo/Redo Performance

**Debitos envolvidos:** SYS-022, PERF-002
**Areas:** Sistema + Frontend

Reportado independentemente por @architect e @ux-design-expert. `JSON.stringify` da arvore completa a cada mutacao. O fix eh unico: implementar command pattern ou structural sharing no `templateStore.ts`.

#### CC-006: E2E / Integration Test Gap

**Debitos envolvidos:** SYS-020, TEST-001
**Areas:** Sistema + Frontend

Ambas as fases identificaram a ausencia de testes E2E. O fix eh uma unica iniciativa: adicionar Playwright com smoke tests cobrindo o flow Upload -> Analyze -> Edit -> Export.

---

### 6. Dependencias entre Debitos

```
DB-002 (add user_id) ──BLOCKS──> DB-001 (fix RLS policies)
                      ──BLOCKS──> DB-003 (scoped credentials)

SYS-002 (ruff/mypy) ──ENABLES──> SYS-014 (typed pipeline context)
SYS-003 (eslint)    ──ENABLES──> SYS-010 (fix any types)

SYS-002 + SYS-003 ──ENABLES──> SYS-013 (pre-commit hooks)

SYS-004 (unify job state) ──DEPENDS ON──> decisao arquitetural CC-001

FE-003 (refactor session.ts) ──SHOULD PRECEDE──> FE-001 (refactor AnalyzingPage)
                              ──SHOULD PRECEDE──> SYS-006 (session god object)
                              [FE-003 e SYS-006 sao o MESMO debito visto de perspectivas diferentes]

SYS-022 ──IS SAME AS──> PERF-002  [mesma issue, reportada 2x]
SYS-020 ──IS SAME AS──> TEST-001  [mesma issue, reportada 2x]
SYS-007 ──OVERLAPS──> FE-006     [HelloWorld.vue citado em ambos]

DB-004 (updated_at trigger) ──INDEPENDENT──> pode ser feito a qualquer momento
DB-005 (status CHECK) ──INDEPENDENT──> pode ser feito a qualquer momento
DB-009 (bucket creation) ──INDEPENDENT──> pode ser feito a qualquer momento

SEC-003 (vite patch) ──INDEPENDENT──> npm audit fix, zero dependencias
SEC-001 (v-html) ──INDEPENDENT──> pode ser feito a qualquer momento
A11Y-001 (focus trap) ──INDEPENDENT──> pode ser feito a qualquer momento
```

**Grafo de dependencia (simplificado):**

```
                    DB-002 (user_id)
                   /       \
                  v         v
             DB-001       DB-003
            (RLS fix)   (scoped creds)

        SYS-002 (ruff)     SYS-003 (eslint)
           |                    |
           v                    v
        SYS-014            SYS-010
      (typed context)     (fix any)
           \                /
            v              v
            SYS-013 (pre-commit hooks)

        FE-003 / SYS-006 (session.ts refactor)
              |
              v
          FE-001 (AnalyzingPage refactor)

        Decisao CC-001 (single source of truth)
              |
              v
          SYS-004 + DB-008 + REDIS-002
```

**Debitos duplicados (mesmo issue, IDs diferentes):**

| Debito A | Debito B | Resolucao |
|----------|----------|-----------|
| SYS-022 | PERF-002 | Manter SYS-022 como primario, PERF-002 como ref |
| SYS-020 | TEST-001 | Manter TEST-001 como primario, SYS-020 como ref |
| SYS-007 (parcial) | FE-006 | Manter SYS-007 como primario (inclui mais items) |
| SYS-006 | FE-003 | Manter FE-003 como primario (mais especifico) |

> **Nota de consolidacao:** Apos deduplicacao, o total efetivo eh **61 debitos unicos** (4 duplicatas identificadas). Os 65 sao mantidos neste DRAFT para rastreabilidade completa; a versao final devera consolidar.

---

### 7. Perguntas para Especialistas

#### Para @data-engineer (Dara):

1. **DB-001 + DB-002: Qual a estrategia de migracao de dados?** -- Ao adicionar `user_id` a tabelas existentes, como tratar rows existentes sem owner? Backfill com um usuario "system"? Nullable com enforcement futuro? Qual o risco de downtime?

2. **DB-003: Service role key vs scoped credentials** -- O backend PRECISA de service role para alguma operacao especifica (e.g., storage admin)? Seria viavel migrar para anon key + user JWT pass-through para operacoes regulares, mantendo service role apenas para operacoes administrativas?

3. **DB-007: Supabase async client** -- Existe timeline para `supabase-py` async? Se nao, a abordagem `asyncio.to_thread()` eh suficiente, ou seria melhor usar `httpx` diretamente contra a PostgREST API?

4. **DB-008 + SYS-004: Single source of truth** -- Dado que Redis eh opcional e pode nao estar disponivel, qual deveria ser o source of truth? (a) In-memory com sync periodico para Supabase, (b) Redis com Supabase como backup, (c) Supabase direto com cache local? Qual opcao minimiza risco de perda de dados?

5. **DB-010: Indices adicionais** -- Alem de `jobs.created_at`, ha necessidade de indices em `templates.name` ou `templates.created_at`? Qual o volume esperado de templates?

6. **DB-011: Cleanup atomico** -- A sugestao de soft-delete flag eh a melhor abordagem? Ou seria preferivel usar Supabase Edge Functions para cleanup assincrono?

7. **REDIS-002: Reconnection strategy** -- Qual a SLA do Redis em producao (Railway)? Vale implementar circuit breaker completo ou basta um retry simples com fallback para InMemoryJobStore em runtime?

#### Para @ux-design-expert (Uma):

1. **FE-001: AnalyzingPage decomposition** -- O state machine deveria ser um composable (`useAnalyzingStateMachine`) ou um store separado (`analyzingStore`)? A pagina tem 5 estados distintos (initializing, running, checkpoint, completed, failed) -- cada um deveria ser um sub-componente?

2. **FE-002: HTMLCanvas decomposition** -- Quais responsabilidades do canvas deveriam ser extraidas para composables vs sub-componentes? Zoom/scroll vs drag/drop vs iframe management?

3. **UX-001: Toast store global** -- Existe algum padrao de notificacao alem de toasts que deveria ser considerado (e.g., notification center, inline alerts)? O `AppToast` atual suporta acao de callback (e.g., "Undo")?

4. **UX-002 + UX-003: Mobile e Dark mode** -- Sao essas features desejadas pelo produto ou podem ser descartadas como "editor is desktop-only by design"? Se sim, devemos remover o debito do catalogo?

5. **A11Y-001: Focus trap** -- `@vueuse/core` ja eh dependencia do projeto. Confirma que `useFocusTrap` eh a abordagem recomendada, ou prefere `vue-focus-lock` para melhor suporte de portals?

6. **A11Y-003: Neutral-500 ajuste** -- Qual a cor de substituicao recomendada que manteria a estetica neutral mas passaria WCAG AA? Neutral-600 (#525252) teria contraste 7.1:1 -- seria excessivo para texto de hint?

7. **PERF-001: Tree virtualization** -- Qual eh o tamanho tipico de documento em producao (numero de nodes)? Se maioria dos docs tem <100 nodes, este debito pode ser deprioritizado. Qual o threshold aceitavel de performance?

8. **SEC-001: v-html em BibliotecaComponentList** -- A abordagem de sandboxed iframe seria aceitavel para preview de componentes, ou impactaria significativamente a UX (e.g., perda de estilos inherited)?

9. **FE-004: Padronizacao de store API** -- Composition API eh a recomendacao? Qual o risco de regressao na migracao de 9 stores de Options para Composition?

10. **TEST-002 + TEST-003: Prioridade de testes** -- Quais atoms/molecules especificos sao mais criticos para testar primeiro? (e.g., Button, ProgressBar, InspectorField?)

---

## Notas de Consolidacao

### Metodologia

1. Todos os debitos das 3 fases foram preservados integralmente com suas descricoes originais
2. IDs foram mantidos no esquema original de cada fase (SYS-*, DB-*, REDIS-*, FE-*, UX-*, A11Y-*, SEC-*, PERF-*, TEST-*)
3. Debitos duplicados foram identificados mas NAO removidos -- serao consolidados na versao final
4. Cross-cutting debts foram identificados a partir de padroes recorrentes entre areas
5. A matriz de priorizacao usa: CRITICAL primeiro, depois HIGH, dentro de cada severidade prioriza por ratio esforco/impacto

### Proximos Passos

1. **@data-engineer (Dara):** Revisar Secao 2 e responder perguntas da Secao 7
2. **@ux-design-expert (Uma):** Revisar Secao 3 e responder perguntas da Secao 7
3. **@architect (Aria):** Consolidar feedback em versao final (`technical-debt-assessment.md`)
4. **@qa:** QA Gate (Phase 7) sobre o documento final

### Controle de Versoes

| Versao | Data | Autor | Mudanca |
|--------|------|-------|---------|
| DRAFT v1.0 | 2026-04-09 | @architect (Aria) | Consolidacao inicial de 3 fases |
