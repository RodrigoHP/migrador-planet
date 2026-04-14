# Epic 1: Frontend Web App — Migrador Planetexpress

**Status:** Ready for Story Creation
**Data:** 2026-03-10
**Criado por:** @pm (Morgan)
**Epic Owner:** @dev (Dex)

---

## Epic Goal

Implementar o frontend web app completo do Migrador Planetexpress — uma SPA Vue 3 + TypeScript servida pelo FastAPI que permite ao Operador Técnico carregar PDF + XSD + Dados, revisar mapeamento de campos, configurar layout e exportar um ZIP HTML/Knockout.js autocontido.

---

## Contexto do Sistema

**Plataforma:** Web app puro — browser Chrome/Edge, sem instalação, sem Electron, sem Tauri
**Backend:** FastAPI em Railway (já documentado em `docs/architecture/architecture.md` v3.1)
**Referências obrigatórias:**
- `docs/prd.md` (v2.2) — requisitos funcionais e não-funcionais
- `docs/architecture/architecture.md` (v3.1) — arquitetura técnica completa
- `docs/front-end-spec.md` (v1.0) — especificação técnica de frontend (fonte de verdade para implementação)

**Stack frontend:**
- Vue 3 + TypeScript + Vite
- Pinia (4 stores) + Vue Router (6 rotas com guards)
- PDF.js, Monaco Editor, Chart.js (todos lazy)
- idb (IndexedDB), lucide-vue-next, Tailwind CSS

**Integração:**
- `POST /extract`, `POST /ai/match`, `POST /generate` — chamadas REST
- `GET /progress/{jobId}` — SSE para progresso em tempo real
- `GET /preview/{jobId}` — preview em nova aba
- `GET /export/{jobId}/zip` — download do ZIP final

---

## Stories

### Story 1.1 — Setup & Scaffold

**Executor:** `@dev`
**Quality Gate:** `@architect`
**Quality Gate Tools:** `[architecture_review, pattern_validation, bundle_size_check]`
**Risco:** BAIXO

**Descrição:** Scaffold completo do projeto frontend — estrutura de pastas Atomic Design, Vite config com code splitting, Tailwind com tokens customizados, Vue Router com 6 rotas e guards, 4 Pinia stores com interfaces TypeScript, 4 composables base, AppHeader e AppToast organisms.

**Quality Gates:**
- Pre-Commit: Estrutura de pastas conforme front-end-spec seção 12.2, TypeScript sem erros, Tailwind tokens corretos
- Pre-PR: @architect valida organização de stores, guards de navegação e separação de responsabilidades

---

### Story 1.2 — Step 1: Upload

**Executor:** `@dev`
**Quality Gate:** `@architect`
**Quality Gate Tools:** `[api_contract_validation, sse_integration_test, file_api_test]`
**Risco:** MÉDIO (File System Access API + SSE)

**Descrição:** Implementar a tela `/upload` completa — FileDropzone × 3 (PDF/XSD/Dados) com File System Access API (`showOpenFilePicker`), CrossValidationBadge, ProgressBar + ProgressLabel via SSE, integração com `POST /extract` e `GET /progress/{jobId}`, e atualização do session store.

**Quality Gates:**
- Pre-Commit: File System Access API funcional em Chrome/Edge, SSE conecta e recebe eventos, session store populado após /extract
- Pre-PR: @architect valida contrato com backend e tratamento de erros fatais vs recuperáveis

---

### Story 1.3 — Step 2: Campos

**Executor:** `@dev`
**Quality Gate:** `@architect`
**Quality Gate Tools:** `[pdfjs_integration_test, mapping_store_validation, ui_state_test]`
**Risco:** MÉDIO (PDF.js lazy + mapeamento manual)

**Descrição:** Implementar a tela `/campos` — PDFViewer com PDF.js lazy (highlight de bounding box), FieldMappingTable com FieldStatusBadge e ConfidenceBadge, FieldDetailPanel com inline editor para mapeamento manual, guards que impedem avançar com campos required `not_found`, e atualização do mapping store.

**Quality Gates:**
- Pre-Commit: PDF.js carrega lazy, bounding box destaca no PDF ao selecionar campo, mapeamento manual persiste no store
- Pre-PR: @architect valida separação PDFViewer/FieldDetailPanel e lógica de guard de confirmação

---

### Story 1.4 — Step 3: Layout

**Executor:** `@dev`
**Quality Gate:** `@dev` → revisão por `@architect`
**Quality Gate Tools:** `[layout_store_validation, preview_render_test, bibliotecas_integration]`
**Risco:** BAIXO

**Descrição:** Implementar a tela `/layout` — LayoutControls (margens, fonte, cores, espaçamento), LayoutPreview com debounce 300ms, ColorPicker, FontSelector, e integração com BibliotecasModal (catálogo de versões via `GET /bibliotecas/catalog`, persistido no layout store via idb).

**Quality Gates:**
- Pre-Commit: Preview atualiza em tempo real com debounce, layout store persiste seleções, modal Bibliotecas abre e fecha corretamente
- Pre-PR: @architect valida BibliotecasModal como organism reutilizável e integração com idb

---

### Story 1.5 — Step 4: Geração

**Executor:** `@dev`
**Quality Gate:** `@architect`
**Quality Gate Tools:** `[monaco_lazy_test, chartjs_config_test, sse_generation_test, preview_tab_test]`
**Risco:** ALTO (Monaco + Chart.js lazy + SSE + preview)

**Descrição:** Implementar a tela `/geracao` — integração com `POST /generate` via SSE, MonacoTabs (3 abas: index.html/style.css/base.js, lazy), FidelityScore com animação, IASuggestionList, ChartjsConfigPanel (lazy), RightPanelToggle, botão "Abrir Preview" que abre `GET /preview/{jobId}` em nova aba, e atualização do generation store.

**Quality Gates:**
- Pre-Commit: Monaco e Chart.js carregam lazy (fora do chunk principal), SSE progresso funcional, preview abre em nova aba com TTL 10min
- Pre-PR: @architect valida code splitting (< 400KB gzip chunk inicial), gestão de EventSource e cleanup em onUnmounted

---

### Story 1.6 — Step 5: Exportar + Projeto

**Executor:** `@dev`
**Quality Gate:** `@architect`
**Quality Gate Tools:** `[zip_download_test, project_save_restore_test, checklist_validation]`
**Risco:** BAIXO

**Descrição:** Implementar a tela `/exportar` — ExportChecklist com validações automáticas do ZIP, botão "Download ZIP" (`GET /export/{jobId}/zip` com `URL.createObjectURL`), botão "Salvar Projeto (.json)" via `showSaveFilePicker`, composable `useProject` (serializa/restaura todos os stores), fluxo "Abrir Projeto" na Home (restaura stores e navega para o step correto).

**Quality Gates:**
- Pre-Commit: ZIP download funcional com revoke após 60s, projeto .json salva e restaura corretamente, navegação retoma no step certo
- Pre-PR: @architect valida `useProject` composable e fluxo completo end-to-end (Upload → Exportar → Retomar)

---

## Compatibility Requirements

- Browser: Chrome/Edge modernos (sem suporte a Firefox/Safari necessário)
- File System Access API: requerida (Chrome 86+, Edge 86+)
- Tela mínima: 1024px (aviso em telas menores, sem colapso responsivo)
- Backend: FastAPI Railway — contrato REST/SSE conforme `docs/architecture/architecture.md` v3.1

---

## Risk Mitigation

| Story | Risco | Mitigação |
|-------|-------|----------|
| 1.2 | File System Access API não disponível | Fallback para `<input type="file">` |
| 1.2 | SSE falha de conexão | Reconexão automática no `useSSE`, timeout 30s |
| 1.5 | Monaco bundle grande | `defineAsyncComponent` + manual chunk Vite |
| 1.5 | Preview expirado (TTL 10min) | `previewExpired: true` no store, botão "Regenerar Preview" |
| Todos | Backend indisponível em dev | Proxy Vite → `localhost:8000`, mock opcional |

**Rollback:** Frontend é estático (SPA). Reverter deploy = redeployar versão anterior no Railway. Sem impacto em dados do backend.

---

## Definition of Done

- [ ] Todas as 6 stories concluídas com critérios de aceite aprovados por @architect
- [ ] Fluxo completo testado manualmente: Upload → Campos → Layout → Geração → Exportar
- [ ] Fluxo "Retomar Projeto" funcional (salvar .json → reabrir → continuar no step)
- [ ] Bundle inicial < 400KB gzip (Monaco, PDF.js, Chart.js fora do chunk principal)
- [ ] Sem erros TypeScript em `npm run build`
- [ ] `frontend/dist/` pronto para ser servido pelo FastAPI StaticFiles

---

## Handoff para @sm

Story Manager — criar user stories detalhadas para este epic. Considerações:

- Este é um **frontend greenfield** — não há código existente para preservar
- Stack definida na `docs/front-end-spec.md` (v1.0) — fonte de verdade para implementação
- Atomic Design obrigatório: atoms → molecules → organisms → templates → pages (seção 5 do spec)
- Guards de navegação obrigatórios: não pular steps sem dados do step anterior
- Lazy loading obrigatório para PDF.js, Monaco Editor e Chart.js
- Interfaces TypeScript exatas definidas na seção 9 do front-end-spec
- Sequência obrigatória: Story 1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 (dependência sequencial)

---

*Epic criado por @pm (Morgan) — 2026-03-10*
*— Morgan, planejando o futuro 📊*
