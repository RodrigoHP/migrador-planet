# RCA Investigation — Guia Completo (LEGACY)

> **⚠ LEGACY:** Este guia narrativo é mantido apenas como referência histórica.
> Fonte autoritativa para agentes AI: `.claude/commands/investigate.md` (workflow) + `docs/qa/rca-knowledge/` (knowledge base YAML)

> Root Cause Analysis & Exploratory Investigation
> Versao: 4.0

## Filosofia

**Cada bug eh uma oportunidade de melhoria.** Nunca aplicar band-aid. Todo problema eh investigado ate a origem. A investigacao sempre produz mais do que entrou: alem do fix, documenta achados colaterais, cria testes e alimenta um registro de anti-patterns que previne bugs futuros.

Baseado em praticas de mercado:
- **Cynefin Framework** (Dave Snowden) — classificar antes de investigar
- **Change Analysis** (Meta DrP, HawkEye) — "o que mudou?" antes de "por que?"
- **FTA / Fault Tree Analysis** (Bell Labs) — grafos causais AND/OR
- **GALA** (ICLR 2025) — multi-agent debate, +42% accuracy
- **Swiss Cheese Model** (James Reason) — camadas de defesa com buracos
- **AgentRx** (Microsoft 2026) — evidence chains grounded
- **Flow-of-Action** (WWW 2025) — SOPs auto-gerados, 64% accuracy vs 35% ReAct
- **5 Whys** (Toyota) — perguntar "por que?" (evoluido para multi-branch)
- **Kaizen** (Lean) — melhoria continua a partir de cada defeito
- **Blameless Postmortem** (Google SRE) — investigacao sem culpa

---

## Artefatos

| # | Artefato | Caminho | Source of Truth Para |
|---|----------|---------|---------------------|
| 1 | Skill | `.claude/commands/investigate.md` | Metodologia v4.0 (portavel, qualquer LLM) |
| 2 | Rule | `.claude/rules/rca-principle.md` | Trigger always-on (~5 linhas) |
| 3 | Task | `.aios-core/development/tasks/rca-investigation.md` | Wrapper AIOS (metadata, escalacoes) |
| 4 | Task Audit | `.aios-core/development/tasks/audit-patterns.md` | Busca proativa de anti-patterns |
| 5 | Workflow | `.aios-core/development/workflows/rca-investigation.yaml` | Pipeline operacional v4.0 (10 fases) |
| 6 | Anti-patterns | `docs/qa/known-anti-patterns.md` | Registry que cresce com cada RCA |
| 7 | Knowledge Base | `docs/qa/rca-knowledge/investigations.yaml` | Registry de investigacoes para pattern matching |
| 8 | SOPs | `docs/qa/rca-knowledge/sops/*.yaml` | Procedimentos executaveis auto-gerados |
| 9 | Este guia | `docs/guides/rca-investigation-guide.md` | Documentacao e portabilidade |

**Principio de nao-duplicacao:** O skill contem a metodologia. A task referencia o skill e adiciona apenas metadata AIOS. O workflow define a sequencia operacional com delegacao multi-agente. Nenhum conteudo metodologico eh duplicado entre artefatos.

---

## Modelo Multi-Tecnica v4.0

### Evolucao v3.0 → v4.0

| Aspecto | v3.0 | v4.0 |
|---------|------|------|
| Tecnica | 5 Whys linear | Multi-tecnica adaptativa |
| Primeiro passo | Triagem direta | Classification (Cynefin) |
| Coleta de dados | Manual | Archaeologist automatico (git forensics) |
| Analise causal | 5 Whys (1 cadeia) | Grafo causal AND/OR multi-branch |
| Conhecimento | Anti-patterns manual | Knowledge graph + SOPs auto-gerados |
| Desafio | Nenhum | Hypothesis Challenger adversarial |
| Defesas | Nao analisadas | Barrier Analysis Swiss Cheese |
| Evidencia | Texto livre | Evidence grading E1-E4 com sources |
| Aprendizado | Nenhum | Meta-Learner com trends e alerts |
| Fases workflow | 6 (single technique) | 10 (adaptive por dominio) |

### Agentes Especializados (8 roles)

| Agente | Inspiracao | Funcao |
|--------|-----------|--------|
| **Classifier** (17.1) | Cynefin, GALA, Meta DrP | Classificar antes de investigar |
| **Archaeologist** (17.2) | Change Analysis, DrP, FaR-Loc | Responder "o que mudou?" |
| **Causal Reasoner** (17.3) | FTA, H-SCM, Judea Pearl | Grafos causais AND/OR |
| **Pattern Matcher** (17.4) | Flow-of-Action, Knowledge Graphs | Reutilizar conhecimento |
| **Hypothesis Challenger** (17.5) | GALA, TruEDebate, Amazon COE | Debate adversarial |
| **Barrier Analyst** (17.6) | Swiss Cheese, Defense in Depth | Analisar defesas |
| **Evidence Grader** (17.7) | AgentRx, Medicina baseada em evidencia | Classificar achados |
| **Meta-Learner** (17.8) | Self-Healing, Flow-of-Action, RL | Aprender com cada RCA |

### Mapeamento de Fases

O skill (portavel) usa 10 fases. O workflow (operacional) mapeia para agentes:

| Fase | Skill | Workflow Step | Agente |
|------|-------|--------------|--------|
| 0 | Classificacao | classification | @qa |
| 1 | Coleta de Dados | archaeology | @qa |
| 2 | Pattern Matching | pattern_match | @qa |
| 3 | Analise Causal | causal_analysis | @qa |
| 4 | Desafio de Hipoteses | hypothesis_challenge | @qa |
| 5 | Analise de Barreiras | barrier_analysis | @qa |
| 6 | Classificacao de Evidencia | evidence_grading | @qa |
| 7 | Solucao | create_branch + create_bug_stories + implement_and_test | @sm + @dev |
| 8 | Documentacao & Backlog | documentation + anti_pattern + verify_tests + qa_gate + backlog | @qa + @sm |
| 9 | Meta-Learning & Entrega | meta_learning + push_and_pr | @qa + @devops |

### Fast Tracks por Dominio Cynefin

| Dominio | Fases | Descricao |
|---------|-------|-----------|
| **Clear** | 0→1→7→8→9 | Bug trivial, 3 fases de investigacao |
| **Complicated** | 0→1→2→3→5→6→7→8→9 | Bug analisavel, sem challenge completo |
| **Complex** | 0-9 (todas) | Bug emergente, full pipeline |
| **Chaotic** | 0-9 (todas) | Estabilizar primeiro, depois full |

---

## Documentacao de Bugs — Abordagem Hibrida

| Classificacao | Criterio | Acao | Quando |
|--------------|----------|------|--------|
| **Trivial** | 1 arquivo, 1 linha | Sem story. Documentar no relatorio. | — |
| **Minor** | 1-2 arquivos, fix comportamental | Story retroativa status=Done | Fase 8 |
| **Significativo** | >2 arquivos, muda comportamento | Story ANTES do fix | Fase 7 |

---

## Como Utilizar

### Cenario 1: Bug reportado — workflow automatico

```bash
@aios-master
*workflow rca-investigation
# Colar screenshot/log/descricao do erro
```

**O que acontece automaticamente (10 fases, adaptadas por dominio):**

```
FASE 0 — Classificacao (@qa) [Classifier Agent]
  → Dedup Check (integrado)
  → Cynefin: Clear / Complicated / Complex / Chaotic
  → Severity + Scope
  → Selecao de estrategia + fast track routing

FASE 1 — Coleta de Dados (@qa) [Archaeologist Agent]
  → Git forensics: log, diff, blame
  → Timeline reconstruction
  → Change ranking: top 5 suspeitos
  → Blast radius mapping

FASE 2 — Pattern Matching (@qa) [Pattern Matcher] (skip se Clear)
  → Busca na knowledge base
  → Anti-pattern registry match
  → SOP suggestion se match encontrado

FASE 3 — Analise Causal (@qa) [Causal Reasoner] (skip se Clear)
  → Grafo causal multi-branch
  → Logic gates AND/OR
  → Evidence tagging por node
  → Primary vs contributing root causes

FASE 4 — Desafio de Hipoteses (@qa) [Hypothesis Challenger] (Complex/Chaotic only)
  → Contra-evidencia search
  → Counterfactual analysis
  → Alternative hypotheses
  → Verdicts: CONFIRMED / WEAKENED / REFUTED / INSUFFICIENT

FASE 5 — Analise de Barreiras (@qa) [Barrier Analyst] (skip se Clear)
  → 6 camadas: Code, Test, Static, CI/CD, Monitoring, Process
  → Swiss Cheese alignment summary
  → Recomendacoes: immediate / short-term / long-term

FASE 6 — Classificacao de Evidencia (@qa) [Evidence Grader] (skip se Clear)
  → E1 Confirmed / E2 Correlated / E3 Hypothesized / E4 Speculative
  → Evidence chains com sources citadas
  → Achados refutados como "Discarded"

FASE 7 — Implementacao (@sm + @dev)
  → Branch fix/{slug}
  → Stories conforme threshold
  → Fix na origem + guards + testes + barrier recs immediate

FASE 8 — Documentacao & QA Gate (@qa + @sm)
  → Relatorio v4.0 completo (12 secoes)
  → Anti-pattern registrado
  → Verify tests accountability
  → QA Gate: PASS / CONCERNS / REJECT
  → Stories backlog + handoff SDC

FASE 9 — Meta-Learning & Entrega (@qa + @devops)
  → Knowledge base atualizada
  → SOP auto-gerado (se padrao novo)
  → Trends + alerts (se historico disponivel)
  → Quality gates + Push + PR
```

### Cenario 2: Investigacao manual

```bash
/investigate
# Colar screenshot/log/descricao do erro
```

Util quando quer controlar cada passo ou esta em outro projeto/LLM.

### Cenario 3: Prevencao proativa

```bash
@qa
*audit-patterns              # codebase inteiro
*audit-patterns backend/     # escopo especifico
```

### Cenario 4: Insights do conhecimento acumulado

```bash
@qa
*rca-insights               # trends, effectiveness, scorecard
```

---

## Configuracao Padrao

| Setting | Valor | Onde muda |
|---------|-------|-----------|
| Modo de execucao | YOLO (multi-agente, zero paradas) | `rca-investigation.yaml` → execution_modes |
| Background | Sim | `rca-investigation.yaml` → metadata.run_in_background |
| Elicit | Nao (`false`) | `rca-investigation.yaml` → metadata.elicit |
| Delegacao | Multi-agente com handoffs | `rca-investigation.yaml` → sequence |
| Fast tracks | Por dominio Cynefin | `rca-investigation.yaml` → fast_tracks |
| Knowledge base | `docs/qa/rca-knowledge/` | Auto-populated |
| Push | Sempre via PR | `rca-investigation.yaml` → step push_and_pr |
| Testes | Obrigatorios para cada fix | `rca-investigation.yaml` → step implement_and_test |

---

## Ciclo Virtuoso v4.0

```
REATIVO                              PROATIVO
   │                                    │
   ▼                                    ▼
Bug acontece                    *audit-patterns
   │                                    │
   ▼                                    ▼
Fase 0: Classificacao           Encontra codigo vulneravel
   │                                    │
   ▼                                    ▼
Fases 1-6: Investigacao         Stories preventivas
   │                                    │
   ▼                                    ▼
Fase 7: Fix + Testes            Padrao detectado: alerta
   │                                    │
   ▼                                    ▼
Fase 8: Docs + QA Gate          ◄── known-anti-patterns.md
   │                                    ▲
   ▼                                    │
Fase 9: Meta-Learn ──────────►  Knowledge base atualizada
   │                            SOP gerado
   ▼                            Trends + alerts
Entrega (PR)                    *rca-insights
```

---

## Evidence Grading System

| Nivel | Nome | Criterio | Confidence Range |
|-------|------|----------|-----------------|
| E1 | **Confirmed** | Reproduzido por teste/git bisect | 0.90-1.0 |
| E2 | **Correlated** | Dados sugerem forte correlacao | 0.60-0.89 |
| E3 | **Hypothesized** | Teoria plausivel sem evidencia | 0.30-0.59 |
| E4 | **Speculative** | Possibilidade remota | 0.00-0.29 |

Source types aceitos: `git_diff`, `git_bisect`, `test_reproduction`, `log_analysis`, `code_analysis`, `coverage_report`, `manual_verification`.

---

## Licoes do v2.0 e v3.0

### v2.0 → v3.0 (9 gaps corrigidos)

| # | Gap | Fix v3.0 |
|---|-----|----------|
| 1 | Fases desalinhadas | 6 fases alinhadas com agentes |
| 2 | Single-agent ficticio | Multi-agent real com handoffs |
| 3 | Testes nao criados | Merge com implement + verify_tests |
| 4 | QA Gate nunca executado | QA gate real por @qa |
| 5 | Dedup check pulado | Movido para dentro da Fase 1 |
| 6 | Conteudo duplicado | Task vira wrapper fino |
| 7 | Stories sem handoff | Handoff artifact para SDC |
| 8 | YOLO pedia confirmacao | `elicit: false` + `yolo_behavior` por step |
| 9 | Bugs nao documentados | Threshold hibrido (trivial/minor/significativo) |

### v3.0 → v4.0 (Epic 17: Multi-Technique Agent-First)

| # | Limitacao v3.0 | Solucao v4.0 | Story |
|---|---------------|-------------|-------|
| 1 | 5 Whys indiscriminado | Cynefin classification + fast tracks | 17.1 |
| 2 | Investigacao sem dados | Archaeologist git forensics automatico | 17.2 |
| 3 | 5 Whys linear (1 cadeia) | Grafo causal AND/OR multi-branch | 17.3 |
| 4 | Cada RCA comeca do zero | Knowledge base + SOPs + pattern matching | 17.4 |
| 5 | Aceita primeira hipotese | Hypothesis Challenger adversarial | 17.5 |
| 6 | Nao analisa defesas | Barrier Analysis Swiss Cheese 6 camadas | 17.6 |
| 7 | Fatos e teorias misturados | Evidence grading E1-E4 com sources | 17.7 |
| 8 | Sem aprendizado entre RCAs | Meta-Learner: trends, SOPs, alerts, scorecard | 17.8 |
| 9 | Artefatos desalinhados | Integration: skill+workflow+task+guia v4.0 | 17.9 |

---

## Feito (historico completo)

| Melhoria | Versao |
|----------|--------|
| Multi-agent real com handoffs | v3.0 |
| Testes obrigatorios | v3.0 |
| YOLO verdadeiro | v3.0 |
| Handoff SDC | v3.0 |
| Eliminacao de duplicacao | v3.0 |
| Bug stories threshold | v3.0 |
| QA gate real | v3.0 |
| Engine yolo_continuous (16.1) | v3.0 |
| Engine timeout por step (16.2) | Engine v4.0 |
| Engine token tracking (16.3) | Engine v4.0 |
| Engine observability (16.4) | Engine v4.0 |
| Engine parse failure retry (16.5) | Engine v4.0 |
| Engine state locking (16.6) | Engine v4.0 |
| Engine output validation (16.7) | Engine v4.0 |
| Engine handoff edge cases (16.8) | Engine v4.0 |
| Engine global limits (16.9) | Engine v4.0 |
| Engine routing defaults (16.10) | Engine v4.0 |
| Cynefin classification (17.1) | **v4.0** |
| Archaeologist git forensics (17.2) | **v4.0** |
| Causal Reasoner AND/OR (17.3) | **v4.0** |
| Pattern Matcher knowledge base (17.4) | **v4.0** |
| Hypothesis Challenger (17.5) | **v4.0** |
| Barrier Analyst Swiss Cheese (17.6) | **v4.0** |
| Evidence Grading E1-E4 (17.7) | **v4.0** |
| Meta-Learner trends+SOPs (17.8) | **v4.0** |
| Integration v4.0 (17.9) | **v4.0** |

### Melhorias futuras

| Melhoria | Esforco | Impacto |
|----------|---------|---------|
| Anti-patterns com auto-fix | Medio | Alto |
| Integrar `*audit-patterns` no CI/CD | Medio | Alto |
| Cross-project knowledge base | Medio | Alto |
| Dashboard visual de saude | Alto | Alto |
| Anti-patterns como linter rules | Alto | Muito alto |
| Embeddings vetoriais para pattern matching | Medio | Medio |
| Integracao com monitoring (Sentry, Datadog) | Medio | Alto |

---

## Instalacao

> Copie esta secao inteira e cole na LLM do projeto destino com o comando:
> "Instale o sistema RCA Investigation neste projeto seguindo as instrucoes abaixo."

### Nivel 1: Qualquer LLM (minimo — 1 arquivo)

| Destino | Instrucao |
|---------|-----------|
| Claude Code | Criar `.claude/commands/investigate.md` |
| Cursor | Criar `.cursor/rules/investigate.md` |
| Codex CLI | Adicionar no `AGENTS.md` |
| ChatGPT/Gemini | Custom Instructions ou system prompt |

### Nivel 2: Claude Code (recomendado — 2 arquivos)

1. `.claude/commands/investigate.md` — Skill v4.0
2. `.claude/rules/rca-principle.md` — Rule always-on

### Nivel 3: Claude Code + AIOS (completo — 9 arquivos)

1. `.claude/commands/investigate.md` — Skill v4.0
2. `.claude/rules/rca-principle.md` — Rule
3. `.aios-core/development/tasks/rca-investigation.md` — Task wrapper
4. `.aios-core/development/tasks/audit-patterns.md` — Audit proativo
5. `.aios-core/development/workflows/rca-investigation.yaml` — Workflow v4.0
6. `docs/qa/known-anti-patterns.md` — Registry
7. `docs/qa/rca-knowledge/investigations.yaml` — Knowledge base
8. `docs/qa/rca-knowledge/sops/` — SOPs directory
9. `docs/guides/rca-investigation-guide.md` — Este guia

---

## Referencia Rapida

```bash
# Bug reportado → automatico (YOLO, multi-tecnica)
@aios-master → *workflow rca-investigation

# Bug reportado → manual
/investigate

# Prevencao proativa
@qa → *audit-patterns

# Insights do conhecimento
@qa → *rca-insights

# Adicionar anti-pattern manualmente
Editar docs/qa/known-anti-patterns.md
```
