---
tools: []
---

# Workflow Status Task

## Purpose

Display the current status of all workflow executions (active, completed, aborted).
Reads state files from `.aios/` and shows a summary table with heartbeat health.

## Task Definition (AIOS Task Format V1.0)

```yaml
task: workflowStatus()
responsavel: Any Agent
responsavel_type: Agente
atomic_layer: Config

**Entrada:**
- campo: filter
  tipo: string
  origem: User Input
  obrigatório: false
  validação: Must be "all", "active", "completed", or "aborted". Default: "all"

**Saída:**
- campo: status_report
  tipo: string
  destino: Output
  persistido: false
```

## Task Execution

```
FUNCTION workflow_status(filter="all"):

  # 1. Scan for engine state files
  state_files = glob(".aios/*-engine-state.yaml") + glob(".aios/*-state.yaml")

  IF state_files is empty:
    Log: "No workflow executions found."
    RETURN

  # 2. Read and filter
  workflows = []
  FOR each file in state_files:
    state = read_yaml(file)
    IF state.workflow_id is null: CONTINUE  # Not a valid engine state

    IF filter != "all" AND state.status != filter: CONTINUE

    # 3. Check health using is_workflow_stale() from Story 26.2
    stale = false
    IF state.status == "active":
      heartbeat = state.heartbeat_at or state.updated_at
      timeout = state.current_step_timeout or 300  # default 5min
      multiplier = 2  # from engine-config stale_detection.multiplier
      age_seconds = (NOW() - parse_iso(heartbeat))
      stale = age_seconds > (timeout * multiplier)

    workflows.append({
      name: state.workflow_name or state.workflow_id,
      instance_id: state.instance_id,
      status: state.status,
      step: "{state.current_step_index or '?'}/{state.action_steps_total or '?'}",
      phase: state.current_phase or "—",
      health: stale ? "⚠️ STALE" : (state.status == "active" ? "✅ alive" : "—"),
      resume_attempts: state.resume_attempts or 0,
      updated: state.heartbeat_at or state.updated_at or state.started_at,
      file: file
    })

  # 3. Sort: active first, then by updated_at desc
  workflows = sort(workflows, key=lambda w: (w.status != "active", -parse_iso(w.updated)))

  # 4. Display
  Log: "=== Workflow Status ==="
  Log: ""

  FOR each wf in workflows:
    status_icon = {active: "🔄", completed: "✅", aborted: "❌", paused: "⏸️"}[wf.status]
    Log: "{status_icon} {wf.name}"
    Log: "   Instance: {wf.instance_id}"
    Log: "   Status: {wf.status} | Step: {wf.step} | Phase: {wf.phase}"
    Log: "   Health: {wf.health} | Resumes: {wf.resume_attempts} | Updated: {wf.updated}"

    IF wf.status == "active" AND wf.health == "⚠️ STALE":
      Log: "   → Resume: *run-workflow {wf.name} continue --mode=engine"
    Log: ""

  # 5. Summary
  active_count = count(workflows WHERE status == "active")
  completed_count = count(workflows WHERE status == "completed")
  aborted_count = count(workflows WHERE status == "aborted")
  stale_count = count(workflows WHERE health == "⚠️ STALE")

  Log: "--- Summary ---"
  Log: "Active: {active_count} ({stale_count} stale) | Completed: {completed_count} | Aborted: {aborted_count}"

  IF stale_count > 0:
    Log: ""
    Log: "⚠️ {stale_count} workflow(s) appear stale. Consider resuming or aborting."
```

## Command

```
*workflow-status [all|active|completed|aborted]
```

## Metadata

```yaml
story: "26.3"
version: 1.0.0
dependencies: []
tags:
  - workflow
  - status
  - monitoring
  - engine
updated_at: 2026-03-31
```
