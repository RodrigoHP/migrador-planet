# Auditoria: Layer Panel + Console/Warnings

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**Layer Panel** — Painel de camadas com lista de elementos ordenados por z-order, drag para reordenar, toggle de visibilidade e lock/unlock por camada. Referência: `docs/wireframes/wireframes-mid-fi.md` painel esquerdo; `docs/ideias/ux/template_editor_main_screen_spec.md`.

**Console/Warnings** — Painel inferior com avisos de campos não mapeados, warnings do backend em tempo real, filtros por categoria e export de log. Referência:
- `docs/ideias/ux/template_editor_main_screen_spec.md` seção 8
- `docs/architecture/gap-analysis-frontend-v3.md` GAP 5
- `docs/stories/epic-29-editor-loop-closure.md` Story 29.5
- `docs/stories/backlog/backlog-epic29-scope-out.md` itens 30.5 e 30.8

---

## Frontend — Status de Implementação

### LayerPanel.vue (`frontend/src/organisms/LayerPanel.vue`)

**Implementado:**
- Lista de camadas ordenadas por z-index (`orderedLayers` de `useLayerOrder`)
- Ícones por tipo (`field`, `section`, `table`, `chart`, `image`)
- Seleção de camada com highlight visual e borda primária
- Botões de reordenação: Bring to Front (⬆⬆), Move Up (⬆), Move Down (⬇), Send to Back (⬇⬇)
- Suporte a grupos: botões Group/Ungroup (integra `useGrouping`)
- Navegação por teclado (ArrowUp/Down para selecionar, Alt+ArrowUp/Down para mover)
- Anúncios de acessibilidade via `aria-live`

**Não implementado:**
- **Toggle de visibilidade por camada** — o template não exibe ícone de olho para mostrar/ocultar camada individualmente; `layer.id === selectedId` é o único estado visual
- **Lock/unlock por camada** — não há botão ou ícone de cadeado; sem estado `locked` no layer model
- **Drag & drop direto na lista** — reordenação é feita apenas pelos botões da toolbar, não arrastando rows

### ConsolePanel.vue (`frontend/src/organisms/ConsolePanel.vue`)

**Implementado:**
- Warnings de campos não mapeados: itera `templateStore.flatNodes`, filtra por `BINDABLE_TYPES` (`field`, `value`, `likely_dynamic`, `dynamic`), gera warning para nodes sem `binding`
- Integração com `confidenceStore.backendWarnings` (Story 30.5): backend warnings exibidos junto com warnings locais
- Filtros por categoria (Story 30.8): chips "Todos", "Não mapeado", "Tabela", "Confiança"
- Export de log JSON (Story 30.8): botão "↓ JSON" gera download de `warnings.json`
- Dismiss por item (botão ✕)
- Clique em warning com `nodeId` seleciona elemento no editor
- Integração com `confidenceStore` (backendWarnings)

**Não implementado / limitações:**
- Filtros cobrem apenas 3 categorias além de "Todos" — categorias como `chart_missing`, `table_inconsistent`, `low_confidence` dependem do backend popular `backendWarnings` com as categorias corretas
- Não há integração direta com `coverageStore` — warnings de cobertura não gerados localmente
- Warning `table_inconsistent` nos chips mas sem geração automática local (depende de backend warning)

---

## Backend — Status de Implementação

**confidenceStore.ts** (`frontend/src/stores/confidenceStore.ts`):
- `backendWarnings: BackendWarning[]` armazenados no store
- `setBackendWarnings()` e `clearBackendWarnings()` actions disponíveis
- Integrado ao ConsolePanel — dados fluem corretamente quando populados

**O que falta no backend:**
- O pipeline não confirma quando e como `setBackendWarnings()` é chamado com dados reais — a ponte WebSocket/SSE entre pipeline e store não está documentada no código auditado
- Categorias dos warnings de backend precisam mapear às categorias do chip filter (`missing_binding`, `table_inconsistent`, `low_confidence`)

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | LayerPanel sem toggle de visibilidade por camada (ícone de olho) | 🟡 Importante | Frontend | wireframes-mid-fi.md, template_editor_main_screen_spec.md |
| 2 | LayerPanel sem lock/unlock por camada | 🟡 Importante | Frontend | template_editor_main_screen_spec.md |
| 3 | LayerPanel sem drag & drop para reordenar (apenas botões) | 🟢 Menor | Frontend | wireframes-mid-fi.md |
| 4 | ConsolePanel: warnings `table_inconsistent` e `low_confidence` dependem exclusivamente de backendWarnings — não gerados localmente | 🟢 Menor | Frontend | gap-analysis-frontend-v3.md GAP 5 |
| 5 | Integração ConsolePanel ↔ coverageStore não implementada — warnings de cobertura não exibidos | 🟡 Importante | Frontend | backlog-epic29-scope-out.md 30.5 |
| 6 | Ponte pipeline → backendWarnings (WebSocket/SSE) não auditada — pode não estar operacional | 🟡 Importante | Backend | Story 29.5, 30.5 |

---

## Backlog Gerado

1. **Toggle de visibilidade por camada** — Adicionar ícone de olho (👁) em cada item do LayerPanel que alterne `visibility: hidden` no elemento via `templateStore.updateNodeProperty`.
2. **Lock/unlock por camada** — Adicionar ícone de cadeado (🔒) em cada item do LayerPanel; estado `locked` deve bloquear interação no Canvas (drag, resize, select).
3. **Drag & drop no LayerPanel** — Implementar reordenação por drag usando HTML5 drag API ou VueDraggable.
4. **Geração local de warnings `table_inconsistent`** — ConsolePanel deve inspecionar nós do tipo `table` no templateStore e gerar warnings quando sem `dataSource` binding.
5. **Integração ConsolePanel ↔ coverageStore** — Gerar warning automático quando `coverageStore.activeLayoutCoverage.percentage < 80`.
6. **Auditoria da ponte pipeline → backendWarnings** — Verificar se SSE/WebSocket do pipeline popula `setBackendWarnings()` em tempo real durante o analyzing e/ou após abertura do editor.

---

## Status Geral

🟡 Parcial — O ConsolePanel está bem implementado com filtros, export e integração com backendWarnings (Stories 30.5/30.8 entregues). O LayerPanel cobre reordenação por z-index e agrupamento, mas falta os controles de visibilidade e lock por camada especificados nos wireframes. A ponte backend → warnings em tempo real não está confirmada como operacional.
