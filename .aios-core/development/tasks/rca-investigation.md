# RCA Investigation — AIOS Task Wrapper

```yaml
task: rcaInvestigation()
responsavel: Multi-agente (orquestrado por @aios-master)
responsavel_type: Workflow
atomic_layer: Strategy

inputs:
  - campo: error_evidence
    tipo: string | array
    origem: User Input
    obrigatorio: true
    descricao: "Screenshots, logs, stack traces, ou descricao do(s) erro(s)"
  - campo: scope
    tipo: string
    origem: User Input
    obrigatorio: false
    descricao: "Arquivo, modulo ou stage afetado (auto-detectado se nao informado)"

outputs:
  - campo: investigation_report
    tipo: file
    destino: "docs/qa/investigations/rca-{date}-{slug}.md"
    persistido: true
    descricao: "Relatorio completo com classification, causal graph, evidence grades, fixes, barrier analysis"
  - campo: knowledge_base_entry
    tipo: file
    destino: "docs/qa/rca-knowledge/investigations.yaml"
    persistido: true
    descricao: "Investigation record na knowledge base para pattern matching futuro"
  - campo: sop_generated
    tipo: file
    destino: "docs/qa/rca-knowledge/sops/sop-{slug}.yaml"
    persistido: true
    descricao: "SOP executavel gerado a partir do relatorio (se padrao novo)"
  - campo: backlog_items
    tipo: array
    destino: "Handoff artifact em .aios/handoffs/ para SDC"
    descricao: "Lista de stories criadas + handoff para @sm/@po"
  - campo: architectural_findings
    tipo: array
    destino: "Escalacao para @architect (se aplicavel)"
    descricao: "Problemas estruturais que requerem decisao arquitetural"
```

---

## Metodologia

Executar `/investigate` (`.claude/commands/investigate.md` v8.0).
O skill contem a metodologia completa de investigacao como pipeline multi-model.
Esta task adiciona orquestracao AIOS multi-agente sobre essa metodologia.

**v8.0 — Multi-Model Pipeline (inclui tudo do v7.0):**
- **Pipeline multi-model** — cada fase como subagent isolado com modelo otimizado (v8.0)
- **Phase contracts** — input/output formal por fase para context isolation (v8.0)
- **Model routing** — configuravel via presets: economy/balanced/quality/single (v8.0)
- **Briefing templates** — 9 prompts autossuficientes para subagents (v8.0)
- **SDC Bridge (Fase 6.5)** — fix via SDC com quality gate real (v8.0)
- **Fallback protocol** — degradacao graceful, inline automatico se subagent falha (v8.0)
- **Pipeline metrics** — custo estimado, phases via subagent/fallback/sdc (v8.0)
- Cynefin classification + dedup check operacional
- Chaotic stabilization protocol — Fase 0.5
- Change Analysis + git forensics (Archaeologist)
- Confidence scoring algorithm normalizado 0-100%
- Knowledge base + SOPs + SOP fast-track + SOP outcome tracking
- Grafos causais AND/OR (Causal Reasoner)
- Debate adversarial + counterfactual (Hypothesis Challenger)
- Swiss Cheese barrier analysis + criticality scoring
- Test gap analysis step-by-step com decision tree
- Evidence grading E1-E4 (Evidence Grading)
- Anti-pattern supersession + registry completeness
- Effectiveness review enforcement
- Alertas adaptativos com SOP effectiveness_rate
- Trend analysis com tag taxonomy controlada
- Escalation criteria codificados — 4 criterios para @architect
- Handoff RCA→SDC operacional — artifact auto-gerado
- Meta-learning com trends e alerts (Meta-Learner)
- Fast tracks por dominio: Clear pula fases 2-6, Chaotic inclui Fase 0.5

---

## Pre-Conditions

- Pelo menos 1 indicio de erro (screenshot, log, stack trace, descricao)
- Acesso ao codebase para leitura

## Post-Conditions

- Problema classificado (Cynefin domain, severity, scope)
- Root cause identificada com grafo causal e evidence grades
- Barreiras de defesa analisadas (Swiss Cheese)
- Bugs classificados (trivial | minor | significativo) e documentados
- Fix aplicado via SDC Bridge com quality gate real (ou inline em preset single)
- Testes automatizados cobrindo o cenario (OBRIGATORIO)
- Relatorio de investigacao v8.0 gerado com pipeline metrics
- Anti-pattern registrado no registry
- Knowledge base atualizada + SOP gerado
- Achados colaterais como stories de backlog + handoff para SDC
- PR criado para main

---

## Documentacao de Bugs — Abordagem Hibrida

| Classificacao | Criterio | Acao |
|--------------|----------|------|
| **Trivial** | 1 arquivo, 1 linha (typo, guard) | Sem story. Documentar no relatorio. |
| **Minor** | Fix comportamental, 1-2 arquivos | Fix no PR do RCA. Story retroativa status=Done na Fase 8. |
| **Significativo** | >2 arquivos, muda comportamento observavel | Story criada ANTES do fix (Fase 7). Se multiplos: 1 story umbrella. |

---

## Fases Operacionais — Multi-Technique v4.0

| Fase | Nome | Agente | Story | Skill Phase |
|------|------|--------|-------|-------------|
| 0 | Classificacao (Cynefin) | @qa | 17.1 | Fase 0 |
| 1 | Coleta de Dados (Archaeology) | @qa | 17.2 | Fase 1 |
| 2 | Pattern Matching | @qa | 17.4 | Fase 2 |
| 3 | Analise Causal (Grafo AND/OR) | @qa | 17.3 | Fase 3 |
| 4 | Desafio de Hipoteses | @qa | 17.5 | Fase 4 |
| 5 | Analise de Barreiras (Swiss Cheese) | @qa | 17.6 | Fase 5 |
| 6 | Classificacao de Evidencia | @qa | 17.7 | Fase 6 |
| 7 | Implementacao (Fix + Testes) | @sm + @dev | — | Fase 7 |
| 8 | Documentacao, QA Gate & Backlog | @qa + @sm | — | Fase 8 |
| 9 | Meta-Learning & Entrega | @qa + @devops | 17.8 | Fase 9 |

### Fast Tracks por Dominio

| Dominio | Fases Executadas | Fases Puladas |
|---------|-----------------|---------------|
| Clear | 0→1→7→8→9 | 2,3,4,5,6 |
| Complicated | 0→1→2→3→5→6→7→8→9 | 4 |
| Complex | Todas (0-9) | Nenhuma |
| Chaotic | Todas (0-9) | Nenhuma (stabilize first) |

### Delegacao Multi-Agente

```
@qa (classifica + investiga + revisa) → @sm (stories) → @dev (implementa) → @qa (QA gate) → @sm (backlog) → @qa (meta-learn) → @devops (entrega)
```

Escalacoes opcionais:
- `@architect` — se problema estrutural identificado na barrier analysis
- `@po` — via handoff SDC para validacao de stories de backlog

---

## Execution Modes

| Modo | Descricao | Quando usar |
|------|-----------|-------------|
| **YOLO** (default) | Execucao continua, zero confirmacoes, fast tracks | Problemas com stack trace claro |
| **Interactive** | Perguntas ao usuario em pontos de duvida | Problemas complexos/ambiguos |
| **Pre-Flight** | Todas as perguntas antes de iniciar | Problemas criticos em producao |

---

## Requisito de Testes

Todo fix DEVE incluir pelo menos 1 teste automatizado. SE nao eh possivel testar (fix puramente visual), o relatorio DEVE documentar o motivo. A secao "Testes Criados" no relatorio eh obrigatoria.

---

## Failure Recovery

| Fase | Falha | Acao |
|------|-------|------|
| 0 (@qa) | Classification falha | ABORT — nenhum codigo alterado |
| 1 (@qa) | Archaeology falha | Continuar sem dados de change |
| 2 (@qa) | Pattern match falha | SKIP — sem knowledge base |
| 3 (@qa) | Causal analysis falha | Fallback para 5 Whys linear |
| 4 (@qa) | Challenge falha | SKIP — aceitar sem challenge |
| 5 (@qa) | Barrier analysis falha | SKIP — apenas recomendar |
| 6 (@qa) | Evidence grading falha | SKIP — sem grading formal |
| 7 (@dev) | Implementacao falha | RETRY 3x → ESCALATE |
| 8 (@qa) | QA gate REJECT | LOOP — @dev corrige |
| 9 (@devops) | Push falha | RETRY quality gates |

---

## Knowledge Base

Investigacoes registradas em `docs/qa/rca-knowledge/`:
- `investigations.yaml` — registry de todas as investigacoes
- `sops/*.yaml` — SOPs executaveis auto-gerados

Knowledge base cresce automaticamente. Permite pattern matching em investigacoes futuras.

---

## Invocacao

```bash
# Via @aios-master (recomendado)
*workflow rca-investigation

# Via @qa
*task rca-investigation

# Standalone (qualquer agente/LLM)
/investigate
```

## Integracao com Workflows

```
Bug reportado → *workflow rca-investigation → classification → investigation → fix → meta-learn → PR
```
