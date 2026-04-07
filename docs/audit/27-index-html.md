# Auditoria: Geração de index.html (Output Template)

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**FR16** — O sistema deve gerar `index.html` com `<body data-bind="with: {ChaveRaizJSON}">`, bindings Knockout (`data-bind="text:"`, `data-bind="html:"`) e placeholder `var data = ##TEMPLATE_DATA##;`.

**FR20** — ZIP contém `template/` com: `index.html`, `css/style.css`, `js/base.js`, `js/exemplo.js`, `assets/`.

**NFR7** — ZIP autocontido: abrindo `index.html` localmente com dados de `exemplo.js` deve renderizar corretamente no browser.

**FR23** — Validação pré-export verifica: placeholder `##TEMPLATE_DATA##`, presença de `ko.applyBindings`, integridade de `data-bind` em relação ao XSD, referências de assets.

**FR2** — Nomes dos campos XSD definem os nomes canônicos nos `data-bind` Knockout do template.

Compatibilidade com motor: `knockout-3.4.2.js`, `knockout.mapping.js`, `Chart.min.js`, `chartjs-plugin-datalabels.min.js`; bibliotecas em `../Bibliotecas/js/`.

Fonte: `docs/prd-v3.md` FR2, FR16, FR20, FR23, NFR7.

---

## Frontend — Status de Implementação

**useExport.ts** (`frontend/src/composables/useExport.ts`) — **Implementado:**
- `exportZip({ includeTestData, skipWarnings })` — gera e dispara download do ZIP
- Integrado à TopToolbar via botão 📦 Exportar
- Suporte a datasets de teste (checkbox no modal)
- Chama `usePreExportValidation` antes de gerar

**usePreExportValidation.ts** (`frontend/src/composables/usePreExportValidation.ts`) — **Implementado:**
- Validação pré-export com erros bloqueantes e warnings
- Verifica referências de assets (FR23)
- ExportValidationModal exibe resultado ao operador

**O que falta no frontend:**
- Geração do `index.html` ocorre no backend — o frontend apenas dispara o endpoint de export e faz download do ZIP
- Validação de `data-bind` vs XSD (FR23) — implementação a confirmar no `usePreExportValidation`

---

## Backend — Status de Implementação

**stage5_template_generation.py** (`backend/services/stages/stage5_template_generation.py`) — **Parcialmente verificado:**
- Gera CSS com classes de fonte real (`font-family: '{font_name}'`)
- Gera `data-bind="text: {field}"` e `data-bind="html: {field}"` para campos mapeados
- Gera `data-bind="text: {xsd_path}"` — caminhos derivados do XSD (FR2)
- Strip de prefixo subset PDF nas fontes

**Não verificado diretamente no stage5:**
- Geração de `<body data-bind="with: {ChaveRaizJSON}">` (FR16)
- Presença do placeholder `var data = ##TEMPLATE_DATA##;` em `exemplo.js` ou `base.js`
- `ko.applyBindings(...)` em `base.js`
- Estrutura do ZIP: `template/index.html`, `css/style.css`, `js/base.js`, `js/exemplo.js`, `assets/`
- Referências às bibliotecas JS em `../Bibliotecas/js/` (knockout, Chart.js)

**Endpoint de export:**
- Não verificado qual endpoint o `useExport.ts` chama para gerar o ZIP
- Não verificado se o ZIP resultante atende NFR7 (autocontido, renderiza localmente)

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Presença de `var data = ##TEMPLATE_DATA##;` no ZIP gerado não confirmada | 🔴 Crítico | Backend | FR16 |
| 2 | `ko.applyBindings` no `base.js` não confirmado | 🔴 Crítico | Backend | FR16, FR23 |
| 3 | Estrutura do ZIP (`template/index.html`, `css/`, `js/`, `assets/`) não auditada diretamente | 🟡 Importante | Backend | FR20 |
| 4 | Referências a `../Bibliotecas/js/` no `index.html` gerado não confirmadas — ZIP pode não ser autocontido | 🟡 Importante | Backend | NFR7 |
| 5 | Validação de `data-bind` vs XSD (FR23) na validação pré-export não confirmada | 🟡 Importante | Frontend | FR23 |
| 6 | `<body data-bind="with: {ChaveRaizJSON}">` não confirmado no HTML gerado | 🟡 Importante | Backend | FR16 |
| 7 | Teste de NFR7 (abrir ZIP localmente no browser) não documentado como executado | 🟡 Importante | Backend/Frontend | NFR7 |

---

## Backlog Gerado

1. **Auditar ZIP gerado** — Descompactar um ZIP de exemplo e verificar: estrutura de pastas, presença de `##TEMPLATE_DATA##`, `ko.applyBindings`, `<body data-bind="with:...">`, referências JS.
2. **Teste NFR7** — Criar teste E2E: gerar ZIP, descompactar, abrir `index.html` localmente no browser com `exemplo.js`, verificar renderização sem servidor.
3. **Bibliotecas JS no ZIP** — Verificar se `knockout-3.4.2.js` e `Chart.min.js` são incluídos no ZIP ou se dependem de `../Bibliotecas/` externas (risco de ZIP não autocontido).
4. **Validação data-bind vs XSD** — Confirmar que `usePreExportValidation` verifica consistência entre `data-bind` gerados e campos do XSD.
5. **Documentar endpoint de export** — Identificar e documentar o endpoint backend chamado pelo `useExport.ts` e o processo de geração do ZIP.

---

## Status Geral

🟡 Parcial — A infraestrutura de export (frontend) está implementada com validação pré-export e modal de confirmação. O backend gera `data-bind` corretamente por campo. Os gaps críticos estão na confirmação da estrutura completa do ZIP: presença de `##TEMPLATE_DATA##`, `ko.applyBindings`, e autocontência do arquivo (NFR7) — itens que precisam de auditoria direta no output gerado.
