# ADR-002 — Planet AST v0 como Source-of-Truth do Template Engine

**Status:** Aprovado  
**Data:** 2026-04-21  
**Contexto:** Epic 49 — Pilar C (Editor Visual + Template Engine)  
**Evidência:** Spike `spike/ast-validation` — Go/No-Go 3/3 (commit acb24a3)

---

## Contexto

O Pilar C precisa de um IR (intermediate representation) entre o pipeline de análise (Stages 1-4) e o renderer de templates HTML. Três opções foram avaliadas no spike de 5 dias:

- **Opção A:** Usar `DocumentTreeNode` diretamente como IR — acoplamento Stage 3, sem tipagem de formatters
- **Opção B:** JSON plano com campos raw — sem semântica, formatter como string pós-compilada
- **Opção C (escolhida):** `PlanetAstV0` — Pydantic v2 discriminated union com `FieldNode.bind_path` + `FieldNode.formatter` como campos tipados

## Decisão

**Usar `PlanetAstV0` (`backend/models/ast/nodes.py`) como source-of-truth do template engine no Epic 49.**

O emitter `ast_emitter.emit()` converte `DocumentTreeNode.model_dump()` → `PlanetAstV0` como saída paralela do Stage 3, sem substituir o pipeline existente.

## Invariante — MJML Issue #1630

> `FieldNode.bind_path` e `FieldNode.formatter` são **campos tipados**, nunca strings pós-compiladas.

O renderer transforma `FieldNode → {{bind_path | formatter.kind}}`. A separação entre estrutura (bind_path) e apresentação (FormatterSpec) deve ser preservada em todo o pipeline Epic 49. Nunca concatenar `bind_path + pattern` em uma string antes da renderização.

## Consequências

### Positivas
- Stage 4 consome `ast_field_pairs` via `extract_field_pairs_multi()` — patch de 5 LOC, não invasivo
- Formatter inference automática: 93.9% de precisão sem anotação manual (C3 medido no spike)
- Round-trip Pydantic: `model_dump()` → `model_validate()` preserva toda a estrutura
- `raw_html` como escape hatch para estruturas inesperadas (lição do Contentful)

### Negativas / Limitações
- **IDs numéricos curtos** (`"341"`, `"12"`) são classificados como `number` em vez de `raw` — 6/99 casos no spike. Mitigação: `xsd_type` hint em `FieldNode` (backlog Story 49.x)
- **Multi-page:** `PlanetAstV0.root` é um único `PageNode`. Documentos multi-página requerem lista de `PlanetAstV0` por cluster ou `MultiPageNode` (backlog)
- **Tabelas OCR:** `TableNode` ainda não integrado com `table_builder.py` de Stage 3.2 Mistral (backlog Story 49.x)

## Mapa de Node Types

| `DocumentTreeNode.type` | `AstNode` resultante |
|------------------------|---------------------|
| `page` (root) | `PageNode` |
| `zone`, `section` | `SectionNode` |
| `value` + classificação dynamic | `FieldNode` |
| `label`, `text`, `static` | `TextNode` |
| `image` | `ImageNode(source="static")` |
| `barcode` | `ImageNode(source="dynamic")` |
| `table` | `TableNode` |
| `repeated_section` | `RepeatingNode` |
| `chart`, `svg` | `RawHtmlNode` |
| `line`, `rect` | skipped (decorativo) |

## Referências

- Spike spec: `docs/architecture/spike-ast-validation-spec.md`
- Retrospectiva: `docs/reports/spike-ast/retrospective.md`
- Ground truth C3: `docs/reports/spike-ast/formatter-ground-truth.yaml`
- Schema: `backend/models/ast/nodes.py`
- Emitter: `backend/services/stages/stage3_structural/ast_emitter.py`
