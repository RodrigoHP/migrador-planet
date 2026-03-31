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

Executar `/investigate` (`.claude/commands/investigate.md` v8.1).
O skill contem a metodologia completa de investigacao como pipeline multi-model.
Esta task adiciona orquestracao AIOS multi-agente sobre essa metodologia.

**v8.1 — Multi-Model Pipeline (inclui tudo do v7.0):**
- **Pipeline multi-model** — cada fase como subagent isolado com modelo otimizado
- **Phase contracts** — input/output formal por fase para context isolation
- **Model routing** — configuravel via presets: economy/balanced/quality/single/adaptive (default)
- **Briefing templates** — 9+ prompts autossuficientes para subagents
- **SDC Bridge (Fase 6.5)** — fix via SDC com quality gate real (ou direto sem AIOS)
- **Retry + Fallback** — retry 1x com feedback antes de fallback inline
- **Parallel phases** — Fases 2∥3 rodam em paralelo (~30-40% mais rapido)
- **Adaptive preset** — auto-seleciona por dominio Cynefin (default)
- **Pipeline metrics** — custo estimado, phases via subagent/retry/fallback/sdc
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
- Relatorio de investigacao v8.1 gerado com pipeline metrics
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
| **Significativo** | >2 arquivos, muda comportamento observavel | Story criada ANTES do fix (Fase 6.5). Se multiplos: 1 story umbrella. |

---

## Fases Operacionais — Multi-Model Pipeline v8.1

| Fase | Nome | Executor | Modelo (balanced) |
|------|------|----------|-------------------|
| 0 | Classificacao (Cynefin + Dedup) | subagent | sonnet |
| 0.5 | Stabilization (Chaotic only) | subagent | sonnet |
| 1 | Coleta de Dados (Archaeology) | subagent | haiku |
| 2 | Pattern Matching (Knowledge Base) | subagent | sonnet |
| 3 | Analise Causal (Grafo AND/OR) | subagent | sonnet |
| 4 | Desafio de Hipoteses (Adversarial) | subagent | opus |
| 5 | Analise de Barreiras (Swiss Cheese) | subagent | sonnet |
| 6 | Classificacao de Evidencia (E1-E4) | subagent | opus |
| 6.5 | SDC Bridge (Fix + Testes) | orquestrador | — |
| 8a | Relatorio + Investigation Record | subagent | opus |
| 8b | Anti-patterns + SOPs + Handoff + Backlog | subagent | sonnet |
| 9 | Meta-Learning & Registro | subagent | sonnet |

### Fast Tracks por Dominio

| Dominio | Fases Executadas | Fases Puladas |
|---------|-----------------|---------------|
| Clear | 0→1→6.5(lite)→8a→8b→9 | 2,3,4,5,6 |
| Complicated | 0→1→2∥3→5→6→6.5→8a→8b→9 | 4 |
| Complex | 0→1→2∥3→4→5→6→6.5→8a→8b→9 | Nenhuma |
| Chaotic | 0→0.5→1→2∥3→4→5→6→6.5→8a→8b→9 | Nenhuma |

> `2∥3` = Fases 2 e 3 rodam em paralelo (ambas dependem apenas da Fase 1)

### Pipeline Architecture

```
Orquestrador (Opus) coordena pipeline multi-model:
  → Spawna subagent por fase com briefing autossuficiente
  → Valida output contra phase contracts
  → Retry 1x se falha → Fallback inline se retry falha
  → TODAS as escritas em disco são do orquestrador (subagents retornam YAML)
  → Fase 6.5 (SDC Bridge) executada diretamente pelo orquestrador
```

Escalacoes opcionais:
- `@architect` — se criterios de escalation atingidos na Fase 5
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

## Failure Recovery (v8.1 — Retry + Fallback)

Cada subagent segue: **tentar → retry 1x (prompt simplificado) → fallback inline**

| Fase | Falha subagent | Acao |
|------|---------------|------|
| 0 | Classification falha | RETRY 1x → FALLBACK inline → se inline falha: ABORT |
| 0.5 | Stabilization falha | RETRY 1x → FALLBACK inline |
| 1 | Archaeology falha | RETRY 1x → FALLBACK inline (investigacao manual) |
| 2 | Pattern match falha | RETRY 1x → FALLBACK inline (continuar sem KB) |
| 3 | Causal analysis falha | RETRY 1x → FALLBACK inline (5 Whys linear) |
| 4 | Challenge falha | RETRY 1x → FALLBACK inline (aceitar sem challenge) |
| 5 | Barrier analysis falha | RETRY 1x → FALLBACK inline (recomendar no relatorio) |
| 6 | Evidence grading falha | RETRY 1x → FALLBACK inline (sem grading formal) |
| 6.5 | SDC Bridge falha | Documentar no relatorio, story no backlog |
| 8a | Report falha | RETRY 1x → FALLBACK inline (orquestrador gera) |
| 8b | Knowledge falha | RETRY 1x → FALLBACK inline (orquestrador gera) |
| 9 | Meta-learning falha | RETRY 1x → FALLBACK inline (registro minimo) |

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
