# Auditoria: Árvore de Estrutura

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**FR38** (`docs/prd-v3.md` linha 113): O painel esquerdo (aba Estrutura) deve exibir a hierarquia do documento como template: `Document > Header > Flow > Footer > elementos`. Cada nó exibe ícone de tipo (📄 Document, 📦 Seção, 🔤 Texto, 📋 Tabela, 📊 Gráfico, 🖼 Imagem), nome semântico e binding (ex: `→ {{cliente}}`). Elementos opcionais marcados com ⚠. Clicar seleciona no Canvas e abre Inspetor. Drag & drop reordena. Clique direito abre menu contextual (adicionar, agrupar, duplicar, remover, mover entre seções). Cada Layout Type tem sua própria árvore.

**Wireframe** (`docs/wireframes/wireframes-mid-fi.md` linhas 449-481): hierarquia visual mostrando `📄 Document > 📦 Header > 🖼 Logo / 🔤 Cliente → {{cliente}} / 🔤 CPF → {{cpf}}` etc., com bindings ao lado do nome e ícones corretos por tipo.

**Spec UX** (`docs/ideias/ux/template_structure_view_spec.md`): define ícones por tipo (📄 Document, 📦 Container, 🔤 Text, 📋 Table, 📊 Chart, 🖼 Image), binding display (`Cliente → {{cliente}}`), drag-and-drop para reordenação, anchor visualization, optional element indicators, e integração com Canvas/Inspector.

**GAP 4** (`docs/architecture/gap-analysis-frontend-v3.md` linhas 91-156): nomes genéricos na árvore — screenshot real de "Boleto Bancário" mostra `label`, `field`, `likely_dynamic`, `section` em vez de nomes semânticos. 0/66 campos mapeados.

**Story 29.4** (`docs/stories/epic-29-editor-loop-closure.md` linhas 115-128): implementar `_extract_semantic_name()` e `_infer_section_name()` no backend para extrair texto real do PDF como `node.name`, humanizar `likely_dynamic`, dar nomes únicos a seções. Frontend não precisa de mudanças.

---

## Frontend — Status de Implementação

### StructureTree.vue
**Arquivo:** `frontend/src/organisms/StructureTree.vue`

Implementado e funcional:
- Renderiza a árvore recursivamente via `StructureTreeNode.vue`
- Expansão/colapso de nós com estado `expandedNodes` (Set)
- Seleção sincronizada: `handleSelect()` chama `inspectorStore.selectNode(node)` e `editorStore.selectElement(node.id)` — seleção na árvore abre Inspector e seleciona no Canvas
- Watch em `inspectorStore.selectedNode` para sincronizar seleção reversa (Canvas → árvore)
- Watch em `layoutStore.activeLayoutId` — reset de seleção ao trocar Layout Type
- **Drag & drop para reordenar**: `handleDropNode()` chama `templateStore.moveNode()` com posição before/after/inside
- **Context menu completo**: adicionar elemento (subMenu por tipo), agrupar em seção, duplicar, mover para Header/Flow/Footer, remover binding, remover
- Drop de campo (do FieldNavigator) com confirmação ao substituir binding existente
- Diálogo de confirmação para remoção de nós com filhos

### StructureTreeNode.vue
**Arquivo:** `frontend/src/molecules/StructureTreeNode.vue`

Implementado e funcional:
- Exibe ícone por tipo via `typeIcons` map (linha 123-140): 📄 document, 📦 section/header/footer/flow/container, 🔤 text/label/value/dynamic, 📋 table, 📊 chart, 🖼 image
- Nome: `{{ node.name || node.type }}` (linha 37) — correto, fallback para type
- Badge de status de binding (🟢/🔴/🟡) para nós bindable (text, field, value, likely_dynamic, dynamic)
- Texto do binding ao lado: `truncatedBinding` (max 20 chars) em indigo
- Coverage mini-bar para containers (X/Y bound com barra verde)
- Badge ⚠ para elementos opcionais (`node.isOptional`)
- Drag & drop emite eventos para StructureTree.vue

**Gaps no frontend:**
- Ícone `field` usa literal `'abc'` em vez de emoji — não é ícone visual correto
- Ícone `likely_dynamic` usa `'~'` — sem emoji, apenas símbolo
- Ícone `barcode` usa `'|||'` — sem emoji
- Binding exibido como texto monospace, não no formato `→ {{campo}}` especificado (exibe só o path, sem seta e chaves)

---

## Backend — Status de Implementação

### stage3_structural_analysis.py
**Arquivo:** `backend/services/stages/stage3_structural_analysis.py`

Implementado (Story 29.4 — status: Done):
- `_extract_semantic_name(block)` (linha 1341): extrai texto real do PDF, remove pontuação trailing, trunca a 50 chars
- `_infer_section_name(section_blocks, block_classifications)` (linha 1357): usa primeiro filho `label` para formar "Seção {label_text}"
- `_build_tree()` (linha 1373): aplica nomes semânticos a nós `label` (linha 1449), `field` (linha 1482), standalone blocks incluindo `likely_dynamic` (linha 1501), seções (linha 1408)
- Classificação `likely_dynamic` existe (linha 204) mas recebe nome do texto real via `_extract_semantic_name`

**Não implementado — auto-bind semântico:**
- Story 29.4 menciona "auto-bind semântico com campos XSD (best-effort, não é AC bloqueante)" — busca por padrão de proximidade semântica entre `node.name` e campo XSD não foi encontrada no código de stage3. Nenhuma função `auto_bind`, `suggested_binding` ou similar existe em stage3.

**Nível "page" intermediário:**
- A árvore ainda tem o nível `page` intermediário: `root > page > zones/sections > fields` (linha 1382-1388). Story 29.4 AC4 decidiu manter por compatibilidade com paginação no frontend (`_convert_tree_to_css_coords` em stage5).

### stage5_template_generation.py
**Arquivo:** `backend/services/stages/stage5_template_generation.py`

- Propagação de `name`: stage5 usa `result = dict(tree)` para conversão de coordenadas — o campo `name` é preservado automaticamente (confirmado em Story 29.4 linhas 198-205)
- `data-node-id` adicionado em rect/line/image/chart/barcode conforme Story 29.4

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Nível `page` intermediário não previsto na spec (`Document > page > Header/Flow/Footer` vs `Document > Header/Flow/Footer`) | 🟡 Importante | Backend (stage3) | FR38, gap-analysis-frontend-v3.md GAP 4 |
| 2 | Auto-bind semântico não implementado — proximidade de nome com campo XSD não ocorre em stage3 | 🟡 Importante | Backend (stage3) | Story 29.4 scope, epic-29 Story 29.4 |
| 3 | Ícones de `field`, `likely_dynamic`, `barcode` usam caracteres ASCII (`abc`, `~`, `|||`) em vez de emoji ou ícone visual | 🟢 Menor | Frontend (StructureTreeNode.vue) | wireframes-mid-fi.md linha 470, template_structure_view_spec.md seção Icons |
| 4 | Binding exibido como path simples em vez de `→ {{campo}}` conforme wireframe | 🟢 Menor | Frontend (StructureTreeNode.vue linha 48) | wireframes-mid-fi.md linha 457, template_structure_view_spec.md seção Binding Display |
| 5 | Coverage por nó sem código de cor (verde/vermelho/amarelo) — mini-bar só tem barra verde, sem estado vermelho/amarelo | 🟢 Menor | Frontend (StructureTreeNode.vue) | prd-v3.md FR38 implícito via cobertura |
| 6 | Context menu na árvore não tem opção "Renomear" (rename) | 🟢 Menor | Frontend (StructureTree.vue) | prd-v3.md FR38 "menu contextual" |

---

## Backlog Gerado

1. **Remover ou aplanar nível `page` intermediário no stage3** — avaliar impacto em paginação frontend (`usePagination.ts`, `HTMLCanvas.vue`) e decidir se é seguro aplanar para conformar com spec `Document > Header/Flow/Footer`. Documentar ADR se mantido.

2. **Implementar auto-bind semântico em stage3** — após extração de `node.name`, tentar match por similaridade com campos do XSD (Levenshtein ou normalização de strings). Salvar como `suggested_binding` no nó. Frontend pode usar para pré-popular binding sem confirmação obrigatória.

3. **Corrigir ícones de `field`, `likely_dynamic`, `barcode` no StructureTreeNode.vue** — substituir `'abc'`, `'~'`, `'|||'` por emojis adequados (🔤 ou 📝 para field, 🔀 para likely_dynamic, 📊 para barcode).

4. **Formatar binding como `→ {{campo}}`** — em `StructureTreeNode.vue`, alterar `truncatedBinding` para formatar como `→ {{${b}}}` conforme wireframe.

5. **Adicionar opção "Renomear" no context menu da árvore** — permitir que operador corrija nome de nó via inline editing ou modal.

---

## Status Geral

🟡 Parcial — A estrutura fundamental da árvore está implementada (ícones, expansão/colapso, drag-drop, context menu, seleção sincronizada com Inspector). O GAP crítico de nomes genéricos foi parcialmente resolvido pela Story 29.4 (backend extrai nomes semânticos), mas o nível `page` intermediário persiste e o auto-bind semântico não foi implementado, deixando coverage em estado subótimo.
