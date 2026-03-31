#!/usr/bin/env bash
# check-pending-workflows.sh — Detect pending workflows for auto-resume
# Part of Story 26.1: Engine Auto-Resume via Claude Code Hooks
#
# Scans .aios/*-engine-state.yaml files for status: active
# Validates state integrity before recommending resume
# Enforces max resume_attempts (3) — auto-aborts if exceeded
#
# Exit codes:
#   0 — pending workflows found (output on stdout)
#   1 — no pending workflows
#   2 — error (invalid state files, etc.)

set -euo pipefail

AIOS_DIR=".aios"
MAX_RESUME_ATTEMPTS=3
REQUIRED_FIELDS=("workflow_id" "workflow_name" "instance_id" "status" "current_step_index")

# Colors (only if terminal supports it)
if [ -t 1 ]; then
  YELLOW='\033[1;33m'
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  NC='\033[0m'
else
  YELLOW=''
  RED=''
  GREEN=''
  NC=''
fi

# Helper: extract YAML value (simple single-line fields only)
yaml_value() {
  local file="$1"
  local key="$2"
  grep -E "^${key}:" "$file" 2>/dev/null | head -1 | sed "s/^${key}:[[:space:]]*//" | sed 's/^["'"'"']//' | sed 's/["'"'"']$//' | tr -d '\r'
}

# Helper: check if field exists in file
yaml_has_field() {
  local file="$1"
  local key="$2"
  grep -qE "^${key}:" "$file" 2>/dev/null
}

# Validate state file has all required fields
validate_state() {
  local file="$1"
  local missing=()

  for field in "${REQUIRED_FIELDS[@]}"; do
    if ! yaml_has_field "$file" "$field"; then
      missing+=("$field")
    fi
  done

  if [ ${#missing[@]} -gt 0 ]; then
    echo "INVALID: $file — missing fields: ${missing[*]}" >&2
    return 1
  fi

  # Validate current_step_index is a number >= 0
  local step_index
  step_index=$(yaml_value "$file" "current_step_index")
  if ! [[ "$step_index" =~ ^[0-9]+$ ]]; then
    echo "INVALID: $file — current_step_index is not a valid number: '$step_index'" >&2
    return 1
  fi

  return 0
}

# Check if heartbeat is stale (Story 26.2 dependency — graceful if field missing)
check_heartbeat() {
  local file="$1"
  if yaml_has_field "$file" "heartbeat"; then
    # Heartbeat field exists — Story 26.2 is implemented
    # For now, just report presence (actual staleness check deferred to 26.2)
    echo "heartbeat_present"
  else
    # No heartbeat field — cannot determine if actively running
    echo "no_heartbeat"
  fi
}

# Main scan
found_pending=0
pending_workflows=()

# Check if AIOS directory exists
if [ ! -d "$AIOS_DIR" ]; then
  exit 1
fi

# Scan for engine state files
for state_file in "$AIOS_DIR"/*-engine-state.yaml "$AIOS_DIR"/*-state.yaml; do
  # Skip glob patterns that didn't match
  [ -e "$state_file" ] || continue

  # Extract status
  status=$(yaml_value "$state_file" "status")

  # Only process active workflows
  if [ "$status" != "active" ]; then
    continue
  fi

  # Validate state integrity
  if ! validate_state "$state_file"; then
    echo -e "${RED}WARNING: Corrupted state file: $state_file${NC}" >&2
    continue
  fi

  # Extract workflow info
  workflow_id=$(yaml_value "$state_file" "workflow_id")
  workflow_name=$(yaml_value "$state_file" "workflow_name")
  instance_id=$(yaml_value "$state_file" "instance_id")
  step_index=$(yaml_value "$state_file" "current_step_index")
  current_phase=$(yaml_value "$state_file" "current_phase")
  updated_at=$(yaml_value "$state_file" "updated_at")

  # Check resume_attempts
  resume_attempts=$(yaml_value "$state_file" "resume_attempts")
  if [ -z "$resume_attempts" ]; then
    resume_attempts=0
  fi

  # Check heartbeat (graceful — works without 26.2)
  heartbeat_status=$(check_heartbeat "$state_file")

  # If max resume attempts exceeded, report for abort
  if [ "$resume_attempts" -ge "$MAX_RESUME_ATTEMPTS" ]; then
    echo -e "${RED}ABORT_REQUIRED: $state_file — resume_attempts ($resume_attempts) >= max ($MAX_RESUME_ATTEMPTS)${NC}"
    echo "  workflow: $workflow_name ($workflow_id)"
    echo "  instance: $instance_id"
    echo "  action: Mark as aborted with reason=max_resume_attempts"
    found_pending=1
    pending_workflows+=("ABORT:$state_file:$workflow_name:$instance_id:$resume_attempts")
    continue
  fi

  # Report as pending for resume
  echo -e "${YELLOW}PENDING: $state_file${NC}"
  echo "  workflow: $workflow_name ($workflow_id)"
  echo "  instance: $instance_id"
  echo "  step_index: $step_index"
  echo "  phase: ${current_phase:-unknown}"
  echo "  last_updated: ${updated_at:-unknown}"
  echo "  resume_attempts: $resume_attempts / $MAX_RESUME_ATTEMPTS"
  echo "  heartbeat: $heartbeat_status"
  echo "  action: *run-workflow $workflow_id continue --mode=engine"
  echo ""

  found_pending=1
  pending_workflows+=("RESUME:$state_file:$workflow_name:$instance_id:$resume_attempts")
done

# Summary
if [ "$found_pending" -eq 1 ]; then
  echo "---"
  echo "Found ${#pending_workflows[@]} pending workflow(s)."
  for entry in "${pending_workflows[@]}"; do
    IFS=':' read -r action file name instance attempts <<< "$entry"
    if [ "$action" = "ABORT" ]; then
      echo "  - $name ($instance): NEEDS ABORT (attempts: $attempts)"
    else
      echo "  - $name ($instance): Ready to resume (attempts: $attempts)"
    fi
  done
  exit 0
else
  exit 1
fi
