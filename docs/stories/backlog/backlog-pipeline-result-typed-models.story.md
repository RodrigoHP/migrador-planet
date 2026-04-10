---
epic: TBD
story: TBD
title: "Tipagem: substituir dict genérico em PipelineResult por modelos Pydantic"
status: Draft
executor: "@dev"
quality_gate: "@qa"
quality_gate_tools: [static_analysis, unit_test, type_check]
depends_on: ["Story 42.13"]
source_debt: "DT-42-3"
priority: medium
---

# Story TBD: PipelineResult — campos genéricos → modelos Pydantic tipados

## Status
Draft

## Story
**As a** desenvolvedor frontend,
**I want** que os tipos TypeScript gerados por `npm run generate:types` sejam precisos
para `field_mappings`, `document_structure` e `confidence_scores`,
**so that** o compilador detecte erros de acesso a campos inexistentes em vez de aceitar `unknown`.

## Contexto

Story 42.13 AC3 foi marcado como adiado porque `PipelineResult` usa `list[dict[str, Any]]`
para campos críticos, gerando `{ [key: string]: unknown }[]` no TypeScript em vez de tipos
precisos. Para que o codegen produza tipos utilizáveis, esses campos precisam de modelos
Pydantic com campos declarados.

**Campos afetados em `PipelineResult` (`backend/models/pipeline_context.py`):**
- `field_mappings: list[dict[str, Any]]` → candidato: `list[FieldMappingEntry]`
- `document_structure: list[dict[str, Any]]` → candidato: `list[DocumentStructureItem]`
- `confidence_scores: dict[str, Any]` → candidato: `ConfidenceScores`

`FieldMappingEntry` já existe em `pipeline_context.py` e pode ser candidato direto.

## Acceptance Criteria

- [ ] AC1: `PipelineResult.field_mappings` usa modelo Pydantic tipado em vez de `list[dict[str, Any]]`
- [ ] AC2: `PipelineResult.document_structure` usa modelo Pydantic tipado
- [ ] AC3: `PipelineResult.confidence_scores` usa modelo Pydantic tipado
- [ ] AC4: `npm run generate:types` gera campos sem `unknown` para os 3 campos acima
- [ ] AC5: mypy zero erros
- [ ] AC6: Nenhuma regressão nos testes existentes

## Escopo

### IN
- `backend/models/pipeline_context.py` — criar/reusar modelos para os 3 campos
- `backend/models/pipeline_context.py::PipelineResult` — substituir `dict[str, Any]`
- `backend/openapi.json` — regen após mudança (via `python -c "from main import app; ..."`)
- `frontend/src/types/generated/pipeline-api.ts` — regen via `npm run generate:types`

### OUT
- Alterar lógica de pipeline (apenas tipos, não comportamento)
- Refatorar frontend para usar novos tipos (opcional, story separada)
- `template.types.ts` — não vem do pipeline backend

## Estimativa
6h

## Dependências
- Story 42.13 Done ✓
- Story 42.7 Done ✓ (extra="forbid" em todos os modelos)

## Riscos

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| `field_mappings` tem campos variáveis por tipo de documento | MÉDIA | Usar `Field(default=None)` para campos opcionais |
| Quebrar serialização existente no pipeline | MÉDIA | Pydantic serializa modelos como dicts por padrão |
| `document_structure` muito heterogêneo | ALTA | Avaliar se `list[Any]` é aceitável aqui |

## Dev Notes

### Modelo candidato para field_mappings
`FieldMappingEntry` já existe em `pipeline_context.py`:
```python
class FieldMappingEntry(BaseModel):
    block_id: str
    pdf_text: str
    xsd_field_path: str
    label_text: str
    confidence: float
    # ...
```

### Regen do openapi.json
```bash
cd backend
python -c "from main import app; import json; print(json.dumps(app.openapi(), indent=2))" > openapi.json
```

### Regen dos tipos TypeScript
```bash
cd frontend && npm run generate:types
```

## Change Log

| Date | Agent | Action |
|------|-------|--------|
| 2026-04-10 | @dev | Story criada — DT-42-3 identificado (Story 42.13 AC3/AC4 adiados) |
