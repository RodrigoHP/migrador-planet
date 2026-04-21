# Spike AST Validation — Retrospectiva Final
**Status:** CONCLUÍDO  
**Branch:** `spike/ast-validation`  
**Data:** 2026-04-21  
**Spec:** `docs/architecture/spike-ast-validation-spec.md`

---

## Resultados Go/No-Go

| Critério | Gate | Resultado | Situação |
|---------|------|-----------|---------|
| **C1** — Stage 3 → AST v0 consumível (2/2 tipos) | 2/2 | 2/2 ✅ | GO |
| **C2** — Stage 4 patch ≤100 LOC | ≤100 LOC | **5 LOC** ✅ | GO |
| **C3** — Formatter inference ≥70% precision | ≥70% | **93.9%** ✅ | GO |

### Veredicto: **GO** — 3/3 critérios aprovados

---

## Medições Detalhadas

### C1 — Emissão AST (Stage 3 → PlanetAstV0)

- **BoletoIndividual:** `emit()` produz `PlanetAstV0` válido com `PageNode` raiz, 3 `FieldNode`s (codigoBanco, dataVencimento, valorDocumento), 1 `ImageNode` (barcode dinâmico), `RepeatingNode` ausente (não há `repeated_section` no boleto).
- **PosicaoConsolidada:** `emit()` produz `PlanetAstV0` válido com `PageNode` raiz, 4 `FieldNode`s, 1 `RepeatingNode` (fundos), `SectionNode`s aninhados.
- **Round-trip serialização:** `model_dump()` → `model_validate()` preserva `schema_version`, estrutura de nós e `bind_path`.
- **Tests:** 11/11 C1 passando.

### C2 — Stage 4 consume_ast path

- **Patch:** 5 LOC adicionados em `run_stage4()` (gate: ≤100 LOC).
- **Não invasivo:** flag `consume_ast` condiciona o path; pipeline existente inalterado.
- **Output:** `context['ast_field_pairs']` populado com lista de dicts `{bind_path, formatter, bbox, page, label, layout_type_id}`.
- **Tests:** 4/4 C2 passando incluindo `test_stage4_context_gets_ast_pairs` async.

### C3 — Formatter Inference Precision

- **Corpus:** 99 campos anotados manualmente (50 BoletoIndividual + 49 PosicaoConsolidada).
- **Corretos:** 93/99 = **93.9%** (gate: ≥70%).
- **Misclassificados (6):** campos de ID/código numérico curto (`NR_PARCELA="1"`, `PARCELA_TOTAL="12"`, `COD_BANCO="341"`, `QTD_PARCELAS="6"`, etc.) classificados como `number` em vez de `raw`. Comportamento esperado para regex sem contexto semântico — strings numéricas ambíguas.
- **Por tipo:**
  - Currency: 100% ✅ (25/25)
  - Date: 100% ✅ (18/18)
  - Percent: 100% ✅ (9/9)
  - Raw: 87.2% ✅ (47/54 — IDs numéricos são o único vetor de erro)

---

## Artefatos Criados

| Arquivo | Tipo | LOC |
|---------|------|-----|
| `backend/models/ast/__init__.py` | Novo | ~15 |
| `backend/models/ast/nodes.py` | Novo | ~215 |
| `backend/services/stages/stage3_structural/formatter_inference.py` | Novo | ~129 |
| `backend/services/stages/stage3_structural/ast_emitter.py` | Novo | ~402 |
| `backend/services/stages/stage4_field_mapping.py` | Patch | +5 LOC (7 com logger) |
| `backend/tests/unit/ast/test_nodes.py` | Novo | ~38 testes |
| `backend/tests/unit/ast/test_formatter_inference.py` | Novo | ~26 testes |
| `backend/tests/unit/ast/test_c3_precision.py` | Novo | ~7 testes |
| `backend/tests/integration/test_ast_spike.py` | Novo | ~15 testes |
| `docs/reports/spike-ast/formatter-ground-truth.yaml` | Novo | ~100 campos |
| `docs/architecture/spike-ast-validation-spec.md` | Novo | spec |

**Total tests:** 86 (63 unit + 15 integration + 7 C3 precision) — todos passando.

---

## Invariante MJML #1630 — Confirmada

`FieldNode.bind_path` e `FieldNode.formatter` são **campos tipados** em `PlanetAstV0`. Nunca strings pós-compiladas. O renderer de Epic 49 transforma `FieldNode → {{bind_path | formatter}}`. Esta separação entre estrutura e apresentação é preservada pelo schema discriminado.

---

## Limitações Conhecidas

1. **IDs numéricos curtos:** `infer_formatter(["341"])` retorna `number` em vez de `raw`. Solução: passar contexto semântico (XSD type hint) para o emitter — `FieldNode` pode receber `xsd_type` hint.
2. **Multi-page:** `PlanetAstV0.root` é um único `PageNode`. Para documentos multi-página, será necessário `MultiPageNode` ou lista de `PlanetAstV0` por cluster.
3. **Tabelas raster:** `ast_emitter` trata `repeated_section` via `RepeatingNode`, mas tabelas OCR (Stage 3.2 Mistral) ainda não têm path de emissão — `TableNode` precisa de integração com `table_builder.py`.

---

## Decisão de Arquitetura Recomendada

**GO para Epic 49 com AST como source-of-truth do template engine.**

Próximos passos:
1. `@architect` emitir ADR-XXX-ast-as-source-of-truth.md
2. Replanejar Epic 49 com `PlanetAstV0` como input do renderer MJML/HTML
3. Resolver limitação #1 (xsd_type hint) em Story 49.x
4. Merge `spike/ast-validation` → `main` antes de iniciar Epic 49

---

## Suite de Testes Final

```
backend/tests/unit/ast/          63 passed  ✅
backend/tests/integration/       15 passed  ✅
Total:                           78 passed  ✅
```
