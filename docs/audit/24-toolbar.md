# Auditoria: Toolbar Principal (TopToolbar)

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**FR29** — Percentual de cobertura exibido na toolbar, clicável para popover com breakdown por tipo.

**FR33** — Pontuação de confiança na toolbar, clicável para popover com breakdown de 5 fatores.

**FR34** — Botão "🔧 Auto Fix" na toolbar para correção assistida por IA.

**FR37** — Seletor de Layout Type na toolbar; oculto quando apenas 1 layout detectado.

**FR41** — Toggle "Diff Mode" na toolbar.

**FR7** — Guias visuais (margens, limites Header/Flow/Footer, colunas, snap lines) controláveis; zoom 50–125%.

**FR10** — Botão 💾 Salvar na toolbar.

**FR20** — Botão 📦 Exportar na toolbar → ZIP direto.

Fonte: `docs/prd-v3.md` FR7, FR10, FR20, FR29, FR33, FR34, FR37, FR41.

---

## Frontend — Status de Implementação

**TopToolbar.vue** (`frontend/src/organisms/TopToolbar.vue`) — **Implementado:**

| Elemento | Status |
|----------|--------|
| Template name / doc type badge | ✅ |
| ConfidenceBadgeMetric + popover | ✅ |
| CoverageBadge + popover | ✅ |
| LayoutSelector (oculto quando 1 layout) | ✅ |
| Toggle Cobertura | ✅ |
| Toggle Diff | ✅ |
| Toggle Snap | ✅ |
| Botão Auto Fix (com limite de sessão) | ✅ |
| Botão Salvar (serializa SavedProjectV2 como JSON) | ✅ |
| Botão Exportar (modal para datasets + validação pré-export) | ✅ |
| ExportValidationModal (erros bloqueantes + warnings) | ✅ |

**AlignmentToolbar.vue** (`frontend/src/molecules/AlignmentToolbar.vue`) — componente de alinhamento de elementos, separado da TopToolbar. Fora do escopo de FR da toolbar principal.

**O que falta no frontend:**
- Toggle "Guias Visuais" (Show Guides) não está exposto na TopToolbar — `editorStore.showGuides` existe mas não há botão na toolbar.
- Zoom control ausente na TopToolbar — o ZoomControls.vue existe mas está posicionado na footer do Canvas (não confirmado se exibido na toolbar conforme FR7).
- Nenhuma indicação de status de sessão (ex: "não salvo" / dirty state badge).

---

## Backend — Status de Implementação

A toolbar é puramente frontend — sem dependências diretas de backend. Os dados exibidos (confiança, cobertura, layout types) são alimentados por stores Pinia que consomem dados do pipeline de análise. Nenhum gap de backend específico desta funcionalidade.

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Toggle "Guias Visuais" ausente da toolbar — `showGuides` existe na store mas sem controle UI na TopToolbar | 🟡 Importante | Frontend | FR7 |
| 2 | Zoom controls não estão na TopToolbar — ZoomControls usa useCanvas mas posicionamento na toolbar não confirmado | 🟡 Importante | Frontend | FR7 |
| 3 | Nenhum indicador visual de dirty state ("projeto não salvo") | 🟢 Menor | Frontend | FR10 |
| 4 | Auto Fix não tem limite visível restante (apenas desabilita ao atingir limite, sem contador) | 🟢 Menor | Frontend | FR34 |

---

## Backlog Gerado

1. **Toggle "Mostrar Guias" na TopToolbar** — Adicionar botão ao grupo de toggles que liga/desliga `editorStore.showGuides`. Ícone de régua ou grade.
2. **Mover ZoomControls para a TopToolbar** — Verificar posicionamento atual do ZoomControls.vue e integrar à seção direita da toolbar conforme FR7 (zoom 50–125%).
3. **Dirty state badge** — Detectar mudanças não salvas e exibir indicador visual próximo ao botão Salvar (ex: ponto laranja ou texto "• não salvo").
4. **Contador de Auto Fix** — Exibir "X/N usos restantes" no botão ou tooltip do Auto Fix.

---

## Status Geral

🟡 Parcial — A toolbar principal está bem implementada com todos os elementos críticos (confiança, cobertura, layout selector, toggles, ações). Os gaps restantes são controles ausentes (guias visuais, zoom) e melhorias de UX (dirty state, contador auto fix) — sem impacto em funcionalidade core.
