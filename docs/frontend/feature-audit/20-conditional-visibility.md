# Auditoria: Condicionais + Tematização Condicional

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**FR9** — Propriedade Visibilidade no Inspetor com construtor visual `SE [campo] [operador] [valor]`, suportando condições compostas (E/OU); gera `<!-- ko if: expressão --> ... <!-- /ko -->` no HTML. Campos detectados como opcionais pelo Analisador Multi-Documento pré-configurados como condicionais.

**FR30** — Tematização Condicional: regras de aparência condicional vinculadas a campos do JSON (cor, imagem, logo). O sistema gera no `base.js` as funções correspondentes. A propriedade Visibilidade cobre show/hide; variações de estilo são configuráveis via Inspetor.

**FR39** — Visibilidade em todos os 4 níveis do Inspetor (Página, Seção, Componente, Elemento): 3 opções — Sempre visível, Condicional, Escondido.

Fonte: `docs/prd-v3.md` seções FR9, FR30, FR39.

---

## Frontend — Status de Implementação

**VisibilityControl.vue** (`frontend/src/molecules/VisibilityControl.vue`) — **Implementado e funcional:**
- Dropdown com 3 modos: `always`, `conditional`, `hidden`
- Construtor de condições com suporte a AND/OR (botões "+ E" e "+ OU")
- 7 operadores: `exists`, `not_exists`, `equals`, `not_equals`, `gt`, `lt`, `contains`
- Preview Knockout gerado em tempo real (ex: `<!-- ko if: campo() === 'valor' -->`)
- Integração com `multiDocStore` — ao marcar como `conditional`, registra detecção no store (Story 14.13)
- Field options populadas a partir de `mappingStore.fieldNavItems`
- Binding a campos do JSON: sim, via dropdown de `fieldPath`

**ImageInspector.vue** (`frontend/src/organisms/inspectors/ImageInspector.vue`):
- Seção Visibilidade com `VisibilityControl` integrada — implementado

**O que falta no frontend:**
- Tematização Condicional (FR30): não existe UI para definir regras de cor/imagem/logo condicional. O `VisibilityControl` cobre apenas show/hide, não variações de estilo.
- Patchamento no Canvas quando visibility muda (display:none): afetado pelo GAP 1/3 (HTMLCanvas.vue não observa mutações do templateStore — ver `docs/architecture/gap-analysis-frontend-v3.md`)
- Integração do VisibilityControl nos inspetores de nível 1 (Página) e nível 3 (Componente) — verificar se todos os inspetores hierárquicos usam o componente

---

## Backend — Status de Implementação

**baseJsGenerators.ts** (`frontend/src/stores/baseJsGenerators.ts`):
- Gera funções `quebrarTabelaEntrePaginas` e `reposicionarElementoFixo` no base.js
- Não há geração de funções de tematização condicional (cor/imagem/logo) no base.js — **lacuna**

**Stage 5** (`backend/services/stages/stage5_template_generation.py`):
- Gera classes CSS por fonte detectada e classes de cor — não condicionais
- Não há geração de lógica de tematização condicional no pipeline

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Tematização condicional (cor/imagem/logo por campo) não implementada — FR30 parcialmente coberto | 🟡 Importante | Frontend + Backend | FR30, `docs/prd-v3.md` |
| 2 | Canvas não reflete mudanças de visibility em tempo real (display:none) | 🔴 Crítico | Frontend | GAP 1/3, `docs/architecture/gap-analysis-frontend-v3.md` |
| 3 | Geração de funções de tematização no base.js ausente | 🟡 Importante | Backend | FR30 |
| 4 | Seções opcionais do multi-doc integradas com visibility rules: integração via multiDocStore existe, mas pré-preenchimento automático de condições no Inspetor não verificado | 🟢 Menor | Frontend | FR9, FR40 |
| 5 | VisibilityControl não integrado em todos os níveis do Inspetor (verificar nível 1 Página e nível 3 Componente) | 🟢 Menor | Frontend | FR39 |

---

## Backlog Gerado

1. **Implementar UI de Tematização Condicional** — Novo painel no Inspetor para regras de estilo condicional (cor de texto, cor de fundo, src de imagem) vinculadas a campos do JSON. Gerar funções correspondentes no base.js. (FR30)
2. **Conectar visibility ao Canvas** — Após resolução do GAP 1/3 (Epic 29), garantir que mudança de visibility no VisibilityControl dispare re-render do iframe e aplique `display:none` / `<!-- ko if -->` corretamente.
3. **Geração de funções de tematização no base.js** — Extender `baseJsGenerators.ts` com `generateThemingFn()` que produza funções JS para aplicação condicional de estilos.
4. **Auditoria de integração do VisibilityControl em todos os inspetores** — Verificar FieldInspector, SectionInspector e PageInspector e adicionar seção Visibilidade onde ausente.
5. **Teste de integração: multiDoc → VisibilityControl** — Garantir que campos detectados como opcionais pela Matriz de Variação sejam pré-configurados como `conditional` na árvore ao abrir o editor.

---

## Status Geral

🟡 Parcial — O construtor visual de condicionais (show/hide) está bem implementado com suporte a AND/OR e preview Knockout. A lacuna crítica é a Tematização Condicional (FR30 — variações de cor/imagem) que não possui UI nem geração no base.js. O loop de visibilidade também está quebrado pelo GAP estrutural de re-render do Canvas (Epic 29).
