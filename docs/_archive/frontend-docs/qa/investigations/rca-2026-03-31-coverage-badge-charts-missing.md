# RCA Report: rca-2026-03-31-coverage-badge-charts-missing

## 1. Classificação
- Domínio: Clear (causa-efeito óbvio, código confirmado)
- Severidade: Medium (badge mostra informação incompleta/enganosa)
- Scope: single-file (CoverageBadge.vue)
- Dedup: new

## 2. Problema Reportado
Badge "Cobertura 40% (Imagens 100%)" mostrava overall 40% mas breakdown
omitia a categoria Gráficos, que era a responsável pela baixa cobertura.
O usuário via um percentual baixo (40%) sem conseguir identificar o motivo
no próprio badge (apenas via CoveragePopover ao clicar).

Segunda badge "Confiança 45%" é dado real do pipeline — comportamento correto.

## 3. Causa Raiz Confirmada (E1_confirmed)
CoverageBadge.vue breakdownText (computed) iterava sobre fields, tables, images
mas omitia charts — apesar de CoverageData.charts existir no tipo TypeScript
e CoveragePopover.vue exibir charts corretamente.

## 4. Fix Aplicado
Adicionada linha em CoverageBadge.vue:
`if (props.breakdown.charts.total > 0) parts.push('gráficos X%')`

## 5. Testes Criados
- shows charts in breakdown when charts.total > 0
- does not show charts in breakdown when charts.total is 0
9/9 testes passando.

## 6. Barreira Analysis
| Camada | Status | Criticality |
|--------|--------|-------------|
| Code Level | absent (sem exhaustiveness check) | MEDIUM |
| Test Level | absent (nenhum teste cobria charts) | HIGH |
| Static Analysis | absent (TypeScript não força exhaustive computed) | LOW |

## 7. Pipeline Metrics
preset: adaptive:clear (fast track)
phases: 0→1→6.5→8a→8b→9
custo estimado: ~$0.03
