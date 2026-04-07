# Epic 29 — Editor Loop Closure: Pipeline HTML + Nomes Semânticos

**Status:** Draft
**Branch:** feature/epic-29-editor-loop-closure
**Data:** 2026-04-07
**Origem:** `docs/architecture/gap-analysis-frontend-v3.md` (v3)
**Validação técnica:** @architect (Aria) — todos os gaps críticos confirmados no código
**Validação produto:** @po (Pax) — aprovado com condição (story de decisão técnica como Story 1)

---

## Problema Central

O editor tem **~88% da spec implementado**, mas os 4 gaps restantes são críticos e **quebram o loop fundamental de edição**:

| Gap | Problema | Arquivo(s) |
|-----|----------|------------|
| 1 | Editar árvore/inspector não atualiza Canvas | `generation.ts`, `templateStore.ts`, `HTMLCanvas.vue` |
| 2 | Editar HTML no Code Editor não atualiza árvore | `MonacoTabsInner.vue`, `codeStore.ts` |
| 3 | Drag/resize muda store mas Canvas não reflete | `useCanvasInteraction.ts`, `HTMLCanvas.vue` |
| 4 | Nomes genéricos na árvore ("label", "likely_dynamic") | `stage3_structural_analysis.py`, `stage5_template_generation.py` |

GAPs 1 e 3 têm **causa raiz comum**: `HTMLCanvas.vue` não observa mutações do `templateStore`. GAP 1 adiciona a ausência de geração HTML local. A solução depende de uma decisão arquitetural (Story 29.1).

---

## Epic Goal

Fechar o loop de edição do editor: qualquer mutação na árvore, inspector ou canvas deve refletir visualmente no Canvas. Nomes na árvore devem ser semânticos e legíveis pelo operador.

---

## Existing System Context

- **Frontend:** Vue 3 + Pinia — `templateStore`, `generationStore`, `codeStore`, `editorStore`
- **Canvas:** `HTMLCanvas.vue` (25KB) — watchers apenas em `generationStore.templateDraft`, `editorStore.selectedElementId`, scroll
- **Backend pipeline:** Python/FastAPI — `stage3_structural_analysis.py` (classifica nós), `stage5_template_generation.py` (gera árvore + HTML)
- **Interação atual:** Editor → `templateStore` → (sem watcher) → Canvas fica desatualizado

---

## Decisão Arquitetural Pendente (Story 29.1)

Antes de implementar GAPs 1+3, é necessário decidir a estratégia de re-render:

| Opção | Descrição | Prós | Contras |
|-------|-----------|------|---------|
| **A — Trigger Backend** | Mutação no `templateStore` → debounce → request ao backend → novo HTML | Sem lógica de geração no frontend, reutiliza engine existente | Round-trip HTTP, latência de 200-500ms, dependência de rede |
| **B — Geração Frontend** | Motor de geração HTML no frontend (spec original) | Tempo real sem latência, offline-capable | Maior investimento, duplicação de lógica backend |

**Recomendação @architect:** Opção A é mais pragmática para MVP. Opção B é a spec original mas requer sprint dedicado.

---

## Estratégia de Implementação

### Wave 1 — Core Loop (bloqueante, dependência sequencial)

```
29.1 → 29.2 → 29.3
29.1 → 29.4 (paralelo com 29.2/29.3)
```

### Wave 2 — Features (não bloqueante, pode ser paralela)

```
29.5 || 29.6
```

---

## Stories

### Wave 1 — Core Loop

#### Story 29.1 — ADR: Estratégia de Re-render do Canvas
**Prioridade:** CRÍTICA — pré-requisito para 29.2 e 29.3
**Tipo:** Decisão técnica (Architecture Decision Record)
**Escopo:**
- Avaliar Opção A (trigger backend) vs Opção B (geração frontend)
- Documentar trade-offs, impacto de escopo, complexidade
- Produzir ADR em `docs/architecture/adr-canvas-rerender-strategy.md`
- Definir interface de integração (seja qual for a opção escolhida)
**Agente:** @architect + @dev
**AC:** ADR documentado, opção escolhida com justificativa, interface definida

---

#### Story 29.2 — GAPs 1+3: Canvas Re-render via templateStore
**Prioridade:** CRÍTICA
**Depende de:** 29.1
**Escopo:**
- Adicionar watcher em `HTMLCanvas.vue` para mutações do `templateStore`
- Implementar trigger de re-render conforme decisão do ADR (29.1)
- `endDrag()` e `endResize()` em `useCanvasInteraction.ts` devem disparar re-render
- `moveNode()`, `updateNodeProperty()`, `updateNodeProperties()` no `templateStore` devem disparar re-render
**Arquivos:** `HTMLCanvas.vue`, `useCanvasInteraction.ts`, `templateStore.ts`, `generation.ts`
**AC:** Arrastar elemento → posição atualiza no Canvas. Editar propriedade no inspector → Canvas reflete. Sem flickering excessivo.

---

#### Story 29.3 — GAP 2: Code → Structure Bidirectional Sync
**Prioridade:** CRÍTICA
**Depende de:** 29.1
**Escopo:**
- Editar HTML no Monaco Editor deve atualizar `templateStore`
- Implementar parser HTML → TreeNode (ou delegar ao backend via Opção A)
- `codeStore.applyMonacoEdit()` deve triggar sincronização com `templateStore`
- Sincronização bidirecional: estrutura → código (já existe via geração) + código → estrutura (novo)
**Arquivos:** `MonacoTabsInner.vue`, `codeStore.ts`, `templateStore.ts`
**AC:** Editar tag HTML no Monaco → nó correspondente atualiza na árvore. Adicionar atributo → inspector reflete.

---

#### Story 29.4 — GAP 4: Nomes Semânticos na Árvore (Backend)
**Prioridade:** CRÍTICA
**Pode ser paralela com:** 29.2 e 29.3
**Escopo (backend):**
- `stage3_structural_analysis.py`: extrair texto real do PDF como `node.name` (ex: detectar "Cliente:" → nomear nó "Cliente")
- Renomear `likely_dynamic` para texto detectado ou nome descritivo (ex: "R$ 1.500,00" → "Valor Total")
- Dar nomes únicos a seções (ex: "Seção Dados Pessoais", "Seção Valores")
- Avaliar remoção ou achatamento do nível `page` intermediário (não está na spec)
- `stage5_template_generation.py`: garantir que `node.name` seja propagado para a árvore entregue ao frontend
- Tentativa de auto-bind semântico (proximidade de nome com campos XSD)
**Arquivos:** `stage3_structural_analysis.py`, `stage5_template_generation.py`
**Frontend:** Nenhuma mudança — `StructureTreeNode.vue:37` já está correto (`node.name || node.type`)
**AC:** Árvore do Boleto Bancário exibe "Cedente", "CNPJ", "Valor", "Vencimento" em vez de "label", "field", "likely_dynamic". Coverage > 0 após nomes corrigidos.

---

#### Story 29.7 — Canvas Patch: Cobertura Completa de Mutações
**Prioridade:** ALTA
**Depende de:** 29.2
**Escopo:**
- `borderStyleGenerator.ts`: adicionar `font_size`, `font_weight`, `color` com `!important` ao CSS injection
- `generation.ts`: `patchRemoveNode`, `patchAddNode`, `patchMoveNode`
- `templateStore.ts`: hooks em `removeNode`, `addNode`, `moveNode` + `mutationVersion.value++`
**Arquivos:** `borderStyleGenerator.ts`, `generation.ts`, `templateStore.ts`
**AC:** font/color/weight refletem no canvas. Nó removido desaparece. Nó adicionado aparece como placeholder. DOM reorganizado após moveNode.

---

### Wave 2 — Features

#### Story 29.5 — GAP 5: Console/Warnings Panel
**Prioridade:** IMPORTANTE
**Depende de:** Nenhuma (independente)
**Escopo:**
- Criar componente `ConsolePanel.vue` (nova aba no bottom panel)
- `EditorLayout.vue`: adicionar aba "Console" ao lado de TestData/TestReport
- Exibir warnings em tempo real durante edição (campos não mapeados, inconsistências)
- Reaproveitar dados de `coverageStore` e `confidenceStore` para popular o painel
**Arquivos:** `layouts/EditorLayout.vue`, novo `organisms/ConsolePanel.vue`
**AC:** Aba "Console" visível no bottom panel. Warning "Field X not mapped" aparece quando campo sem binding. Limpa ao resolver o problema.

---

#### Story 29.6 — GAP 6: Context Menu no Canvas
**Prioridade:** IMPORTANTE
**Depende de:** Nenhuma (independente)
**Escopo:**
- Adicionar handler `contextmenu` em `HTMLCanvas.vue` ou `CanvasSelectionOverlay.vue`
- Menu com opções: Map field, Convert to table, Mark as static text, Remove element
- Reaproveitar lógica do context menu existente em `StructureTree.vue`
**Arquivos:** `HTMLCanvas.vue`, `CanvasSelectionOverlay.vue`, reutilizar `StructureTree.vue`
**AC:** Clique direito no Canvas abre menu contextual. "Map field" abre FieldNavigator no campo correspondente. "Remove element" remove da árvore.

---

## Out of Scope (backlog futuro)

| Gap | Motivo |
|-----|--------|
| GAP 8 — Column guides | Minor polish, dados vazios no store |
| GAP 9 — Tab navigation Canvas | Minor UX, arrow keys já funcionam |
| GAP 10 — FileExplorer CRUD | Decisão MVP intencional |
| GAP 11 — Asset management | Upload/replace parcial, não bloqueante |

---

## Métricas de Sucesso

| Métrica | Antes | Depois |
|---------|-------|--------|
| Edição na árvore reflete no Canvas | ❌ | ✅ |
| Drag/resize visual no Canvas | ❌ | ✅ |
| Code Editor sincroniza com árvore | ❌ | ✅ |
| Nomes semânticos na árvore | ❌ ("label", "field") | ✅ ("Cliente", "Valor") |
| Coverage inicial (Boleto Bancário) | 0/66 | > 20/66 esperado |
| Console/Warnings panel | ❌ | ✅ |
| Context menu Canvas | ❌ | ✅ |

---

## Change Log

| Data | Agente | Ação |
|------|--------|------|
| 2026-04-07 | @pm (Morgan) | Epic criado — baseado em gap-analysis-frontend-v3.md, validado por @architect + @po |
| 2026-04-07 | @sm River | Story 29.7 criada — cobertura completa de patches (font/structural mutations). Story 29.4 escopo expandido com data-node-id para rect/line/image/chart |
