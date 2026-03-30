# Epic 18 — Adaptive Engine: Feedback Intelligence & Learning System

## Epic Goal

Transformar o workflow engine yolo_continuous de um **executor deterministico** (executa a receita como escrita) em um **executor adaptativo** que aprende com cada execucao, injeta contexto de falhas nos retries, consome handoffs de forma programatica, e melhora progressivamente sua taxa de sucesso.

## Epic Description

### Existing System Context

- **Funcionalidade atual:** Workflow engine v4.0 (Epic 16) com yolo_continuous, 10 features de robustez (timeout, token tracking, observability, error recovery, state locking, output validation, handoff edge cases, global limits, routing defaults). RCA Investigation v4.0 (Epic 17) multi-tecnica agent-first.
- **Technology stack:** AIOS Framework (agents YAML, tasks MD, workflows YAML), Claude Code Task tool (subagent spawning), state persistence em `.aios/`
- **Integration points:** `run-workflow-engine.md` (1643 linhas), `subagent-step-prompt.md` (template), `.aios/handoffs/` (artifacts), `.aios/*-state.yaml` (persistence)
- **Referencia:** Stories 16.1-16.10 (engine v4.0), Story 11.3 (development-cycle.yaml)

### Enhancement Details

- **O que esta sendo adicionado:** 10 features de inteligencia adaptativa organizadas em 3 waves — Feedback Intelligence, Adaptive Engine, Learning System
- **Diagnostico:** O engine v4.0 e robusto mecanicamente (retry, timeout, loop guard) mas opera sem memoria entre execucoes. Retries usam mesma estrategia sempre. Handoffs sao gerados mas nao consumidos. Dois workflows de development cycle coexistem com gaps entre si.
- **Estrategia:** 3 waves incrementais — cada wave adiciona uma camada de inteligencia sobre a anterior
- **Success criteria:** Reducao mensuravel na taxa de abort, eliminacao de retries identicos, continuidade de contexto entre agentes, e visibilidade operacional agregada

### Architectural Decision

**ADR-018: Adaptive Engine Architecture** (2026-03-30)
- Feedback injection no Subagent Prompt Builder (template variable `{{FAILURE_CONTEXT}}`)
- Handoff consumption integrada no prompt builder (template variable `{{HANDOFF_DATA}}`)
- Execution Intelligence como arquivo YAML persistente (`.aios/execution-intelligence.yaml`)
- Confidence scoring como campo opcional no `step_output` schema
- Parallel execution via multiplos Task tool calls simultaneos
- Alternativas descartadas: LLM-based retry selection (over-engineering), external DB para analytics (desnecessario no volume atual)

---

## Escopo por Wave

### Wave 1 — Feedback Intelligence (~3-4 dias)
**Objetivo:** Retries informados, handoffs consumidos, workflow unificado.

| Story | Item | Impacto | Executor | Quality Gate | Estimativa |
|-------|------|---------|----------|--------------|------------|
| 18.1 | **Failure Context Injection** — injetar qa_report/failure_reason no prompt de retry | Retries deixam de ser "tente de novo" e passam a ser "corrija X" | @dev | @architect | M |
| 18.2 | **Handoff Consumption** — engine injeta handoff artifact no subagent prompt via template | Agentes recebem contexto do anterior em vez de comecar do zero | @dev | @architect | S |
| 18.3 | **Workflow Unification** — merge story-development-cycle + development-cycle em um workflow canonico | Fim da fragmentacao, self-healing e push funcionam no yolo | @dev | @architect | M |

### Wave 2 — Adaptive Engine (~4-5 dias)
**Objetivo:** Engine que ajusta comportamento baseado em sinais de qualidade.

| Story | Item | Impacto | Executor | Quality Gate | Estimativa |
|-------|------|---------|----------|--------------|------------|
| 18.4 | **Adaptive Retry Strategy** — 3 niveis progressivos: contexto, simplificacao, decomposicao | Taxa de abort cai porque abordagens diferentes sao tentadas | @dev | @architect | L |
| 18.5 | **Confidence Scoring** — steps retornam confidence 0-1, engine age baseado no score | Problemas pegos antes de chegar no QA, menos ciclos desperdicados | @dev | @architect | M |
| 18.6 | **Project Context Injection** — warm-up automatico com tech stack, patterns, arquitetura | Subagentes comecam sabendo o contexto do projeto, menos redescoberta | @dev | @architect | S |

### Wave 3 — Learning System (~5-6 dias)
**Objetivo:** Sistema que aprende e melhora a cada execucao.

| Story | Item | Impacto | Executor | Quality Gate | Estimativa |
|-------|------|---------|----------|--------------|------------|
| 18.7 | **Execution Intelligence** — aprendizado cross-execucao, padroes de falha acumulados | Erros repetitivos eliminados progressivamente entre runs | @dev | @architect | L |
| 18.8 | **Workflow Analytics** — metricas agregadas de agente, step, custo, tendencias | Decisoes operacionais informadas por dados reais | @dev | @architect | M |
| 18.9 | **Auto Post-Mortem** — artefato estruturado de falha com recommendations | Proximo run recebe sugestoes de ajuste do run anterior que falhou | @dev | @architect | M |
| 18.10 | **Parallel Step Execution** — steps independentes executam em paralelo via Task tool | Workflows ate 40% mais rapidos quando steps sao paralelizaveis | @dev | @architect | L |

---

## Dependencias

### Internas (dentro do Epic)
- 18.1 e 18.2 sao independentes (podem ser paralelas)
- 18.3 depende de 18.1 e 18.2 (unificacao incorpora as novas features)
- 18.4 depende de 18.1 (retry adaptativo precisa de failure context)
- 18.5 e 18.6 sao independentes de 18.4
- 18.7 depende de 18.8 (intelligence usa analytics como fonte)
- 18.9 depende de 18.7 (post-mortem alimenta intelligence)
- 18.10 e independente (pode ser desenvolvida a qualquer ponto)

### Externas
- Epic 16 (engine v4.0) — **DONE** — base do engine
- Epic 17 (RCA v4.0) — **DONE** — workflow que mais se beneficia
- `run-workflow-engine.md` — arquivo principal a ser modificado
- `subagent-step-prompt.md` — template que recebe novas variaveis

---

## Riscos e Mitigacao

| Risco | Severidade | Mitigacao |
|-------|-----------|-----------|
| Prompt inflado com muito contexto (failure + handoff + project) | MEDIO | Token budget por secao: max 500 tokens failure, 300 handoff, 200 project |
| Execution intelligence stale/incorreta | MEDIO | TTL em cada entrada, limpeza automatica apos 30 dias |
| Parallel execution com race conditions no state file | ALTO | State locking v2: lock por step, nao por workflow. Merge de outputs apos grupo completar |
| Confidence scoring ignorado pelos subagentes | BAIXO | Campo opcional com fallback: se ausente, assume 1.0 (backward compatible) |
| Workflow unification quebra runs existentes | MEDIO | Manter backward compat: IDs antigos redirecionam pro novo workflow |

---

## Definition of Done

- [ ] Todas as 10 stories completas com acceptance criteria atendidos
- [ ] Engine v5.0 executa todos os workflows existentes sem regressao
- [ ] Retry com failure context demonstrado em pelo menos 1 workflow real
- [ ] Handoff artifacts consumidos e visiveis no prompt dos subagentes
- [ ] Workflow unificado substitui os dois anteriores
- [ ] Analytics command funcional com dados reais de execucoes passadas
- [ ] Documentacao do engine atualizada (run-workflow-engine.md)
- [ ] Zero regressao nos workflows existentes (RCA, SDC)

---

## Metricas de Sucesso

| Metrica | Baseline (v4.0) | Target (v5.0) |
|---------|-----------------|---------------|
| Taxa de abort por max_loops | ~25% dos runs | < 10% |
| Retries identicos (mesmo output) | Nao medido | 0 (cada retry diferente) |
| Tempo medio por story (SDC) | ~14 min | < 10 min |
| First-try success rate | ~85% | > 92% |
| Context warm-up time (1st step) | ~30s redescoberta | < 5s (pre-injetado) |

---

## Metadata

| Campo | Valor |
|-------|-------|
| Epic ID | 18 |
| Titulo | Adaptive Engine: Feedback Intelligence & Learning System |
| Criado | 2026-03-30 |
| Autor | @pm (Morgan) com analise de @aios-master (Orion) |
| Status | Draft |
| Branch | `feature/epic-18-adaptive-engine` |
| Stories | 10 |
| Waves | 3 |
| Estimativa total | 12-15 dias |
