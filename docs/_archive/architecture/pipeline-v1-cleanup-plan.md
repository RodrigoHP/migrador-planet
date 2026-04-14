# Pipeline v1 Cleanup Plan

## Overview

This document describes the plan for removing pipeline v1 (28-stage) code after pipeline v2 (5-stage) has been validated in production.

**Status:** Draft
**Created:** 2026-03-22 (Story 13.12)
**Prerequisite:** Pipeline v2 running in production with `PIPELINE_VERSION=v2` for at least 2 weeks with zero critical issues.

---

## When to Remove v1

### Criteria (ALL must be met)

1. **Production validation:** v2 has been running in production for >= 2 weeks
2. **Zero critical bugs:** No pipeline-related P0/P1 issues in that period
3. **Performance baseline met:** 100 pages < 60s, API cost < $0.20/job
4. **All document types tested:** Boleto, Fatura, Recibo, Nota Fiscal tested end-to-end
5. **Frontend rendering verified:** Layout switch, multidimensional coverage, table overlays all working
6. **Stakeholder sign-off:** Product owner confirms v2 parity with v1

---

## Files to Remove (Backend)

### Pipeline v1 Stage Files (`backend/services/stages/`)

These files implement the 28-stage v1 pipeline:

| File | Description | Action |
|------|-------------|--------|
| `confidence_scoring.py` | v1 confidence scoring (replaced by Stage 4.6) | Remove |
| `field_matching.py` | v1 field matching (replaced by Stage 4.5) | Remove |
| `template_draft.py` | v1 template draft (replaced by Stage 5) | Remove |
| `vision_self_check.py` | v1 vision self-check | Remove |
| `visual_interpretation.py` | v1 visual interpretation (replaced by Stage 3.2) | Remove |
| `visual_segmentation.py` | v1 visual segmentation (replaced by Stage 3.2) | Remove |

### Pipeline v1 Model/Registry

| File | Description | Action |
|------|-------------|--------|
| `backend/models/pipeline.py` | `PipelineDefinition`, `default_registry` (28-stage definitions) | Remove after confirming no other imports |

### Pipeline v1 Tests

| File | Description | Action |
|------|-------------|--------|
| `backend/tests/test_pipeline.py` | v1 pipeline integration tests | Remove |
| `backend/tests/test_pipeline_result.py` | v1 pipeline result tests | Remove |
| `backend/tests/test_field_matching.py` | v1 field matching tests | Remove |
| `backend/tests/test_layout_intelligence.py` | v1 layout intelligence tests | Remove |
| `backend/tests/test_matching.py` | v1 matching tests | Remove |
| `backend/tests/test_vision_ai.py` | v1 vision AI tests | Remove |
| `backend/tests/test_template_draft.py` | v1 template draft tests | Remove |
| `backend/tests/test_validation_template.py` | v1 validation tests | Remove |

---

## Files to Modify (Backend)

### `backend/routers/analyze.py`

1. Remove `_run_pipeline()` function (v1 executor, lines ~224-349)
2. Remove feature flag logic in `start_analyze()`:
   - Remove `_get_pipeline_version()` function
   - Remove the `if pipeline_version == "v2": ... else: ...` branch
   - Always call `_run_pipeline_v2()`
3. Remove import of `default_registry` from `models.pipeline`
4. Remove `pipeline_version` from the response dict

### `backend/routers/analyze.py` — Response Change

```python
# Before (with feature flag)
return {"status": "started", "job_id": job_id, "pipeline_version": pipeline_version}

# After (v2 only)
return {"status": "started", "job_id": job_id}
```

---

## Files to Remove (Frontend)

| File | Description | Action |
|------|-------------|--------|
| `frontend/src/pages/analyzingPageConstants.ts` | v1 stage definitions (28 stages) | Remove |

---

## Files to Modify (Frontend)

### `frontend/src/pages/AnalyzingPage.vue`

1. Remove `isV2` ref and all `v-if="!isV2"` / `v-if="isV2"` conditionals
2. Remove v1 stage rendering block (`PIPELINE_BLOCKS` loop)
3. Remove v1 event handling code (`!isV2.value && data.block !== undefined`)
4. Keep only v2 stage rendering (`PIPELINE_V2_STAGES` loop)
5. Remove import of `analyzingPageConstants.ts`

### `frontend/src/pages/analyzingPageConstantsV2.ts`

Rename to `analyzingPageConstants.ts` after removing the v1 file.

---

## Environment Variable Cleanup

| Variable | Current | After Cleanup |
|----------|---------|---------------|
| `PIPELINE_VERSION` | Required (`v1` or `v2`) | Remove — v2 is the only pipeline |
| `VISION_AI_ENABLED` | Optional (default `true`) | Keep — still controls GPT-4o Vision |
| `OPENROUTER_API_KEY` | Required for LLM | Keep — used by Stages 3 and 4 |

---

## Migration Checklist

### Pre-Cleanup

- [ ] All E2E tests pass with `PIPELINE_VERSION=v2`
- [ ] Benchmark: 100 pages < 60s confirmed
- [ ] API cost < $0.20/job confirmed with real PDFs
- [ ] Frontend renders correctly: layout switch, coverage, overlays
- [ ] SSE 5-stage sub-progress works in production
- [ ] No regression in existing functionality

### During Cleanup

- [ ] Create branch `feature/cleanup-pipeline-v1`
- [ ] Remove v1 stage files listed above
- [ ] Remove `models/pipeline.py` (verify no other imports first)
- [ ] Modify `analyze.py` — remove v1 executor and feature flag
- [ ] Remove v1 frontend constants
- [ ] Simplify `AnalyzingPage.vue` — remove v1 conditionals
- [ ] Remove `PIPELINE_VERSION` from all deployment configs
- [ ] Remove v1-specific test files
- [ ] Adapt remaining shared tests if needed
- [ ] Run full test suite
- [ ] Create PR with cleanup changes

### Post-Cleanup

- [ ] Verify production deployment works without `PIPELINE_VERSION` env var
- [ ] Monitor for 48h after deployment
- [ ] Update architecture docs to remove v1 references
- [ ] Close Epic 13 as complete

---

## Risk Mitigation

1. **Rollback plan:** Keep the cleanup branch separate; if issues arise, revert the merge
2. **Feature flag grace period:** Even after cleanup, the v2 code structure supports adding a new flag if needed
3. **Test coverage:** All v2 tests (E2E, benchmark, unit) must pass before and after cleanup

---

## Estimated Effort

| Task | Estimate |
|------|----------|
| Remove v1 backend files | 1h |
| Modify analyze.py | 30min |
| Remove v1 frontend files | 30min |
| Simplify AnalyzingPage.vue | 1h |
| Update tests | 1h |
| Code review + testing | 2h |
| **Total** | **~6h** |
