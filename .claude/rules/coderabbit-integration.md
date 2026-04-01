---
paths:
  - ".aios-core/**"
  - "tests/**"
  - "packages/**"
  - "bin/**"
---

# CodeRabbit Integration — Detailed Rules

## Self-Healing Configuration

### Dev Phase (@dev — Story Development Cycle Phase 3)

```yaml
mode: light
max_iterations: 2
timeout_minutes: 30
severity_filter: [CRITICAL, HIGH]
behavior:
  CRITICAL: auto_fix
  HIGH: auto_fix (iteration < 2) else document_as_debt
  MEDIUM: document_as_debt
  LOW: ignore
```

**Flow:**
```
RUN CodeRabbit → CRITICAL found?
  YES → auto-fix (iteration < 2) → Re-run
  NO → Document HIGH as debt, proceed
After 2 iterations with CRITICAL → HALT, manual intervention
```

### QA Phase (@qa — QA Loop Pre-Review)

```yaml
mode: full
max_iterations: 1
timeout_minutes: 30
severity_filter: [CRITICAL, HIGH]
behavior:
  CRITICAL: delegate_fix_to_dev  # @qa identifica, @dev implementa
  HIGH: delegate_fix_to_dev      # @qa identifica, @dev implementa
  MEDIUM: document_as_debt
  LOW: ignore
```

**Flow:**
1. Pre-commit review scan
2. Document CRITICAL/HIGH issues with file, line, description
3. Generate fix_request for @dev (via *create-fix-request)
4. Manual QA analysis (architectural, traceability, NFR)
5. Gate decision (verdict) — FAIL if CRITICAL/HIGH found

**IMPORTANT:** @qa does NOT auto-fix. @qa identifies and delegates to @dev.

## Severity Handling Summary

| Severity | Dev Phase | QA Phase |
|----------|-----------|----------|
| CRITICAL | auto_fix, block if persists | delegate_fix_to_dev, block |
| HIGH | auto_fix, document if fails | delegate_fix_to_dev, block |
| MEDIUM | document_as_tech_debt | document_as_tech_debt |
| LOW | ignore | ignore |

## WSL Execution (Windows)

```bash
# Converter path Windows para WSL: C:\CohortAios\projeto → /mnt/c/CohortAios/projeto
# Usar ${PROJECT_ROOT_WSL} como placeholder — substituir pelo path real do projeto

# Self-healing mode (automatic in dev tasks)
wsl bash -c 'cd ${PROJECT_ROOT_WSL} && ~/.local/bin/coderabbit --severity CRITICAL,HIGH --auto-fix'

# Manual review
wsl bash -c 'cd ${PROJECT_ROOT_WSL} && ~/.local/bin/coderabbit -t uncommitted'

# Prompt-only mode
wsl bash -c 'cd ${PROJECT_ROOT_WSL} && ~/.local/bin/coderabbit --prompt-only -t uncommitted'
```

## Integration Points

| Workflow | Phase | Trigger | Agent |
|----------|-------|---------|-------|
| Story Development Cycle | 3 (Implement) | After task completion | @dev |
| QA Loop | 1 (Review) | At review start | @qa |
| Standalone | Any | `*coderabbit-review` command | Any |

## Focus Areas by Story Type

| Story Type | Primary Focus |
|-----------|--------------|
| Feature | Code patterns, test coverage, API design |
| Bug Fix | Regression risk, root cause coverage |
| Refactor | Breaking changes, interface stability |
| Documentation | Markdown quality, reference validity |
| Database | SQL injection, RLS coverage, migration safety |

## Report Location

CodeRabbit reports saved to: `docs/qa/coderabbit-reports/`

## Configuration Reference

Full config in `.aios-core/core-config.yaml` under `coderabbit_integration` section.
