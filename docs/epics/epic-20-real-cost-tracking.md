# Epic 20 — Real Cost Tracking: Visibilidade de custo real por workflow

## Epic Goal

Substituir a estimativa heurística de tokens (`len/4`) por **medição real de custo** integrada com billing da API, com alertas em tempo real, circuit breaker automático, e report de custo por step/workflow/epic.

## Epic Description

### Existing System Context

- **Funcionalidade atual:** Engine v5.0 tem `token_tracking` com heurística `ceil(len(text) / 4)` e custo estimado via fórmula fixa (60% input $3/M + 40% output $15/M)
- **Problema:** Não sabemos quanto um workflow realmente custa. A heurística tem margem de erro de 20-30%. Não diferencia modelos (Opus vs Sonnet vs Haiku). Não há alertas em tempo real — só sabemos do custo ao final do workflow.
- **Cenário de risco:** Epic execution com 10 stories * 7 steps * retries = 200+ subagent calls, potencialmente $30-100 sem visibilidade até acabar

### Enhancement Details

- **O que está sendo feito:** Captura de tokens reais do Task tool response, pricing table por modelo, alertas de threshold, circuit breaker, cost report detalhado
- **Diagnóstico:** Estamos voando cegos em custo. A única proteção é `max_estimated_cost_usd` que usa estimativa, não medição
- **Estratégia:** 2 waves — Medição real → Controle & Alertas
- **Success criteria:** Saber o custo real de cada workflow com precisão >95%, e ser alertado antes de exceder budget

### Architectural Decision

**ADR-020: Real Cost Tracking** (2026-03-30)
- Tokens reais extraídos do Task tool response metadata (input_tokens, output_tokens)
- Pricing table por modelo em `.aios/cost-config.yaml` (atualizável)
- Cost accumulator no state com granularidade: por step, por agent, por workflow
- Circuit breaker: pause automático quando custo real atinge threshold (não estimativa)
- Alternativas descartadas: integração com Anthropic billing API (requer auth, over-engineering), proxy de API (complexidade desnecessária)

---

## Escopo por Wave

### Wave 1 — Medição Real (~3-4 dias)
**Objetivo:** Saber exatamente quanto cada step e workflow custa.

| Story | Item | Impacto | Executor | Estimativa |
|-------|------|---------|----------|------------|
| 20.1 | **Token Extraction from Task Tool** — capturar input_tokens e output_tokens reais do response metadata de cada subagent spawn | Base para tudo — tokens reais em vez de heurística | @dev | M |
| 20.2 | **Model-Aware Pricing Table** — `.aios/cost-config.yaml` com pricing por modelo (opus, sonnet, haiku), atualizável, com fallback para estimativa se modelo desconhecido | Custo calculado corretamente por modelo usado | @dev | S |
| 20.3 | **Cost Accumulator no State** — tracking granular: `cost_tracking.per_step[id]`, `cost_tracking.per_agent[agent]`, `cost_tracking.total_usd`, com input/output tokens separados | Visibilidade total de onde o dinheiro vai | @dev | M |
| 20.4 | **Cost Report no Final Report** — seção detalhada no final report com breakdown por step, por agent, total, e comparação estimado vs real | Report acionável ao final de cada workflow | @dev | M |

### Wave 2 — Controle & Alertas (~2-3 dias)
**Objetivo:** Ser alertado e protegido antes de gastar demais.

| Story | Item | Impacto | Executor | Estimativa |
|-------|------|---------|----------|------------|
| 20.5 | **Real-Time Budget Alerts** — warnings a 50%, 75%, 90% do budget usando custo REAL (não estimado), log no execution_log | Visibilidade durante execução, não só no final | @dev | M |
| 20.6 | **Circuit Breaker** — auto-pause quando custo real atinge limit, com opção de override em yolo mode (`--force-budget`) | Proteção real contra runaway costs | @dev | M |
| 20.7 | **Historical Cost Analytics** — `*workflow-analytics` inclui seção de custo real: tendências, custo médio por story type, agent mais caro, custo por retry | Decisões operacionais informadas por custo real | @dev | M |
| 20.8 | **Cost-Aware Retry Strategy** — adaptive retry considera custo acumulado: se já gastou >80% do budget, skip decomposition retry (level 3) e vai direto para abort | Evita gastar o restante do budget em retries fúteis | @dev | S |

---

## Dependências

### Internas
- 20.1 é fundação (tudo depende de tokens reais)
- 20.2 pode ser paralela com 20.1 (pricing table independente)
- 20.3 depende de 20.1 + 20.2 (accumulator usa ambos)
- 20.4 depende de 20.3 (report lê o accumulator)
- 20.5 depende de 20.3 (alertas usam accumulator)
- 20.6 depende de 20.5 (circuit breaker é extensão dos alertas)
- 20.7 depende de 20.3 (analytics lê dados de custo do state)
- 20.8 depende de 20.3 + 20.6 (retry strategy consulta custo)

### Externas
- Epic 18 (engine v5.0) — **DONE** — base do engine com token_tracking heurístico
- Epic 19 (portabilidade) — independente, pode ser paralelo
- Task tool metadata — depende de Claude Code expor input/output tokens no response

---

## Design Técnico

### 20.1 — Token Extraction

```
FUNCTION extract_real_tokens(task_tool_response):
  # Task tool response inclui metadata com token counts
  IF response.metadata AND response.metadata.usage:
    RETURN {
      input_tokens: response.metadata.usage.input_tokens,
      output_tokens: response.metadata.usage.output_tokens,
      model: response.metadata.model or "unknown"
    }
  ELSE:
    # Fallback para heurística (backward compatible)
    RETURN {
      input_tokens: estimate_tokens(prompt_text),
      output_tokens: estimate_tokens(response_text),
      model: "estimated",
      is_estimated: true
    }
```

### 20.2 — Pricing Table

```yaml
# .aios/cost-config.yaml
cost_tracking:
  enabled: true
  currency: USD
  pricing:
    claude-opus-4:
      input_per_million: 15.00
      output_per_million: 75.00
    claude-sonnet-4:
      input_per_million: 3.00
      output_per_million: 15.00
    claude-haiku-3.5:
      input_per_million: 0.80
      output_per_million: 4.00
    default:  # Fallback
      input_per_million: 15.00   # Assume mais caro (safe)
      output_per_million: 75.00
  budget:
    per_workflow: 10.00    # USD
    per_story: 5.00        # USD
    per_epic: 50.00        # USD
    alert_thresholds: [50, 75, 90]  # percentages
  updated_at: "2026-03-30"
```

### 20.3 — Cost Accumulator (State Extension)

```yaml
# Adicionado ao engine_state:
cost_tracking:
  total_usd: 0.0
  total_input_tokens: 0
  total_output_tokens: 0
  is_all_real: true  # false se algum step usou estimativa
  per_step:
    step_id:
      input_tokens: 1234
      output_tokens: 567
      model: "claude-opus-4"
      cost_usd: 0.061
      is_estimated: false
  per_agent:
    "@dev":
      steps: 3
      total_cost_usd: 0.15
      total_tokens: 5000
    "@qa":
      steps: 2
      total_cost_usd: 0.08
      total_tokens: 3000
```

### 20.6 — Circuit Breaker

```
FUNCTION check_cost_circuit_breaker(state):
  IF NOT state.cost_tracking.enabled:
    RETURN "OK"

  budget = state.cost_config.budget.per_workflow
  current = state.cost_tracking.total_usd

  IF current >= budget:
    IF state.mode == "yolo_continuous" AND NOT state.force_budget:
      log_event(state, "circuit_breaker_triggered", {cost: current, budget: budget})
      ABORT "budget_exceeded_real — actual cost ${current} exceeds ${budget} limit"
    ELIF state.force_budget:
      Log: "⚠️ Budget exceeded but --force-budget active. Continuing."
      RETURN "WARNING"

  RETURN "OK"
```

---

## Riscos e Mitigação

| Risco | Severidade | Mitigação |
|-------|-----------|-----------|
| Task tool não expõe token metadata | ALTO | Fallback para heurística melhorada (20.1 fallback), marcar como `is_estimated` |
| Pricing table desatualizada | MEDIO | `updated_at` field + warning se >30 dias, fácil de atualizar manualmente |
| Circuit breaker interrompe workflow no meio | MEDIO | `--force-budget` override, warning a 50/75/90% antes de breaker |
| Custo de retries não previsível | BAIXO | Story 20.8 integra custo na decisão de retry |

---

## Definition of Done

- [ ] Token count real extraído de cada subagent spawn (ou fallback marcado)
- [ ] Pricing table configurável por modelo em `.aios/cost-config.yaml`
- [ ] Cost accumulator no state com granularidade step + agent
- [ ] Final report inclui seção de custo real com breakdown
- [ ] Alertas em 50%, 75%, 90% do budget durante execução
- [ ] Circuit breaker funcional com override `--force-budget`
- [ ] `*workflow-analytics` inclui tendências de custo real
- [ ] Retry strategy considera custo restante
- [ ] Backward compatible — engine sem cost-config funciona com estimativa

---

## Métricas de Sucesso

| Métrica | Baseline (hoje) | Target |
|---------|-----------------|--------|
| Precisão do custo reportado | ~70% (heurística) | >95% (tokens reais) |
| Tempo para saber custo de um workflow | Nunca (não reportamos) | Tempo real durante execução |
| Workflows que excedem budget sem aviso | 100% (sem alertas) | 0% (circuit breaker) |
| Granularidade do custo | Total estimado | Por step, por agent, por retry |
