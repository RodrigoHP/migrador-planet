---
id: backlog-editor-redirect-to-home-1
title: "Garantir children: [] em todos os nós folha do Stage 3"
type: improvement
status: Draft
priority: medium
source_rca: "rca-2026-03-31-editor-redirect-to-home"
source_finding: "F-1"
---

# Backlog — Garantir children: [] em nós folha do Stage 3

## Origem
Achado colateral da investigação [rca-2026-03-31-editor-redirect-to-home](../investigations/rca-2026-03-31-editor-redirect-to-home.md).

## Descrição
O Stage 3 cria nós folha (`cell`, `image`, `chart`, `barcode`) sem a chave `children`. O fix atual em `_convert_tree_to_css_coords` (Stage 5) corrige o sintoma, mas a raiz está no Stage 3. Nós sem `children` são um contrato inconsistente que pode causar bugs em outros consumidores da árvore.

## Localização
`backend/services/stages/stage3_structural_analysis.py` linhas 1316, 1321, 1327, 1337, 1348

## Ação Sugerida
Adicionar `"children": []` explícito em todos os nós folha criados no Stage 3. Adicionar teste de contrato que valida que todo nó da árvore tem a chave `children`.

## Prioridade
MEDIUM — o sintoma está resolvido pelo fix no Stage 5, mas a origem permanece inconsistente.

## Notas
Este draft foi auto-gerado pela Fase 8 do `/investigate`.
Requer validação por @po antes de entrar no backlog oficial.
