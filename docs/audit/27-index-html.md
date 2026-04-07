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

**services/template_generator.py** (`backend/services/template_generator.py`) — **Implementado:**
- `_generate_index_html()` — gera `index.html` completo com `<body data-bind="with: {root_key}">` ✅
- Placeholder `var data = ##TEMPLATE_DATA##;` presente ✅
- `ko.applyBindings(new ViewModel(data))` em `base.js` e `exemplo.js` ✅
- Referência a `../Bibliotecas/js/knockout-3.4.2.js` no `index.html` gerado
- `_generate_base_js()` — gera `js/base.js` com funções de formatação BR, helpers de paginação, ViewModel
- `_generate_exemplo_js()` — gera `exemplo.js` com dados sintéticos do XSD

**routers/export.py** (`backend/routers/export.py`) — **Implementado com gaps:**
- `GET /export/{job_id}/zip` — gera ZIP com `zipfile.ZipFile`
- Estrutura atual do ZIP:
  - ✅ `index.html`
  - ✅ `js/base.js`
  - ⚠️ `exemplo.js` (na raiz, não em `js/exemplo.js` como especifica FR20)
  - ❌ `css/style.css` ausente do ZIP
  - ❌ `assets/` ausente do ZIP

**NFR7 — Autocontido:**
- `index.html` referencia `../Bibliotecas/js/knockout-3.4.2.js` — depende de pasta `Bibliotecas/` **externa** ao ZIP
- ZIP **não é autocontido** — abrindo localmente sem a pasta Bibliotecas, o Knockout não carrega e o template não renderiza

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | ZIP não inclui `css/style.css` — template gerado sem folha de estilos no pacote | 🔴 Crítico | Backend | FR20 |
| 2 | ZIP não inclui pasta `assets/` — imagens do template ausentes no pacote de export | 🔴 Crítico | Backend | FR20 |
| 3 | ZIP **não é autocontido** — referencia `../Bibliotecas/js/knockout-3.4.2.js` externo; falha ao abrir localmente sem Bibliotecas | 🔴 Crítico | Backend | NFR7 |
| 4 | `exemplo.js` está na raiz do ZIP em vez de `js/exemplo.js` (divergência da spec FR20) | 🟡 Importante | Backend | FR20 |
| 5 | Validação de `data-bind` vs XSD (FR23) na validação pré-export não confirmada | 🟡 Importante | Frontend | FR23 |
| 6 | `Chart.min.js` e `chartjs-plugin-datalabels.min.js` não incluídos no ZIP — gráficos quebram offline | 🟡 Importante | Backend | NFR7 |

---

## Backlog Gerado

1. **Incluir `css/style.css` no ZIP** — Adicionar geração e inclusão da folha de estilos em `export.py` via `zf.writestr("css/style.css", css_content)`.
2. **Incluir `assets/` no ZIP** — Ler pasta `assets/` do template e adicionar cada arquivo ao ZIP em `zf.write(path, "assets/{name}")`.
3. **Tornar ZIP autocontido (NFR7)** — Duas opções: (a) incluir `knockout-3.4.2.js` e `Chart.min.js` diretamente no ZIP em `js/libs/`; (b) usar CDN com fallback. Atualizar referências no `index.html` gerado.
4. **Mover `exemplo.js` para `js/`** — Corrigir `export.py`: `zf.writestr("js/exemplo.js", exemplo)` e atualizar referência no `index.html`.
5. **Validação data-bind vs XSD** — Confirmar que `usePreExportValidation` verifica consistência entre `data-bind` gerados e campos do XSD.
6. **Teste E2E NFR7** — Criar teste: gerar ZIP, descompactar, abrir `index.html` localmente no browser com `js/exemplo.js`, verificar renderização sem servidor.

---

## Status Geral

🔴 Crítico — A geração do `index.html` com bindings Knockout, `##TEMPLATE_DATA##` e `ko.applyBindings` está corretamente implementada em `template_generator.py`. Porém o ZIP de export tem 3 gaps críticos: ausência de `css/style.css`, ausência de `assets/`, e dependência de `../Bibliotecas/js/` externas que tornam o ZIP não autocontido (NFR7 violado). O template gerado não renderiza corretamente ao ser aberto localmente sem a estrutura de Bibliotecas do servidor.
