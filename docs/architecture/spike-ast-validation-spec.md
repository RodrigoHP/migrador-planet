# Spike AST Validation — Spec

**Status:** current
**Owner:** @architect (Aria)
**Executor:** @dev sênior (--yolo)
**Duração:** 5 dias úteis
**Branch:** `spike/ast-validation` (cortada de `main` após merge de `feature/epic-48-pilar-b`)
**Gate final:** @architect (Dia 5) — Go/No-Go vinculante para Epic 49

---

## 1. Contexto

A pesquisa `docs/reports/research-ast-intermediate-representation-template.md` (Wave 4, 2026-04-21) recomenda **Opção C — AST próprio (Pydantic) + renderer escolhido a posteriori** como source-of-truth do template engine, **condicional a este spike**.

Invariante mandatória do design (lição MJML #1630): `binding` é **campo tipado** no `FieldNode` (não string pós-compilada). Renderer transforma `FieldNode → {{x | formatter}}`. Violação reintroduz a dor documentada de MJML.

Este spike NÃO compromete Epic 49. Decisão Go/No-Go no Dia 5 é vinculante.

---

## 2. Premissa reavaliada — NÃO HÁ PRODUÇÃO

O produto ainda não está deployado. Todas as medições ocorrem **localmente** contra fixtures em `backend/tests/fixtures/samples/`.

**Consequência prática:**
- Zero risco de "quebrar produção"
- Zero gate de deploy antes do spike
- scalar_coverage do Epic 48 é **re-medido local** contra fixtures pós-fix do Stage 1 — não depende de ambiente externo
- Trilha A (Epic 48 re-validação) e Trilha B (este spike) rodam em paralelo, ambas locais, sem acoplamento

---

## 3. Objetivo

Validar 3 critérios operacionais em 5 dias. Se 3/3 PASS → Go (AST vira base para Epic 49). Se <3/3 → No-Go (branch descartada, zero rollback necessário porque tudo é aditivo).

**Schema migration foi removida do escopo do spike:** não há templates salvos nem PRD de persistência, logo não há o que migrar. Evolução de schema fica livre até o primeiro template ser criado em produção — aí, sim, vira preocupação real (tratada em ADR futura ou story específica).

---

## 4. Escopo

### IN
- Novo módulo `backend/models/ast/` — 8 tipos de node em discriminated union Pydantic v2
- Emitter paralelo em Stage 3: `backend/services/stages/stage3_structural/ast_emitter.py`
- Inference: `backend/services/stages/stage3_structural/formatter_inference.py`
- Consumer test em Stage 4 via flag `--consume-ast` (opcional, não substitui caminho dict atual)
- 2 tipos de PDF: **Boleto Individual** (4 samples + XSD) e **Posição Consolidada** (4 samples + XSD)

### OUT (explícito)
- Refactor in-place de `tree_builder.py`
- Modificação de `DocumentTreeNode`, `BlockClassification`, `RepeatedSection`, `SectionTemplate`, `SectionInstance`, `SectionFieldTemplate`
- Qualquer tipo além de boleto + relatório
- Renderer (Mustache/outro) — pós-spike
- Adapter GrapesJS — pós-spike
- Frontend — não tocado
- **Schema migration** (v0→v1) — sem templates salvos, não aplicável

---

## 5. Schema AST v0 — 8 tipos MVP

```python
# backend/models/ast/nodes.py
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field

class BBox(BaseModel):
    page: int
    x0: float
    y0: float
    x1: float
    y1: float

class FormatterSpec(BaseModel):
    kind: Literal["date", "currency", "number", "percent", "raw"]
    pattern: str | None = None   # ex: "dd/MM/yyyy", "R$ #.##0,00"
    locale: str = "pt-BR"

class TextNode(BaseModel):
    type: Literal["text"]
    content: str
    bbox: BBox
    # style herdada (font_family, size, weight, color) opcional

class FieldNode(BaseModel):
    type: Literal["field"]
    bind_path: str               # ex: "boleto.vencimento"
    formatter: FormatterSpec
    bbox: BBox
    # INVARIANTE MJML #1630: binding é campo tipado, nunca string pós-compilada

class SectionNode(BaseModel):
    type: Literal["section"]
    children: list["AstNode"]
    bbox: BBox

class RepeatingNode(BaseModel):
    type: Literal["repeating"]
    iterator: str                # ex: "itens[]"
    item_template: "AstNode"
    bbox: BBox

class ImageNode(BaseModel):
    type: Literal["image"]
    source: Literal["static", "dynamic"]
    bind_path: str | None        # se dynamic
    bbox: BBox

class TableNode(BaseModel):
    type: Literal["table"]
    rows: list[list["AstNode"]]
    bbox: BBox

class PageNode(BaseModel):
    type: Literal["page"]
    page_num: int
    children: list["AstNode"]

class RawHtmlNode(BaseModel):
    type: Literal["raw_html"]
    html: str
    bbox: BBox
    # escape hatch — lição Contentful

AstNode = Annotated[
    Union[TextNode, FieldNode, SectionNode, RepeatingNode,
          ImageNode, TableNode, PageNode, RawHtmlNode],
    Field(discriminator="type")
]

class PlanetAstV0(BaseModel):
    schema_version: Literal["planet-ast-v0"] = "planet-ast-v0"
    root: AstNode
```

---

## 6. Critérios operacionais de sucesso

### C1: Stage 3 → AST v0 consumível por Stage 4

- **Medição:** `make test-integration -- -k "ast_spike"`
- **Numerador:** testes E2E que passam consumindo AST via flag `--consume-ast`
- **Denominador:** 2 (Boleto Individual + Posição Consolidada)
- **Gate:** 2/2 PASS
- **Arquivo de teste:** `backend/tests/integration/test_ast_spike.py`

### C2: ≤100 LOC ajuste em Stage 4

- **Medição:**
  ```bash
  git diff main..spike/ast-validation -- \
    backend/services/stages/stage4_field_mapping/ \
    | grep -E "^[+-]" | grep -vE "^(\+\+\+|---)" | wc -l
  ```
- **Gate:** LOC_changed ≤ 100
- **Exclui:** arquivos de teste (`test_*.py`), renames detectados pelo git (`-M`)
- **Justificativa:** valida que contrato AST é realmente consumível sem rebuild massivo

### C3: Formatter inference ≥70% precisão

- **Ground truth:** `docs/reports/spike-ast/formatter-ground-truth.yaml` — 50 campos anotados manualmente por tipo (total 100), cada um com `expected_kind` e `expected_pattern`
- **Medição:**
  ```python
  precision = (campos com kind_inferido == expected_kind
               E pattern_inferido normalizado == expected_pattern)
              / 100
  ```
- **Normalização de pattern:** case-insensitive, whitespace-stripped, "R$" == "R$ " == "BRL"
- **Gate:** precision ≥ 0.70
- **Escopo:** apenas campos classificados como dinâmicos pelo Stage 3 atual — campos fixos ficam fora do denominador

---

## 7. Cronograma e checkpoints

| Dia | Entrega | Gate |
|---|---|---|
| **1** | `backend/models/ast/` completo + testes unitários de schema | — |
| **2** | `ast_emitter.py` + boleto + relatório emitem `PlanetAstV0` válido | **Checkpoint @architect** — abort se emitter não funciona |
| **3** | `formatter_inference.py` + ground truth anotado | — |
| **4** | Stage 4 consumer via flag + testes E2E integrados | — |
| **5** | Medições finais dos 3 critérios + retrospective | **Gate final @architect** — Go/No-Go |

### Checkpoint Dia 2 (anti-desperdício)

Se `ast_emitter.py` não produz `PlanetAstV0` válido para boleto+relatório no final do Dia 2:
- **Abort precoce.** Custo real = 2 dias.
- Não avançar para C3/C4 — dado suficiente para No-Go.

---

## 8. Go/No-Go (Dia 5)

### Go (3/3 PASS)
- Merge `spike/ast-validation` → `main` como base de Epic 49
- @architect escreve `docs/architecture/adrs/ADR-XXX-ast-as-source-of-truth.md` com evidência do spike embutida
- @architect escreve `docs/architecture/planet-ast-spec.md` (spec formal do schema)
- Epic 49 replanejado sobre AST

### No-Go (<3/3 PASS)
- Branch `spike/ast-validation` **não** mergeada (preservada como research artifact)
- Relatório em `docs/reports/spike-ast/retrospective.md` documentando qual critério falhou e por quê
- Epic 49 re-planejado **sem AST** (fallback: seguir block model consolidado do pre-research)

### Partial (2/3 PASS)
- Caso-a-caso com @architect. Default: No-Go, mas critério específico falho pode ser reavaliado:
  - C1 falhou → No-Go hard (contrato não funciona)
  - C2 falhou → Avaliar se LOC explodiu por motivo estrutural ou acidental
  - C3 falhou → Go condicional com formatter inference adiada (escope reduzido)

---

## 9. Branch strategy

```
main
 ├── feature/epic-48-pilar-b           (Trilha A — Epic 48 re-validação)
 └── spike/ast-validation              (Trilha B — este spike)
```

- Branch cortada de `main` **após** `feature/epic-48-pilar-b` ser mergeada (para incluir fix Stage 1)
- 100% aditivo: zero modificação em arquivos existentes (exceto adição opcional de flag `--consume-ast` em Stage 4)
- Merge só se Go no Dia 5

---

## 10. Responsabilidades

| Agente | Responsabilidade |
|---|---|
| @dev sênior (--yolo) | Implementação em 5 dias, sem interrupção |
| @architect | Checkpoint Dia 2 + Gate Dia 5 |
| @qa | **Não envolvido** — spike não é story, não passa por QA gate |
| @analyst | Opcional: outreach a CCM alumni durante os 5 dias (reduz viés residual) |

---

## 11. Caveats residuais (do research)

- **Formatter inference é contribuição original** sem precedente direto — C3 é o critério mais incerto, daí a meta 70% (não 100%)
- **Viés de sobrevivência residual:** outreach a alumni de Exstream/Inspire/AEM Forms não feito; pode revelar armadilhas não-documentadas publicamente
- **Estimativas de 7.5-9 stories para Epic 49 pós-Go** calibradas por leitura de código, não validadas no spike em si — o spike valida viabilidade, não custo total

---

## 12. Post-spike (se Go)

Ordem dos próximos artefatos:

1. ADR-XXX — AST as source-of-truth
2. `planet-ast-spec.md` — spec formal
3. Answers às 6 open questions do handoff (consolidadas na ADR)
4. Replanejamento Epic 49 com backlog AST-based

**Open questions a resolver na ADR (não aqui):**
1. Spec doc: markdown + Pydantic OR JSON Schema?
2. Schema versão inicial: v0 ou v1?
3. Renderer único ou múltiplo no MVP?
4. Migrations: custom ou library?
5. Spike executor: confirmado @dev sênior --yolo ✓
6. CCM alumni outreach: opcional, em paralelo

---

## 13. Referências

- `docs/reports/research-ast-intermediate-representation-template.md` — pesquisa base (Wave 4, 2026-04-21)
- `docs/reports/research-block-model-template-editors.md` — pesquisa anterior (modelo de 3 camadas, §11 Addendum)
- `.aios/handoffs/handoff-analyst-to-architect-20260421-ast-research.yaml` — handoff consumido
- `backend/models/pipeline_context/` — modelos Pydantic existentes (não modificar no spike)
- `backend/services/stages/stage3_structural/tree_builder.py` — output atual que o `ast_emitter.py` consome (read-only)
