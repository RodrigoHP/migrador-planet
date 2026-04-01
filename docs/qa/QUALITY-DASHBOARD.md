# Quality Dashboard

> Atualizado automaticamente apos cada `/investigate`. Ponto de entrada unico para saude do projeto.

## Metricas

| Metrica | Valor |
|---------|-------|
| Total investigacoes | 9 |
| Por layer | FAST: 0 / STANDARD: 0 / DEEP: 9 |
| Effectiveness | Resolved: 9 / Pending: 0 |
| Anti-patterns ativos | 10 (AP-001 a AP-010) |
| SOPs disponiveis | 1 |
| Recurrence rate | 33% (3 de 9 bugs tiveram recurrence) |

## Top Areas com Mais Bugs

| Area | Bugs | Ultimo |
|------|------|--------|
| frontend/src/components/editor/ | 4 | 2026-03-31 |
| backend/services/pipeline/ | 3 | 2026-03-31 |
| backend/services/storage/ | 2 | 2026-03-31 |

## Top Anti-Patterns (por recurrence)

| AP | Descricao | Recurrence | SOP |
|----|-----------|-----------|-----|
| AP-001 | Missing isinstance guard | 4 | sop-missing-isinstance-guard |
| AP-002 | Stage contract divergence | 3 | pendente |
| AP-005 | Selector mismatch | 2 | pendente |
| AP-008 | CSS reset missing dimensions | 2 | pendente |
| AP-009 | Selector data-page vs data-layout-type | 1 | pendente |

## Ultimas 10 Investigacoes

| Data | ID | Layer | Causa | Status |
|------|----|-------|-------|--------|
| 2026-03-31 | [canvas-blank-selector-mismatch](investigations/rca-2026-03-31-canvas-blank-selector-mismatch.md) | DEEP | Selector mismatch data-page vs data-layout-type | Resolved |
| 2026-03-31 | [canvas-blank-tree-no-labels](investigations/rca-2026-03-31-canvas-blank-tree-no-labels.md) | DEEP | querySelectorAll('[data-page]') returns 0 elements | Resolved |
| 2026-03-31 | [canvas-blank-v2](investigations/rca-2026-03-31-canvas-blank-v2.md) | DEEP | CSS reset missing width/height | Resolved |
| 2026-03-31 | [coverage-badge-charts-missing](investigations/rca-2026-03-31-coverage-badge-charts-missing.md) | DEEP | breakdownText omitting charts category | Resolved |
| 2026-03-31 | [stage5-document-trees-contract](investigations/rca-2026-03-31-stage5-document-trees-contract.md) | DEEP | Stage 5 missing children:[] in leaf nodes | Resolved |
| 2026-03-31 | [editor-redirect-to-home](investigations/rca-2026-03-31-editor-redirect-to-home.md) | DEEP | Router guard redirecting valid editor URLs | Resolved |
| 2026-03-31 | [custo-api-zero](investigations/rca-2026-03-31-custo-api-zero.md) | DEEP | API cost calculation returning 0 | Resolved |
| 2026-03-31 | [spacy-xsd-warnings](investigations/rca-2026-03-31-spacy-xsd-warnings.md) | DEEP | XSD path resolution via disk instead of gateway | Resolved |
| 2026-03-31 | [editor-empty-after-analysis](investigations/rca-20260331-editor-empty-after-analysis.md) | DEEP | Editor page blank after analysis complete | Resolved |
| 2026-03-29 | [analyzing-page](investigations/rca-2026-03-29-analyzing-page.md) | DEEP | Analyzing page UI bugs | Resolved |

## Gaps Identificados

- **0 investigacoes FAST/STANDARD** — sistema ainda nao capturou bugs simples
- **9 SOPs pendentes** — 10 anti-patterns mas so 1 SOP gerado
- **0 SOP fast-tracks usados** — sistema de SOP subutilizado

## Links

- [investigations.yaml](rca-knowledge/investigations.yaml) — registro completo
- [Anti-patterns](known-anti-patterns.md) — padrao de erros (AP-001 a AP-010)
- [SOPs](rca-knowledge/sops/) — procedimentos de fix
- [Tag taxonomy](rca-knowledge/tag-taxonomy.yaml) — vocabulario controlado
- [Quality Gates](gates/) — validacao de stories (36 registros)
