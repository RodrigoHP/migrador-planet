---
paths:
  - "**/*"
---

# Root Cause Analysis — Principio Constitucional

Quando um bug ou erro for reportado, SEMPRE execute `/investigate` (ou `*investigate` no agente @qa) antes de aplicar qualquer fix. Nunca aplique guards, workarounds ou band-aids como solucao principal sem antes investigar a origem do problema. Cada bug eh uma oportunidade de melhoria — a investigacao deve produzir mais do que entrou.

**Regras (v6.0):**
- @qa DEVE usar `*investigate` para qualquer bug — nunca corrigir diretamente
- @dev DEVE escalar bugs para @qa via `*investigate` — nunca corrigir sem investigar
- Se SOP existe com confidence >80% (algoritmo normalizado), o fast-track pode ser aceito
- SOP com effectiveness_rate < 50% NAO pode ser oferecido como fast-track
- Effectiveness de fixes DEVE ser revisada como PRIMEIRO step da Fase 9 e via `*audit-patterns`
- Tags DEVEM seguir taxonomia controlada em `docs/qa/rca-knowledge/tag-taxonomy.yaml`
- Anti-patterns DEVEM incluir todos os campos obrigatorios do schema v6.0
