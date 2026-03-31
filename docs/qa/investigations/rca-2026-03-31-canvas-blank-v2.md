# RCA Report: rca-2026-03-31-canvas-blank-v2

## 1. Classificação
- **Domínio:** Complicated (requer análise CSS + pipeline para identificar)
- **Severidade:** High (editor inutilizável — canvas em branco)
- **Scope:** Multi-file (stage5 backend + HTMLCanvas frontend)
- **Dedup:** RELATED a `rca-2026-03-31-canvas-blank-tree-no-labels` (mesma manifestação, causa diferente)
- **Preset:** adaptive:complicated

## 2. Problema Reportado
Canvas permanece em branco APÓS o fix de `673b7f2`. O fix anterior resolveu o caso
dos standalone text blocks mas o canvas continuou branco para documentos com apenas
field pairs (todos com bbox → `position:absolute`).

## 3. Causa Raiz (E1_confirmed, 0.97)

### Root Cause Primária
`_BASE_CSS_RESET` em `stage5_template_generation.py:47` define:
```css
.page {
  position: relative;
  overflow: hidden;
  /* SEM width, SEM height */
}
```

As dimensões do `.page` só são injetadas por `_step_5_2_css_from_extraction:539`:
```python
if page_widths and page_heights:
    css_parts.append(f".page {{ width: {px_w}px; height: {px_h}px; }}")
```

Esta linha **só executa quando `enriched_documents` tem páginas com `is_representative=True`**
e campos `width/height` válidos. Quando o CSS dinâmico não é gerado, `.page` tem `0×0px`.

### Mecanismo
```
.page { overflow: hidden; height: 0 }
  ├─ .header { position: absolute }  → não expande pai
  ├─ .flow { position: absolute }    → não expande pai
  │     └─ .section { position: relative; height: 0 }
  │           └─ <span style="position:absolute">  → clipped pelo .page
  └─ .footer { position: absolute }  → não expande pai
```

Com altura 0, `overflow: hidden` corta **todo** conteúdo absoluto → canvas branco.

### Por que o fix anterior (673b7f2) funcionou parcialmente
Standalone text blocks são `<span>` **inline** (sem `position:absolute`). Elementos inline
expandem o height do container pai. Se o documento tinha pelo menos um bloco standalone,
`.page` ganhava altura suficiente para mostrar parte do conteúdo. Documentos com **apenas
field pairs** (label+value com bbox, todos `position:absolute`) ficaram em branco.

## 4. Grafo Causal
```
Canvas branco
  └─ [AND] .page colapsa (height=0) + overflow:hidden
       ├─ [E1] _BASE_CSS_RESET sem width/height → stage5:47
       │    └─ CSS dinâmico condicional (só se page_widths não vazio) → stage5:534
       └─ [E1] Todos os filhos são position:absolute → não expandem pai
            ├─ .header/.flow/.footer → stage5:55-71
            └─ spans de field com bbox → stage5:249-285
```

## 5. Fix Aplicado

**Arquivo:** `backend/services/stages/stage5_template_generation.py:47`

```python
# ANTES:
.page {
  position: relative;
  overflow: hidden;
}

# DEPOIS:
.page {
  position: relative;
  overflow: hidden;
  width: 794px;   /* fallback A4 */
  height: 1123px; /* fallback A4 */
}
```

O CSS dinâmico de `_step_5_2_css_from_extraction:539` continua funcionando como
**override** quando os dados reais do PDF estão disponíveis.

**Commit:** `70d8519`

## 6. Testes
- 48 testes stage5 passando (2 novos de regressão adicionados)
- `test_base_css_reset_has_page_dimensions` — confirma fallback no BASE
- `test_css_without_enriched_documents_still_has_page_size` — confirma que canvas não fica branco sem enriched_documents

## 7. Barrier Analysis
| Camada | Status | Criticality | Contrafactual |
|--------|--------|-------------|---------------|
| Code Level | absent | HIGH | Teste de CSS gerado sem enriched_docs teria detectado |
| Test Level | absent | HIGH | `test_css_fallback_without_enriched_documents` não existia |
| Code Review | absent | MEDIUM | Review da PR do Epic 13 teria identificado ausência de dimensões |

## 8. Achado Colateral
O fix anterior `673b7f2` foi correto mas **incompleto** — resolveu o sintoma
(standalone text blocks) sem endereçar a causa raiz (ausência de fallback de
dimensões). Bugs com sintoma similar devem verificar se `.page` tem dimensões
explícitas em TODOS os cenários de geração CSS.

## 9. Pipeline Metrics
```yaml
preset: adaptive:complicated
phases_executed: [0, 1, 2, 3, 6, 6.5]
phases_parallel: []
phases_via_fallback: [3]  # inline
estimated_cost: ~$0.00 (inline)
```
