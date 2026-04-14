# Epic 24 — Vision AI Observability: Silent Degradation Fix

## Status
Ready

## Objetivo
Corrigir degradação silenciosa quando Vision AI não está disponível: o pipeline roda
em modo fallback (~75% qualidade) sem notificar o usuário, e o campo "CUSTO API"
exibe `$0.00` de forma ambígua (não distingue "não chamada" de "gratuita").

## Origem
RCA `rca-2026-03-31-custo-api-zero` — investigação `*investigate` sobre CUSTO API = $0.00.
Anti-pattern AP-005 registrado: Silent Service Degradation.
Handoff: `.aios/handoffs/handoff-rca-to-sdc-20260331-custo-api-zero.yaml`

## Stories

| Story | Título | Executor | Prioridade | Status |
|-------|--------|----------|-----------|--------|
| 24.1 | Propagar warning quando Vision AI usa fallback | @dev | HIGH | Draft |
| 24.2 | Frontend distinguir $0.00 de Vision AI desabilitado | @dev | MEDIUM | Draft |
| 24.3 | Rastrear custo real via completion.usage | @dev | LOW | Draft |

## Definition of Done
- Quando Vision AI não está configurada, usuário recebe aviso explícito na UI
- Campo CUSTO API exibe "N/A" ou badge de aviso quando Vision AI foi desabilitada
- SSE summary inclui flag `vision_ai_used` para o frontend
- Testes cobrindo o path "API key ausente → fallback → warning propagado"
- Zero regressões nos testes existentes

## Prioridade
HIGH (24.1) → MEDIUM (24.2) → LOW (24.3)
Story 24.2 depende de 24.1 (precisa do flag `vision_ai_used` no SSE).
