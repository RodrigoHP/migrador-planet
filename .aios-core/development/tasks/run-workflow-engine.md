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
story: 16.1
version: 3.0.0
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
updated_at: 2026-03-29
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
  loop_guard:
    max_loops_per_target: 3   # overridable by workflow.failure_recovery
    current_loops: {}
  handoffs_generated: []
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

### Failure Detection

The engine determines if a step failed by inspecting the parsed `step_output`:

```
FUNCTION step_failed(parsed_output, step):
  # 1. Parse failure — subagent returned no structured output
  IF parsed_output is null:
    RETURN true

  # 2. Explicit status
  IF parsed_output.status == "failed":
    RETURN true

  # 3. QA gate verdict
  IF step.id contains "qa_gate" OR step.id contains "gate":
    IF parsed_output.outputs.gate_verdict == "REJECT":
      RETURN true

  RETURN false
```

In `yolo_continuous` mode, failure detection drives automatic routing:
- If step has `on_failure` field → route to target step (with loop guard)
- If step has NO `on_failure` → treat as blocking error → ABORT

---

### Handoff Artifact Generation

When transitioning between agents in `yolo_continuous` mode, the engine generates a handoff artifact to preserve context:

```
FUNCTION generate_handoff(current_step, next_step, state):
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
        # Collect all outputs from the completed step
        FOR each key in state.step_outputs[current_step.id]:
          key: value (truncated to 500 chars if needed)
      timestamp: {ISO now}
  }

  # Write to .aios/handoffs/
  filename = "handoff-{current_step.agent}-to-{next_step.agent}-{timestamp}.yaml"
  Write artifact to .aios/handoffs/{filename}

  # Track in state
  state.handoffs_generated.append(filename)

  Log: "🔄 Handoff: @{current_step.agent} → @{next_step.agent}"
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
      Execute the step:
        1. IF elicit=true AND mode != "yolo_continuous" → run Elicitation Handler
           (In yolo_continuous, elicitation is skipped — decisions are autonomous)
        2. Resolve agent file path
        3. Read agent file
        4. Resolve task file path (from 'uses')
        5. Read task file (if 'uses' defined)
        6. Read data files (agent deps + workflow resources)
        7. Collect requires from state.step_outputs
        8. Build prompt (Subagent Prompt Builder)
        9. Spawn subagent via Task tool
        10. Parse output (Output Parser)
        11. Store in state.step_results[{step_id}] and state.step_outputs
      Display step result to user.

      # --- Mode-dependent behavior after step execution ---
      IF state.mode == "yolo_continuous":
        # Check for failure
        IF step_failed(parsed_output, item):
          IF item has 'on_failure' field:
            target = find_step_index(item.on_failure, sequence)
            guard_result = check_loop_guard(state, item.on_failure)
            IF guard_result == "ABORT":
              → Generate Abort Report. Set status=aborted. RETURN.
            ELSE:
              Log: "⚠️ Step failed — looping to {item.on_failure} (attempt {count})"
              index = target
              Save state.
              CONTINUE LOOP
          ELSE:
            # No on_failure defined — blocking error
            Log: "❌ Step failed with no recovery route — aborting"
            → Generate Abort Report. Set status=aborted. RETURN.

        # Step succeeded — generate handoff if agent changes
        next_item = find_next_action_step(sequence, index + 1)
        IF next_item AND next_item.agent != item.agent:
          generate_handoff(item, next_item, state)

        # Continue to next step (NO STOP)
        index = index + 1
        Save state.
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

--- Final Outputs ---
  {key}: {summary_value}
  ...

--- Artifacts ---
  {list of all artifacts created across all steps}

State saved to: .aios/{instance_id}-engine-state.yaml
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
3. **Extract task content:**
   - Read task file (from `uses`) → full content → `{{TASK_CONTENT}}`
   - If no `uses` field → set to "Execute the action described in Step Instructions"
4. **Set context variables:**
   - `{{WORKFLOW_NAME}}` from `workflow.name`
   - `{{STEP_ID}}` from step's `id` field
   - `{{PHASE_NAME}}` from current phase
   - `{{ACTION}}` from step's `action` field
5. **Build input data:**
   - For each item in step's `requires`:
     - Look up in `state.step_outputs`
     - Format as YAML block → `{{INPUT_DATA}}`
   - If no requires → set to "No previous step outputs required"
6. **Build reference data:**
   - Read each file from agent's `dependencies.data` list
   - Read each file from workflow's `resources.data` list
   - Concatenate contents → `{{REFERENCE_DATA}}`
   - If no data files → set to "No reference data"
7. **Set user input:**
   - From elicitation results → `{{USER_INPUT}}`
   - If `elicit: false` → set to "No user input required for this step"
8. **Set step notes:**
   - From step's `notes` field → `{{STEP_NOTES}}`
   - If no notes → set to "Execute the action as described above"
9. **Replace all variables** in the template string
10. **Return the complete prompt**

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

### Manual Routing Fallback

If no route matches the evaluated value:
1. Display current values to the user
2. List available routes with their descriptions
3. Use AskUserQuestion to let user choose
4. Record as manual decision in state

---

## Spawning a Subagent

The actual Task tool invocation for each action step.

### Invocation Pattern

```
Task tool call:
  description: "WF:{workflow_id} Step:{step_id} Agent:{agent_name}"
  subagent_type: "general-purpose"
  prompt: {built prompt from Subagent Prompt Builder}
```

### Important Rules

- Each subagent runs in an isolated context (separate process)
- The subagent does NOT have access to the orchestrator's conversation history
- The subagent does NOT have access to other subagents' outputs (only what's passed via prompt)
- The subagent should NOT use AskUserQuestion (all inputs are pre-collected)
- The orchestrator waits for the subagent to complete before proceeding

---

## State Persistence

State is saved after **every invocation** (start, continue, skip, abort). This enables resume across sessions.

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
