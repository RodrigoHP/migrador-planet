---
paths:
  - "**/*"
---

# Root Cause Analysis — Principio Constitucional

Quando um bug ou erro for reportado, SEMPRE execute `/investigate` (ou `*investigate` no agente @qa) antes de aplicar qualquer fix. Nunca aplique guards, workarounds ou band-aids como solucao principal sem antes investigar a origem do problema. Cada bug eh uma oportunidade de melhoria — a investigacao deve produzir mais do que entrou.

**Regras (v8.1 — Multi-Model Pipeline):**
- @qa DEVE usar `*investigate` para qualquer bug — nunca corrigir diretamente
- @dev DEVE escalar bugs para @qa via `*investigate` — nunca corrigir sem investigar
- Cada fase roda como subagent isolado com modelo otimizado (default preset: adaptive)
- Preset configuravel via `--preset {economy|balanced|quality|single|adaptive}`
- Preset `adaptive` (default) auto-seleciona: Clear→economy, Complicated→balanced, Complex/Chaotic→quality
- Preset `single` reproduz comportamento v7.0 exato (zero subagents)
- Phase contracts definem input/output formal por fase — subagent recebe briefing autossuficiente
- Retry: se subagent falha validacao, retry 1x com feedback antes de fallback
- Fallback: se retry falha, orquestrador executa inline (v7.0 behavior)
- Fases 2 e 3 rodam em PARALELO (ambas dependem apenas da Fase 1)
- Fase 6.5 (SDC Bridge) delega fix para SDC com quality gate real — @qa NAO implementa inline
- Pipeline metrics DEVEM ser registradas no relatorio (preset, phases, custo estimado)
- Se SOP existe com confidence >80% (algoritmo normalizado), o fast-track pode ser aceito
- SOP com effectiveness_rate < 50% NAO pode ser oferecido como fast-track
- Effectiveness de fixes DEVE ser revisada em 2 pontos: Fase 0 (pre-investigation trigger) e `*audit-patterns`
- Tags DEVEM seguir taxonomia controlada em `docs/qa/rca-knowledge/tag-taxonomy.yaml`
- Anti-patterns DEVEM incluir todos os campos obrigatorios do schema v6.0
- Schema validation checklist (Fase 8a secao 15) eh OBRIGATORIA antes de registrar investigacao
- Dedup check usa scoring concreto (error msg +40, file overlap +30, tag overlap +20, AP match +10)
- Barrier analysis DEVE incluir contrafactual para cada camada e ranking "Fix This First"
- Escalation assessment (4 criterios) eh OBRIGATORIO na Fase 5 — nao pode ser pulado
- Evidence Summary DEVE ter pelo menos 1 achado E1_confirmed para prosseguir para fix
- SOP counters DEVEM ser atualizados em 3 pontos: Fase 2 (times_applied), Fase 9 (effectiveness), audit-patterns
- Achados colaterais DEVEM ser materializados como story drafts em `docs/stories/backlog/`
