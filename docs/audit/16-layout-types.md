# Auditoria: Layout Types — clustering, seletor, Canvas por tipo

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**FR37** (`docs/prd-v3.md`, linha 109): O sistema deve clusterizar páginas de PDFs por similaridade de layout, criando Layout Types nomeados (ex: Capa, Transações, Resumo). O operador edita um template por Layout Type via seletor na toolbar. Ao trocar de Layout Type, a Árvore de Estrutura, o Canvas, a Confiança e a Cobertura atualizam. Cada Layout Type tem métricas independentes. O seletor é oculto quando há apenas 1 Layout Type.

**`layout_types_canvas_spec.md`**: detalha a detecção em pipeline (extração → comparação de geometria → clustering), seletor dropdown na toolbar, atualização de Canvas + PDF Reference + Structure Tree + Inspector ao trocar tipo, renderização de página representativa por cluster.

**`layout_variants_explorer.md`**: especifica o módulo Layout Variants Explorer (painel esquerdo) para análise de múltiplos PDFs, fingerprinting estrutural, detecção de campos opcionais/condicionais, e merge de variantes em template unificado.

---

## Frontend — Status de Implementação

**Componentes existentes:**

- `/home/user/migrador-planet/frontend/src/stores/layout.ts` — store `useLayoutStore` com `layoutTypes: LayoutType[]`, `activeLayoutId`, `layoutStates` (per-layout transient state, Story 12.9). Action `setActiveLayout()` preserva estado do layout atual, troca para o novo, restaura templateStore + confidenceStore + coverageStore + inspectorStore + editorStore zoom. Action `syncActiveLayoutFromScroll()` sincroniza ativo via scroll do Canvas.
- `/home/user/migrador-planet/frontend/src/molecules/LayoutSelector.vue` — dropdown que lista `lt.name (N pgs em M docs)`, oculto quando `layoutTypes.length <= 1` via `v-show`, chama `setActiveLayout()` no change.
- `/home/user/migrador-planet/frontend/src/organisms/TopToolbar.vue` — integra `<LayoutSelector />` condicionalmente (separador `v-if="layoutStore.layoutTypes.length > 1"`), exibe Confidence e Coverage badges com popover, toggles Cobertura/Diff/Snap, Auto Fix, Salvar, Exportar.

**O que funciona:**
- Seletor de Layout Type na toolbar com visibilidade condicional (FR37).
- Ao trocar Layout Type: templateStore, confidenceStore, coverageStore, inspectorStore e zoom atualizam (FR37 — Canvas/Tree/Inspector/Confidence/Coverage por layout).
- Per-layout transient state preservado (Story 12.9): nó selecionado, zoom, campo selecionado.
- Coverage e Confidence por Layout Type via `activeLayoutCoverage` e `overallForActiveLayout`.
- Persistência em IndexedDB (`hydrateFromIdb` / `persistToIdb`).

**O que falta:**
- Layout Variants Explorer (painel esquerdo, `layout_variants_explorer.md`): módulo de comparação visual de variantes, merge de layouts, campo opcional/condicional via interface visual — não encontrado nenhum componente implementado.
- Nomes de Layout Types são gerados automaticamente pelo backend (letras A/B/C/…, linhas 1237-1241 de `stage1_layout_clustering.py`); não há campo editável no frontend para renomear o tipo detectado.
- Canvas scrolling to layout section (`pendingScrollToLayout`) está preparado no store mas a implementação no componente Canvas não foi auditada.

---

## Backend — Status de Implementação

**Stage 1** (`/home/user/migrador-planet/backend/services/stages/stage1_layout_clustering.py`):

- Clustering via `fcluster` (hierárquico, `scipy`) com threshold configurável (padrão 0.85). Não usa silhouette score — usa `ClusteringConfig.clustering_threshold` com distância de Ward.
- 3 camadas de defesa: Prevention (steps 1.1–1.9), Detection (1.10–1.13), Correction (1.14–1.15) + Homogeneity Check (1.16).
- Step 1.9: `_select_representatives()` — seleciona página representativa por cluster via "weighted degree" (nó mais conectado no grafo de similaridade), não por silhouette score.
- Step 1.12: `_validate_representatives()` — valida que a página representativa de fato representa o cluster.
- Nomes de Layout Types: gerados automaticamente como letras sequenciais (A, B, C… ou C0, C1…), linhas 1237–1241. Não há sistema de naming configurável nem sugestão por IA.
- Layout Fingerprint / Registry: **não implementado**. Não há mecanismo de reutilização de templates conhecidos.

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Layout Variants Explorer não implementado (painel de comparação visual de variantes, merge de layouts, campos opcionais/condicionais via UI) | 🟡 Importante | Frontend | `layout_variants_explorer.md` |
| 2 | Nomes dos Layout Types são gerados automaticamente (A/B/C) sem possibilidade de renomeação pelo operador no frontend | 🟡 Importante | Frontend + Backend | FR37, `layout_types_canvas_spec.md` seção 3 |
| 3 | Layout Fingerprint / Registry (reutilização de templates conhecidos) não implementado | 🟡 Importante | Backend | `layout_variants_explorer.md` (Structural Fingerprinting) |
| 4 | Clustering usa distância hierárquica (Ward/fcluster), não silhouette score — spec menciona silhouette mas implementação usa threshold fixo | 🟢 Menor | Backend | `layout_types_canvas_spec.md` seção 2, `ClusteringConfig` |
| 5 | Canvas scroll-to-layout via `pendingScrollToLayout` — implementação no componente Canvas não verificada | 🟢 Menor | Frontend | `layout.ts` linha 184 |

---

## Backlog Gerado

1. **Layout Type renaming**: Adicionar campo editável no LayoutSelector ou no Inspector de Page para renomear o Layout Type detectado; persistir nome customizado no layoutStore e no backend output.
2. **Layout Variants Explorer**: Implementar painel esquerdo (nova aba na estrutura) mostrando clusters lado a lado, diferenças destacadas, ações "Marcar como Opcional", "Criar Condição", "Mesclar Layouts".
3. **Layout Fingerprint / Registry**: Backend — criar hash estrutural do cluster e comparar com banco de templates conhecidos; surfacear no frontend como sugestão de template pré-existente.
4. **Verificar pendingScrollToLayout no Canvas**: Confirmar que o componente Canvas lê e aplica `pendingScrollToLayout` e chama `clearScrollTarget()` após o scroll.

---

## Status Geral

🟡 Parcial — A funcionalidade central (clustering, seletor na toolbar, troca de Canvas/Tree/Confidence/Coverage por Layout Type) está implementada e funcional. Faltam o Layout Variants Explorer (UX de comparação de variantes), renomeação de Layout Types pelo operador, e o Layout Fingerprint/Registry.
