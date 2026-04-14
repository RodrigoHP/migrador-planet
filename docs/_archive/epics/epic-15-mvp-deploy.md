# Epic 15 — MVP Deploy: Production-Ready Infrastructure

## Epic Goal

Levar o migrador-planet de ambiente local para **produção acessível via web**, com autenticação, persistência de jobs resiliente, e código limpo — usando Vercel (frontend) + Railway (backend) + Supabase (Auth + DB + Storage) + Redis (job state).

## Epic Description

### Existing System Context

- **Funcionalidade atual:** Plataforma completa de engenharia reversa de PDFs → HTML templates. Pipeline 5 stages (Epic 13), editor visual 100% fidelidade (Epic 14). 14 epics concluídos, ~143 stories, 22 PRs.
- **Technology stack:** Vue 3 + TypeScript + Pinia + Vite (frontend), FastAPI + Python (backend), Supabase (DB + Storage), OpenRouter (AI)
- **Integration points:** StorageGateway (local/supabase), SSE progress tracking, 8 API routers, 18 Pinia stores
- **Referência arquitetural:** `docs/architecture/brownfield-system-architecture.md` (Brownfield Discovery Phase 1, ADR-006)

### Enhancement Details

- **O que está sendo adicionado:** Deploy infrastructure (Vercel + Railway), autenticação (Supabase Auth), job persistence (Redis), rate limiting, input validation, limpeza de código morto
- **Diagnóstico:** Sistema funcional mas 100% local. 4 blockers para produção identificados no brownfield audit (TD-01 a TD-04). Com escolha de Vercel + Railway, TD-04 eliminado e TD-03 reduzido.
- **Estratégia:** 3 waves — infraestrutura → segurança → cleanup
- **Success criteria:** Aplicação acessível via URL pública, com login, jobs persistentes entre restarts, e pipeline antigo removido

### Architectural Decision

**ADR-006: Vercel + Railway + Supabase** (decidido 2026-03-23)
- Vercel: Frontend SPA, auto-deploy, preview URLs por PR
- Railway: Backend Python nativo (sem Docker), Redis addon grátis, suporta processos longos + SSE
- Supabase Auth: Já no stack, apenas wiring necessário
- Alternativas descartadas: Docker (overhead), AWS/GCP (over-engineering), Vercel Serverless (incompatível com deps pesadas)

---

## Escopo por Wave

### Wave 1 — Deploy Infrastructure (~2-3 dias)
**Objetivo:** Aplicação rodando em produção com URLs públicas.

| Story | Item | Tech Debt | Executor | Quality Gate | Estimativa | Status |
|-------|------|-----------|----------|--------------|------------|--------|
| 15.1 | **Deploy backend Railway** + Procfile + env vars + CORS dinâmico | TD-04, TD-06, TD-12 | @devops | @architect | S | ✅ Done |
| 15.2 | **Deploy frontend Vercel** + env vars + API URL config | — | @devops | @architect | XS | ✅ Done |

### Wave 2 — Auth + Job Persistence (~5-7 dias)
**Objetivo:** Sistema seguro com jobs resilientes.

| Story | Item | Tech Debt | Executor | Quality Gate | Estimativa | Status |
|-------|------|-----------|----------|--------------|------------|--------|
| 15.3 | **Supabase Auth integration** — middleware FastAPI + frontend auth flow | TD-02 | @dev | @architect | M | ✅ Done |
| 15.4 | **Redis job persistence** — migrar `_pipeline_jobs` dict → Redis | TD-01 | @dev | @architect | M | ✅ Done |
| 15.5 | **Rate limiting + input validation** — slowapi + file size/page limits | TD-07, TD-11 | @dev | @architect | S | ✅ Done |

### Wave 3 — Code Cleanup (~3-4 dias)
**Objetivo:** Código limpo, sem dead code do pipeline antigo.

| Story | Item | Tech Debt | Executor | Quality Gate | Estimativa | Status |
|-------|------|-----------|----------|--------------|------------|--------|
| 15.6 | **Remove old 28-stage pipeline** + dead stage helpers audit | TD-05, TD-16 | @dev | @architect | S | ✅ Done |
| 15.7 | **GitHub Actions CI** — pytest + vitest on PR | TD-03 | @devops | @architect | S | ✅ Done |
| 15.8 | Bug: Auth ES256 JWKS | — | @dev | @qa | XS | ✅ Done |
| 15.9–20 | Fixes diversos (env, upload, analyzing-page, layout, screenshot, job, stages, vision) | — | @dev | @qa | — | ✅ Done |
| 15.21 | Fix analyzing-page spec import quebrado | — | @dev | @qa | XS | 📝 Draft |

### Deferred (Post-MVP)

| Item | Tech Debt | Razão |
|------|-----------|-------|
| Global error boundary (frontend) | TD-08 | Railway logs suficiente |
| Centralize API client | TD-10 | Funciona, não quebra |
| Component decomposition | TD-14 | Funciona, não quebra |
| E2E testing (Playwright) | TD-17 | Manual testing aceitável |
| Sentry/monitoring | — | Railway dashboard built-in |
| Docker/containerização | TD-04 | Railway não precisa |
| Editor state consolidation | TD-15 | Funciona, não quebra |

---

## Stories Detalhadas

### Story 15.1 — Deploy Backend Railway + CORS Dinâmico
- **Description:** Configurar Railway para deploy do backend FastAPI. Criar `Procfile`, configurar env vars (OPENROUTER_API_KEY, STORAGE_MODE, SUPABASE_URL/KEY, ALLOWED_ORIGINS), fazer CORS ler de env var em vez de hardcoded localhost:5173. Download do spaCy model no build.
- **Executor:** `@devops` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[infra_review, env_validation, security_scan]`
- **Tech Debt resolvido:** TD-04 (eliminado), TD-06 (hardcoded /tmp), TD-12 (CORS hardcoded)
- **Acceptance Criteria:**
  - [ ] `Procfile` criado na raiz com comando uvicorn
  - [ ] CORS lê `ALLOWED_ORIGINS` de env var (comma-separated)
  - [ ] `/tmp/jobs` funciona no Railway (ou usa env var `TMP_DIR`)
  - [ ] spaCy model `pt_core_news_lg` baixado no build (nixpacks ou Procfile)
  - [ ] `GET /api/health` retorna 200 no Railway
  - [ ] SSE `/api/analyze/{job_id}/progress` funciona através do Railway proxy
  - [ ] Testes existentes passam sem modificação

### Story 15.2 — Deploy Frontend Vercel
- **Description:** Configurar Vercel para deploy do frontend Vue 3 + Vite. Configurar env var `VITE_API_URL` para apontar ao Railway backend. Configurar rewrite rules para SPA routing.
- **Executor:** `@devops` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[infra_review, build_validation]`
- **Acceptance Criteria:**
  - [ ] `vercel.json` criado com rewrites para SPA (`/index.html` fallback)
  - [ ] `VITE_API_URL` configurado para URL do Railway
  - [ ] Frontend builds sem erros no Vercel
  - [ ] Todas as 4 rotas (/, /upload, /analyzing, /editor) funcionam
  - [ ] API calls do frontend chegam ao backend Railway
  - [ ] Preview URLs funcionam em PRs
  - [ ] Testes existentes passam sem modificação

### Story 15.3 — Supabase Auth Integration
- **Description:** Integrar Supabase Auth no backend (FastAPI middleware que valida JWT) e frontend (login/logout flow, token management). Proteger todas as rotas API exceto `/api/health`. Frontend redireciona para login se não autenticado.
- **Executor:** `@dev` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[code_review, security_scan, pattern_validation]`
- **Tech Debt resolvido:** TD-02
- **Acceptance Criteria:**
  - [ ] FastAPI dependency `get_current_user()` valida JWT do Supabase
  - [ ] Todas as rotas (exceto `/api/health`) requerem token válido
  - [ ] Frontend: página de login com email/password via Supabase Auth
  - [ ] Frontend: token armazenado e enviado em `Authorization: Bearer` header
  - [ ] Frontend: redirect para login se 401
  - [ ] Frontend: logout limpa token e redireciona
  - [ ] Jobs associados ao `user_id` do token
  - [ ] Testes existentes adaptados com mock de auth

### Story 15.4 — Redis Job Persistence
- **Description:** Migrar `_pipeline_jobs` dict in-memory (`routers/analyze.py`) para Redis (Railway addon). Jobs sobrevivem a restarts. SSE replay buffer mantido via Redis pub/sub ou list.
- **Executor:** `@dev` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[code_review, pattern_validation, performance_review]`
- **Tech Debt resolvido:** TD-01
- **Acceptance Criteria:**
  - [ ] Railway Redis addon provisionado
  - [ ] `_pipeline_jobs` dict substituído por Redis hash/keys
  - [ ] Job state (status, result, error, event_log) persistido em Redis
  - [ ] TTL de 1h mantido (Redis EXPIRE)
  - [ ] SSE replay buffer funciona via Redis (list ou pub/sub)
  - [ ] Pipeline resume funciona após restart do servidor
  - [ ] `cancel_flag` funciona com Redis (pub/sub ou polling)
  - [ ] Fallback para in-memory se Redis indisponível (dev local)
  - [ ] Testes existentes passam com mock de Redis

### Story 15.5 — Rate Limiting + Input Validation
- **Description:** Adicionar rate limiting via `slowapi` (10 req/min por IP em `/api/analyze`, 30 req/min global). Validar file size (max 50MB por PDF) e page count (max 500 páginas total) no upload.
- **Executor:** `@dev` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[code_review, security_scan]`
- **Tech Debt resolvido:** TD-07, TD-11
- **Acceptance Criteria:**
  - [ ] `slowapi` instalado e configurado como middleware
  - [ ] `/api/analyze` limitado a 10 req/min por IP
  - [ ] Rotas gerais limitadas a 30 req/min por IP
  - [ ] Upload rejeita PDFs > 50MB com 413 Payload Too Large
  - [ ] Upload rejeita se total de páginas > 500 com 422
  - [ ] Rate limit headers presentes nas respostas (X-RateLimit-*)
  - [ ] Erros de rate limit retornam 429 com mensagem clara
  - [ ] Testes validam limites de file size e page count

### Story 15.6 — Remove Old 28-Stage Pipeline + Dead Code Audit
- **Description:** Remover `StageRegistry` e blocos do pipeline antigo de 28 stages (`models/pipeline.py`). Auditar os 31 helper files em `services/stages/` para identificar e remover dead code que não é usado pelo pipeline v2 de 5 stages. Manter `_deprecated/` como referência se necessário.
- **Executor:** `@dev` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[code_review, pattern_validation, regression_test]`
- **Tech Debt resolvido:** TD-05, TD-16
- **Acceptance Criteria:**
  - [ ] `StageRegistry` com 8 blocks removido de `models/pipeline.py`
  - [ ] `BlockDefinition`, `StageDefinition` legados removidos (se não usados pelo v2)
  - [ ] Cada um dos 31 helper files em `stages/` auditado:
    - Se usado por stage1-5: MANTER
    - Se não usado: REMOVER
  - [ ] `register_all.py` atualizado (se referenciava stages antigos)
  - [ ] Imports quebrados corrigidos
  - [ ] Todos os testes existentes passam
  - [ ] Nenhum `import` referencia entidades removidas (grep validation)

### Story 15.7 — GitHub Actions CI (pytest + vitest)
- **Description:** Criar workflow GitHub Actions que roda `pytest` (backend) e `vitest` (frontend) em cada PR para main. Não inclui deploy (Vercel e Railway fazem auto-deploy).
- **Executor:** `@devops` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[infra_review, ci_validation]`
- **Tech Debt resolvido:** TD-03 (residual)
- **Acceptance Criteria:**
  - [ ] `.github/workflows/ci.yml` criado
  - [ ] Trigger: `pull_request` para `main`
  - [ ] Job backend: Python 3.11, install requirements, `pytest` (sem spaCy model para speed)
  - [ ] Job frontend: Node 20, install, `npm run typecheck`, `npm run test`
  - [ ] Jobs rodam em paralelo
  - [ ] PR bloqueado se CI falha (branch protection rule)
  - [ ] Tempo de CI < 5 minutos

---

## Compatibility Requirements

- [x] Pipeline 5 stages (Epic 13) não é alterado
- [x] Editor visual (Epic 14) não é alterado
- [x] StorageGateway pattern preservado (supabase mode em prod)
- [x] SSE progress tracking preservado
- [x] Todos os 140+ testes existentes devem passar
- [ ] API contracts mantidos (novos headers de auth são aditivos)

## Risk Mitigation

- **Primary Risk:** Auth middleware quebra pipeline flow (SSE + long-running jobs)
  - **Mitigation:** Auth valida token uma vez no início, não em cada SSE event
  - **Rollback:** Env var `AUTH_ENABLED=false` desativa middleware

- **Secondary Risk:** Redis indisponível causa falha total
  - **Mitigation:** Fallback para in-memory se `REDIS_URL` não configurado
  - **Rollback:** Remove Redis config, volta para in-memory

- **Tertiary Risk:** spaCy model falha no build do Railway
  - **Mitigation:** Download no Procfile ou custom nixpacks
  - **Rollback:** Pre-baked model no repo (last resort)

## Definition of Done

- [x] Aplicação acessível via URL pública (Vercel + Railway)
- [x] Login funcional com Supabase Auth
- [x] Jobs persistem entre restarts (Redis)
- [x] Rate limiting ativo em produção
- [x] Pipeline antigo (28 stages) removido
- [x] CI rodando em PRs (pytest + vitest)
- [x] Todos os testes existentes passam
- [x] Zero downtime no deploy
- [ ] 15.21 — Fix analyzing-page spec import quebrado (Draft)

---

## Story Manager Handoff

"Please develop detailed user stories for this MVP Deploy epic. Key considerations:

- This is infrastructure + security work on an existing production-ready system
- Integration points: FastAPI routers (8), StorageGateway, SSE progress, Pinia stores (18)
- Existing patterns to follow: StorageGateway factory pattern, Pinia store hub pattern
- Critical compatibility: Pipeline 5 stages + Editor visual must work unchanged
- Each story must include verification that existing 140+ tests pass
- Wave 1 (deploy) should be completed FIRST as other waves depend on infra being live
- Auth story (15.3) is the most complex — affects both frontend and backend

The epic should maintain system integrity while delivering production-ready infrastructure."

---

*— Morgan, planejando o futuro 📊*
