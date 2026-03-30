# aiox-integration-test — Engine Portability Smoke Test

> **Version:** 1.0
> **Agent:** @aios-master
> **Command:** `*aiox-test [--dry-run] [--keep]`

---

## Purpose

Validate that the AIOX engine works correctly in a clean project by executing a full bootstrap → config → workflow start → step execution → state persistence cycle in a temporary directory.

---

## Synopsis

```
*aiox-test              # Full smoke test with cleanup
*aiox-test --dry-run    # Validate structure only (no workflow execution)
*aiox-test --keep       # Keep temp directory after test (for debugging)
```

---

## Exit Codes

```
0 — All tests passed
1 — Bootstrap failure (aiox init failed)
2 — Config validation failure (engine-config.yaml invalid)
3 — Workflow execution failure (SDC could not start or step failed)
4 — State persistence failure (state file missing or invalid)
```

---

## Test Execution Flow

### STEP 1: Setup

```
FUNCTION aiox_integration_test(args):
  dry_run = args.dry_run OR false
  keep = args.keep OR false

  # Create isolated temp directory
  temp_dir = create_temp_directory("aiox-test-{timestamp}")
  LOG "Test directory: {temp_dir}"

  # Initialize git (engine expects git context)
  run("git init", cwd=temp_dir)
  run("git commit --allow-empty -m 'init'", cwd=temp_dir)

  results = {
    bootstrap: null,
    config: null,
    context: null,
    workflow_load: null,
    step_execution: null,
    state_persistence: null
  }
```

### STEP 2: Bootstrap Test

```
  LOG "TEST 1/6: Bootstrap (aiox init --tier core)"

  # Execute aiox-init logic in temp_dir
  execute_aiox_init(root=temp_dir, tier="core", force=false)

  # Verify directory structure
  ASSERT directory_exists("{temp_dir}/.aios/")
  ASSERT directory_exists("{temp_dir}/.aios/handoffs/")
  ASSERT directory_exists("{temp_dir}/.aios/state/")
  ASSERT directory_exists("{temp_dir}/.aios-core/development/tasks/")
  ASSERT directory_exists("{temp_dir}/.aios-core/development/workflows/")
  ASSERT directory_exists("{temp_dir}/.aios-core/development/agents/")
  ASSERT directory_exists("{temp_dir}/.aios-core/development/templates/")
  ASSERT directory_exists("{temp_dir}/.claude/rules/")

  # Verify key files exist
  ASSERT file_exists("{temp_dir}/.aios/engine-config.yaml")
  ASSERT file_exists("{temp_dir}/.aios/project-context.yaml")
  ASSERT file_exists("{temp_dir}/.aios/agents.yaml")
  ASSERT file_exists("{temp_dir}/.aios-core/development/tasks/run-workflow-engine.md")
  ASSERT file_exists("{temp_dir}/.aios-core/development/workflows/story-development-cycle.yaml")
  ASSERT file_exists("{temp_dir}/.aios-core/development/agents/dev.md")
  ASSERT file_exists("{temp_dir}/.aios-core/development/agents/qa.md")
  ASSERT file_exists("{temp_dir}/.aios-core/development/agents/devops.md")
  ASSERT file_exists("{temp_dir}/.aios-core/development/templates/subagent-step-prompt.md")

  results.bootstrap = PASS
  LOG "  PASS: Bootstrap — all directories and files created"

  ON FAILURE:
    results.bootstrap = FAIL
    LOG "  FAIL: Bootstrap — {error_message}"
    EXIT 1
```

### STEP 3: Config Validation Test

```
  LOG "TEST 2/6: Config validation"

  config = read_yaml("{temp_dir}/.aios/engine-config.yaml")

  # Required top-level sections
  ASSERT "engine" IN config
  ASSERT "execution" IN config
  ASSERT "tokens" IN config
  ASSERT "cost" IN config
  ASSERT "timeouts" IN config
  ASSERT "confidence" IN config
  ASSERT "retry_strategy" IN config

  # Required field values (must match DEFAULT_ENGINE_CONFIG)
  ASSERT config.execution.max_loops_per_target == 4
  ASSERT config.tokens.context_window_limit == 180000
  ASSERT config.cost.max_per_workflow_usd == 10.0
  ASSERT config.timeouts.default_step_seconds == 300
  ASSERT config.confidence.high_threshold == 0.8
  ASSERT config.retry_strategy.default_max_loops == 4

  # Validate types
  ASSERT typeof(config.execution.max_loops_per_target) == "number"
  ASSERT typeof(config.cost.max_per_workflow_usd) == "number"
  ASSERT typeof(config.confidence.high_threshold) == "number"

  results.config = PASS
  LOG "  PASS: Config — all required sections and defaults present"

  ON FAILURE:
    results.config = FAIL
    LOG "  FAIL: Config — {error_message}"
    EXIT 2
```

### STEP 4: Project Context Test

```
  LOG "TEST 3/6: Project context"

  context = read_yaml("{temp_dir}/.aios/project-context.yaml")

  # Must have project section
  ASSERT "project" IN context

  # Required fields (even if "unknown")
  ASSERT "name" IN context.project
  ASSERT "type" IN context.project
  ASSERT "languages" IN context.project
  ASSERT "primary" IN context.project.languages

  # Parseable YAML (no syntax errors)
  ASSERT yaml_valid(context)

  results.context = PASS
  LOG "  PASS: Context — project-context.yaml valid and parseable"

  ON FAILURE:
    results.context = FAIL
    LOG "  FAIL: Context — {error_message}"
    EXIT 2
```

### STEP 5: Workflow Load Test

```
  IF dry_run:
    LOG "TEST 4/6: Workflow load (SKIPPED — dry-run mode)"
    results.workflow_load = SKIP
    GOTO STEP 8

  LOG "TEST 4/6: Workflow load"

  # Create test story
  ensure_directory("{temp_dir}/docs/stories/")
  write_file("{temp_dir}/docs/stories/test.1.smoke-test.story.md", TEST_STORY_CONTENT)

  # Load SDC workflow
  workflow_path = "{temp_dir}/.aios-core/development/workflows/story-development-cycle.yaml"
  workflow = read_yaml(workflow_path)

  # Verify workflow structure
  ASSERT "metadata" IN workflow
  ASSERT "phases" IN workflow OR "steps" IN workflow
  ASSERT workflow.metadata.name IS NOT null

  results.workflow_load = PASS
  LOG "  PASS: Workflow — SDC loaded and parsed correctly"

  ON FAILURE:
    results.workflow_load = FAIL
    LOG "  FAIL: Workflow — {error_message}"
    EXIT 3
```

### STEP 6: Step Execution Test

```
  LOG "TEST 5/6: Step execution"

  # Initialize engine state (simulated)
  state = {
    workflow_name: "story-development-cycle",
    instance_id: "test-smoke-{timestamp}",
    status: "running",
    current_step: 0,
    steps_completed: [],
    execution_log: [],
    config: read_yaml("{temp_dir}/.aios/engine-config.yaml"),
    project_context: read_yaml("{temp_dir}/.aios/project-context.yaml")
  }

  # Write initial state
  state_path = "{temp_dir}/.aios/test-smoke-engine-state.yaml"
  write_yaml(state_path, state)

  # Verify state file was written
  ASSERT file_exists(state_path)
  reloaded = read_yaml(state_path)
  ASSERT reloaded.status == "running"
  ASSERT reloaded.workflow_name == "story-development-cycle"

  # Simulate step completion
  state.steps_completed.append({
    step: "validate",
    status: "completed",
    timestamp: current_timestamp(),
    output: { verdict: "GO", score: 8 }
  })
  state.current_step = 1
  write_yaml(state_path, state)

  results.step_execution = PASS
  LOG "  PASS: Step — state initialized and step logged"

  ON FAILURE:
    results.step_execution = FAIL
    LOG "  FAIL: Step — {error_message}"
    EXIT 3
```

### STEP 7: State Persistence Test

```
  LOG "TEST 6/6: State persistence"

  # Re-read state from disk (simulate engine restart)
  persisted = read_yaml(state_path)

  # Verify all fields survived persistence
  ASSERT persisted.workflow_name == "story-development-cycle"
  ASSERT persisted.instance_id STARTS_WITH "test-smoke-"
  ASSERT persisted.current_step == 1
  ASSERT len(persisted.steps_completed) == 1
  ASSERT persisted.steps_completed[0].step == "validate"
  ASSERT persisted.steps_completed[0].status == "completed"
  ASSERT persisted.config IS NOT null
  ASSERT persisted.project_context IS NOT null

  results.state_persistence = PASS
  LOG "  PASS: State — all fields persisted and recovered correctly"

  ON FAILURE:
    results.state_persistence = FAIL
    LOG "  FAIL: State — {error_message}"
    EXIT 4
```

### STEP 8: Cleanup & Report

```
  # Cleanup
  IF NOT keep:
    delete_directory(temp_dir)
    LOG "Temp directory cleaned up"
  ELSE:
    LOG "Temp directory preserved at: {temp_dir}"

  # Report
  passed = count(results WHERE value == PASS)
  failed = count(results WHERE value == FAIL)
  skipped = count(results WHERE value == SKIP)
  total = passed + failed + skipped

  DISPLAY:
  """
  ==========================================
   AIOX Integration Test Results
  ==========================================

  Tests: {passed}/{total} passed{", {skipped} skipped" IF skipped > 0}

  1. Bootstrap:         {results.bootstrap}
  2. Config:            {results.config}
  3. Context:           {results.context}
  4. Workflow Load:     {results.workflow_load}
  5. Step Execution:    {results.step_execution}
  6. State Persistence: {results.state_persistence}

  {IF failed == 0: "All tests passed — engine is portable!"}
  {IF failed > 0: "FAILURES DETECTED — see logs above"}

  ==========================================
  """

  EXIT {0 IF failed == 0 ELSE max(exit_codes)}
```

---

## Test Story Content

```
TEST_STORY_CONTENT = """
---
id: test.1
title: "Test Story — Smoke Test"
type: feature
status: Ready
executor: "@dev"
quality_gate: "@qa"
---

# Test Story — Smoke Test

## Story
**Como** test harness,
**Quero** uma story minima para validar o engine,
**Para** que o smoke test possa verificar carregamento de workflow.

## Acceptance Criteria
- [ ] AC1: This is a test acceptance criterion
- [ ] AC2: Engine can load this story without errors

## File List
- [ ] test-output.txt
"""
```

---

## Idempotency

- Creates fresh temp directory each run (no collisions)
- Cleanup on success (unless --keep)
- Cleanup on failure (unless --keep)
- No side effects on the host project

---

## Integration with CI/CD

```yaml
# .github/workflows/aiox-test.yml (example)
- name: AIOX Smoke Test
  run: |
    # Execute test harness
    claude --agent @aios-master --command "*aiox-test --dry-run"
```

---

## Timing Budget

| Step | Max Time |
|------|----------|
| Bootstrap | 10s |
| Config validation | 2s |
| Context validation | 2s |
| Workflow load | 5s |
| Step execution | 10s |
| State persistence | 5s |
| Cleanup | 5s |
| **Total** | **< 40s** (dry-run: < 20s) |
