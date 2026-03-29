# QA Epic Gap Analysis Task

Varre todas as stories de um épico, extrai os Acceptance Criteria e valida contra o código implementado (frontend e/ou backend). Gera backlog consolidado de gaps.

---

## Task Definition

```yaml
task: qaEpicGapAnalysis()
responsavel: Quinn (Guardian) / Orion (Orchestrator)
atomic_layer: Organism

inputs:
  - epic_id: string (required)          # ex: "13"
  - scope: "frontend" | "backend" | "both" (default: "both")
  - frontend_root: string (default: "frontend/src")
  - backend_root: string (default: "backend")
  - output_path: string (default: "docs/qa/gap-reports/epic-{epic_id}-gap-report.md")

outputs:
  - gap_report: file (docs/qa/gap-reports/epic-{epic_id}-gap-report.md)
  - backlog_items: list of items ready for @sm *draft
```

---

## Execution Steps

### Step 1 — Descobrir stories do épico

```
pattern: docs/stories/{epic_id}.*.story.md
```

Para cada story encontrada:
- Extrair: ID, título, status, Acceptance Criteria

### Step 2 — Para cada AC de cada story

Para cada Acceptance Criteria:
1. Identificar **palavras-chave técnicas** (component names, function names, types, endpoints, store names)
2. Buscar evidências no código:
   - `Grep` por nome de componente/função/tipo em `{frontend_root}` e/ou `{backend_root}`
   - Verificar se o AC descreve UI → buscar em `*.vue`, `*.tsx`
   - Verificar se o AC descreve tipo/interface → buscar em `*.ts` (types)
   - Verificar se o AC descreve store → buscar em `stores/`
   - Verificar se o AC descreve endpoint → buscar em `backend/routers/`
3. Classificar evidência:
   - `IMPLEMENTED` — código encontrado, AC claramente atendido
   - `PARTIAL` — código encontrado mas incompleto ou diferente do especificado
   - `NOT_FOUND` — nenhuma evidência no código
   - `UNTESTABLE` — AC não verificável via análise estática (ex: "animação suave")

### Step 3 — Consolidar gaps

Agregar todos os ACs com status `NOT_FOUND` ou `PARTIAL`.

Para cada gap:
```yaml
gap:
  story_id: "13.X"
  story_title: "..."
  ac_number: N
  ac_text: "..."
  status: NOT_FOUND | PARTIAL
  evidence_found: "..." # o que foi encontrado (se PARTIAL)
  suggested_backlog_item:
    type: bug | feature | tech-debt
    priority: high | medium | low
    title: "..."
    description: "Implementar/corrigir: {ac_text}"
```

### Step 4 — Gerar relatório

Output: `docs/qa/gap-reports/epic-{epic_id}-gap-report.md`

Seções:
1. **Resumo** — total de ACs analisados, % implementados, gaps encontrados
2. **Gaps por Story** — tabela detalhada
3. **Backlog Gerado** — lista pronta para @sm
4. **Itens UNTESTABLE** — ACs que precisam de validação manual

---

## Output Template

```markdown
# Gap Report — Epic {epic_id}
**Gerado em:** {date}
**Stories analisadas:** {N}
**ACs totais:** {total}
**Implementados:** {implemented} ({pct}%)
**Gaps encontrados:** {gaps}

## Resumo por Story

| Story | Título | ACs | Implementados | Gaps |
|-------|--------|-----|--------------|------|
| 13.1  | ...    | N   | N            | N    |

## Gaps Detalhados

### [13.X] {título}

| # | AC | Status | Evidência |
|---|----|--------|-----------|
| 1 | ... | NOT_FOUND | — |

## Backlog Gerado

### Alta Prioridade
- [ ] **[BUG/FEATURE]** {título} — {story_id} AC#{n}

### Média Prioridade
- [ ] ...

## Itens para Validação Manual (UNTESTABLE)
- ...
```

---

## Notas de Uso

- ACs puramente visuais (animações, cores, espaçamentos) devem ser marcados como `UNTESTABLE` — requerem validação no browser
- Stories `status: Done` com muitos `NOT_FOUND` indicam possível divergência entre spec e implementação final
- Prioridade sugerida: `high` se AC tinha critério de negócio explícito, `medium` se técnico, `low` se cosmético
