# Auditoria: Exportar — ZIP com HTML/CSS/JS + Pré-validação

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**FR20** (PRD v3.0): botão **📦 Exportar** na toolbar do editor; ZIP contém `template/` (index.html, css/style.css, js/base.js, js/exemplo.js, assets/); se houver datasets, exibe checkbox "Incluir datasets de teste" (padrão: desmarcado); geração e download ocorrem diretamente.

**FR23** (PRD v3.0): validação técnica automática antes do export verificando: `##TEMPLATE_DATA##`, `ko.applyBindings`, integridade dos `data-bind` em relação ao XSD, referências de assets; erro bloqueante bloqueia export.

**FR16–FR19** (PRD v3.0):
- `index.html`: `<body data-bind="with: {ChaveRaizJSON}">`, bindings KO, placeholder `var data = ##TEMPLATE_DATA##;`
- `css/style.css`: dimensões de página em polegadas (A4: 8.27in × 11.69in)
- `js/base.js`: funções Knockout, formatações, lógica de paginação dinâmica
- `exemplo.js`: JSON de dados de exemplo

**`docs/prd-v3.md` seção Validação (FR23)**: checklist pré-export com erros bloqueantes vs warnings.

---

## Frontend — Status de Implementação

### Componentes existentes

| Componente | Arquivo | Status |
|---|---|---|
| Composable de export | `frontend/src/composables/useExport.ts` | Implementado |
| Composable de validação | `frontend/src/composables/usePreExportValidation.ts` | Implementado |
| Checklist (legado) | `frontend/src/organisms/ExportChecklist.vue` | Legado (v1) |
| Botão Exportar | `frontend/src/organisms/TopToolbar.vue` | Implementado |
| Modal de validação | `frontend/src/molecules/ExportValidationModal.vue` | Implementado |

### O que funciona

**useExport.ts (`exportZip`):**
- Chama `usePreExportValidation.validate()` antes de exportar
- Erros bloqueantes → retorna `{ success: false, blockingErrors }` e mostra modal
- Só warnings → retorna `{ success: false, hasWarnings: true }` → caller mostra modal com opção de prosseguir
- Chama `POST /api/generate` com payload: `template_name`, `document_structure`, `field_mappings`, `layout_types`, `active_layout_id`
- Recebe `{ html, css, js, exemplo }` do backend
- Monta ZIP com JSZip:
  - `template/index.html`
  - `template/css/style.css`
  - `template/js/base.js`
  - `template/js/exemplo.js`
  - `template/assets/.gitkeep` (placeholder vazio)
- Se `includeTestData: true` → adiciona `test_data/{datasetId}.json` por dataset
- Download via `downloadBlob()` → `<a download>` com nome `{templateName}.zip`

**TopToolbar.vue:**
- Botão "📦 Exportar" chama `onExport()`
- Se há datasets → exibe modal com checkbox "Incluir datasets de teste"
- Passa `includeTestData` para `runExport()`
- Resultado com `blockingErrors` ou `hasWarnings` → exibe `ExportValidationModal`
- Confirmação do modal com warnings → reexecuta export com `skipWarnings: true`

**usePreExportValidation.ts:**
- **AC2**: verifica `##TEMPLATE_DATA##` no HTML — bloqueante
- **AC3**: verifica `ko.applyBindings` no JS — bloqueante
- **AC4**: extrai todos os `data-bind` do HTML; para cada campo verificado vs `mappingStore.fields`; campos obrigatórios ausentes → erro bloqueante; campos opcionais ausentes → warning
- **AC9–11**: valida `<!-- ko if/foreach/with/ifnot: path -->` comments contra XSD — bloqueante
- **AC6**: `isHtmlWellFormed()` via DOMParser — bloqueante
- **AC9** (CSS): `isCssValid()` via contagem de chaves — bloqueante
- **AC10**: referências a `../Bibliotecas/` não encontradas no catálogo — warning
- **AC5**: referências a assets locais não verificadas — warning

### O que falta / está incompleto

- **`ExportChecklist.vue` é legado (v1)**: verifica apenas se `generation.html/css/js` existem (stores do paradigma wizard), não os arquivos do `codeStore`. Não integrado ao fluxo v3 atual. O fluxo v3 usa `usePreExportValidation` diretamente.
- **Conteúdo do ZIP vem de `/api/generate`**, não do `codeStore`: se o operador editou o HTML/CSS/JS manualmente no Monaco, essas edições **não são enviadas** para `/api/generate` — o endpoint regenera a partir do `documentTree`/`fieldMappings`. As edições manuais no Monaco são perdidas no export.
- **`template/assets/` está vazio** (apenas `.gitkeep`): imagens extraídas do PDF não são incluídas no ZIP — o `index.html` gerado pode referenciar assets que não existem no pacote.
- **`base.js` sem funções de paginação dinâmica**: FR18 especifica `quebrarTabelaEntrePaginas()`, `criarNovaPagina()` — o conteúdo real de `base.js` gerado pelo backend não foi auditado neste documento, mas o `codeStore` tem apenas um template placeholder.
- **Cobertura como critério de export**: FR20/FR23 não exige cobertura mínima como critério de bloqueio, mas a spec menciona que campos obrigatórios mapeados é um dos checks. O check atual (`BINDING_FIELD_NOT_FOUND`) é mais rigoroso: bloqueia se qualquer campo referenciado em `data-bind` não existir no XSD, não se campos do XSD estão sem `data-bind`.
- **Backend `/api/export/{job_id}/zip`**: endpoint legado que empacota `html/css/js/exemplo` do job result — sem pasta `template/`, sem `test_data/`, sem `assets/`. Estrutura diferente do ZIP gerado pelo frontend via JSZip. Este endpoint parece não ser usado pelo fluxo v3.

---

## Backend — Status de Implementação

### `/api/generate` (usado pelo export v3)

Chamado por `useExport.ts`. Recebe `document_structure`, `field_mappings`, `layout_types`, `active_layout_id` e retorna `{ html, css, js, exemplo }`. Este é o endpoint principal de geração no fluxo v3. Arquivo não auditado diretamente, mas integração confirmada pelo `useExport.ts`.

### `/api/export/{job_id}/zip` (`backend/routers/export.py`)

Endpoint legado (v1) que:
- Busca job por ID e retorna ZIP com: `index.html`, `css/style.css`, `js/base.js`, `exemplo.js`
- Sem estrutura `template/`, sem `test_data/`, sem `assets/`
- Estrutura de ZIP diferente do formato v3
- Não parece estar integrado ao fluxo v3 do editor

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Edições manuais no Monaco (HTML/CSS/JS) não chegam ao ZIP — `/api/generate` regenera do zero | 🔴 Crítico | `useExport.ts` — payload não inclui `codeStore.fileContents` | FR20, FR24 |
| 2 | `template/assets/` no ZIP está vazio — imagens extraídas do PDF não empacotadas | 🔴 Crítico | `useExport.ts` linha ~127 `assets/.gitkeep` | FR14, FR20 |
| 3 | `ExportChecklist.vue` é legado v1 — não integrado ao fluxo v3 | 🟡 Importante | `ExportChecklist.vue` — usa `generation` store v1 | — |
| 4 | `/api/export/{job_id}/zip` é legado — estrutura de ZIP diferente do formato v3 | 🟡 Importante | `backend/routers/export.py` | FR20 |
| 5 | Cobertura de campos XSD sem `data-bind` não é critério de bloqueio | 🟢 Menor | `usePreExportValidation.ts` | FR23 |
| 6 | `base.js` com funções de paginação dinâmica não verificadas nesta auditoria | 🟢 Menor | Backend `/api/generate` | FR18 |

---

## Backlog Gerado

1. **Enviar `codeStore.fileContents` para `/api/generate`**: adicionar `code_overrides: { html, css, js }` ao payload de export para que edições manuais do Monaco prevaleçam sobre a regeneração do backend.
2. **Incluir assets no ZIP**: ao chamar `/api/generate`, receber URLs/base64 dos assets e adicioná-los a `template/assets/` no ZIP via JSZip.
3. **Deprecar `ExportChecklist.vue`**: componente verifica stores v1 (`generation.html/css/js`); substituir por uso do `usePreExportValidation` no fluxo v3.
4. **Deprecar `/api/export/{job_id}/zip`** ou atualizá-lo para o formato v3 (com pasta `template/`, `test_data/`, `assets/`).
5. **Adicionar check de cobertura mínima**: warning se cobertura geral < 80% (threshold de FR29) antes de exportar.

---

## Status Geral

🟡 **Parcial** — O fluxo de export está funcional: botão na toolbar, pré-validação com erros bloqueantes e warnings, ZIP com estrutura `template/`, opção de incluir datasets, download no navegador. Os gaps críticos são: (1) edições manuais no Monaco não chegam ao ZIP, pois o export regenera do zero via backend; (2) assets de imagem não são incluídos no pacote, resultando em ZIPs com referências quebradas de imagens.
