# Engine Metrics — Visualizar metricas agregadas do engine

```yaml
task: engineMetrics()
responsavel: Any Agent
responsavel_type: Agente
atomic_layer: Atom

inputs: []

outputs:
  - campo: metrics_summary
    tipo: text
    destino: stdout
    persistido: false
```

---

## Objetivo

Exibir um resumo formatado das metricas historicas agregadas de todas as execucoes do workflow engine, lidas de `.aios/engine-metrics.yaml`.

---

## Comando

```
*engine-metrics
```

---

## Execucao

### Passo 1 — Ler arquivo de metricas

1. Verificar se `.aios/engine-metrics.yaml` existe
2. Se NAO existe:
   - Exibir: "No engine metrics found. Metrics are automatically collected after the first workflow execution."
   - RETURN
3. Ler o arquivo YAML

### Passo 2 — Exibir resumo global

Formato:

```
=== Engine Metrics Summary ===
Updated: {updated_at}

--- Global ---
  Total runs:      {global.total_runs}
  Completed:       {global.total_completed}
  Aborted:         {global.total_aborted}
  Success rate:    {global.success_rate * 100}%
  Total cost:      ${global.total_estimated_cost_usd}
  Avg duration:    {global.avg_duration_minutes} min
```

### Passo 3 — Exibir breakdown por workflow

Para cada entrada em `by_workflow`:

```
--- By Workflow ---
  {workflow_id}:
    Runs: {total_runs} | Completed: {total_completed} | Aborted: {total_aborted}
    Success rate: {success_rate * 100}% | Avg duration: {avg_duration_minutes} min
    Avg cost: ${avg_estimated_cost_usd}
```

### Passo 4 — Exibir execucoes recentes

Lista as ultimas execucoes de `recent_runs` (max 20):

```
--- Recent Runs (last {N}) ---
  {completed_at} | {workflow_id} | {instance_id} | {status} | {duration_minutes} min | ${estimated_cost_usd}
  ...
```

---

## Notas

- Este comando eh somente leitura — nao modifica nenhum arquivo
- O arquivo `.aios/engine-metrics.yaml` eh atualizado automaticamente pela funcao `update_engine_metrics()` no `run-workflow-engine.md` (Story 26.6)
- Se o arquivo estiver corrompido ou invalido, exibir erro amigavel e sugerir deletar para recriacao automatica
