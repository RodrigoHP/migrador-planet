---
epic: 4
title: "Integração Frontend ↔ Backend"
status: Ready
owner: "@pm (Morgan)"
executor: "@dev"
quality_gate: "@architect"
---

# Epic 4: Integração Frontend ↔ Backend

## Status

Ready

## Objetivo

Conectar o frontend Vue (Epic 1) ao backend FastAPI (Epic 3), corrigindo todos os mismatches de rota, contrato e fluxo identificados na análise de integração. Ao final, o fluxo completo — upload → processamento → geração → download ZIP — deve funcionar end-to-end com dados reais.

## Contexto

O frontend (Epic 1) e o backend (Epic 3) foram desenvolvidos em paralelo com base nos contratos definidos no PRD e nos tipos TypeScript. A análise de integração revelou **8 gaps** entre as chamadas do frontend e os endpoints do backend:

### Gaps Identificados

| # | Frontend chama | Backend tem | Tipo de gap |
|---|---|---|---|
| G1 | `POST /upload/pdf` | `POST /api/upload/pdf` | Prefixo `/api` ausente nas chamadas — proxy Vite não intercepta |
| G2 | `POST /upload/xsd` | `POST /api/upload/xsd` | Idem G1 |
| G3 | `POST /upload/data` | `POST /api/upload/data` | Idem G1 |
| G4 | `GET /progress/{id}` | `GET /api/progress/{id}` | Idem G1 |
| G5 | `POST /extract` → retorna `{jobId}` | `POST /api/jobs` + body `{jobId}` | Rota diferente + schema invertido |
| G6 | `POST /generate` + body | ❌ não existe | Endpoint ausente |
| G7 | `GET /export/{id}/zip` | ❌ não existe | Endpoint ausente (FR20) |
| G8 | `GET /preview/{id}` (window.open) | `POST /api/preview` + body | Método HTTP + rota incompatíveis |

### Causa raiz dos gaps G1–G4

O Vite proxy (`vite.config.ts`) só intercepta paths que começam com `/api`:
```ts
proxy: {
  '/api': { target: 'http://localhost:8000', changeOrigin: true }
}
```
O frontend chama `/upload/pdf`, `/progress/...` — sem o prefixo. Solução: adicionar `/api/` em todas as chamadas do frontend, aproveitando o proxy existente.

### Causa raiz do gap G5

O frontend chama `POST /extract` esperando receber `{jobId}` de volta — ou seja, o backend gera o jobId. O backend tem `POST /api/jobs` que recebe `{jobId}` no body (o jobId é gerado no upload). A solução é: adicionar endpoint `POST /api/extract` que aceita chamada sem body, usa o jobId da sessão (via armazenamento temporário compartilhado) ou muda o frontend para seguir o fluxo correto.

**Decisão de design:** Criar `POST /api/extract` que gera um novo jobId internamente (usando o último upload da sessão), inicia o pipeline e retorna `{jobId}`. Isso preserva o contrato esperado pelo frontend.

## Stack

- **Frontend:** Vue 3 + TypeScript + Pinia + Vite (proxy `/api` → `:8000`)
- **Backend:** FastAPI + Python + uvicorn

## Arquivos de Referência

| Arquivo | Relevância |
|---------|-----------|
| `frontend/vite.config.ts` | Proxy config — confirma roteamento via `/api` |
| `frontend/src/pages/UploadPage.vue` | Chama upload + extract + SSE |
| `frontend/src/pages/GeracaoPage.vue` | Chama `/generate` + preview |
| `frontend/src/pages/ExportarPage.vue` | Chama `/export/{id}/zip` |
| `frontend/src/composables/useSSE.ts` | SSE client — path `/progress/{id}` |
| `backend/main.py` | Routers com prefix `/api` |
| `backend/routers/upload.py` | Upload handlers |
| `backend/routers/jobs.py` | Pipeline + `POST /api/jobs` + `GET /api/result/{id}` |
| `backend/routers/progress.py` | SSE `GET /api/progress/{id}` |
| `backend/routers/preview.py` | `POST /api/preview` (incompatível com frontend) |

---

## Stories

### Story 4.1 — Correção de Rotas e Fluxo Upload → Extraction (G1–G5)

**Executor:** `@dev`
**Quality Gate:** `@architect`
**Quality Gate Tools:** `[api_contract_review, route_alignment_check, sse_integration_test]`

**Objetivo:** Corrigir os 5 gaps de prefixo de rota e o gap do endpoint `/extract`. Ao final, o fluxo upload → processamento → SSE deve funcionar end-to-end.

**Scope:**

*Frontend (UploadPage.vue + useSSE.ts):*
- Adicionar `/api` prefix em todas as chamadas de upload: `/upload/pdf` → `/api/upload/pdf`, `/upload/xsd` → `/api/upload/xsd`, `/upload/data` → `/api/upload/data`
- Mudar chamada `POST /extract` → `POST /api/extract`
- Corrigir SSE path em `useSSE.ts`: `/progress/${id}` → `/api/progress/${id}`

*Backend (novo endpoint):*
- Criar `POST /api/extract` em `backend/routers/jobs.py`: gera UUID v4 como jobId, reusa o diretório de upload mais recente em `/tmp/jobs/` (ou recebe `jobId` do upload se necessário), inicia pipeline, retorna `{jobId}`
- Alternativa mais simples: mudar frontend para enviar `POST /api/jobs` com o `jobId` retornado pelo upload

**Decisão:** A abordagem mais simples é modificar os uploads para retornar `{jobId}` (gerando e persistindo o UUID desde o primeiro upload), e usar esse jobId para chamar `POST /api/jobs`. Isso elimina a necessidade de um endpoint `/extract` novo e resolve G5 com mudança mínima.

**AC:**
1. `POST /api/upload/pdf` aceita arquivo, gera jobId, salva `input.pdf`, retorna `{jobId}`
2. `POST /api/upload/xsd` aceita arquivo, usa jobId do body (ou cookie/header de sessão), salva `schema.xsd`
3. `POST /api/upload/data` aceita arquivo, usa jobId, salva `data.json` ou `data.xml`
4. `POST /api/jobs` com `{jobId}` inicia pipeline — frontend usa jobId retornado pelo upload do PDF
5. SSE `GET /api/progress/{jobId}` recebe eventos `step` e `done` corretamente
6. Ao receber evento `done`, frontend navega para `/campos` com `session.extraction` populado
7. Nenhuma chamada do frontend bate em rota sem prefixo `/api`

---

### Story 4.2 — Endpoint `/api/generate` e Preview via GET (G6 + G8)

**Executor:** `@dev`
**Quality Gate:** `@architect`
**Quality Gate Tools:** `[api_contract_review, template_generation_test, preview_render_test]`

**Objetivo:** Criar o endpoint `POST /api/generate` que recebe mapeamento + config de layout + edições Monaco e dispara geração do template como job SSE. Converter preview para `GET /api/preview/{id}`.

**Scope:**

*Backend:*
- Criar `POST /api/generate` em `backend/routers/jobs.py` (ou novo router `generate.py`):
  - Body: `{mappingFields: List[FieldMapping], layoutConfig: dict, monacoEdits: dict}`
  - Gera novo jobId, salva request em disco, inicia pipeline de geração
  - Retorna `{jobId}` imediatamente
  - Pipeline de geração (separado do pipeline de extração): recebe fields + layout, chama `TemplateGenerator`, emite SSE, retorna `{html, css, js, exemplo, fidelityScore, fidelityComment, iaSuggestions}`
- Converter `POST /api/preview` → `GET /api/preview/{job_id}` (mantendo comportamento interno igual)

*Frontend (GeracaoPage.vue):*
- Atualizar chamada `/generate` → `/api/generate`
- Atualizar `window.open(${API_BASE}/preview/${id})` → `window.open(/api/preview/${id})`
- Tratar retorno SSE de geração: ao receber `done`, chamar `GET /api/result/{jobId}` para obter artefatos

**AC:**
1. `POST /api/generate` com body válido retorna `{jobId}` e inicia pipeline de geração
2. SSE stream de geração emite steps: "Gerando HTML", "Calculando fidelidade" com pcts
3. Ao final, `GET /api/result/{jobId}` retorna `{html, css, js, exemplo, fidelityScore, fidelityComment, iaSuggestions}`
4. Frontend popula `generation.html`, `generation.css`, `generation.js`, `generation.fidelityScore`
5. `GET /api/preview/{job_id}` retorna HTML renderizado (200 OK)
6. `window.open(/api/preview/${id})` abre preview em nova aba corretamente

---

### Story 4.3 — Endpoint ZIP Export (FR20) + Validação E2E (G7)

**Executor:** `@dev`
**Quality Gate:** `@architect`
**Quality Gate Tools:** `[zip_integrity_check, fr20_validation, e2e_flow_test]`

**Objetivo:** Implementar `GET /api/export/{job_id}/zip` que empacota o output do template como arquivo ZIP autocontido (FR20). Validar o fluxo completo end-to-end.

**Scope:**

*Backend (novo endpoint):*
- Criar `GET /api/export/{job_id}/zip` em novo router `backend/routers/export.py`:
  - Valida jobId (UUID v4 strict)
  - Busca resultado do job via `job_manager.get_job(job_id)`
  - Monta estrutura: `index.html`, `css/style.css`, `js/base.js`, `exemplo.js`
  - Cria ZIP em memória (`io.BytesIO` + `zipfile.ZipFile`)
  - Retorna `FileResponse` ou `Response` com `Content-Type: application/zip`
  - Nome do arquivo: `template-{job_id}.zip`
- Registrar router em `main.py`: `app.include_router(export.router, prefix="/api")`

*Frontend (ExportarPage.vue):*
- Atualizar chamada `/export/${id}/zip` → `/api/export/${id}/zip`
- Usar `generation.previewJobId` como source do jobId (já implementado)

*Validação E2E:*
- Documentar o fluxo completo testável manualmente:
  1. `start-backend.bat` + `start-frontend.bat`
  2. Upload PDF + XSD + dados → Analisar
  3. SSE progress → navega para /campos automaticamente
  4. /campos → /layout → /geracao → geração via `/api/generate`
  5. /exportar → Download ZIP → validar estrutura do ZIP

**AC:**
1. `GET /api/export/{job_id}/zip` retorna arquivo ZIP com `Content-Type: application/zip`
2. ZIP contém: `index.html`, `css/style.css`, `js/base.js`, `exemplo.js`
3. `index.html` contém bindings Knockout.js e `##TEMPLATE_DATA##` placeholder (FR16)
4. Abrindo `index.html` localmente com `exemplo.js` renderiza o documento (NFR7)
5. Frontend inicia download do ZIP com nome `template-{jobId}.zip`
6. Botão "Download ZIP" fica habilitado apenas quando `generation.previewJobId` está definido
7. Fluxo E2E completo funciona sem erros de console (404, CORS, 422)

---

## Compatibilidade

- Endpoints existentes (`/api/upload/*`, `/api/jobs`, `/api/progress/*`, `/api/result/*`) mantêm contrato atual
- Mudanças no frontend são aditivas (troca de path string) — sem breaking changes nos stores Pinia
- `POST /api/preview` pode coexistir com `GET /api/preview/{id}` durante transição

## Riscos

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| `TemplateGenerator` não suporta `monacoEdits` aplicados ao output | Média | Story 4.2: pipeline de geração aceita `monacoEdits` como override pós-geração |
| ZIP corrompido em Windows (paths com `\`) | Baixa | Usar forward slashes em zipfile.ZipFile |
| Sessão de upload sem jobId compartilhado entre routers | Média | Story 4.1: upload PDF gera e retorna jobId que é usado em todas as chamadas subsequentes |

## Rollback

Cada story é reversível independentemente — são novos endpoints ou alterações de string de path. Nenhuma mudança de schema de banco de dados ou store Pinia.

## Definition of Done

- [ ] Story 4.1: Upload + SSE funcionando end-to-end via `/api/*`
- [ ] Story 4.2: Geração via `/api/generate` + preview via `GET /api/preview/{id}`
- [ ] Story 4.3: Download ZIP via `GET /api/export/{id}/zip`
- [ ] Nenhum erro 404/CORS/422 no fluxo completo
- [ ] `start-backend.bat` + `start-frontend.bat` → fluxo completo funcional

— Morgan, planejando o futuro 📊
