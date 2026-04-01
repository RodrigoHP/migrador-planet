# QA Agent Memory (Quinn)

## Active Patterns
<!-- Current, verified patterns used by this agent -->

### RCA v9.0 — Progressive Escalation
- `/investigate` ou `*investigate` — OBRIGATORIO para qualquer bug
- 3 layers: FAST (70%, ~2min) / STANDARD (25%, ~10min) / DEEP (5%, ~30min)
- Auto-escalation: FAST→STANDARD→DEEP conforme complexidade
- Origin Gate: 5-point checkpoint OBRIGATORIO antes de qualquer fix
- `--yolo`: investigar + implementar + testar sem paradas
- `--deep`: forcar pipeline completo (11 fases)
- @qa investiga, @dev implementa, @architect revisa (se escalation)
- Toda investigacao DEVE persistir em investigations.yaml + learned-patterns.yaml

### Review Patterns
- ONLY update "QA Results" section in story files
- Gate decisions: PASS / CONCERNS / FAIL / WAIVED
- CodeRabbit: @qa identifica issues, @dev implementa fixes (delegate_fix_to_dev)

### Test Infrastructure
- Backend: `pytest` — tests in `backend/tests/`
- Frontend: `vitest` — tests in `frontend/src/**/*.test.ts`
- Coverage: `pytest --cov` / `npx vitest --coverage`

### Quality Checks (7-point)
1. Code review (patterns, readability)
2. Unit tests (coverage, passing)
3. Acceptance criteria met
4. No regressions
5. Performance acceptable
6. Security (OWASP basics)
7. Documentation updated

### Known Problem Areas
- `frontend/src/components/editor/` — 4 bugs (selector mismatches, CSS reset)
- `backend/services/pipeline/` — 3 bugs (stage contracts, data flow)
- `backend/services/storage/` — 2 bugs (path resolution, gateway)
- Anti-pattern mais recorrente: AP-001 guard_missing (4 ocorrencias)

### Knowledge Base Locations
- Investigations: `docs/qa/rca-knowledge/investigations.yaml`
- SOPs: `docs/qa/rca-knowledge/sops/`
- Anti-patterns: `docs/qa/known-anti-patterns.md`
- Tag taxonomy: `docs/qa/rca-knowledge/tag-taxonomy.yaml`
- Learned patterns: `.aios-core/data/learned-patterns.yaml`
- Investigation artifacts: `.aios/investigations/`

### Git Rules
- Read-only: `git status`, `git log`, `git diff`
- NEVER commit or push

## Promotion Candidates
<!-- Patterns seen across 3+ agents — candidates for CLAUDE.md or .claude/rules/ -->
- **guard_missing pattern** | Source: @qa (AP-001, 4 occurrences) | Detected: 2026-03-31

## Archived
<!-- Patterns no longer relevant — kept for history -->
- ~~CodeRabbit auto_fix for CRITICAL/HIGH~~ | Archived: 2026-04-01 | Reason: Changed to delegate_fix_to_dev in v9.0
