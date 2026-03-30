---

## Execution Modes

**This task always runs in Engine Mode** — real subagent spawning via Task tool.

For guided automation (persona-switching), use `run-workflow.md` directly.

---

## Task Definition (AIOS Task Format V1.0)

```yaml
task: runWorkflowEngine()
responsavel: Orion (Commander)
responsavel_type: Agente
atomic_layer: Config

**Entrada:**
- campo: workflow_name
  tipo: string
  origem: Delegated from run-workflow.md
  obrigatório: true
  validação: Must match an existing workflow YAML file

- campo: target_context
  tipo: string
  origem: Delegated from run-workflow.md
  obrigatório: false
  validação: Must be "core", "squad", or "hybrid". Default: "core"

- campo: squad_name
  tipo: string
  origem: Delegated from run-workflow.md
  obrigatório: false (required when target_context="squad" or "hybrid")
  validação: Must be kebab-case, squad must exist in squads/

- campo: action
  tipo: string
  origem: Delegated from run-workflow.md
  obrigatório: false
  validação: Must be "start", "continue", "yolo_continuous", "status", "skip", or "abort". Default: "continue"

**Saída:**
- campo: workflow_state
  tipo: object
  destino: File system (.aios/{instance-id}-engine-state.yaml)
  persistido: true

- campo: execution_report
  tipo: object
  destino: Output
  persistido: false

- campo: step_outputs
  tipo: map
  destino: In-memory state (passed between steps)
  persistido: true (in state file)
```

---

## Pre-Conditions

```yaml
pre-conditions:
  - [ ] workflow_name must resolve to an existing YAML file
    tipo: pre-condition
    blocker: true
    validação: |
      Check workflow file exists at resolved path
    error_message: "Pre-condition failed: Workflow '{workflow_name}' not found"
  - [ ] When target_context="squad" or "hybrid", squad directory must exist
    tipo: pre-condition
    blocker: true
    validação: |
      If target_context is "squad" or "hybrid", verify squads/{squad_name}/ exists
    error_message: "Pre-condition failed: Squad '{squad_name}' not found"
  - [ ] For action=continue/status/skip/abort, an active engine state file must exist
    tipo: pre-condition
    blocker: true
    validação: |
      Check .aios/{instance-id}-engine-state.yaml exists with status=active
    error_message: "Pre-condition failed: No active engine workflow instance found. Use action=start first."
  - [ ] Task tool must be available for subagent spawning
    tipo: pre-condition
    blocker: true
    validação: |
      Verify Task tool is accessible in the current Claude Code session
    error_message: "Pre-condition failed: Task tool not available"
```

---

## Post-Conditions

```yaml
post-conditions:
  - [ ] All non-optional steps completed or workflow aborted with report
    tipo: post-condition
    blocker: true
    validação: |
      Verify all required steps have status: completed in state
    error_message: "Post-condition failed: Not all steps completed"
  - [ ] State file created with all step outputs
    tipo: post-condition
    blocker: true
    validação: |
      Verify .aios/{instance-id}-engine-state.yaml exists and contains outputs
    error_message: "Post-condition failed: State file not written"
```

---

## Acceptance Criteria

```yaml
acceptance-criteria:
  - [ ] Each action step spawned a real subagent via Task tool
    tipo: acceptance-criterion
    blocker: true
    validação: |
      Each step with an agent was executed as a separate Task tool call
    error_message: "Acceptance criterion not met: Steps were not spawned as real subagents"
  - [ ] Outputs from previous steps were correctly passed to subsequent steps
    tipo: acceptance-criterion
    blocker: true
    validação: |
      Verify requires chain: each step received the outputs it depends on
    error_message: "Acceptance criterion not met: Output chain broken"
  - [ ] Decision routing evaluated correctly based on thresholds
    tipo: acceptance-criterion
    blocker: true
    validação: |
      Verify routing decisions match the conditions defined in the workflow
    error_message: "Acceptance criterion not met: Routing decisions incorrect"
```

---

## Tools

- **Tool:** Task tool (Claude Code built-in)
  - **Purpose:** Spawn real subagents with isolated context
  - **Source:** Claude Code runtime

- **Tool:** AskUserQuestion (Claude Code built-in)
  - **Purpose:** Collect elicitation inputs before spawning subagents
  - **Source:** Claude Code runtime

- **Tool:** Read tool (Claude Code built-in)
  - **Purpose:** Read agent files, task files, data files, workflow YAML
  - **Source:** Claude Code runtime

- **Tool:** workflow-state-manager
  - **Purpose:** Create and manage workflow state
  - **Source:** .aios-core/development/scripts/workflow-state-manager.js

- **Tool:** workflow-validator
  - **Purpose:** Validate workflow before starting
  - **Source:** .aios-core/development/scripts/workflow-validator.js

---

## Error Handling

**Strategy:** retry-then-fallback

**Common Errors:**

1. **Error:** Subagent returns no YAML block
   - **Cause:** Subagent did not follow output format instructions
   - **Resolution:** Attempt regex extraction of step_output from response
   - **Recovery:** If extraction fails, re-spawn with explicit format reminder; after max_retries, request manual intervention

2. **Error:** Subagent returns status: failed
   - **Cause:** Task execution failed within the subagent
   - **Resolution:** Check global_error_handling.max_retries_per_phase
   - **Recovery:** Re-spawn with previous error as additional context; after max_retries, follow fallback strategy

3. **Error:** Routing condition cannot be evaluated
   - **Cause:** Required value missing from state or no route matches
   - **Resolution:** Display current values to user
   - **Recovery:** Ask user to choose route manually

4. **Error:** Agent file not found
   - **Cause:** Agent referenced in step doesn't exist at resolved path
   - **Resolution:** Check hybrid fallback paths
   - **Recovery:** List available agents and ask user to choose

5. **Error:** Task file not found (uses field)
   - **Cause:** Task referenced in step's 'uses' field doesn't exist
   - **Resolution:** Check alternate paths
   - **Recovery:** Skip task content in prompt (agent persona alone may suffice)

---

## Performance

```yaml
duration_per_invocation: 1-5 min (single step spawn + execution)
cost_per_step: $0.01-0.10 (one API call per action step)
token_usage: ~2,000-10,000 tokens per subagent call
total_cost: Depends on workflow (N steps × cost_per_step)
```

---

## Metadata

```yaml
story: "16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7, 16.8, 16.9, 16.10, 18.1, 18.2"
version: 5.0.0
dependencies:
  - run-workflow.md (delegates to this task)
  - subagent-step-prompt.md (template for prompt building)
  - workflow-state-manager.js
  - workflow-validator.js
tags:
  - workflow
  - engine
  - subagent
  - spawn
  - orchestration
  - runtime
updated_at: 2026-03-30
```

---

# Workflow Runtime Engine Task

## Purpose

Execute workflows by spawning **real subagents** via the Task tool. Supports two execution modes:

- **Step-by-step** (actions: `start`, `continue`): Processes ONE action step per invocation, stops for user validation between steps.
- **YOLO continuous** (action: `yolo_continuous`): Executes ALL steps sequentially without stopping, with automatic handoff artifact generation between agent transitions and loop guards for failure recovery.

Unlike guided mode (persona-switching), each agent runs in its own context with full persona fidelity and zero contamination from other steps.

## Prerequisites

- Workflow YAML validated and accessible
- Template: `subagent-step-prompt.md` available at `.aios-core/development/templates/`
- Agent files accessible at resolved paths
- Task files accessible at resolved paths (via `uses` field)

---

## Engine Constants & Functions (Stories 16.2–16.10)

### Timeout Resolution (Story 16.2)

```
ENGINE_DEFAULT_TIMEOUT = 300  # 5 minutes (seconds)

FUNCTION resolve_timeout(step, workflow, state):
  # Precedence: step > workflow > engine default
  IF step.timeout exists:
    RETURN step.timeout
  IF workflow.metadata.default_step_timeout exists:
    RETURN workflow.metadata.default_step_timeout
  RETURN ENGINE_DEFAULT_TIMEOUT
```

Timeout only applies in `yolo_continuous` mode. Step-by-step mode is NOT affected.

### Token Estimation (Story 16.3)

```
FUNCTION estimate_tokens(text):
  # Heuristic: ~1 token per 4 characters (conservative)
  RETURN ceil(len(text) / 4)

FUNCTION check_token_limits(state, prompt_text):
  estimated = estimate_tokens(prompt_text)
  state.token_tracking.per_step[current_step_id] = estimated
  state.token_tracking.total_estimated += estimated
  limit = state.token_tracking.context_window_limit

  IF state.token_tracking.total_estimated >= limit:
    Log: "❌ Context window limit exceeded — aborting"
    RETURN "ABORT"

  IF state.token_tracking.total_estimated >= limit * 0.8:
    IF "80_percent" not in state.token_tracking.warnings_issued:
      Log: "⚠️ Token usage at 80% of limit ({total}/{limit})"
      state.token_tracking.warnings_issued.append("80_percent")

  RETURN "OK"

FUNCTION truncate_requires_output(output_value, max_tokens=2000):
  estimated = estimate_tokens(output_value)
  IF estimated <= max_tokens:
    RETURN output_value
  # Truncate preserving keys: if YAML, keep key names and truncate values
  max_chars = max_tokens * 4
  RETURN output_value[:max_chars] + "\n... [truncated from {estimated} to {max_tokens} tokens]"

FUNCTION enforce_handoff_max_size(text, max_chars=500):
  IF len(text) <= max_chars:
    RETURN text
  RETURN text[:max_chars - 15] + "... [truncated]"
```

**Configuration:** `context_window_limit` is configurable in the workflow metadata (default: 180000).

### Observability & Execution Log (Story 16.4)

```
FUNCTION log_event(state, event_type, fields):
  event = {
    timestamp: ISO_NOW(),
    event: event_type,
    ...fields
  }
  state.execution_log.append(event)

# Event types:
#   step_started, step_completed, step_failed, step_timeout,
#   handoff_generated, loop_guard_warning, hang_warning,
#   workflow_aborted, workflow_completed, parse_failure_retry,
#   output_validation_failed, output_validation_retry,
#   routing_fallback, handoff_write_failed, state_conflict,
#   token_warning, global_limit_warning, global_limit_exceeded

FUNCTION emit_progress(state, step, elapsed_ms):
  completed = state.action_steps_completed
  total = state.action_steps_total
  total_elapsed = NOW() - state.started_at
  Log: "[yolo_continuous] Step {completed}/{total} completed: {step.id} (@{step.agent}) — {format_duration(elapsed_ms)}"
  Log: "  Next: {next_step_preview}"
  Log: "  Total elapsed: {format_duration(total_elapsed)}"

FUNCTION check_hang_detection(state, step, elapsed_ms, timeout):
  IF elapsed_ms > timeout * 2000:  # 2x timeout in ms
    Log: "⚠️ Step {step.id} (@{step.agent}) running for {format_duration(elapsed_ms)} (expected ~{format_duration(timeout * 1000)}) — may be hanging"
    log_event(state, "hang_warning", {step_id: step.id, elapsed_ms: elapsed_ms, timeout: timeout})
```

### Parse Failure Retry (Story 16.5)

```
FUNCTION handle_step_result(parsed_output, step, state, workflow):
  IF parsed_output is null:
    → parse_failure_retry(step, state, workflow)
  ELSE IF step_failed(parsed_output, step):
    → execution_failure_route(step, state, parsed_output)
  ELSE:
    → step_succeeded(step, state, parsed_output)

FUNCTION parse_failure_retry(step, state, workflow):
  retries = state.parse_retries[step.id] or 0
  max = workflow.global_error_handling.max_retries_per_phase or 2

  log_event(state, "parse_failure_retry", {step_id: step.id, attempt: retries + 1})

  IF retries < max:
    state.parse_retries[step.id] = retries + 1
    prompt = original_prompt + FORMAT_REMINDER
    re_spawn(step, prompt)
  ELSE:
    IF step.on_failure: route to on_failure (with loop guard)
    ELSE: ABORT "parse_failure_after_retries"

FORMAT_REMINDER = """
## FORMAT REMINDER
Your output MUST include this exact block:
```yaml
step_output:
  status: completed|failed
  outputs:
    key: value
```
Previous attempt did not include this block. This is attempt {N} of {max}.
"""
```

### State Locking (Story 16.6)

```
FUNCTION save_state_with_locking(state):
  on_disk = read_from_disk(state.instance_id)

  IF on_disk exists AND on_disk._version > state._expected_version:
    # Conflict detected!
    log_event(state, "state_conflict", {
      expected_version: state._expected_version,
      disk_version: on_disk._version,
      session_id: state._session_id
    })
    state.concurrency_events.append({
      type: "conflict_detected",
      timestamp: ISO_NOW(),
      expected: state._expected_version,
      actual: on_disk._version
    })

    IF state.mode == "yolo_continuous":
      ABORT "state_conflict — another session modified the state file"
    ELSE:
      WARN user: "State file was modified externally. Continue? (y/n)"

  state._version = (on_disk._version or 0) + 1
  state._expected_version = state._version
  state.updated_at = ISO_NOW()

  # Atomic write: temp file + rename
  temp_path = state_path + ".tmp"
  write(temp_path, serialize(state))
  rename(temp_path, state_path)

FUNCTION validate_state_on_resume(state):
  completed_count = count(state.step_results WHERE status == "completed")
  expected_index = state.current_step_index
  IF completed_count != expected_index:
    WARN: "State inconsistency: {completed_count} steps completed but index is {expected_index}"
    IF state.mode != "yolo_continuous":
      ASK user to confirm continue
```

### Output Validation (Story 16.7)

```
FUNCTION validate_step_outputs(parsed_output, step, state):
  expected = step.outputs or []
  IF expected is empty:
    RETURN "OK"  # No outputs declared, skip validation

  provided = keys(parsed_output.outputs)
  missing = expected - provided
  extras = provided - expected

  IF extras.length > 0:
    Log info: "Step {step.id} provided extra outputs: {extras} (accepted)"

  IF missing.length > 0:
    log_event(state, "output_validation_failed", {
      step_id: step.id, missing: missing, provided: provided
    })

    retries = state.output_retries[step.id] or 0
    max = 2

    IF retries < max:
      state.output_retries[step.id] = retries + 1
      log_event(state, "output_validation_retry", {step_id: step.id, attempt: retries + 1})
      prompt = original_prompt + OUTPUT_REMINDER(expected, missing)
      re_spawn(step, prompt)
      RETURN "RETRY"
    ELSE:
      IF step.on_failure: route to on_failure
      ELSE: ABORT "missing_outputs_after_retries: {missing}"

  RETURN "OK"

OUTPUT_REMINDER(expected, missing) = """
## OUTPUT REMINDER
You MUST provide ALL of these outputs:
{for each in expected: "- {key}"}
Your previous attempt was missing: {missing}
"""
```

### Global Workflow Limits (Story 16.9)

```
FUNCTION check_workflow_limits(state):
  constraints = state.execution_constraints
  warn_pct = constraints.warn_at_percent / 100.0

  # Duration check
  elapsed_hours = (NOW() - state.started_at) / 3600
  max_hours = constraints.max_workflow_duration_hours

  IF elapsed_hours > max_hours:
    log_event(state, "global_limit_exceeded", {type: "duration", value: elapsed_hours, limit: max_hours})
    ABORT "duration_limit — workflow exceeded {max_hours}h (elapsed: {elapsed_hours}h)"

  IF elapsed_hours > max_hours * warn_pct:
    IF "duration_80" not in state.global_warnings_issued:
      Log: "⚠️ Workflow duration at {pct}% of limit ({elapsed_hours}h / {max_hours}h)"
      state.global_warnings_issued.append("duration_80")
      log_event(state, "global_limit_warning", {type: "duration"})

  # Cost check (requires token tracking from 16.3)
  IF state.token_tracking exists:
    total_tokens = state.token_tracking.total_estimated
    # Heuristic: ~60% input ($3/1M), ~40% output ($15/1M) for Opus
    estimated_cost = (total_tokens * 0.6 * 3 / 1000000) + (total_tokens * 0.4 * 15 / 1000000)
    max_cost = constraints.max_estimated_cost_usd

    IF estimated_cost > max_cost:
      log_event(state, "global_limit_exceeded", {type: "cost", value: estimated_cost, limit: max_cost})
      ABORT "budget_exceeded — estimated ${estimated_cost} exceeds ${max_cost} limit"

    IF estimated_cost > max_cost * warn_pct:
      IF "cost_80" not in state.global_warnings_issued:
        Log: "⚠️ Estimated cost at {pct}% of budget (${estimated_cost} / ${max_cost})"
        state.global_warnings_issued.append("cost_80")
        log_event(state, "global_limit_warning", {type: "cost"})
```

### Failure Context Collection & Injection (Story 18.1)

```
FAILURE_CONTEXT_MAX_TOKENS = 500  # Max tokens for failure context in prompt

FUNCTION collect_failure_context(parsed_output, failed_step, state):
  reason = failure_reason(parsed_output)
  feedback = extract_feedback(parsed_output, reason)
  target_id = failed_step.on_failure
  current_loops = state.loop_guard.current_loops[target_id] or 0
  max_loops = state.loop_guard.max_loops_per_target

  RETURN {
    reason: reason,
    feedback: truncate_to_tokens(feedback, max_tokens=400),
    attempt: current_loops + 1,
    max_attempts: max_loops,
    previous_outputs: summarize_outputs(parsed_output.outputs, max_chars=500),
    collected_at: ISO_NOW()
  }

FUNCTION extract_feedback(parsed_output, reason):
  # Extracts human-readable feedback based on failure type
  SWITCH reason:
    "qa_gate_rejected":
      # Extract QA findings/recommendations from output
      IF parsed_output.outputs.findings exists:
        RETURN format_list(parsed_output.outputs.findings)
      IF parsed_output.outputs.qa_report exists:
        RETURN parsed_output.outputs.qa_report
      IF parsed_output.outputs.recommendations exists:
        RETURN format_list(parsed_output.outputs.recommendations)
      RETURN parsed_output.notes or "QA gate rejected without detailed feedback"

    "execution_failed":
      IF parsed_output.outputs.error exists:
        RETURN parsed_output.outputs.error
      IF parsed_output.notes exists:
        RETURN parsed_output.notes
      RETURN "Step execution failed without detailed error message"

    "timeout":
      RETURN "Step exceeded timeout limit ({timeout}s). Consider simplifying the task scope."

    "parse_failure":
      RETURN null  # Parse failures use FORMAT_REMINDER (Story 16.5), NOT failure context

    default:
      RETURN parsed_output.notes or "Step failed (reason: {reason})"

FUNCTION format_failure_context_for_prompt(failure_ctx):
  # Formats failure context as markdown for injection into subagent prompt
  IF failure_ctx is null:
    RETURN ""

  # Parse failure uses separate FORMAT_REMINDER (Story 16.5)
  IF failure_ctx.reason == "parse_failure":
    RETURN ""

  text = """
## FAILURE CONTEXT (Tentativa {failure_ctx.attempt} de {failure_ctx.max_attempts})

**Motivo da falha anterior:** {failure_ctx.reason}

**Feedback especifico:**
{failure_ctx.feedback}

**IMPORTANTE:** Corrija ESPECIFICAMENTE os pontos acima antes de prosseguir.
O resto da implementacao anterior estava correto — nao refaca do zero.
"""
  RETURN truncate_to_tokens(text, max_tokens=FAILURE_CONTEXT_MAX_TOKENS)

FUNCTION summarize_outputs(outputs, max_chars):
  IF outputs is null: RETURN "No outputs from previous attempt"
  summary = yaml_serialize(outputs)
  IF len(summary) > max_chars:
    RETURN summary[:max_chars] + "\n... [truncated]"
  RETURN summary
```

**Integration with Subagent Prompt Builder:**

In step 8 of the Sequence Advancer (Build prompt), after collecting requires:

```
# Story 18.1: Inject failure context if retrying
IF state.failure_contexts[step.id] exists:
  failure_ctx = state.failure_contexts[step.id]
  Set {{FAILURE_CONTEXT}} = format_failure_context_for_prompt(failure_ctx)
  # Clear after injection (consumed)
  delete state.failure_contexts[step.id]
ELSE:
  Set {{FAILURE_CONTEXT}} = ""
```

---

### Handoff Consumption & Injection (Story 18.2)

```
HANDOFF_CONTEXT_MAX_TOKENS = 300  # Max tokens for handoff data in prompt

FUNCTION inject_handoff_into_prompt(step, state):
  # Find the most recent handoff artifact targeting this step's agent
  latest_handoff = find_latest_handoff_for_agent(step.agent, state)

  IF latest_handoff is null:
    Set {{HANDOFF_DATA}} = ""
    RETURN

  from_agent = latest_handoff.handoff.from_agent
  from_step = latest_handoff.handoff.step_completed
  outputs_summary = truncate_to_tokens(
    yaml_serialize(latest_handoff.handoff.outputs),
    max_tokens=200
  )
  prior_steps = format_prior_steps(latest_handoff.handoff.prior_steps_same_agent)

  handoff_text = """
## HANDOFF DO AGENTE ANTERIOR

**De:** @{from_agent} (step: {from_step})
**Outputs/contexto:**
{outputs_summary}
"""

  IF prior_steps is not empty:
    handoff_text += """
**Steps anteriores do mesmo agente:**
{prior_steps}
"""

  Set {{HANDOFF_DATA}} = truncate_to_tokens(handoff_text, max_tokens=HANDOFF_CONTEXT_MAX_TOKENS)

FUNCTION find_latest_handoff_for_agent(agent_id, state):
  # Option 1: From in-memory state (during yolo_continuous)
  FOR each filename in reverse(state.handoffs_generated):
    IF filename contains "-to-{agent_id}-":
      TRY:
        parsed = read_and_parse(".aios/handoffs/{filename}")
        RETURN parsed
      CATCH:
        CONTINUE  # File read failed, try next

  # Option 2: Scan disk (for recovery/continue mode)
  files = glob(".aios/handoffs/handoff-*-to-{agent_id}-*.yaml")
  IF files is not empty:
    sorted = sort_by_timestamp(files, descending=true)
    TRY:
      RETURN read_and_parse(sorted[0])
    CATCH:
      RETURN null

  RETURN null

FUNCTION format_prior_steps(prior_steps_list):
  IF prior_steps_list is null or empty:
    RETURN ""
  lines = []
  FOR each entry in prior_steps_list:
    lines.append("- {entry.step_id}: {entry.summary}")
  RETURN join(lines, "\n")
```

**Integration with Subagent Prompt Builder:**

In step 8 of the Sequence Advancer, after failure context injection:

```
# Story 18.2: Inject handoff data if agent changed
inject_handoff_into_prompt(step, state)
# {{HANDOFF_DATA}} is now set (empty string if no handoff)
```

---

### Adaptive Retry Strategy (Story 18.4)

```
DEFAULT_RETRY_STRATEGY = {
  level_1: "context",          # Attempt 2: same prompt + failure context (18.1)
  level_2: "simplification",   # Attempt 3: reduced scope, focus on failed ACs
  level_3: "decomposition",    # Attempt 4: split into sub-steps
  fallback: "abort"            # After all levels exhausted
}

FUNCTION get_retry_strategy(step, state, attempt):
  # Resolve strategy: step-level > workflow-level > engine default
  config = step.retry_strategy or state.workflow_retry_strategy or DEFAULT_RETRY_STRATEGY

  IF attempt == 1: RETURN config.level_1 or "context"
  IF attempt == 2: RETURN config.level_2 or "simplification"
  IF attempt == 3: RETURN config.level_3 or "decomposition"
  RETURN config.fallback or "abort"

FUNCTION build_retry_prompt(step, state, strategy, failure_ctx, original_prompt):
  log_event(state, "retry_strategy_applied", {
    step_id: step.id, strategy: strategy, attempt: failure_ctx.attempt
  })

  SWITCH strategy:
    "context":
      # Level 1: Original prompt + failure context (handled by 18.1 injection)
      # No additional modification needed — format_failure_context_for_prompt() handles it
      RETURN original_prompt  # {{FAILURE_CONTEXT}} already injected

    "simplification":
      # Level 2: Reduce scope to focus on what failed
      pending_acs = extract_pending_acs(failure_ctx)
      simplified = simplify_prompt(original_prompt, pending_acs, failure_ctx)
      RETURN simplified

    "decomposition":
      # Level 3: Split step into sequential sub-steps
      sub_prompts = decompose_step(step, failure_ctx, original_prompt)
      RETURN sub_prompts  # Array — engine spawns each sequentially, merges outputs

    "abort":
      RETURN null  # Signal to abort

FUNCTION extract_pending_acs(failure_ctx):
  # Parse failure feedback to identify which ACs are pending
  feedback = failure_ctx.feedback
  previous = failure_ctx.previous_outputs

  # Heuristic: look for AC references in feedback
  # e.g., "AC #3 not implemented", "Missing test for edge case"
  pending = []
  IF feedback contains "AC" or feedback contains "acceptance criteria":
    # Extract AC numbers/descriptions from feedback text
    pending = parse_ac_references(feedback)
  IF pending is empty:
    # Fallback: treat entire feedback as the pending work
    pending = [feedback]
  RETURN pending

FUNCTION simplify_prompt(original_prompt, pending_acs, failure_ctx):
  simplified_section = """
## SIMPLIFIED SCOPE (Tentativa {failure_ctx.attempt} de {failure_ctx.max_attempts})

**ATENCAO:** Esta e uma tentativa simplificada. Foque APENAS nos pontos pendentes:

{for each ac in pending_acs: "- {ac}"}

**NAO refaca** o que ja funciona da tentativa anterior.
**NAO adicione** funcionalidades extras alem do listado acima.

**Outputs da tentativa anterior (manter o que funciona):**
{failure_ctx.previous_outputs}
"""
  # Replace the step notes section with simplified version
  RETURN replace_step_notes(original_prompt, simplified_section)

FUNCTION decompose_step(step, failure_ctx, original_prompt):
  # Generate 2 sub-steps: test-first, then implement
  sub_step_1 = {
    prompt: original_prompt + """
## DECOMPOSED STEP (Parte 1 de 2)

Foque APENAS em criar/atualizar os TESTES para os pontos que falharam:
{failure_ctx.feedback}

NAO implemente o codigo ainda. Apenas testes que capturam o comportamento esperado.
Retorne os testes criados como output.
""",
    id: step.id + "_tests"
  }

  sub_step_2 = {
    prompt: original_prompt + """
## DECOMPOSED STEP (Parte 2 de 2)

Os testes ja foram criados na parte anterior. Agora implemente o codigo
que faz TODOS os testes passarem.

**Testes criados:** {{sub_step_1_outputs}}
**Feedback original:** {failure_ctx.feedback}
""",
    id: step.id + "_impl"
  }

  RETURN [sub_step_1, sub_step_2]
```

**Integration with Sequence Advancer:**

In the failure handling block of yolo_continuous mode, replace direct loop with strategy-aware retry:

```
# Story 18.4: Adaptive retry replaces blind re-loop
# Called when step_failed() and on_failure exists and loop_guard allows

FUNCTION execute_adaptive_retry(step, state, parsed_output, sequence):
  failure_ctx = state.failure_contexts[step.on_failure]  # Set by 18.1
  attempt = failure_ctx.attempt  # 1-based (1 = first retry)
  strategy = get_retry_strategy(step, state, attempt)

  IF strategy == "abort":
    RETURN "ABORT"

  IF strategy == "decomposition":
    # Special case: spawn sub-steps sequentially
    sub_prompts = build_retry_prompt(step, state, strategy, failure_ctx, original_prompt)
    merged_outputs = {}
    FOR each (sub_prompt, idx) in enumerate(sub_prompts):
      result = spawn_subagent(step.agent, sub_prompt.prompt)
      parsed = parse_output(result)
      merged_outputs.update(parsed.outputs)
      IF step_failed(parsed, step):
        RETURN "ABORT"  # Sub-step failed, give up
    # Store merged outputs
    state.step_outputs[step.id] = merged_outputs
    RETURN "CONTINUE"  # Skip re-loop, step effectively completed

  ELSE:
    # context or simplification: modify the prompt and re-loop normally
    # The prompt is modified via failure_context injection (18.1) for "context"
    # For "simplification", override the prompt before spawn
    IF strategy == "simplification":
      state.simplified_prompt_override[step.on_failure] = build_retry_prompt(
        step, state, strategy, failure_ctx, original_prompt
      )
    RETURN "LOOP"  # Normal loop to on_failure target

# Engine state init addition:
#   simplified_prompt_override: {}  # map step_id → simplified prompt (cleared after use)
```

**Loop guard adjustment:**

```
# When adaptive retry is enabled, default max_loops increases from 3 to 4
# to accommodate the 3 retry levels + original attempt
ADAPTIVE_RETRY_DEFAULT_MAX_LOOPS = 4

# Applied during state init:
IF workflow has adaptive_retry enabled (default: true):
  state.loop_guard.max_loops_per_target = ADAPTIVE_RETRY_DEFAULT_MAX_LOOPS
```

---

### Confidence Scoring (Story 18.5)

```
# Confidence thresholds for engine behavior
CONFIDENCE_HIGH = 0.8      # >= 0.8: continue normally
CONFIDENCE_MEDIUM = 0.5    # 0.5-0.79: continue with extra review flag
CONFIDENCE_LOW = 0.5       # < 0.5: soft failure, try to improve

FUNCTION extract_confidence(parsed_output):
  # Extract confidence from step_output (optional field, default 1.0)
  IF parsed_output is null:
    RETURN 1.0  # Parse failures handled separately
  confidence = parsed_output.confidence or 1.0
  confidence_notes = parsed_output.confidence_notes or ""
  # Clamp to valid range
  confidence = max(0.0, min(1.0, confidence))
  RETURN {score: confidence, notes: confidence_notes}

FUNCTION evaluate_confidence(confidence, step, state):
  score = confidence.score
  notes = confidence.notes

  # Record in step_results
  state.step_results[step.id].confidence = score
  state.step_results[step.id].confidence_notes = notes
  log_event(state, "confidence_evaluated", {step_id: step.id, score: score})

  IF score >= CONFIDENCE_HIGH:
    # High confidence — proceed normally
    RETURN "CONTINUE"

  IF score >= CONFIDENCE_MEDIUM:
    # Medium confidence — continue but flag for extra review
    state.step_results[step.id].needs_extra_review = true
    Log: "⚠️ Step {step.id} completed with medium confidence ({score}): {notes}"
    # Inject note into next step's context
    state.confidence_notes_for_next[step.id] = {
      from_step: step.id,
      from_agent: step.agent,
      score: score,
      notes: notes
    }
    RETURN "CONTINUE"

  # Low confidence — soft failure, try to improve
  Log: "⚠️ Step {step.id} has low confidence ({score}): {notes}"
  log_event(state, "low_confidence_retry", {step_id: step.id, score: score})

  # Build improvement prompt
  improvement_context = """
## LOW CONFIDENCE — IMPROVEMENT REQUIRED

Your previous output had confidence {score} (minimum required: {CONFIDENCE_MEDIUM}).
Reason: {notes}

Please review and improve your output. Focus on:
- The specific areas you flagged as low-confidence
- Ensure all acceptance criteria are fully covered
- Add missing tests or validations

Return the COMPLETE improved output (not just the delta).
"""
  # Re-spawn with improvement context (counts as a retry)
  state.failure_contexts[step.id] = {
    reason: "low_confidence",
    feedback: improvement_context,
    attempt: 1,
    max_attempts: 2  # Max 1 improvement attempt for low confidence
  }
  RETURN "RETRY"  # Re-execute same step with improvement prompt
```

**Integration with Sequence Advancer:**

After output validation (Story 16.7) and before handoff generation:

```
# Story 18.5: Evaluate confidence score
confidence = extract_confidence(parsed_output)
confidence_result = evaluate_confidence(confidence, item, state)
IF confidence_result == "RETRY":
  CONTINUE LOOP  # Re-executes step with improvement prompt
# If CONTINUE, proceed to handoff generation
```

**Integration with Subagent Prompt Builder:**

Inject confidence notes from previous step if flagged:

```
# Story 18.5: Inject previous step's confidence notes
IF state.confidence_notes_for_next contains any entry for current step's requires:
  notes = collect_relevant_confidence_notes(step, state)
  Append to {{INPUT_DATA}}: "\n## Previous Step Confidence Notes\n{notes}"
```

**Final Report addition:**

```
--- Confidence Scores (Story 18.5) ---
  {step_id}: {confidence} {needs_extra_review ? "⚠️ flagged" : "✅"}
  ...
  Average confidence: {avg}
  Steps flagged for extra review: {count}
```

### Project Context Injection (Story 18.6)

```
PROJECT_CONTEXT_PATH = ".aios/project-context.yaml"
PROJECT_CONTEXT_MAX_TOKENS = 200  # Token budget for project context

FUNCTION load_project_context():
  # Read once at workflow init, reuse for all steps
  IF file_exists(PROJECT_CONTEXT_PATH):
    raw = read_file(PROJECT_CONTEXT_PATH)
    tokens = estimate_tokens(raw)
    IF tokens > PROJECT_CONTEXT_MAX_TOKENS:
      # Truncate to budget — keep tech_stack and patterns, trim architecture/conventions
      truncated = truncate_yaml_to_budget(raw, PROJECT_CONTEXT_MAX_TOKENS)
      Log: "⚠️ Project context truncated from {tokens} to ~{PROJECT_CONTEXT_MAX_TOKENS} tokens"
      RETURN truncated
    RETURN raw
  ELSE:
    RETURN null  # Graceful skip — no project context file

FUNCTION truncate_yaml_to_budget(raw, max_tokens):
  # Priority order: tech_stack > patterns > architecture > conventions
  sections = parse_yaml_sections(raw)
  result = "project_context:\n  name: {sections.name}\n  description: {sections.description}\n"
  FOR section IN ["tech_stack", "patterns", "architecture", "conventions"]:
    IF estimate_tokens(result + sections[section]) <= max_tokens:
      result += sections[section]
    ELSE:
      BREAK
  RETURN result
```

**State initialization:**

Add to both `start` and `yolo_continuous` state init:
```yaml
  # Story 18.6: Project Context Injection
  project_context: {load_project_context()}  # Read ONCE, reuse for all steps
```

**Integration with Subagent Prompt Builder:**

In the Prompt Builder process, add new step between step 2 (Extract agent info) and step 3 (Extract task content):

```
  2.5. Set project context:
       IF state.project_context is not null:
         Set {{PROJECT_CONTEXT}} = state.project_context
       ELSE:
         Set {{PROJECT_CONTEXT}} = "No project context available"
```

**Backward compatibility:**
- If `.aios/project-context.yaml` does not exist → `{{PROJECT_CONTEXT}}` = "No project context available"
- Zero impact on existing workflows — section simply shows neutral text
- Works in both yolo_continuous and step-by-step modes (context read from state)

---

### Routing Defaults & Fallback (Story 16.10)

```
FUNCTION resolve_route_with_fallback(routing_step, state, mode):
  routes = routing_step.routing.routes
  condition = routing_step.routing.condition

  # Pre-routing dependency check
  required_values = extract_dependencies(condition)
  FOR each value in required_values:
    IF value not in state.step_outputs:
      Log warning: "Routing dependency missing: {value}"
      log_event(state, "routing_fallback", {reason: "missing_dependency", value: value})
      RETURN use_default_or_first(routes, mode)

  # Normal evaluation
  evaluated = evaluate_condition(condition, state)
  matched = find_matching_route(routes, evaluated)

  IF matched:
    RETURN matched

  # No match — fallback chain (yolo_continuous only, step-by-step asks user)
  IF mode == "yolo_continuous":
    log_event(state, "routing_fallback", {reason: "no_match", evaluated: evaluated})
    RETURN use_default_or_first(routes, mode)
  ELSE:
    → Ask user to choose (existing behavior)

FUNCTION use_default_or_first(routes, mode):
  # 1. Try route with default: true
  default_route = find(routes, r => r.default == true)
  IF default_route:
    Log: "Using default route: {default_route.name}"
    RETURN default_route

  # 2. Use first route + warning
  IF routes.length > 0:
    Log warning: "⚠️ No default route — using first route: {routes[0].name}"
    RETURN routes[0]

  # 3. No routes at all
  ABORT "routing_undefined — no routes defined for routing step"
```

---

## Engine Loop (Step-by-Step)

The engine processes **ONE action step per invocation**. Phase markers and routing decisions are processed automatically (they don't require spawning). The engine stops after each action step so the user can validate the output before continuing.

```
Invocation 1: start    → init state → spawn step 1 → save → STOP (user validates)
Invocation 2: continue → load state → spawn step 2 → save → STOP (user validates)
Invocation 3: continue → load state → [routing: score OK] → spawn step 3 → save → STOP
...
Invocation N: continue → load state → [end marker] → final report → DONE
```

---

### Action: `start`

Initialize a new workflow and execute the first action step.

**1. Resolve workflow path** based on `target_context`:
- `core` → `.aios-core/development/workflows/{workflow_name}.yaml`
- `squad` → `squads/{squad_name}/workflows/{workflow_name}.yaml`
- `hybrid` → `squads/{squad_name}/workflows/{workflow_name}.yaml`

Read the workflow YAML file.

**2. Validate workflow** using WorkflowValidator:
- Must pass validation before proceeding
- Display any warnings to the user
- If validation fails → abort with error details

**3. Initialize state:**

```yaml
engine_state:
  workflow_id: {workflow.id}
  workflow_name: {workflow.name}
  instance_id: "{workflow_id}-engine-{timestamp}"
  target_context: {target_context}
  squad_name: {squad_name}
  mode: engine
  started_at: {ISO timestamp}
  status: active
  current_step_index: 0
  current_phase: null
  step_outputs: {}
  decisions: []
  retries: {}
```

**4. Display header:**
```
=== Workflow Engine Started: {workflow_name} ===
Mode: ENGINE (real subagent spawning, step-by-step)
Instance: {instance_id}
Total sequence items: {N} ({action_count} action steps)
```

**5. Advance to first action step** — call the **Sequence Advancer** (see below).

**6. Save state and STOP.**

---

### Action: `continue`

Resume from current position and execute the next action step.

**1. Find and load** the active engine state file for this workflow.

**2. Verify** state.status is `active`. If not, show error.

**3. Advance to next action step** — call the **Sequence Advancer** (see below).

**4. Save state and STOP.**

---

### Action: `status`

Show progress without executing anything.

**1. Load state.**

**2. Generate status report:**

```
=== Engine Status: {workflow_name} ===
Instance: {instance_id}
Mode: ENGINE (step-by-step)
Status: {active|completed|aborted}
Phase: {current_phase}
Progress: [{progress_bar}] {percentage}% ({completed}/{total_action_steps})

--- Steps ---
  [x] {step_id}: {agent} — {action} (score: {score})
  [x] {step_id}: {agent} — {action}
  [>] {step_id}: {agent} — {action}    <-- current
  [ ] {step_id}: {agent} — {action}
  ...

--- Routing Decisions ---
  {step}: {condition} = {value} → {route_chosen}
  ...

--- Execution Timeline (Story 16.4) ---
  {event.timestamp} {event.event}: {event details}
  ...
  (last 10 events from execution_log)

--- Token Usage (Story 16.3) ---
  Total: {total_estimated} / {context_window_limit} ({percentage}%)

--- Last Step Output ---
  {summary of most recent step's outputs}

Next: *run-workflow {name} continue --mode=engine
```

---

### Action: `skip`

Skip the current step (only if marked `optional: true`).

**1. Load state.**

**2. Identify the current step** at `current_step_index`.

**3. Verify** the step has `optional: true`. If not → error: "Step {id} is not optional."

**4. Record skip** in state:
```yaml
step_results:
  {step_id}:
    status: skipped
    skipped_at: {timestamp}
```

**5. Advance `current_step_index`** past the skipped step.

**6. Save state.**

**7. Show** what was skipped and what comes next.

---

### Action: `abort`

Abort the workflow.

**1. Load state.**

**2. Set status to `aborted`.**

**3. Generate abort report:**
```
=== Workflow Aborted: {workflow_name} ===
Instance: {instance_id}
Progress: {completed}/{total} action steps completed

Completed steps:
  - {step_id}: {agent} — {action}
  ...

Artifacts created:
  - {list from step_results}

State preserved at: .aios/{instance_id}-engine-state.yaml
```

**4. Save state.**

---

### Action: `yolo_continuous`

Execute the entire workflow from start to completion without stopping between steps.

**1. Auto-detect:** If no explicit `yolo_continuous` action was requested, check if the workflow defines a default YOLO mode:
```
IF workflow.execution_modes exists:
  FOR each mode in workflow.execution_modes:
    IF mode.default == true AND mode.mode == "yolo":
      → Auto-upgrade to yolo_continuous
      Log: "Auto-detected YOLO mode from workflow definition"
```

**2. Fallback check:** Verify Task tool is available:
```
IF Task tool is NOT available:
  Log: "⚠️ Task tool not available — falling back to guided mode (persona-switch)"
  → Delegate to run-workflow.md (guided mode)
  RETURN
```

**3. Initialize state** (same as `start`, with mode difference):

```yaml
engine_state:
  workflow_id: {workflow.id}
  workflow_name: {workflow.name}
  instance_id: "{workflow_id}-engine-{timestamp}"
  target_context: {target_context}
  squad_name: {squad_name}
  mode: yolo_continuous   # <-- different from step-by-step
  started_at: {ISO timestamp}
  status: active
  current_step_index: 0
  current_phase: null
  step_outputs: {}
  decisions: []
  retries: {}
  parse_retries: {}           # Story 16.5: parse failure retry counters
  output_retries: {}          # Story 16.7: output validation retry counters
  loop_guard:
    max_loops_per_target: 3   # overridable by workflow.failure_recovery
    current_loops: {}
  handoffs_generated: []
  # Story 16.2: Timeout
  default_step_timeout: {workflow.metadata.default_step_timeout or ENGINE_DEFAULT_TIMEOUT}
  # Story 16.3: Token Tracking
  token_tracking:
    total_estimated: 0
    per_step: {}
    context_window_limit: {workflow.metadata.context_window_limit or 180000}
    warnings_issued: []
  # Story 16.4: Observability
  execution_log: []
  # Story 16.6: State Locking
  _version: 1
  _session_id: {uuid()}
  _expected_version: 1
  concurrency_events: []
  # Story 16.8: Handoff Edge Cases
  same_agent_summaries: []    # accumulated when agent doesn't change
  handoff_write_failures: []
  # Story 16.9: Global Limits
  execution_constraints:
    max_workflow_duration_hours: {workflow.execution_constraints.max_workflow_duration_hours or 4}
    max_estimated_cost_usd: {workflow.execution_constraints.max_estimated_cost_usd or 10.0}
    warn_at_percent: {workflow.execution_constraints.warn_at_percent or 80}
  global_warnings_issued: []
  # Story 18.1: Failure Context Injection
  failure_contexts: {}          # map step_id → {reason, feedback, attempt, max_attempts, previous_outputs}
  # Story 18.4: Adaptive Retry Strategy
  simplified_prompt_override: {} # map step_id → simplified prompt (cleared after use)
  # Story 18.6: Project Context Injection
  project_context: {load_project_context()}  # Read ONCE at init, reused for all steps
```

**4. Display header:**
```
=== Workflow Engine Started: {workflow_name} ===
Mode: YOLO CONTINUOUS (real subagent spawning, zero stops)
Instance: {instance_id}
Total sequence items: {N} ({action_count} action steps)
⚡ Running all steps without pausing...
```

**5. Run continuous loop** — call **Sequence Advancer** with `mode=yolo_continuous` (see below). The advancer does NOT return between action steps; it loops until workflow complete, abort, or error.

**6. Generate Final Report** (same format as step-by-step, with additional yolo_continuous fields).

---

### Failure Detection (Updated Story 16.5)

The engine determines if a step failed by inspecting the parsed `step_output`. **Parse failures and execution failures are handled differently:**

```
FUNCTION step_failed(parsed_output, step):
  # 1. Parse failure — subagent returned no structured output
  #    In yolo_continuous: routed to parse_failure_retry() (Story 16.5)
  #    NOT treated as execution failure — gets format reminder retry
  IF parsed_output is null:
    RETURN true  # Caller checks: if null → parse_failure_retry, if status:failed → execution route

  # 2. Explicit status
  IF parsed_output.status == "failed":
    RETURN true

  # 3. QA gate verdict
  IF step.id contains "qa_gate" OR step.id contains "gate":
    IF parsed_output.outputs.gate_verdict == "REJECT":
      RETURN true

  # 4. Timeout (Story 16.2)
  IF step.timeout_triggered:
    RETURN true

  RETURN false

FUNCTION failure_reason(parsed_output):
  IF parsed_output is null: RETURN "parse_failure"
  IF parsed_output.status == "failed": RETURN "execution_failed"
  IF parsed_output.outputs.gate_verdict == "REJECT": RETURN "qa_gate_rejected"
  RETURN "unknown"
```

In `yolo_continuous` mode, failure detection drives automatic routing:
- **Parse failure (null output)** → `parse_failure_retry()` with format reminder (max 2 retries) (Story 16.5)
- **Execution failure (status: failed)** → route via `on_failure` if defined, else ABORT
- **Timeout** → treated as failure via `step_failed()` flow (Story 16.2)
- If step has NO `on_failure` and retries exhausted → ABORT

---

### Handoff Artifact Generation (Updated Story 16.8)

When transitioning between agents in `yolo_continuous` mode, the engine generates a handoff artifact to preserve context. **v4.0 adds: same-agent accumulation, write failure handling, smart truncation, cleanup, and initial context.**

```
FUNCTION generate_handoff_v2(current_step, next_step, state):
  IF current_step.agent == next_step.agent:
    RETURN  # Same agent, no handoff needed

  artifact = {
    handoff:
      from_agent: current_step.agent
      to_agent: next_step.agent
      workflow: state.workflow_id
      step_completed: current_step.id
      step_next: next_step.id
      outputs:
        # Smart truncation (Story 16.8): truncate per field, preserve keys
        # Prioritize fields referenced in next_step.requires
        FOR each key in state.step_outputs[current_step.id]:
          value = state.step_outputs[current_step.id][key]
          IF key in next_step.requires:
            truncated = enforce_handoff_max_size(value, max_chars=200)  # Priority fields get more space
          ELSE:
            truncated = enforce_handoff_max_size(value, max_chars=100)
          key: truncated
      # Story 16.8: Include accumulated same-agent summaries
      prior_steps_same_agent: state.same_agent_summaries  # Array of {step_id, summary}
      timestamp: {ISO now}
  }

  # Write to .aios/handoffs/ with error handling (Story 16.8)
  filename = "handoff-{current_step.agent}-to-{next_step.agent}-{timestamp}.yaml"
  TRY:
    Write artifact to .aios/handoffs/{filename}
    state.handoffs_generated.append(filename)
    log_event(state, "handoff_generated", {from: current_step.agent, to: next_step.agent})
    Log: "🔄 Handoff: @{current_step.agent} → @{next_step.agent}"
  CATCH write_error:
    # Story 16.8: Graceful degradation — log warning, continue workflow
    Log: "⚠️ Handoff write failed: {write_error} — continuing without handoff"
    state.handoff_write_failures.append({
      filename: filename, error: write_error, timestamp: ISO_NOW()
    })
    log_event(state, "handoff_write_failed", {filename: filename, error: str(write_error)})

FUNCTION generate_initial_context(workflow, state, user_input):
  # Story 16.8: First step receives synthetic handoff with trigger info
  artifact = {
    handoff:
      from_agent: "workflow_trigger"
      to_agent: workflow.sequence[first_action_step].agent
      workflow: state.workflow_id
      trigger_info:
        workflow_name: workflow.name
        started_at: state.started_at
        mode: state.mode
        user_input: user_input or "No user input"
      timestamp: {ISO now}
  }
  Write artifact to .aios/handoffs/

FUNCTION cleanup_duplicate_handoffs(state):
  # Story 16.8: At workflow end, keep only latest handoff per transition
  transitions = {}
  FOR each filename in state.handoffs_generated:
    key = extract_transition(filename)  # e.g., "qa-to-sm"
    transitions[key] = filename  # Latest overwrites earlier
  # Remove files not in transitions.values()
  FOR each filename in state.handoffs_generated:
    IF filename not in transitions.values():
      delete .aios/handoffs/{filename}
```

---

### Loop Guard

Prevents infinite loops when `on_failure` routes back to a previous step:

```
FUNCTION check_loop_guard(state, target_step_id):
  max = state.loop_guard.max_loops_per_target  # default: 3

  # Check workflow-level override
  IF workflow.failure_recovery exists:
    # Parse max from failure_recovery rules (e.g., "RETRY ate 3x")
    override = extract_max_from_failure_recovery(workflow, target_step_id)
    IF override: max = override

  current = state.loop_guard.current_loops[target_step_id] or 0

  IF current >= max:
    RETURN "ABORT"  # Max loops exceeded
  ELSE:
    state.loop_guard.current_loops[target_step_id] = current + 1
    RETURN "CONTINUE"  # Loop allowed
```

When `ABORT` is returned:
```
Log: "❌ Max loops exceeded for step {target_step_id} ({max} attempts)"
Generate Abort Report with:
  - reason: "max_loops_exceeded"
  - target_step: {target_step_id}
  - attempts: {current}
  - last_failure: {last step_output}
Set state.status = "aborted"
RETURN
```

---

### Sequence Advancer (Core Algorithm)

This is the internal procedure called by `start`, `continue`, and `yolo_continuous`. It walks through the sequence from `current_step_index`, automatically processing non-action items. In step-by-step mode it stops after each action step; in `yolo_continuous` mode it continues until workflow complete, abort, or blocking error.

```
PROCEDURE advance_and_execute(state, workflow):

  index = state.current_step_index
  sequence = workflow.sequence

  LOOP:
    IF index >= length(sequence):
      → Workflow complete. Generate Final Report. Set status=completed. RETURN.

    item = sequence[index]

    # --- Phase Marker ---
    IF item has 'phase' field:
      state.current_phase = item.name
      Log: "--- Phase {item.phase}: {item.name} ---"
      index = index + 1
      CONTINUE LOOP

    # --- End Marker ---
    IF item has 'meta: end':
      Log: "=== Workflow Complete ==="
      Generate Final Report.
      Set state.status = completed.
      RETURN.

    # --- Routing Step ---
    IF item has 'meta: routing':
      Execute Decision Router (see section below).
      The router returns a new index (loop_back, continue, or complete).
      IF complete → Generate Final Report. Set status=completed. RETURN.
      index = {new index from router}
      CONTINUE LOOP

    # --- Action Step (spawn subagent) ---
    IF item has 'agent' field:
      state.current_step_index = index

      # --- Pre-step checks (Story 16.9: Global Limits) ---
      IF state.mode == "yolo_continuous":
        limit_result = check_workflow_limits(state)
        IF limit_result == "ABORT":
          → Generate Abort Report. Set status=aborted. RETURN.

      # --- Resolve timeout (Story 16.2) ---
      timeout = resolve_timeout(item, workflow, state)

      Execute the step:
        1. IF elicit=true AND mode != "yolo_continuous" → run Elicitation Handler
           (In yolo_continuous, elicitation is skipped — decisions are autonomous)
        2. Resolve agent file path
        3. Read agent file
        4. Resolve task file path (from 'uses')
        5. Read task file (if 'uses' defined)
        6. Read data files (agent deps + workflow resources)
        7. Collect requires from state.step_outputs
           # Story 16.3: Truncate requires outputs exceeding 2000 tokens
           FOR each required_output in requires:
             required_output = truncate_requires_output(required_output, max_tokens=2000)
        8. Build prompt (Subagent Prompt Builder)
           # Story 16.3: Check token limits before spawning
           token_result = check_token_limits(state, built_prompt)
           IF token_result == "ABORT" AND state.mode == "yolo_continuous":
             → Auto-truncate and warn
           ELIF token_result == "ABORT":
             → Warn user, ask to continue
        9. # Story 16.4: Log step_started
           log_event(state, "step_started", {step_id: item.id, agent: item.agent})
           step_start_time = NOW()
           # Story 16.2: Spawn subagent via Task tool WITH timeout
           IF state.mode == "yolo_continuous":
             Spawn subagent via Task tool with timeout={timeout * 1000}ms
           ELSE:
             Spawn subagent via Task tool (no timeout in step-by-step)
        10. Parse output (Output Parser)
            step_elapsed_ms = NOW() - step_start_time
            # Story 16.4: Log completion + hang detection
            IF parsed_output is not null AND not step_failed(parsed_output, item):
              log_event(state, "step_completed", {step_id: item.id, elapsed_ms: step_elapsed_ms})
            # Story 16.4: Hang detection (check even if completed — logs warning for slow steps)
            check_hang_detection(state, item, step_elapsed_ms, timeout)
            # Story 16.2: Check if timeout was triggered
            IF step timed out:
              log_event(state, "step_timeout", {step_id: item.id, timeout: timeout, elapsed_ms: step_elapsed_ms})
              state.step_results[item.id].timeout_triggered = true
              state.step_results[item.id].timeout_limit = timeout
              → Treat as failure via step_failed() flow
        11. Store in state.step_results[{step_id}] and state.step_outputs
            state.step_results[item.id].elapsed_ms = step_elapsed_ms
      Display step result to user.

      # --- Story 16.4: Emit progress display ---
      IF state.mode == "yolo_continuous":
        emit_progress(state, item, step_elapsed_ms)

      # --- Mode-dependent behavior after step execution ---
      IF state.mode == "yolo_continuous":
        # Story 16.5: Handle result (separates parse failures from execution failures)
        # Use handle_step_result() which routes to parse_failure_retry or execution_failure_route

        # Check for failure
        IF step_failed(parsed_output, item):
          log_event(state, "step_failed", {step_id: item.id, reason: failure_reason(parsed_output)})
          IF item has 'on_failure' field:
            target = find_step_index(item.on_failure, sequence)
            guard_result = check_loop_guard(state, item.on_failure)
            IF guard_result == "ABORT":
              → Generate Abort Report. Set status=aborted. RETURN.
            ELSE:
              # Story 18.1: Collect failure context BEFORE looping
              failure_ctx = collect_failure_context(parsed_output, item, state)
              state.failure_contexts[item.on_failure] = failure_ctx
              log_event(state, "failure_context_collected", {target_step: item.on_failure, reason: failure_ctx.reason, attempt: failure_ctx.attempt})
              Log: "⚠️ Step failed — looping to {item.on_failure} (attempt {count}) with failure context"
              log_event(state, "loop_guard_warning", {target_step: item.on_failure, current_loops: count, max_loops: max})
              index = target
              save_state_with_locking(state).  # Story 16.6
              CONTINUE LOOP
          ELSE:
            # No on_failure defined — blocking error
            Log: "❌ Step failed with no recovery route — aborting"
            → Generate Abort Report. Set status=aborted. RETURN.

        # --- Story 16.7: Validate declared outputs ---
        validation_result = validate_step_outputs(parsed_output, item, state)
        IF validation_result == "RETRY":
          CONTINUE LOOP  # Re-executes same step with output reminder

        # Step succeeded — generate handoff if agent changes
        next_item = find_next_action_step(sequence, index + 1)
        IF next_item AND next_item.agent != item.agent:
          # Story 16.8: Include same_agent_summaries in handoff
          generate_handoff_v2(item, next_item, state)
          state.same_agent_summaries = []  # Reset after handoff
        ELIF next_item AND next_item.agent == item.agent:
          # Story 16.8: Accumulate summary for same-agent consecutive steps
          summary = summarize_output(parsed_output, max_chars=200)
          state.same_agent_summaries.append({step_id: item.id, summary: summary})

        # Continue to next step (NO STOP)
        index = index + 1
        save_state_with_locking(state).  # Story 16.6
        CONTINUE LOOP

      ELSE:
        # Step-by-step mode — STOP for user validation
        Advance index for next invocation:
          state.current_step_index = index + 1
        Show what comes next (preview):
          Scan ahead to find next action step, show its agent/action.
          "Next: @{next_agent} — {next_action}"
          "Run: *run-workflow {name} continue --mode=engine"
        RETURN (STOP — wait for user validation).

  END LOOP
```

**Display format after each action step:**
```
[Step {N}/{total_actions}] @{agent}: {action}
  Status: {completed|failed}
  Score: {score if applicable}
  Outputs: {list of output keys with brief values}

--- Output Preview ---
{First 500 chars of the main output, or artifact summary}

--- What's Next ---
  Phase: {next_phase if changing}
  Next step: @{next_agent} — {next_action}
  Command: *run-workflow {name} continue --mode=engine
  (or: *run-workflow {name} skip --mode=engine  if next step is optional)
```

---

### Final Report

Generated when the workflow reaches the end marker or a `complete` route.

```
=== Engine Execution Report ===
Workflow: {workflow_name}
Instance: {instance_id}
Started: {started_at}
Completed: {now}
Mode: ENGINE ({mode_description})

--- Steps Summary ---
  [x] {step_id}: @{agent} — {action} (score: {score})
  [x] {step_id}: @{agent} — {action}
  ...

--- Routing Decisions ---
  {step}: {condition} = {value} → {route_chosen}
  ...

--- Handoff Artifacts (yolo_continuous only) ---
  {list of handoff files generated in .aios/handoffs/}

--- Loop Guard Activity (yolo_continuous only) ---
  {target_step_id}: {attempts}/{max} loops
  ...

--- Execution Timeline (Story 16.4) ---
  {step_id}: @{agent} — {elapsed_ms}ms ({formatted duration})
  {step_id}: @{agent} — {elapsed_ms}ms ({formatted duration})
  Total: {total_elapsed}

--- Token Usage (Story 16.3) ---
  Total estimated: {total_estimated} tokens
  Per step:
    {step_id}: {tokens} tokens
    {step_id}: {tokens} tokens
  Context window: {total_estimated}/{context_window_limit} ({percentage}%)
  Warnings: {list of warnings_issued}

--- Resource Usage (Story 16.9) ---
  Duration: {elapsed_hours}h / {max_hours}h limit ({percentage}%)
  Estimated cost: ${estimated_cost} / ${max_cost} limit
  Warnings: {list of global_warnings_issued}

--- Timeout Report (Story 16.2) ---
  Steps with timeout:
    {step_id}: timeout={limit}s, elapsed={elapsed}s, triggered={true/false}
  (Only shown if any step had timeout_triggered=true)

--- Parse Failures & Retries (Story 16.5) ---
  {step_id}: {retry_count} parse retries (resolved: {yes/no})
  (Only shown if any parse retries occurred)

--- Output Validation (Story 16.7) ---
  {step_id}: missing outputs {list}, retries: {count} (resolved: {yes/no})
  (Only shown if any output validation failures occurred)

--- Routing Decisions (Updated Story 16.10) ---
  {step}: {condition} = {value} → {route_chosen} {fallback_used: true/false}
  ...

--- Final Outputs ---
  {key}: {summary_value}
  ...

--- Artifacts ---
  {list of all artifacts created across all steps}

--- Concurrency Events (Story 16.6) ---
  {list of concurrency_events if any}
  (Only shown if any conflicts detected)

State saved to: .aios/{instance_id}-engine-state.yaml
Version: {_version}
```

In step-by-step mode: after the report, ask the user if they want to create a handoff document.
In yolo_continuous mode: handoff documents were already generated automatically during execution.

---

## Elicitation Handler

For each step with `elicit: true`, the orchestrator collects input BEFORE spawning the subagent.

### Process

1. Read the `notes` field of the current step in the workflow YAML
2. If the step has a `uses` field, read the task file and find its `Entrada` section
3. For each field in `Entrada` with `origem: User Input` and `obrigatório: true`:
   - Use `AskUserQuestion` tool to ask the user
   - Validate the response against the field's `validação` rule
4. If no formal `Entrada` exists, extract questions from the step's `notes` field
5. Aggregate all responses into a YAML block:

```yaml
user_input:
  {field_name}: "{user_response}"
  {field_name}: "{user_response}"
```

6. Pass this block as `{{USER_INPUT}}` in the subagent prompt

### Rules

- Elicitation is collected by the orchestrator, NOT by the subagent
- The subagent receives pre-collected inputs and does NOT ask questions
- If the user declines to provide optional input, pass `null` for that field
- For the first step with `elicit: true`, also collect workflow-level `inputs` if defined

---

## Subagent Prompt Builder

Constructs the complete prompt for a subagent using the template.

### Process

1. **Load template** from `.aios-core/development/templates/subagent-step-prompt.md`
2. **Extract agent info:**
   - Read agent file → extract `agent.name` → `{{AGENT_NAME}}`
   - Read agent file → extract `agent.title` → `{{AGENT_TITLE}}`
   - Read agent file → extract full YAML block → `{{AGENT_YAML}}`
3. **Set project context (Story 18.6):**
   - If `state.project_context` is not null → `{{PROJECT_CONTEXT}}` = state.project_context
   - If null → `{{PROJECT_CONTEXT}}` = "No project context available"
4. **Extract task content:**
   - Read task file (from `uses`) → full content → `{{TASK_CONTENT}}`
   - If no `uses` field → set to "Execute the action described in Step Instructions"
5. **Set context variables:**
   - `{{WORKFLOW_NAME}}` from `workflow.name`
   - `{{STEP_ID}}` from step's `id` field
   - `{{PHASE_NAME}}` from current phase
   - `{{ACTION}}` from step's `action` field
6. **Build input data:**
   - For each item in step's `requires`:
     - Look up in `state.step_outputs`
     - Format as YAML block → `{{INPUT_DATA}}`
   - If no requires → set to "No previous step outputs required"
7. **Build reference data:**
   - Read each file from agent's `dependencies.data` list
   - Read each file from workflow's `resources.data` list
   - Concatenate contents → `{{REFERENCE_DATA}}`
   - If no data files → set to "No reference data"
8. **Set user input:**
   - From elicitation results → `{{USER_INPUT}}`
   - If `elicit: false` → set to "No user input required for this step"
9. **Set step notes:**
   - From step's `notes` field → `{{STEP_NOTES}}`
   - If no notes → set to "Execute the action as described above"
10. **Replace all variables** in the template string
11. **Return the complete prompt**

### Path Resolution for Agent Files

```
resolve_agent_path(agent_ref, target_context, squad_name):
  # Handle explicit prefix
  IF agent_ref starts with "core:":
    RETURN ".aios-core/development/agents/{agent_ref without prefix}.md"
  IF agent_ref starts with "squad:":
    RETURN "squads/{squad_name}/agents/{agent_ref without prefix}.md"

  # Context-based resolution
  IF target_context == "core":
    RETURN ".aios-core/development/agents/{agent_ref}.md"
  IF target_context == "squad":
    RETURN "squads/{squad_name}/agents/{agent_ref}.md"
  IF target_context == "hybrid":
    squad_path = "squads/{squad_name}/agents/{agent_ref}.md"
    core_path = ".aios-core/development/agents/{agent_ref}.md"
    IF squad_path exists → RETURN squad_path
    IF core_path exists → RETURN core_path
    ERROR: Agent not found in either context
```

### Path Resolution for Task Files (uses field)

```
resolve_task_path(uses_ref, target_context, squad_name):
  IF target_context == "core":
    RETURN ".aios-core/development/tasks/{uses_ref}.md"
  IF target_context == "squad":
    RETURN "squads/{squad_name}/tasks/{uses_ref}.md"
  IF target_context == "hybrid":
    squad_path = "squads/{squad_name}/tasks/{uses_ref}.md"
    core_path = ".aios-core/development/tasks/{uses_ref}.md"
    IF squad_path exists → RETURN squad_path
    IF core_path exists → RETURN core_path
    ERROR: Task not found in either context
```

### Path Resolution for Data Files

```
resolve_data_path(data_ref, target_context, squad_name):
  IF target_context == "core":
    RETURN ".aios-core/data/{data_ref}"
  IF target_context == "squad":
    RETURN "squads/{squad_name}/data/{data_ref}"
  IF target_context == "hybrid":
    squad_path = "squads/{squad_name}/data/{data_ref}"
    core_path = ".aios-core/data/{data_ref}"
    IF squad_path exists → RETURN squad_path
    IF core_path exists → RETURN core_path
    WARN: Data file not found, skip
```

---

## Output Parser

Extracts structured output from the subagent's response.

### Process

1. **Search for YAML block** in the subagent response:
   - Look for content between ` ```yaml ` and ` ``` ` markers
   - Specifically look for a block starting with `step_output:`
2. **Parse the YAML block** into a structured object
3. **Validate required fields:**
   - `status` must be `completed` or `failed`
   - `outputs` must be an object (can be empty)
4. **Extract outputs:**
   - Map each key in `outputs` to `state.step_outputs[{step_id}].{key}`
   - Store `score` if present
   - Store `artifacts` list if present
5. **Handle parse failures:**
   - Attempt 1: Regex for `step_output:` block without YAML markers
   - Attempt 2: Look for individual output fields mentioned in step's `outputs` list
   - Attempt 3: Mark step as needing manual review

### Regex Fallback Pattern

```
/step_output:\s*\n([\s\S]*?)(?=\n[^\s]|\Z)/
```

If the YAML block cannot be parsed:
- Extract `status` from any line containing "status: completed" or "status: failed"
- Extract individual output values by searching for each expected output key
- Log a warning that structured parsing failed

---

## Decision Router

Evaluates routing conditions and determines the next step.

### Process

For each step with `meta: routing`:

1. **Read the condition field** (e.g., `based_on_score_9p`, `based_on_compliance_score`)
2. **Map condition to state value:**
   - `based_on_score_9p` → look for `score_9p` in recent step outputs
   - `based_on_compliance_score` → look for `compliance_score` in recent step outputs
   - `based_on_validation_status` → look for `resultado_validado` or `status` in recent step outputs
   - `based_on_pedro_approval` → look for `aprovacao_final` in recent step outputs
3. **Evaluate each route:**
   - Read the route's name to determine the threshold (e.g., `score_below_70`, `score_90_plus`)
   - Compare the extracted value against the threshold
   - Select the matching route
4. **Execute the route action:**
   - `loop_back` → Find the target step ID in the sequence, set step index to that position
   - `continue` → Advance to the next step normally
   - `continue_with_adjustments` → Log adjustments needed, advance to target step
   - `apply_corrections` → Log corrections, advance to target step
   - `complete` → Set workflow status to `completed`, jump to Final Report
5. **Record decision in state:**

```yaml
decisions:
  - step: {routing_step_id}
    condition: {condition}
    evaluated_value: {the value checked}
    route_chosen: {route_name}
    action: {loop_back|continue|complete}
    target: {target_step_id if applicable}
    timestamp: {ISO timestamp}
```

### Threshold Extraction Rules

Parse the route key name to extract comparison:
- `*_below_{N}` → value < N
- `*_{N}_to_{M}` → N <= value <= M
- `*_{N}_plus` → value >= N
- `reprovado` → status equals "REPROVADO" or "failed" or false
- `aprovado` / `approved` → status equals "APROVADO" or "completed" or true
- `not_approved` → negation of approved
- `compliance_below_{N}` → compliance_score < N
- `compliance_{N}_plus` → compliance_score >= N

### Routing Fallback (Updated Story 16.10)

**In `yolo_continuous` mode**, the engine uses automatic fallback (never stops to ask):

```
Fallback chain:
  1. Evaluate condition normally
  2. If value absent → use route with default: true
  3. If no route matches → use route with default: true
  4. If no default route → use first route + log warning
  5. If no routes exist → ABORT "routing_undefined"
```

Each routing step accepts an optional `default: true` field on one route:
```yaml
routing:
  condition: based_on_score_9p
  routes:
    - name: simple_flow
      threshold: "< 9"
      target_step: implement_and_test
    - name: complex_flow
      threshold: ">= 9"
      target_step: architect_review
    - name: fallback
      default: true
      target_step: implement_and_test
```

**Pre-routing dependency check** (Story 16.10): Before evaluating conditions, verify that referenced values exist in state. If missing, skip to fallback immediately.

**In step-by-step mode**, existing behavior is maintained: display values to user, list routes, ask user to choose.

---

## Spawning a Subagent

The actual Task tool invocation for each action step.

### Invocation Pattern

```
Task tool call:
  description: "WF:{workflow_id} Step:{step_id} Agent:{agent_name}"
  subagent_type: "general-purpose"
  prompt: {built prompt from Subagent Prompt Builder}
  timeout: {resolved_timeout * 1000}ms  # Story 16.2: timeout per step (yolo_continuous only)
```

**Timeout behavior (Story 16.2):**
- In `yolo_continuous`: timeout passed to Task tool; if exceeded, step marked as `timeout` and treated as failure
- In step-by-step: NO timeout applied (user controls timing)
- Precedence: `step.timeout` > `workflow.metadata.default_step_timeout` > `ENGINE_DEFAULT_TIMEOUT` (300s)

### Important Rules

- Each subagent runs in an isolated context (separate process)
- The subagent does NOT have access to the orchestrator's conversation history
- The subagent does NOT have access to other subagents' outputs (only what's passed via prompt)
- The subagent should NOT use AskUserQuestion (all inputs are pre-collected)
- The orchestrator waits for the subagent to complete before proceeding

---

## State Persistence (Updated Story 16.6)

State is saved after **every invocation** (start, continue, skip, abort) using `save_state_with_locking()`. This enables resume across sessions with **optimistic locking** to detect concurrent access.

**Write mechanism:** Atomic write via temp file + rename (prevents partial corruption).
**Version tracking:** `_version` incremented on every save; conflict detected if disk version > expected.
**Resume validation:** On `continue` action, verify step_results count matches current_step_index.

```yaml
# .aios/{instance-id}-engine-state.yaml
engine_state:
  workflow_id: {id}
  workflow_name: {name}
  instance_id: {instance_id}
  target_context: {context}
  squad_name: {squad}
  mode: engine
  started_at: {timestamp}
  updated_at: {current timestamp}
  status: active|completed|aborted
  current_step_index: {index of NEXT step to process}
  current_phase: {phase name}
  last_completed_step: {id of last completed action step, or null}
  action_steps_completed: {count}
  action_steps_total: {count}

  step_outputs:
    {step_id}:
      {output_key}: {output_value}
      ...

  step_results:
    {step_id}:
      status: completed|failed|skipped
      outputs: {parsed outputs}
      score: {if applicable}
      artifacts: [{list}]
      spawned_at: {timestamp}
      completed_at: {timestamp}
      retries: {count}

  decisions:
    - {decision records from routing}

  elicitation_responses:
    {step_id}:
      {field}: {value}

  # yolo_continuous fields (only present when mode=yolo_continuous)
  loop_guard:
    max_loops_per_target: 3
    current_loops:
      {target_step_id}: {count}

  handoffs_generated:
    - {filename_1}
    - {filename_2}

  # Story 16.2: Timeout tracking
  default_step_timeout: {resolved timeout default}

  # Story 16.3: Token tracking
  token_tracking:
    total_estimated: {accumulated tokens}
    per_step:
      {step_id}: {estimated tokens}
    context_window_limit: 180000
    warnings_issued: []

  # Story 16.4: Execution log (append-only)
  execution_log:
    - {timestamp, event, fields...}

  # Story 16.5: Parse retry counters
  parse_retries:
    {step_id}: {count}

  # Story 16.6: State locking
  _version: {integer, incremented on each save}
  _session_id: {uuid, unique per session}
  _expected_version: {last known version}
  concurrency_events: []

  # Story 16.7: Output validation retry counters
  output_retries:
    {step_id}: {count}

  # Story 16.8: Handoff edge cases
  same_agent_summaries: []
  handoff_write_failures: []

  # Story 16.9: Global limits
  execution_constraints:
    max_workflow_duration_hours: 4
    max_estimated_cost_usd: 10.0
    warn_at_percent: 80
  global_warnings_issued: []

  # Story 18.1: Failure context for retry injection
  failure_contexts:
    {target_step_id}:
      reason: "qa_gate_rejected|execution_failed|timeout"
      feedback: "Specific feedback extracted from failed output"
      attempt: {current attempt number}
      max_attempts: {max loops for this target}
      previous_outputs: "Summarized outputs from failed attempt"
      collected_at: {ISO timestamp}
```

### Resume Across Sessions

The state file persists on disk. To resume in a new Claude Code session:

```
@aios-master
*run-workflow {name} continue --mode=engine
```

The engine loads the state, reads `current_step_index`, and picks up exactly where it left off. All previous step outputs are available in `step_outputs` for the `requires` chain.

---

## Retry Logic

When a step fails:

1. Check `workflow.global_error_handling.max_retries_per_phase` (default: 2)
2. Check `state.retries[{step_id}]` count
3. If retries < max:
   - Increment retry counter
   - Add previous error to the prompt as additional context:
     ```
     ## Previous Attempt Failed
     Error: {error description}
     Previous output: {raw output if available}
     Please fix the issues and try again.
     ```
   - Re-spawn the subagent
4. If retries >= max:
   - **Step-by-step mode:**
     - Display error to user
     - Offer options:
       1. Retry manually (user provides input)
       2. Skip step (if optional)
       3. Abort workflow
   - **yolo_continuous mode:**
     - Check step's `on_failure` field for automatic routing
     - If `on_failure` exists → route to target (with loop guard check)
     - If no `on_failure` → ABORT with report (no user prompt)

---

## Output Format

The engine produces structured output at the end of execution. See Step 6 (Final Report) in the Engine Loop section above.
