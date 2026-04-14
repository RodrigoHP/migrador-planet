# Frontend Specification & UX Audit

**Project:** migrador-planet (PDF-to-HTML Template Migration Tool)
**Date:** 2026-04-09
**Status:** `current` — spec canônica do frontend (pós-Epic 40/41)
**Dono:** `@ux-design-expert` — atualiza quando nova feature de UI for entregue
**Fonte:** `frontend/src/` — auditoria de componentes Vue + stores Pinia + composables
**Atualizar quando:** nova feature de UI entregue ou componente arquitetural alterado
**Última validação:** 2026-04-09 (Brownfield Discovery Phase 3)
**Auditor:** @ux-design-expert (Uma) - Brownfield Discovery Phase 3
**Framework:** Vue 3.5 + Vite 7.3 + TypeScript 5.9 + Pinia 3 + Tailwind CSS 4.2

---

## 1. Executive Summary

The frontend is a well-structured, editor-style SPA with ~136 Vue components, 20+ Pinia stores, 18 composables, and 1,794 passing tests across 123 test files. The architecture follows atomic design (atoms/molecules/organisms/templates/pages) with consistent BEM naming for scoped styles. Key strengths include high test coverage, good state management separation, proper lazy loading, and solid accessibility foundations. Primary concerns are oversized components (7 files >600 LOC), a monolithic session store (534 LOC), no E2E tests, no responsive/mobile support, no dark mode, and 3 npm vulnerabilities.

---

## 2. Component Architecture

### 2.1 Organization Pattern: Atomic Design

The project follows atomic design consistently:

| Layer | Path | Count | Purpose |
|-------|------|-------|---------|
| **Atoms** | `src/atoms/` | 16 | Button, ProgressBar, ToggleButton, ColorPicker, badges |
| **Molecules** | `src/molecules/` | 55 | InspectorField, BindingEditor, ContextMenu, BorderEditor |
| **Organisms** | `src/organisms/` | 30+ | HTMLCanvas, InspectorPanel, TopToolbar, StructureTree |
| **Templates** | `src/templates/` | 1 | FullWidthLayout |
| **Pages** | `src/pages/` | 6 | HomePage, UploadPage, AnalyzingPage, TemplateEditor, LoginPage, AuthCallback |
| **Layouts** | `src/layouts/` | 1 | EditorLayout (grid-based 3-panel editor) |

**Verdict:** Good adherence to atomic design. Barrel exports (`index.ts`) exist for atoms, molecules, organisms, and templates.

### 2.2 Component Size

Files exceeding 400 LOC (candidates for decomposition):

| File | LOC | Concern |
|------|-----|---------|
| `pages/AnalyzingPage.vue` | 1,195 | Manages pipeline states, stepper, banners, checkpoint, cancellation |
| `organisms/HTMLCanvas.vue` | 913 | Canvas rendering, zoom, scroll, drag/drop, iframe management, keyboard |
| `organisms/TestDataPanel.vue` | 757 | Dataset CRUD, import/export, validation, preview |
| `pages/UploadPage.vue` | 695 | Dropzones, file validation, multi-PDF, XSD, data file handling |
| `organisms/DiffViewer.vue` | 688 | Side-by-side diff with scroll sync, highlighting |
| `organisms/BibliotecasModal.vue` | 654 | Component library CRUD, import/export, preview |
| `organisms/SyncView.vue` | 638 | PDF/HTML sync scroll, selection overlay, zoom |
| `organisms/AutoFixPanel.vue` | 637 | Auto-fix list, preview, apply/revert logic |
| `organisms/TopToolbar.vue` | 626 | 10+ toggle buttons, badges, popovers, export trigger |
| `organisms/inspectors/ElementInspector.vue` | 620 | Position, dimension, typography, border, binding, conditional styles |
| `organisms/FieldNavigator.vue` | 618 | Field list, status filtering, drag, navigation |
| `organisms/StructureTree.vue` | 589 | Tree navigation, multi-select, context menu, keyboard |

### 2.3 Props Drilling

Props drilling is minimal. The project correctly uses Pinia stores for cross-component state. Components access stores directly rather than passing data through deep prop chains. Inspector sub-components (`InspectorField`, `InspectorInput`, `InspectorSelect`) receive props from their direct parent inspector, which is appropriate.

### 2.4 Reusability

**Good patterns:**
- `InspectorSection`, `InspectorField`, `InspectorInput`, `InspectorSelect`, `InspectorCheckbox` form a cohesive inspector primitive set
- `Button` atom with `variant` prop (primary/secondary)
- `ToggleButton` reused across TopToolbar
- `ProgressBar`, `ProgressLabel` reused in pipeline screens

**Duplication concern:**
- `ConfidenceBadge` exists as both an atom (`atoms/ConfidenceBadge.vue`) and a molecule (`molecules/ConfidenceBadge.vue`) with `ConfidenceBadgeMetric.vue` -- overlapping responsibilities

### 2.5 Naming Conventions

- **Files:** PascalCase for components (consistent)
- **Stores:** camelCase with `use*Store` convention (consistent)
- **Composables:** `use*.ts` pattern (consistent)
- **Types:** Separate type files per domain in `src/types/` (clean separation)
- **Tests:** Co-located `*.spec.ts` files (consistent)
- **CSS classes:** BEM-style (`block__element--modifier`) with scoped styles (consistent)

---

## 3. State Management

### 3.1 Pinia Store Inventory

| Store | LOC | Style | Dependencies |
|-------|-----|-------|-------------|
| `session.ts` | 534 | Options API | templateStore, mappingStore, confidenceStore, coverageStore, layoutStore, generationStore, inspectorStore, multiDocStore, testDataStore (all via dynamic import) |
| `templateStore.ts` | 613 | Composition API | generationStore |
| `codeStore.ts` | 541 | Composition API | templateStore, chartStore, generationStore |
| `generation.ts` | 410 | Options API | -- |
| `mapping.ts` | ~250 | Options API | templateStore |
| `layout.ts` | 214 | Options API | templateStore, confidenceStore, coverageStore, inspectorStore, editorStore, mappingStore |
| `editorStore.ts` | ~100 | Composition API | -- |
| `inspectorStore.ts` | 93 | Composition API | -- |
| `confidenceStore.ts` | ~80 | Composition API | layoutStore |
| `coverageStore.ts` | ~80 | Composition API | layoutStore, templateStore |
| `authStore.ts` | 48 | Options API | -- |
| `chartStore.ts` | ~60 | Composition API | -- |
| `diffStore.ts` | ~60 | Composition API | multiDocStore, templateStore, coverageStore |
| `autoFixStore.ts` | ~80 | Options API | templateStore |
| `multiDocStore.ts` | ~80 | Options API | templateStore |
| `testDataStore.ts` | 327 | Options API | -- |
| `testReportStore.ts` | ~60 | Options API | -- |

### 3.2 Store API Style Inconsistency

**Mixed API styles:** Some stores use Composition API (`defineStore('id', () => {...})`), others use Options API (`defineStore('id', { state, getters, actions })`). This is a consistency debt:
- Composition API: templateStore, codeStore, editorStore, inspectorStore, confidenceStore, coverageStore, chartStore, diffStore
- Options API: session, generation, mapping, layout, authStore, autoFixStore, multiDocStore, testDataStore, testReportStore

### 3.3 Store Dependency Graph

```
session.ts (orchestrator)
  --> templateStore, mappingStore, confidenceStore, coverageStore,
      layoutStore, generationStore, inspectorStore, multiDocStore, testDataStore

layout.ts (hub)
  --> templateStore, confidenceStore, coverageStore, inspectorStore, editorStore, mappingStore

codeStore.ts
  --> templateStore, chartStore, generationStore

diffStore.ts
  --> multiDocStore, templateStore, coverageStore

coverageStore.ts --> layoutStore, templateStore
confidenceStore.ts --> layoutStore
autoFixStore.ts --> templateStore
multiDocStore.ts --> templateStore
mapping.ts --> templateStore
```

**Risk:** `layout.ts` imports 6 other stores and is itself imported by `confidenceStore` and `coverageStore`, creating a shallow but wide coupling. The `session.ts` store uses dynamic `import()` to break circular dependencies, which is a smart workaround but makes the dependency graph harder to trace.

### 3.4 Reactivity Patterns

- **ref/computed usage:** Correct and consistent across Composition API stores
- **Watchers:** 36 `watch()` calls across 24 component files -- reasonable for an editor app
- **watchEffect:** Only 2 usages (in `ImageReplacePreview.vue`) -- minimal
- **Undo/Redo:** templateStore maintains undo/redo stacks via JSON snapshots (max 20). Uses `structuredClone`-compatible approach via JSON.stringify/parse.
- **Mutation tracking:** `mutationVersion` counter pattern (ADR-029) for canvas-relevant mutations -- clean reactive signal approach

---

## 4. Design System / Visual

### 4.1 CSS Approach

- **Primary:** Tailwind CSS 4.2 via `@tailwindcss/vite` plugin
- **Component styles:** BEM-named scoped CSS (`<style scoped>`) in 131 of 136 components
- **Global leaks:** Only 3 components use unscoped `<style>` (HTMLCanvas, MonacoTabsInner, SyncView) -- these likely need global styles for iframe/Monaco integration, which is acceptable
- **Hybrid approach:** HomePage uses Tailwind utility classes directly in templates; most other components use BEM scoped styles. This inconsistency is minor but notable.

### 4.2 Design Tokens

Defined in `src/assets/main.css` via `@theme`:
- **Colors:** primary-600/700, success-600, warning-500, error-600, neutral-50/100/200/500/700/800/900, blue-50/100/400/900
- **Typography:** Inter (sans), JetBrains Mono (mono)
- **Spacing:** Base unit 0.25rem (4px)

Duplicated in `tailwind.config.ts` (same values). This dual definition could drift.

### 4.3 Component Library

Custom components throughout. No third-party UI library (no Vuetify, PrimeVue, etc.). Icons from `lucide-vue-next` (declared in package.json). Some emoji icons used inline (ToggleButton icons, dropzone labels).

### 4.4 Responsive Design

**Not implemented.** Only 2 files contain `@media` queries:
- `EditorLayout.vue` (structural breakpoint)
- `StructureTreeNode.vue` (minor adjustment)

The editor is desktop-only by design (complex 3-panel layout with drag/drop, canvas, inspector). The HomePage has minimal responsive grid (`md:grid-cols-2`). Login/Upload pages are centered but not mobile-optimized.

### 4.5 Dark Mode

**Not supported.** No `dark:` variants, no color scheme toggles, no `prefers-color-scheme` media query. All colors are light-mode only.

---

## 5. UX Patterns

### 5.1 Loading States

- **Pipeline progress:** Full stepper component (`AnalyzingStepper`) with stage states, progress bar, sub-step descriptions, timing data
- **Initializing state:** Dedicated `InitializingState` component with shimmer effect
- **Button loading:** `Button` atom supports `:loading` prop
- **No skeleton screens** in editor panels (data loads via pipeline result, so content appears all at once)

### 5.2 Error Handling

- **Pipeline errors:** `ErrorCard` component with retry/dismiss actions, stage-specific error detail
- **Connection/Session loss:** Banner alerts with reconnect/back-to-upload actions
- **Store loading errors:** Each store loader in `session.ts:loadFromPipelineResult()` is wrapped in try/catch with user-facing error messages
- **File validation:** Size errors on upload, format validation
- **SVG sanitization:** Dedicated `svgSanitizer.ts` for safe inline SVG insertion
- **Template name sanitization:** HTML stripping, charset limiting (TD-38.2)

### 5.3 Empty States

- Empty field list: "Nenhum componente salvo." (BibliotecaComponentList)
- Empty datasets: handled in TestDataPanel
- Upload dropzones show hint text when no files selected

### 5.4 Feedback / Notifications

- **Toast:** `AppToast` component (fixed bottom-right, auto-dismiss after 4s, variants: success/warning/error/neutral, manual dismiss)
- **Confirmation:** Export validation modal (`ExportValidationModal`)
- **Service failure:** `ServiceFailureModal` for backend connection issues
- **No global notification store** -- toasts are managed via component-level refs and `defineExpose()`

### 5.5 Keyboard Navigation

- **Canvas keyboard:** `useCanvasKeyboard` composable handles Delete, Ctrl+Z/Y, Ctrl+C/V, arrow keys for element movement
- **Context menu:** Keyboard-accessible context menu with proper role/ARIA
- **Tab focus:** Components use `tabindex` where appropriate (canvas div has `tabindex="0"`)
- **No visible focus indicators defined** beyond browser defaults

### 5.6 Drag & Drop

- **File upload:** Dropzone-based drag with visual feedback (`.dropzone--drag`)
- **Field mapping:** Drag from FieldNavigator to canvas with dragover/dragleave/drop handlers
- **Element positioning:** Canvas selection overlay with 8-point resize handles and snap lines

---

## 6. Accessibility (a11y)

### 6.1 ARIA Attributes

- **261 `aria-*` usages** across 76 component files -- good foundation
- **121 `role=*` usages** across 52 files
- Common patterns: `role="alert"`, `role="list"`, `role="group"`, `aria-label`, `aria-current`, `aria-hidden`, `aria-live="polite"`
- Breadcrumb navigation uses `aria-label="Breadcrumb"` and `aria-current="page"`
- Toolbar groups use `role="group"` with `aria-label`

### 6.2 Semantic HTML

- Good use of `<header>`, `<main>`, `<aside>`, `<nav>`, `<section>`, `<footer>`
- EditorLayout uses proper grid areas with semantic tags
- Form inputs have associated labels (UploadPage)

### 6.3 Color Contrast

- Primary blue (#2563EB on white) passes WCAG AA for normal text
- Error red (#DC2626) passes WCAG AA
- Neutral-500 (#737373) on white may fail WCAG AA for small text (4.48:1 ratio, needs 4.5:1)
- **No programmatic contrast testing configured**

### 6.4 Focus Management

- `prefers-reduced-motion: reduce` handled globally in main.css (animations disabled)
- No custom focus ring styles defined -- relies on browser defaults
- No focus trap implementation for modals (BibliotecasModal, AmbiguousFieldModal, ExportValidationModal)
- Canvas `tabindex="0"` enables keyboard focus

---

## 7. Performance

### 7.1 Bundle Optimization

**Code splitting:** All routes use lazy loading (`() => import(...)`) in router:
- LoginPage, AuthCallback, HomePage, UploadPage, AnalyzingPage, TemplateEditor

**Manual chunks** in `vite.config.ts`:
- `monaco-editor` -> separate chunk
- `pdfjs-dist` -> separate chunk
- `chart.js` -> separate chunk

**Heavy dependencies:**
- `monaco-editor` (0.55.1) -- ~3MB compressed
- `pdfjs-dist` (5.5.207) -- ~1.5MB
- `chart.js` (4.5.1) -- ~200KB
- `jszip` (3.10.1) -- ~100KB

### 7.2 Render Performance

- **Canvas lazy loading:** `isPageVisible()` check per page with IntersectionObserver refs -- only visible pages render iframes
- **Pagination:** `usePagination` composable for list views
- **No virtualization** for large tree structures (StructureTree renders all nodes). For complex documents with hundreds of nodes, this could be a performance bottleneck.
- **JSON undo/redo snapshots:** `JSON.stringify` of full document tree on each mutation. With large trees (100+ nodes), this could cause frame drops.

### 7.3 Asset Optimization

- **SVG:** Icons via lucide-vue-next (tree-shakeable SVG icons)
- **Fonts:** Inter and JetBrains Mono declared in CSS -- loaded from system/CDN (no local font files observed)
- **IndexedDB:** Layout state persisted via `idb` library for offline resilience

---

## 8. Testing

### 8.1 Test Coverage

| Category | Files with Tests | Total Files | Coverage |
|----------|-----------------|-------------|----------|
| **Stores** | 18 spec files | 18 stores | ~100% |
| **Composables** | 16 spec files | 18 composables | ~89% |
| **Organisms** | 25+ spec files | 30+ organisms | ~80% |
| **Molecules** | 25+ spec files | 55 molecules | ~45% |
| **Atoms** | 2 spec files | 16 atoms | ~12% |
| **Pages** | 5 spec files | 6 pages | ~83% |
| **Utils** | 8 spec files | 9 utils | ~89% |

**Total:** 123 test files, 1,794 tests, all passing (170s runtime)

### 8.2 Test Quality

Tests use `@vue/test-utils` + `vitest` with jsdom environment. Store tests properly set up Pinia test instances. Tests include:
- Unit tests for pure logic (formatters, validators, generators)
- Component mount tests with prop/emit assertions
- Store action/getter tests with state verification
- Integration-level tests (pipelineE2E.spec.ts, sessionStore.spec.ts)

### 8.3 E2E Tests

**No E2E test framework configured.** No Playwright, Cypress, or similar. The critical user flow (Upload -> Analyzing -> Editor -> Export) has no end-to-end coverage. The `pipelineE2E.spec.ts` is a store-level integration test, not a browser-level E2E test.

### 8.4 Gaps

- **Atoms undertested:** Only ResizableHandle and ToggleButton have specs. The remaining 14 atoms (Button, ProgressBar, ColorPicker, etc.) lack tests.
- **Molecules ~55% untested:** About half of molecules lack dedicated test files.
- **LoginPage:** No tests.

---

## 9. Security (Frontend)

### 9.1 XSS Vectors

| Vector | Location | Risk | Mitigation |
|--------|----------|------|------------|
| `v-html` | `BibliotecaComponentList.vue:14` | MEDIUM | Renders `item.previewHtml` from user-saved component library. Content originates from DOM snapshot but could be tampered with in saved project JSON. |
| `srcdoc` iframes | `HTMLCanvas.vue:43`, `SyncView.vue:71` | LOW | Sandboxed (`allow-same-origin allow-scripts`). Content from backend pipeline, not user input. |
| SVG injection | `svgSanitizer.ts` | LOW | Custom sanitizer removes `<script>`, `on*` handlers, `javascript:` URLs. |
| Template name | `session.ts:sanitizeTemplateName()` | LOW | Strips HTML tags and special characters. |

### 9.2 Authentication & Tokens

- **Auth:** Supabase OAuth (Google sign-in) via `@supabase/supabase-js`
- **Token storage:** Supabase manages token persistence (localStorage by default). Tokens injected via `apiFetch.ts` wrapper (`Authorization: Bearer {token}`)
- **Supabase client init:** Uses `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` env vars. Anon key is public by design (RLS enforces security server-side).
- **No CSRF token handling** -- not needed for API-only backend with Bearer auth.

### 9.3 Sensitive Data

- **localStorage:** Only `migrador-planet:recent-colors` (non-sensitive). Supabase manages its own auth storage.
- **No API keys in code** -- env vars via `import.meta.env.VITE_*`
- **IndexedDB:** Layout state persisted. Contains document tree (user data) but no credentials.

### 9.4 Dependency Vulnerabilities

```
3 vulnerabilities found (npm audit):

1. dompurify <=3.3.1 (MODERATE x2)
   - Mutation-XSS via Re-Contextualization
   - ADD_ATTR predicate skips URI validation
   - Transitive via monaco-editor >=0.54.0
   - Fix: npm audit fix --force (downgrades monaco-editor to 0.53.0)

2. vite 7.0.0-7.3.1 (HIGH)
   - Path Traversal in Optimized Deps
   - server.fs.deny bypass
   - Arbitrary File Read via WebSocket
   - Fix: npm audit fix (patch available)
```

---

## 10. Technical Debt Catalog

### Frontend Architecture (FE-*)

| ID | Description | Severity | Impact | Effort |
|----|-------------|----------|--------|--------|
| FE-001 | **AnalyzingPage.vue is 1,195 LOC** -- combines stepper logic, state machine, checkpoint handling, cancellation, reconnection, and rendering. Should extract state machine logic into composable and split sub-views. | HIGH | Maintainability | 8h |
| FE-002 | **HTMLCanvas.vue is 913 LOC** -- mixes rendering, zoom, scroll, keyboard, drag/drop, iframe management. Canvas interaction logic already extracted to composable but rendering logic remains oversized. | HIGH | Maintainability | 6h |
| FE-003 | **session.ts is 534 LOC** -- `loadFromPipelineResult()` alone is ~200 lines orchestrating 9 stores. Should be split into a pipeline loader service. | HIGH | Maintainability, Testability | 4h |
| FE-004 | **Mixed store API styles** -- 8 stores use Composition API, 9 use Options API. Should standardize on one style. | MEDIUM | Consistency | 4h |
| FE-005 | **Duplicate ConfidenceBadge** -- exists in both `atoms/` and `molecules/` with overlapping purposes. | LOW | Confusion | 1h |
| FE-006 | **HelloWorld.vue still present** -- Vite scaffold leftover in `components/`. | LOW | Cleanliness | 5min |
| FE-007 | **No barrel export for composables** -- unlike atoms/molecules/organisms, composables lack an `index.ts`. | LOW | DX | 30min |
| FE-008 | **Design token duplication** -- Colors defined in both `main.css @theme` and `tailwind.config.ts`. Risk of drift. | MEDIUM | Consistency | 2h |
| FE-009 | **CSS approach inconsistency** -- HomePage uses Tailwind utilities in template, all other components use BEM scoped styles. | LOW | Consistency | 2h |

### UX Patterns (UX-*)

| ID | Description | Severity | Impact | Effort |
|----|-------------|----------|--------|--------|
| UX-001 | **No global notification/toast store** -- toast management via component-level `defineExpose` makes it impossible to trigger toasts from stores or services. | MEDIUM | UX, DX | 3h |
| UX-002 | **No responsive/mobile design** -- editor is desktop-only. Login, Home, Upload pages lack mobile optimization. | LOW | Reach | 16h+ |
| UX-003 | **No dark mode support** -- no color scheme toggle, no `dark:` variants. | LOW | UX | 16h+ |
| UX-004 | **No skeleton screens in editor** -- panels appear empty until pipeline data loads. | LOW | Perceived Performance | 4h |
| UX-005 | **Emoji icons in toolbar buttons** -- ToggleButtons in TopToolbar use emoji (e.g., `icon="map"`) which renders inconsistently across OS/browsers. Should use lucide-vue-next icons. | MEDIUM | Visual Consistency | 2h |

### Accessibility (A11Y-*)

| ID | Description | Severity | Impact | Effort |
|----|-------------|----------|--------|--------|
| A11Y-001 | **No focus trap in modals** -- BibliotecasModal, AmbiguousFieldModal, ExportValidationModal, ServiceFailureModal lack focus trapping. Tab can escape to background content. | HIGH | Accessibility | 4h |
| A11Y-002 | **No custom focus indicators** -- relies on browser defaults which are inconsistent and often invisible on dark backgrounds. | MEDIUM | Accessibility | 3h |
| A11Y-003 | **Neutral-500 text contrast** -- #737373 on white is 4.48:1, below WCAG AA 4.5:1 threshold for normal text. Used in meta text, timestamps, hints. | MEDIUM | Accessibility | 1h |
| A11Y-004 | **Missing alt texts** -- PDF viewer and canvas iframe placeholders have `aria-label` but no alt text fallback on decorative images/icons. | LOW | Accessibility | 2h |

### Performance (PERF-*)

| ID | Description | Severity | Impact | Effort |
|----|-------------|----------|--------|--------|
| PERF-001 | **No tree virtualization** -- StructureTree renders all nodes in DOM. Documents with 200+ nodes will cause scroll jank. | MEDIUM | Performance | 8h |
| PERF-002 | **JSON.stringify undo snapshots** -- Full document tree serialized on each mutation. Large trees cause GC pressure and potential frame drops. | MEDIUM | Performance | 6h |
| PERF-003 | **Monaco editor bundle size** -- ~3MB compressed. Consider lazy-loading Monaco only when code tab is activated. | LOW | Initial Load | 2h |

### Security (SEC-*)

| ID | Description | Severity | Impact | Effort |
|----|-------------|----------|--------|--------|
| SEC-001 | **v-html with user-controlled content** -- `BibliotecaComponentList.vue` renders `previewHtml` from saved project data via v-html. Should sanitize with DOMPurify or render as sandboxed iframe. | HIGH | Security (XSS) | 2h |
| SEC-002 | **Vulnerable dompurify (transitive)** -- monaco-editor depends on dompurify <=3.3.1 with known mutation-XSS. | MEDIUM | Security | 1h |
| SEC-003 | **Vulnerable vite (dev server)** -- vite 7.0.0-7.3.1 has path traversal and file read vulnerabilities. Dev-only risk but should be patched. | HIGH | Security (Dev) | 30min |

### Testing (TEST-*)

| ID | Description | Severity | Impact | Effort |
|----|-------------|----------|--------|--------|
| TEST-001 | **No E2E test framework** -- Critical user flow (Upload->Analyze->Edit->Export) has zero browser-level test coverage. | HIGH | Quality Assurance | 16h |
| TEST-002 | **Atoms are 88% untested** -- Only 2 of 16 atoms have spec files. Foundational UI primitives should have tests. | MEDIUM | Regression Risk | 6h |
| TEST-003 | **Molecules ~55% untested** -- 30 of 55 molecules lack tests. | MEDIUM | Regression Risk | 12h |
| TEST-004 | **LoginPage has no tests** -- Auth flow untested. | LOW | Regression Risk | 2h |

---

## 11. Debt Summary by Priority

### CRITICAL (0 items)
No critical debts identified. The application is functional and stable.

### HIGH (7 items)
| ID | Description | Effort |
|----|-------------|--------|
| SEC-001 | v-html XSS vector in BibliotecaComponentList | 2h |
| SEC-003 | Vite dev server vulnerabilities (patch available) | 30min |
| A11Y-001 | No focus trap in modals | 4h |
| FE-001 | AnalyzingPage.vue oversized (1,195 LOC) | 8h |
| FE-002 | HTMLCanvas.vue oversized (913 LOC) | 6h |
| FE-003 | session.ts orchestrator too large (534 LOC) | 4h |
| TEST-001 | No E2E test framework | 16h |

### MEDIUM (11 items)
| ID | Description | Effort |
|----|-------------|--------|
| SEC-002 | Vulnerable dompurify (transitive) | 1h |
| FE-004 | Mixed store API styles | 4h |
| FE-008 | Design token duplication (CSS + Tailwind config) | 2h |
| UX-001 | No global toast/notification store | 3h |
| UX-005 | Emoji icons inconsistency | 2h |
| A11Y-002 | No custom focus indicators | 3h |
| A11Y-003 | Neutral-500 contrast issue | 1h |
| PERF-001 | No tree virtualization for StructureTree | 8h |
| PERF-002 | JSON.stringify undo snapshots performance | 6h |
| TEST-002 | Atoms 88% untested | 6h |
| TEST-003 | Molecules 55% untested | 12h |

### LOW (8 items)
| ID | Description | Effort |
|----|-------------|--------|
| FE-005 | Duplicate ConfidenceBadge (atom + molecule) | 1h |
| FE-006 | HelloWorld.vue scaffold leftover | 5min |
| FE-007 | No composables barrel export | 30min |
| FE-009 | CSS approach inconsistency (Tailwind vs BEM) | 2h |
| UX-002 | No responsive/mobile design | 16h+ |
| UX-003 | No dark mode | 16h+ |
| UX-004 | No skeleton screens in editor | 4h |
| A11Y-004 | Missing alt texts on images/icons | 2h |
| PERF-003 | Monaco bundle optimization | 2h |
| TEST-004 | LoginPage untested | 2h |

---

## 12. Architecture Diagram

```
[Router] ──> [Pages]
               |
               ├── LoginPage
               ├── HomePage
               ├── UploadPage
               ├── AnalyzingPage (pipeline flow)
               └── TemplateEditor
                     └── [EditorLayout]
                           ├── TopToolbar (organism)
                           ├── LeftPanel
                           │     ├── StructureTree
                           │     ├── FieldNavigator
                           │     └── FileExplorer
                           ├── CenterPanel
                           │     ├── HTMLCanvas (iframe-based)
                           │     ├── PDFReference
                           │     ├── MonacoTabsInner
                           │     └── SyncView / DiffViewer
                           ├── InspectorPanel
                           │     ├── ElementInspector
                           │     ├── SectionInspector
                           │     ├── TableInspector
                           │     ├── ImageInspector
                           │     ├── ChartInspector
                           │     └── ComponentInspector
                           └── BottomPanel
                                 ├── ConsolePanel
                                 ├── TestDataPanel
                                 ├── TestReportPanel
                                 └── AutoFixPanel

[Pinia Stores]
  sessionStore (orchestrator) ──> all other stores
  templateStore (document tree) <── inspectorStore, codeStore, mappingStore
  editorStore (UI state) <── layoutStore
  layoutStore (multi-layout) ──> templateStore, confidenceStore, coverageStore
  generationStore (HTML/CSS output)
  codeStore (Monaco content) ──> templateStore, generationStore, chartStore
```

---

## 13. Recommendations

### Immediate (Next Sprint)
1. **Patch vite** (`npm audit fix`) -- 30 min, zero risk
2. **Sanitize v-html in BibliotecaComponentList** -- add DOMPurify or use sandboxed iframe
3. **Add focus trap to modals** -- use `@vueuse/core` `useFocusTrap` (already a dependency)

### Short-Term (1-2 Sprints)
4. **Extract AnalyzingPage state machine** into `useAnalyzingStateMachine` composable
5. **Create global toast store** for cross-component notifications
6. **Add E2E test framework** (Playwright recommended) with smoke test for Upload->Edit flow
7. **Standardize store API style** (Composition API recommended for consistency)

### Medium-Term (3-5 Sprints)
8. **Virtualize StructureTree** for large documents (use `@tanstack/vue-virtual`)
9. **Optimize undo/redo** -- use structural sharing or delta-based snapshots instead of full JSON
10. **Increase atom/molecule test coverage** to >80%
11. **Unify design token source** -- single source of truth in CSS custom properties
