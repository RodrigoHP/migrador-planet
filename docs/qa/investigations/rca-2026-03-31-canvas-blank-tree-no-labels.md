# RCA Report: rca-2026-03-31-canvas-blank-tree-no-labels

## 1. Classificação
- **Domínio:** Complicated (dois bugs distintos, causa-efeito requer análise de pipeline)
- **Severidade:** High (editor inutilizável — canvas em branco + árvore sem labels)
- **Scope:** Multi-file (stage5 backend + StructureTreeNode frontend + useCanvas frontend)
- **Dedup:** new

## 2. Problema Reportado
Após análise de PDF Boleto Bancário concluída com sucesso, o editor exibia dois problemas:
- **Bug 1:** Árvore de estrutura (sidebar) mostrava ícones mas SEM TEXTO nos nós
- **Bug 2:** Canvas completamente em branco — documento não renderizava

## 3. Causa Raiz

### Bug 1 — Tree sem labels (E1_confirmed)
`StructureTreeNode.vue` linha 37: `{{ node.name }}` — mas `stage3._build_tree` nunca popula
o campo `name` nos nós da árvore. Nós têm `type`, `text`, `block_id`, `variant` mas NÃO `name`.
Resultado: `node.name === undefined` → span renderiza vazio, apenas ícone visível.

```vue
<!-- ANTES: -->
<span class="structure-tree-node__name">{{ node.name }}</span>

<!-- DEPOIS: -->
<span class="structure-tree-node__name">{{ node.name || node.text || node.type }}</span>
```

### Bug 2 — Canvas em branco (E1_confirmed)
`stage5._tree_to_html` branch `else` (linha 211-219): blocos standalone (não-pareados)
retornavam `""` porque o código só recursava filhos — mas blocos standalone NÃO TÊM filhos,
apenas campo `text`. Isso afetava todos os blocos não classificados como label+value pair:
headers, títulos, parágrafos, labels standalone, valores standalone.

```python
# ANTES — blocos standalone silenciosamente descartados:
else:
    if children:
        return "\n".join(_tree_to_html(c, ...) for c in children)
    return ""  # ← blocos com text mas sem children → descartados!

# DEPOIS — renderiza como span:
else:
    if children:
        return "\n".join(_tree_to_html(c, ...) for c in children)
    text = node.get("text", "")
    block_id = node.get("block_id", "")
    if text or block_id:
        node_id = block_id or f"{node_type}-{id(node)}"
        return f'{pad}<span data-node-id="{node_id}" data-type="{node_type}">{text}</span>'
    return ""
```

### Bug 3 (colateral) — Observer attribute mismatch
`useCanvas.ts` linha 54: `dataset.page` mas elemento `.html-canvas__page-wrapper` tem
`data-page-wrapper`. Observer nunca disparava corretamente. Compensado por seeding manual
em `onMounted` e `watch`, mas prejudica documentos multi-página.

```typescript
// ANTES:
const pageNum = Number((entry.target as HTMLElement).dataset.page)
// DEPOIS:
const pageNum = Number((entry.target as HTMLElement).dataset.pageWrapper)
```

## 4. Fixes Aplicados

| Arquivo | Mudança |
|---------|---------|
| `frontend/src/molecules/StructureTreeNode.vue:37` | Fallback `node.name \|\| node.text \|\| node.type` |
| `backend/services/stages/stage5_template_generation.py:211` | Render standalone blocks como `<span>` |
| `frontend/src/composables/useCanvas.ts:54` | `dataset.page` → `dataset.pageWrapper` |

## 5. Testes
- Backend: 46/46 testes stage5 passando (fix compatível com todos)
- Frontend: 220/220 testes frontend passando

## 6. Barrier Analysis
| Camada | Status | Criticality | Contrafactual |
|--------|--------|-------------|---------------|
| Code Level (stage5) | absent | HIGH | Teste com bloco standalone sem children teria detectado |
| Code Level (frontend) | absent | HIGH | Teste de renderização do tree com node sem name teria detectado |
| Code Review | absent | MEDIUM | Review da PR do Epic 13 teria identificado o return "" |

**Fix This First:** Testes unitários — ambos os bugs teriam sido detectados com testes simples.

## 7. Pipeline Metrics
```yaml
preset: adaptive:complicated (inline — fase 0 e investigação manual)
phases_executed: [0, 1, 2, 3, 8]
phases_parallel: []
estimated_cost: ~$0.00 (inline)
```
