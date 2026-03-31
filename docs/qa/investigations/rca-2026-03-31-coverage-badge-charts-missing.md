# RCA Report: rca-2026-03-31-coverage-badge-charts-missing

## 1. Classificação
- **Domínio:** Clear (causa-efeito óbvio, código confirmado via E1)
- **Severidade:** Medium (badge exibe informação incompleta/enganosa)
- **Scope:** single-file (`CoverageBadge.vue`)
- **Dedup:** new

## 2. Problema Reportado
Badge "Cobertura 40% (Imagens 100%)" exibia overall 40% mas o breakdown omitia a categoria **Gráficos**, que era a responsável pela baixa cobertura. O usuário via um percentual baixo (40%) sem conseguir identificar o motivo no próprio badge (apenas via CoveragePopover ao clicar).

Segunda badge "Confiança 45%" é dado real do pipeline backend — comportamento correto.

## 3. Causa Raiz (E1_confirmed)
`CoverageBadge.vue` — `breakdownText` (computed) iterava sobre `fields`, `tables`, `images` mas **omitia `charts`**, apesar de:
- `CoverageData.charts` existir no tipo TypeScript (`coverage.types.ts:12`)
- `CoveragePopover.vue` exibir "Gráficos" corretamente (linhas 44-45)

```typescript
// ANTES — charts ausente:
if (props.breakdown.fields.total > 0) parts.push(`campos ${pct(...)}%`)
if (props.breakdown.tables.total > 0) parts.push(`tabelas ${pct(...)}%`)
if (props.breakdown.images.total > 0) parts.push(`imagens ${pct(...)}%`)
// ← charts NÃO estava aqui

// DEPOIS — fix aplicado:
if (props.breakdown.images.total > 0) parts.push(`imagens ${pct(...)}%`)
if (props.breakdown.charts.total > 0) parts.push(`gráficos ${pct(props.breakdown.charts.mapped, props.breakdown.charts.total)}%`)
```

## 4. Fix Aplicado
**Arquivo:** `frontend/src/molecules/CoverageBadge.vue`
Adicionada linha ao `breakdownText` computed para incluir `charts` quando `total > 0`.

## 5. Testes Criados
**Arquivo:** `frontend/src/molecules/CoverageBadge.spec.ts`
- `shows charts in breakdown when charts.total > 0` — valida "gráficos 40%" e "imagens 100%"
- `does not show charts in breakdown when charts.total is 0` — valida que não aparece quando sem gráficos

**Resultado:** 9/9 testes passando.

## 6. Barreira Analysis
| Camada | Status | Criticality | Contrafactual |
|--------|--------|-------------|---------------|
| Code Level | absent | MEDIUM | Exhaustiveness check detectaria |
| Test Level | absent | HIGH | Teste com charts.total>0 teria detectado imediatamente |
| Static Analysis | absent | LOW | TypeScript não força exhaustive em computed |

**Fix This First:** Test Level — teste com cenário de charts teria detectado imediatamente.

## 7. Confiança 45% — Diagnóstico
Não é bug. O badge exibe vermelho corretamente (< 80%). O valor vem do `overall` computado pelo backend pipeline. Causa provável: Vision AI rodando em modo fallback (~75% qualidade) quando `OPENROUTER_API_KEY` não configurada (ver `rca-2026-03-31-custo-api-zero`).

## 8. Pipeline Metrics
```yaml
preset: adaptive:clear (fast track)
phases_executed: [0, 1, 6.5, 8a, 8b, 9]
phases_parallel: []
estimated_cost: ~$0.03
```
