---
paths:
  - "**/*"
---

# Root Cause Analysis — Principio Constitucional

Quando um bug ou erro for reportado, SEMPRE execute `/investigate` (ou `*investigate` no agente @qa) antes de aplicar qualquer fix. Nunca aplique guards, workarounds ou band-aids como solucao principal sem antes investigar a origem do problema. Cada bug eh uma oportunidade de melhoria — a investigacao deve produzir mais do que entrou.

**Regras:**
- @qa DEVE usar `*investigate` para qualquer bug — nunca corrigir diretamente
- @dev DEVE escalar bugs para @qa via `*investigate` — nunca corrigir sem investigar
- Se SOP existe com confidence >80%, o fast-track pode ser aceito (v5.0)
- Effectiveness de fixes DEVE ser revisada via `*audit-patterns` apos 7 dias
