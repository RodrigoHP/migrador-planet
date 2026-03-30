# Workflow Analytics Task

> **Story:** 18.8 — Engine Workflow Analytics
> **Agent:** @aios-master
> **Command:** `*workflow-analytics`

## Purpose

Aggregate metrics from all engine state files (`.aios/*-engine-state.yaml`) and generate a comprehensive analytics report.

## Process

1. **Scan state files:** Read all `*-engine-state.yaml` files from `.aios/` directory
2. **Parse and validate:** Parse each YAML file, skip invalid/incomplete files gracefully
3. **Aggregate metrics** across all executions
4. **Generate report** in the format below

## Report Format

```
=== Workflow Analytics Report ===
Generated: {ISO timestamp}
Data source: {count} engine state files in .aios/

--- Performance ---
  Total workflow runs: {count}
  Completed: {count} | Aborted: {count}
  Avg time/workflow: {duration}
  Fastest run: {workflow_name} ({duration})
  Slowest run: {workflow_name} ({duration})

--- Agent Performance ---
  | Agent | Steps | Avg Time | Retry Rate | First-Try % | Avg Confidence |
  |-------|-------|----------|------------|-------------|----------------|
  | @dev  | 15    | 45s      | 13%        | 87%         | 0.85           |
  | @qa   | 8     | 30s      | 5%         | 95%         | 0.92           |
  ...

--- Failure Patterns (Top 5) ---
  1. {pattern_description} — {occurrences}x ({workflow}:{step})
  2. ...

--- Cost ---
  Total estimated: ${total}
  Avg per workflow: ${avg}
  Avg per story: ${avg_story}
  Trend: {increasing|decreasing|stable} (last 5 runs)

--- Retry Analysis ---
  Parse retries: {count} ({percentage}%)
  Output retries: {count} ({percentage}%)
  QA reject loops: {count} ({percentage}%)
  Timeout retries: {count} ({percentage}%)
  Total retries: {count}

--- Abort Analysis ---
  Total aborts: {count}
  By reason:
    qa_reject_loop: {count}
    timeout: {count}
    budget: {count}
    parse_failure: {count}
    state_conflict: {count}
```

## Aggregation Logic

```
FUNCTION generate_analytics():
  state_files = glob(".aios/*-engine-state.yaml")
  IF state_files is empty:
    PRINT "No data available — no engine state files found in .aios/"
    RETURN

  runs = []
  FOR file IN state_files:
    TRY:
      state = read_yaml(file)
      IF state.workflow_id AND state.started_at:
        runs.append(state)
    CATCH:
      Log: "⚠️ Skipping invalid state file: {file}"
      CONTINUE

  IF runs is empty:
    PRINT "No valid engine state files found"
    RETURN

  # Performance
  completed = [r for r in runs if r.status == "completed"]
  aborted = [r for r in runs if r.status == "aborted"]
  durations = [r.completed_at - r.started_at for r in runs if r.completed_at]

  # Agent Performance
  agent_stats = {}
  FOR run IN runs:
    FOR step_id, result IN run.step_results:
      agent = result.agent
      IF agent not in agent_stats:
        agent_stats[agent] = { steps: 0, total_time: 0, retries: 0, first_try: 0, confidences: [] }
      stats = agent_stats[agent]
      stats.steps += 1
      stats.total_time += result.elapsed_ms or 0
      IF result.retries > 0:
        stats.retries += 1
      ELSE:
        stats.first_try += 1
      IF result.confidence:
        stats.confidences.append(result.confidence)

  # Failure Patterns (from execution_intelligence if available)
  # Cost (from token_tracking)
  # Retry Analysis (from retries, parse_retries, output_retries)
  # Abort Analysis (from aborted runs)

  FORMAT and PRINT report
```

## Edge Cases

- **0 state files:** Show "No data available" message (AC8)
- **Partial/incomplete state files:** Skip gracefully, log warning (AC9)
- **Missing fields:** Use defaults (0 for counts, "N/A" for strings)
- **Intelligence integration:** If `.aios/execution-intelligence.yaml` exists, include failure patterns from there (AC10)

## Dependencies

- Reads: `.aios/*-engine-state.yaml` (all state files)
- Reads: `.aios/execution-intelligence.yaml` (optional, for failure patterns)
- Writes: None (display only)
