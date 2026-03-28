# Brownfield Discovery — System Architecture Audit

**Phase:** 1 of 10 (Data Collection)
**Agent:** @architect (Aria)
**Date:** 2026-03-23
**Scope:** Post-Epic 13 + Epic 14 — Full system audit
**Status:** COMPLETE

---

## 1. Executive Summary

O **migrador-planet** é uma plataforma de engenharia reversa de documentos que converte PDFs gerados pelo motor PlanetPress em templates HTML/Knockout.js reutilizáveis. Após a conclusão dos Epics 13 (Pipeline Redesign) e 14 (Editor Visual), o sistema está funcional e maduro, mas apresenta **tech debt acumulado** dos epics iniciais e **gaps de infraestrutura** que impedem deploy em produção.

### Deploy Strategy (MVP)

| Camada | Serviço | Custo MVP | Justificativa |
|--------|---------|-----------|---------------|
| **Frontend** | **Vercel** | Free | Vue 3 + Vite = deploy nativo. Preview URL por PR grátis. Auto-deploy on push. |
| **Backend** | **Railway** | ~$5-10/mo | Deploy direto de `requirements.txt` + `Procfile`. Sem Docker. Suporta processos longos, SSE, /tmp filesystem. Redis addon grátis. |
| **DB + Storage + Auth** | **Supabase** | Free tier | Já integrado. DB, Storage buckets, Auth — tudo pronto para ativar. |
| **AI** | **OpenRouter** | ~$0.20/job | Já integrado. Sem mudança necessária. |

> **Decisão arquitetural:** Docker/containerização **descartado** para MVP. Railway faz build nativo de Python. Vercel + Railway fornecem CI/CD automático (auto-deploy on push). Isso elimina TD-04 e reduz TD-03 significativamente.

### Números-Chave

| Métrica | Valor |
|---------|-------|
| Epics completos | 14 |
| Stories entregues | ~143 |
| Componentes Vue | 126 |
| Pinia Stores | 18 |
| Composables | 37 |
| Stages backend | 5 (redesenhados de 28) |
| Linhas de stage code | ~6.839 |
| Arquivos de teste backend | 34 |
| Arquivos de teste frontend | 106 |
| PRs mergeados | 22 |

---

## 2. Architecture Overview (Current State v5.0)

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 FRONTEND — Vercel (Free)                  │
│  Pages: Home → Upload → Analyzing → TemplateEditor      │
│  Stack: Vue 3 + TS + Pinia + Vite + TailwindCSS         │
│  Editor: Monaco + PDF.js + Chart.js + Konva.js           │
│  Storage: IndexedDB (idb) para persistência local        │
│  Deploy: Auto on push to main. Preview URLs per PR.      │
├─────────────────────────────────────────────────────────┤
│                 API (REST + SSE)                          │
│  Prod: https://{app}.up.railway.app/api                  │
│  Dev:  Vite proxy → localhost:8000                       │
├─────────────────────────────────────────────────────────┤
│                BACKEND — Railway (~$5-10/mo)              │
│  8 Routers: analyze, upload, preview, generate,          │
│             export, auto_fix, assets, font                │
│  Pipeline: 5 stages (orchestrator_v2)                    │
│  Storage: StorageGateway (local | supabase)              │
│  AI: OpenRouter (GPT-4o Vision, Gemini Flash)            │
│  NLP: spaCy pt_core_news_lg                              │
│  Jobs: Redis (Railway addon, free)                       │
│  Auth: Supabase JWT verification middleware              │
│  Deploy: Auto on push. Procfile + requirements.txt.      │
├─────────────────────────────────────────────────────────┤
│              DATABASE — Supabase (Free tier)              │
│  Tables: job_clusters, templates                         │
│  Storage: Buckets com RLS                                │
│  Auth: Supabase Auth (JWT, email/password)               │
│  Migrations: 3 SQL files (2026-03-22)                    │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Pipeline Architecture (5 Stages)

```
PDF(s) + XSD + Data
       │
       ▼
┌──────────────────┐
│ Stage 1: Layout  │ → Clusters páginas idênticas (tolerant clustering)
│ Clustering       │   3 defense layers + pHash + LLM validation
│ (1.372 lines)    │   Output: clusters[], _raw_text_blocks
└───────┬──────────┘
        ▼
┌──────────────────┐
│ Stage 2: Deep    │ → Extrai tudo de representativas only
│ Extraction       │   text, fonts, images, tables, drawings, screenshots
│ (1.217 lines)    │   Output: enriched_documents[]
└───────┬──────────┘
        ▼
┌──────────────────┐
│ Stage 3: Struct  │ → Classifica blocks (label/dynamic/stability)
│ Analysis         │   3 layers: statistical → regex → spaCy NER
│ (1.547 lines)    │   GPT-4o Vision (obrigatório) → document_trees[]
└───────┬──────────┘
        ▼
┌──────────────────┐
│ Stage 4: Field   │ → Match XSD paths, 2-pass + LLM batch
│ Mapping          │   Format detection, confidence scoring
│ (1.238 lines)    │   Output: field_mappings[], ~95% accuracy
└───────┬──────────┘
        ▼
┌──────────────────┐
│ Stage 5: Template│ → Tree-driven HTML+CSS generation
│ Generation       │   Multi-doc connection, layout switching
│ (1.465 lines)    │   Output: result_json (completo)
└──────────────────┘
```

### 2.3 Frontend Component Architecture

```
Atomic Design Pattern:
  atoms/      (14) → Button, ProgressBar, ColorPicker, etc.
  molecules/  (51) → BorderEditor, SnapLineOverlay, InspectorField, etc.
  organisms/  (44) → LeftPanel, CenterPanel, InspectorPanel, HTMLCanvas, etc.
  pages/       (4) → Home, Upload, Analyzing, TemplateEditor
  layouts/     (2) → EditorLayout (3-pane), FullWidthLayout

Store Hub Pattern:
  session (hub) ──→ hydrates 14 stores via loadFromPipelineResult()
  editorStore (UI) ──→ independent, tabs/zoom/selection
  templateStore (data) ──→ document tree, node CRUD, undo
  layout (persistent) ──→ IDB save/load per layout
```

---

## 3. Tech Debt Inventory

### 3.1 CRITICAL — Bloqueia produção

| ID | Debt | Localização | Impacto | Esforço | Deploy Fix |
|----|------|-------------|---------|---------|------------|
| **TD-01** | **Job state in-memory only** | `routers/analyze.py` — `_pipeline_jobs` dict | Jobs perdidos no restart do servidor. Zero resiliência. | S | Railway Redis addon (grátis, 1 clique) |
| **TD-02** | **Zero autenticação/autorização** | Todas as rotas API | API completamente aberta. Qualquer pessoa acessa qualquer job. | S | Supabase Auth (já no stack, só wiring) |
| **TD-03** | ~~**Sem CI/CD**~~ → **Reduzido** | `.github/workflows/` vazio | ~~Deploy manual~~ → Vercel + Railway = auto-deploy on push. Falta: testes em PR. | XS | Vercel + Railway auto-deploy |
| ~~**TD-04**~~ | ~~**Sem containerização**~~ | ~~Raiz do projeto~~ | **ELIMINADO.** Railway faz build nativo de Python via `Procfile`. Docker desnecessário para MVP. | — | Railway Procfile (1 linha) |

### 3.2 HIGH — Risco operacional

| ID | Debt | Localização | Impacto | Esforço |
|----|------|-------------|---------|---------|
| **TD-05** | **Old 28-stage pipeline still present** | `models/pipeline.py` — `StageRegistry` com 8 blocks | Código morto confunde devs. StageRegistry ainda referenciado em imports. | S |
| **TD-06** | **Hardcoded `/tmp/jobs`** | `routers/analyze.py` — `TMP_BASE` | Não funciona em Windows nativo. Assume filesystem Unix. | S |
| **TD-07** | **Sem rate limiting** | Todas as rotas | LLM calls custam $0.15/job. Sem proteção contra abuse. | S |
| **TD-08** | **Sem global error boundary (frontend)** | Composables/components | Erros de API handled inline. Sem error tracking (Sentry etc). | S |
| **TD-09** | **TTL eviction on-demand only** | `routers/analyze.py` | Cleanup de jobs roda só quando próximo request chega. Sem background scheduler. | S |
| **TD-10** | **Mixed HTTP patterns (frontend)** | `services/`, composables, components | Calls API espalhados em 3+ locais. Sem client centralizado. | M |

### 3.3 MEDIUM — Manutenibilidade

| ID | Debt | Localização | Impacto | Esforço |
|----|------|-------------|---------|---------|
| **TD-11** | **Sem validation de file size/page count** | `routers/upload.py` | PDFs grandes podem crashar pipeline ou estourar memória. | S |
| **TD-12** | **CORS hardcoded localhost:5173** | `main.py` | Sem suporte para deploy em domínio diferente. | XS |
| **TD-13** | **Circular dep mitigation via lazy imports** | `stores/session.ts` | Funciona mas é frágil. Dependency injection seria mais robusto. | M |
| **TD-14** | **Large component files** | `AnalyzingPage.vue` (40KB), `analyze.py` (750 lines) | Dificulta manutenção e code review. | M |
| **TD-15** | **Editor state fragmentation** | `editorStore` + `inspectorStore` + `layout.layoutStates` | UI state disperso em 3+ stores. | M |
| **TD-16** | **31 helper files in stages/** | `services/stages/*.py` | Muitos helpers do pipeline antigo. Validar quais são dead code. | S |
| **TD-17** | **Sem E2E testing** | `package.json` — Playwright referenciado mas não instalado | Sem validação end-to-end automatizada. | L |

### 3.4 LOW — Melhorias futuras

| ID | Debt | Localização | Impacto | Esforço |
|----|------|-------------|---------|---------|
| **TD-18** | **Sem health check sofisticado** | `main.py` — `/api/health` retorna OK | Não verifica DB, storage, spaCy model, OpenRouter key. | S |
| **TD-19** | **Test co-location inconsistente** | Frontend spec files | Mistura de co-located e `__tests__/` directory. | XS |
| **TD-20** | **Vendor directory** | `backend/vendor/` | OpenAI/httpx vendored. Pode causar drift de versão. | S |

---

## 4. Architecture Strengths (Preservar)

| # | Strength | Evidência |
|---|----------|-----------|
| 1 | **Contract-driven pipeline** | Cada stage tem input/output explícito (Section 3.x) |
| 2 | **StorageGateway abstraction** | Clean separation local vs cloud, factory pattern |
| 3 | **Atomic Design frontend** | 126 componentes bem organizados em atoms→organisms |
| 4 | **Comprehensive testing** | 34 backend + 106 frontend test files |
| 5 | **SSE replay buffer** | Late-connecting clients recebem eventos passados |
| 6 | **Progressive NLP** | 3-layer fallback: algorithmic → regex → spaCy NER |
| 7 | **Lazy loading everywhere** | spaCy, Supabase, Monaco — loaded on demand |
| 8 | **Type safety** | TypeScript strict mode + Pydantic models |
| 9 | **Multi-doc support** | Pool-unique clustering, variation matrix, diff viewer |
| 10 | **Store hub pattern** | `session.loadFromPipelineResult()` hydrates all 14 stores |

---

## 5. Architecture Gaps (vs Production Readiness)

### 5.1 Infrastructure Gaps

| Gap | Current State | Required State (MVP) | Solução |
|-----|---------------|---------------------|---------|
| **Authentication** | Nenhuma | Supabase Auth + JWT | Supabase Auth (já no stack) |
| **Authorization** | Nenhuma | API key ou JWT middleware | FastAPI middleware + Supabase JWT verify |
| ~~**Containerization**~~ | ~~Nenhuma~~ | ~~Docker~~ | **ELIMINADO** — Railway build nativo |
| **CI/CD** | Nenhuma | Auto-deploy + testes em PR | Vercel + Railway auto-deploy. GitHub Actions só para `pytest`. |
| **Monitoring** | Console.log | Railway logs + health check | Railway dashboard (built-in) |
| ~~**Error tracking**~~ | ~~Nenhum~~ | ~~Sentry~~ | **DEFERRED** — Railway logs suficiente para MVP |
| **Job persistence** | In-memory dict | Redis | Railway Redis addon (grátis) |

### 5.2 Security Gaps

| Gap | Risk | Mitigation |
|-----|------|------------|
| **Open API** | Qualquer pessoa acessa | Auth middleware + API keys |
| **No input validation (files)** | Memory DoS | File size limits + page count validation |
| **No rate limiting** | Cost abuse (LLM) | Rate limiter per-user/per-IP |
| **CORS wildcard risk** | XSS se configurado errado | Dynamic CORS from env |
| **No HTTPS enforcement** | MITM | TLS termination no proxy |

### 5.3 Scalability Gaps

| Gap | Current Limit | MVP Solution | Post-MVP |
|-----|--------------|-------------|----------|
| **Single process** | ~10 concurrent jobs | Suficiente para MVP | Worker pool (Celery/ARQ) |
| **In-memory state** | Lost on restart | Railway Redis addon | Redis cluster |
| **No caching** | Repeated LLM calls | **DEFERRED** | Result cache per fingerprint |
| **Synchronous cleanup** | Blocks request thread | **DEFERRED** | Background task scheduler |

---

## 6. Dependency Analysis

### 6.1 Backend Dependencies — Risk Assessment

| Dependency | Version | Risk | Notes |
|------------|---------|------|-------|
| PyMuPDF | >=1.24.0 | **Medium** | GPL licensed. Verificar compatibilidade com licença do projeto. |
| openai SDK | >=1.0.0 | Low | Stable, via OpenRouter proxy |
| spaCy | >=3.7.0 | Low | Estável. Model pt_core_news_lg requer download separado (~50MB) |
| scikit-learn | >=1.4.0 | Low | Estável, usado para clustering |
| pdfplumber | >=0.10.0 | Low | Wrapper sobre pdfminer |
| networkx | >=3.0 | Low | Graph clustering Stage 1 |

### 6.2 Frontend Dependencies — Risk Assessment

| Dependency | Version | Risk | Notes |
|------------|---------|------|-------|
| Vue | 3.5.25 | Low | LTS, stable |
| monaco-editor | 0.55.1 | **Medium** | Heavy bundle (~2MB). Manual chunk split mitiga. |
| pdfjs-dist | 5.5.207 | Low | Mozilla maintained |
| chart.js | 4.5.1 | Low | Stable |
| Vite | 7.3.1 | Low | Fast builds |

---

## 7. Data Flow Architecture

### 7.1 Upload → Pipeline → Editor Flow

```
User uploads PDF(s) + XSD + Data
         │
         ▼
   POST /api/analyze
         │
         ├─→ Creates job_id (UUID)
         ├─→ Stores files via StorageGateway
         ├─→ Spawns asyncio.Task (pipeline)
         │
         ▼
   SSE /api/analyze/{job_id}/progress
         │
         ├─→ Stage 1: clusters[], _raw_text_blocks
         ├─→ Stage 2: enriched_documents[]
         ├─→ Stage 3: document_trees[]
         ├─→ Stage 4: field_mappings[]
         ├─→ Stage 5: result_json (completo)
         │
         ▼
   GET /api/analyze/{job_id}/result
         │
         ▼
   Frontend: session.loadFromPipelineResult()
         │
         ├─→ templateStore (document tree)
         ├─→ mapping (field bindings)
         ├─→ generation (HTML/CSS/JS)
         ├─→ multiDoc (variation matrix)
         ├─→ confidence, coverage, layout, ...
         │
         ▼
   TemplateEditor (3-pane visual editor)
```

### 7.2 LLM Usage Map

| Stage | Model | Calls/Job | Cost/Call | Purpose |
|-------|-------|-----------|-----------|---------|
| 1 | Gemini Flash | 1 | ~$0.003 | Cluster validation |
| 3 | GPT-4o Vision | ~6 | ~$0.025 | Visual region detection |
| 4 | GPT-4o | 1/layout | ~$0.010 | Ambiguity resolution |
| AutoFix | GPT-4o | 1-5 | ~$0.010 | Field correction |
| **Total** | — | **~10** | **~$0.20** | — |

---

## 8. Recommended Remediation Priorities (MVP-Accelerated)

> **Estratégia revisada:** Com Vercel + Railway + Supabase Auth, os blockers originais (4 waves, ~30 stories) foram reduzidos para **3 waves, ~10 stories**. Docker e CI/CD complexo eliminados.

### Wave 1 — Deploy Infrastructure (1-2 stories)

| Priority | Item | Tech Debt IDs | Esforço | Detalhes |
|----------|------|---------------|---------|----------|
| P0 | **Vercel deploy (frontend)** | — | XS | `vercel init` + env vars. Pronto em minutos. |
| P0 | **Railway deploy (backend)** | TD-04 ~~eliminado~~ | XS | `Procfile` + `requirements.txt` + env vars + spaCy model download no build. |
| P0 | **CORS dinâmico** | TD-06, TD-12 | XS | `ALLOWED_ORIGINS` env var em vez de hardcoded localhost. |

**Procfile (1 linha):**
```
web: python -m spacy download pt_core_news_lg && uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

### Wave 2 — Auth + Job Persistence (3-4 stories)

| Priority | Item | Tech Debt IDs | Esforço | Detalhes |
|----------|------|---------------|---------|----------|
| P0 | **Supabase Auth middleware** | TD-02 | S | FastAPI dependency que valida JWT do Supabase. ~100 lines. |
| P0 | **Redis job persistence** | TD-01 | S | Railway Redis addon. Migrar `_pipeline_jobs` dict → Redis. ~200 lines. |
| P1 | **Rate limiting** | TD-07 | XS | `slowapi` middleware. 10 req/min por IP. ~30 lines. |
| P1 | **Input validation** | TD-11 | XS | File size limit (50MB) + page count limit (500). ~20 lines. |

### Wave 3 — Code Cleanup (2-3 stories)

| Priority | Item | Tech Debt IDs | Esforço | Detalhes |
|----------|------|---------------|---------|----------|
| P1 | **Remove old 28-stage pipeline** | TD-05 | S | Delete StageRegistry + dead code em `models/pipeline.py`. |
| P1 | **Validate/remove dead stage helpers** | TD-16 | S | Auditar 31 helper files em `stages/`. |
| P2 | **GitHub Actions básico** | TD-03 | XS | Workflow simples: `pytest` on PR. Vercel/Railway já fazem deploy. |

### Deferred (Post-MVP)

| Item | Tech Debt IDs | Razão do Defer |
|------|---------------|----------------|
| Global error boundary | TD-08 | Railway logs suficiente para MVP |
| Centralize API client | TD-10 | Funciona, não quebra |
| Component decomposition | TD-14 | Funciona, não quebra |
| E2E testing (Playwright) | TD-17 | Manual testing aceitável para MVP |
| Background job scheduler | TD-09 | Railway Redis TTL resolve |
| Sentry/monitoring | — | Railway dashboard built-in |
| Docker/containerização | TD-04 | Railway não precisa |
| Editor state consolidation | TD-15 | Funciona, não quebra |

---

## 9. Architecture Decision Records (ADRs)

### ADR-001: Pipeline 28→5 Redesign
- **Status:** Implemented (Epic 13)
- **Decision:** Consolidar 28 stages em 5 stages substanciais
- **Rationale:** 13x faster, 25x cheaper, ~95% accuracy
- **Consequence:** Old pipeline code ainda presente (TD-05)

### ADR-002: StorageGateway Abstraction
- **Status:** Implemented (Epic 13.1-13.2)
- **Decision:** Abstract storage behind gateway interface
- **Rationale:** Supabase em prod, local em dev, sem code change
- **Consequence:** Dual implementation required para cada feature

### ADR-003: In-Memory Job State
- **Status:** Active (precisa migrar)
- **Decision:** Jobs em dict Python in-memory
- **Rationale:** Simplicidade durante desenvolvimento
- **Consequence:** **Bloqueio para produção** (TD-01)

### ADR-004: Atomic Design Frontend
- **Status:** Implemented
- **Decision:** atoms→molecules→organisms→pages
- **Rationale:** Escalabilidade e reuso de componentes
- **Consequence:** 126 componentes bem organizados

### ADR-005: SSE para Progress Tracking
- **Status:** Implemented
- **Decision:** Server-Sent Events com replay buffer
- **Rationale:** Unidirecional, reconexão automática, leve
- **Consequence:** Late-connecting clients suportados

### ADR-006: Deploy Stack — Vercel + Railway + Supabase
- **Status:** Decided (2026-03-23)
- **Decision:** Frontend no Vercel, backend no Railway, DB/Storage/Auth no Supabase
- **Rationale:** Menor overhead para MVP. Railway faz build nativo de Python (sem Docker). Vercel + Railway fornecem auto-deploy on push. Supabase Auth já está no stack (só wiring). Redis addon grátis no Railway resolve job persistence.
- **Alternatives rejected:**
  - Docker/docker-compose: Overhead desnecessário — Railway não precisa
  - Vercel Serverless para backend: Incompatível com dependências pesadas (spaCy, PyMuPDF)
  - AWS/GCP: Over-engineering para MVP
- **Consequence:** TD-04 eliminado. TD-03 reduzido. Epic de deploy cai de ~30 stories para ~10.

---

## 10. Next Steps (Brownfield Discovery)

| Phase | Agent | Deliverable | Status |
|-------|-------|-------------|--------|
| **1. System Architecture** | @architect | `brownfield-system-architecture.md` | **COMPLETE** |
| 2. Database Audit | @data-engineer | `SCHEMA.md` + `DB-AUDIT.md` | PENDING |
| 3. Frontend Spec | @ux-design-expert | `frontend-spec.md` | PENDING |
| 4. Tech Debt Draft | @architect | `technical-debt-DRAFT.md` | PENDING |
| 5. DB Review | @data-engineer | `db-specialist-review.md` | PENDING |
| 6. UX Review | @ux-design-expert | `ux-specialist-review.md` | PENDING |
| 7. QA Gate | @qa | `qa-review.md` | PENDING |
| 8. Final Assessment | @architect | `technical-debt-assessment.md` | PENDING |
| 9. Executive Report | @analyst | `TECHNICAL-DEBT-REPORT.md` | PENDING |
| 10. Epic Creation | @pm | Epic + stories | PENDING |

---

*— Aria, arquitetando o futuro 🏗️*
