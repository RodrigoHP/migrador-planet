---
epic: TBD
story: TBD
title: "Fix: alinhar contract_3_2.json com campos reais de FontInfo"
status: Draft
executor: "@dev"
quality_gate: "@qa"
quality_gate_tools: [static_analysis, unit_test]
depends_on: []
source_debt: "DT-42-1"
priority: high
---

# Story TBD: Alinhar schema de contrato com campos reais de FontInfo

## Status
Draft

## Story
**As a** desenvolvedor que executa a suite de testes,
**I want** que `test_stage1_stage2_integration.py` passe sem falhas de schema,
**so that** o CI seja verde e o contrato de Stage 2 reflita o modelo real.

## Contexto

`contract_3_2.json` foi criado no Epic 13 antecipando uma refatoração de `FontInfo`
que nunca aconteceu. Desde então, 5 testes em `test_stage1_stage2_integration.py`
falham com `jsonschema.ValidationError: 'font_family' is a required property`.

**Causa raiz:** Schema espera `font_family/font_size/font_weight/font_style` mas
`FontInfo` (em `backend/models/pipeline_context.py:150`) produz:
```python
class FontInfo(BaseModel):
    name: str = ""
    css_family: str = ""
    size: float = 0.0
    is_bold: bool = False
    is_italic: bool = False
```

## Acceptance Criteria

- [ ] AC1: Os 5 testes em `test_stage1_stage2_integration.py` passam limpos
- [ ] AC2: `contract_3_2.json` reflete os campos reais de `FontInfo`
- [ ] AC3: Nenhuma regressão nos demais testes que usam `FontInfo`
- [ ] AC4: mypy continua com zero erros

## Escopo

### IN
- `backend/tests/schemas/contract_3_2.json` — atualizar campos `fonts.items` de
  `font_family/font_size/font_weight/font_style` para `name/css_family/size/is_bold/is_italic`
- Verificar se outros arquivos referenciam esses campos do schema

### OUT
- Renomear campos de `FontInfo` (mudança invasiva — não é o objetivo desta story)
- Alterar Stage 2 extraction logic

## Estimativa
1h

## Dependências
Nenhuma

## Dev Notes

### Mudança no schema
```json
// ANTES (errado — campos nunca implementados):
"fonts": {
  "type": "array",
  "items": {
    "type": "object",
    "required": ["font_family", "font_size", "font_weight", "font_style"],
    "properties": {
      "font_family": { "type": "string" },
      "font_size": { "type": "number" },
      "font_weight": { "type": "string" },
      "font_style": { "type": "string" }
    }
  }
}

// DEPOIS (correto — campos reais de FontInfo):
"fonts": {
  "type": "array",
  "items": {
    "type": "object",
    "required": ["name", "css_family", "size", "is_bold", "is_italic"],
    "properties": {
      "name": { "type": "string" },
      "css_family": { "type": "string" },
      "size": { "type": "number" },
      "is_bold": { "type": "boolean" },
      "is_italic": { "type": "boolean" }
    }
  }
}
```

### Arquivo alvo
`backend/tests/schemas/contract_3_2.json` — localizar bloco `"fonts"` e substituir.

## Change Log

| Date | Agent | Action |
|------|-------|--------|
| 2026-04-10 | @dev | Story criada — DT-42-1 identificado pós Epic 42 |
