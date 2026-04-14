# System Architecture Analysis — Migrador Planet

**Date:** 2026-04-09
**Status:** `current` — visão geral do sistema (stack, componentes, integrações)
**Dono:** `@architect` — atualiza quando stack ou deploy mudam
**Fonte:** código em `backend/` + `frontend/` + configurações de deploy (Railway/Vercel)
**Atualizar quando:** mudança de stack, novo serviço externo, mudança de deploy
**Última validação:** 2026-04-09 (Brownfield Discovery Phase 1)

---

## 1. Executive Summary

Migrador Planet is a PDF-to-HTML template migration tool. The backend is a Python 3.11 FastAPI application with a 5-stage pipeline that uses PDF parsing (PyMuPDF, pdfplumber), NLP (spaCy), and Vision AI (GPT-4o via OpenRouter) to analyze PDF documents and generate editable HTML templates. The frontend is a Vue 3 + TypeScript SPA with a visual template editor (canvas, structure tree, inspector panels, code editor with Monaco).

The codebase is **mature and well-structured** overall, having gone through 39+ epics of iterative development. TypeScript strict mode is enabled, auth is properly implemented, and the pipeline architecture is clean. However, the audit reveals **22 technical debts** across infrastructure, testing, security, and code quality dimensions.

---

## 2. Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Runtime** | Python | 3.11.11 |
| **Backend Framework** | FastAPI | >= 0.110.0 |
| **ASGI Server** | Uvicorn | >= 0.27.0 |
| **Frontend Framework** | Vue 3 | ^3.5.25 |
| **State Management** | Pinia | ^3.0.4 |
| **Build Tool** | Vite | ^7.3.1 |
| **TypeScript** | TS | ~5.9.3 |
| **CSS Framework** | Tailwind CSS | ^4.2.1 |
| **Test (Frontend)** | Vitest | ^4.1.0 |
| **Test (Backend)** | pytest + pytest-asyncio | >= 0.23.0 |
| **Database** | Supabase (Postgres) | SaaS |
| **Cache/Persistence** | Redis | >= 5.0.0 |
| **PDF Parsing** | PyMuPDF + pdfplumber | >= 1.24.0 / >= 0.10.0 |
| **NLP** | spaCy | >= 3.8.0, < 3.9.0 |
| **Vision AI** | GPT-4o via OpenRouter | OpenAI SDK >= 1.0.0 |
| **Code Editor** | Monaco Editor | ^0.55.1 |
| **PDF Viewer** | pdfjs-dist | ^5.5.207 |
| **Deployment (Backend)** | Railway (Nixpacks) | - |
| **Deployment (Frontend)** | Vercel | - |

### Key Observations
- Modern stack with up-to-date versions (Vite 7, Vue 3.5, TS 5.9, Tailwind 4)
- TypeScript **strict mode enabled** with `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`
- Dual PDF parsing libraries (PyMuPDF for rendering/images, pdfplumber for text extraction) -- justified by different strengths
- Vision AI used optionally for structural analysis (fallback when unavailable)

---

## 3. Architecture Overview

### 3.1 Backend Architecture

```
backend/
  main.py                  # FastAPI app, CORS, rate limiting, lifespan
  middleware/auth.py        # Supabase JWT (JWKS ES256/RS256)
  routers/                  # 8 route modules (analyze, upload, preview, etc.)
  services/
    pipeline_orchestrator_v2.py   # 5-stage pipeline coordinator
    stages/                       # Stage 1-5 implementations (8,525 LOC)
    storage/                      # ABC gateway + local/supabase impls
    job_store.py                  # In-memory + Redis persistence
    openrouter_client.py          # GPT-4o Vision with retry
  models/                   # Dataclasses (LayoutType, TextBlock, etc.)
  utils/validation.py       # UUID + path traversal validation
  vendor/                   # Vendored OpenAI SDK (32MB)
  tests/                    # 30 test files (15,863 LOC)
```

**Pipeline Architecture (5 Stages):**
1. Layout Clustering (1,403 LOC) -- scikit-learn clustering + pHash similarity
2. Deep Extraction (1,296 LOC) -- text blocks, tables, drawn elements
3. Structural Analysis (2,048 LOC) -- NER + GPT-4o Vision + hierarchy building
4. Field Mapping (1,238 LOC) -- XSD-to-PDF field matching
5. Template Generation (2,008 LOC) -- HTML/CSS generation from document tree

**Pattern:** SSE (Server-Sent Events) replay buffer for progress streaming. Events are stored in an append-only log and replayed to late-connecting clients.

### 3.2 Frontend Architecture

```
frontend/src/
  pages/          5 page components (Login, Home, Upload, Analyzing, TemplateEditor)
  organisms/     14 complex components (HTMLCanvas, SplitView, inspectors/)
  molecules/     50+ UI building blocks
  atoms/         15 primitive components
  composables/   20 composition functions (7,872 LOC)
  stores/        17 Pinia stores (6,573 LOC)
  services/       2 service modules (apiFetch, authService)
  types/          9 type definition files
  utils/          9 utility modules
  router/         1 route config with auth + session guards
  lib/            1 Supabase client singleton
  layouts/        1 EditorLayout
  templates/      1 FullWidthLayout
```

**Total:** 136 `.vue` files, 196 `.ts` files

**Component Architecture:** Atomic Design (atoms/molecules/organisms/pages) with some inconsistency (see SYS-008).

**State Management:** 17 Pinia stores covering session, template tree, code generation, field mapping, confidence, coverage, diff, multi-doc, and more. The session store acts as the central coordinator, dispatching pipeline results to all other stores.

### 3.3 Infrastructure

- **Backend Deployment:** Railway via Nixpacks (Python 3.11, `Procfile` + `nixpacks.toml`)
- **Frontend Deployment:** Vercel with API rewrites to Railway backend
- **Database:** Supabase Postgres with 4 migrations (jobs, clusters, templates, storage policies)
- **Cache:** Redis for job persistence (optional, falls back to in-memory)
- **CI/CD:** GitHub Actions with 3 jobs (backend tests, frontend tests+typecheck+build, Supabase migration validation)

---

## 4. Strengths

1. **Clean pipeline architecture** -- 5 well-defined stages with clear contracts, SSE progress streaming, service failure checkpoints with operator decisions
2. **TypeScript strict mode** -- Full strict config with unused variable checks, no fallthrough, erasable syntax only
3. **Good auth implementation** -- JWKS-based JWT validation (ES256/RS256), proper token refresh, auth guards on routes
4. **Storage abstraction** -- Clean ABC pattern with local/supabase implementations, no automatic fallback (fail-fast)
5. **Input validation** -- UUID v4 validation, path traversal prevention, file size limits, page count limits, template name sanitization
6. **Rate limiting** -- Per-endpoint configurable rate limits via slowapi
7. **Comprehensive test suite** -- 123 frontend spec files (23,464 LOC), 30 backend test files (15,863 LOC)
8. **Build optimization** -- Manual chunks for monaco, pdfjs, chartjs in Vite config
9. **Undo/redo system** -- JSON snapshot-based undo stack with configurable max depth
10. **SSE replay buffer** -- Late-connecting clients receive full event history with timed replay

---

## 5. Technical Debt Catalog

### SYS-001: Vendored Dependencies in Repository (32MB)
- **Severity:** HIGH
- **Impact:** Repository size, dependency management, security updates
- **Description:** The `backend/vendor/` directory contains vendored copies of openai, pydantic, httpx, and other packages (32MB). This was likely done to work around Railway deployment issues, but it means: (a) dependency updates require manual re-vendoring, (b) security patches are not automatically applied, (c) repository bloat. The `conftest.py` adds vendor to `sys.path` for tests.
- **Effort:** 4h -- Configure proper virtualenv/pip install in deployment, remove vendor dir, update `.gitignore`

### SYS-002: No Python Linter/Formatter Configuration
- **Severity:** HIGH
- **Impact:** Code quality, consistency, developer experience
- **Description:** No `pyproject.toml`, `ruff.toml`, `mypy.ini`, `.flake8`, or any Python linting/formatting config exists. Backend code has no automated quality enforcement. Only 6 `# noqa` comments exist, suggesting linters have never been configured. No type checking (mypy/pyright) is configured for the backend despite heavy use of type hints.
- **Effort:** 4h -- Add ruff + mypy config, fix initial lint errors, add to CI

### SYS-003: No ESLint/Prettier Configuration (Frontend)
- **Severity:** HIGH
- **Impact:** Code quality, consistency
- **Description:** No ESLint or Prettier configuration exists at the project level. Vue-tsc (type checking) is the only quality gate. No auto-formatting, no import ordering, no Vue-specific linting rules. The `package.json` has no lint script beyond `vue-tsc --noEmit`.
- **Effort:** 4h -- Add eslint + prettier config with Vue plugin, fix initial errors, add to CI

### SYS-004: Dual Job State Management (In-Memory + Store)
- **Severity:** HIGH
- **Impact:** Data consistency, reliability
- **Description:** `analyze.py` maintains its own `_pipeline_jobs` dict alongside the `job_store` module. The `_pipeline_jobs` dict is the primary source of truth during pipeline execution, while `job_store` (Redis) is only updated at the end. This creates a split-brain scenario: if the server crashes mid-pipeline, Redis has stale state. The `recover_running_jobs()` function exists but is not called in the lifespan handler (only `_cleanup_orphaned_dirs` is called). Additionally, `_JOB_TTL_SECONDS` is hardcoded in `analyze.py` (3600) separately from `job_store.py` (also 3600 but configurable via env).
- **Effort:** 8h -- Unify job state into a single source, call `recover_running_jobs` in lifespan, remove duplicate TTL constant

### SYS-005: `_pipeline_jobs` Dict Duplicates `TMP_BASE` Constant
- **Severity:** MEDIUM
- **Impact:** Maintainability
- **Description:** `TMP_BASE` is defined independently in `analyze.py`, `upload.py`, and `validation.py` -- all reading from `JOBS_DIR` env var with the same default. Any change to the env var name or default requires updating 3 files.
- **Effort:** 2h -- Extract to a shared config module

### SYS-006: Heavyweight Session Store (God Object Pattern)
- **Severity:** MEDIUM
- **Impact:** Maintainability, testability
- **Description:** `session.ts` (534 LOC) acts as a coordinator that imports and dispatches to 10+ other stores in `loadFromPipelineResult()`. This method is ~150 lines and contains business logic (tree normalization, table cell flag propagation, binding reconciliation, test data population). It also duplicates the `applyTableCellFlags` logic inline. This is the classic "God Object" anti-pattern where one module knows about everything.
- **Effort:** 8h -- Extract pipeline result processing into a dedicated service/composable, use a mediator pattern

### SYS-007: Dead Code and Scaffolding Remnants
- **Severity:** LOW
- **Impact:** Code cleanliness
- **Description:** Several dead code items remain: (a) `HelloWorld.vue` -- Vite scaffolding component, never used; (b) `backend/_deprecated/` directory with `jobs.py` and `progress.py` (223 LOC); (c) `vue.svg` in assets (Vite default); (d) `@faker-js/faker` listed as a production dependency but not imported anywhere in `src/`.
- **Effort:** 1h -- Delete dead files, move faker to devDependencies

### SYS-008: Inconsistent Component Organization
- **Severity:** MEDIUM
- **Impact:** Developer experience, discoverability
- **Description:** The project uses Atomic Design (atoms/molecules/organisms/pages) but with inconsistencies: (a) `components/` directory exists alongside atoms/molecules/organisms and contains `AnalyzingPage` sub-components plus `SnapLineOverlay` and `HelloWorld`; (b) `layouts/` and `templates/` directories serve similar purposes; (c) No clear guidelines for what goes in `components/` vs the atomic hierarchy.
- **Effort:** 4h -- Move components to correct atomic level, document guidelines

### SYS-009: `console.log/warn/error` in Production Code
- **Severity:** LOW
- **Impact:** Production observability, noise in browser console
- **Description:** 10 `console.*` calls found across 6 production files (3 .vue files, 3 .ts files). No structured logging or log-level filtering on the frontend. The backend uses Python `logging` correctly.
- **Effort:** 2h -- Replace with a structured logger utility, add log level control

### SYS-010: `any` Type Usage in TypeScript
- **Severity:** MEDIUM
- **Impact:** Type safety
- **Description:** 80 occurrences of `any` across 28 files despite strict mode being enabled. Many are in test files (acceptable) but some are in production code (`session.ts`, `mapping.ts`, `generation.ts`, `autoFixStore.ts`, `useProject.ts`, `useFileSystem.ts`, `usePdfRenderer.ts`, `usePreExportValidation.ts`). Strict mode catches `noUnusedLocals` but does not enforce `noImplicitAny` for `Record<string, any>` patterns.
- **Effort:** 6h -- Replace `any` with proper types or `unknown` in production files

### SYS-011: Large Stage Files Without Decomposition
- **Severity:** MEDIUM
- **Impact:** Maintainability, testability
- **Description:** Backend stage files are large monoliths: `stage3_structural_analysis.py` (2,048 LOC), `stage5_template_generation.py` (2,008 LOC), `stage1_layout_clustering.py` (1,403 LOC). Each contains multiple sub-steps that could be independent modules. This makes unit testing individual sub-steps difficult and increases cognitive load.
- **Effort:** 16h -- Extract sub-steps into separate modules per stage

### SYS-012: Missing Error Boundary / Global Error Handler (Frontend)
- **Severity:** MEDIUM
- **Impact:** User experience, error recovery
- **Description:** No Vue error boundary component or `app.config.errorHandler` is configured in `main.ts`. Unhandled errors in components will show a blank screen. The `app.mount('#app')` has no error handling wrapper. No Sentry or error tracking integration is configured (SENTRY_DSN exists in .env.example but is not used).
- **Effort:** 4h -- Add Vue error handler, error boundary component, optional Sentry integration

### SYS-013: No Pre-Commit Hooks
- **Severity:** MEDIUM
- **Impact:** Code quality enforcement
- **Description:** No `.husky/`, `.pre-commit-config.yaml`, or any git hooks configuration exists. Developers can commit without running type checks, linters, or tests. The CI pipeline catches issues but only after push.
- **Effort:** 2h -- Add husky + lint-staged for frontend, pre-commit for backend

### SYS-014: `Dict[str, Any]` Pervasive in Pipeline (Untyped Context)
- **Severity:** HIGH
- **Impact:** Type safety, maintainability, debugging
- **Description:** The pipeline orchestrator passes a `Dict[str, Any]` context between all 5 stages. This is essentially an untyped bag where stages add and read keys by string convention. 123 occurrences of `Dict[str, Any]` across 20 backend files. Stage contracts are documented in markdown but not enforced by the type system. A typo in a context key (`_raw_text_blocks` vs `raw_text_blocks`) would only be caught at runtime.
- **Effort:** 12h -- Define TypedDict or dataclass for pipeline context, enforce at stage boundaries

### SYS-015: Backend Missing CORS CSP Headers
- **Severity:** MEDIUM
- **Impact:** Security (OWASP)
- **Description:** CORS is configured but overly permissive (`allow_methods=["*"]`, `allow_headers=["*"]`). No Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, or Strict-Transport-Security headers are set. The API serves PDF files (`FileResponse`) without Content-Disposition headers. These are OWASP security header best practices.
- **Effort:** 4h -- Add security headers middleware, restrict CORS methods/headers to actual needs

### SYS-016: Supabase Project Reference Hardcoded in CI
- **Severity:** MEDIUM
- **Impact:** Portability, security
- **Description:** The CI workflow `ci.yml` hardcodes the Supabase project reference (`xrmlhuytgebovrgtzypl`) in the `supabase link` command. This should be a GitHub Actions secret or environment variable.
- **Effort:** 1h -- Move to GitHub Actions variable/secret

### SYS-017: No Backend Health Check Beyond `/api/health`
- **Severity:** LOW
- **Impact:** Observability, deployment reliability
- **Description:** The health endpoint returns a static `{"status": "ok"}` without checking Redis connectivity, Supabase connectivity, or disk space availability. Railway and load balancers need meaningful health checks to route traffic correctly.
- **Effort:** 4h -- Add deep health check with Redis ping, Supabase ping, disk space check

### SYS-018: spaCy Model Mismatch
- **Severity:** MEDIUM
- **Impact:** NLP accuracy
- **Description:** `requirements.txt` installs `pt_core_news_sm` (small model) but `stage3_structural_analysis.py` attempts to load `pt_core_news_lg` (large model). The code has a fallback chain (`lg` -> `sm` -> None) but the large model is never installed. This means NER classification always runs on the small model or fails silently.
- **Effort:** 1h -- Either install `lg` model or update code to load `sm` directly

### SYS-019: No API Versioning
- **Severity:** LOW
- **Impact:** API evolution, backward compatibility
- **Description:** All API routes are under `/api/` with no version prefix. Breaking changes to the API contract would require frontend and backend to be deployed simultaneously. No OpenAPI schema export is configured despite FastAPI's built-in support.
- **Effort:** 4h -- Add `/api/v1/` prefix, enable OpenAPI docs endpoint

### SYS-020: Missing Integration/E2E Test Coverage
- **Severity:** MEDIUM
- **Impact:** Regression prevention
- **Description:** While unit test coverage is strong (123 frontend specs, 30 backend test files), there are gaps: (a) No end-to-end browser tests (Playwright/Cypress); (b) `test_pipeline_benchmark.py` is excluded from CI; (c) No frontend store integration tests that verify the full `loadFromPipelineResult` flow with real pipeline output; (d) Auth service tests exist but mock everything.
- **Effort:** 16h -- Add Playwright E2E suite, add pipeline integration tests

### SYS-021: `@faker-js/faker` as Production Dependency
- **Severity:** LOW
- **Impact:** Bundle size
- **Description:** `@faker-js/faker` (^10.3.0) is listed under `dependencies` instead of `devDependencies` in `frontend/package.json`. This is a large library (several MB) that should only be used in tests/development. Since Vite tree-shakes unused imports, this may not affect the production bundle, but it increases `npm install` time and signals incorrect dependency classification.
- **Effort:** 0.5h -- Move to devDependencies

### SYS-022: Undo/Redo Uses Full JSON Serialization
- **Severity:** MEDIUM
- **Impact:** Performance, memory
- **Description:** `templateStore.ts` implements undo/redo by `JSON.stringify`-ing the entire document tree on every mutation (every drag, resize, property change). For large documents with many nodes, this creates significant GC pressure. The max stack size is 20 snapshots, but each snapshot could be several KB for complex documents. A structural sharing or diff-based approach would be more efficient.
- **Effort:** 8h -- Implement command pattern or structural sharing for undo stack

---

## 6. Architecture Diagrams

### 6.1 Request Flow

```
Browser (Vue 3 SPA)
  |
  | HTTPS (Vercel rewrites /api/* to Railway)
  v
FastAPI (Railway)
  |-- POST /api/upload    --> StorageGateway.upload_pdf()
  |-- POST /api/analyze   --> Background Task: run_pipeline_v2()
  |     |-- SSE /api/analyze/{id}/progress
  |     |-- Stage 1: Layout Clustering (scikit-learn)
  |     |-- Stage 2: Deep Extraction (PyMuPDF + pdfplumber)
  |     |-- Stage 3: Structural Analysis (spaCy + GPT-4o Vision)
  |     |-- Stage 4: Field Mapping (XSD matching)
  |     |-- Stage 5: Template Generation (HTML/CSS)
  |-- GET /api/analyze/{id}/result --> Pipeline JSON result
  |-- POST /api/auto-fix   --> AI-powered auto-fix suggestions
  |-- POST /api/export     --> ZIP with HTML template
  |
  v
Supabase (Postgres + Storage)     Redis (Job persistence)
```

### 6.2 Frontend State Flow

```
PipelineResult (from API)
  |
  v
SessionStore.loadFromPipelineResult()
  |-- LayoutStore (layout types, active layout)
  |-- TemplateStore (document tree, flat node map)
  |-- MappingStore (field mappings, XSD bindings)
  |-- ConfidenceStore (per-layout confidence scores)
  |-- CoverageStore (field coverage data)
  |-- GenerationStore (template draft HTML/CSS/JS)
  |-- InspectorStore (inspector panel state)
  |-- MultiDocStore (multi-PDF support)
  |-- TestDataStore (sample data for preview)
```

---

## 7. Security Assessment

| Check | Status | Notes |
|-------|--------|-------|
| Authentication | PASS | Supabase JWKS JWT validation (ES256/RS256) |
| Authorization | PARTIAL | Auth checks per-route but no role-based access control |
| Input Validation | PASS | UUID v4 validation, path traversal prevention, file size limits |
| Rate Limiting | PASS | Per-endpoint via slowapi |
| CORS | WARN | Overly permissive (`*` methods and headers) |
| Security Headers | FAIL | No CSP, HSTS, X-Frame-Options, X-Content-Type-Options |
| Secret Management | PASS | `.env` files gitignored, `.env.example` has no values |
| SQL Injection | N/A | No raw SQL (Supabase client handles parameterization) |
| XSS | PASS | Vue template auto-escaping, template_name sanitized |
| SSRF | LOW RISK | OpenRouter URL hardcoded, no user-controlled URLs |
| File Upload | PASS | Size limits, page count limits, PDF format validation |
| Path Traversal | PASS | UUID validation + resolve() check against TMP_BASE |

---

## 8. Performance Considerations

| Area | Status | Notes |
|------|--------|-------|
| Bundle Splitting | GOOD | Manual chunks for monaco, pdfjs, chartjs |
| Lazy Loading (Routes) | GOOD | All routes use dynamic `import()` |
| Lazy Loading (Stores) | PARTIAL | Session store dynamically imports other stores, but some composables eagerly import |
| SSE Streaming | GOOD | Replay buffer prevents missed events |
| Image Optimization | WARN | Screenshots stored as PNG, no WebP conversion |
| Backend Concurrency | GOOD | asyncio-based pipeline, non-blocking I/O |
| Memory (Backend) | WARN | Full PDF bytes held in memory during processing |
| Memory (Frontend) | WARN | JSON.stringify undo stack on every mutation (SYS-022) |

---

## 9. Codebase Metrics

| Metric | Value |
|--------|-------|
| Backend Python LOC (services/) | ~10,763 |
| Backend Python LOC (routers/) | ~1,790 |
| Backend Python LOC (tests/) | ~15,863 |
| Frontend Vue LOC | ~30,036 |
| Frontend TS LOC (non-spec) | ~14,445 (est.) |
| Frontend Spec LOC | ~23,464 |
| Total Test Files | 153 (123 frontend + 30 backend) |
| Pinia Stores | 17 |
| Composables | 20 |
| API Routes | 8 routers, ~15 endpoints |
| DB Migrations | 4 |
| Backend `# type: ignore` | Minimal |
| Frontend `any` usage | 80 occurrences (28 files) |

---

## 10. Debt Priority Matrix

| Priority | IDs | Rationale |
|----------|-----|-----------|
| **P0 (Critical)** | SYS-001, SYS-002, SYS-003, SYS-014 | Vendored deps (security risk), no linting (quality drift), untyped pipeline context (runtime errors) |
| **P1 (High)** | SYS-004, SYS-006, SYS-013, SYS-015 | Dual job state (data loss risk), god object (maintainability), no pre-commit (quality gate), security headers (OWASP) |
| **P2 (Medium)** | SYS-005, SYS-008, SYS-010, SYS-011, SYS-012, SYS-016, SYS-018, SYS-020, SYS-022 | Maintainability and reliability improvements |
| **P3 (Low)** | SYS-007, SYS-009, SYS-017, SYS-019, SYS-021 | Cleanup, observability, nice-to-have |

**Total estimated effort:** ~109 hours

---

## 11. Recommendations

### Immediate (Sprint 1)
1. **SYS-002 + SYS-003 + SYS-013:** Add ruff + mypy (backend) and eslint + prettier (frontend) with pre-commit hooks. This is the single highest-ROI improvement -- it prevents all future quality drift.
2. **SYS-001:** Remove vendored dependencies, configure proper pip install in Railway deployment.
3. **SYS-018:** Fix spaCy model reference (sm vs lg).

### Short-term (Sprint 2-3)
4. **SYS-014:** Define TypedDict for pipeline context -- this will prevent runtime key errors.
5. **SYS-004:** Unify job state management, add `recover_running_jobs` to lifespan.
6. **SYS-015:** Add security headers middleware.
7. **SYS-012:** Add Vue error boundary and error handler.

### Medium-term (Sprint 4+)
8. **SYS-006:** Refactor session store coordinator pattern.
9. **SYS-011:** Decompose large stage files.
10. **SYS-020:** Add Playwright E2E tests.
11. **SYS-022:** Optimize undo/redo with command pattern.
