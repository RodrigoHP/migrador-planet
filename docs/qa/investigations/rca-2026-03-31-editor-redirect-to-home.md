# RCA: Botão "Abrir no Editor" redireciona para Home

**ID:** rca-2026-03-31-editor-redirect-to-home
**Data:** 2026-03-31
**Investigador:** @qa (Quinn)
**Severidade:** High
**Status:** Resolvido

---

## Sintoma

Ao clicar em "Abrir no Editor" após análise concluída, o browser navega para `/editor` mas é imediatamente redirecionado para `/` (home) em vez de abrir o editor.

## Classificação

| Dimensão | Valor |
|----------|-------|
| Cynefin | Complicated |
| Severidade | High |
| Scope | Cross-module (Stage 3 → Stage 5 → session store → router guard) |
| Dedup | NEW |

---

## Root Cause (E1 — Confirmed)

**Cadeia causal completa:**

```
Botão "Abrir no Editor" → handleOpenEditor() → fetchAndLoadResult()
  → await session.loadFromPipelineResult(data.result)
    → templateStore loader: loadTree(result.document_structure)
      → buildFlatMap(tree.root, map)
        → leaf node sem chave 'children' → TypeError: undefined is not iterable
  → catch(e) → this.error = "..." → return  [analysisCompleted permanece false]
  → router.push('/editor')  [chamado incondicionalmente]
  → guard: session.analysisCompleted !== true → redirect { name: 'home' }
```

**Causa raiz primária:** `_convert_tree_to_css_coords` (Stage 5) não garante `children: []` para nós folha que não possuem a chave `children`. Nós `cell`, `image`, `chart`, `barcode` criados no Stage 3 são gerados sem a chave `children`. Após conversão, esses nós chegam ao frontend sem `children`, causando `TypeError` em `buildFlatMap`.

**Causa raiz ativadora:** Commit `4b6be4c` (fix editor vazio) tornou `document_structure.root` disponível no resultado flat, fazendo `loadTree()` ser chamado pela primeira vez e expondo o bug latente em `buildFlatMap`.

**Contributing factors:**
- `buildFlatMap` itera `node.children` sem guard `?? []`
- `applyOptionalVisibility` e `applyTableCellFlags` têm o mesmo problema
- `fetchAndLoadResult` chama `router.push('/editor')` sem verificar se `loadFromPipelineResult` teve sucesso

---

## Fix Aplicado

### 1. Origem (backend) — `_convert_tree_to_css_coords`
```python
# Antes: nós folha sem children key
children = tree.get("children", [])
if children:
    result["children"] = [_convert_tree_to_css_coords(child, layout) for child in children]
# result ficava sem chave 'children' para nós folha

# Depois: children: [] garantido em todo nó
elif "children" not in result:
    result["children"] = []
```

### 2. Guards defensivos (frontend)
- `buildFlatMap`: `for (const child of (node.children ?? []))`
- `applyOptionalVisibility`: mesmo guard
- `applyTableCellFlags` (2 iterações): mesmo guard

### 3. Defense-in-depth (navegação)
`fetchAndLoadResult` agora verifica `session.error` após `loadFromPipelineResult` — exibe erro no lugar de navegar para o editor (que seria rejeitado pelo guard de qualquer forma).

---

## Testes Criados

- `test_stage5_template_generation.py::TestConvertTreeToCssCoords` (5 testes)
  - `test_leaf_node_without_children_key_gets_empty_children` — reproduz o bug original
  - `test_leaf_node_with_empty_children_keeps_empty_children`
  - `test_image_node_without_children_gets_empty_children`
  - `test_parent_node_children_are_converted_recursively`
  - `test_bbox_coords_converted_to_css_pixels`

---

## Barrier Analysis

| Camada | Status | Criticality | Contrafactual |
|--------|--------|-------------|---------------|
| Code Level | absent | HIGH | `?? []` em `buildFlatMap` teria prevenido o crash sozinho |
| Test Level | absent | HIGH | Teste com leaf node sem children teria detectado na CI |
| Static Analysis | worked (parcial) | LOW | TypeScript declara `children` required mas não enforça em runtime |
| CI/CD Level | absent | MEDIUM | Integration test com resultado real teria detectado |
| Monitoring | absent | MEDIUM | Error tracking no store loader alertaria antes do usuário |
| Process Level | failed | MEDIUM | Code review de 4b6be4c não verificou `buildFlatMap` com novo resultado |

**Fix This First:** Code Level [HIGH] → Test Level [HIGH] → CI/CD [MEDIUM] → Process [MEDIUM]

---

## Escalação

**@ARCHITECT RECOMENDADA** — scope amplo (5 módulos), 4+ barreiras falhadas.
Sugestão: avaliar schema validation de `TreeNode.children` no orchestrator antes de persistir.

---

## Achados Colaterais (Backlog)

| ID | Tipo | Severidade | Descrição | Localização |
|----|------|-----------|-----------|-------------|
| F-1 | improvement | MEDIUM | Stage 3 tree builder cria nós folha sem `children: []` — contrato inconsistente | stage3:1316,1321,1327,1337,1348 |
| F-2 | improvement | MEDIUM | `fetchAndLoadResult` não reporta erro quando `loadFromPipelineResult` retorna sem carregar | AnalyzingPage.vue:670-673 (melhorar mensagem) |

---

## Anti-Pattern

**AP-007** registrado: `null_children_tree_node` — ver `known-anti-patterns.md`.

---

## Evidence Summary

| # | Claim | Level | Confidence |
|---|-------|-------|------------|
| 1 | Stage 3 cria nós sem `children` | E1_confirmed | 0.99 |
| 2 | `_convert_tree_to_css_coords` não garante `children: []` | E1_confirmed | 0.99 |
| 3 | `buildFlatMap` sem guard → TypeError | E1_confirmed | 0.99 |
| 4 | `loadFromPipelineResult` retorna sem `analysisCompleted = true` | E1_confirmed | 0.99 |
| 5 | `fetchAndLoadResult` navega incondicionalmente | E1_confirmed | 0.99 |
| 6 | Guard do router redireciona para home | E1_confirmed | 0.99 |
| 7 | Bug ativado pelo commit 4b6be4c | E2_correlated | 0.85 |
