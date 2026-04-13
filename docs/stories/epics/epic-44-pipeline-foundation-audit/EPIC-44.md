# Epic 44 — Pipeline Foundation Audit

## Status: Draft

## Objetivo

Auditar empiricamente as decisões **fundacionais** do pipeline (stages de detecção/agrupamento que precedem o template final) para prevenir regressões silenciosas. Cada spike desafia premissas da implementação atual contra alternativas modernas, com ground truth manual e ablation study.

## Contexto

Epic 43 corrige causas-raiz imediatas do primeiro PDF (boleto: mapeamento 17%→≥80%). Mas algumas decisões do pipeline são **fundacionais**: erros silenciosos ali cascatear para todos os stages seguintes sem aparecer nas métricas de saída final.

Exemplo: se Stage 1 (Layout Clustering) agrupa páginas erradas no mesmo cluster, Stage 2 processa apenas uma delas como representative, Stage 3 compara instâncias com estruturas diferentes e Stage 5 gera um template vazio ou inconsistente para aquele cluster — mas o número final de "campos mapeados" pode parecer OK.

**Princípio:** antes de investir em tuning fino, validar que a base está correta. Spikes geram decisões baseadas em dados, não opinião.

## Escopo

Este epic contém **spikes de auditoria** (pesquisa, não implementação). Cada spike:
- Define ground truth manual contra PDFs reais
- Roda baseline atual + alternativas como ablation study
- Produz relatório empírico + recomendação
- **Implementação** das recomendações vira story(ies) separada(s) em epic futuro ou Epic 43/44 update

## Stories

| Story | Título | Prioridade | Esforço | Dep |
|-------|--------|-----------|---------|-----|
| 44.1 | SPIKE: Re-avaliação do Stage 1 Layout Clustering | P0 | 14h | — |

**Futuras candidatas a este epic (não criadas ainda):**
- Stage 3 Structural Analysis re-audit (hierarquia, semantic classification heuristics)
- Field Mapping strategy re-audit (Gemini vs alternativas)
- Visual cross-check standards (pHash vs CLIP vs DINOv2 em múltiplos stages)

## Critério de Conclusão

- Cada spike produziu relatório empírico versionado
- Recomendações claras (manter baseline / trocar / complementar) com evidência
- Stories de implementação criadas quando spike indica mudança
- Auditoria documentada permite reabrir discussão com dados se futuro contradizer a decisão

## Princípio de Execução

- **Não implementar dentro do Epic 44.** Spikes produzem recomendação, não código de produção.
- **Baseline empírica obrigatória** em todo spike — comparar contra o que está em produção hoje.
- **Se spike mostrar que baseline já é ótimo:** resultado válido, documentar e fechar sem mudança.

## Change Log

| Date | Agent | Action |
|------|-------|--------|
| 2026-04-13 | @architect (Aria) | Epic criado — audit fundacional começa por Stage 1 clustering |
