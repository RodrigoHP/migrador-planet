---
paths:
  - "**/*"
---

# Root Cause Analysis — Principio Constitucional

Quando um bug ou erro for reportado, SEMPRE execute `/investigate` (ou `*investigate` no agente @qa) antes de aplicar qualquer fix. Nunca aplique guards, workarounds ou band-aids como solucao principal sem antes investigar a origem do problema. Cada bug eh uma oportunidade de melhoria — a investigacao deve produzir mais do que entrou.

**Regras (v9.0 — Progressive Escalation):**

### Principio Core
- @qa DEVE usar `*investigate` para qualquer bug — nunca corrigir diretamente
- @dev DEVE escalar bugs para @qa via `*investigate` — nunca corrigir sem investigar
- Em modo interativo: @qa gera fix_requirements e delega para @dev
- Em modo `--yolo`: @qa investiga E implementa o fix inline (end-to-end sem troca de agente)
- @architect revisa se barrier analysis indica falhas arquiteturais
- **Toda investigacao DEVE registrar em `investigations.yaml`** — sem excecao, em qualquer layer

### Progressive Escalation (3 layers — tecnicas DISTINTAS)
- **FAST (70%) — RECONHECER:** Pattern match + Knowledge Check + SOP fast-track. ~2 min, 0 subagents. "Ja vi isso antes?"
- **STANDARD (25%) — RASTREAR:** Backward trace + git forensics + subagent causal. ~10 min, 1 subagent. "De onde vem o valor errado?"
- **DEEP (5%) — PROVAR:** Adversarial challenge + barrier analysis + evidence grading. ~30 min, 11 subagents. "Consigo provar? Alguem refuta?"
- Escalacao = tecnica mais poderosa, nao a mesma com mais tempo. Nenhum trabalho jogado fora (standard_handoff).
- Force deep: `/investigate --deep "bug"` para bugs que sabidamente precisam de war room
- Modo YOLO: `/investigate --yolo "bug"` — investigar + implementar fix + testar sem paradas

### Documentacao Proporcional (OBRIGATORIO)
- **FAST:** Registro minimo em `investigations.yaml` (~10 campos)
- **STANDARD:** Registro + SOP se padrao novo
- **DEEP:** Relatorio completo + investigation_record + anti-patterns + SOPs + meta-learning
- Regra de ouro: TODA investigacao deixa rastro em `investigations.yaml`
- Apos cada investigacao: `file-intelligence.yaml` eh regenerado automaticamente (Passo 8.2)

### Knowledge Flow (Retroalimentacao)
- `investigations.yaml` → `file-intelligence.yaml` (auto-gerado no Passo 8.2)
- `file-intelligence.yaml` → @dev Risk Briefing (proativo, antes de codar)
- `file-intelligence.yaml` → @qa Review Proporcional (profundidade por risco)
- `file-intelligence.yaml` → `/investigate` Quick Knowledge Check (consulta rapida)

### Origin Gate (OBRIGATORIO em todas as layers)
- 5-point checkpoint antes de QUALQUER fix: origin_point, symptom_point, test_at_origin, is_band_aid, recurrence_guard
- 5/5 PASS → delegar fix; 4/5 → delegar com warning; 3/5 ou menos → BLOQUEAR
- Pergunta "is_band_aid" FAIL → BLOQUEAR independente do score

### DEEP Layer (detalhes em `.claude/commands/rca/deep-pipeline.md`)
- Phase briefings isolados em `.claude/commands/rca/phase-*.md`
- Retry 1x + fallback inline por fase
- Fases 2 e 3 em PARALELO
- Tags DEVEM seguir taxonomia em `docs/qa/rca-knowledge/tag-taxonomy.yaml`
- Evidence Summary DEVE ter pelo menos 1 achado E1_confirmed para fix
- SOP counters atualizados em 3 pontos: Fase 2, Fase 9, audit-patterns
- Achados colaterais materializados como story drafts em `docs/stories/backlog/`
